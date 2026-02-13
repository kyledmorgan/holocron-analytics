"""
Generic Entity Extraction Interrogation (entity_extraction_generic_v1).

Phase 3: Generalized extraction supporting ALL entity types (PersonCharacter,
LocationPlace, Organization, VehicleCraft, Work, Event, Concept, etc.)
in a unified, contract-driven way.

The generic prompt handles multiple entity types with flexible attributes
and consistent confidence scoring. Domain-specific prompts remain available
for cases where specialization outperforms the generic approach.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from ..registry import InterrogationDefinition


# System prompt for generic entity extraction
SYSTEM_PROMPT = """You are extracting structured facts from the provided text.

Task: Extract ALL entities mentioned in the text.

Return JSON with:
- entities: array of {name, type, confidence, aliases, attributes, evidence_quote, temporal_context, work_references}
Optional:
- relationships: array of {from_entity, to_entity, relation_type, start_date, end_date, confidence}
- extraction_metadata: {source_page_title, total_entities_found, entity_types_found, primary_type_focus, extraction_notes}

CORE PRINCIPLE: Extract what is present; do NOT invent what is absent.

RULES:
1. Output ONLY valid JSON. No markdown, no commentary, no explanations.
2. Do NOT invent or hallucinate entities not present in the text.
3. Extract entities of ANY type found in the text.
4. The `type` field is an open string taxonomy - use descriptive types.
5. The `attributes` field is flexible JSON; include only what the text supports.
6. Include `evidence_quote` with a brief supporting quote when available.

CONFIDENCE SCORING:
- 1.0: Explicitly named - entity name appears verbatim in text
- 0.7-0.9: Strongly implied - context makes identity clear
- 0.4-0.6: Weakly implied - mentioned indirectly or partially
- <0.4: Uncertain - vague reference, may be ambiguous

