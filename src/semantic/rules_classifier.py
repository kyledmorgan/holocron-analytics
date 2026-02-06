"""
Rules-based classifier for page classification (Stage 0).

Uses title patterns to classify pages without reading the payload.
This is the cheapest and fastest classification method.
"""

import re
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from .models import (
    ClassificationMethod,
    ContinuityHint,
    Namespace,
    PageClassification,
    PageType,
    SourcePage,
    TypeWeight,
)

logger = logging.getLogger(__name__)


# Namespace prefix patterns
NAMESPACE_PREFIXES: Dict[str, Namespace] = {
    "User:": Namespace.USER,
    "User talk:": Namespace.USER_TALK,
    "Forum:": Namespace.FORUM,
    "Module:": Namespace.MODULE,
    "Template:": Namespace.TEMPLATE,
    "Category:": Namespace.CATEGORY,
    "File:": Namespace.FILE,
    "Wookieepedia:": Namespace.WOOKIEEPEDIA,
    "Help:": Namespace.HELP,
    "MediaWiki:": Namespace.MEDIAWIKI,
}

# Technical namespace prefixes that should be classified as TechnicalSitePage
TECHNICAL_NAMESPACES = {
    Namespace.USER,
    Namespace.USER_TALK,
    Namespace.MODULE,
    Namespace.TEMPLATE,
    Namespace.MEDIAWIKI,
    Namespace.HELP,
    Namespace.WOOKIEEPEDIA,
}


@dataclass
class RulesClassifierConfig:
    """Configuration for the rules classifier."""
    # Minimum confidence threshold for rules-based classification
    min_confidence: Decimal = Decimal("0.7")
    # Whether to detect continuity from /Legends suffix
    detect_legends_suffix: bool = True
    # Whether to detect meta/reference pages
    detect_meta_pages: bool = True
    # Whether to detect time period pages
    detect_time_periods: bool = True


@dataclass
class RulesClassificationResult:
    """Result from rules-based classification."""
    primary_type: PageType
    confidence: Decimal
    namespace: Namespace
    continuity_hint: ContinuityHint
    type_weights: List[TypeWeight] = field(default_factory=list)
    rationale: str = ""
    suggested_tags: List[str] = field(default_factory=list)
    is_complete: bool = False  # True if rules provide complete classification


