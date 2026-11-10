; TypeScript and TSX -> UAST query
;
; The same query is compiled independently against:
; - the TypeScript grammar
; - the TSX grammar
;
; Semantic field extraction is handled by TypeScript-specific handlers.

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

(abstract_class_declaration) @definition.class

(interface_declaration) @definition.interface

(type_alias_declaration) @definition.type_alias

(enum_declaration) @definition.enum


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

(required_parameter) @definition.parameter

(optional_parameter) @definition.parameter


; Untyped single-parameter arrow function:
; value => value + 1

(arrow_function
  parameter: (identifier) @definition.parameter)


; ---------------------------------------------------------------------------
; Variables, constants and class fields
; ---------------------------------------------------------------------------

; Handlers classify variable declarators as:
; - function
; - constant
; - variable

(variable_declarator) @definition.variable


; TypeScript uses public_field_definition for class fields.
; Handlers classify function-valued fields as methods.

(public_field_definition) @definition.field


; ---------------------------------------------------------------------------
; Dependencies
; ---------------------------------------------------------------------------

(import_statement) @dependency.import


; export { value } from "./module"

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