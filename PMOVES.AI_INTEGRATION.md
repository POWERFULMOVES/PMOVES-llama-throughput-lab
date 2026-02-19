# PMOVES.AI Integration Dossier

_Last updated: 2026-02-19_

## Module
- Name: PMOVES-llama-throughput-lab
- Path: PMOVES-llama-throughput-lab/

## Purpose in PMOVES.AI
- LLM inference throughput benchmarking and optimization toolkit.
- Runs multi-dimensional parameter sweeps (instances, parallel, batch, concurrency) against llama.cpp servers to find optimal inference configurations for each model/GPU combination.
- Role: **tooling** — produces optimization data consumed by agents and operators.

## PMOVES Overlay Surface
- pmoves-integrations/ overlay path (if used): N/A (standalone submodule)
- Compose/profile wiring: `benchmarks`, `gpu` profiles in `pmoves/docker-compose.yml`
- Env/secret inputs:
  - `NATS_URL` — NATS connection (optional, degrades gracefully)
  - `LLAMA_MODEL_PATH` — path to GGUF model inside `/models` volume
  - `LLAMA_MODELS_PATH` — host path mounted as `/models:ro`
  - `CIPHER_MEMORY_URL` — Cipher Memory API for reasoning storage (optional)
  - `PRESIGN_SHARED_SECRET` — MinIO presign for CSV archival (optional)
  - `GPU_ORCHESTRATOR_URL` — GPU orchestrator endpoint (optional)
- Auth/JWT requirements: None (internal tooling service)

## Contracts and Topics
- NATS subjects:
  - `llama.benchmark.started.v1` — sweep config, model, timestamp
  - `llama.benchmark.cell.v1` — per-row results (throughput_tps, tokens, errors)
  - `llama.benchmark.completed.v1` — sweep summary, best config, CSV path
- Supabase schema/tables touched: None (results stored via Cipher Memory + MinIO)
- MCP endpoints/skills: None (CLI/container tool, not an agent service)

## Boot Order and Health
- Bring-up dependency order: after NATS (optional), GPU orchestrator (optional)
- Health endpoints: `GET :8201/healthz` — `{"ok": true}`
- Smoke targets: `make -C pmoves llama-throughput-smoke`

## Hardening Notes
- Image pinning / provenance: Built from `python:3.12-slim`, no external model weights in image
- Secrets source: `PRESIGN_SHARED_SECRET` via env (not required for core operation)
- Network/security policy constraints:
  - Networks: `pmoves_api`, `pmoves_bus`, `pmoves_monitoring`
  - Model files mounted read-only (`/models:ro`)
  - Results written to named volume (`llama-results`)

## Source Documentation
- Upstream docs entrypoint: README.md
- PMOVES docs index reference: pmoves/docs/SUBMODULE_DOCS_DOSSIER.md

## Owner / Audit
- Owning lane: ai-lab (GPU workloads)
- Last integration audit run: 2026-02-19
