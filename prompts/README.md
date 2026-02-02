# Prompts Directory

This directory contains prompt templates for working with Large Language Models (LLMs) in data extraction, normalization, and evaluation workflows. These prompts are designed to transform semi-structured narrative content into structured, queryable data.

---

## Directory Structure

```
prompts/
├── extraction/       # Prompts for extracting entities, events, and facts (placeholder)
├── normalization/    # Prompts for normalizing and standardizing data (placeholder)
└── evaluation/       # Prompts for evaluating data quality and consistency (placeholder)
```

---

## Status

🚧 **Under Development** — Prompt subdirectories are currently placeholders.

For production prompt templates, see:
- **[src/llm/prompts/](../src/llm/prompts/)** — Production prompt templates for the LLM module
- **[agents/templates/prompts/](../agents/templates/prompts/)** — Agent-specific prompt templates

---

## Planned Prompt Categories

### Extraction Prompts (`extraction/`)

Prompts for extracting structured data from unstructured or semi-structured sources:

**Entity Extraction:**
- `character_extraction.md` — Extract character attributes (name, species, homeworld, etc.)
- `planet_extraction.md` — Extract planetary data (climate, terrain, population, etc.)
- `event_extraction.md` — Extract events with temporal context
- `relationship_extraction.md` — Extract character relationships and affiliations

**Metadata Extraction:**
- `source_citation.md` — Extract proper source citations
- `date_parsing.md` — Parse and normalize dates (BBY/ABY, real-world)
- `claim_identification.md` — Identify claims vs. facts

**Content Classification:**
- `content_type.md` — Classify content (canon, legends, fan theory, etc.)
- `continuity_tag.md` — Tag content by continuity universe

### Normalization Prompts (`normalization/`)

Prompts for standardizing and cleaning extracted data:

**Name Standardization:**
- `character_name_normalization.md` — Normalize character name variants
- `location_name_normalization.md` — Standardize location names
- `species_name_normalization.md` — Normalize species names

**Data Enrichment:**
- `attribute_inference.md` — Infer missing attributes from context
- `relationship_inference.md` — Infer implicit relationships
- `date_estimation.md` — Estimate missing dates from context

**Deduplication:**
- `entity_matching.md` — Match duplicate entity references
- `conflict_detection.md` — Detect conflicting information
- `merge_strategy.md` — Suggest merge strategies for duplicates

### Evaluation Prompts (`evaluation/`)

Prompts for assessing data quality, completeness, and consistency:

**Quality Assessment:**
- `completeness_check.md` — Evaluate data completeness
- `consistency_check.md` — Check for logical inconsistencies
- `accuracy_assessment.md` — Assess accuracy against known facts
- `citation_validation.md` — Validate source citations

**Continuity Analysis:**
- `timeline_validation.md` — Check event chronology
- `contradiction_detection.md` — Find contradictory claims
- `continuity_drift.md` — Identify continuity inconsistencies

**Bias Detection:**
- `source_bias.md` — Detect source bias or POV
- `fan_theory_detection.md` — Distinguish canon from fan theories
- `speculation_detection.md` — Identify speculative vs. factual content

---

## Prompt Design Principles

When creating prompts for this project:

1. **Output Format First** — Specify the exact JSON schema or structured output format
2. **Evidence-Based** — Always require citations and evidence
3. **Uncertainty Handling** — Allow the model to express uncertainty
4. **No Hallucination** — Discourage making up information
5. **Separation of Concerns** — One prompt per task (extract, then normalize, then evaluate)
6. **Version Control** — Include prompt version in filename or header
7. **Examples Included** — Provide 2-3 examples of expected input/output

**Example Prompt Structure:**

