ARG NODE_VERSION="24"
FROM node:${NODE_VERSION}-bookworm

# https://github.com/sourcegraph/scip-typescript
RUN npm install -g @sourcegraph/scip-typescript

RUN mkdir -p /sandbox/projects
RUN mkdir -p /sandbox/output

CMD ["/bin/bash"]