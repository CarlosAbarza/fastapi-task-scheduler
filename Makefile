.PHONY: run stop restart test logs clean lint format

# Archivo de docker-compose
COMPOSE_FILE=deployments/docker-compose.yml

run:
	docker compose -f $(COMPOSE_FILE) up --build -d

stop:
	docker compose -f $(COMPOSE_FILE) down

restart: stop run

test:
	python -m pytest tests/

logs:
	docker compose -f $(COMPOSE_FILE) logs -f

clean:
	docker compose -f $(COMPOSE_FILE) down -v

lint:
	black --check app/ worker/ tests/
	flake8 app/ worker/ tests/ --max-line-length=120

format:
	black app/ worker/ tests/
