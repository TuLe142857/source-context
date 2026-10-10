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

### GitHub App setup for private repositories

Set `SOURCE_CONTEXT_GITHUB_APP_ID` to the **App ID** (not the Client ID) and `SOURCE_CONTEXT_GITHUB_APP_PRIVATE_KEY` to the private key PEM generated in the GitHub App settings. In `.env.prod`, encode PEM line breaks as the literal `\n` sequence. Set `GITHUB_WEBHOOK_SECRET` to the same webhook secret configured on the GitHub App.

Grant the App repository **Contents: Read-only** access (Metadata is required by GitHub), and subscribe it to `push`, `installation`, and `installation_repositories` events. The setup URL should point to `/api/v1/webhooks/setup`. Install the App on each account and select the private repositories the workspace may read. The backend exchanges App JWTs for short-lived installation tokens; tokens are cached only in process memory until shortly before expiry and are not written to repository URLs or the database.

Both backend and Celery worker need the App ID/private key and webhook secret. The frontend's `VITE_GITHUB_APP_NAME` must be the App slug used in the GitHub installation URL.

Before deploying a backend version that adds a database field, apply its SQL migration to the production database. The initial commit-checkpoint migration is:

```shell
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < backend/migrations/20261004_add_indexed_commit_sha.sql
```

Apply the GitHub repository identity and webhook delivery migration as well:

```shell
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < backend/migrations/20261004_add_github_webhook_deliveries.sql
```

The webhook endpoint verifies `X-Hub-Signature-256` and records `X-GitHub-Delivery` before applying repository changes. Configure GitHub to send deliveries to `/api/v1/webhooks/github`. Pushes to tracked branches create an indexing job when the pushed SHA is not indexed; pushes received during a running job are coalesced into a follow-up job after the current checkpoint is committed. Monitor webhook deliveries and Celery for queue failures.

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
