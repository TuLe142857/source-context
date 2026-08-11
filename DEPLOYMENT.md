# Deployment

## Deploy Backend

### Requirements
- A domain
- A Cloudflare account (this project is set up to deploy via Cloudflare Tunnel, available on the free plan)
- A VPS

### Setup Cloudflare Tunnel
- Add your domain to your Cloudflare account.
- Create a Cloudflare Tunnel and copy its token into `TUNNEL_TOKEN` in `.env.prod`.
- Configure the tunnel's public hostnames:

| Service URL          | Public hostname |
|-----------------------|------------------|
| http://backend:8000  | api.\<domain\>  |
| http://grafana:3000  | log.\<domain\>  |

### First-time Setup
SSH into your server and clone the project:
```shell
git clone https://github.com/TuLe142857/source-context.git
cd source-context
```

Create the env file:
```shell
cp .env.example .env.prod
```
Then edit `.env.prod` and set the secret values (e.g. `SOURCE_CONTEXT_SECRET_KEY`, database/queue passwords, `TUNNEL_TOKEN`, etc.).

Build the Docker sandbox images:
```shell
cd docker/sandboxes
make build-sandbox
cd ../..
```

### Start the Server
```shell
alias dc="docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod"
dc pull
dc up -d
```

## Deploy Frontend
> [!NOTE]
> The frontend is deployed with Vercel.
> See: [.github/workflows/deploy-fe.yml](.github/workflows/deploy-fe.yml)

Configure the following variables in the Vercel Production environment:

| Key                  | Value                    |
|----------------------|--------------------------|
| VITE_API_BASE_URL    | https://api.\<domain\>  |
| VITE_GITHUB_APP_NAME | GitHub App name          |

For manual deploy:
```shell
export VERCEL_TOKEN=<your token>
vercel pull --environment=production
vercel build --prod
vercel deploy --prod --prebuilt
```

## Deploy MCP to PyPI

> [!NOTE]
> MCP is published to PyPI via GitHub Actions.
> See: [.github/workflows/publish-mcp.yml](.github/workflows/publish-mcp.yml)

For manual publish:
(use `uv publish --publish-url https://test.pypi.org/legacy/` to publish to Test PyPI)
```shell
uv build mcp
uv publish

# You may need to enter credentials:
# user: __token__
# password: <your token>
```
