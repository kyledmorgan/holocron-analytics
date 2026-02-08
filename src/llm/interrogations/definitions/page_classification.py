"""
Page Classification Interrogation (page_classification_v1).

Classifies wiki pages into semantic types using title and minimal signals.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..registry import InterrogationDefinition


# Configuration constants
MAX_LEAD_SENTENCE_LENGTH = 500
MAX_RATIONALE_LENGTH = 500


# System prompt for the interrogation
SYSTEM_PROMPT = """You are a precise page classification assistant for wiki pages about fictional universes.

Your task is to classify what TYPE of thing a wiki page is about based on the title and minimal signals.

---
TYPE KEY (Controlled Vocabulary)
Choose exactly ONE primary_type. Use secondary_types only to add nuance (subtypes) that still fit the primary selection.

PersonCharacter:
- A sentient individual (or named character persona) in-universe: people, Force users, named aliens, named creatures (excluding droids) if treated as a character.
- Strong cues: biography, "was a… who…", personal history, relationships, homeworld, affiliations, appearances.
- NOT this: a film/book/comic itself (WorkMedia), a battle (EventConflict), a planet (LocationPlace), a droid (use Droid type).

Droid:
- Named droids as individuals OR droid model lines/types/series.
- Strong cues: droid designation (R2-D2, C-3PO), model series (R2-series), droid class/type, technical specifications for droid models.
- Examples: "R2-D2" (named droid), "R2-series astromech droid" (model line), "Protocol droid" (type/class).

LocationPlace:
- A physical place: planet, moon, city, region, facility, shipyard, temple, base, station, terrain feature.
- Strong cues: geography, climate, coordinates, "located on/in", inhabitants, points of interest.

VehicleCraft:
- Starships, starfighters, shuttles, freighters, battle stations, vehicles with specs/class/manufacturer.
- Strong cues: ship class, manufacturer, armament, propulsion systems, technical specifications, "commanded by".
- Examples: "Millennium Falcon" (named craft), "X-wing starfighter" (model), "Death Star" (battle station).
- Distinguished from ObjectItem by being primarily a vehicle/craft vs. a handheld/worn item.

ObjectItem:
- Physical objects: weapons, lightsabers, blasters, armor, helmets, clothing, insignia, gear, relics, tattoos.
- Strong cues: physical description, materials, ownership, "wielded by", "worn by", design details.
- Examples: "Anakin's lightsaber", "Clone trooper armor", "Mandalorian helmet", "Jedi robes".

WorkMedia:
- A published work: film, episode, series, novel, comic issue/run, game, soundtrack, reference book.
- Strong cues: release date, creators, publisher, "is a film/novel/comic", plot summary as the primary framing.
- NOT this: a character who appears in a film (that stays PersonCharacter).

EventConflict:
- A discrete event: battle, war, raid, uprising, treaty signing, catastrophe, mission, duel, major incident.
- Strong cues: "battle of…", "during…", timeline emphasis, participants, outcome, casualties.

Organization:
- A group or formal body: governments, militaries, orders, syndicates, corporations, councils, clans.
- Strong cues: membership, leadership, doctrine, structure, formation/dissolution.

Species:
- A biological species or sentient group (not a single individual): Human, Twi'lek, Wookiee, etc.
- Strong cues: physiology, culture, homeworlds (plural), notable members list.

Concept:
- An abstract idea or system: the Force, hyperspace, ideologies, technologies as concepts, doctrines.
- Strong cues: definitions, principles, mechanics, applications, not a single place/person/event.

TimePeriod:
- A span of time: eras, ages, reigns, periods (e.g., "Imperial Era", "High Republic Era").
- Strong cues: start/end markers, "era", "period", chronology framing.

ReferenceMeta:
- Cross-page helper concepts: disambiguation, lists, timelines, glossaries, behind-the-scenes reference aggregations.
- Strong cues: list-of entries, index pages, "may refer to", navigation role, "Timeline of...", "List of...".

TechnicalSitePage:
- Site policy/technical/wiki infrastructure pages: protection policy, templates, categories, guidelines, help pages.
- Strong cues: wiki policy language, editors, formatting instructions, non-universe content.

Unknown:
- Only use when none of the above apply with any confidence and explain why in rationale.

---
DECISION RULES (to reduce common errors):
1) If the page is clearly a list/timeline/disambiguation/reference aggregation, it is ReferenceMeta.
2) If it is a single craft/vehicle/station with specs/class/manufacturer, it is VehicleCraft.
3) If it is a physical object/gear/weapon/apparel/handheld item, it is ObjectItem.
4) If it is a named droid or droid model/type, it is Droid (NOT PersonCharacter).
5) If it is centered on a named individual's life/story, it is PersonCharacter.
6) If the title is a film/book/comic/game, it is WorkMedia.
7) If the page is a battle/war/incident, it is EventConflict.
8) If the page is an era or "Age of…", it is TimePeriod.

---
SECONDARY TYPES (optional, free-text):
Use secondary_types to add specificity like: "Jedi", "Sith", "Smuggler", "Planet", "Space station", "Comic series", "Film episode", "Battle", "Religious order"
Each secondary_types[i].type is free-text; weight is 0.0–1.0.

---
TAG GUIDANCE (optional):
Suggested tags should be meaningful and not redundant with primary_type.
- Use tag_type examples: "Faction", "Role", "Species", "Era", "Theme", "EntitySubtype"
- Use visibility: "public" for user-facing, "hidden" for internal retrieval helpers.

---
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
                "Droid",
                "Species",
                "LocationPlace",
                "VehicleCraft",
                "ObjectItem",
                "ObjectArtifact",
                "Organization",
                "Concept",
                "EventConflict",
                "TimePeriod",
                "WorkMedia",
                "ReferenceMeta",
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
        "rationale": {"type": "string", "maxLength": MAX_RATIONALE_LENGTH},
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
        lines.append(f"Lead Sentence: {input_data['lead_sentence'][:MAX_LEAD_SENTENCE_LENGTH]}")
    
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
        version="1.1.0",
        description="Classify wiki pages into semantic types using title and minimal signals. Includes TYPE KEY controlled vocabulary with explicit definitions.",
        prompt_template=PROMPT_TEMPLATE,
        output_schema=OUTPUT_SCHEMA,
        system_prompt=SYSTEM_PROMPT,
        recommended_model="llama3.2",
        recommended_temperature=0.0,
        validator=validate_page_classification_output,
    )
