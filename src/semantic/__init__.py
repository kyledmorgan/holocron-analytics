"""
Semantic Staging Module

This module provides the semantic staging pipeline for classifying ingested pages
and preparing them for promotion to the dimensional model.

The pipeline consists of three stages:
1. Stage 0 - Title-only routing (rules-based classification)
2. Stage 1 - Minimal peek into payload (signals extraction)
3. Stage 2 - LLM classification (Ollama local)
4. Stage 3 - Promotion workflow (manual adjudication)
"""

from .models import (
    SourcePage,
    PageSignals,
    PageClassification,
    PageClassificationResult,
    PromotionState,
    ClassificationMethod,
    PageType,
    Namespace,
    ContinuityHint,
)

from .rules_classifier import RulesClassifier
from .signals_extractor import SignalsExtractor
from .page_router import PageRouter
from .store import SemanticStagingStore

__all__ = [
    # Models
    'SourcePage',
    'PageSignals',
    'PageClassification',
    'PageClassificationResult',
    'PromotionState',
    'ClassificationMethod',
    'PageType',
    'Namespace',
    'ContinuityHint',
    # Classifiers
    'RulesClassifier',
    'SignalsExtractor',
    'PageRouter',
    # Store
    'SemanticStagingStore',
]
