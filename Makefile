# Makefile for Healthcare Integration Engine

# Variables
DOCKER_COMPOSE = docker-compose
DOCKER_COMPOSE_TEST = docker-compose -f docker-compose.test.yml
DOCKER_COMPOSE_DEV = docker-compose -f docker-compose.dev.yml

.PHONY: help build up down restart logs test test-cov test-down lint format check-format

help: ## Display this help message
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Development
build: ## Build all services
	$(DOCKER_COMPOSE) build

up: ## Start all services in detached mode
	$(DOCKER_COMPOSE) up -d

down: ## Stop and remove all containers, networks, and volumes
	$(DOCKER_COMPOSE) down -v --remove-orphans

restart: down up ## Restart all services

logs: ## View logs from all services
	$(DOCKER_COMPOSE) logs -f

# Testing
test-up: ## Start test services
	$(DOCKER_COMPOSE_TEST) up -d

	test: test-up ## Run all tests
	$(DOCKER_COMPOSE_TEST) run --rm backend pytest -v

test-cov: test-up ## Run tests with coverage report
	$(DOCKER_COMPOSE_TEST) run --rm backend pytest --cov=app --cov-report=term-missing

test-down: ## Stop test services
	$(DOCKER_COMPOSE_TEST) down -v --remove-orphans

# Code Quality
lint: ## Run linters
	$(DOCKER_COMPOSE) run --rm backend flake8 app tests
	$(DOCKER_COMPOSE) run --rm backend black --check app tests
	$(DOCKER_COMPOSE) run --rm backend isort --check-only app tests

format: ## Format code
	$(DOCKER_COMPOSE) run --rm backend black app tests
	$(DOCKER_COMPOSE) run --rm backend isort app tests

# Database
db-shell: ## Open database shell
	$(DOCKER_COMPOSE) exec db psql -U postgres -d healthcare_integration

db-migrate: ## Run database migrations
	$(DOCKER_COMPOSE) run --rm backend alembic upgrade head

db-makemigrations: ## Create new database migration
	$(DOCKER_COMPOSE) run --rm backend alembic revision --autogenerate -m "$(m)"

# Cleanup
clean: ## Remove all build, test, and Python artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
	rm -f .coverage

distclean: clean ## Remove all build, test, coverage, and Python artifacts
	docker system prune -f
	docker volume prune -f
	docker network prune -f
