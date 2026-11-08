"""Fixtures of the API map tests.

``fixtures/fastapi_sample`` is a small FastAPI + requests/httpx project, read as source code only
(never imported). Its two SCIP indexes come from the real sandbox image:

* ``index.scip``: ``sandbox/python313`` as used in production, project dependencies NOT installed;
* ``index_with_deps.scip``: same image after ``pip install fastapi requests httpx`` (Tier A).

Regenerate after editing the sample::

    cd backend/tests/test_api_map/fixtures/fastapi_sample
    docker run --rm -v $PWD:/sandbox/projects/s:ro -v /tmp/out:/sandbox/output \\
        -w /sandbox/projects/s sandbox/python313:latest scip-python index --output /sandbox/output/index.scip
"""

from collections.abc import Callable
from pathlib import Path

import pytest

from app.engine.api_map import ApiMapContext
from app.engine.scip import scip_pb2
from app.engine.scip.index_reader import SymbolTable, read_index

collect_ignore_glob = ["fixtures/*"]

SAMPLE = Path(__file__).parent / "fixtures" / "fastapi_sample"


def load_symbols(name: str) -> SymbolTable:
    index = scip_pb2.Index()
    index.ParseFromString((SAMPLE / name).read_bytes())
    return read_index(index)


def sample_files(prefix: str = "") -> dict[str, str]:
    """Relative path -> fake File uid for the sample's Python files under ``prefix``."""

    return {
        str(path.relative_to(SAMPLE)): f"file:{path.relative_to(SAMPLE)}"
        for path in sorted(SAMPLE.rglob("*.py"))
        if str(path.relative_to(SAMPLE)).startswith(prefix)
    }


def sample_context(
    index: str | None = "index.scip", project_id: int = 1, prefix: str = ""
) -> ApiMapContext:
    return ApiMapContext(
        project_id,
        SAMPLE,
        sample_files(prefix),
        load_symbols(index) if index is not None else None,
    )


type MakeContext = Callable[..., ApiMapContext]


@pytest.fixture
def make_ctx() -> MakeContext:
    """``make_ctx(index="index.scip" | "index_with_deps.scip" | None, project_id=1, prefix="")``."""

    return sample_context


EXPRESS_SAMPLE = Path(__file__).parent / "fixtures" / "express_sample"
"""Two JS/TS projects, each with the index ``sandbox/node24`` produces for it:
``server`` (TypeScript: Express routers, NestJS controller) and ``client`` (JavaScript: axios,
fetch). Indexed through a writable copy, see ``app/engine/scip/sandbox.py``."""


def js_context(project: str, index: bool = True, project_id: int = 1) -> ApiMapContext:
    root = EXPRESS_SAMPLE / project
    files = {
        str(path.relative_to(root)): f"file:{project}/{path.relative_to(root)}"
        for path in sorted(root.rglob("*"))
        if path.suffix in (".js", ".ts")
    }
    symbols = None
    if index:
        scip = scip_pb2.Index()
        scip.ParseFromString((root / "index.scip").read_bytes())
        symbols = read_index(scip)
    return ApiMapContext(project_id, root, files, symbols)


@pytest.fixture
def make_js_ctx() -> Callable[..., ApiMapContext]:
    """``make_js_ctx("server" | "client", index=True, project_id=1)``."""

    return js_context


@pytest.fixture
def sample_root() -> Path:
    return SAMPLE


@pytest.fixture
def ctx() -> ApiMapContext:
    """Sample project with the production-like index (no third-party packages)."""

    return sample_context("index.scip")
