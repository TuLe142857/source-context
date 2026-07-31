; Python -> UAST query
;
; Queries identify semantic node boundaries.
; Python-specific field extraction is performed by adapter handlers.

; ---------------------------------------------------------------------------
; Documentation and decorators
; ---------------------------------------------------------------------------

(module
  . (expression_statement
      (string) @meta.doc))

(function_definition
  body: (block
    . (expression_statement
        (string) @meta.doc)))

(class_definition
  body: (block
    . (expression_statement
        (string) @meta.doc)))

(decorator) @meta.decorator


; ---------------------------------------------------------------------------
; Type definitions
; ---------------------------------------------------------------------------

(class_definition) @definition.class


; ---------------------------------------------------------------------------
; Function-like definitions
; ---------------------------------------------------------------------------

; Constructors have the highest capture priority.

(class_definition
  body: (block
    (function_definition
      name: (identifier) @_.constructor_name
      (#eq? @_.constructor_name "__init__"))
      @definition.constructor))

(class_definition
  body: (block
    (decorated_definition
      definition: (function_definition
        name: (identifier) @_.decorated_constructor_name
        (#eq? @_.decorated_constructor_name "__init__"))
        @definition.constructor)))


; Direct and decorated methods.

(class_definition
  body: (block
    (function_definition)
      @definition.method))

(class_definition
  body: (block
    (decorated_definition
      definition: (function_definition)
        @definition.method)))


; Generic function capture.
; Method and constructor captures win through adapter priority.

(function_definition) @definition.function

(lambda) @definition.lambda


; ---------------------------------------------------------------------------
; Parameters
; ---------------------------------------------------------------------------

; Plain positional parameters.

(parameters
  (identifier) @definition.parameter)

(lambda_parameters
  (identifier) @definition.parameter)


; Typed, default and typed-default parameters.

(typed_parameter) @definition.parameter

(default_parameter) @definition.parameter

(typed_default_parameter) @definition.parameter


; Untyped *args and **kwargs.
; Typed splats are represented by the enclosing typed_parameter node.

(parameters
  (list_splat_pattern) @definition.parameter)

(parameters
  (dictionary_splat_pattern) @definition.parameter)

(lambda_parameters
  (list_splat_pattern) @definition.parameter)

(lambda_parameters
  (dictionary_splat_pattern) @definition.parameter)


; ---------------------------------------------------------------------------
; Variables
; ---------------------------------------------------------------------------

; Only a normal assignment with an identifier target creates a variable
; definition. An augmented assignment is a write to an existing binding.

(assignment
  left: (identifier)) @definition.variable


; ---------------------------------------------------------------------------
; Dependencies
; ---------------------------------------------------------------------------

(import_statement) @dependency.import

(import_statement
  (dotted_name) @meta.module_path)

(import_statement
  (aliased_import
    name: (dotted_name) @meta.module_path))


(import_from_statement) @dependency.import

(import_from_statement
  module_name: (dotted_name) @meta.module_path)

(import_from_statement
  module_name: (relative_import) @meta.module_path)


; ---------------------------------------------------------------------------
; References
; ---------------------------------------------------------------------------

(call) @reference.call

(attribute) @reference.attribute


; Keep simple type references as explicit UAST nodes.
; Complex types are still retained as return_type/data_type metadata
; by the Python-specific handlers.

(type
  (identifier) @meta.name) @reference.type