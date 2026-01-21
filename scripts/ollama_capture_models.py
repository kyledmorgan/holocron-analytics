#!/usr/bin/env python3
"""
Ollama Model Inventory Capture Tool

Captures metadata about models available in Ollama and writes a JSON snapshot
for benchmarking preparation and model registry tracking.

Usage:
    python scripts/ollama_capture_models.py
    python scripts/ollama_capture_models.py --base-url http://192.168.1.100:11434
    python scripts/ollama_capture_models.py --output ./artifacts/ollama/models_snapshot.json

Environment Variables:
    LLM_BASE_URL: Ollama base URL (default: http://localhost:11434)

Exit Codes:
    0: Success
    1: Ollama unreachable or error

Output:
    JSON file with model inventory including:
    - model name
    - digest (content hash)
    - modified timestamp
    - size (bytes)
    - parameter size (e.g., "7B")
    - quantization level (e.g., "Q4_0")

Future Integration:
    TODO: This data will be persisted to derive.ModelRegistry table in SQL Server
    for tracking model versions used in LLM-derived data runs.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Default output location
DEFAULT_OUTPUT_DIR = Path("artifacts/ollama")
DEFAULT_OUTPUT_FILE = "models_snapshot.json"


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Capture Ollama model inventory to JSON"
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("LLM_BASE_URL", "http://localhost:11434"),
        help="Ollama base URL (default: http://localhost:11434)"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help=f"Output file path (default: {DEFAULT_OUTPUT_DIR / DEFAULT_OUTPUT_FILE})"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    return parser.parse_args()


def fetch_model_list(base_url: str, verbose: bool = False) -> list:
    """
    Fetch list of models from Ollama API.
    
    Args:
        base_url: Ollama base URL
        verbose: Enable verbose output
        
    Returns:
        List of model dictionaries from /api/tags endpoint
    """
    url = f"{base_url.rstrip('/')}/api/tags"
    
    if verbose:
        print(f"Fetching model list from: {url}")
    
    try:
        request = Request(url, method="GET")
        with urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("models", [])
    except HTTPError as e:
        print(f"HTTP error fetching model list: {e.code}", file=sys.stderr)
        raise
    except URLError as e:
        print(f"Failed to connect to Ollama at {base_url}: {e}", file=sys.stderr)
        raise


def fetch_model_details(base_url: str, model_name: str, verbose: bool = False) -> dict:
    """
    Fetch detailed information about a specific model.
    
    Args:
        base_url: Ollama base URL
        model_name: Name of the model to query
        verbose: Enable verbose output
        
    Returns:
        Dictionary with model details from /api/show endpoint
    """
    url = f"{base_url.rstrip('/')}/api/show"
    
    if verbose:
        print(f"  Fetching details for: {model_name}")
    
    try:
        payload = json.dumps({"name": model_name}).encode("utf-8")
        request = Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as e:
        if verbose:
            print(f"  Warning: Could not fetch details for {model_name}: {e.code}")
        return {}
    except URLError as e:
        if verbose:
            print(f"  Warning: Connection error for {model_name}: {e}")
        return {}


def parse_parameter_size(model_name: str, details: dict) -> str:
    """
    Extract parameter size from model name or details.
    
    Looks for patterns like "7b", "13b", "70b" in model name or modelfile.
    
    Args:
        model_name: Full model name (e.g., "llama3.2:7b")
        details: Model details from /api/show
        
    Returns:
        Parameter size string (e.g., "7B") or None if not found
    """
    # Try to extract from model name first (most reliable)
    name_lower = model_name.lower()
    
    # Common patterns: 7b, 13b, 70b, 3b, etc.
    match = re.search(r'(\d+(?:\.\d+)?)[bB]', model_name)
    if match:
        size = match.group(1)
        return f"{size}B"
    
    # Try to extract from modelfile in details
    modelfile = details.get("modelfile", "")
    if modelfile:
        match = re.search(r'(\d+(?:\.\d+)?)[bB]', modelfile)
        if match:
            size = match.group(1)
            return f"{size}B"
    
    return None


def parse_quantization(model_name: str, details: dict) -> str:
    """
    Extract quantization level from model name or details.
    
    Looks for patterns like "q4_0", "q8_0", "fp16" in model name or modelfile.
    
    Args:
        model_name: Full model name
        details: Model details from /api/show
        
    Returns:
        Quantization string (e.g., "Q4_0") or None if not found
    """
    # Common quantization patterns
    patterns = [
        r'(q[48]_[0kKmM])',      # q4_0, q8_0, q4_K, etc.
        r'(q[48]_[kKmM]_[smSM])', # q4_K_S, q4_K_M, etc.
        r'(fp16|fp32)',          # Full precision
        r'(int8|int4)',          # Integer quantization
    ]
    
    # Try model name first
    name_lower = model_name.lower()
    for pattern in patterns:
        match = re.search(pattern, name_lower)
        if match:
            return match.group(1).upper()
    
    # Try modelfile
    modelfile = details.get("modelfile", "").lower()
    for pattern in patterns:
        match = re.search(pattern, modelfile)
        if match:
            return match.group(1).upper()
    
    return None


def capture_model_inventory(base_url: str, verbose: bool = False) -> dict:
    """
    Capture complete model inventory from Ollama.
    
    Args:
        base_url: Ollama base URL
        verbose: Enable verbose output
        
    Returns:
        Dictionary with capture metadata and model list
    """
    capture_time = datetime.utcnow().isoformat() + "Z"
    
    # Fetch model list
    models = fetch_model_list(base_url, verbose)
    
    if verbose:
        print(f"Found {len(models)} models")
    
    # Enrich each model with additional details
    enriched_models = []
    for model in models:
        model_name = model.get("name", "unknown")
        
        # Fetch additional details
        details = fetch_model_details(base_url, model_name, verbose)
        
        # Build enriched record
        enriched = {
            "name": model_name,
            "digest": model.get("digest"),
            "modified_at": model.get("modified_at"),
            "size_bytes": model.get("size"),
            "parameter_size": parse_parameter_size(model_name, details),
            "quantization": parse_quantization(model_name, details),
            # Additional fields from details
            "format": details.get("details", {}).get("format"),
            "family": details.get("details", {}).get("family"),
            "parameter_size_from_api": details.get("details", {}).get("parameter_size"),
            "quantization_from_api": details.get("details", {}).get("quantization_level"),
        }
        
        enriched_models.append(enriched)
    
    return {
        "capture_timestamp": capture_time,
        "ollama_base_url": base_url,
        "model_count": len(enriched_models),
        "models": enriched_models,
        # TODO: Future integration with derive.ModelRegistry table
        # This snapshot can be loaded into SQL Server for tracking
        # which model versions were used in LLM-derived data runs.
        "_future_table": "derive.ModelRegistry",
    }


def main():
    """Main entry point."""
    args = parse_args()
    
    print("Ollama Model Inventory Capture")
    print("=" * 50)
    print(f"Base URL: {args.base_url}")
    
    try:
        # Capture inventory
        inventory = capture_model_inventory(args.base_url, args.verbose)
        
        print(f"Models found: {inventory['model_count']}")
        
        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = DEFAULT_OUTPUT_DIR / DEFAULT_OUTPUT_FILE
        
        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write snapshot
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(inventory, f, indent=2)
        
        print(f"Snapshot written to: {output_path}")
        
        # Summary
        print()
        print("Models captured:")
        for model in inventory["models"]:
            size = model.get("parameter_size") or model.get("parameter_size_from_api") or "?"
            quant = model.get("quantization") or model.get("quantization_from_api") or "?"
            print(f"  - {model['name']} ({size}, {quant})")
        
        print()
        print("=" * 50)
        print("✓ Capture complete")
        
        return 0
        
    except (HTTPError, URLError) as e:
        print(f"\n❌ Failed to connect to Ollama: {e}", file=sys.stderr)
        print(f"Hint: Is Ollama running? Try: docker compose up -d ollama", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
