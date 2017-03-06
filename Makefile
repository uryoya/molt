.DEFAULT_GOAL := help

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: venv-init
venv-init: ## venvを使った開発環境の構築
	test -d venv || python3 -m venv venv
	venv/bin/pip install -Ur requirements.txt
