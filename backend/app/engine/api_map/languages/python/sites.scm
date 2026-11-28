; Sites the Python framework detectors look at (app/engine/api_map/languages/python/cst.py).
;
;   @site      the call: inside a decorator, or a plain call
;   @receiver  object the method is called on (absent for bare calls)
;   @method    called name
;   @args      argument_list
;   @handler   decorated function (decorator sites only)

; pattern 0: @<receiver>.<method>(<args>) on a function or a method
(decorated_definition
  (decorator
    (call
      function: (attribute object: (_) @receiver attribute: (identifier) @method)
      arguments: (argument_list) @args) @site)
  definition: (function_definition) @handler)

; pattern 1: <receiver>.<method>(<args>)
(call
  function: (attribute object: (_) @receiver attribute: (identifier) @method)
  arguments: (argument_list) @args) @site

; pattern 2: <method>(<args>), bare calls such as urlopen(...) or a from-imported get(...)
(call
  function: (identifier) @method
  arguments: (argument_list) @args) @site
