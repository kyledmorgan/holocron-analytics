"""
Relationship Extraction Interrogation (relationship_extraction_v1).

Extracts relationships between entities from source text into contract-compliant JSON.
Phase 2 focuses on entity-to-entity relationships with temporal bounds and work context.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from ..registry import InterrogationDefinition


# System prompt for relationship extraction
SYSTEM_PROMPT = """You are extracting structured relationship assertions from the provided text.

Task: Extract ALL relationships between entities mentioned in the text.

Return JSON with:
- relationships: array of {from_entity, to_entity, relation_type, start_date, end_date, work_context, confidence, evidence_quote, bidirectional}
Optional:
- entities_referenced: array of {name, type, confidence} for entities mentioned in relationships
- extraction_metadata: {source_page_title, total_relationships_found, relationship_types_found, extraction_notes}

RULES:
1. Output ONLY valid JSON. No markdown, no commentary, no explanations.
2. Do NOT invent or hallucinate relationships not present in the text.
3. Use confidence 1.0 ONLY when the relationship is explicitly stated.
4. Use confidence 0.7-0.9 when the relationship is strongly implied but not explicitly stated.
5. Use confidence 0.4-0.6 when the relationship is weakly implied or uncertain.
6. Include temporal bounds (start_date, end_date) ONLY when stated or clearly implied in text.
7. Include work_context when relationships are tied to specific media/works.
8. Include `evidence_quote` with a brief supporting quote when available.

RELATIONSHIP TYPE GUIDANCE:
Relationship types are open-ended strings. Examples include:
- Ownership: owned_by, belongs_to
- Service/Affiliation: served, worked_for, member_of, allied_with
- Creation: manufactured_by, created_by, built_by
- Personal: companion_of, friend_of, enemy_of, rival_of, trained_by, mentor_of
- Location: located_in, based_at, traveled_to
- Participation: participated_in, fought_in, attended
- Appearance: appeared_in, mentioned_in, featured_in
- Family: parent_of, child_of, sibling_of, married_to

TIME-BOUNDED ASSERTIONS:
- Use start_date and end_date for relationships with clear temporal bounds
- Dates can be fuzzy: "22 BBY", "Clone Wars era", "during the Empire", "approximately 0 BBY"
- Leave null if temporal information is not available or unclear

WORK CONTEXT:
- Include work_context array if the relationship is depicted in specific works
- Examples: ["A New Hope"], ["The Clone Wars Season 1", "Rebels"]
- This helps with provenance and context anchoring

EXAMPLES:

Example 1 - Explicit ownership relationship:
Text: "R2-D2, originally owned by Padmé Amidala, later served Luke Skywalker after the fall of the Empire."

Output:
{
  "relationships": [
    {
      "from_entity": "R2-D2",
      "to_entity": "Padmé Amidala",
      "relation_type": "owned_by",
      "start_date": null,
      "end_date": "19 BBY",
      "work_context": null,
      "confidence": 1.0,
      "evidence_quote": "R2-D2, originally owned by Padmé Amidala",
      "bidirectional": false
    },
    {
      "from_entity": "R2-D2",
      "to_entity": "Luke Skywalker",
      "relation_type": "served",
      "start_date": "after the fall of the Empire",
      "end_date": null,
      "work_context": null,
      "confidence": 1.0,
      "evidence_quote": "later served Luke Skywalker after the fall of the Empire",
      "bidirectional": false
    }
  ],
  "entities_referenced": [
    {"name": "R2-D2", "type": "Droid", "confidence": 1.0},
    {"name": "Padmé Amidala", "type": "PersonCharacter", "confidence": 1.0},
    {"name": "Luke Skywalker", "type": "PersonCharacter", "confidence": 1.0}
  ],
  "extraction_metadata": {
    "source_page_title": null,
    "total_relationships_found": 2,
    "relationship_types_found": ["owned_by", "served"],
    "extraction_notes": null
  }
}

Example 2 - Multiple relationships with work context:
Text: "In 'A New Hope', C-3PO and R2-D2 were companions who escaped the Tantive IV together."

