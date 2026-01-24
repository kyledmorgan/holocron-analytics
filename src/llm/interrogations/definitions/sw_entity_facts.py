"""
Star Wars Entity Facts Interrogation (sw_entity_facts_v1).

Extracts normalized facts about Star Wars entities from evidence snippets.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from ..registry import InterrogationDefinition
from ...contracts.phase1_contracts import validate_entity_facts_output


# System prompt for the interrogation
SYSTEM_PROMPT = """You are a precise data extraction assistant specializing in Star Wars universe information.

Your task is to extract structured facts from provided evidence about Star Wars entities.

Rules:
1. ONLY extract information explicitly stated in the provided evidence.
2. DO NOT hallucinate or infer information not present in the evidence.
3. If information is not found, set value to null and confidence to 0.
4. Always cite which evidence snippet supports each fact using evidence_ids.
5. Use confidence scores appropriately:
   - 1.0: Explicitly and clearly stated
   - 0.7-0.9: Strongly implied or stated with some ambiguity
   - 0.4-0.6: Weakly implied or conflicting information exists
   - 0.1-0.3: Very uncertain, barely mentioned
   - 0.0: Not found in evidence (value should be null)
6. Respond ONLY with valid JSON matching the required schema."""

# Prompt template with placeholders
PROMPT_TEMPLATE = """Extract facts about the following Star Wars entity from the provided evidence.

Entity Type: {entity_type}
Entity ID: {entity_id}

Evidence:
{evidence_content}

Extract the following types of facts if present in the evidence:
- name: The canonical name of the entity
- aliases: Alternative names or titles
- description: Brief description
- For characters: species, homeworld, birth_year, affiliations, notable_events
- For planets: region, climate, terrain, population, notable_inhabitants
- For starships: class, manufacturer, length, crew, passengers
- For organizations: type, founding_date, leaders, headquarters

Return a JSON object with:
- entity_type: "{entity_type}"
- entity_id: "{entity_id}"
- entity_name: The canonical name (or null if not found)
- facts: Array of extracted facts, each with:
  - fact_key: The type of fact
  - value: The extracted value (or null if not found)
  - unit: Unit if applicable (e.g., "BBY" for years)
  - confidence: Score from 0.0 to 1.0
  - evidence_ids: Array of evidence IDs that support this fact
  - notes: Optional notes about uncertainty or conflicts

If no facts can be extracted, return an empty facts array."""


def _load_output_schema() -> Dict[str, Any]:
    """Load the output schema from the contracts directory."""
    schema_path = Path(__file__).parent.parent.parent / "contracts" / "sw_entity_facts_v1_output.json"
    
    if schema_path.exists():
        with open(schema_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    # Fallback inline schema if file not found
    return {
        "type": "object",
        "required": ["entity_type", "entity_id", "facts"],
        "properties": {
            "entity_type": {"type": "string"},
            "entity_id": {"type": "string"},
            "entity_name": {"type": ["string", "null"]},
            "facts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["fact_key", "confidence", "evidence_ids"],
                    "properties": {
                        "fact_key": {"type": "string"},
                        "value": {},
                        "unit": {"type": ["string", "null"]},
                        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "evidence_ids": {"type": "array", "items": {"type": "string"}},
                        "notes": {"type": ["string", "null"]}
                    }
                }
            },
            "metadata": {"type": ["object", "null"]}
        }
    }


def create_sw_entity_facts_v1() -> InterrogationDefinition:
    """
    Create the sw_entity_facts_v1 interrogation definition.
    
    Returns:
        InterrogationDefinition for Star Wars entity fact extraction
    """
    return InterrogationDefinition(
        key="sw_entity_facts_v1",
        name="Star Wars Entity Facts",
        version="1.0.0",
        description="Extract normalized facts about Star Wars entities from evidence snippets.",
        prompt_template=PROMPT_TEMPLATE,
        output_schema=_load_output_schema(),
        system_prompt=SYSTEM_PROMPT,
        recommended_model="llama3.2",
        recommended_temperature=0.0,
        validator=validate_entity_facts_output,
    )
