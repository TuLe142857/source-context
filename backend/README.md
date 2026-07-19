## Local development

Install and synchronize the workspace dependencies from the repository root:

```bash
uv sync --all-packages
```

Run the development server:

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Verify that the backend is accessible by checking the health endpoint:

```bash
curl http://localhost:8000/health
```

You should receive a JSON response similar to:

```json
{
  "status": "ok",
  "service": "Source Context Backend",
  "version": "0.1.0",
  "environment": "development"
}
```

The API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc