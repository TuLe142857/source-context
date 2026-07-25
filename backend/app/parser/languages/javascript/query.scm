; JavaScript and JSX -> UAST query
;
; Query captures identify semantic boundaries.
; Field extraction is performed by JavaScript-specific handlers.

; ---------------------------------------------------------------------------
; Documentation
; ---------------------------------------------------------------------------

(
  (comment) @meta.doc
  (#match? @meta.doc "^/\\*\\*")
)


; ---------------------------------------------------------------------------
; Type definitions
; ---------------------------------------------------------------------------

(class_declaration) @definition.class


; ---------------------------------------------------------------------------
; Constructors and methods
; ---------------------------------------------------------------------------

(
  (method_definition
    name: (property_identifier) @_.constructor_name)
    @definition.constructor
  (#eq? @_.constructor_name "constructor")
)

(method_definition) @definition.method



; ---------------------------------------------------------------------------
; Functions
; ---------------------------------------------------------------------------

(function_declaration) @definition.function

(generator_function_declaration) @definition.function



; ---------------------------------------------------------------------------
; Parameters
; ---------------------------------------------------------------------------

(formal_parameters
  (identifier) @definition.parameter)

(formal_parameters
  (assignment_pattern) @definition.parameter)

(formal_parameters
  (rest_pattern) @definition.parameter)

(formal_parameters
  (object_pattern) @definition.parameter)

(formal_parameters
  (array_pattern) @definition.parameter)


; Arrow function without parentheses: value => value + 1

(arrow_function
  parameter: (identifier) @definition.parameter)


; ---------------------------------------------------------------------------
; Variables, constants and fields
; ---------------------------------------------------------------------------


(variable_declarator) @definition.variable

(field_definition) @definition.field


; ---------------------------------------------------------------------------
; Dependencies
; ---------------------------------------------------------------------------

(import_statement) @dependency.import


; export { value } from "./module.js"

(export_statement
  source: (string)) @dependency.import


; const package = require("package")

(
  (call_expression
    function: (identifier) @_.require_function
    arguments: (arguments
      (string) @_.require_source))
    @dependency.import
  (#eq? @_.require_function "require")
)


; ---------------------------------------------------------------------------
; References
; ---------------------------------------------------------------------------

(call_expression) @reference.call

(new_expression) @reference.call

(member_expression) @reference.attribute

(subscript_expression) @reference.attribute