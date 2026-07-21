; Python -> UAST query
;
; The converter groups captures by tree-sitter node id.  Definition captures
; therefore live on the definition/assignment node, while meta.name lives on
; its name/target child.  Keep patterns below mutually specific where two
; definition kinds could otherwise be emitted for the same node.

; ---------------------------------------------------------------------------
; Metadata
; ---------------------------------------------------------------------------

; A docstring is the first expression in a body.  The leading `.` is
; intentional: later string expressions are ordinary expression statements.
(module
  . (expression_statement (string) @meta.doc))
(function_definition
  body: (block . (expression_statement (string) @meta.doc)))
(class_definition
  body: (block . (expression_statement (string) @meta.doc)))

; Comments are retained as a query capture for clients which expose raw
; captures.  The current UAST handler does not turn comments into nodes.
(comment) @comment

; ---------------------------------------------------------------------------
; Definitions
; ---------------------------------------------------------------------------

; Classes.  `superclasses` is deliberately not captured as a definition: the
; current handler has no meta.base_type consumer.
(class_definition
  name: (identifier) @meta.name) @definition.class

; A constructor is more specific than a method.  The adapter gives the
; constructor capture higher priority when both patterns match the node.
(class_definition
  body: (block
    (function_definition
      name: (identifier) @_.constructor_name
      (#eq? @_.constructor_name "__init__")) @definition.constructor))
(class_definition
  body: (block
    (decorated_definition
      definition: (function_definition
        name: (identifier) @_.decorated_constructor_name
        (#eq? @_.decorated_constructor_name "__init__")) @definition.constructor)))

(class_definition
  body: (block (function_definition) @definition.method))
(class_definition
  body: (block (decorated_definition definition: (function_definition) @definition.method)))

; All function definitions, including nested functions.  Constructor/method
; matches above sort before this generic capture in the converter.
(function_definition
  name: (identifier) @meta.name) @definition.function
(function_definition
  name: (identifier) @meta.name
  return_type: (type) @meta.type)

; Parameters: capture the binding node, never identifiers occurring inside a
; default expression.  The name capture is a child of the parameter node.
(parameters (identifier) @definition.parameter)
(parameters (typed_parameter
  (identifier) @meta.name
  type: (type) @meta.type) @definition.parameter)
(parameters (default_parameter
  name: (identifier) @meta.name) @definition.parameter)
(parameters (typed_default_parameter
  name: (identifier) @meta.name
  type: (type) @meta.type) @definition.parameter)
(parameters (list_splat_pattern
  (identifier) @meta.name) @definition.parameter)
(parameters (dictionary_splat_pattern
  (identifier) @meta.name) @definition.parameter)

; Lambda parameters use the same binding rules but have a different parent.
(lambda) @definition.lambda
(lambda_parameters (identifier) @definition.parameter)
(lambda_parameters (typed_parameter
  (identifier) @meta.name
  type: (type) @meta.type) @definition.parameter)
(lambda_parameters (default_parameter
  name: (identifier) @meta.name) @definition.parameter)
(lambda_parameters (typed_default_parameter
  name: (identifier) @meta.name
  type: (type) @meta.type) @definition.parameter)
(lambda_parameters (list_splat_pattern
  (identifier) @meta.name) @definition.parameter)
(lambda_parameters (dictionary_splat_pattern
  (identifier) @meta.name) @definition.parameter)

; Bindings are captured wherever assignment nodes occur (module, class and
; nested scopes).  Only identifier targets are bindings; expressions such as
; calls, literals and attribute reads are not variables.
(assignment left: (identifier) @meta.name) @definition.variable
(augmented_assignment left: (identifier) @meta.name) @definition.variable

; ---------------------------------------------------------------------------
; Dependencies
; ---------------------------------------------------------------------------

; One import UAST node is created per import statement.  For a plain import,
; only the imported dotted name is a module path; aliases are handled by the
; import node contract without treating their identifier as another module.
(import_statement) @dependency.import
(import_statement (dotted_name) @meta.module_path)
(import_statement
  (aliased_import name: (dotted_name) @meta.module_path))

; `module_name` excludes names imported after `from`, including wildcard and
; aliased imports.  A missing module in a relative import is valid Python CST
; and simply has no module_path metadata.
(import_from_statement) @dependency.import
(import_from_statement module_name: (dotted_name) @meta.module_path)
(import_from_statement module_name: (relative_import) @meta.module_path)

; ---------------------------------------------------------------------------
; References
; ---------------------------------------------------------------------------

; Calls: name is the callable's final identifier, while subject is the
; receiver for attribute calls.  Nested calls are naturally represented by
; separate call nodes on their own `call` CST nodes.
(call
  function: (identifier) @meta.name) @reference.call
(call
  function: (attribute
    attribute: (identifier) @meta.name)) @reference.call

; Attribute access has its own UAST node.  Do not capture every identifier in
; an expression as a reference; only the attribute field is the accessed name.
(attribute
  attribute: (identifier) @meta.name) @reference.attribute

; `type` is the grammar's annotation wrapper.  This covers annotations on
; parameters, returns and variables without treating ordinary body names as
; type references.  The handler also uses this capture to populate parameter
; data_type.
(type
  (identifier) @meta.name) @reference.type