Output:
{
  "relationships": [
    {
      "from_entity": "C-3PO",
      "to_entity": "R2-D2",
      "relation_type": "companion_of",
      "start_date": null,
      "end_date": null,
      "work_context": ["A New Hope"],
      "confidence": 1.0,
      "evidence_quote": "C-3PO and R2-D2 were companions",
      "bidirectional": true
    },
    {
      "from_entity": "C-3PO",
      "to_entity": "Tantive IV",
      "relation_type": "escaped_from",
      "start_date": null,
      "end_date": null,
      "work_context": ["A New Hope"],
      "confidence": 1.0,
      "evidence_quote": "escaped the Tantive IV together",
      "bidirectional": false
    },
    {
      "from_entity": "R2-D2",
      "to_entity": "Tantive IV",
      "relation_type": "escaped_from",
      "start_date": null,
      "end_date": null,
      "work_context": ["A New Hope"],
      "confidence": 1.0,
      "evidence_quote": "escaped the Tantive IV together",
      "bidirectional": false
    }
  ],
  "entities_referenced": [
    {"name": "C-3PO", "type": "Droid", "confidence": 1.0},
    {"name": "R2-D2", "type": "Droid", "confidence": 1.0},
    {"name": "Tantive IV", "type": "VehicleCraft", "confidence": 1.0}
  ],
  "extraction_metadata": {
    "source_page_title": null,
    "total_relationships_found": 3,
    "relationship_types_found": ["companion_of", "escaped_from"],
    "extraction_notes": "Companion relationship marked as bidirectional"
  }
}

Example 3 - Implied relationship (lower confidence):
Text: "The droids were seen together at the Rebel base."

Output:
{
  "relationships": [
    {
      "from_entity": "droids",
      "to_entity": "Rebel base",
      "relation_type": "located_at",
      "start_date": null,
      "end_date": null,
      "work_context": null,
      "confidence": 0.6,
      "evidence_quote": "droids were seen together at the Rebel base",
      "bidirectional": false
    }
  ],
  "entities_referenced": [
    {"name": "droids", "type": null, "confidence": 0.5},
    {"name": "Rebel base", "type": "LocationPlace", "confidence": 0.8}
  ],
  "extraction_metadata": {
    "source_page_title": null,
    "total_relationships_found": 1,
    "relationship_types_found": ["located_at"],
    "extraction_notes": "Vague reference to 'droids' without specific identification"
  }
}

Example 4 - No relationships found:
Text: "The desert planet had two suns that baked the surface."

Output:
{
  "relationships": [],
  "entities_referenced": [],
  "extraction_metadata": {
    "source_page_title": null,
    "total_relationships_found": 0,
    "relationship_types_found": [],
    "extraction_notes": "No entity relationships found in text"
  }
}"""


# Prompt template with placeholders
PROMPT_TEMPLATE = """Extract ALL relationships between entities from the following text.

Source Page: {source_page_title}
Source ID: {source_id}

--- TEXT START ---
{content}
--- TEXT END ---

Extract:
1. All relationships between entities mentioned (ownership, service, affiliation, location, participation, etc.)
2. Temporal bounds when stated or clearly implied (start_date, end_date)
3. Work context if relationships are tied to specific media
4. Evidence quotes supporting each relationship

