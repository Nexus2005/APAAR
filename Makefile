SHELL := bash
PY := python
BACKEND := backend
FRONTEND := frontend

.PHONY: help generate seed dev-backend dev-frontend build lint test test-backend test-frontend evaluate clean

help:
	@echo "APAAR-Setu — prototype commands"
	@echo "  make generate       regenerate deterministic synthetic data + ground truth"
	@echo "  make seed           reset the local SQLite DB and seed the full demo"
	@echo "  make dev-backend    run FastAPI on :8000"
	@echo "  make dev-frontend   run Vite on :5173"
	@echo "  make lint           ruff + TypeScript typecheck"
	@echo "  make test           pytest + vitest"
	@echo "  make evaluate       measured evaluation against ground truth"
	@echo "  make build          production frontend build"

generate:
	$(PY) scripts/generate_synthetic.py --seed 42

seed: generate
	rm -f data/app.db
	cd $(BACKEND) && PYTHONPATH=. $(PY) -m app.seed.demo

dev-backend:
	cd $(BACKEND) && PYTHONPATH=. $(PY) -m uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd $(FRONTEND) && npm run dev

build:
	cd $(FRONTEND) && npm run build

lint:
	cd $(BACKEND) && PYTHONPATH=. $(PY) -m ruff check app tests
	cd $(FRONTEND) && npx tsc -b

test-backend:
	cd $(BACKEND) && PYTHONPATH=. $(PY) -m pytest

test-frontend:
	cd $(FRONTEND) && npm test

test: test-backend test-frontend

evaluate:
	$(PY) scripts/evaluate.py --stage all

clean:
	rm -f data/app.db
	rm -rf $(FRONTEND)/dist $(BACKEND)/.pytest_cache
