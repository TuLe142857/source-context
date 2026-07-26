ARG JAVA_VERSION="21"

FROM eclipse-temurin:${JAVA_VERSION}-jdk

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates && \
    rm -rf /var/lib/apt/lists/*

RUN curl -fLo /usr/local/bin/cs \
    https://github.com/coursier/launchers/raw/master/cs-x86_64-pc-linux && \
    chmod +x /usr/local/bin/cs

RUN java --version && \
    javac --version && \
    cs --version

RUN cs install scip-java

WORKDIR /workspace