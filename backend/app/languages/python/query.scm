; ==============================================================
;                   COMMENT & DOCs
; ==============================================================
;   DOC
(module . (expression_statement (string)) @meta.doc)
(function_definition
    body: (block . (expression_statement (string)) @meta.doc )
)
(class_definition
    body: (block . (expression_statement (string)) @meta.doc )
)


;   COMMENT
(comment) @meta.comment
(module (expression_statement (string)) @meta.comment)
(function_definition
    body: (block (expression_statement (string)) @meta.comment )
)
(class_definition
    body: (block (expression_statement (string)) @meta.comment )
)
; ==============================================================

(module (expression_statement (assignment left: (identifier) @meta.name) @definition.constant))

(class_definition
    name: (identifier) @meta.name
) @definition.class

(class_definition
    body: (block
        (function_definition
            name: (identifier) @_.constructor_name
            (#eq? @_.constructor_name "__init__")
        ) @definition.constructor
    )
)

(class_definition body: (block (function_definition) @definition.method ))

(function_definition name: (identifier) @meta.name) @definition.function

(call function: [
      (identifier) @meta.name
      (attribute
        attribute: (identifier) @meta.name)
  ]) @reference.call
