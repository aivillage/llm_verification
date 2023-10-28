clean:
	rm -rf .data

dev:
	docker compose -f development_helpers/docker-compose.dev.yml up --build
