; ==============================================================
;                   COMMENT & DOCs
; ==============================================================
;   DOC
(module . (expression_statement (string)) @doc)
(function_definition
    body: (block . (expression_statement (string)) @doc )
)
(class_definition
    body: (block . (expression_statement (string)) @doc )
)

;   COMMENT
(comment) @comment
(module (expression_statement (string)) @comment)
(function_definition
    body: (block (expression_statement (string)) @comment )
)
(class_definition
    body: (block (expression_statement (string)) @comment )
)
; ==============================================================

(module (expression_statement (assignment left: (identifier) @name) @definition.constant))

(class_definition name: (identifier) @name ) @definition.class

(function_definition name: (identifier) @name) @definition.function

(call function: [
      (identifier) @name
      (attribute
        attribute: (identifier) @name)
  ]) @reference.call
