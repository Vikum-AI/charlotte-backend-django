.PHONY: all installdeps install createmigrations migrate adminuser dev run shell test \
	neo4j-labels seed-neo4j backfill-customers backfill-transactions backfill-transactions-dry-run startworker

POETRY := poetry
MANAGE := $(POETRY) run python manage.py
DEV_PORT := 8000
GUNICORN_PORT := 9000

all:
	@echo "Available commands:"
	@echo "  make installdeps              Install poetry deps"
	@echo "  make createmigrations         Generate Django migrations"
	@echo "  make install                  installdeps + createmigrations"
	@echo "  make migrate                  Apply migrations"
	@echo "  make adminuser                Create Django superuser (email login)"
	@echo "  make dev                      Run dev server (port $(DEV_PORT))"
	@echo "  make run                      Run gunicorn (port $(GUNICORN_PORT))"
	@echo "  make shell                    Open poetry shell"
	@echo "  make test                     Run test suite"
	@echo "  make neo4j-labels             Install Neo4j constraints/indexes (neomodel)"
	@echo "  make seed-neo4j               Seed Neo4j graph from Kaggle datasets"
	@echo "  make backfill-customers       Backfill Customer kyc/risk/industry"
	@echo "  make backfill-transactions    Backfill missing Transaction fields"
	@echo "  make backfill-transactions-dry-run  Report missing Transaction fields only"
	@echo "  make startworker              Start Dramatiq worker (requires Redis)"

installdeps:
	@if command -v poetry >/dev/null 2>&1; then \
		echo "Poetry already installed"; \
	else \
		python3 -m pip install poetry; \
	fi
	$(POETRY) install

createmigrations:
	$(MANAGE) makemigrations

install: installdeps createmigrations

migrate:
	$(MANAGE) migrate

adminuser:
	$(MANAGE) createsuperuser

dev:
	$(MANAGE) runserver $(DEV_PORT)

run:
	$(POETRY) run gunicorn verity.wsgi:application --bind 127.0.0.1:$(GUNICORN_PORT)

shell:
	@echo "Starting poetry shell. Press Ctrl-d to exit."
	$(POETRY) shell

test:
	$(MANAGE) test

neo4j-labels:
	$(MANAGE) install_labels

seed-neo4j:
	$(MANAGE) seed_db

backfill-customers:
	$(MANAGE) backfill_customer_attributes

backfill-transactions:
	$(MANAGE) backfill_transaction_fields

backfill-transactions-dry-run:
	$(MANAGE) backfill_transaction_fields --dry-run

startworker:
	$(MANAGE) rundramatiq
