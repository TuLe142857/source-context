from functools import lru_cache

from app.parser.language_registry import LanguageRegistry

from . import c as c
from . import c_sharp as c_sharp
from . import cpp as cpp
from . import go as go
from . import html as html
from . import java as java
from . import javascript as javascript
from . import php as php
from . import python as python
from . import ruby as ruby
from . import rust as rust
from . import typescript as typescript


@lru_cache
def get_language_registry() -> LanguageRegistry:
    return LanguageRegistry(
        [
            python.get_language_config(),
            java.get_language_config(),
        ]
    )
