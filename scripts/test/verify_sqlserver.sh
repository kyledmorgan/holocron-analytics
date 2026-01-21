#!/usr/bin/env bash
# One command to verify SQL Server integration works end-to-end
#
# This script:
# 1. Starts SQL Server container (if needed)
# 2. Waits for SQL Server to be ready
# 3. Initializes schema/tables
# 4. Runs smoke test
# 5. Runs integration and E2E tests
#
# Usage:
#   export MSSQL_SA_PASSWORD='YourPassword123!'
#   ./scripts/test/verify_sqlserver.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       SQL Server Integration Verification                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check for password
if [ -z "$MSSQL_SA_PASSWORD" ] && [ -z "$INGEST_SQLSERVER_PASSWORD" ]; then
    echo -e "${RED}Error: SQL Server password not set${NC}"
    echo ""
    echo "Set the password and try again:"
    echo "  export MSSQL_SA_PASSWORD='YourPassword123!'"
    echo "  ./scripts/test/verify_sqlserver.sh"
    exit 1
fi

cd "$PROJECT_DIR"

# Step 1: Start SQL Server
echo -e "${YELLOW}Step 1/5: Starting SQL Server container...${NC}"
docker compose up -d sqlserver
echo ""

# Step 2: Wait for SQL Server
echo -e "${YELLOW}Step 2/5: Waiting for SQL Server to be ready...${NC}"
python -c "
import sys
sys.path.insert(0, '.')
from tests.conftest import wait_for_sqlserver
if not wait_for_sqlserver(timeout=60):
    print('SQL Server not ready after 60s')
    sys.exit(1)
"
echo ""

# Step 3: Initialize database
echo -e "${YELLOW}Step 3/5: Initializing database schema...${NC}"
python -m tools.db_init --migrations-dir db/migrations
echo ""

# Step 4: Smoke test
echo -e "${YELLOW}Step 4/5: Running smoke test...${NC}"
python scripts/db/db_smoketest.py
echo ""

# Step 5: Run tests
echo -e "${YELLOW}Step 5/5: Running integration and E2E tests...${NC}"
python -m pytest tests/integration/ tests/e2e/ -v --tb=short
echo ""

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       ✓ All verifications passed!                          ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}SQL Server integration is working correctly.${NC}"
echo ""
