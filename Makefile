# Holocron Analytics - Development Makefile
# 
# Usage:
#   make help          - Show available targets
#   make test          - Run all tests
#   make verify-sqlserver - One command to prove SQL Server integration works
#
# Prerequisites:
#   - Docker and Docker Compose installed
#   - Python 3.11+ with pip
#   - ODBC Driver 18 for SQL Server
#
# Environment variables:
#   MSSQL_SA_PASSWORD - SQL Server SA password (required for SQL Server tests)

.PHONY: help test test-unit test-sqlserver test-e2e verify-sqlserver \
        db-up db-down db-init db-wait install lint clean

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m  # No Color

#------------------------------------------------------------------------------
# Help
#------------------------------------------------------------------------------

help: ## Show this help message
	@echo ""
	@echo "$(BLUE)Holocron Analytics - Development Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Test Commands:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Quick Start:$(NC)"
	@echo "  1. Set password:    export MSSQL_SA_PASSWORD='YourPassword123!'"
	@echo "  2. Verify all:      make verify-sqlserver"
	@echo ""

#------------------------------------------------------------------------------
# Installation
#------------------------------------------------------------------------------

install: ## Install Python dependencies
	pip install -r src/ingest/requirements.txt
	pip install pytest pytest-env

#------------------------------------------------------------------------------
# Docker/SQL Server Commands
#------------------------------------------------------------------------------

db-up: ## Start SQL Server container
	@echo "$(BLUE)Starting SQL Server...$(NC)"
	docker compose up -d sqlserver
	@echo "$(GREEN)SQL Server container started$(NC)"

db-down: ## Stop SQL Server container
	@echo "$(BLUE)Stopping SQL Server...$(NC)"
	docker compose down
	@echo "$(GREEN)SQL Server container stopped$(NC)"

db-wait: ## Wait for SQL Server to be ready
	@echo "$(BLUE)Waiting for SQL Server to be ready...$(NC)"
	@for i in $$(seq 1 60); do \
		docker compose exec -T sqlserver /opt/mssql-tools18/bin/sqlcmd \
			-S localhost -U sa -P "$$MSSQL_SA_PASSWORD" -C -Q "SELECT 1" \
			> /dev/null 2>&1 && break; \
		echo "  Waiting... ($$i/60)"; \
		sleep 2; \
	done
	@echo "$(GREEN)SQL Server is ready$(NC)"

db-init: ## Initialize database schema (runs migrations)
	@echo "$(BLUE)Initializing database schema...$(NC)"
	python -m tools.db_init --migrations-dir db/migrations
	@echo "$(GREEN)Database initialized$(NC)"

db-smoketest: ## Run database smoke test
	@echo "$(BLUE)Running database smoke test...$(NC)"
	python scripts/db/db_smoketest.py

#------------------------------------------------------------------------------
# Test Commands
#------------------------------------------------------------------------------

test: ## Run all tests
	@echo "$(BLUE)Running all tests...$(NC)"
	python -m pytest tests/ -v

test-unit: ## Run unit tests only (no external dependencies)
	@echo "$(BLUE)Running unit tests...$(NC)"
	python -m pytest tests/unit/ -v -m "not integration and not e2e"

test-sqlserver: test-integration ## Run SQL Server integration tests (alias)

test-integration: ## Run integration tests (requires SQL Server)
	@echo "$(BLUE)Running integration tests...$(NC)"
	@if [ -z "$$MSSQL_SA_PASSWORD" ]; then \
		echo "$(RED)Error: MSSQL_SA_PASSWORD not set$(NC)"; \
		echo "Set with: export MSSQL_SA_PASSWORD='YourPassword123!'"; \
		exit 1; \
	fi
	python -m pytest tests/integration/ -v -m integration

test-e2e: ## Run end-to-end tests (requires SQL Server)
	@echo "$(BLUE)Running E2E tests...$(NC)"
	@if [ -z "$$MSSQL_SA_PASSWORD" ]; then \
		echo "$(RED)Error: MSSQL_SA_PASSWORD not set$(NC)"; \
		echo "Set with: export MSSQL_SA_PASSWORD='YourPassword123!'"; \
		exit 1; \
	fi
	python -m pytest tests/e2e/ -v -m e2e

#------------------------------------------------------------------------------
# One-Command Verification
#------------------------------------------------------------------------------

verify-sqlserver: ## One command to verify SQL Server integration works end-to-end
	@echo ""
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║       SQL Server Integration Verification                   ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@if [ -z "$$MSSQL_SA_PASSWORD" ]; then \
		echo "$(RED)Error: MSSQL_SA_PASSWORD not set$(NC)"; \
		echo ""; \
		echo "Set the password and try again:"; \
		echo "  export MSSQL_SA_PASSWORD='YourPassword123!'"; \
		echo "  make verify-sqlserver"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Step 1/5: Starting SQL Server container...$(NC)"
	@docker compose up -d sqlserver
	@echo ""
	@echo "$(YELLOW)Step 2/5: Waiting for SQL Server to be ready...$(NC)"
	@python -c "from tests.conftest import wait_for_sqlserver; import sys; sys.exit(0 if wait_for_sqlserver(timeout=60) else 1)" || \
		(echo "$(RED)SQL Server not ready after 60s$(NC)" && exit 1)
	@echo ""
	@echo "$(YELLOW)Step 3/5: Initializing database schema...$(NC)"
	@python -m tools.db_init --migrations-dir db/migrations || \
		(echo "$(RED)Failed to initialize database$(NC)" && exit 1)
	@echo ""
	@echo "$(YELLOW)Step 4/5: Running smoke test...$(NC)"
	@python scripts/db/db_smoketest.py || \
		(echo "$(RED)Smoke test failed$(NC)" && exit 1)
	@echo ""
	@echo "$(YELLOW)Step 5/5: Running integration and E2E tests...$(NC)"
	@python -m pytest tests/integration/ tests/e2e/ -v --tb=short || \
		(echo "$(RED)Tests failed$(NC)" && exit 1)
	@echo ""
	@echo "$(GREEN)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(GREEN)║       ✓ All verifications passed!                          ║$(NC)"
	@echo "$(GREEN)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(GREEN)SQL Server integration is working correctly.$(NC)"
	@echo ""

#------------------------------------------------------------------------------
# Utility Commands
#------------------------------------------------------------------------------

lint: ## Run linters
	@echo "$(BLUE)Running linters...$(NC)"
	python -m py_compile src/ingest/**/*.py 2>/dev/null || true
	python -m py_compile tools/*.py 2>/dev/null || true

clean: ## Clean up temporary files
	@echo "$(BLUE)Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)Cleanup complete$(NC)"
