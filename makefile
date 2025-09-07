# FILE CONTRACT (KEEP THIS COMMENT)
# See COPILOT_SPEC.md for full build and style requirements.

# Makefile for Enterprise RAG POC
# Provides shortcuts for common Docker Compose workflows

# Start all services with build
up:
	# Bring up all containers in detached mode, rebuilding as needed
	docker compose up -d --build

# Stop and remove all containers, networks, and volumes
 down:
	# Tear down all running containers
	docker compose down

# Rebuild all images and restart services
rebuild:
	# Full rebuild and restart
	docker compose down && docker compose up -d --build

# Tail logs from all services (last 200 lines)
logs:
	# Follow logs for all containers
	docker compose logs -f --tail=200

# Open a shell in the API container
api-shell:
	# Interactive bash shell in FastAPI container
	docker exec -it api /bin/bash

# Open a shell in the ingest container
ingest-shell:
	# Interactive bash shell in ingest CLI container
	docker exec -it ingest /bin/bash

# Pull the Mistral model inside the Ollama container
pull-models:
	# Download Mistral-7B quantized model for Ollama
	docker exec -it ollama ollama pull mistral:7b-instruct-q4_K_M

# Run API tests inside the api container
 test:
	# Run pytest in FastAPI container
	docker exec -it api pytest -q
