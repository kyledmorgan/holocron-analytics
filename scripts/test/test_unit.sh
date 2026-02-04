#!/usr/bin/env bash
# Run unit tests (no external dependencies required)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "========================================"
echo "Running Unit Tests"
echo "========================================"

cd "$PROJECT_DIR"

python -m pytest tests/unit/ -v -m "not integration and not e2e"

echo ""
echo "✓ Unit tests passed!"
