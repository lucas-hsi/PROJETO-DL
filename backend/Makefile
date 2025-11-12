.PHONY: test init-db seed run

test:
	@docker compose exec -T backend pytest -q

init-db:
	@docker compose exec -T backend python -c "from app.core.database import init_db; init_db()"
	@docker compose exec -T backend python -m app.services.seed

seed:
	@docker compose exec -T backend python -m app.services.seed

run:
	@docker compose up --build