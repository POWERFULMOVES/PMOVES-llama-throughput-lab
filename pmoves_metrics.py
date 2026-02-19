"""Prometheus metrics exporter for llama-throughput-lab.

Exposes ``/metrics`` and ``/healthz`` on port 8201 (configurable via
``METRICS_PORT``).  Import and call ``update_cell()`` / ``update_sweep()``
from sweep scripts to push live data into the gauges.

Can also be run standalone as the container entrypoint — it starts the
HTTP server and blocks until interrupted.
"""

from __future__ import annotations

import os
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any

try:
    from prometheus_client import (
        Counter,
        Gauge,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )

    _HAS_PROM = True
except ImportError:
    _HAS_PROM = False

METRICS_PORT = int(os.getenv("METRICS_PORT", "8201"))

# ── Metrics definitions ──────────────────────────────────────────────

if _HAS_PROM:
    THROUGHPUT_TPS = Gauge(
        "llama_benchmark_throughput_tps",
        "Tokens per second for the most recent measurement",
        ["model", "sweep_type", "config"],
    )
    SWEEPS_TOTAL = Counter(
        "llama_benchmark_sweeps_total",
        "Total number of completed sweeps",
        ["sweep_type"],
    )
    ERRORS_TOTAL = Counter(
        "llama_benchmark_errors_total",
        "Total benchmark errors",
        ["sweep_type"],
    )
    LAST_SWEEP_TS = Gauge(
        "llama_benchmark_last_sweep_timestamp",
        "Unix timestamp of most recent completed sweep",
    )
    BEST_THROUGHPUT = Gauge(
        "llama_benchmark_best_throughput_tps",
        "Best throughput achieved across all sweeps",
        ["model", "sweep_type"],
    )


# ── Public helpers (called from sweep scripts) ───────────────────────


def update_cell(
    model: str,
    sweep_type: str,
    config_label: str,
    throughput_tps: float,
    errors: int = 0,
) -> None:
    """Record a single benchmark cell measurement."""
    if not _HAS_PROM:
        return
    THROUGHPUT_TPS.labels(
        model=model, sweep_type=sweep_type, config=config_label
    ).set(throughput_tps)
    if errors:
        ERRORS_TOTAL.labels(sweep_type=sweep_type).inc(errors)


def update_sweep(
    model: str,
    sweep_type: str,
    best_throughput: float,
) -> None:
    """Record sweep completion."""
    if not _HAS_PROM:
        return
    SWEEPS_TOTAL.labels(sweep_type=sweep_type).inc()
    LAST_SWEEP_TS.set(time.time())
    BEST_THROUGHPUT.labels(model=model, sweep_type=sweep_type).set(
        best_throughput
    )


# ── HTTP server ──────────────────────────────────────────────────────

_started = time.time()


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/healthz":
            body = b'{"ok":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/metrics" and _HAS_PROM:
            body = generate_latest()
            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPE_LATEST)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def log_message(self, fmt: str, *args: Any) -> None:
        # suppress noisy access logs
        pass


_server: HTTPServer | None = None


def start_server(port: int = METRICS_PORT, background: bool = True) -> None:
    """Start the metrics/health HTTP server.

    When *background=True* (default), runs in a daemon thread so sweep
    scripts can call this once and continue.
    """
    global _server
    if _server is not None:
        return
    _server = HTTPServer(("0.0.0.0", port), _Handler)
    if background:
        t = threading.Thread(target=_server.serve_forever, daemon=True)
        t.start()
    else:
        _server.serve_forever()


if __name__ == "__main__":
    print(f"llama-throughput-lab metrics server on :{METRICS_PORT}")
    start_server(background=False)
