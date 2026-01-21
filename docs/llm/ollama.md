# Ollama Integration Guide

## Overview

[Ollama](https://ollama.ai) is the primary LLM provider for the LLM-Derived Data subsystem. This document covers API usage, configuration, and operational considerations.

## Why Ollama?

- **Local-first**: Run models on local hardware, no cloud dependency
- **Easy setup**: Single binary, simple model management
- **Model variety**: Access to Llama, Mistral, CodeLlama, and many others
- **OpenAI compatibility**: Drop-in replacement for OpenAI API clients

## Installation

### macOS/Linux

```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### Windows

Download from [ollama.ai/download](https://ollama.ai/download).

### Docker

```bash
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
```

## Pulling Models

Before using a model, pull it:

```bash
ollama pull llama3.2
ollama pull mistral
ollama pull codellama
```

List available models:

```bash
ollama list
```

## API Endpoints

Ollama provides two API patterns:

### Native Ollama API

**Base URL**: `http://localhost:11434/api`

#### POST /api/generate

Generate text from a prompt (non-chat).

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "What is 2+2?",
  "stream": false
}'
```

**Response**:
```json
{
  "model": "llama3.2",
  "response": "2+2 equals 4.",
  "done": true,
  "prompt_eval_count": 15,
  "eval_count": 8
}
```

#### POST /api/chat

Multi-turn chat with message history.

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "llama3.2",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is 2+2?"}
  ],
  "stream": false
}'
```

**Response**:
```json
{
  "model": "llama3.2",
  "message": {
    "role": "assistant",
    "content": "2+2 equals 4."
  },
  "done": true,
  "prompt_eval_count": 25,
  "eval_count": 8
}
```

### OpenAI-Compatible API

**Base URL**: `http://localhost:11434/v1`

#### POST /v1/chat/completions

OpenAI-compatible chat completions endpoint.

```bash
curl http://localhost:11434/v1/chat/completions -d '{
  "model": "llama3.2",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is 2+2?"}
  ]
}'
```

**Response**:
```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "model": "llama3.2",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "2+2 equals 4."
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 8,
    "total_tokens": 33
  }
}
```

#### POST /v1/responses

Non-stateful response generation (simpler than chat).

```bash
curl http://localhost:11434/v1/responses -d '{
  "model": "llama3.2",
  "input": "What is 2+2?"
}'
```

## API Selection (TBD)

The choice between native and OpenAI-compatible APIs has not been finalized:

| Aspect | Native API | OpenAI-Compatible |
|--------|------------|-------------------|
| Portability | Ollama-specific | Works with any OpenAI client |
| Features | Full Ollama features | Subset of features |
| Token usage | `prompt_eval_count`/`eval_count` | `usage` object |
| Recommendation | Better for Ollama-specific features | Better for provider-agnostic code |

Current implementation supports both; configuration determines which is used.

## Configuration Options

### Base URL

Default: `http://localhost:11434`

Override with environment variable:
```bash
export LLM_BASE_URL="http://192.168.1.100:11434"
```

Or in `config/llm.yaml`:
```yaml
llm:
  base_url: "http://192.168.1.100:11434"
```

### Model Name

Specify model with optional tag:
```yaml
llm:
  model: "llama3.2"      # Latest version
  model: "llama3.2:7b"   # Specific size
  model: "llama3.2:q4_0" # Specific quantization
```

### Streaming

Default: `false` (recommended for deterministic capture)

Streaming returns tokens as they're generated. For reproducibility and artifact storage, non-streaming is preferred.

```yaml
llm:
  stream: false
```

### Timeouts and Retries

```yaml
llm:
  timeout: 120          # Request timeout in seconds
```

Retry logic is handled at the runner level, not the provider level.

### Temperature

Controls randomness. For reproducible extractions, use `0.0`:

```yaml
llm:
  temperature: 0.0  # Deterministic
  temperature: 0.7  # More creative (not recommended for extraction)
```

## Operational Behavior

### Default Bind Address and Port

Ollama binds to `127.0.0.1:11434` by default.

To change, set `OLLAMA_HOST` before starting:

```bash
# Bind to all interfaces on port 11434
export OLLAMA_HOST="0.0.0.0:11434"
ollama serve

# Bind to specific IP and different port
export OLLAMA_HOST="192.168.1.100:8080"
ollama serve
```

### Running as a Service

#### systemd (Linux)

```bash
sudo systemctl enable ollama
sudo systemctl start ollama
```

#### Docker Compose

```yaml
services:
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
```

### GPU Acceleration

Ollama automatically detects and uses:
- NVIDIA GPUs (CUDA)
- Apple Silicon (Metal)
- AMD GPUs (ROCm, experimental)

Check GPU usage:
```bash
ollama ps  # Shows running models and GPU memory
```

### Model Memory Management

Ollama keeps models in memory for fast inference. To unload:

```bash
ollama stop llama3.2
```

## Health Checks

### Check if Ollama is Running

```bash
curl http://localhost:11434/api/tags
```

Returns list of available models if healthy.

### Programmatic Health Check

```python
from src.llm.providers import OllamaClient
from src.llm.core.types import LLMConfig

config = LLMConfig(provider="ollama", model="llama3.2")
client = OllamaClient(config)

if client.health_check():
    print("Ollama is healthy and model is available")
else:
    print("Ollama is not reachable or model not found")
```

## Troubleshooting

### "Connection refused"

- Check if Ollama is running: `ollama serve`
- Check port: `netstat -an | grep 11434`
- Check firewall settings

### "Model not found"

- Pull the model: `ollama pull llama3.2`
- Check model name spelling
- List available models: `ollama list`

### Slow Responses

- Check if GPU is being used: `ollama ps`
- Consider smaller model or quantization
- Increase system RAM/VRAM

### Out of Memory

- Use smaller model: `llama3.2:7b` instead of `llama3.2:70b`
- Use quantized model: `llama3.2:q4_0`
- Close other GPU-intensive applications

## Related Documentation

- [LLM-Derived Data Overview](derived-data.md)
- [Configuration Reference](../../src/llm/config/config.md)
- [Ollama Official Docs](https://ollama.ai/docs)
