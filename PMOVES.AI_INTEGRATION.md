# PMOVES.AI Integration — llama-throughput-lab

## Service Description

llama-throughput-lab is a benchmarking tool for measuring LLM inference
throughput across different hardware configurations and model sizes.

## Port Bindings

No persistent service ports — this is a CLI/batch tool, not a long-running
service.

## Integration Points

- **TensorZero Gateway** (`http://tensorzero-gateway:3000`): Use as
  OpenAI-compatible endpoint for benchmarking routed models
- **Prometheus** (`http://prometheus:9090`): Query
  `tensorzero_request_duration_seconds` for latency baselines
- **NATS** (`nats://nats:pmoves@nats:4222`): Publish benchmark results to
  `mesh.gpu.benchmark.v1` (planned)
- **MinIO** (`http://minio:9000`): Store benchmark artifacts in `outputs`
  bucket

## Docker Image

Built from repo root:

```yaml
# pmoves/images.yaml
llama-throughput-lab:
  context: PMOVES-llama-throughput-lab
  dockerfile: Dockerfile
```

## Usage

```bash
# Run benchmark via Make target
make -C pmoves benchmark-llama MODEL=qwen3-coder-plus

# Direct execution
cd PMOVES-llama-throughput-lab
python run_llama_tests.py --model qwen3-coder-plus --provider tensorzero
```
