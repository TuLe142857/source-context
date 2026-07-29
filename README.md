# Source Context

# Requirements
- build tool: uv, npm
- python: 3.13
- node: 24
- docker

# Setup, build, run
- For development(localhost): [DEVELOPMENT.md](./DEVELOPMENT.md)  
- For production: [DEPLOYMENT.md](./DEPLOYMENT.md)

# RUN MCP Server

## Development

Run this command in root repo to install mcp tool local
```shell
uv tool install mcp --editable
```

Use tool to inspect the mcp(This will open browser).
```shell
npx -y @modelcontextprotocol/inspector uvx source-context-mcp run
```