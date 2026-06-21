# LLM Prompts

## Overview

This directory contains **prompt templates** for LLM interrogation. Prompts are organized by "interrogation prompt families" — groups of related prompts that share a common purpose and output structure.

## Prompt Modules

### `page_classification.py` *(NEW)*

Standardized prompts for Wikipedia/Wookieepedia page classification. Provides:

- `PROMPT_VERSION` — Version identifier for tracking (`v3_contract`)
- `SYSTEM_PROMPT` — Role definition and output rules for the classifier
- `build_messages()` — Build complete message list for LLM call
- `build_user_message()` — Build the user message with clean input envelope

**Key features:**
- Model-agnostic design (works with any Ollama model)
- Clean input envelope (title, namespace, continuity_hint, excerpt_text)
- Strict JSON output enforcement
- Confidence calibration guidance
- Structured notes field for subtype handling
- Noise handling instructions

**Usage:**
```python
from llm.prompts.page_classification import build_messages, PROMPT_VERSION

messages = build_messages(
    title="Luke Skywalker",
    namespace="Main",
    continuity_hint="Canon",
    excerpt_text="Luke Skywalker was a legendary Jedi Master...",
)
# Pass to OllamaClient.chat_with_structured_output()
```

## Prompt Philosophy

### JSON-Contract-First Prompting

All prompts in this system follow a **JSON-contract-first** approach:

1. **Define the output schema first** — Before writing a prompt, define the expected JSON output structure in `contracts/`
2. **Include schema in prompt** — The prompt explicitly describes the expected JSON structure
3. **Fail-closed validation** — If the LLM output doesn't match the schema, the operation fails (no partial data accepted)
4. **Nulls with reasons** — If a field cannot be extracted, the LLM should return `null` with an explanation, not guess

### Example Prompt Structure

```text
You are an extraction assistant. Given the following evidence, extract structured data according to the schema below.

## Evidence
{evidence_content}

## Output Schema
{
  "entity_name": "string (required)",
  "entity_type": "string (required, one of: person, place, organization, other)",
  "description": "string or null",
  "confidence": "string (one of: high, medium, low)"
}

## Instructions
- Extract ONLY from the provided evidence
- If a field cannot be determined from evidence, use null
- Do not hallucinate or infer beyond what is explicitly stated
- Return ONLY valid JSON, no additional text

## Response
```

## Directory Structure

```
prompts/
├── README.md           # This file
└── templates/          # Prompt template files
    └── .gitkeep        # Placeholder (add templates here)
```

## Template Format

Templates use simple variable substitution with `{variable_name}` placeholders. Future implementations may support more advanced templating (Jinja2, etc.).

### Variables

Common template variables:
- `{evidence_content}` — The assembled evidence text
- `{output_schema}` — JSON schema for expected output
- `{task_instructions}` — Task-specific instructions
- `{examples}` — Few-shot examples (if applicable)

## Interrogation Prompt Families

### Planned Families (TBD)

1. **Entity Extraction** — Extract named entities with attributes
2. **Relationship Extraction** — Extract relationships between entities
3. **Summarization** — Summarize evidence into structured summaries
4. **Classification** — Classify documents or content
5. **Q&A Extraction** — Answer specific questions from evidence

## Best Practices

### DO

- Include explicit JSON schema in the prompt
- Provide examples when possible (few-shot prompting)
- Instruct the model to only use provided evidence
- Request confidence levels for extracted data
- Ask for null-with-reason when data is missing

### DON'T

- Allow open-ended responses
- Trust the model to infer schema from context
- Accept partial or malformed JSON
- Allow the model to cite sources outside the evidence bundle

## Related Documentation

- [Contracts README](../contracts/README.md) — JSON schemas for outputs
- [LLM-Derived Data Overview](../../../docs/llm/derived-data.md)
- [Extraction Template Example](../../../agents/templates/prompts/extraction_template.md)
