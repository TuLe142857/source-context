import pytest
from tree_sitter import Language, Parser

from app.parser.languages import get_language_registry
from app.parser import LanguageRegistry
from app.parser.uast import UASTConverter


@pytest.fixture(scope="class")
def registry() -> LanguageRegistry:
    return get_language_registry()


class TestLoadConfig:
    def test_load_registry(self, registry: LanguageRegistry) -> None:
        assert isinstance(registry, LanguageRegistry)

    @pytest.mark.parametrize(
        ["language_name", "file_names"],
        [("python", ["test.py"]), ("java", ["test.java"])],
    )
    def test_get_language_object(
        self, registry: LanguageRegistry, language_name: str, file_names: list[str]
    ) -> None:
        language = registry.get_language(language_name)
        assert isinstance(language, Language)

        for file_name in file_names:
            language_by_file = registry.get_language_for_file(file_name)
            assert isinstance(language_by_file, Language)

    @pytest.mark.parametrize(
        ["language_name", "file_names"],
        [("python", ["test.py"]), ("java", ["test.java"])],
    )
    def test_get_parser_object(
        self, registry: LanguageRegistry, language_name: str, file_names: list[str]
    ) -> None:
        parser = registry.get_parser(language_name)
        assert isinstance(parser, Parser)
        for file_name in file_names:
            parser_by_file = registry.get_parser_for_file(file_name)
            assert isinstance(parser_by_file, Parser)

    @pytest.mark.parametrize(
        ["language_name", "file_names"],
        [("python", ["test.py"]), ("java", ["test.java"])],
    )
    def test_get_converter_object(
        self, registry: LanguageRegistry, language_name: str, file_names: list[str]
    ) -> None:
        converter = registry.get_converter(language_name)
        assert isinstance(converter, UASTConverter)
