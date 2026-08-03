.PHONY: demo-reset

demo-reset:
	docker compose up --build --wait db
	docker compose run --rm migrate
	docker compose run --rm seed
	docker compose run --rm --no-deps \
		-e CHANGEOPS_DEMO_RESET_CONFIRMED=reset-changeops-local-demo \
		api python -m changeops.demo_reset
	docker compose up --build --wait api web
