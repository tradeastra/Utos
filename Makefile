.PHONY: install docker-up docker-down docker-logs test test-backend test-frontend lint format migrate migrate-make run-dev

install:
	poetry install --no-root
	cd frontend && npm install

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

test: test-backend test-frontend

test-backend:
	cd backend && poetry run pytest --cov=. --cov-report=term-missing --cov-fail-under=80 -v

test-frontend:
	cd frontend && npm run lint && npm run type-check

lint:
	poetry run ruff check backend/
	poetry run black --check backend/
	poetry run mypy backend/ --ignore-missing-imports
	cd frontend && npm run lint

format:
	poetry run ruff check --fix backend/
	poetry run black backend/
	poetry run isort backend/
	cd frontend && npm run format

migrate:
	cd backend && poetry run alembic upgrade head

migrate-make:
	cd backend && poetry run alembic revision --autogenerate -m "$(msg)"

run-dev:
	docker compose up postgres redis -d
	cd backend && poetry run uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
	cd frontend && npm run dev