ENTITY TYPE TAXONOMY (open-ended, examples):
- PersonCharacter: Named individuals (Luke Skywalker, Darth Vader)
- Droid: Named droids or droid models (R2-D2, C-3PO, B1 battle droid)
- Species: Species or races (Human, Wookiee, Twi'lek)
- LocationPlace: Planets, cities, buildings, regions (Tatooine, Coruscant, Mos Eisley)
- VehicleCraft: Ships, vehicles, craft (Millennium Falcon, X-wing, AT-AT)
- ObjectItem: Weapons, gear, armor, items (Lightsaber, Blaster, Holocron)
- Organization: Groups, factions, governments (Rebel Alliance, Galactic Empire, Jedi Order)
- Concept: Ideas, Force abilities, philosophies (The Force, Order 66, Rule of Two)
- EventConflict: Battles, wars, events (Battle of Yavin, Clone Wars, Order 66)
- TimePeriod: Eras, periods (Clone Wars era, Age of the Empire, High Republic)
- WorkMedia: Films, books, games, episodes (A New Hope, Heir to the Empire)

ATTRIBUTE GUIDANCE BY TYPE:
PersonCharacter:
- species, homeworld, affiliation, occupation, title, era_active

Droid:
- model, manufacturer, droid_class, affiliation, color, height, programming

Species:
- homeworld, classification, language, notable_traits

LocationPlace:
- planet, system, sector, region, terrain, climate, government

VehicleCraft:
- manufacturer, model, class, length, crew, armament, hyperdrive

ObjectItem:
- type, manufacturer, material, function, notable_owners

Organization:
- type, headquarters, leader, ideology, era_active, parent_org

Concept:
- category, origin, related_to

EventConflict:
- date_start, date_end, location, participants, outcome

TimePeriod:
- date_start, date_end, era_name, key_events

WorkMedia:
- medium (film/tv/book/comic/game), release_date, creator, canon_status

EXAMPLES:

Example 1 - Multiple entity types:
Text: "Luke Skywalker piloted his X-wing fighter during the Battle of Yavin in 0 BBY. The Rebel Alliance celebrated their victory against the Galactic Empire."

Output:
{
  "entities": [
    {
      "name": "Luke Skywalker",
      "type": "PersonCharacter",
      "confidence": 1.0,
      "aliases": [],
      "attributes": {
        "affiliation": "Rebel Alliance"
      },
      "evidence_quote": "Luke Skywalker piloted his X-wing fighter",
      "temporal_context": "0 BBY",
      "work_references": null
    },
    {
      "name": "X-wing",
      "type": "VehicleCraft",
      "confidence": 1.0,
      "aliases": ["X-wing fighter"],
      "attributes": {
        "class": "starfighter"
      },
      "evidence_quote": "piloted his X-wing fighter",
      "temporal_context": null,
      "work_references": null
    },
    {
      "name": "Battle of Yavin",
      "type": "EventConflict",
      "confidence": 1.0,
      "aliases": [],
      "attributes": {
        "date_start": "0 BBY",
        "participants": ["Rebel Alliance", "Galactic Empire"]
      },
      "evidence_quote": "Battle of Yavin in 0 BBY",
      "temporal_context": "0 BBY",
      "work_references": null
    },
    {
      "name": "Rebel Alliance",
      "type": "Organization",
      "confidence": 1.0,
      "aliases": [],
      "attributes": {
        "type": "resistance movement"
      },
      "evidence_quote": "The Rebel Alliance celebrated their victory",
      "temporal_context": null,
      "work_references": null
    },
    {
      "name": "Galactic Empire",
      "type": "Organization",
      "confidence": 1.0,
      "aliases": [],
      "attributes": {
        "type": "government"
      },
      "evidence_quote": "victory against the Galactic Empire",
      "temporal_context": null,
      "work_references": null
    }
  ],
  "relationships": [
    {
      "from_entity": "Luke Skywalker",
      "to_entity": "X-wing",
      "relation_type": "piloted",
      "start_date": "0 BBY",
      "end_date": null,
      "confidence": 1.0
    },
    {
      "from_entity": "Luke Skywalker",
      "to_entity": "Rebel Alliance",
      "relation_type": "member_of",
      "start_date": null,
      "end_date": null,
      "confidence": 0.9
    }
  ],
  "extraction_metadata": {
    "source_page_title": null,
    "total_entities_found": 5,
    "entity_types_found": ["PersonCharacter", "VehicleCraft", "EventConflict", "Organization"],
    "primary_type_focus": null,
    "extraction_notes": null
  }
}

Example 2 - Location and species focus:
Text: "Kashyyyk, the forested homeworld of the Wookiees, is located in the Mytaranor sector."

Output:
{
  "entities": [
    {
      "name": "Kashyyyk",
      "type": "LocationPlace",
      "confidence": 1.0,
      "aliases": [],
      "attributes": {
        "terrain": "forested",
        "sector": "Mytaranor sector"
      },
      "evidence_quote": "Kashyyyk, the forested homeworld",
      "temporal_context": null,
      "work_references": null
    },
    {
      "name": "Wookiees",
      "type": "Species",
      "confidence": 1.0,
      "aliases": ["Wookiee"],
      "attributes": {
        "homeworld": "Kashyyyk"
      },
      "evidence_quote": "homeworld of the Wookiees",
      "temporal_context": null,
      "work_references": null
    },
    {
      "name": "Mytaranor sector",
      "type": "LocationPlace",
      "confidence": 1.0,
      "aliases": [],
      "attributes": {
        "type": "sector"
      },
      "evidence_quote": "located in the Mytaranor sector",
      "temporal_context": null,
      "work_references": null
    }
  ],
  "relationships": [
    {
      "from_entity": "Kashyyyk",
      "to_entity": "Mytaranor sector",
      "relation_type": "located_in",
      "start_date": null,
      "end_date": null,
      "confidence": 1.0
    }
  ],
  "extraction_metadata": {
    "source_page_title": null,
    "total_entities_found": 3,
    "entity_types_found": ["LocationPlace", "Species"],
    "primary_type_focus": null,
    "extraction_notes": null
  }
}

Example 3 - Vague references (lower confidence):
Text: "The starship docked at an orbital station somewhere in the Outer Rim."

Output:
{
  "entities": [
    {
      "name": "unnamed starship",
      "type": "VehicleCraft",
      "confidence": 0.4,
      "aliases": [],
      "attributes": {
        "class": "starship"
      },
      "evidence_quote": "The starship docked",
      "temporal_context": null,
      "work_references": null
    },
    {
      "name": "orbital station",
      "type": "LocationPlace",
      "confidence": 0.5,
      "aliases": [],
      "attributes": {
        "type": "station",
        "region": "Outer Rim"
      },
      "evidence_quote": "an orbital station somewhere in the Outer Rim",
      "temporal_context": null,
      "work_references": null
    },
    {
      "name": "Outer Rim",
      "type": "LocationPlace",
      "confidence": 1.0,
      "aliases": ["Outer Rim Territories"],
      "attributes": {
        "type": "region"
      },
      "evidence_quote": "in the Outer Rim",
      "temporal_context": null,
      "work_references": null
    }
  ],
  "relationships": [],
  "extraction_metadata": {
    "source_page_title": null,
    "total_entities_found": 3,
    "entity_types_found": ["VehicleCraft", "LocationPlace"],
    "primary_type_focus": null,
    "extraction_notes": "Starship and station are unnamed; lower confidence for unidentified entities"
  }
}

Example 4 - No entities found:
Text: "The light from the twin suns faded as darkness fell across the dunes."

Output:
{
  "entities": [],
  "relationships": [],
  "extraction_metadata": {
    "source_page_title": null,
    "total_entities_found": 0,
    "entity_types_found": [],
    "primary_type_focus": null,
    "extraction_notes": "No named entities found in text; describes scenery without specific entity references"
  }
}"""


# Prompt template with placeholders
PROMPT_TEMPLATE = """Extract ALL entities from the following text.

Source Page: {source_page_title}
Source ID: {source_id}

--- TEXT START ---
{content}
--- TEXT END ---

Extract:
1. All entities mentioned (characters, droids, locations, vehicles, organizations, events, works, concepts, etc.)
2. Entity attributes where supported by the text
3. Relationships between entities (if apparent)
4. Evidence quotes supporting each extraction

Return ONLY valid JSON matching the schema. Do not include any explanation or markdown."""


def _load_output_schema() -> Dict[str, Any]:
    """Load the output schema from the contracts directory."""
    schema_path = Path(__file__).parent.parent.parent / "contracts" / "entity_extraction_generic_v1_schema.json"
    
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
                        "type": {"type": "string", "maxLength": 100},
                        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                        "aliases": {"type": "array", "items": {"type": "string"}},
                        "attributes": {"type": "object", "additionalProperties": True},
                        "evidence_quote": {"type": ["string", "null"]},
                        "temporal_context": {"type": ["string", "null"]},
                        "work_references": {"type": "array", "items": {"type": "string"}}
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


def validate_entity_extraction_generic_output(data: Dict[str, Any]) -> List[str]:
    """
    Validate generic entity extraction output against the contract.
    
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
            elif len(entity["type"]) > 100:
                errors.append(f"entities[{i}].type exceeds maximum length of 100 characters")
            
            if "confidence" not in entity:
                errors.append(f"entities[{i}]: Missing required field: confidence")
            elif not isinstance(entity["confidence"], (int, float)):
                errors.append(f"entities[{i}].confidence must be a number")
            elif entity["confidence"] < 0.0 or entity["confidence"] > 1.0:
                errors.append(f"entities[{i}].confidence must be between 0.0 and 1.0")
            
            # Optional field validation
            if "aliases" in entity and entity["aliases"] is not None:
                if not isinstance(entity["aliases"], list):
                    errors.append(f"entities[{i}].aliases must be an array")
                else:
                    for j, alias in enumerate(entity["aliases"]):
                        if not isinstance(alias, str):
                            errors.append(f"entities[{i}].aliases[{j}] must be a string")
            
            if "attributes" in entity and entity["attributes"] is not None:
                if not isinstance(entity["attributes"], dict):
                    errors.append(f"entities[{i}].attributes must be an object")
            
            if "temporal_context" in entity and entity["temporal_context"] is not None:
                if not isinstance(entity["temporal_context"], str):
                    errors.append(f"entities[{i}].temporal_context must be a string")
                elif len(entity["temporal_context"]) > 200:
                    errors.append(f"entities[{i}].temporal_context exceeds maximum length of 200 characters")
            
            if "work_references" in entity and entity["work_references"] is not None:
                if not isinstance(entity["work_references"], list):
                    errors.append(f"entities[{i}].work_references must be an array")
                else:
                    for j, ref in enumerate(entity["work_references"]):
                        if not isinstance(ref, str):
                            errors.append(f"entities[{i}].work_references[{j}] must be a string")
    
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
    
    # Validate extraction_metadata if present
    if "extraction_metadata" in data and data["extraction_metadata"] is not None:
        meta = data["extraction_metadata"]
        if not isinstance(meta, dict):
            errors.append("extraction_metadata must be an object")
        else:
            if "total_entities_found" in meta:
                if not isinstance(meta["total_entities_found"], int):
                    errors.append("extraction_metadata.total_entities_found must be an integer")
                elif meta["total_entities_found"] < 0:
                    errors.append("extraction_metadata.total_entities_found must be >= 0")
            
            if "entity_types_found" in meta and meta["entity_types_found"] is not None:
                if not isinstance(meta["entity_types_found"], list):
                    errors.append("extraction_metadata.entity_types_found must be an array")
    
    return errors


def create_entity_extraction_generic_v1() -> InterrogationDefinition:
    """
    Create the entity_extraction_generic_v1 interrogation definition.
    
    Returns:
        InterrogationDefinition for generic entity extraction
    """
    return InterrogationDefinition(
        key="entity_extraction_generic_v1",
        name="Generic Entity Extraction",
        version="1.0.0",
        description=(
            "Extract entities of ALL types from source text into contract-compliant JSON. "
            "Phase 3 generalized prompt supporting PersonCharacter, LocationPlace, Organization, "
            "VehicleCraft, Work, Event, Concept, and more. Uses flexible attributes and "
            "consistent confidence scoring."
        ),
        prompt_template=PROMPT_TEMPLATE,
        output_schema=_load_output_schema(),
        system_prompt=SYSTEM_PROMPT,
        recommended_model="llama3.2",
        recommended_temperature=0.0,
        validator=validate_entity_extraction_generic_output,
    )
