import re
import urllib.parse


def canonicalize_url_path(url_or_path: str) -> str:
    """Standardize URL paths across all languages and frameworks.

    - Strips host/port or leading base URL variable if present:
        * 'http://localhost:8000/api/v1/x' -> '/api/v1/x'
        * '${CATALOG_BASE_URL}/api/v1/x' -> '/api/v1/x'
        * '{self.base_url}/api/v1/x' -> '/api/v1/x'
    - Normalizes template parameter syntax:
        * JS template literal: ${id} -> {}
        * Flask/Django: <int:id>, <id> -> {}
        * Next.js dynamic routes: [id], [...slug] -> {}
        * FastAPI/OpenAPI: {user_id} -> {}
        * Express/Koa/Fastify/NestJS: :userId -> {}
    - Normalizes trailing slashes and multiple slashes: '/users//' -> '/users'
    """
    if not url_or_path:
        return "/"

    # Strip scheme, domain, port if absolute URL was provided
    if "://" in url_or_path:
        parsed = urllib.parse.urlparse(url_or_path)
        path = parsed.path or "/"
    else:
        path = url_or_path.split("?")[0].split("#")[0]
        # Strip leading host/base_url template variable like ${CATALOG_BASE_URL} or {self.base_url}
        path = re.sub(r"^(?:\$\{[^}]*\}|\{[^}]*\})", "", path)

    # 1. Template literal interpolations (${...} or ${}) - must run before single {}
    path = re.sub(r"\$\{[^}]*\}", "{}", path)
    # 2. Flask / Django param (<id>, <int:id>, <slug:slug>) - must run before :param
    path = re.sub(r"<[^>]+>", "{}", path)
    # 3. Next.js dynamic routes ([id], [...slug], [[...slug]])
    path = re.sub(r"\[[^\]]+\]", "{}", path)
    # 4. FastAPI / OpenAPI param ({id})
    path = re.sub(r"\{[^}]+\}", "{}", path)
    # 5. Express / Koa / Fastify / NestJS param (:id)
    path = re.sub(r"(?<=/):[a-zA-Z0-9_]+", "{}", path)

    # Normalize segment slashes
    segments = [s for s in path.strip("/").split("/") if s]
    return "/" + "/".join(segments) if segments else "/"
