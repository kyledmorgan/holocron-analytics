#!/usr/bin/env python3
"""
Capture Ollama Models

A utility script that captures a snapshot of available Ollama models
and their metadata, writing the inventory to a JSON file.

Usage:
    python src/llm/tools/capture_ollama_models.py
    python src/llm/tools/capture_ollama_models.py --base-url http://192.168.1.100:11434
    python src/llm/tools/capture_ollama_models.py --output-dir local/llm_artifacts

Environment Variables:
    LLM_BASE_URL: Ollama base URL (default: http://localhost:11434)

Exit Codes:
    0: Success
    1: Failed to connect to Ollama or capture models
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Capture Ollama models inventory to JSON"
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("LLM_BASE_URL", "http://localhost:11434"),
        help="Ollama base URL (default: http://localhost:11434)"
    )
    parser.add_argument(
        "--output-dir",
        default="local/llm_artifacts/model_inventory",
        help="Directory to write output files (default: local/llm_artifacts/model_inventory)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    return parser.parse_args()


def fetch_models(base_url: str) -> dict:
    """
    Fetch available models from Ollama.
    
    Args:
        base_url: Ollama API base URL
        
    Returns:
        Dictionary with model list from Ollama
        
    Raises:
        Exception: If request fails
    """
    url = f"{base_url.rstrip('/')}/api/tags"
    
    request = Request(url, method="GET")
    request.add_header("Accept", "application/json")
    
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_model_details(base_url: str, model_name: str) -> dict:
    """
    Fetch detailed information about a specific model.
    
    Args:
        base_url: Ollama API base URL
        model_name: Name of the model
        
    Returns:
        Dictionary with model details
    """
    url = f"{base_url.rstrip('/')}/api/show"
    
    payload = json.dumps({"name": model_name}).encode("utf-8")
    request = Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError) as e:
        return {"error": str(e)}


def capture_inventory(base_url: str, verbose: bool = False) -> dict:
    """
    Capture complete model inventory.
    
    Args:
        base_url: Ollama API base URL
        verbose: Whether to print verbose output
        
    Returns:
        Complete inventory dictionary
    """
    print(f"Capturing Ollama model inventory from {base_url}")
    
    # Fetch model list
    models_response = fetch_models(base_url)
    models = models_response.get("models", [])
    
    print(f"Found {len(models)} models")
    
    # Build inventory
    inventory = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "ollama_base_url": base_url,
        "model_count": len(models),
        "models": []
    }
    
    for model in models:
        model_name = model.get("name", "unknown")
        
        if verbose:
            print(f"  - {model_name}")
        
        model_entry = {
            "name": model_name,
            "model": model.get("model"),
            "modified_at": model.get("modified_at"),
            "size": model.get("size"),
            "digest": model.get("digest"),
            "details": model.get("details", {})
        }
        
        # Optionally fetch additional details
        # Commented out to avoid slow operation with many models
        # details = fetch_model_details(base_url, model_name)
        # model_entry["full_details"] = details
        
        inventory["models"].append(model_entry)
    
    return inventory


def write_inventory(inventory: dict, output_dir: Path) -> Path:
    """
    Write inventory to JSON file.
    
    Args:
        inventory: Inventory dictionary
        output_dir: Directory to write file
        
    Returns:
        Path to written file
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"ollama_models_{timestamp}.json"
    file_path = output_dir / filename
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(inventory, f, indent=2, ensure_ascii=False)
    
    return file_path


def main():
    """Main entry point."""
    args = parse_args()
    
    output_dir = Path(args.output_dir)
    
    try:
        # Capture inventory
        inventory = capture_inventory(args.base_url, args.verbose)
        
        # Write to file
        file_path = write_inventory(inventory, output_dir)
        
        print(f"\nInventory written to: {file_path}")
        print(f"Models captured: {inventory['model_count']}")
        
        return 0
        
    except HTTPError as e:
        print(f"HTTP error: {e.code} - {e.reason}")
        return 1
    except URLError as e:
        print(f"Failed to connect to Ollama at {args.base_url}: {e}")
        print("Hint: Is Ollama running? Try: ollama serve")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
