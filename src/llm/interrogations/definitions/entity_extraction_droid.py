"""
Droid Entity Extraction Interrogation (entity_extraction_droid_v1).

Extracts droid entities from source text into contract-compliant JSON.
Phase 1 focuses on droids as a single entity subtype.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from ..registry import InterrogationDefinition


# System prompt for droid entity extraction
SYSTEM_PROMPT = """You are extracting structured facts from the provided text.

Task: Extract ALL droid entities mentioned in the text.

Return JSON with:
- entities: array of {name, type, confidence, aliases, attributes, evidence_quote}
Optional:
- relationships: array of {from_entity, to_entity, relation_type, start_date, end_date, confidence}
- extraction_metadata: {source_page_title, total_entities_found, primary_type_focus, extraction_notes}

RULES:
1. Output ONLY valid JSON. No markdown, no commentary, no explanations.
2. Do NOT invent or hallucinate entities not present in the text.
3. Use confidence 1.0 ONLY when the entity is explicitly named.
4. Use confidence 0.7-0.9 when the entity is strongly implied but not explicitly named.
5. Use confidence 0.4-0.6 when the entity is vaguely mentioned.
6. The `attributes` field is flexible JSON; include only what the text supports.
7. Include `evidence_quote` with a brief supporting quote when available.
8. If an entity has multiple names/designations, list alternatives in `aliases`.

ATTRIBUTE GUIDANCE FOR DROIDS:
Common attributes to extract if present in text:
- model: Droid model/series (e.g., "R2-series", "Protocol droid")
- manufacturer: Who made the droid (e.g., "Industrial Automaton")
- droid_class: Functional class (e.g., "astromech", "protocol", "battle")
- affiliation: Who the droid serves or is associated with
- color: Physical color scheme
- height: Physical height if mentioned
- programming: Special programming or capabilities
- era: Time period when active

TYPE STRING:
Always use "Droid" as the type for droid entities.

RELATIONSHIP TYPES (if extracting relationships):
- owned_by: Droid is owned by entity
- served: Droid served/worked for entity
- manufactured_by: Droid was made by manufacturer
- companion_of: Droid is a companion to entity
- repaired_by: Droid was repaired by entity
- destroyed_by: Droid was destroyed by entity

EXAMPLES:

Example 1 - Explicit named droid:
Text: "R2-D2, an astromech droid manufactured by Industrial Automaton, served Anakin Skywalker during the Clone Wars."

Output:
{
  "entities": [
    {
      "name": "R2-D2",
      "type": "Droid",
      "confidence": 1.0,
      "aliases": [],
      "attributes": {
        "model": "astromech droid",
        "manufacturer": "Industrial Automaton"
      },
      "evidence_quote": "R2-D2, an astromech droid manufactured by Industrial Automaton"
    }
  ],
  "relationships": [
    {
      "from_entity": "R2-D2",
      "to_entity": "Anakin Skywalker",
      "relation_type": "served",
      "start_date": "Clone Wars",
      "end_date": null,
      "confidence": 1.0
    }
  ],
  "extraction_metadata": {
    "source_page_title": null,
    "total_entities_found": 1,
    "primary_type_focus": "Droid",
    "extraction_notes": null
  }
}

Example 2 - Vague reference (lower confidence):
Text: "The rebels had a few droids helping with repairs in the hangar."

Output:
{
  "entities": [
    {
      "name": "unnamed repair droids",
      "type": "Droid",
      "confidence": 0.4,
      "aliases": [],
      "attributes": {
        "droid_class": "repair"
      },
      "evidence_quote": "a few droids helping with repairs"
    }
  ],
  "relationships": [],
  "extraction_metadata": {
    "source_page_title": null,
    "total_entities_found": 1,
    "primary_type_focus": "Droid",
    "extraction_notes": "No specific droid names mentioned; generic reference only"
  }
}

Example 3 - Non-droid mention (return empty):
Text: "Luke Skywalker trained with Obi-Wan Kenobi on Tatooine."

Output:
{
  "entities": [],
  "relationships": [],
  "extraction_metadata": {
    "source_page_title": null,
    "total_entities_found": 0,
    "primary_type_focus": "Droid",
    "extraction_notes": "No droid entities found in text"
  }
}

Example 4 - Model line (not individual):
Text: "The R2-series astromech droids were produced by Industrial Automaton and were popular throughout the galaxy."

Output:
{
  "entities": [
    {
      "name": "R2-series astromech droid",
      "type": "Droid",
      "confidence": 1.0,
      "aliases": ["R2-series", "R2 unit"],
      "attributes": {
        "model": "R2-series",
        "droid_class": "astromech",
        "manufacturer": "Industrial Automaton"
      },
      "evidence_quote": "R2-series astromech droids were produced by Industrial Automaton"
    }
  ],
  "relationships": [],
  "extraction_metadata": {
    "source_page_title": null,
    "total_entities_found": 1,
    "primary_type_focus": "Droid",
    "extraction_notes": "This is a droid model line, not an individual droid"
  }
}"""


# Prompt template with placeholders
PROMPT_TEMPLATE = """Extract ALL droid entities from the following text.