Return ONLY valid JSON matching the schema. Do not include any explanation or markdown."""


def _load_output_schema() -> Dict[str, Any]:
    """Load the output schema from the contracts directory."""
    schema_path = Path(__file__).parent.parent.parent / "contracts" / "relationship_extraction_v1_output.json"
    
    if schema_path.exists():
        with open(schema_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    # Fallback inline schema if file not found
    return {
        "type": "object",
        "required": ["relationships"],
        "properties": {
            "relationships": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["from_entity", "to_entity", "relation_type", "confidence"],
                    "properties": {
                        "from_entity": {"type": "string", "maxLength": 500},
                        "to_entity": {"type": "string", "maxLength": 500},
                        "relation_type": {"type": "string", "maxLength": 100},
                        "start_date": {"type": ["string", "null"]},
                        "end_date": {"type": ["string", "null"]},
                        "work_context": {"type": "array", "items": {"type": "string"}},
                        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "evidence_quote": {"type": ["string", "null"]},
                        "bidirectional": {"type": "boolean"}
                    }
                }
            },
            "entities_referenced": {"type": "array"},
            "extraction_metadata": {"type": ["object", "null"]}
        }
    }


def validate_relationship_extraction_output(data: Dict[str, Any]) -> List[str]:
    """
    Validate relationship extraction output against the contract.
    
    Returns a list of validation errors (empty if valid).
    """
    errors = []
    
    # Check required fields
    if "relationships" not in data:
        errors.append("Missing required field: relationships")
    elif not isinstance(data["relationships"], list):
        errors.append("relationships must be an array")
    else:
        # Validate each relationship
        for i, rel in enumerate(data["relationships"]):
            if not isinstance(rel, dict):
                errors.append(f"relationships[{i}] must be an object")
                continue
            
            # Required relationship fields
            if "from_entity" not in rel:
                errors.append(f"relationships[{i}]: Missing required field: from_entity")
            elif not isinstance(rel["from_entity"], str):
                errors.append(f"relationships[{i}].from_entity must be a string")
            elif len(rel["from_entity"]) > 500:
                errors.append(f"relationships[{i}].from_entity exceeds maximum length of 500 characters")
            
            if "to_entity" not in rel:
                errors.append(f"relationships[{i}]: Missing required field: to_entity")
            elif not isinstance(rel["to_entity"], str):
                errors.append(f"relationships[{i}].to_entity must be a string")
            elif len(rel["to_entity"]) > 500:
                errors.append(f"relationships[{i}].to_entity exceeds maximum length of 500 characters")
            
            if "relation_type" not in rel:
                errors.append(f"relationships[{i}]: Missing required field: relation_type")
            elif not isinstance(rel["relation_type"], str):
                errors.append(f"relationships[{i}].relation_type must be a string")
            elif len(rel["relation_type"]) > 100:
                errors.append(f"relationships[{i}].relation_type exceeds maximum length of 100 characters")
            
            if "confidence" not in rel:
                errors.append(f"relationships[{i}]: Missing required field: confidence")
            elif not isinstance(rel["confidence"], (int, float)):
                errors.append(f"relationships[{i}].confidence must be a number")
            elif rel["confidence"] < 0.0 or rel["confidence"] > 1.0:
                errors.append(f"relationships[{i}].confidence must be between 0.0 and 1.0")
            
            # Optional field validation
            if "work_context" in rel and rel["work_context"] is not None:
                if not isinstance(rel["work_context"], list):
                    errors.append(f"relationships[{i}].work_context must be an array")
                else:
                    for j, work in enumerate(rel["work_context"]):
                        if not isinstance(work, str):
                            errors.append(f"relationships[{i}].work_context[{j}] must be a string")
            
            if "bidirectional" in rel and rel["bidirectional"] is not None:
                if not isinstance(rel["bidirectional"], bool):
                    errors.append(f"relationships[{i}].bidirectional must be a boolean")
    
    # Validate entities_referenced if present
    if "entities_referenced" in data:
        if not isinstance(data["entities_referenced"], list):
            errors.append("entities_referenced must be an array")
        else:
            for i, entity in enumerate(data["entities_referenced"]):
                if not isinstance(entity, dict):
                    errors.append(f"entities_referenced[{i}] must be an object")
                    continue
                
                if "name" not in entity:
                    errors.append(f"entities_referenced[{i}]: Missing required field: name")
                elif not isinstance(entity["name"], str):
                    errors.append(f"entities_referenced[{i}].name must be a string")
    
    return errors


def create_relationship_extraction_v1() -> InterrogationDefinition:
    """
    Create the relationship_extraction_v1 interrogation definition.
    
    Returns:
        InterrogationDefinition for relationship extraction
    """
    return InterrogationDefinition(
        key="relationship_extraction_v1",
        name="Relationship Extraction",
        version="1.0.0",
        description="Extract relationships between entities from source text into contract-compliant JSON. Phase 2 focuses on entity-to-entity relationships with temporal bounds and work context.",
        prompt_template=PROMPT_TEMPLATE,
        output_schema=_load_output_schema(),
        system_prompt=SYSTEM_PROMPT,
        recommended_model="llama3.2",
        recommended_temperature=0.0,
        validator=validate_relationship_extraction_output,
    )
