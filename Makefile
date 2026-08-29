.PHONY: help install test lint format check fix clean ci

help: ## Show help for make commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install development dependencies
	pip install -r requirements-dev.txt

test: ## Run tests
	pytest -v

coverage: ## Lance les tests avec coverage
	pytest --cov=mypacer_api --cov-report=term-missing --cov-report=html
	@echo "📊 Rapport HTML généré dans htmlcov/index.html"

lint: ## Check code quality (ruff + mypy)
	@echo "Linting with ruff..."
	ruff check .
	@echo "\nType checking with mypy..."
	mypy mypacer_api/ --ignore-missing-imports

format: ## Format code with ruff
	@echo "Formatting with ruff..."
	ruff format .
	@echo "Organizing imports with ruff..."
	ruff check --fix --select I .

check: lint test ## Run all checks (lint + tests)

fix: format ## Automatically fix formatting and import issues
	ruff check --fix .

clean: ## Clean up temporary files
	rm -rf __pycache__ */__pycache__ */*/__pycache__
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

ci: ## Simulate the CI pipeline locally
	@echo "--- CI Simulation ---"
	@echo "\n1. Checking formatting..."
	ruff format --check --diff . || (echo "❌ Formatting check failed" && exit 1)
	@echo "✅ Formatting OK"
	@echo "\n2. Linting..."
	ruff check . || (echo "❌ Linter check failed" && exit 1)
	@echo "✅ Linter OK"
	@echo "\n3. Type checking..."
	mypy mypacer_api/ --ignore-missing-imports || (echo "⚠️  Type checking has warnings/errors" && true)
	@echo "\n4. Running tests with coverage..."
	pytest --cov=mypacer_api --cov-report=term-missing || (echo "❌ Tests failed" && exit 1)
	@echo "\n✅ All checks passed!"
