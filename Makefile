# Crypto-Signal Makefile
# Comandos útiles para desarrollo

DOCKER_REPO_NAME ?= ssolis-ti/
DOCKER_CONTAINER_NAME ?= crypto-signal
DOCKER_IMAGE_NAME ?= ${DOCKER_REPO_NAME}${DOCKER_CONTAINER_NAME}
GIT_BRANCH ?= $(shell git rev-parse --abbrev-ref HEAD)

# Construir imagen Docker
build:
	docker build -t ${DOCKER_IMAGE_NAME}:${GIT_BRANCH} .
	docker tag ${DOCKER_IMAGE_NAME}:${GIT_BRANCH} ${DOCKER_IMAGE_NAME}:latest

# Ejecutar con docker-compose (recomendado)
run:
	docker compose up

# Ejecutar con rebuild
run-build:
	docker compose up --build

# Limpiar imágenes huérfanas
clean:
	docker system prune -f
