((block_comment)  @meta.doc . (class_declaration))
((block_comment) @meta.doc . (record_declaration))
((block_comment) @meta.doc . (method_declaration))
(modifiers _ * @meta.modifier )

(class_declaration

    "class"
   	name :(identifier) @meta.name
) @definition.class


(class_declaration body:(class_body
	(field_declaration
    	declarator: (variable_declarator
        	name: (_) @meta.name
        )
    )@definition.variable
)
)

(record_declaration
	name: (identifier) @meta.name
	parameters:(formal_parameters
    	(formal_parameter
        	type: (_) @meta.type
            name: (_) @meta.name
        )* @definition.field
    )
)@definition.struct

(method_declaration
	name: (identifier) @meta.name
) @definition.method
(block_comment) @comment

