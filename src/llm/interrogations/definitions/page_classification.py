"""
Page Classification Interrogation (page_classification_v1).

Classifies wiki pages into semantic types using title and minimal signals.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..registry import InterrogationDefinition


# System prompt for the interrogation
SYSTEM_PROMPT = """You are a precise page classification assistant for wiki pages about fictional universes.

Your task is to classify what TYPE of thing a wiki page is about based on the title and minimal signals.

You must classify pages into one of these primary types:
- PersonCharacter: An individual person, character, or being
- LocationPlace: A planet, region, city, building, or other geographic location
- WorkMedia: A creative work like a film, book, comic, game, or TV series
- EventConflict: A battle, war, political event, or other significant occurrence
- Concept: An abstract concept, philosophy, belief, or practice
- Organization: A group, faction, government, or corporation
- Species: A species or race of beings
- Technology: A technology, device, or invention
- Vehicle: A vehicle, ship, or transport
- Weapon: A weapon or armament
- MetaReference: A reference page, list, timeline, or disambiguation page
- TimePeriod: A specific year, era, or date reference
- TechnicalSitePage: A wiki maintenance page, template, or module
- Unknown: Cannot determine with confidence

Rules:
1. Use the title as the primary signal for classification.
2. Use lead sentence and infobox type if provided for additional context.
3. Use categories if provided to confirm or refine classification.
4. Be conservative - if uncertain, indicate lower confidence and set needs_review=true.
5. Provide a brief rationale explaining your classification.
6. Suggest relevant tags based on the classification.
7. Respond ONLY with valid JSON matching the required schema."""


# Prompt template with placeholders
PROMPT_TEMPLATE = """Classify the following wiki page based on the provided signals.

Title: {title}
Namespace: {namespace}
Continuity Hint: {continuity_hint}

{optional_signals}

Based on these signals, determine:
1. What PRIMARY TYPE of thing is this page about?
2. What is your confidence score (0.0 to 1.0)?
3. What secondary types might apply (with weights)?
4. Does this need human review?
5. What tags should be applied?

Return a JSON object with:
- primary_type: One of the allowed types
- confidence_score: Number from 0.0 to 1.0
- secondary_types: Array of {{"type": "...", "weight": 0.0-1.0}}
- needs_review: Boolean
- rationale: Brief explanation
- suggested_tags: Array of tag strings (e.g., "type:person_character", "role:jedi")
- entity_hints: Object with any detected entity metadata (optional)"""


# Output schema for structured output
OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["primary_type", "confidence_score", "needs_review", "rationale"],
    "properties": {
        "primary_type": {
            "type": "string",
            "enum": [
                "PersonCharacter",
                "LocationPlace", 
                "WorkMedia",
                "EventConflict",
                "Concept",
                "Organization",
                "Species",
                "Technology",
                "Vehicle",
                "Weapon",
                "MetaReference",
                "TimePeriod",
                "TechnicalSitePage",
                "Unknown"
            ]
        },
        "confidence_score": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0
        },
        "secondary_types": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["type", "weight"],
                "properties": {
                    "type": {"type": "string"},
                    "weight": {"type": "number", "minimum": 0.0, "maximum": 1.0}
                }
            }
        },
        "needs_review": {"type": "boolean"},
        "rationale": {"type": "string", "maxLength": 500},
        "suggested_tags": {
            "type": "array",
            "items": {"type": "string"}
        },
        "entity_hints": {
            "type": ["object", "null"],
            "properties": {
                "possible_species": {"type": ["string", "null"]},
                "possible_affiliation": {"type": ["string", "null"]},
                "possible_era": {"type": ["string", "null"]}
            }
        }
    }
}


def validate_page_classification_output(output: Dict[str, Any]) -> List[str]:
    """
    Validate page classification output.
    
    Returns a list of validation errors (empty if valid).
    """
    errors = []
    
    # Check required fields
    if "primary_type" not in output:
        errors.append("Missing required field: primary_type")
    elif output["primary_type"] not in OUTPUT_SCHEMA["properties"]["primary_type"]["enum"]:
        errors.append(f"Invalid primary_type: {output['primary_type']}")
    
    if "confidence_score" not in output:
        errors.append("Missing required field: confidence_score")
    elif not isinstance(output["confidence_score"], (int, float)):
        errors.append("confidence_score must be a number")
    elif output["confidence_score"] < 0.0 or output["confidence_score"] > 1.0:
        errors.append("confidence_score must be between 0.0 and 1.0")
    
    if "needs_review" not in output:
        errors.append("Missing required field: needs_review")
    elif not isinstance(output["needs_review"], bool):
        errors.append("needs_review must be a boolean")
    
    if "rationale" not in output:
        errors.append("Missing required field: rationale")
    elif not isinstance(output["rationale"], str):
        errors.append("rationale must be a string")
    
    # Validate optional fields
    if "secondary_types" in output:
        if not isinstance(output["secondary_types"], list):
            errors.append("secondary_types must be an array")
        else:
            for i, st in enumerate(output["secondary_types"]):
                if not isinstance(st, dict):
                    errors.append(f"secondary_types[{i}] must be an object")
                elif "type" not in st or "weight" not in st:
                    errors.append(f"secondary_types[{i}] must have type and weight")
    
    if "suggested_tags" in output:
        if not isinstance(output["suggested_tags"], list):
            errors.append("suggested_tags must be an array")
    
    return errors


def format_optional_signals(input_data: Dict[str, Any]) -> str:
    """Format optional signals for the prompt."""
    lines = []
    
    if input_data.get("lead_sentence"):
        lines.append(f"Lead Sentence: {input_data['lead_sentence'][:500]}")
    
    if input_data.get("infobox_type"):
        lines.append(f"Infobox Type: {input_data['infobox_type']}")
    
    if input_data.get("categories"):
        cats = input_data["categories"][:10]
        lines.append(f"Categories: {', '.join(cats)}")
    
    if input_data.get("is_list_page"):
        lines.append("Flag: This is a list page")
    
    if input_data.get("is_disambiguation"):
        lines.append("Flag: This is a disambiguation page")
    
    if not lines:
        return "No additional signals available."
    
    return "\n".join(lines)


def create_page_classification_v1() -> InterrogationDefinition:
    """
    Create the page_classification_v1 interrogation definition.
    
    Returns:
        InterrogationDefinition for page classification
    """
    return InterrogationDefinition(
        key="page_classification_v1",
        name="Page Classification",
        version="1.0.0",
        description="Classify wiki pages into semantic types using title and minimal signals.",
        prompt_template=PROMPT_TEMPLATE,
        output_schema=OUTPUT_SCHEMA,
        system_prompt=SYSTEM_PROMPT,
        recommended_model="llama3.2",
        recommended_temperature=0.0,
        validator=validate_page_classification_output,
    )
