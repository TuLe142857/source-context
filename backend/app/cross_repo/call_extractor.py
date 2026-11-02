import re
from typing import Sequence
from app.parser.uast import UASTNode, FunctionNode
from app.route_extractor.normalizer import canonicalize_url_path
from .ir import ClientCallSite


class UniversalClientCallExtractor:
    """Extracts outgoing HTTP/RPC client calls from Python, TypeScript, and JavaScript code."""

    def extract_calls(
        self,
        file_path: str,
        code_bytes: bytes,
        project_id: int,
        uast_root: UASTNode | None = None,
    ) -> Sequence[ClientCallSite]:
        p = file_path.lower()
        if p.endswith(".py"):
            return self._extract_python_calls(file_path, code_bytes, project_id, uast_root)
        if p.endswith((".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")):
            return self._extract_javascript_calls(file_path, code_bytes, project_id, uast_root)
        return []

    def _extract_python_calls(
        self,
        file_path: str,
        code_bytes: bytes,
        project_id: int,
        uast_root: UASTNode | None,
    ) -> list[ClientCallSite]:
        text = code_bytes.decode("utf-8", errors="ignore")
        if "requests." not in text and "httpx" not in text and "client." not in text and "urlopen" not in text:
            return []

        calls: list[ClientCallSite] = []
        functions = self._flatten_functions(uast_root) if uast_root else []

        # 1. requests.get/post/put/delete or client.get/post/put/delete
        # Example: requests.post(endpoint, json=payload), client.get(f"{self.base_url}/api/v1/billing/invoices/{invoice_id}")
        py_pattern = re.compile(
            r"(?:requests|client|httpx|session)\.(get|post|put|delete|patch|options|head)\s*\(\s*([fF]?['\"][^'\"]+['\"]|[a-zA-Z0-9_.]+)",
            re.MULTILINE,
        )
        for m in py_pattern.finditer(text):
            method = m.group(1).upper()
            raw_arg = m.group(2).strip("fF'\"")

            # Resolve local variable if argument is an identifier
            resolved_url = raw_arg
            if re.match(r"^[a-zA-Z0-9_]+$", raw_arg):
                var_match = re.search(
                    rf"{raw_arg}\s*=\s*(?:f['\"]|['\"]|os\.getenv\([^,]+,\s*['\"])([^'\"]+)",
                    text,
                )
                if var_match:
                    resolved_url = var_match.group(1)

            # Skip calls that do not look like URL paths or external services
            canonical = canonicalize_url_path(resolved_url)
            if not self._is_valid_route_target(canonical):
                continue

            enclosing_fn = self._find_enclosing_function(m.start(), functions)
            calls.append(
                ClientCallSite(
                    caller_func_uid=enclosing_fn.id if enclosing_fn else None,
                    caller_func_name=enclosing_fn.name if enclosing_fn else "anonymous",
                    file_path=file_path,
                    project_id=project_id,
                    method=method,
                    raw_path=resolved_url,
                    canonical_path=canonical,
                    client_library="requests/httpx",
                    metadata={"offset": m.start()},
                )
            )

        return calls

    def _extract_javascript_calls(
        self,
        file_path: str,
        code_bytes: bytes,
        project_id: int,
        uast_root: UASTNode | None,
    ) -> list[ClientCallSite]:
        text = code_bytes.decode("utf-8", errors="ignore")
        if "axios" not in text and "fetch(" not in text and "apiClient" not in text:
            return []

        calls: list[ClientCallSite] = []
        functions = self._flatten_functions(uast_root) if uast_root else []

        # 1. axios.get<T>(url), axios.post(url), apiClient.get(url)
        axios_pattern = re.compile(
            r"(?:axios|client|apiClient|api)\.(get|post|put|delete|patch)\s*(?:<[^>]+>)?\s*\(\s*([`'\"][^`'\"]+[`'\"]|[a-zA-Z0-9_.]+)",
            re.MULTILINE,
        )
        for m in axios_pattern.finditer(text):
            method = m.group(1).upper()
            raw_arg = m.group(2).strip("`'\"")

            resolved_url = raw_arg
            if re.match(r"^[a-zA-Z0-9_]+$", raw_arg):
                var_match = re.search(rf"{raw_arg}\s*=\s*[`'\"]([^`'\"]+)[`'\"]", text)
                if var_match:
                    resolved_url = var_match.group(1)

            canonical = canonicalize_url_path(resolved_url)
            if not self._is_valid_route_target(canonical):
                continue

            enclosing_fn = self._find_enclosing_function(m.start(), functions)
            calls.append(
                ClientCallSite(
                    caller_func_uid=enclosing_fn.id if enclosing_fn else None,
                    caller_func_name=enclosing_fn.name if enclosing_fn else "anonymous",
                    file_path=file_path,
                    project_id=project_id,
                    method=method,
                    raw_path=resolved_url,
                    canonical_path=canonical,
                    client_library="axios",
                    metadata={"offset": m.start()},
                )
            )

        # 2. fetch(`${URL}/path`)
        fetch_pattern = re.compile(
            r"fetch\s*\(\s*([`'\"][^`'\"]+[`'\"]|[a-zA-Z0-9_.]+)(?:[,\s]+(\{[^}]*\}))?",
            re.MULTILINE,
        )
        for m in fetch_pattern.finditer(text):
            raw_arg = m.group(1).strip("`'\"")
            options = m.group(2) or ""

            # Check method in fetch options, default is GET
            method = "GET"
            method_match = re.search(r"method\s*:\s*['\"]([a-zA-Z]+)['\"]", options)
            if method_match:
                method = method_match.group(1).upper()

            resolved_url = raw_arg
            if re.match(r"^[a-zA-Z0-9_]+$", raw_arg):
                var_match = re.search(rf"{raw_arg}\s*=\s*[`'\"]([^`'\"]+)[`'\"]", text)
                if var_match:
                    resolved_url = var_match.group(1)

            canonical = canonicalize_url_path(resolved_url)
            if not self._is_valid_route_target(canonical):
                continue

            enclosing_fn = self._find_enclosing_function(m.start(), functions)
            calls.append(
                ClientCallSite(
                    caller_func_uid=enclosing_fn.id if enclosing_fn else None,
                    caller_func_name=enclosing_fn.name if enclosing_fn else "anonymous",
                    file_path=file_path,
                    project_id=project_id,
                    method=method,
                    raw_path=resolved_url,
                    canonical_path=canonical,
                    client_library="fetch",
                    metadata={"offset": m.start()},
                )
            )

        return calls

    def _is_valid_route_target(self, canonical: str) -> bool:
        # A valid route must start with '/' and have at least one meaningful segment
        return bool(canonical and canonical != "/" and canonical.startswith("/"))

    def _flatten_functions(self, node: UASTNode) -> list[FunctionNode]:
        res: list[FunctionNode] = []
        if isinstance(node, FunctionNode):
            res.append(node)
        for child in getattr(node, "children", []):
            res.extend(self._flatten_functions(child))
        return res

    def _find_enclosing_function(
        self,
        offset: int,
        functions: list[FunctionNode],
    ) -> FunctionNode | None:
        best_match: FunctionNode | None = None
        for fn in functions:
            if fn.start_byte <= offset <= fn.end_byte:
                if best_match is None or (fn.end_byte - fn.start_byte) < (best_match.end_byte - best_match.start_byte):
                    best_match = fn
        return best_match
