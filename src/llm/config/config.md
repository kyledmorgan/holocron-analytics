# LLM Configuration Reference

## Overview

Configuration for the LLM-Derived Data module follows patterns established in the repository (see `config/ingest.example.yaml`).

## Configuration File

The primary configuration file is `config/llm.yaml` (copy from `llm.example.yaml` in this directory or the repo `config/` folder).

## Configuration Sections

### LLM Provider Settings

```yaml
llm:
  # Provider name (currently only 'ollama' supported)
  provider: "ollama"
  
  # Model identifier
  model: "llama3.2"
  
  # Base URL for the provider API
  # See "Networking Conventions" section below for host vs container URLs
  base_url: "http://ollama:11434"
  
  # Sampling temperature (0.0 = deterministic, higher = more random)
  temperature: 0.0
  
  # Maximum tokens in response (null = model default)
  max_tokens: null
  
  # Request timeout in seconds
  timeout: 120
  
  # Whether to use streaming responses (false recommended for reproducibility)
  stream: false
  
  # API mode: "native" (Ollama API) or "openai" (OpenAI-compatible)
  api_mode: "native"
```

### Storage Settings

```yaml
storage:
  # Artifact lake (filesystem storage)
  artifact_lake:
    enabled: true
    base_dir: "local/llm_artifacts"
    pretty_print: true
  
  # SQL Server queue (optional)
  sql_server:
    enabled: false
    # Connection from environment: LLM_SQLSERVER_CONN_STR
    schema: "llm"
```

### Queue Settings

```yaml
queue:
  # Maximum concurrent jobs
  max_workers: 1
  
  # Retry settings
  max_retries: 3
  retry_delay_seconds: 60
  
  # Job timeout
  job_timeout_seconds: 300
```

### Evidence Settings

```yaml
evidence:
  # Maximum size of evidence bundle (characters)
  max_bundle_size: 50000
  
  # Hash algorithm for integrity verification
  hash_algorithm: "sha256"
```

## Environment Variables

Configuration values can be overridden with environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | LLM provider name | `ollama` |
| `LLM_MODEL` | Model identifier | `llama3.2` |
| `LLM_BASE_URL` | Provider API base URL | `http://ollama:11434` |
| `LLM_TEMPERATURE` | Sampling temperature | `0.0` |
| `LLM_TIMEOUT` | Request timeout (seconds) | `120` |
| `LLM_ARTIFACT_DIR` | Artifact storage directory | `local/llm_artifacts` |
| `LLM_SQLSERVER_CONN_STR` | SQL Server connection string | (none) |

### Ollama-Specific Variables

These are defined in `.env.example` for Ollama configuration:

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_BASE_URL` | Ollama API URL (container-to-container) | `http://ollama:11434` |
| `OLLAMA_HOST_BASE_URL` | Ollama API URL (host-based testing) | `http://localhost:11434` |
| `OLLAMA_MODEL` | Default model | `llama3.2` |
| `OLLAMA_TIMEOUT_SECONDS` | Request timeout | `120` |
| `OLLAMA_STREAM` | Enable streaming | `false` |

## Networking Conventions

Ollama runs as a Docker Compose service. The correct base URL depends on where your code is running:

### From Another Container (Default)

When running code inside a container that's part of the same Compose stack (e.g., a future derive runner):

```yaml
base_url: "http://ollama:11434"
```

The service name `ollama` resolves to the container's IP within the Docker network.

### From Host Machine

When running Python scripts directly on your Windows host (e.g., during development):

```yaml
base_url: "http://localhost:11434"
```

Or use the `OLLAMA_HOST_BASE_URL` environment variable.

### Environment Variable Override

For flexibility, set `LLM_BASE_URL` to switch between environments:

```bash
# Host-based testing
export LLM_BASE_URL="http://localhost:11434"
python scripts/llm_smoke_test.py

# Container-based (in Compose)
export LLM_BASE_URL="http://ollama:11434"
```

## Configuration Loading

Configuration is loaded in priority order:
1. Environment variables (highest priority)
2. YAML configuration file
3. Default values (lowest priority)

## TBD Items

The following configuration areas are planned but not finalized:

- **JSON Validation Library**: Which library to use for schema validation
- **Vector Store Settings**: For future embedding/RAG features
- **Multi-Model Benchmarking**: Configuration for comparing models

## Related Documentation

- [Ollama Integration Guide](../../../docs/llm/ollama.md) — Provider-specific settings
- [Ollama in Docker](../../../docs/llm/ollama-docker.md) — Docker Compose setup and networking
- [LLM Module README](../README.md) — Module overview
