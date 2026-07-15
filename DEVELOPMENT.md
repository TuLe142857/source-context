# Development

# Install & run BE, FE
```shell
docker compose up -f docker-compose.yml -f docker-compose-dev.yml
```

# Install & run MCP tool(local)
```shell
cd mcp
uv build
uv tool install . --editable
```

Config mcp for coding agent:
- Command: "uvx source-context-mcp"