.PHONY build
build:
	docker build -t swkoubou/molt .

.PHONY run
run:
	docker run -it --rm -p 80:5000 swkoubou/molt
