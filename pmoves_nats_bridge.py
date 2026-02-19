"""Optional NATS publisher for llama-throughput-lab benchmark events.

Degrades gracefully when NATS is unavailable — all public functions
are safe to call even without a connection.

Subjects
--------
- ``llama.benchmark.started.v1``  — sweep config, model, timestamp
- ``llama.benchmark.cell.v1``     — per-row results (throughput_tps, tokens, errors)
- ``llama.benchmark.completed.v1``— sweep summary, best config, CSV path
"""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any

_nc = None  # lazily initialised NATS connection

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")


def _ensure_connected() -> Any:
    """Return an async-compatible NATS client, or *None* if unavailable."""
    global _nc
    if _nc is not None:
        return _nc
    try:
        import nats  # noqa: F811

        # Synchronous helper — sweep scripts are sync, so we use a thin
        # wrapper that creates a one-shot event-loop per publish batch.
        _nc = _SyncNats(NATS_URL)
        return _nc
    except Exception:
        return None


class _SyncNats:
    """Minimal synchronous wrapper around *nats-py* async client."""

    def __init__(self, url: str) -> None:
        import asyncio

        import nats as _nats_mod

        self._loop = asyncio.new_event_loop()
        self._nc = self._loop.run_until_complete(_nats_mod.connect(url))

    @property
    def is_connected(self) -> bool:
        return self._nc.is_connected

    def publish(self, subject: str, payload: bytes) -> None:
        import asyncio

        self._loop.run_until_complete(self._nc.publish(subject, payload))
        self._loop.run_until_complete(self._nc.flush())

    def close(self) -> None:
        import asyncio

        self._loop.run_until_complete(self._nc.drain())
        self._loop.close()


def _envelope(subject: str, payload: dict) -> bytes:
    return json.dumps(
        {
            "id": str(uuid.uuid4()),
            "topic": subject,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "version": "v1",
            "source": "llama-throughput-lab",
            "payload": payload,
        }
    ).encode()


def _safe_publish(subject: str, payload: dict) -> None:
    try:
        nc = _ensure_connected()
        if nc is None:
            return
        nc.publish(subject, _envelope(subject, payload))
    except Exception:
        pass  # graceful degradation


# ── Public API ───────────────────────────────────────────────────────


def publish_started(
    sweep_type: str,
    model_path: str,
    config: dict,
) -> None:
    """Announce that a benchmark sweep has started."""
    _safe_publish(
        "llama.benchmark.started.v1",
        {
            "sweep_type": sweep_type,
            "model": model_path,
            "config": config,
        },
    )


def publish_cell(
    sweep_type: str,
    row: dict,
) -> None:
    """Publish a single benchmark measurement row."""
    _safe_publish(
        "llama.benchmark.cell.v1",
        {
            "sweep_type": sweep_type,
            **row,
        },
    )


def publish_completed(
    sweep_type: str,
    best: dict,
    csv_path: str,
    total_cells: int,
) -> None:
    """Announce that a benchmark sweep has completed."""
    _safe_publish(
        "llama.benchmark.completed.v1",
        {
            "sweep_type": sweep_type,
            "best": best,
            "csv_path": csv_path,
            "total_cells": total_cells,
        },
    )


def close() -> None:
    """Drain and close the NATS connection (if open)."""
    global _nc
    if _nc is not None:
        try:
            _nc.close()
        except Exception:
            pass
        _nc = None
