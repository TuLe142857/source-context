from typing import Literal

type ContainerCaptureType = Literal[
    "container.project",
    "container.module",
    "container.file",
]

type DefinitionCaptureType = Literal[
    "definition.interface",
    "definition.enum",
    "definition.struct",
    "definition.trait",
    "definition.protocol",
    "definition.class",
    "definition.method",
    "definition.constructor",
    "definition.lambda",
    "definition.function",
    "definition.field",
    "definition.constant",
    "definition.parameter",
    "definition.variable",
]

type ReferenceCaptureType = Literal[
    "reference.call",
    "reference.attribute",
    "reference.type",
]

type DependencyCaptureType = Literal[
    "dependency.import",
    "dependency.export",
]

type MetaCaptureType = Literal[
    "meta.name",
    "meta.comment",
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
    "meta.receiver",
]


type CaptureType = (
    ContainerCaptureType | DefinitionCaptureType | ReferenceCaptureType | DependencyCaptureType | MetaCaptureType | str
)
