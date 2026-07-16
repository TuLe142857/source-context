---
trigger: always_on
---

This file provides Python coding rules that any developer/agent must follow for the `backend/` and `mcp/` directories.

## Package Management & Tooling
- **Dependency Management:** Use only `uv` for all package management and running scripts.
- **Linting & Formatting:** The project uses `ruff` and `mypy`. After making any changes to Python code, you MUST automatically run the following commands:
  - `uv run ruff format .`
  - `uv run ruff check --fix .`
  - `uv run mypy .`
- Ensure that no linting or typing errors remain before completing your task.

## Typing & Modern Syntax
- **Strict Typing:** All functions, methods, and variables must have explicit type hints. `mypy` is configured with `strict = true`.
- **Modern Python (3.10+):**
  - Use the `|` operator for unions (e.g., `str | int` instead of `Union[str, int]`).
  - Use `| None` for optional types (e.g., `str | None` instead of `Optional[str]`).
  - Use built-in generic collections (`list`, `dict`, `set`, `tuple`) instead of imports from the `typing` module.

## Documentation
- **Docstrings Required:** Every public module, class, and function MUST have a docstring.
- **Style:** Use **Google Style** docstrings exclusively.
- **Example:**
  ```python
  def fetch_data(url: str, timeout: int = 10) -> dict | None:
      """Fetches data from the given URL.

      Args:
          url (str): The URL to fetch data from.
          timeout (int, optional): The timeout in seconds. Defaults to 10.

      Returns:
          dict | None: The JSON response as a dictionary, or None if the request fails.
      """
  ```

## Code Structure & Error Handling
- Imports must be sorted automatically using `ruff check --fix .`.
- Avoid catching generic `Exception`. Always catch specific exceptions where possible to avoid swallowing unexpected errors.
