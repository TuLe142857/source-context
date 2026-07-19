# Source Context Backend

# Directory Structure
```text
backend
backend
├── app                 # Server here
│   ├── core                # Core
│   ├── languages           # Language: plugins for module parser - custom for each language
│   ├── parser              # Parser: tree-sitter, uast, converter, ...
│   ├── scanner             # Repo scanner
│   ├── util                # Shared utility classes/methods for backend
│   ├── __init__.py         # Python module init
│   └── main.py             # Entry point, container FastAPI object to run server
│   
├── cli                 # Script cli, use for debug, ....
├── app                 # documents for modules, ...
├── tests               # pytest
├── Dockerfile
├── pyproject.toml
└── README.md
```

# Use cli
```text
uv run python -m cli
```