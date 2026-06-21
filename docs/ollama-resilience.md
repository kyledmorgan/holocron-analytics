# Ollama JSON Parsing Resilience

## Overview

The Holocron Analytics runner has been enhanced with resilient JSON parsing for Ollama responses. The runner now gracefully handles invalid JSON from LLM responses instead of crashing the entire job batch.

## Features

### 1. Retry Logic with Exponential Backoff
- **Max Attempts**: 3 retries per Ollama call
- **Backoff Strategy**: 250ms → 500ms → 1s (exponential with jitter)
- **Jitter**: ±25% random variation to avoid thundering herd

### 2. Multiple Parsing Strategies
The runner attempts multiple JSON parsing strategies in sequence:

1. **Direct parsing**: Standard `json.loads()`
2. **Whitespace stripping**: Remove leading/trailing whitespace
3. **Embedded JSON extraction**: Extract first `{...}` block from text (conservative)

### 3. Error Artifacts
When all retries are exhausted, the runner writes comprehensive error artifacts:

#### Invalid JSON Response (`invalid_json_response.txt`)
Raw text response from Ollama for troubleshooting

#### Error Manifest (`error_manifest.json`)
```json
{
  "job_id": "abc-123",
  "run_id": "run-456",
  "error_type": "invalid_json",
  "attempts": 3,
  "error_history": [
    "Attempt 1: Expecting value: line 1 column 1 (char 0)",
    "Attempt 2: Expecting value: line 1 column 1 (char 0)",
    "Attempt 3: Expecting value: line 1 column 1 (char 0)"
  ],
  "final_error": "LLM returned invalid JSON after all parsing strategies",
  "raw_content_preview": "First 500 chars of response...",
  "decision": "skipped_after_max_retries"
}
```

### 4. Resilient Runner Behavior
- **No crashes**: Runner continues processing next job after invalid JSON
- **Job status**: Failed jobs marked with `status="FAILED"` and descriptive error
- **Artifact preservation**: All artifacts (request, response, evidence) written even on failure

## Usage

### Phase 1 Runner

The Phase1Runner automatically includes retry logic:

```python
from llm.runners.phase1_runner import Phase1Runner, RunnerConfig

config = RunnerConfig.from_env()
runner = Phase1Runner(config)

# Runner will retry on invalid JSON
runner.run_loop()  # Continuous processing
# or
runner.run_once()  # Single job
```

### Dry Run Script

The dry run script also includes retry logic:

```bash
python -m src.sem_staging.dry_run_page_classification \
    --title "Luke Skywalker" \
    --dump-ollama
```

If Ollama returns invalid JSON:
- Script will retry up to 3 times
- Error artifacts written to `logs/ollama/`
- Script exits with code 1 (but doesn't crash)

## Configuration

Retry behavior can be configured via `RetryConfig`:

```python
from llm.utils.retry import RetryConfig

config = RetryConfig(
    max_attempts=3,          # Number of attempts (including first)
    initial_delay_ms=250.0,  # Initial delay
    max_delay_ms=1000.0,     # Maximum delay
    backoff_multiplier=2.0,  # Exponential multiplier
    jitter=True,             # Add random jitter
)
```

## Exception Hierarchy

```
Exception
└── LLMError
    ├── LLMProviderError (connection issues)
    └── LLMValidationError
        └── InvalidOllamaJsonError (JSON parsing failures)
```

Use `InvalidOllamaJsonError` to specifically catch and track JSON parsing failures:

```python
from llm.core.exceptions import InvalidOllamaJsonError

try:
    response = client.chat_with_structured_output(messages, schema)
    parsed = json.loads(response.content)
except InvalidOllamaJsonError as e:
    print(f"JSON parsing failed after {e.attempt} attempts")
    print(f"Raw content preview: {e.raw_content[:200]}")
```

## Troubleshooting

### Finding Error Artifacts

Error artifacts are written to the lake under the run directory:

```
lake/llm_runs/{yyyy}/{mm}/{dd}/{run_id}/
├── request.json              # Original request
├── response.json             # Ollama's raw response
├── invalid_json_response.txt # Raw text when JSON invalid
└── error_manifest.json       # Error details
```

For dry run script:
```
logs/ollama/
├── {timestamp}_{title}_invalid.txt  # Raw response
└── {timestamp}_{title}_error.json   # Error manifest
```

### Common Scenarios

#### Scenario 1: Transient LLM issues
- **Symptom**: Occasional invalid JSON
- **Resolution**: Retry succeeds on 2nd or 3rd attempt
- **Action**: Monitor retry frequency; may indicate model issues

#### Scenario 2: Systematic formatting issues
- **Symptom**: All retries fail consistently
- **Resolution**: Check error manifests for patterns
- **Action**: May need prompt engineering or schema adjustments

#### Scenario 3: Model instability
- **Symptom**: High retry rate across all jobs
- **Resolution**: Check Ollama service health
- **Action**: Consider model reload or temperature adjustments

## Testing

### Unit Tests

```bash
# Test retry logic
pytest tests/unit/llm/test_retry.py -v

# Test Phase1Runner resilience
pytest tests/unit/llm/test_phase1_runner_resilience.py -v

# All LLM tests
pytest tests/unit/llm/ -v
```

### Integration Testing

To test resilience with a real Ollama instance:

1. Start Ollama with an unstable model
2. Run Phase1Runner or dry run script
3. Verify error artifacts are created
4. Check that runner continues processing

## Performance Considerations

### Latency Impact
- **Best case** (success on first attempt): No additional latency
- **Typical** (1 retry): +250-500ms per job
- **Worst case** (3 retries): +1.5-2s per job

### Throughput
- Failed jobs release resources quickly
- Runner continues processing without restarts
- Overall throughput maintained for batch processing

## Future Enhancements

Potential improvements for consideration:

1. **Adaptive retry**: Adjust retry count based on success rate
2. **Circuit breaker**: Temporarily bypass retries if failure rate too high
3. **Model-specific strategies**: Different parsing approaches per model
4. **Streaming support**: Handle streaming responses with partial JSON
5. **Metrics collection**: Track retry rates and patterns over time

## References

- Exception definitions: `src/llm/core/exceptions.py`
- Retry utilities: `src/llm/utils/retry.py`
- Phase1Runner: `src/llm/runners/phase1_runner.py`
- Dry run script: `src/sem_staging/dry_run_page_classification.py`
