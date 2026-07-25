ARG NODE_VERSION="24"
FROM node:${NODE_VERSION}-bookworm

# https://github.com/sourcegraph/scip-typescript
RUN npm install -g @sourcegraph/scip-typescript

CMD ["/bin/bash"]