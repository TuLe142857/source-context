"""Read-only view of one project for the API detectors."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from tree_sitter import Tree

from app.engine.parser import UnsupportedLanguageError
from app.engine.parser.languages import get_language_registry
from app.engine.parser.uast import ImportNode, UASTNode
from app.engine.scip.index_reader import SymbolTable
from app.engine.scip.position import LineIndex
from app.engine.scip.symbol import DescriptorSuffix, parse_symbol

logger = logging.getLogger(__name__)


def walk(node: UASTNode) -> Iterator[UASTNode]:
    """Yield a UAST node and all its descendants, depth first, in source order."""

    yield node
    for child in node.children:
        yield from walk(child)


class ApiMapContext:
    """Sources, CST, UAST and SCIP lookups of one project, loaded lazily and cached per file.

    Detectors read only through this object: they never touch Neo4j, so they run on a fixture
    directory with a checked-in ``index.scip`` as well as inside the indexing pipeline.
    """

    def __init__(
        self,
        project_id: int,
        project_root: Path,
        file_uids: dict[str, str],
        symbols: SymbolTable | None = None,
        uast_roots: dict[str, UASTNode] | None = None,
    ) -> None:
        """
        Args:
            project_id: ``uid`` of the ``ProjectNodeModel``.
            project_root: Directory every file path is relative to.
            file_uids: Relative path -> ``FileNodeModel.uid`` of the files indexed in this run.
            symbols: Symbol table of the project's SCIP index, ``None`` when there is no index.
            uast_roots: Stage-2 UAST roots by path. Their ids are the Neo4j uids, so anchors can be
                resolved in memory; without them each file's UAST is converted again from its CST.
        """

        self.project_id = project_id
        self.project_root = project_root
        self.file_uids = file_uids
        self.symbols = symbols
        """``None`` without a SCIP index: detectors fall back to same-file resolution."""

        self.memo: dict[str, Any] = {}
        """Per-project scratch space of detectors (object resolution cache, router graph...)."""

        self._persisted: dict[str, UASTNode] = dict(uast_roots or {})
        self._uast: dict[str, UASTNode] = dict(self._persisted)
        self._source: dict[str, bytes] = {}
        self._tree: dict[str, Tree] = {}
        self._lines: dict[str, LineIndex] = {}
        self._spans: dict[str, dict[tuple[int, int], str]] = {}
        self._imports: dict[str, dict[str, str]] = {}

    # ------------------------------------------------------------------ files

    def paths(self, language: str) -> list[str]:
        """Project files of one language, sorted."""

        registry = get_language_registry()
        result = []
        for path in sorted(self.file_uids):
            try:
                if registry.resolve_language_name(path) == language:
                    result.append(path)
            except UnsupportedLanguageError:
                continue
        return result

    def languages(self) -> set[str]:
        """Languages present among the project files."""

        registry = get_language_registry()
        found = set()
        for path in self.file_uids:
            try:
                found.add(registry.resolve_language_name(path))
            except UnsupportedLanguageError:
                continue
        return found

    def source(self, path: str) -> bytes:
        if path not in self._source:
            self._source[path] = (self.project_root / path).read_bytes()
        return self._source[path]

    def text(self, path: str, start_byte: int, end_byte: int) -> str:
        return self.source(path)[start_byte:end_byte].decode("utf-8", errors="replace")

    def tree(self, path: str) -> Tree:
        """Tree-sitter CST of the file, parsed once."""

        if path not in self._tree:
            parser = get_language_registry().get_parser_for_file(path)
            self._tree[path] = parser.parse(self.source(path))
        return self._tree[path]

    def persisted_root(self, path: str) -> UASTNode | None:
        """The stage-2 root of a file: its ids are the Neo4j uids, so anchors resolve in memory."""

        return self._persisted.get(path)

    def uast(self, path: str) -> UASTNode:
        """Stage-2 UAST root when given, else converted from :meth:`tree` (no second parse)."""

        if path not in self._uast:
            converter = get_language_registry().get_converter_for_file(path)
            self._uast[path] = converter.convert(
                self.tree(path), self.source(path), path
            )
        return self._uast[path]

    # ------------------------------------------------------------------ SCIP

    def symbol_at(self, path: str, start_byte: int, end_byte: int) -> str | None:
        """Qualified SCIP symbol of the occurrence covering exactly this identifier span."""

        if self.symbols is None:
            return None
        if path not in self._spans:
            spans: dict[tuple[int, int], str] = {}
            for occurrence in self.symbols.occurrences_by_document.get(path, []):
                try:
                    span = self._line_index(path).range_to_bytes(occurrence.scip_range)
                except (ValueError, OSError):
                    continue
                spans.setdefault(span, occurrence.symbol)
            self._spans[path] = spans
        return self._spans[path].get((start_byte, end_byte))

    def definition_site(self, symbol: str) -> tuple[str, int, int] | None:
        """``(path, start_byte, end_byte)`` of the first definition of a *project* symbol.

        ``None`` for symbols defined outside the project, and for unresolved imports, which
        scip-python reports as plain references without any definition.
        """

        if self.symbols is None:
            return None
        sites = self.symbols.definitions.get(symbol)
        if not sites or sites[0].document_path not in self.file_uids:
            return None
        try:
            start, end = self._line_index(sites[0].document_path).range_to_bytes(
                sites[0].scip_range
            )
        except (ValueError, OSError):
            return None
        return sites[0].document_path, start, end

    def scip_owner(self, path: str, start_byte: int, end_byte: int) -> str | None:
        """Tier A: owner of a called name according to SCIP, language independent.

        ``fastapi.routing/APIRouter#get().`` -> ``"fastapi.routing.APIRouter()"`` (a type owner is an
        instance); ``requests.api/get().`` -> ``"requests.api"``. ``None`` for locals, unknown and
        project symbols. Only descriptors are read: scip-python package names are unreliable.
        Gives something only when the indexing sandbox had the library installed.
        """

        symbol = self.symbol_at(path, start_byte, end_byte)
        if symbol is None or self.definition_site(symbol) is not None:
            return None
        parsed = parse_symbol(symbol)
        if not parsed.is_well_formed or len(parsed.descriptors) < 2:
            return None
        owner = parsed.descriptors[:-1]
        qualname = ".".join(descriptor.name for descriptor in owner)
        return (
            f"{qualname}()" if owner[-1].suffix == DescriptorSuffix.TYPE else qualname
        )

    # ------------------------------------------------------------------ imports

    def import_table(self, path: str) -> dict[str, str]:
        """Local name -> qualified name, from the file's ``ImportNode``.

        ``import httpx as hx`` -> ``{"hx": "httpx"}``; ``import os.path`` -> ``{"os": "os"}``;
        ``from fastapi import APIRouter as R`` -> ``{"R": "fastapi.APIRouter"}``.
        JS/TS: ``import axios from "axios"`` and ``const axios = require("axios")`` -> ``{"axios":
        "axios"}`` (a default export stands for the module); ``import { Router } from "express"``
        -> ``{"Router": "express.Router"}``; ``import "./styles.css"`` binds nothing.
        """

        if path not in self._imports:
            python = self.language_of(path) == "python"
            table: dict[str, str] = {}
            for node in walk(self.uast(path)):
                if not isinstance(node, ImportNode) or not node.module_path:
                    continue
                module = node.module_path
                if (
                    not node.imported_names
                ):  # module form: `import a.b [as c]`, `import * as c`
                    alias = node.alias.get(module)
                    if alias is not None:
                        table[alias] = module
                    elif python:  # `import a.b` binds `a`
                        top = module.split(".")[0]
                        table[top] = top
                for (
                    name
                ) in node.imported_names:  # `from a import b [as c]`, `import { b }`
                    if name == "*":
                        continue
                    local = node.alias.get(name, name)
                    table[local] = (
                        module
                        if name == "default" and not python
                        else f"{module}.{name}"
                    )
            self._imports[path] = table
        return self._imports[path]

    def language_of(self, path: str) -> str | None:
        try:
            return get_language_registry().resolve_language_name(path)
        except UnsupportedLanguageError:
            return None

    def _line_index(self, path: str) -> LineIndex:
        if path not in self._lines:
            self._lines[path] = LineIndex(self.source(path))
        return self._lines[path]
