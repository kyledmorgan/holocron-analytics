"""
Page router for coordinating the semantic staging pipeline.

Orchestrates the classification stages:
1. Rules classification (Stage 0)
2. Signals extraction (Stage 1)
3. LLM classification enqueue (Stage 2)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from .models import (
    ClassificationMethod,
    ContinuityHint,
    Namespace,
    PageClassification,
    PageClassificationResult,
    PageSignals,
    PageType,
    PromotionState,
    SourcePage,
)
from .rules_classifier import RulesClassifier, RulesClassificationResult
from .signals_extractor import SignalsExtractor

logger = logging.getLogger(__name__)


@dataclass
class PageRouterConfig:
    """Configuration for the page router."""
    # Confidence threshold for accepting rules-only classification
    rules_confidence_threshold: Decimal = Decimal("0.80")
    # Whether to run signals extraction for all pages
    always_extract_signals: bool = True
    # Confidence threshold for promoting to candidate
    candidate_confidence_threshold: Decimal = Decimal("0.75")
    # Types that should never be auto-promoted
    suppress_types: Tuple[PageType, ...] = (
        PageType.TECHNICAL_SITE_PAGE,
    )
    # Types that skip entity creation
    skip_entity_types: Tuple[PageType, ...] = (
        PageType.TECHNICAL_SITE_PAGE,
        PageType.META_REFERENCE,
    )
    # Maximum categories to include in evidence/LLM input
    max_categories_evidence: int = 5
    # Maximum categories for LLM input
    max_categories_llm_input: int = 10


class PageRouter:
    """
    Routes pages through the semantic staging pipeline.
    
    The router coordinates:
    1. Rules-based classification (always runs first)
    2. Signals extraction (if rules are inconclusive or always_extract_signals=True)
    3. LLM classification enqueue (if more context needed and confidence too low)
    
    Example usage:
        >>> router = PageRouter()
        >>> result = router.process_page(source_page, payload)
        >>> if result.needs_llm_classification:
        ...     # Enqueue for LLM processing
        ...     pass
        >>> else:
        ...     # Classification is complete
        ...     print(result.classification.primary_type)
    """
    
    def __init__(
        self,
        config: Optional[PageRouterConfig] = None,
        rules_classifier: Optional[RulesClassifier] = None,
        signals_extractor: Optional[SignalsExtractor] = None,
    ):
        self.config = config or PageRouterConfig()
        self.rules_classifier = rules_classifier or RulesClassifier()
        self.signals_extractor = signals_extractor or SignalsExtractor()
    
    def process_page(
        self,
        source_page: SourcePage,
        payload: Optional[Any] = None,
        content_type: Optional[str] = None,
    ) -> PageRoutingResult:
        """
        Process a page through the classification pipeline.
        
        Args:
            source_page: The source page to process
            payload: Optional page payload for signals extraction
            content_type: Optional content type hint
            
        Returns:
            PageRoutingResult with classification and routing decision
        """
        # Stage 0: Rules classification
        rules_result = self.rules_classifier.classify(source_page.resource_id)
        
        # Update source page with detected namespace and continuity
        source_page.namespace = rules_result.namespace
        source_page.continuity_hint = rules_result.continuity_hint
        
        # Check if rules provide complete classification
        if rules_result.is_complete and rules_result.confidence >= self.config.rules_confidence_threshold:
            classification = self.rules_classifier.create_classification(
                source_page, rules_result
            )
            
            return PageRoutingResult(
                source_page=source_page,
                signals=None,
                classification=classification,
                rules_result=rules_result,
                suggested_promotion_state=self._get_promotion_state(
                    classification, None
                ),
                suggested_tags=rules_result.suggested_tags,
                needs_llm_classification=False,
                routing_decision="rules_complete",
            )
        
        # Stage 1: Signals extraction (if payload available)
        signals = None
        if payload is not None and (
            self.config.always_extract_signals or not rules_result.is_complete
        ):
            signals = self.signals_extractor.extract(
                source_page, payload, content_type
            )
        
        # Use signals to enhance classification if available
        if signals:
            enhanced_result = self._enhance_with_signals(
                source_page, rules_result, signals
            )
            
            if enhanced_result.is_complete:
                classification = self._create_hybrid_classification(
                    source_page, enhanced_result, signals
                )
                
                return PageRoutingResult(
                    source_page=source_page,
                    signals=signals,
                    classification=classification,
                    rules_result=rules_result,
                    suggested_promotion_state=self._get_promotion_state(
                        classification, signals
                    ),
                    suggested_tags=enhanced_result.suggested_tags,
                    needs_llm_classification=False,
                    routing_decision="signals_enhanced",
                )
        
        # Need LLM classification for better confidence
        classification = self._create_preliminary_classification(
            source_page, rules_result, signals
        )
        
        return PageRoutingResult(
            source_page=source_page,
            signals=signals,
            classification=classification,
            rules_result=rules_result,
            suggested_promotion_state=PromotionState.STAGED,
            suggested_tags=rules_result.suggested_tags,
            needs_llm_classification=True,
            routing_decision="needs_llm",
        )
    
    def _enhance_with_signals(
        self,
        source_page: SourcePage,
        rules_result: RulesClassificationResult,
        signals: PageSignals,
    ) -> RulesClassificationResult:
        """
        Enhance rules result using extracted signals.
        
        Uses infobox type and categories to improve classification.
        """
        # Clone the result
        enhanced = RulesClassificationResult(
            primary_type=rules_result.primary_type,
            confidence=rules_result.confidence,
            namespace=rules_result.namespace,
            continuity_hint=rules_result.continuity_hint,
            type_weights=rules_result.type_weights.copy(),
            rationale=rules_result.rationale,
            suggested_tags=rules_result.suggested_tags.copy(),
            is_complete=rules_result.is_complete,
        )
        
        # Use infobox type to infer page type
        if signals.infobox_type:
            infobox_lower = signals.infobox_type.lower()
            
            type_mapping = {
                "character": PageType.PERSON_CHARACTER,
                "person": PageType.PERSON_CHARACTER,
                "individual": PageType.PERSON_CHARACTER,
                "location": PageType.LOCATION_PLACE,
                "planet": PageType.LOCATION_PLACE,
                "place": PageType.LOCATION_PLACE,
                "system": PageType.LOCATION_PLACE,
                "event": PageType.EVENT_CONFLICT,
                "battle": PageType.EVENT_CONFLICT,
                "conflict": PageType.EVENT_CONFLICT,
                "war": PageType.EVENT_CONFLICT,
                "film": PageType.WORK_MEDIA,
                "movie": PageType.WORK_MEDIA,
                "book": PageType.WORK_MEDIA,
                "novel": PageType.WORK_MEDIA,
                "comic": PageType.WORK_MEDIA,
                "game": PageType.WORK_MEDIA,
                "organization": PageType.ORGANIZATION,
                "faction": PageType.ORGANIZATION,
                "species": PageType.SPECIES,
                "technology": PageType.TECHNOLOGY,
                "starship": PageType.VEHICLE,
                "vehicle": PageType.VEHICLE,
                "weapon": PageType.WEAPON,
            }
            
            for key, page_type in type_mapping.items():
                if key in infobox_lower:
                    enhanced.primary_type = page_type
                    enhanced.confidence = Decimal("0.85")
                    enhanced.rationale = f"Infobox type suggests {page_type.value}"
                    enhanced.is_complete = True
                    enhanced.suggested_tags.append(f"type:{page_type.value.lower()}")
                    enhanced.suggested_tags.append(f"infobox:{signals.infobox_type.lower()}")
                    break
        
        # Check categories for additional hints
        if signals.categories:
            categories_lower = [c.lower() for c in signals.categories]
            
            # Character indicators
            if any(c for c in categories_lower if "character" in c or "individual" in c):
                if enhanced.primary_type == PageType.UNKNOWN:
                    enhanced.primary_type = PageType.PERSON_CHARACTER
                    enhanced.confidence = Decimal("0.70")
                    enhanced.rationale = "Categories suggest character page"
                    enhanced.is_complete = True
            
            # Location indicators
            if any(c for c in categories_lower if "planet" in c or "location" in c):
                if enhanced.primary_type == PageType.UNKNOWN:
                    enhanced.primary_type = PageType.LOCATION_PLACE
                    enhanced.confidence = Decimal("0.70")
                    enhanced.rationale = "Categories suggest location page"
                    enhanced.is_complete = True
        
        # Disambiguation check
        if signals.is_disambiguation:
            enhanced.primary_type = PageType.META_REFERENCE
            enhanced.confidence = Decimal("0.95")
            enhanced.rationale = "Page is disambiguation"
            enhanced.is_complete = True
            enhanced.suggested_tags.append("meta:disambiguation")
        
        return enhanced
    
    def _create_hybrid_classification(
        self,
        source_page: SourcePage,
        result: RulesClassificationResult,
        signals: PageSignals,
    ) -> PageClassification:
        """Create a classification using hybrid (rules + signals) method."""
        type_set = {}
        for tw in result.type_weights:
            type_set[tw.page_type.value] = tw.weight
        if result.primary_type != PageType.UNKNOWN:
            type_set[result.primary_type.value] = float(result.confidence)
        
        evidence = {
            "namespace": result.namespace.value,
            "continuity_hint": result.continuity_hint.value,
            "title": source_page.resource_id,
            "infobox_type": signals.infobox_type,
            "categories": signals.categories[:self.config.max_categories_evidence] if signals.categories else [],
            "is_disambiguation": signals.is_disambiguation,
            "is_list_page": signals.is_list_page,
        }
        
        return PageClassification(
            source_page_id=source_page.source_page_id,
            taxonomy_version="v1",
            primary_type=result.primary_type,
            type_set_json=json.dumps(type_set) if type_set else None,
            confidence_score=result.confidence,
            method=ClassificationMethod.HYBRID,
            evidence_json=json.dumps(evidence),
            rationale=result.rationale,
            needs_review=not result.is_complete or result.confidence < Decimal("0.70"),
            suggested_tags_json=json.dumps(result.suggested_tags),
        )
    
    def _create_preliminary_classification(
        self,
        source_page: SourcePage,
        rules_result: RulesClassificationResult,
        signals: Optional[PageSignals],
    ) -> PageClassification:
        """Create a preliminary classification pending LLM enhancement."""
        evidence = {
            "namespace": rules_result.namespace.value,
            "continuity_hint": rules_result.continuity_hint.value,
            "title": source_page.resource_id,
            "stage": "preliminary",
        }
        
        if signals:
            evidence["infobox_type"] = signals.infobox_type
            evidence["has_categories"] = bool(signals.categories)
        
        return PageClassification(
            source_page_id=source_page.source_page_id,
            taxonomy_version="v1",
            primary_type=rules_result.primary_type,
            type_set_json=None,
            confidence_score=rules_result.confidence,
            method=ClassificationMethod.RULES,
            evidence_json=json.dumps(evidence),
            rationale=rules_result.rationale + " (preliminary, awaiting LLM)",
            needs_review=True,
            suggested_tags_json=json.dumps(rules_result.suggested_tags),
        )
    
    def _get_promotion_state(
        self,
        classification: PageClassification,
        signals: Optional[PageSignals],
    ) -> PromotionState:
        """Determine the suggested promotion state."""
        # Suppress technical pages
        if classification.primary_type in self.config.suppress_types:
            return PromotionState.SUPPRESSED
        
        # Low confidence needs review
        if classification.confidence_score and classification.confidence_score < self.config.candidate_confidence_threshold:
            return PromotionState.STAGED
        
        # High confidence non-technical pages can be candidates
        if classification.confidence_score and classification.confidence_score >= self.config.candidate_confidence_threshold:
            if classification.primary_type not in self.config.skip_entity_types:
                return PromotionState.CANDIDATE
        
        return PromotionState.STAGED


@dataclass
class PageRoutingResult:
    """Result from the page routing process."""
    source_page: SourcePage
    signals: Optional[PageSignals]
    classification: PageClassification
    rules_result: RulesClassificationResult
    suggested_promotion_state: PromotionState
    suggested_tags: List[str]
    needs_llm_classification: bool
    routing_decision: str
    
    def to_classification_result(self) -> PageClassificationResult:
        """Convert to PageClassificationResult for downstream use."""
        return PageClassificationResult(
            source_page=self.source_page,
            signals=self.signals,
            classification=self.classification,
            suggested_promotion_state=self.suggested_promotion_state,
            suggested_tags=self.suggested_tags,
        )
    
    def get_llm_input(self, max_categories: int = 10) -> Dict[str, Any]:
        """
        Get the input data for LLM classification.
        
        This is what gets sent to the LLM job queue.
        
        Args:
            max_categories: Maximum number of categories to include in input.
        """
        input_data = {
            "title": self.source_page.resource_id,
            "namespace": self.rules_result.namespace.value,
            "continuity_hint": self.rules_result.continuity_hint.value,
        }
        
        if self.signals:
            input_data["lead_sentence"] = self.signals.lead_sentence
            input_data["infobox_type"] = self.signals.infobox_type
            input_data["categories"] = self.signals.categories[:max_categories] if self.signals.categories else []
            input_data["is_list_page"] = self.signals.is_list_page
            input_data["is_disambiguation"] = self.signals.is_disambiguation
        
        return input_data