```markdown
# Character Attribute Extraction

**Version:** 1.0  
**Model Tested:** llama3.2, mistral  
**Task:** Extract character attributes from narrative text

## Output Schema

```json
{
  "character_name": "string",
  "species": "string or null",
  "homeworld": "string or null",
  "affiliations": ["string"],
  "citations": ["string"]
}
```

## Instructions

Given narrative text about a character:

1. Extract the character's canonical name (most common form)
2. Identify species if mentioned
3. Identify homeworld if mentioned
4. List affiliations (organizations, groups, factions)
5. Provide exact quotes as citations for each extracted fact

**Important:**
- Only extract information explicitly stated in the text
- Use `null` for unknown attributes
- Include page numbers or section headers in citations
- Do not infer information not present in the text

## Examples

### Example 1

**Input:**
> Luke Skywalker was a human Jedi Knight from Tatooine who served the Rebel Alliance.

**Output:**
```json
{
  "character_name": "Luke Skywalker",
  "species": "human",
  "homeworld": "Tatooine",
  "affiliations": ["Jedi Order", "Rebel Alliance"],
  "citations": [
    "Luke Skywalker was a human",
    "Jedi Knight from Tatooine",
    "served the Rebel Alliance"
  ]
}
```

### Example 2

**Input:**
> Yoda was a Jedi Master who trained Luke Skywalker.

**Output:**
```json
{
  "character_name": "Yoda",
  "species": null,
  "homeworld": null,
  "affiliations": ["Jedi Order"],
  "citations": [
    "Yoda was a Jedi Master"
  ]
}
```

## Validation

After extraction:
- Verify all citations exist in input text
- Check species/homeworld against known entities
- Ensure no duplicate affiliations
```

---

## Relationship to LLM Module

The prompts in this directory are **reference templates** for experimentation. Production prompts live in:

- **`src/llm/prompts/`** — Production-ready prompts used by the LLM module
- **`src/llm/interrogations/`** — Interrogation templates for structured derive jobs

See [LLM Prompts README](../src/llm/prompts/README.md) for active prompt development.

---

## Prompt Versioning

All prompts should include version metadata:

```markdown
# Prompt Name

**Version:** 1.2  
**Created:** 2026-01-15  
**Last Updated:** 2026-02-01  
**Model Compatibility:** llama3.2, mistral, gpt-4  
**Status:** Production | Experimental | Deprecated  
```

---

## Testing Prompts

Before promoting a prompt to production:

1. **Manual Testing** — Test with 5-10 diverse examples
2. **Model Comparison** — Test with multiple models (llama, mistral, etc.)
3. **Edge Cases** — Test with ambiguous, incomplete, or conflicting input
4. **Output Validation** — Ensure outputs conform to schema
5. **Bias Check** — Look for systematic bias in outputs
6. **Citation Validation** — Verify citations are accurate

Use `scripts/llm_smoke_test.py` for basic connectivity testing.

---

## Related Documentation

- [LLM Module README](../src/llm/README.md) — LLM module overview
- [LLM Prompts README](../src/llm/prompts/README.md) — Production prompt guidelines
- [Interrogations README](../src/llm/interrogations/README.md) — Interrogation catalog
- [Agent Extraction Template](../agents/templates/prompts/extraction_template.md) — Agent-specific prompts
- [LLM Vision and Roadmap](../docs/llm/vision-and-roadmap.md) — LLM subsystem goals

---

## Contributing

To contribute a prompt:

1. Choose the appropriate subdirectory (`extraction/`, `normalization/`, `evaluation/`)
2. Follow the prompt design principles above
3. Include version metadata, instructions, and examples
4. Test with at least two different models
5. Document model compatibility and limitations
6. Add an entry to this README

---

## Best Practices

- **Be Specific** — Vague prompts produce inconsistent results
- **Show, Don't Tell** — Examples are more effective than descriptions
- **Constrain Output** — Use strict schemas to enforce structure
- **Handle Edge Cases** — Test with incomplete or ambiguous data
- **Iterate Rapidly** — Prompt engineering is experimental; iterate quickly
- **Document Failures** — Note what doesn't work (model limitations, prompt issues)

---

## Future Enhancements

- [ ] Add prompt performance metrics (accuracy, consistency)
- [ ] Create prompt testing framework
- [ ] Add few-shot learning examples library
- [ ] Build prompt version comparison tool
- [ ] Create prompt optimization guide
- [ ] Add model-specific prompt variants

---

## Questions or Ideas?

Open an issue to suggest new prompts or improvements to existing templates.