class RulesClassifier:
    """
    Rules-based classifier for page classification.
    
    Uses title patterns to infer:
    - Namespace (from prefix)
    - Continuity hint (from /Legends suffix)
    - Primary type (from title patterns)
    - Suggested tags (namespace, continuity, type)
    
    Example usage:
        >>> classifier = RulesClassifier()
        >>> result = classifier.classify("Module:ArchiveAccess/SW")
        >>> result.primary_type
        PageType.TECHNICAL_SITE_PAGE
        >>> result.namespace
        Namespace.MODULE
    """
    
    def __init__(self, config: Optional[RulesClassifierConfig] = None):
        self.config = config or RulesClassifierConfig()
        
        # Compile regex patterns
        self._time_period_pattern = re.compile(
            r'^(\d+)\s*(BBY|ABY)$', re.IGNORECASE
        )
        self._list_pattern = re.compile(
            r'^List of\s+', re.IGNORECASE
        )
        self._timeline_pattern = re.compile(
            r'^Timeline\s+(of|:)', re.IGNORECASE
        )
        
    def classify(self, title: str) -> RulesClassificationResult:
        """
        Classify a page based on its title alone.
        
        Args:
            title: The page title to classify
            
        Returns:
            RulesClassificationResult with classification and metadata
        """
        # Extract namespace
        namespace, base_title = self._extract_namespace(title)
        
        # Detect continuity hint
        continuity_hint, base_title = self._detect_continuity(base_title)
        
        # Initialize result
        result = RulesClassificationResult(
            primary_type=PageType.UNKNOWN,
            confidence=Decimal("0.0"),
            namespace=namespace,
            continuity_hint=continuity_hint,
            type_weights=[],
            rationale="",
            suggested_tags=[],
            is_complete=False,
        )
        
        # Add namespace tag
        result.suggested_tags.append(f"namespace:{namespace.value}")
        
        # Add continuity tag
        if continuity_hint != ContinuityHint.UNKNOWN:
            result.suggested_tags.append(f"continuity:{continuity_hint.value}")
        
        # Classify based on namespace first
        if namespace in TECHNICAL_NAMESPACES:
            result.primary_type = PageType.TECHNICAL_SITE_PAGE
            result.confidence = Decimal("1.0")
            result.rationale = f"Technical namespace: {namespace.value}"
            result.is_complete = True
            result.suggested_tags.append("type:technical_site_page")
            return result
        
        # Forum namespace
        if namespace == Namespace.FORUM:
            result.primary_type = PageType.TECHNICAL_SITE_PAGE
            result.confidence = Decimal("0.95")
            result.rationale = "Forum namespace"
            result.is_complete = True
            result.suggested_tags.append("type:technical_site_page")
            return result
        
        # Category namespace
        if namespace == Namespace.CATEGORY:
            result.primary_type = PageType.META_REFERENCE
            result.confidence = Decimal("0.90")
            result.rationale = "Category namespace"
            result.is_complete = True
            result.suggested_tags.append("type:meta_reference")
            result.suggested_tags.append("meta:category")
            return result
        
        # File namespace
        if namespace == Namespace.FILE:
            result.primary_type = PageType.META_REFERENCE
            result.confidence = Decimal("0.85")
            result.rationale = "File namespace"
            result.is_complete = True
            result.suggested_tags.append("type:meta_reference")
            result.suggested_tags.append("meta:file")
            return result
        
        # Check for meta/reference patterns in main namespace
        if self.config.detect_meta_pages:
            meta_result = self._detect_meta_patterns(base_title)
            if meta_result:
                result.primary_type = meta_result[0]
                result.confidence = meta_result[1]
                result.rationale = meta_result[2]
                result.suggested_tags.extend(meta_result[3])
                result.is_complete = meta_result[1] >= self.config.min_confidence
                return result
        
        # Check for time period patterns
        if self.config.detect_time_periods:
            time_result = self._detect_time_period(base_title)
            if time_result:
                result.primary_type = time_result[0]
                result.confidence = time_result[1]
                result.rationale = time_result[2]
                result.suggested_tags.extend(time_result[3])
                result.is_complete = True
                return result
        
        # If we reach here, we need more context (signals/LLM)
        result.primary_type = PageType.UNKNOWN
        result.confidence = Decimal("0.0")
        result.rationale = "Title patterns inconclusive; requires signals extraction"
        
        return result
    
    def _extract_namespace(self, title: str) -> Tuple[Namespace, str]:
        """
        Extract namespace from title prefix.
        
        Returns (namespace, remaining_title).
        """
        for prefix, namespace in NAMESPACE_PREFIXES.items():
            if title.startswith(prefix):
                return namespace, title[len(prefix):]
        
        return Namespace.MAIN, title
    
    def _detect_continuity(self, title: str) -> Tuple[ContinuityHint, str]:
        """
        Detect continuity hint from title suffix.
        
        Returns (continuity_hint, title_without_suffix).
        """
        if not self.config.detect_legends_suffix:
            return ContinuityHint.UNKNOWN, title
        
        if title.endswith("/Legends"):
            return ContinuityHint.LEGENDS, title[:-8]
        
        if title.endswith("/Canon"):
            return ContinuityHint.CANON, title[:-6]
        
        return ContinuityHint.UNKNOWN, title
    
    def _detect_meta_patterns(
        self, title: str
    ) -> Optional[Tuple[PageType, Decimal, str, List[str]]]:
        """
        Detect meta/reference page patterns.
        
        Returns (type, confidence, rationale, tags) or None.
        """
        # Timeline pages
        if self._timeline_pattern.match(title):
            return (
                PageType.META_REFERENCE,
                Decimal("0.95"),
                "Title starts with 'Timeline'",
                ["type:meta_reference", "meta:timeline"],
            )
        
        # List pages
        if self._list_pattern.match(title):
            return (
                PageType.META_REFERENCE,
                Decimal("0.90"),
                "Title starts with 'List of'",
                ["type:meta_reference", "meta:list"],
            )
        
        # Behind the scenes / production pages
        if title.endswith("/Behind the scenes"):
            return (
                PageType.META_REFERENCE,
                Decimal("0.90"),
                "Behind the scenes page",
                ["type:meta_reference", "meta:production"],
            )
        
        # Appearances pages
        if title.endswith("/Appearances"):
            return (
                PageType.META_REFERENCE,
                Decimal("0.85"),
                "Appearances list page",
                ["type:meta_reference", "meta:appearances"],
            )
        
        return None
    
    def _detect_time_period(
        self, title: str
    ) -> Optional[Tuple[PageType, Decimal, str, List[str]]]:
        """
        Detect time period pages (e.g., "19 BBY", "4 ABY").
        
        Returns (type, confidence, rationale, tags) or None.
        """
        match = self._time_period_pattern.match(title.strip())
        if match:
            year = match.group(1)
            era = match.group(2).upper()
            return (
                PageType.TIME_PERIOD,
                Decimal("0.95"),
                f"Time period: {year} {era}",
                ["type:time_period", f"era:{era.lower()}"],
            )
        
        return None
    
    def create_classification(
        self,
        source_page: SourcePage,
        result: RulesClassificationResult,
    ) -> PageClassification:
        """
        Create a PageClassification from a RulesClassificationResult.
        
        Args:
            source_page: The source page being classified
            result: The rules classification result
            
        Returns:
            A PageClassification instance
        """
        import json
        
        type_set = {}
        for tw in result.type_weights:
            type_set[tw.page_type.value] = tw.weight
        if result.primary_type != PageType.UNKNOWN:
            type_set[result.primary_type.value] = float(result.confidence)
        
        return PageClassification(
            source_page_id=source_page.source_page_id,
            taxonomy_version="v1",
            primary_type=result.primary_type,
            type_set_json=json.dumps(type_set) if type_set else None,
            confidence_score=result.confidence,
            method=ClassificationMethod.RULES,
            model_name=None,
            prompt_version=None,
            run_id=None,
            evidence_json=json.dumps({
                "namespace": result.namespace.value,
                "continuity_hint": result.continuity_hint.value,
                "title": source_page.resource_id,
            }),
            rationale=result.rationale,
            needs_review=not result.is_complete,
            suggested_tags_json=json.dumps(result.suggested_tags),
        )
