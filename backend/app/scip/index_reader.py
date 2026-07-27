"""Read a SCIP ``Index`` into a lookup-friendly symbol table.

This is a single pass over every occurrence in the index. It answers the three
questions the graph builder needs:

* where is a symbol *defined*? (``definitions``)
* which symbols does a given document *mention*, and at what source range?
  (``occurrences_by_document``)
* which file does a module symbol correspond to? (``document_by_module_symbol``)

Two properties of real indexer output shape the design:

``symbol_roles`` carries almost no information
    ``scip-python`` only ever emits ``Definition`` (1) and ``ReadAccess`` (8) — never
    ``Import`` or ``WriteAccess``. The single reliable distinction is therefore
    "definition or not"; anything finer has to come from the UAST node type.

``local N`` is scoped to one document
    ``local 0`` in two different files are unrelated symbols. Every symbol read here is
    passed through :func:`qualify_symbol` so it can safely be used as a global key.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from app.scip import scip_pb2
from app.scip.symbol import is_local_symbol

_DEFINITION_ROLE = scip_pb2.Definition


@dataclass(frozen=True, slots=True)
class DefinitionSite:
    """Where a symbol is defined."""

    document_path: str
    scip_range: tuple[int, ...]
    """Range of the *identifier* only."""

    enclosing_range: tuple[int, ...]
    """Range of the whole definition body, or empty when the indexer omitted it."""


@dataclass(frozen=True, slots=True)
class SymbolOccurrence:
    """One mention of a symbol inside a document."""

    scip_range: tuple[int, ...]
    symbol: str
    """Qualified symbol — document-scoped locals already carry their document."""

    is_definition: bool


@dataclass(frozen=True, slots=True)
class InheritanceEdge:
    """A ``is_implementation`` relationship between two symbols."""

    child_symbol: str
    parent_symbol: str


@dataclass(slots=True)
class SymbolTable:
    """Everything the graph builder needs from a SCIP index."""

    definitions: dict[str, list[DefinitionSite]] = field(default_factory=dict)
    """Qualified symbol -> its definition sites. A list because a symbol can be
    defined more than once (conditional definitions, ``@overload``, re-assignment)."""

    occurrences_by_document: dict[str, list[SymbolOccurrence]] = field(
        default_factory=dict
    )
    """Document path -> every occurrence in it, in index order."""

    document_by_module_symbol: dict[str, str] = field(default_factory=dict)
    """Module symbol -> the document that defines it."""

    module_symbol_by_document: dict[str, str] = field(default_factory=dict)
    """Document path -> the module symbol it defines."""

    inheritance_edges: list[InheritanceEdge] = field(default_factory=list)
    """Child/parent pairs from ``SymbolInformation.relationships``."""

    referenced_symbols: set[str] = field(default_factory=set)
    """Every qualified symbol mentioned anywhere, definitions included."""

    project_root: str = ""
    """``Metadata.project_root`` — a URI, and a path *inside the indexer sandbox*."""

    tool_name: str = ""
    tool_version: str = ""

    def is_defined(self, symbol: str) -> bool:
        """Whether the index contains a definition site for ``symbol``."""

        return symbol in self.definitions

    def external_symbols(self) -> set[str]:
        """Symbols referenced by this project but defined outside it.

        Package name cannot be used for this test: indexers routinely attribute
        third-party modules to the project's own package (``scip-python`` files
        ``fastapi`` under ``source-context-backend``). Absence of a definition site
        anywhere in the index is the reliable signal.

        Document-scoped locals are excluded — an unresolved local is a binding the
        indexer gave up on, not a package dependency.
        """

        return {
            symbol
            for symbol in self.referenced_symbols
            if symbol not in self.definitions and not is_local_symbol(symbol)
        }

    def document_paths(self) -> set[str]:
        """Every document path present in the index."""

        return set(self.occurrences_by_document)


def qualify_symbol(symbol: str, document_path: str) -> str:
    """Make a document-scoped symbol globally unique.

    ``local 0`` means something different in every document, so it is namespaced with
    the document that owns it. Global symbols are returned unchanged.

    Args:
        symbol: Raw symbol string from the index.
        document_path: Path of the document the symbol was read from.

    Returns:
        A symbol usable as a key across the whole index.
    """

    if is_local_symbol(symbol):
        return f"{symbol}@{document_path}"
    return symbol


def read_index(index: scip_pb2.Index) -> SymbolTable:
    """Build a :class:`SymbolTable` from a parsed SCIP index.

    Args:
        index: The ``Index`` message, already deserialized.

    Returns:
        The symbol table. One pass, ``O(number of occurrences)``.
    """

    definitions: dict[str, list[DefinitionSite]] = defaultdict(list)
    occurrences_by_document: dict[str, list[SymbolOccurrence]] = {}
    document_by_module_symbol: dict[str, str] = {}
    module_symbol_by_document: dict[str, str] = {}
    inheritance_edges: list[InheritanceEdge] = []
    referenced_symbols: set[str] = set()

    for document in index.documents:
        document_path = document.relative_path
        occurrences: list[SymbolOccurrence] = []

        for occurrence in document.occurrences:
            if not occurrence.symbol:
                continue

            scip_range = tuple(occurrence.range)
            qualified = qualify_symbol(occurrence.symbol, document_path)
            is_definition = bool(occurrence.symbol_roles & _DEFINITION_ROLE)

            referenced_symbols.add(qualified)
            occurrences.append(
                SymbolOccurrence(
                    scip_range=scip_range,
                    symbol=qualified,
                    is_definition=is_definition,
                )
            )

            if not is_definition:
                continue

            definitions[qualified].append(
                DefinitionSite(
                    document_path=document_path,
                    scip_range=scip_range,
                    enclosing_range=tuple(occurrence.enclosing_range),
                )
            )

            if (
                _is_module_definition(scip_range)
                and document_path not in module_symbol_by_document
            ):
                module_symbol_by_document[document_path] = occurrence.symbol
                document_by_module_symbol[occurrence.symbol] = document_path

        occurrences_by_document[document_path] = occurrences

        for symbol_information in document.symbols:
            _collect_inheritance(
                symbol_information, inheritance_edges, referenced_symbols
            )

    for symbol_information in index.external_symbols:
        _collect_inheritance(symbol_information, inheritance_edges, referenced_symbols)

    return SymbolTable(
        definitions=dict(definitions),
        occurrences_by_document=occurrences_by_document,
        document_by_module_symbol=document_by_module_symbol,
        module_symbol_by_document=module_symbol_by_document,
        inheritance_edges=inheritance_edges,
        referenced_symbols=referenced_symbols,
        project_root=index.metadata.project_root,
        tool_name=index.metadata.tool_info.name,
        tool_version=index.metadata.tool_info.version,
    )


def _is_module_definition(scip_range: tuple[int, ...]) -> bool:
    """Whether a definition range marks a document's own module symbol.

    Indexers emit the module symbol as a zero-width definition at the very start of the
    file (``[0, 0, 0]``). Detecting it by range rather than by name keeps this working
    across languages, where the module descriptor differs (``/__init__:`` for Python,
    a file namespace for TypeScript).
    """

    if len(scip_range) == 3:
        return scip_range[0] == 0 and scip_range[1] == 0 and scip_range[2] == 0
    if len(scip_range) == 4:
        return scip_range[:4] == (0, 0, 0, 0)
    return False


def _collect_inheritance(
    symbol_information: scip_pb2.SymbolInformation,
    inheritance_edges: list[InheritanceEdge],
    referenced_symbols: set[str],
) -> None:
    """Record the ``is_implementation`` relationships of one symbol.

    ``relationships`` is the only part of ``SymbolInformation`` that real indexer output
    actually populates — ``kind``, ``display_name`` and ``enclosing_symbol`` all come
    back empty — so it is the only usable source for inheritance edges.

    Parents count as referenced even when nothing in the index mentions them at a source
    range, which is how a base class the project never names directly still shows up as
    an external dependency.
    """

    for relationship in symbol_information.relationships:
        if not relationship.is_implementation or not relationship.symbol:
            continue
        inheritance_edges.append(
            InheritanceEdge(
                child_symbol=symbol_information.symbol,
                parent_symbol=relationship.symbol,
            )
        )
        referenced_symbols.add(relationship.symbol)
