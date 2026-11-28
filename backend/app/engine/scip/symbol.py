"""Parse SCIP symbol strings.

A SCIP symbol is a structured, human-readable string rather than an opaque id::

    scip-python python source-context-backend 0.1.0 `app.api.routes.health`/read_health().
    <scheme>    <mgr>  <package name>         <ver> <descriptors>

Grammar (from ``scip.proto``)::

    <symbol>     ::= <scheme> ' ' <package> ' ' (<descriptor>)+ | 'local ' <local-id>
    <package>    ::= <manager> ' ' <package-name> ' ' <version>
    <descriptor> ::= <name> '/'    namespace
                   | <name> '#'    type
                   | <name> '.'    term
                   | <name> ':'    meta
                   | <name> '!'    macro
                   | <name> '(' <disambiguator> ').'   method
                   | '(' <name> ')'                    parameter
                   | '[' <name> ']'                    type parameter

Spaces inside the first four fields are escaped by doubling them, and a descriptor name
containing delimiters is wrapped in backticks (with ``` `` ``` for a literal backtick).

Parsing never raises on malformed input: indexers vary, and a symbol we cannot fully
decompose is still usable as an opaque key. Such symbols come back with
``is_well_formed=False`` so callers can report them instead of silently trusting a
wrong decomposition.
"""

from dataclasses import dataclass
from enum import StrEnum

LOCAL_PREFIX = "local "
"""Prefix marking a symbol whose scope is a single document."""

_EMPTY_FIELD = "."
"""Placeholder the SCIP grammar uses for an absent manager/package/version."""

_DESCRIPTOR_DELIMITERS = frozenset("/#.:!()[]`")


class DescriptorSuffix(StrEnum):
    """What a descriptor denotes, derived from its trailing delimiter."""

    NAMESPACE = "namespace"
    TYPE = "type"
    TERM = "term"
    METHOD = "method"
    TYPE_PARAMETER = "type_parameter"
    PARAMETER = "parameter"
    META = "meta"
    MACRO = "macro"


_SUFFIX_BY_DELIMITER = {
    "/": DescriptorSuffix.NAMESPACE,
    "#": DescriptorSuffix.TYPE,
    ".": DescriptorSuffix.TERM,
    ":": DescriptorSuffix.META,
    "!": DescriptorSuffix.MACRO,
}


@dataclass(frozen=True, slots=True)
class Descriptor:
    """One segment of a symbol's descriptor path."""

    name: str
    suffix: DescriptorSuffix


@dataclass(frozen=True, slots=True)
class ParsedSymbol:
    """A SCIP symbol string broken into its parts."""

    symbol: str
    """The original, unmodified symbol string."""

    scheme: str
    manager: str
    package: str
    version: str

    descriptors: tuple[Descriptor, ...]

    is_local: bool
    """True for ``local <id>`` symbols, whose scope is a single document."""

    is_well_formed: bool
    """False when the string could not be fully decomposed; parts are best-effort."""

    @property
    def kind(self) -> DescriptorSuffix | None:
        """What the symbol denotes, taken from its last descriptor."""

        return self.descriptors[-1].suffix if self.descriptors else None

    @property
    def display_name(self) -> str:
        """Short human-readable name: the last descriptor, or the local id."""

        if self.descriptors:
            return self.descriptors[-1].name
        if self.is_local:
            return self.symbol[len(LOCAL_PREFIX) :]
        return self.symbol

    @property
    def package_coordinate(self) -> str:
        """``<manager> <package> <version>`` — the scope in which symbols are comparable.

        Two symbols from different indexing runs denote the same thing only when their
        coordinates match as well; this is what limits naive cross-repository joins.
        """

        return f"{self.manager} {self.package} {self.version}"


def is_local_symbol(symbol: str) -> bool:
    """Return whether ``symbol`` is scoped to a single document.

    ``local 0`` in one document is unrelated to ``local 0`` in another, so these must
    be qualified with the document path before being used as a global key.
    """

    return symbol.startswith(LOCAL_PREFIX)


def parse_symbol(symbol: str) -> ParsedSymbol:
    """Decompose a SCIP symbol string.

    Args:
        symbol: Raw ``Occurrence.symbol`` / ``SymbolInformation.symbol`` value.

    Returns:
        The parsed symbol. Malformed input yields ``is_well_formed=False`` rather than
        an exception.
    """

    if is_local_symbol(symbol):
        return ParsedSymbol(
            symbol=symbol,
            scheme=LOCAL_PREFIX.strip(),
            manager="",
            package="",
            version="",
            descriptors=(),
            is_local=True,
            is_well_formed=True,
        )

    fields, remainder = _split_escaped_fields(symbol, field_count=4)
    if len(fields) < 4:
        return _malformed(symbol)

    descriptors, complete = _parse_descriptors(remainder)
    scheme, manager, package, version = fields

    return ParsedSymbol(
        symbol=symbol,
        scheme=scheme,
        manager=_decode_field(manager),
        package=_decode_field(package),
        version=_decode_field(version),
        descriptors=descriptors,
        is_local=False,
        is_well_formed=complete and bool(descriptors),
    )


