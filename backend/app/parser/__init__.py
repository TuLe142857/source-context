"""
Module docs...
"""

from . import uast as uast
from . import languages as languages
from .exc import UnsupportedLanguageError as UnsupportedLanguageError
from .language_registry import LanguageConfig as LanguageConfig
from .language_registry import LanguageRegistry as LanguageRegistry

from .contracts import (
    ParseDiagnostic,
    ParseDiagnosticKind,
    ParseDiagnosticSeverity,
    ParseResult,
    ParseStatus,
    SourcePoint,
    SourceRange,
)
from .service import ParserService

__all__ = [
    "LanguageConfig",
    "LanguageRegistry",
    "UnsupportedLanguageError",
    "ParseDiagnostic",
    "ParseDiagnosticKind",
    "ParseDiagnosticSeverity",
    "ParseResult",
    "ParseStatus",
    "ParserService",
    "SourcePoint",
    "SourceRange",
]
