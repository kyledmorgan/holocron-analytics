# Ollama Smoke Tests - Bruno Collection

This Bruno collection provides an interactive smoke-test harness for local LLM APIs via Ollama running in Docker.

## Purpose

Manual interrogation harness for testing Ollama API endpoints one request at a time. This collection lets you:
- Verify connectivity to Ollama
- Test different models interactively
- Experiment with prompts and parameters
- Validate JSON contract responses
- Switch between local and Docker network addressing

This is **not** a batch runner—it's designed for hands-on exploration and validation.

---

## Prerequisites

### 1. Bruno Installed

Install Bruno from [https://www.usebruno.com/](https://www.usebruno.com/) or via package manager:

```bash
# macOS
brew install bruno

# Linux (snap)
snap install bruno

# Or download from GitHub releases
```

### 2. Ollama Running in Docker

Ollama must be running and accessible. Default setup assumes:
- Ollama container is running
- Port `11434` is exposed to the host
- API is reachable at `http://localhost:11434/api`

#### Basic Docker Run

```bash
docker run -d \
  --name ollama \
  -p 11434:11434 \
  -v ollama-data:/root/.ollama \
  ollama/ollama:latest
```

#### Docker Networking Gotchas

**Bind Address Issue:**
By default, Ollama binds to `127.0.0.1:11434` inside the container. For host-to-container communication via port mapping, this works fine. However, for container-to-container networking, you may need to set:

```bash
docker run -d \
  --name ollama \
  -p 11434:11434 \
  -e OLLAMA_HOST=0.0.0.0:11434 \
  -v ollama-data:/root/.ollama \
  ollama/ollama:latest
```

Or in `docker-compose.yml`:

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
    volumes:
      - ollama-data:/root/.ollama

volumes:
  ollama-data:
```

### 3. Pull a Model

Ensure at least one model is available:

```bash
# Pull a model (e.g., llama3.2)
docker exec -it ollama ollama pull llama3.2:latest

# Or use the Bruno collection request: "01 - Model Lifecycle / Pull model"
```

---

## Opening the Collection

### In Bruno UI

1. Open Bruno
2. Click **"Open Collection"**
3. Navigate to: `tools/bruno/ollama-smoke-tests/`
4. Bruno will load the collection

The collection structure:
```
ollama-smoke-tests/
├── bruno.json                           # Collection metadata
├── environments/
│   ├── local.bru                        # Host → Docker port mapping
│   └── docker-network.bru               # Container → container addressing
├── data/
│   └── movies.top10.json                # Sample movie prompts
├── 00 - Connectivity & Meta/
│   ├── Get version.bru
│   ├── List models (tags).bru
│   └── List running models.bru
├── 01 - Model Lifecycle/
│   ├── Show model details.bru
│   └── Pull model.bru
├── 02 - Generate/
│   ├── Generate - plain text.bru
│   └── Generate - JSON contract (strict).bru
├── 03 - Chat/
│   ├── Chat - minimal.bru
│   └── Chat - system + user + contract JSON.bru
├── 04 - OpenAI Compatibility/
│   └── OpenAI-compatible chat completions.bru
└── README.md                            # This file
```

---

## Selecting an Environment

Bruno environments let you switch between different configurations without changing request definitions.

### Available Environments

1. **`local`** (default)
   - `OLLAMA_URL`: `http://localhost:11434`
   - Use when running Bruno on the host machine

2. **`docker-network`**
   - `OLLAMA_URL`: `http://ollama:11434`
   - Use when running Bruno from inside a Docker network with Ollama

### How to Switch Environments

1. In Bruno, look for the **Environment dropdown** (usually top-right)
2. Select `local` or `docker-network`
3. All requests will use the selected environment's variables

---

## Environment Variables

Both environments define these variables:

| Variable           | Default (local)         | Description                                      |
|--------------------|-------------------------|--------------------------------------------------|
| `OLLAMA_URL`       | `http://localhost:11434`| Base URL for Ollama                              |
| `OLLAMA_API_BASE`  | `{{OLLAMA_URL}}/api`    | API base path (computed from OLLAMA_URL)         |
| `MODEL`            | `llama3.2:latest`       | Model to use for generation/chat                 |
| `STREAM`           | `false`                 | Disable streaming (returns single JSON response) |
| `TEMPERATURE`      | `0.2`                   | Randomness (0.0-1.0); lower = more deterministic |
| `SEED`             | `42`                    | Seed for reproducibility                         |
| `PROMPT`           | `What is the capital...`| Default prompt text                              |
| `MOVIE_TITLE`      | `The Empire Strikes...` | Default movie for contract tests                 |

### Customizing Variables

You can override these per request or change them in the environment file:

1. **Edit environment file directly:**
   - `environments/local.bru` or `environments/docker-network.bru`

2. **Override in request:**
   - In Bruno's request view, you can set request-level variables

---

## Running Requests

### Basic Workflow

1. **Select environment** (e.g., `local`)
2. **Pick a request** from the sidebar
3. **Customize variables** if needed (e.g., change `MODEL` or `PROMPT`)
4. **Click "Send"**
5. **Review response** in the response pane
6. **Check Tests tab** to see if assertions passed

### Request Organization

Requests are grouped by functionality:

- **00 - Connectivity & Meta**: Verify Ollama is reachable and list models
- **01 - Model Lifecycle**: Inspect and download models
- **02 - Generate**: Single-prompt text and JSON generation
- **03 - Chat**: Multi-turn conversations
- **04 - OpenAI Compatibility**: OpenAI-compatible endpoint

### Recommended Testing Sequence

1. **Get version** → Verify connectivity
2. **List models (tags)** → Ensure at least one model is available
3. **Generate - plain text** → Test basic generation
4. **Chat - minimal** → Test chat endpoint
5. **Generate - JSON contract (strict)** → Test structured output
6. **Chat - system + user + contract JSON** → Test full contract

---

## Using Movie Data

The `data/movies.top10.json` file contains 10 movie prompts designed for narrative analysis testing.

Each entry includes:
- `movie_title`: The movie name
- `year`: Release year
- `seed_prompt`: A safe, paraphrase-focused prompt

### Using Movie Prompts in Requests

**Option 1: Update `MOVIE_TITLE` in environment**

Edit `environments/local.bru`:
```
MOVIE_TITLE: Inception
```

**Option 2: Override in request variables**

In Bruno, go to the request's **Vars** tab and set:
```
MOVIE_TITLE = Inception
```

**Option 3: Copy seed_prompt**

Copy the `seed_prompt` from `movies.top10.json` and paste it as the `PROMPT` variable.

---

## Testing JSON Contracts

Several requests test the model's ability to produce structured JSON:

- **Generate - JSON contract (strict)**
- **Chat - system + user + contract JSON**

These requests:
1. Instruct the model to output ONLY JSON (no markdown, no extra text)
2. Provide a schema to follow
3. Use Ollama's `"format": "json"` parameter to enforce JSON output
4. Include Bruno tests to validate the response structure

### Expected JSON Schema

```json
{
  "movie": { "title": "string", "year": number },
  "summary": "string (1-3 paragraphs, paraphrase only)",
  "key_events": [
    { "event_id": "E01", "event": "string", "act": number, "confidence": number }
  ],
  "scenes": [
    { "scene_id": "S01", "setting": "string", "beat": "string", "characters": ["string"], "confidence": number }
  ],
  "entities": {
    "characters": ["string"],
    "locations": ["string"],
    "objects": ["string"]
  },
  "open_questions": ["string"]
}
```

### Contract Design Principles

- **Use "unknown"** for uncertain fields (don't hallucinate)
- **Include confidence scores** (0.0 to 1.0) for data points
- **List open questions** instead of inventing details
- **Never reproduce copyrighted content** (dialogue, narration)

---

## Bruno Tests

Many requests include automated tests (in the `tests` block). After running a request:

1. Click the **Tests** tab in the response pane
2. Review which assertions passed/failed
3. Green checkmarks = passed
4. Red X = failed (with error message)

Example tests:
- Status code is 200
- Response contains expected fields
- JSON is valid and parseable
- Arrays are actually arrays
- Required keys are present

---

## OpenAI Compatibility

Ollama provides an OpenAI-compatible endpoint at `/v1/chat/completions`.

**Request:** `04 - OpenAI Compatibility / OpenAI-compatible chat completions`

This allows tools/libraries built for OpenAI to work with Ollama:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"  # required by client, but ignored by Ollama
)

response = client.chat.completions.create(
    model="llama3.2:latest",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

**Note:** The `api_key` is required by OpenAI client libraries but ignored by Ollama.

---

## Using bru CLI (Optional)

Bruno provides a CLI for running requests from the terminal.

### Install bru CLI

```bash
npm install -g @usebruno/cli
```

### Run a Request

```bash
cd tools/bruno/ollama-smoke-tests

# Run a single request
bru run "00 - Connectivity & Meta/Get version.bru" --env local

# Run all requests in a folder
bru run "00 - Connectivity & Meta" --env local

# Run entire collection
bru run . --env local
```

### CLI Output

- Shows request/response details
- Displays test results (pass/fail)
- Exit code 0 = all tests passed, non-zero = failures

---

## Troubleshooting

### "Connection refused" or "Network error"

**Problem:** Bruno can't reach Ollama at `http://localhost:11434`

**Solutions:**
1. Verify Ollama container is running:
   ```bash
   docker ps | grep ollama
   ```

2. Check port mapping:
   ```bash
   docker port ollama
   ```
   Should show: `11434/tcp -> 0.0.0.0:11434`

3. Test connectivity from host:
   ```bash
   curl http://localhost:11434/api/version
   ```

4. Check `OLLAMA_HOST` environment variable in container:
   ```bash
   docker exec ollama env | grep OLLAMA_HOST
   ```
   If accessing from other containers, set to `0.0.0.0:11434`

### "Model not found"

**Problem:** Request fails with model not found error

**Solutions:**
1. List available models:
   - Run `List models (tags)` request in Bruno
   - Or: `docker exec ollama ollama list`

2. Pull the model:
   - Run `01 - Model Lifecycle / Pull model` request
   - Or: `docker exec ollama ollama pull llama3.2:latest`

3. Update `MODEL` variable in environment to a model you have

### "Stream is not supported" or streaming issues

**Problem:** Responses are partial or Bruno hangs

**Solution:**
Ensure `STREAM` is set to `false` in your environment. Bruno is designed for non-streaming responses in this collection.

### JSON parsing errors in contract tests

**Problem:** Tests fail because response isn't valid JSON

**Possible causes:**
1. Model isn't following instructions (try a different model or adjust temperature)
2. Model is prefixing JSON with markdown (```json)
3. Using `"format": "json"` helps but isn't foolproof

**Solutions:**
- Use the chat endpoint with a strong system message
- Set `"format": "json"` in the request body
- Lower temperature (0.0-0.2) for more deterministic output
- Try a more capable model

### HTTPS/Reverse Proxy Setup

**Problem:** Ollama is behind a reverse proxy with HTTPS

**Solution:**
Only change the environment variable—don't modify requests:

Edit `environments/local.bru`:
```
OLLAMA_URL: https://ollama.yourdomain.com
```

All requests will automatically use HTTPS since they reference `{{OLLAMA_URL}}`.

---

## Next Steps

This collection is designed to evolve into a batch runner. Future enhancements may include:

- Automated test runs across all movie prompts
- Response logging and comparison
- Integration with Python/Node.js test harness
- JSON schema validation and diff tracking

---

## Additional Resources

- [Ollama API Documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Bruno Documentation](https://docs.usebruno.com/)
- [Ollama Docker Hub](https://hub.docker.com/r/ollama/ollama)

---

## License

This collection is part of the holocron-analytics repository. See the repository's LICENSE file for details.
