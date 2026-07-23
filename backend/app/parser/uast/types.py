from __future__ import annotations

from typing import Literal, get_args

# ========================================
#       Container
# ========================================
ContainerCapture = Literal[
    "container.project",
    "container.module",
    "container.file",
]
CONTAINER_CAPTURES = get_args(ContainerCapture)


# ========================================
#       Definition
# ========================================
TypeDefinitionCapture = Literal[
    "definition.interface",
    "definition.enum",
    "definition.struct",
    "definition.trait",
    "definition.protocol",
    "definition.class",
]
TYPE_DEFINITION_CAPTURES = get_args(TypeDefinitionCapture)

FunctionLikeCapture = Literal[
    "definition.method",
    "definition.constructor",
    "definition.lambda",
    "definition.function",
]
FUNCTION_LIKE_CAPTURES = get_args(FunctionLikeCapture)

VariableLikeCapture = Literal[
    "definition.field",
    "definition.constant",
    "definition.parameter",
    "definition.variable",
]
VARIABLE_LIKE_CAPTURES = get_args(VariableLikeCapture)


type DefinitionCapture = (
    TypeDefinitionCapture | FunctionLikeCapture | VariableLikeCapture
)
DEFINITION_CAPTURES = (
    TYPE_DEFINITION_CAPTURES + FUNCTION_LIKE_CAPTURES + VARIABLE_LIKE_CAPTURES
)

# ========================================
#       Reference
# ========================================
type ReferenceCapture = Literal[
    "reference.call",
    "reference.attribute",
    "reference.type",
]
REFERENCE_CAPTURES = get_args(ReferenceCapture.__value__)

# ========================================
#       Dependency
# ========================================

type DependencyCapture = Literal[
    "dependency.import",
    "dependency.export",
]
DEPENDENCY_CAPTURES = get_args(DependencyCapture.__value__)

# ========================================
#       Metadata
# ========================================

type MetaCaptureType = Literal[
    "meta.name",
    "meta.doc",
    "meta.modifier",
    "meta.visibility",
    "meta.base_type",
    "meta.type",
    "meta.value",
    "meta.enum_value",
    "meta.decorator",
    "meta.module_path",
    "meta.alias",
    "meta.subject",
]
META_CAPTURES = get_args(MetaCaptureType.__value__)


type CaptureType = (
    ContainerCapture
    | DefinitionCapture
    | ReferenceCapture
    | DependencyCapture
    | MetaCaptureType
    | str
)


def is_definition_capture(capture_name: CaptureType) -> bool:
    return any(
        [
            capture_name in TYPE_DEFINITION_CAPTURES,
            capture_name in FUNCTION_LIKE_CAPTURES,
            capture_name in VARIABLE_LIKE_CAPTURES,
        ]
    )


def is_type_def_capture(capture_name: CaptureType) -> bool:
    """
    Check if a capture_name is a type definition capture.

    Args:
        capture_name: capture name

    Returns:
        true or false
    """
    return capture_name in TYPE_DEFINITION_CAPTURES


def is_variable_like_capture(capture_name: CaptureType) -> bool:
    return capture_name in TYPE_DEFINITION_CAPTURES


def is_function_like_capture(capture_name: CaptureType) -> bool:
    return capture_name in FUNCTION_LIKE_CAPTURES


def is_dependency_capture(capture_name: CaptureType) -> bool:
    return capture_name in DEPENDENCY_CAPTURES


def is_reference_capture(capture_name: CaptureType) -> bool:
    return capture_name in REFERENCE_CAPTURES


if __name__ == "__main__":
    print(
        f"Type def: {TYPE_DEFINITION_CAPTURES}",
        f"Function def: {FUNCTION_LIKE_CAPTURES}",
        f"Variable def: {VARIABLE_LIKE_CAPTURES}",
        sep="\n",
    )
