"""
Core data models for the semantic staging module.

Uses dataclasses following the pattern established in src/ingest/core/models.py.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class PromotionState(str, Enum):
    """Promotion state for entities derived from page classification."""
    STAGED = "staged"
    CANDIDATE = "candidate"
    ADJUDICATED = "adjudicated"
    PROMOTED = "promoted"
    SUPPRESSED = "suppressed"
    MERGED = "merged"


class ClassificationMethod(str, Enum):
    """Method used for page classification."""
    RULES = "rules"
    LLM = "llm"
    HYBRID = "hybrid"
    MANUAL = "manual"


class PageType(str, Enum):
    """
    Primary type taxonomy for page classification (v1).
    
    This taxonomy is designed for initial classification of wiki pages.
    """
    # In-universe entities
    PERSON_CHARACTER = "PersonCharacter"
    LOCATION_PLACE = "LocationPlace"
    WORK_MEDIA = "WorkMedia"
    EVENT_CONFLICT = "EventConflict"
    CONCEPT = "Concept"
    ORGANIZATION = "Organization"
    SPECIES = "Species"
    TECHNOLOGY = "Technology"
    VEHICLE = "Vehicle"
    WEAPON = "Weapon"
    
    # Meta/reference content
    META_REFERENCE = "MetaReference"
    TIME_PERIOD = "TimePeriod"
    
    # Site/technical pages
    TECHNICAL_SITE_PAGE = "TechnicalSitePage"
    
    # Unknown/ambiguous
    UNKNOWN = "Unknown"


class Namespace(str, Enum):
    """
    Wiki namespace detected from page title.
    """
    MAIN = "main"
    USER = "user"
    USER_TALK = "user_talk"
    FORUM = "forum"
    MODULE = "module"
    TEMPLATE = "template"
    CATEGORY = "category"
    FILE = "file"
    WOOKIEEPEDIA = "wookieepedia"
    HELP = "help"
    MEDIAWIKI = "mediawiki"
    OTHER = "other"


class ContinuityHint(str, Enum):
    """Continuity hint detected from page title or metadata."""
    CANON = "canon"
    LEGENDS = "legends"
    UNKNOWN = "unknown"


@dataclass
class SourcePage:
    """
    Represents a page identity derived from ingest + registry.
    
    Bridges to:
      - Latest fetch: ingest.IngestRecords.ingest_id
      - Optional indexing: llm.source_registry.source_id
    
    Attributes:
        source_page_id: Unique identifier for this source page
        source_system: Source system (e.g., 'wookieepedia')
        resource_id: Page title / resource identifier
        variant: Content variant (raw, html)
        namespace: Detected wiki namespace
        continuity_hint: Detected continuity (canon, legends, unknown)
        content_hash_sha256: SHA256 hash of content for deduplication
        latest_ingest_id: Reference to latest ingest record
        source_registry_id: Reference to llm.source_registry
        created_utc: When the page was first seen
        updated_utc: When the page was last updated
        is_active: Whether the page is still active
    """
    source_page_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_system: str = ""
    resource_id: str = ""
    variant: Optional[str] = None
    namespace: Optional[Namespace] = None
    continuity_hint: Optional[ContinuityHint] = None
    content_hash_sha256: Optional[str] = None
    latest_ingest_id: Optional[str] = None
    source_registry_id: Optional[str] = None
    created_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

    def get_key(self) -> str:
        """Generate a stable key for this source page."""
        base = f"{self.source_system}:{self.resource_id}"
        if self.variant:
            return f"{base}:{self.variant}"
        return base


@dataclass
class PageSignals:
    """
    Stores small extracted cues from pages (minimal content peek).
    
    Attributes:
        page_signals_id: Unique identifier
        source_page_id: Reference to source page
        content_hash_sha256: Hash of content when signals were extracted
        signals_version: Version number for incremental updates
        lead_sentence: First sentence or paragraph
        infobox_type: Type of infobox (if present)
        categories_json: Top categories as JSON array
        is_list_page: Whether this is a list page
        is_disambiguation: Whether this is a disambiguation page
        has_timeline_markers: Whether page has timeline markers
        has_infobox: Whether page has an infobox
        signals_json: Additional signals as JSON
        extracted_utc: When signals were extracted
        extraction_method: Method used for extraction
        extraction_duration_ms: Time taken to extract
        is_current: Whether this is the current signals version
        content_format_detected: Detected content format (wikitext/html/unknown)
        content_start_strategy: Strategy used to find content start
        content_start_offset: Character offset where content starts
        lead_excerpt_text: Bounded excerpt used for LLM classification
        lead_excerpt_len: Length of the lead excerpt
        lead_excerpt_hash: SHA256 hash of the lead excerpt
    """
    page_signals_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_page_id: str = ""
    content_hash_sha256: Optional[str] = None
    signals_version: int = 1
    lead_sentence: Optional[str] = None
    infobox_type: Optional[str] = None
    categories_json: Optional[str] = None
    is_list_page: bool = False
    is_disambiguation: bool = False
    has_timeline_markers: bool = False
    has_infobox: bool = False
    signals_json: Optional[str] = None
    extracted_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    extraction_method: Optional[str] = None
    extraction_duration_ms: Optional[int] = None
    is_current: bool = True
    # Content extraction fields
    content_format_detected: Optional[str] = None
    content_start_strategy: Optional[str] = None
    content_start_offset: Optional[int] = None
    lead_excerpt_text: Optional[str] = None
    lead_excerpt_len: Optional[int] = None
    lead_excerpt_hash: Optional[str] = None

    @property
    def categories(self) -> List[str]:
        """Parse categories from JSON."""
        if not self.categories_json:
            return []
        import json
        try:
            return json.loads(self.categories_json)
        except (json.JSONDecodeError, TypeError):
            return []


@dataclass
class PageClassification:
    """
    Stores type inference and lineage for pages.
    
    Many rows over time per SourcePage (taxonomy_version + run lineage).
    
    Attributes:
        page_classification_id: Unique identifier
        source_page_id: Reference to source page
        taxonomy_version: Version of the classification taxonomy
        primary_type: Primary classification result
        type_set_json: Multi-label classification with weights as JSON
        confidence_score: Confidence in the classification (0.0 to 1.0)
        method: Classification method used
        model_name: Model used (if LLM)
        prompt_version: Prompt version used (if LLM)
        run_id: Reference to llm.run (if LLM)
        evidence_json: Explainability data as JSON
        rationale: Human-readable rationale
        needs_review: Whether manual review is needed
        review_notes: Notes from review
        suggested_tags_json: Suggested tags as JSON
        created_utc: When classification was performed
        is_current: Whether this is the current classification
        superseded_by_id: ID of classification that supersedes this one
        descriptor_sentence: LLM-generated single sentence descriptor (<= 50 words)
    """
    page_classification_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_page_id: str = ""
    taxonomy_version: str = "v1"
    primary_type: PageType = PageType.UNKNOWN
    type_set_json: Optional[str] = None
    confidence_score: Optional[Decimal] = None
    method: ClassificationMethod = ClassificationMethod.RULES
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None
    run_id: Optional[str] = None
    evidence_json: Optional[str] = None
    rationale: Optional[str] = None
    needs_review: bool = False
    review_notes: Optional[str] = None
    suggested_tags_json: Optional[str] = None
    created_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_current: bool = True
    superseded_by_id: Optional[str] = None
    descriptor_sentence: Optional[str] = None

    @property
    def type_set(self) -> Dict[str, float]:
        """Parse type set from JSON."""
        if not self.type_set_json:
            return {}
        import json
        try:
            return json.loads(self.type_set_json)
        except (json.JSONDecodeError, TypeError):
            return {}

    @property
    def suggested_tags(self) -> List[str]:
        """Parse suggested tags from JSON."""
        if not self.suggested_tags_json:
            return []
        import json
        try:
            return json.loads(self.suggested_tags_json)
        except (json.JSONDecodeError, TypeError):
            return []


@dataclass
class PageClassificationResult:
    """
    Result from running the page classification pipeline.
    
    Combines classification with metadata for downstream processing.
    """
    source_page: SourcePage
    signals: Optional[PageSignals]
    classification: PageClassification
    suggested_promotion_state: PromotionState = PromotionState.STAGED
    suggested_tags: List[str] = field(default_factory=list)
    
    @property
    def should_create_entity(self) -> bool:
        """Determine if an entity should be created for this page."""
        # Don't create entities for technical/meta pages
        if self.classification.primary_type in (
            PageType.TECHNICAL_SITE_PAGE,
            PageType.META_REFERENCE,
        ):
            return False
        return True
    
    @property
    def should_suppress(self) -> bool:
        """Determine if this page should be suppressed from promotion."""
        return self.classification.primary_type == PageType.TECHNICAL_SITE_PAGE


@dataclass
class TypeWeight:
    """A type with its weight/probability."""
    page_type: PageType
    weight: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.page_type.value,
            "weight": self.weight
        }
