"""
Standardized prompts for page classification.

Model-agnostic prompts for Wikipedia/Wookieepedia page classification.
Designed for use with Ollama and any compatible local LLM.
"""

# Version identifier for prompt tracking
PROMPT_VERSION = "v3_contract"


# System prompt: Role definition + strict output rules
SYSTEM_PROMPT = """You are a Wikipedia-style page classifier and metadata extractor. You will be given a page title and a bounded excerpt from the article body. Your job is to infer the page's entity type(s), continuity hint, confidence, and suggested tags for indexing.

OUTPUT RULES (STRICT):
- Return ONLY valid JSON matching the provided schema
- No markdown, no extra keys, no commentary
- If uncertain, set needs_review=true and reduce confidence

PRIMARY TYPE CLASSIFICATION RUBRIC:
Follow this decision order to reduce Unknown classifications:

1. **ReferenceMeta** - Lists, indexes, timelines, disambiguation, guides, reference aggregations
   - Cues: "List of...", "Timeline of...", "may refer to", navigation role, encyclopedic cross-references
   - Examples: "List of Star Wars films", "Timeline of galactic history", "Skywalker (disambiguation)"

2. **VehicleCraft** - Starships, starfighters, shuttles, freighters, battle stations, vehicles with specs/class/manufacturer
   - Cues: ship class, manufacturer, armament, propulsion systems, technical specifications
   - Examples: "Millennium Falcon" (named craft), "X-wing starfighter" (model), "Death Star" (battle station)

3. **ObjectItem** - Physical objects: weapons, lightsabers, blasters, armor, helmets, clothing, insignia, gear, tattoos
   - Cues: physical description, materials, ownership, "wielded by", "worn by", design details
   - Examples: "Anakin's lightsaber", "Clone trooper armor", "Mandalorian helmet", "Jedi robes"

4. **Droid** - Named droids as individuals OR droid model lines/types
   - Cues: droid designation (R2-D2, C-3PO), model series (R2-series), droid class/type
   - Examples: "R2-D2" (named droid), "R2-series astromech droid" (model), "Protocol droid" (type)
   - Note: Named droids as characters (with biography) go here, NOT PersonCharacter

5. **PersonCharacter** - Sentient individuals with biography, personal history, relationships
   - Cues: "was a...", biography, homeworld, family, affiliations, character arc, appearances
   - Examples: "Luke Skywalker", "Darth Vader", "Ahsoka Tano", "Yoda"
   - Note: NOT for droids (use Droid type), NOT for films/books (use WorkMedia)

6. **LocationPlace** - Physical places: planets, moons, cities, regions, facilities, bases, stations, structures
   - Cues: geography, climate, coordinates, inhabitants, "located on/in", points of interest
   - Examples: "Tatooine" (planet), "Coruscant" (planet/city), "Jedi Temple" (structure), "Echo Base" (facility)

7. **Species** - Biological species or sentient groups (NOT individuals)
   - Cues: physiology, culture, homeworlds (plural), notable members list, "a species of..."
   - Examples: "Human", "Twi'lek", "Wookiee", "Hutt"

8. **Organization** - Groups, governments, militaries, orders, syndicates, corporations, councils
   - Cues: membership, leadership, structure, doctrine, formation/dissolution, hierarchy
   - Examples: "Jedi Order", "Galactic Empire", "Rebel Alliance", "Hutt Cartel"

9. **EventConflict** - Discrete events: battles, wars, raids, missions, duels, treaties, catastrophes
   - Cues: "Battle of...", "during...", participants, outcome, casualties, date/timeline
   - Examples: "Battle of Yavin", "Clone Wars", "Order 66", "Duel on Mustafar"

10. **WorkMedia** - Published creative works: films, episodes, series, novels, comics, games, soundtracks
    - Cues: release date, creators, publisher, plot summary, "is a film/novel/comic/game"
    - Examples: "Star Wars (film)", "The Empire Strikes Back", "Knights of the Old Republic" (game)
    - IMPORTANT: If primary_type is WorkMedia, you MUST populate work_medium and canon_context fields

11. **TimePeriod** - Spans of time: eras, ages, periods, reigns
    - Cues: start/end dates, "era", "period", "age", chronology framing
    - Examples: "Imperial Era", "High Republic Era", "Old Republic"

12. **Concept** - Abstract ideas, systems, philosophies, technologies as concepts, doctrines
    - Cues: definitions, principles, mechanics, applications, NOT a single place/person/event
    - Examples: "The Force", "Hyperspace", "Dark side", "Lightsaber combat"

13. **TechnicalSitePage** - Wiki infrastructure: templates, categories, policies, help pages, guidelines
    - Cues: wiki policy language, template syntax, editing instructions, non-universe content
    - Examples: "Template:Character infobox", "Wookieepedia:Policy", "Help:Editing"

14. **Unknown** - ONLY if none of the above apply with any confidence
    - Explain in notes.why_primary_type why no category fits

WORK MEDIA METADATA:
- If primary_type == "WorkMedia", you MUST populate:
  - work_medium: film|tv|game|book|comic|reference|episode|short|other|unknown
  - canon_context: canon|legends|both|unknown
- If primary_type != "WorkMedia", set both to null

DESCRIPTOR_SENTENCE RULES:
- Exactly ONE sentence, maximum 50 words
- Plain text only (no citations, links, wikitext, HTML, brackets, or markup)
- Summarize what this entity/page is

CONFIDENCE CALIBRATION:
- 0.90-1.00: title + excerpt clearly match one entity type
- 0.70-0.89: mostly clear, minor ambiguity
- 0.40-0.69: uncertain; set needs_review=true
- <0.40: very uncertain; set needs_review=true

TAGS:
- Mix of Public (user-facing) and Hidden (internal retrieval) tags
- Keep tags short and human-readable
- Hidden tags can include classifier assists (e.g., "biography", "list-like", "disambiguation-risk")

NOISE HANDLING:
Treat the following as noise unless helpful for type inference:
- Citations and reference markup
- Link targets / URLs
- Template names and policy flags
- Navigation elements and issue lists
If excerpt is noisy/markup-heavy, note it in notes.ignored_noise and set needs_review=true.
"""


