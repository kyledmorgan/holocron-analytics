#!/usr/bin/env bash
# Run end-to-end tests
# Requires: SQL Server running, MSSQL_SA_PASSWORD set

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "========================================"
echo "Running End-to-End Tests"
echo "========================================"

# Check for password
if [ -z "$MSSQL_SA_PASSWORD" ] && [ -z "$INGEST_SQLSERVER_PASSWORD" ]; then
    echo "Error: SQL Server password not set"
    echo ""
    echo "Set the password with one of:"
    echo "  export MSSQL_SA_PASSWORD='YourPassword123!'"
    echo "  export INGEST_SQLSERVER_PASSWORD='YourPassword123!'"
    exit 1
fi

cd "$PROJECT_DIR"

python -m pytest tests/e2e/ -v -m e2e

echo ""
echo "✓ E2E tests passed!"
