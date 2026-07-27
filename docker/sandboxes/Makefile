
help:
	@echo "Usage: make TARGET"
	@echo ""
	@echo "TARGET:"
	@echo "  build-sandbox"
	@echo "  build-sandbox-python"
	@echo "  build-sandbox-java"
	@echo "  build-sandbox-node"
	@echo "  help"


build-sandbox: build-sandbox-python build-sandbox-node build-sandbox-java

build-sandbox-python:
	docker build -f python.Dockerfile -t sandbox/python310:latest  --build-arg PY_VERSION=3.10 .
	docker build -f python.Dockerfile -t sandbox/python311:latest  --build-arg PY_VERSION=3.11 .
	docker build -f python.Dockerfile -t sandbox/python312:latest  --build-arg PY_VERSION=3.12 .
	docker build -f python.Dockerfile -t sandbox/python313:latest  --build-arg PY_VERSION=3.13 .
	docker build -f python.Dockerfile -t sandbox/python314:latest  --build-arg PY_VERSION=3.14 .
# 	docker build -f python.Dockerfile -t sandbox/python315:latest  --build-arg PY_VERSION=3.15 .

build-sandbox-java:
	@echo Note: Currently java docker sandbox not completed yet.
#	docker build -f java.Dockerfile -t sandbox/java17:latest --build-arg JAVA_VERSION=17 .
#	docker build -f java.Dockerfile -t sandbox/java21:latest --build-arg JAVA_VERSION=21 .
#	docker build -f java.Dockerfile -t sandbox/java25:latest --build-arg JAVA_VERSION=25 .

build-sandbox-node:
	docker build -f node.Dockerfile -t sandbox/node24:latest --build-arg NODE_VERSION=22 .
	docker build -f node.Dockerfile -t sandbox/node24:latest --build-arg NODE_VERSION=24 .

