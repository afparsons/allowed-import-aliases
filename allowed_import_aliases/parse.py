"""Parsing logic."""

import ast
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, Generator, NamedTuple, Set, Union


class AsName(NamedTuple):
    """
    A container for import data parsed from a Python module's abstract syntax tree.
    """

    qualname: str
    """The fully-qualified name import name."""

    alias: str
    """An import's alias."""

    lineno: int
    """The import statement's line number."""

    def __eq__(self, other: str) -> bool:
        return other == self.alias

    def __hash__(self) -> int:
        return hash(self.alias)


def parse_ast_from_filepath(filepath):
    with open(filepath, "rt") as file:
        return ast.parse(source=file.read(), filename=filepath)


def parse_ast_from_stream(stream: bytes, filename: str):
    return ast.parse(source=stream, filename=filename)


def get_imports(filepath: Union[str, Path]) -> DefaultDict[str, Set[AsName]]:
    """
    Args:
        filepath (Union[str, Path]):

    Returns:
        A DefaultDict with the fully-qualified string names of Python imports a keys
        and a set of named tuples containing information parsed from the import using the abstract syntax tree.
    """
    with open(filepath, "r") as f:
        root = ast.parse(source=f.read(), filename=filepath)
    imports = defaultdict(set)
    for node in ast.walk(root):
        if isinstance(node, ast.Import):
            module = ""
        elif isinstance(node, ast.ImportFrom):
            module = f"{node.module}."
        else:
            continue
        for alias in node.names:
            if alias.asname:
                qualname = f"{module}{alias.name}"
                imports[qualname].add(AsName(qualname=qualname, alias=alias.asname, lineno=node.lineno))
    return imports


def format_error_message(
    filepath: str,
    qualname: str,
    allowed_aliases: Set[str],
    actual_alias: AsName,
) -> str:
    return (
        f"{filepath}:{actual_alias.lineno}:"
        f" \033[1m{qualname}\033[0m"
        f" is aliased as"
        f" \033[1m{actual_alias.alias}\033[0m."
        f" The only allowed alias{'es are' if len(allowed_aliases) > 1 else ' is'}"
        f" \033[1m{allowed_aliases}\033[0m"
    )


class DisallowedImportAlias(Exception):
    pass



def evaluate_file(
    allowed_aliases: Dict[str, Set[str]],
    filepath: Union[Path, str],
    *,
    lazy: bool = False,
) -> Generator[DisallowedImportAlias, None, None]:
    """
    Args:
        allowed_aliases (Dict[str, Set[str]]):
            A mapping of imports to a set of allowed aliases.

        filepath (Union[Path, str]):
            A Python module to check

        lazy (bool):
            Whether to break early. Defaults to false.

    Return:
        A Generator of DisallowedImportAliases, each containing an error message string.
    """
    imports = get_imports(filepath=filepath)
    for qualname, as_names in imports.items():
        if qualname in allowed_aliases:
            if allowed_aliases[qualname] != as_names:
                for actual in as_names:
                    for allowed in allowed_aliases[qualname]:
                        if allowed != actual:
                            yield DisallowedImportAlias(
                                format_error_message(
                                    filepath=filepath,
                                    qualname=qualname,
                                    allowed_aliases=allowed_aliases[qualname],
                                    actual_alias=actual,
                                )
                            )
                            if lazy:
                                break
