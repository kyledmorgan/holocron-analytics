#!/usr/bin/env python3
"""
CLI for running the semantic staging pipeline.

Usage:
    python -m src.semantic.cli --help
    python -m src.semantic.cli process --limit 100
    python -m src.semantic.cli classify "Anakin Skywalker"
"""

import argparse
import json
import logging
import sys
from typing import Optional

from .models import PageType, PromotionState
from .page_router import PageRouter
from .rules_classifier import RulesClassifier


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def cmd_classify(args: argparse.Namespace) -> int:
    """Run classification on a single title."""
    classifier = RulesClassifier()
    result = classifier.classify(args.title)
    
    print(f"\nClassification for: {args.title}")
    print("=" * 50)
    print(f"Namespace:      {result.namespace.value}")
    print(f"Continuity:     {result.continuity_hint.value}")
    print(f"Primary Type:   {result.primary_type.value}")
    print(f"Confidence:     {result.confidence}")
    print(f"Is Complete:    {result.is_complete}")
    print(f"Rationale:      {result.rationale}")
    print(f"Suggested Tags: {', '.join(result.suggested_tags)}")
    
    if args.json:
        output = {
            "title": args.title,
            "namespace": result.namespace.value,
            "continuity_hint": result.continuity_hint.value,
            "primary_type": result.primary_type.value,
            "confidence": float(result.confidence),
            "is_complete": result.is_complete,
            "rationale": result.rationale,
            "suggested_tags": result.suggested_tags,
        }
        print("\nJSON output:")
        print(json.dumps(output, indent=2))
    
    return 0


def cmd_batch_classify(args: argparse.Namespace) -> int:
    """Run classification on multiple titles from a file."""
    classifier = RulesClassifier()
    
    with open(args.file, 'r', encoding='utf-8') as f:
        titles = [line.strip() for line in f if line.strip()]
    
    results = []
    type_counts = {}
    
    for title in titles:
        result = classifier.classify(title)
        
        type_key = result.primary_type.value
        type_counts[type_key] = type_counts.get(type_key, 0) + 1
        
        results.append({
            "title": title,
            "namespace": result.namespace.value,
            "continuity_hint": result.continuity_hint.value,
            "primary_type": result.primary_type.value,
            "confidence": float(result.confidence),
            "is_complete": result.is_complete,
        })
    
    # Print summary
    print(f"\nClassified {len(titles)} titles")
    print("=" * 50)
    print("\nType distribution:")
    for type_name, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        pct = 100 * count / len(titles)
        print(f"  {type_name}: {count} ({pct:.1f}%)")
    
    # Output results
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults written to {args.output}")
    
    return 0


def cmd_taxonomy(args: argparse.Namespace) -> int:
    """Show the page type taxonomy."""
    print("\nPage Type Taxonomy (v1)")
    print("=" * 50)
    
    categories = {
        "In-Universe Entities": [
            PageType.PERSON_CHARACTER,
            PageType.LOCATION_PLACE,
            PageType.ORGANIZATION,
            PageType.SPECIES,
            PageType.TECHNOLOGY,
            PageType.VEHICLE,
            PageType.WEAPON,
        ],
        "Narrative Elements": [
            PageType.EVENT_CONFLICT,
            PageType.CONCEPT,
            PageType.WORK_MEDIA,
        ],
        "Meta/Reference": [
            PageType.META_REFERENCE,
            PageType.TIME_PERIOD,
        ],
        "Technical": [
            PageType.TECHNICAL_SITE_PAGE,
            PageType.UNKNOWN,
        ],
    }
    
    for category, types in categories.items():
        print(f"\n{category}:")
        for pt in types:
            print(f"  - {pt.value}")
    
    return 0


def cmd_promotion_states(args: argparse.Namespace) -> int:
    """Show the promotion state definitions."""
    print("\nPromotion States")
    print("=" * 50)
    
    states = {
        PromotionState.STAGED: "Initial state after classification. Entity exists but is not visible downstream.",
        PromotionState.CANDIDATE: "High-confidence classification ready for adjudication.",
        PromotionState.ADJUDICATED: "Human-reviewed and confirmed. Ready for promotion.",
        PromotionState.PROMOTED: "Fully promoted and visible in downstream views/marts.",
        PromotionState.SUPPRESSED: "Intentionally hidden (e.g., technical pages, duplicates).",
        PromotionState.MERGED: "Merged into another entity (deduplicated).",
    }
    
    for state, description in states.items():
        print(f"\n{state.value}:")
        print(f"  {description}")
    
    return 0


def main(argv: Optional[list] = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Semantic staging pipeline CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # classify command
    classify_parser = subparsers.add_parser(
        "classify", help="Classify a single page title"
    )
    classify_parser.add_argument("title", help="Page title to classify")
    classify_parser.add_argument("--json", action="store_true", help="Output JSON")
    classify_parser.set_defaults(func=cmd_classify)
    
    # batch-classify command
    batch_parser = subparsers.add_parser(
        "batch-classify", help="Classify multiple titles from a file"
    )
    batch_parser.add_argument("file", help="File with one title per line")
    batch_parser.add_argument("-o", "--output", help="Output JSON file")
    batch_parser.set_defaults(func=cmd_batch_classify)
    
    # taxonomy command
    taxonomy_parser = subparsers.add_parser(
        "taxonomy", help="Show the page type taxonomy"
    )
    taxonomy_parser.set_defaults(func=cmd_taxonomy)
    
    # promotion-states command
    states_parser = subparsers.add_parser(
        "promotion-states", help="Show promotion state definitions"
    )
    states_parser.set_defaults(func=cmd_promotion_states)
    
    args = parser.parse_args(argv)
    
    setup_logging(args.verbose)
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
