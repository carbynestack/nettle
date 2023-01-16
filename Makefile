.PHONY: all
all: cli

.PHONY: build
build:
	pip install -r requirements.txt

.PHONY: cli
cli:
	docker build -t carbynestack/cs-jar -f build/cli.Dockerfile build