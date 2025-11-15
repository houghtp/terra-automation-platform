# TerraAutomationPlatform Development Makefile

.PHONY: help install test compliance-check compliance-report compliance-fix dev-setup clean

help: ## Show this help message
	@echo "TerraAutomationPlatform Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt
	pip install pytest pre-commit

dev-setup: install ## Set up development environment
	pre-commit install
	@echo "Development environment setup complete!"

test: ## Run all tests
	pytest tests/ -v

compliance-check: ## Run tenant CRUD compliance check
	@echo "🔍 Running Tenant CRUD Compliance Check..."
	@python3 scripts/check_compliance.py
	pytest tests/compliance/test_tenant_crud_compliance.py -v

logging-compliance-check: ## Run logging standards compliance check
	@echo "🔍 Running Logging Compliance Check..."
	@python3 scripts/check_logging_compliance.py

route-structure-compliance: ## Run route structure compliance check
	@echo "🔍 Running Route Structure Compliance Check..."
	pytest tests/compliance/test_route_structure_compliance.py -v

global-admin-compliance: ## Run global admin pattern compliance check
	@echo "🔍 Running Global Admin Compliance Check..."
	pytest tests/compliance/test_global_admin_compliance.py -v

all-compliance-checks: compliance-check logging-compliance-check route-structure-compliance global-admin-compliance ## Run all compliance checks
	@echo "✅ All compliance checks completed"

compliance-report: ## Generate compliance report
	@echo "Generating Compliance Report..."
	pytest tests/compliance/test_tenant_crud_compliance.py::TestTenantCRUDCompliance::test_generate_compliance_report -v
	@echo "Report generated at docs/compliance-report.md"

compliance-fix: ## Run automated compliance fixes (placeholder)
	@echo "Automated compliance fixes not yet implemented"
	@echo "Please fix violations manually based on compliance report"

test-compliance: all-compliance-checks ## Alias for all compliance checks
	@echo "All compliance tests completed"

clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

lint: ## Run linting checks
	flake8 app/ tests/
	mypy app/

format: ## Format code
	black app/ tests/
	isort app/ tests/

pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

# Database commands
db-migrate: ## Run database migrations
	alembic upgrade head

db-reset: ## Reset database (DESTRUCTIVE)
	@echo "This will destroy all data. Are you sure? [y/N]" && read ans && [ $${ans:-N} = y ]
	python manage_db.py reset

seed-connectors: ## Seed connector catalog with predefined connectors
	@echo "🌱 Seeding connector catalog..."
	python app/seed_connectors.py

# Server commands
dev-server: ## Start development server
	python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

prod-server: ## Start production server
	python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Docker commands
docker-build: ## Build Docker image
	docker build -t terra-automation-platform .

docker-run: ## Run Docker container
	docker run -p 8000:8000 terra-automation-platform

docker-compose-up: ## Start with docker-compose
	docker-compose up -d

docker-compose-down: ## Stop docker-compose
	docker-compose down

# Security and compliance
security-check: ## Run security checks
	bandit -r app/
	safety check

audit: compliance-check security-check ## Run full audit (compliance + security)
	@echo "Full audit completed"

# Documentation
docs-build: ## Build documentation
	@echo "Documentation build not yet implemented"

docs-serve: ## Serve documentation locally
	@echo "Documentation serve not yet implemented"

# Testing categories
test-unit: ## Run unit tests only
	pytest tests/unit/ -v

test-integration: ## Run integration tests only
	pytest tests/integration/ -v

test-performance: ## Run performance tests
	pytest tests/performance/ -v

test-ui: ## Run UI tests
	pytest tests/ui/ -v

# CI/CD simulation
ci-test: ## Simulate CI/CD pipeline locally
	make lint
	make compliance-check
	make security-check
	make test
	@echo "CI/CD simulation completed successfully!"

# Quick development workflow
quick-check: ## Quick development check (fast tests + compliance)
	make compliance-check
	make test-unit
	@echo "Quick check completed!"
