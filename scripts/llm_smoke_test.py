#!/usr/bin/env python3
"""
LLM Smoke Test

A lightweight test script to validate Ollama connectivity and basic LLM functionality.

Usage:
    python scripts/llm_smoke_test.py
    python scripts/llm_smoke_test.py --base-url http://192.168.1.100:11434
    python scripts/llm_smoke_test.py --model mistral

Environment Variables:
    LLM_BASE_URL: Ollama base URL (default: http://localhost:11434)
    LLM_MODEL: Model to use (default: llama3.2)

Exit Codes:
    0: Success
    1: Provider unreachable or JSON parse failure
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm.core.types import LLMConfig
from src.llm.providers.ollama_client import OllamaClient
from src.llm.core.exceptions import LLMProviderError


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="LLM Smoke Test - Validate Ollama connectivity"
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("LLM_BASE_URL", "http://localhost:11434"),
        help="Ollama base URL (default: http://localhost:11434)"
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("LLM_MODEL", "llama3.2"),
        help="Model to use (default: llama3.2)"
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to write output files (default: temp directory)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    return parser.parse_args()


def run_smoke_test(base_url: str, model: str, output_dir: Path, verbose: bool) -> bool:
    """
    Run the smoke test.
    
    Returns:
        True if test passed, False otherwise
    """
    print(f"LLM Smoke Test")
    print(f"=" * 50)
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    print(f"Output Directory: {output_dir}")
    print()
    
    # Create config
    config = LLMConfig(
        provider="ollama",
        model=model,
        base_url=base_url,
        temperature=0.0,
        stream=False,
        timeout_seconds=60,
    )
    
    # Create client
    client = OllamaClient(config)
    
    # Step 1: Health check
    print("[1/3] Checking Ollama health...")
    if not client.health_check():
        print(f"  ❌ FAILED: Ollama is not reachable or model '{model}' is not available")
        print(f"  Hint: Is Ollama running? Try: ollama serve")
        print(f"  Hint: Is the model pulled? Try: ollama pull {model}")
        return False
    print("  ✓ Ollama is healthy and model is available")
    
    # Step 2: Generate with JSON output request
    print("[2/3] Testing JSON generation...")
    
    prompt = """Return a JSON object with the following structure:
{
  "test_name": "smoke_test",
  "status": "success",
  "timestamp": "<current timestamp>",
  "message": "Hello from the LLM!"
}

Return ONLY the JSON object, no additional text."""

    try:
        response = client.generate(prompt)
        
        if not response.success:
            print(f"  ❌ FAILED: Generation returned error: {response.error_message}")
            return False
        
        if verbose:
            print(f"  Raw response:\n{response.content}")
        
        print(f"  ✓ Received response ({len(response.content or '')} chars)")
        
    except LLMProviderError as e:
        print(f"  ❌ FAILED: Provider error: {e}")
        return False
    except Exception as e:
        print(f"  ❌ FAILED: Unexpected error: {e}")
        return False
    
    # Step 3: Parse JSON
    print("[3/3] Parsing JSON response...")
    
    content = response.content or ""
    
    # Try to extract JSON from response (may have markdown)
    text = content.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    try:
        parsed = json.loads(text)
        print(f"  ✓ Successfully parsed JSON")
        
        if verbose:
            print(f"  Parsed content:")
            print(json.dumps(parsed, indent=2))
        
    except json.JSONDecodeError as e:
        print(f"  ❌ FAILED: JSON parse error: {e}")
        print(f"  Response was: {text[:200]}...")
        return False
    
    # Step 4: Write outputs
    print()
    print("Writing outputs...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Write raw response
    raw_path = output_dir / f"smoke_test_{timestamp}_raw.txt"
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Raw response: {raw_path}")
    
    # Write parsed JSON
    parsed_path = output_dir / f"smoke_test_{timestamp}_parsed.json"
    with open(parsed_path, "w", encoding="utf-8") as f:
        json.dump(parsed, f, indent=2)
    print(f"  Parsed JSON: {parsed_path}")
    
    # Write metadata
    metadata = {
        "test_timestamp": datetime.now().isoformat(),
        "base_url": base_url,
        "model": model,
        "prompt_tokens": response.prompt_tokens,
        "completion_tokens": response.completion_tokens,
        "total_tokens": response.total_tokens,
        "success": True,
    }
    meta_path = output_dir / f"smoke_test_{timestamp}_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"  Metadata: {meta_path}")
    
    print()
    print("=" * 50)
    print("✓ SMOKE TEST PASSED")
    print("=" * 50)
    
    return True


def main():
    """Main entry point."""
    args = parse_args()
    
    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = Path(tempfile.mkdtemp(prefix="llm_smoke_test_"))
    
    # Run test
    success = run_smoke_test(
        base_url=args.base_url,
        model=args.model,
        output_dir=output_dir,
        verbose=args.verbose,
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
