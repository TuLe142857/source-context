; JavaScript declarations

(function_declaration
  name: (identifier) @meta.name) @definition.function

(class_declaration
  name: (identifier) @meta.name) @definition.class

(method_definition
  name: (property_identifier) @meta.name) @definition.method

(variable_declarator
  name: (identifier) @meta.name) @definition.variable


; JavaScript imports

(import_statement
  source: (string) @meta.module_path) @dependency.import


; Direct function calls: execute()

(call_expression
  function: (identifier) @meta.name) @reference.call


; Member calls: service.execute()

(call_expression
  function: (member_expression
    object: (identifier) @meta.subject
    property: (property_identifier) @meta.name)) @reference.call