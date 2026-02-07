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

CLASSIFICATION RULES:
1. primary_type: Choose from the enum list. Use "Other" only if no enum fits.
2. If the entity is a specialized subtype not yet modeled (e.g., droid type, starfighter class):
   - Choose the closest broad primary_type (often ObjectArtifact, Species, Organization, or Concept)
   - Set notes.likely_subtype with the precise label
   - Add to notes.new_type_suggestions
   - Optionally add to secondary_types with is_candidate_new_type=true

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
