# Ollama in Docker

This document explains how to run Ollama as a Docker Compose service for the LLM-Derived Data subsystem in this repository.

## Overview

### What Ollama Does in This Repo

Ollama is the **local LLM runtime** for the LLM-Derived Data subsystem. It:

- Provides a REST API for generating structured JSON from evidence bundles
- Runs inside Docker for repeatability, portability, and isolation
- Persists downloaded models in a Docker volume to avoid re-downloading

Running Ollama in Docker means:
- Consistent behavior across Windows, macOS, and Linux hosts
- No need to install Ollama on your host machine
- Easy migration to cloud or server environments later
- Clear separation of concerns in the Compose stack

### Docker-First Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Docker Compose Stack                            │
├──────────────────┬────────────────────┬────────────────────────────┤
│    sqlserver     │       ollama       │      (future runner)       │
│                  │                    │                            │
│  SQL Server 2022 │  Local LLM API     │  Python derive jobs        │
│  Port: 1433      │  Port: 11434       │  Calls ollama:11434        │
│  Volume: mssql_data │ Volume: ollama_data │                        │
└──────────────────┴────────────────────┴────────────────────────────┘
                           │
            Compose default network (bridge)
```

---

## Prerequisites

### Windows Host Setup

This guide assumes a **Windows host** with the following:

1. **Docker Desktop** installed and running
   - Download: [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
   
2. **WSL2 backend enabled**
   - Docker Desktop → Settings → General → "Use WSL 2 based engine" ✓
   - If not enabled, Docker Desktop will prompt you to install WSL2

3. **Sufficient resources**
   - Allocate at least 8GB RAM to Docker (Settings → Resources → Memory)
   - LLM inference is memory-intensive; 16GB+ recommended for larger models

### GPU Support (Optional)

GPU acceleration is **optional** but significantly improves inference speed.

#### Requirements for GPU Support

- NVIDIA GPU with CUDA support
- NVIDIA drivers installed on Windows host
- Docker Desktop configured for GPU passthrough (WSL2 backend required)

#### Verify GPU Passthrough

Run this command to test if GPU passthrough is working:

```bash
docker run --rm -it --gpus=all nvcr.io/nvidia/k8s/cuda-sample:nbody nbody -gpu -benchmark
```

**If this succeeds**: You'll see GPU benchmark output with frame rates.

**If this fails**: GPU passthrough is not available. Ollama will still work using CPU inference.

Common reasons for failure:
- NVIDIA drivers not installed or outdated
- WSL2 not properly configured
- Docker Desktop not using WSL2 backend
- GPU not CUDA-capable

**Note**: GPU support is not required. Ollama works well with CPU-only inference for smaller models (7B parameters or less).

---

## Starting Ollama

### Start Only Ollama

```bash
docker compose up -d ollama
```

This starts Ollama in detached mode. The service will:
- Pull the `ollama/ollama:latest` image if not present
- Create the `ollama_data` volume for model persistence
- Start the Ollama API on port 11434

### Start the Full Stack

```bash
docker compose up -d
```

This starts all services: SQL Server, Ollama, and any other services defined in the Compose file.

### View Logs

```bash
# Follow Ollama logs
docker compose logs -f ollama

# View last 100 lines
docker compose logs --tail=100 ollama
```

### Stop Ollama

```bash
# Stop but keep volume (models remain)
docker compose down

# Stop and delete volume (models will need to be re-downloaded)
docker compose down -v
```

---

## Model Management

### Pulling Models

Models must be pulled before use. Run commands inside the container:

```bash
# Pull a model
docker exec -it holocron-ollama ollama pull llama3.2

# Pull a specific size/quantization
docker exec -it holocron-ollama ollama pull llama3.2:7b
docker exec -it holocron-ollama ollama pull mistral:7b-instruct-q4_0
```

Recommended starting models:
- `llama3.2` - Good general-purpose model (default)
- `mistral` - Fast and capable
- `codellama` - Optimized for code tasks

### Listing Models

```bash
# Via CLI
docker exec -it holocron-ollama ollama list

# Via API
curl http://localhost:11434/api/tags
```

### Running Interactive Chat

For testing:

```bash
docker exec -it holocron-ollama ollama run llama3.2
```

Type your prompts and press Enter. Type `/bye` to exit.

### Checking Model Details

```bash
docker exec -it holocron-ollama ollama show llama3.2
```

---

## Model Persistence

### How It Works

Models are stored in `/root/.ollama` inside the container. This directory is mounted to a **named Docker volume** (`ollama_data`).

Benefits:
- Models survive container restarts
- Models survive `docker compose down` (without `-v`)
- Models survive image updates (`docker compose pull ollama`)

### Volume Location

Docker manages the volume location. To inspect:

```bash
docker volume inspect holocron-analytics_ollama_data
```

### Clearing Models

To delete all downloaded models:

```bash
docker compose down
docker volume rm holocron-analytics_ollama_data
docker compose up -d ollama
```

---

## Networking Conventions

Ollama is accessible via different URLs depending on where the client is running:

### From Host Machine (Manual Testing)

Use `localhost`:

```bash
# Health check
curl http://localhost:11434/api/tags

