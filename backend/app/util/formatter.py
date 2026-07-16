from typing import Any, Protocol


class Formatter[T](Protocol):
    """
    Use for convert object to string
    """

    def format(self, data: T) -> str:
        pass


class TreeFormatter(Formatter[Any]):
    def __init__(
        self,
        branch: str = "├──",
        last_branch: str = "└──",
        space: str = "   ",
        vertical: str = "│  ",
    ):
        self._space = space
        self._vertical = vertical
        self._branch = branch
        self._last_branch = last_branch

    @staticmethod
    def _convert(data: Any) -> list[tuple[str, Any]]:
        """
        Convert object to list of (node_name, children_object)
        Args:
            data: object to convert

        Returns:

        """
        if isinstance(data, dict):
            return list(data.items())
        elif isinstance(data, list) or isinstance(data, tuple):
            res = []
            for item in data:
                if isinstance(item, dict):
                    if len(item) == 0:
                        pass
                    elif len(item) == 1:
                        k, v = list(item.items())[0]
                        res.append((k, v))
                    else:
                        res.append(("", item))
                elif isinstance(item, list):
                    res.append(("", item))
                else:
                    res.append((str(item), None))
            return res
        else:
            return [
                (str(data), None),
            ]

    def _build_tree(self, lines: list[str], data: Any, indent: str = "") -> None:
        nodes = self._convert(data)
        for idx, (node_name, children) in enumerate(nodes):
            is_last_node = idx == len(nodes) - 1
            branch = self._last_branch if is_last_node else self._branch
            lines.append(f"{indent}{branch}{node_name}")

            if children is not None:
                children_indent = f"{indent}{self._space if is_last_node else self._vertical}"
                self._build_tree(lines, children, children_indent)

    def format(self, data: Any) -> str:
        lines: list[str] = []
        self._build_tree(lines, data)
        return "\n".join(lines)


if __name__ == "__main__":
    formatter = TreeFormatter()
    value = [  # type: ignore
        {"backend": {}},
        {"mcp": {}},
        {"frontend": {}},
    ]
    print(formatter.format(value))
