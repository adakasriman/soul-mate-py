# ============================================================
# E-Commerce Backend — Makefile
# Run `make help` to see all available commands
# ============================================================

.DEFAULT_GOAL := help
.PHONY: help install setup run run-prod migrate makemigrations \
        createsuperuser shell test test-cov celery celery-beat \
        redis docker-up docker-down lint format clean

# ── Variables ────────────────────────────────────────────────
PYTHON      = python3
PIP         = pip
MANAGE      = $(PYTHON) manage.py
SETTINGS    = config.settings.development
DJANGO_ENV  = DJANGO_SETTINGS_MODULE=$(SETTINGS)
CELERY_APP  = config.celery

# ── Help ─────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  E-Commerce Backend — Available Commands"
	@echo "  ========================================"
	@echo ""
	@echo "  Setup:"
	@echo "    make install          Install all Python dependencies"
	@echo "    make setup            Full first-time setup (install + env + migrate)"
	@echo "    make createsuperuser  Create a superuser account"
	@echo ""
	@echo "  Running:"
	@echo "    make run              Start development server (port 8000)"
	@echo "    make run-prod         Start with Gunicorn (production mode)"
	@echo "    make celery           Start Celery worker"
	@echo "    make celery-beat      Start Celery beat scheduler"
	@echo "    make redis            Start Redis (local, requires redis-server)"
	@echo ""
	@echo "  Database:"
	@echo "    make migrate          Run all pending migrations"
	@echo "    make makemigrations   Create new migrations"
	@echo "    make shell            Open Django shell"
	@echo ""
	@echo "  Testing:"
	@echo "    make test             Run all tests"
	@echo "    make test-cov         Run tests with coverage report"
	@echo ""
	@echo "  Docker:"
	@echo "    make docker-up        Start all services via Docker Compose"
	@echo "    make docker-down      Stop all Docker Compose services"
	@echo ""
	@echo "  Code Quality:"
	@echo "    make lint             Run flake8 linter"
	@echo "    make format           Run black + isort formatter"
	@echo ""

# ── Setup ────────────────────────────────────────────────────
install:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

setup: install
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "  .env file created from .env.example — please update your values."; \
	fi
	mkdir -p logs
	$(DJANGO_ENV) $(MANAGE) migrate
	@echo ""
	@echo "  Setup complete! Run 'make createsuperuser' then 'make run'."

createsuperuser:
	$(DJANGO_ENV) $(MANAGE) createsuperuser

# ── Running ──────────────────────────────────────────────────
run:
	$(DJANGO_ENV) $(MANAGE) runserver 0.0.0.0:8000

run-prod:
	gunicorn config.wsgi:application \
		--bind 0.0.0.0:8000 \
		--workers 4 \
		--worker-class gthread \
		--threads 2 \
		--timeout 120 \
		--access-logfile - \
		--error-logfile -

celery:
	$(DJANGO_ENV) celery -A $(CELERY_APP) worker \
		--loglevel=info \
		--concurrency=4 \
		-Q default,email,notifications

celery-beat:
	$(DJANGO_ENV) celery -A $(CELERY_APP) beat \
		--loglevel=info \
		--scheduler django_celery_beat.schedulers:DatabaseScheduler

celery-flower:
	$(DJANGO_ENV) celery -A $(CELERY_APP) flower --port=5555

redis:
	redis-server

# ── Database ─────────────────────────────────────────────────
migrate:
	$(DJANGO_ENV) $(MANAGE) migrate

makemigrations:
	$(DJANGO_ENV) $(MANAGE) makemigrations

shell:
	$(DJANGO_ENV) $(MANAGE) shell_plus 2>/dev/null || $(DJANGO_ENV) $(MANAGE) shell

# ── Testing ──────────────────────────────────────────────────
test:
	$(DJANGO_ENV) pytest apps/ tests/ -v --tb=short

test-cov:
	$(DJANGO_ENV) pytest apps/ tests/ \
		--cov=apps \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		-v

# ── Docker ───────────────────────────────────────────────────
docker-up:
	docker-compose up --build

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f api

# ── Code Quality ─────────────────────────────────────────────
lint:
	flake8 apps/ core/ config/ --max-line-length=120 --exclude=migrations

format:
	black apps/ core/ config/ tests/ --line-length=120
	isort apps/ core/ config/ tests/

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov .coverage