Source Page: {source_page_title}
Source ID: {source_id}

--- TEXT START ---
{content}
--- TEXT END ---

Extract:
1. All droid entities mentioned (named individuals, model types, or unnamed references)
2. Relationships between droids and other entities (if apparent)
3. Attributes for each droid (model, manufacturer, class, affiliation, etc.)

Return ONLY valid JSON matching the schema. Do not include any explanation or markdown."""


def _load_output_schema() -> Dict[str, Any]:
    """Load the output schema from the contracts directory."""
    schema_path = Path(__file__).parent.parent.parent / "contracts" / "entity_extraction_v1_output.json"
    
    if schema_path.exists():
        with open(schema_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    # Fallback inline schema if file not found
    return {
        "type": "object",
        "required": ["entities"],
        "properties": {
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "type", "confidence"],
                    "properties": {
                        "name": {"type": "string", "maxLength": 500},
                        "type": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "aliases": {"type": "array", "items": {"type": "string"}},
                        "attributes": {"type": "object", "additionalProperties": True},
                        "evidence_quote": {"type": ["string", "null"]}
                    }
                }
            },
            "relationships": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["from_entity", "to_entity", "relation_type", "confidence"],
                    "properties": {
                        "from_entity": {"type": "string"},
                        "to_entity": {"type": "string"},
                        "relation_type": {"type": "string"},
                        "start_date": {"type": ["string", "null"]},
                        "end_date": {"type": ["string", "null"]},
                        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0}
                    }
                }
            },
            "extraction_metadata": {"type": ["object", "null"]}
        }
    }


def validate_entity_extraction_output(data: Dict[str, Any]) -> List[str]:
    """
    Validate entity extraction output against the contract.
    
    Returns a list of validation errors (empty if valid).
    """
    errors = []
    
    # Check required fields
    if "entities" not in data:
        errors.append("Missing required field: entities")
    elif not isinstance(data["entities"], list):
        errors.append("entities must be an array")
    else:
        # Validate each entity
        for i, entity in enumerate(data["entities"]):
            if not isinstance(entity, dict):
                errors.append(f"entities[{i}] must be an object")
                continue
            
            # Required entity fields
            if "name" not in entity:
                errors.append(f"entities[{i}]: Missing required field: name")
            elif not isinstance(entity["name"], str):
                errors.append(f"entities[{i}].name must be a string")
            elif len(entity["name"]) > 500:
                errors.append(f"entities[{i}].name exceeds maximum length of 500 characters")
            
            if "type" not in entity:
                errors.append(f"entities[{i}]: Missing required field: type")
            elif not isinstance(entity["type"], str):
                errors.append(f"entities[{i}].type must be a string")
            
            if "confidence" not in entity:
                errors.append(f"entities[{i}]: Missing required field: confidence")
            elif not isinstance(entity["confidence"], (int, float)):
                errors.append(f"entities[{i}].confidence must be a number")
            elif entity["confidence"] < 0.0 or entity["confidence"] > 1.0:
                errors.append(f"entities[{i}].confidence must be between 0.0 and 1.0")
            
            # Optional field validation
            if "aliases" in entity and not isinstance(entity["aliases"], list):
                errors.append(f"entities[{i}].aliases must be an array")
            
            if "attributes" in entity and not isinstance(entity["attributes"], dict):
                errors.append(f"entities[{i}].attributes must be an object")
    
    # Validate relationships if present
    if "relationships" in data:
        if not isinstance(data["relationships"], list):
            errors.append("relationships must be an array")
        else:
            for i, rel in enumerate(data["relationships"]):
                if not isinstance(rel, dict):
                    errors.append(f"relationships[{i}] must be an object")
                    continue
                
                # Required relationship fields
                for field in ["from_entity", "to_entity", "relation_type"]:
                    if field not in rel:
                        errors.append(f"relationships[{i}]: Missing required field: {field}")
                    elif not isinstance(rel[field], str):
                        errors.append(f"relationships[{i}].{field} must be a string")
                
                if "confidence" in rel:
                    conf = rel["confidence"]
                    if not isinstance(conf, (int, float)):
                        errors.append(f"relationships[{i}].confidence must be a number")
                    elif conf < 0.0 or conf > 1.0:
                        errors.append(f"relationships[{i}].confidence must be between 0.0 and 1.0")
    
    return errors


def create_entity_extraction_droid_v1() -> InterrogationDefinition:
    """
    Create the entity_extraction_droid_v1 interrogation definition.
    
    Returns:
        InterrogationDefinition for droid entity extraction
    """
    return InterrogationDefinition(
        key="entity_extraction_droid_v1",
        name="Droid Entity Extraction",
        version="1.0.0",
        description="Extract droid entities from source text into contract-compliant JSON. Phase 1 focuses on droids as a single entity subtype.",
        prompt_template=PROMPT_TEMPLATE,
        output_schema=_load_output_schema(),
        system_prompt=SYSTEM_PROMPT,
        recommended_model="llama3.2",
        recommended_temperature=0.0,
        validator=validate_entity_extraction_output,
    )