# Generate text
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "What is 2+2?",
  "stream": false
}'
```

### From Other Containers (Same Compose Network)

Use the service name `ollama`:

```python
# Python code running in another container
base_url = "http://ollama:11434"
```

This works because all services in the same Compose file share a default bridge network. The service name resolves to the container's IP.

### Environment Variable Convention

| Variable | Use Case | Value |
|----------|----------|-------|
| `OLLAMA_BASE_URL` | Container-to-container | `http://ollama:11434` |
| `OLLAMA_HOST_BASE_URL` | Host-based testing | `http://localhost:11434` |

---

## Security Posture

### Default: Localhost Only

The Compose file binds Ollama to `127.0.0.1:11434`:

```yaml
ports:
  - "127.0.0.1:11434:11434"
```

This means:
- ✓ Accessible from your Windows host via `localhost`
- ✓ Accessible from other containers via `ollama:11434`
- ✗ NOT accessible from other machines on your LAN
- ✗ NOT accessible from the internet

### Broader Exposure (Not Recommended)

If you need LAN access (e.g., for remote testing), you can bind to all interfaces:

```yaml
ports:
  - "11434:11434"  # WARNING: Exposes to LAN
```

**Security implications:**
- Anyone on your network can call the Ollama API
- No authentication or authorization by default
- Consider firewall rules if you do this

### Container-to-Container Security

Traffic between containers stays within the Docker network and does not traverse your host's network stack.

---

## GPU Configuration

GPU support is **commented out by default** in the Compose file. This ensures the stack works on machines without NVIDIA GPUs.

### Enabling GPU Support

If you have verified GPU passthrough works (see Prerequisites), edit `docker-compose.yml`:

```yaml
ollama:
  image: ollama/ollama:latest
  container_name: holocron-ollama
  ports:
    - "127.0.0.1:11434:11434"
  volumes:
    - ollama_data:/root/.ollama
  restart: unless-stopped
  # Uncomment below for GPU support:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: all
            capabilities: [gpu]
```

### Verifying GPU Usage

After enabling GPU support:

```bash
# Check if Ollama sees the GPU
docker exec -it holocron-ollama nvidia-smi

# Check GPU usage while running inference
docker exec -it holocron-ollama ollama run llama3.2
# (In another terminal)
docker exec -it holocron-ollama nvidia-smi
```

---

## Operational Commands Reference

| Task | Command |
|------|---------|
| Start Ollama | `docker compose up -d ollama` |
| Stop Ollama | `docker compose stop ollama` |
| View logs | `docker compose logs -f ollama` |
| Pull model | `docker exec -it holocron-ollama ollama pull <model>` |
| List models | `docker exec -it holocron-ollama ollama list` |
| Run interactive | `docker exec -it holocron-ollama ollama run <model>` |
| Check API | `curl http://localhost:11434/api/tags` |
| Show model info | `docker exec -it holocron-ollama ollama show <model>` |
| Stop model | `docker exec -it holocron-ollama ollama stop <model>` |

---

## Troubleshooting

### "Connection refused" from Host

1. Check if Ollama is running: `docker compose ps`
2. Check logs for errors: `docker compose logs ollama`
3. Verify port binding: `docker compose port ollama 11434`

### "Connection refused" from Another Container

1. Use `http://ollama:11434`, not `localhost`
2. Ensure both containers are in the same Compose stack
3. Check network: `docker network ls` and `docker network inspect`

### Model Download Slow or Fails

1. Check internet connectivity
2. Try a smaller model first: `ollama pull tinyllama`
3. Check available disk space in Docker

### Out of Memory

1. Use a smaller model (e.g., `llama3.2:7b-q4_0`)
2. Increase Docker memory allocation (Settings → Resources)
3. Stop other containers to free resources

### GPU Not Detected

1. Verify GPU passthrough: `docker run --rm -it --gpus=all nvidia/cuda:12.0-base nvidia-smi`
2. Update NVIDIA drivers
3. Restart Docker Desktop

---

## Related Documentation

- [Ollama Integration Guide](ollama.md) - API documentation and configuration
- [LLM-Derived Data Overview](derived-data.md) - Subsystem concepts
- [Configuration Reference](../../src/llm/config/config.md) - Environment variables
- [Docker Local Dev Runbook](../runbooks/docker_local_dev.md) - General Docker setup
