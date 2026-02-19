FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/POWERFULMOVES/PMOVES.AI"
LABEL org.opencontainers.image.description="PMOVES llama.cpp throughput benchmarking toolkit"

RUN apt-get update && \
    apt-get install -y --no-install-recommends nginx curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (stdlib-only core; optional NATS/metrics)
COPY requirements-platform.txt ./
RUN pip install --no-cache-dir -r requirements-platform.txt

# Copy project files
COPY scripts/ ./scripts/
COPY tests/ ./tests/
COPY pmoves_nats_bridge.py pmoves_chit_bridge.py pmoves_metrics.py ./
COPY start_llama_rr.sh ./

# Results volume mount point
RUN mkdir -p /results

ENV LLAMA_RESULTS_DIR=/results \
    LLAMA_SERVER_HOST=127.0.0.1 \
    PYTHONUNBUFFERED=1

EXPOSE 8201

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -sf http://localhost:8201/healthz || exit 1

# Default: start metrics server and wait for commands
CMD ["python", "pmoves_metrics.py"]