def build_user_message(
    title: str,
    namespace: str,
    continuity_hint: str,
    excerpt_text: str,
    source_system: str = None,
    resource_id: str = None,
) -> str:
    """
    Build the user message for page classification.
    
    Uses a clean input envelope format instead of embedding raw payloads.
    
    Args:
        title: Page title
        namespace: Wiki namespace (Main, Module, Forum, etc.)
        continuity_hint: Continuity (Canon, Legends, Unknown)
        excerpt_text: Bounded excerpt from the article (already cleaned)
        source_system: Optional source system for traceability
        resource_id: Optional resource ID for traceability
        
    Returns:
        JSON-formatted user message string
    """
    import json
    
    envelope = {
        "title": title,
        "namespace": namespace,
        "continuity_hint": continuity_hint,
        "excerpt_text": excerpt_text,
    }
    
    # Add optional traceability hints
    if source_system:
        envelope["source_system"] = source_system
    if resource_id:
        envelope["resource_id"] = resource_id
    
    return json.dumps(envelope, ensure_ascii=False)


def build_messages(
    title: str,
    namespace: str,
    continuity_hint: str,
    excerpt_text: str,
    source_system: str = None,
    resource_id: str = None,
) -> list:
    """
    Build the complete messages list for the classification call.
    
    Args:
        title: Page title
        namespace: Wiki namespace
        continuity_hint: Continuity hint
        excerpt_text: Bounded excerpt
        source_system: Optional source system
        resource_id: Optional resource ID
        
    Returns:
        List of message dicts for the LLM call
    """
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": build_user_message(
                title=title,
                namespace=namespace,
                continuity_hint=continuity_hint,
                excerpt_text=excerpt_text,
                source_system=source_system,
                resource_id=resource_id,
            ),
        },
    ]
