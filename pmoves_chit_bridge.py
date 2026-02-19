"""Optional CHIT bridge for storing benchmark results as reasoning patterns.

Posts sweep results to Cipher Memory API for persistent storage and
optionally archives CSV files to MinIO via the presign service.

Degrades gracefully when services are unavailable.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError


CIPHER_MEMORY_URL = os.getenv(
    "CIPHER_MEMORY_URL", "http://localhost:8096"
)
PRESIGN_URL = os.getenv("PRESIGN_URL", "http://localhost:8088")
PRESIGN_SECRET = os.getenv("PRESIGN_SHARED_SECRET", "")


def _post_json(url: str, payload: dict, timeout: int = 10) -> dict | None:
    """POST JSON and return decoded response, or *None* on failure."""
    try:
        req = Request(
            url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except (URLError, OSError, json.JSONDecodeError):
        return None


def store_reasoning(
    sweep_type: str,
    model_path: str,
    best: dict,
    csv_path: str,
    gpu_type: str | None = None,
) -> dict | None:
    """Store the best sweep configuration as a Cipher Memory reasoning pattern.

    Returns the API response dict on success, *None* on failure.
    """
    best_config = {k: v for k, v in best.items() if k != "throughput"}
    content = (
        f"Model {os.path.basename(model_path)} achieves "
        f"{best.get('throughput', 0):.1f} tok/s at "
        + ", ".join(f"{k}={v}" for k, v in best_config.items())
    )

    payload: dict[str, Any] = {
        "type": "reasoning",
        "domain": "llama_inference_optimization",
        "content": content,
        "metadata": {
            "model": model_path,
            "best_throughput_tps": best.get("throughput", 0),
            "best_config": best_config,
            "sweep_type": sweep_type,
            "csv_path": csv_path,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    }
    if gpu_type:
        payload["metadata"]["gpu_type"] = gpu_type

    return _post_json(f"{CIPHER_MEMORY_URL}/api/memory", payload)


def archive_csv_to_minio(
    csv_path: str,
    bucket: str = "outputs",
    object_key: str | None = None,
) -> str | None:
    """Upload a CSV file to MinIO via the presign service.

    Returns the presigned download URL on success, *None* on failure.
    """
    if not PRESIGN_SECRET:
        return None

    if object_key is None:
        object_key = f"llama-throughput-lab/{os.path.basename(csv_path)}"

    try:
        from urllib.parse import urlencode, quote

        params = urlencode({
            "bucket": bucket,
            "key": object_key,
            "method": "PUT",
        })
        req = Request(
            f"{PRESIGN_URL}/presign?{params}",
            headers={
                "Authorization": f"Bearer {PRESIGN_SECRET}",
            },
            method="GET",
        )
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            upload_url = data.get("url")

        if not upload_url:
            return None

        with open(csv_path, "rb") as f:
            put_req = Request(
                upload_url,
                data=f.read(),
                headers={"Content-Type": "text/csv"},
                method="PUT",
            )
            urlopen(put_req, timeout=30)

        # Return a download presign
        params = urlencode({
            "bucket": bucket,
            "key": object_key,
            "method": "GET",
        })
        req = Request(
            f"{PRESIGN_URL}/presign?{params}",
            headers={
                "Authorization": f"Bearer {PRESIGN_SECRET}",
            },
            method="GET",
        )
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("url")
    except (URLError, OSError):
        return None