def _malformed(symbol: str) -> ParsedSymbol:
    """Build a best-effort result for a symbol that does not match the grammar."""

    return ParsedSymbol(
        symbol=symbol,
        scheme="",
        manager="",
        package="",
        version="",
        descriptors=(),
        is_local=False,
        is_well_formed=False,
    )


def _decode_field(field: str) -> str:
    """Turn the ``.`` placeholder into an empty string."""

    return "" if field == _EMPTY_FIELD else field


def _split_escaped_fields(symbol: str, field_count: int) -> tuple[list[str], str]:
    """Split the leading space-separated fields, honouring the double-space escape.

    Args:
        symbol: The full symbol string.
        field_count: How many leading fields to consume.

    Returns:
        The consumed fields and the unparsed remainder. Fewer than ``field_count``
        fields are returned when the string runs out early.
    """

    fields: list[str] = []
    current: list[str] = []
    index = 0
    length = len(symbol)

    while index < length and len(fields) < field_count:
        char = symbol[index]
        if char != " ":
            current.append(char)
            index += 1
            continue

        if index + 1 < length and symbol[index + 1] == " ":
            # A doubled space is an escaped literal space, not a separator.
            current.append(" ")
            index += 2
            continue

        fields.append("".join(current))
        current = []
        index += 1

    if len(fields) < field_count:
        fields.append("".join(current))
        return fields, ""

    return fields, symbol[index:]


def _parse_descriptors(text: str) -> tuple[tuple[Descriptor, ...], bool]:
    """Parse the descriptor path of a symbol.

    Args:
        text: Everything after the version field.

    Returns:
        The descriptors parsed, and whether the whole string was consumed.
    """

    descriptors: list[Descriptor] = []
    index = 0
    length = len(text)

    while index < length:
        char = text[index]

        if char in "([":
            closing = ")" if char == "(" else "]"
            suffix = (
                DescriptorSuffix.PARAMETER
                if char == "("
                else DescriptorSuffix.TYPE_PARAMETER
            )
            name, index, ok = _read_until(text, index + 1, closing)
            if not ok:
                return tuple(descriptors), False
            descriptors.append(Descriptor(name=name, suffix=suffix))
            continue

        name, index, ok = _read_name(text, index)
        if not ok or index >= length:
            return tuple(descriptors), False

        delimiter = text[index]

        if delimiter == "(":
            # Method: '(' <disambiguator> ').' — the disambiguator is discarded.
            _, index, ok = _read_until(text, index + 1, ")")
            if not ok or index >= length or text[index] != ".":
                return tuple(descriptors), False
            index += 1
            descriptors.append(Descriptor(name=name, suffix=DescriptorSuffix.METHOD))
            continue

        suffix_kind = _SUFFIX_BY_DELIMITER.get(delimiter)
        if suffix_kind is None:
            return tuple(descriptors), False

        index += 1
        descriptors.append(Descriptor(name=name, suffix=suffix_kind))

    return tuple(descriptors), True


def _read_name(text: str, index: int) -> tuple[str, int, bool]:
    """Read one descriptor name, backtick-escaped or simple.

    Returns:
        The name, the index just past it, and whether reading succeeded.
    """

    if index < len(text) and text[index] == "`":
        return _read_escaped_name(text, index + 1)

    start = index
    while index < len(text) and text[index] not in _DESCRIPTOR_DELIMITERS:
        index += 1
    return text[start:index], index, index > start


def _read_escaped_name(text: str, index: int) -> tuple[str, int, bool]:
    """Read a backtick-quoted name, where ``` `` ``` denotes a literal backtick."""

    chars: list[str] = []
    length = len(text)

    while index < length:
        if text[index] != "`":
            chars.append(text[index])
            index += 1
            continue

        if index + 1 < length and text[index + 1] == "`":
            chars.append("`")
            index += 2
            continue

        return "".join(chars), index + 1, True

    return "".join(chars), index, False


def _read_until(text: str, index: int, closing: str) -> tuple[str, int, bool]:
    """Read up to ``closing``.

    Returns:
        The text read, the index just past the closing delimiter, and whether the
        delimiter was found.
    """

    end = text.find(closing, index)
    if end == -1:
        return text[index:], len(text), False
    return text[index:end], end + 1, True
