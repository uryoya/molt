.DEFAULT_GOAL := help

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: build
build: ## dockerイメージのビルド
	docker build -t swkoubou/molt .

.PHONY: run
run: ## コンテナの起動
	docker run -it --rm -p 80:5000 swkoubou/molt
