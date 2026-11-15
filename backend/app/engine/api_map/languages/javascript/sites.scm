; Sites the JavaScript / TypeScript framework detectors look at (languages/javascript/cst.py).
; Compiled once per grammar: javascript, typescript and tsx share these node types.
;
;   @site      the call: inside a decorator, or a plain call
;   @decorator the decorator around the call (decorator sites only)
;   @receiver  object the method is called on (absent for bare calls)
;   @method    called name
;   @args      arguments

; decorator on a class member: @Get(":id") findOne() {...}
(class_body
  (decorator
    (call_expression
      function: (identifier) @method
      arguments: (arguments) @args) @site) @decorator)

; <receiver>.<method>(<args>)
(call_expression
  function: (member_expression
    object: (_) @receiver
    property: (property_identifier) @method)
  arguments: (arguments) @args) @site

; <method>(<args>): fetch(url), axios(config), Router()
(call_expression
  function: (identifier) @method
  arguments: (arguments) @args) @site
