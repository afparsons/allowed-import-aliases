"""Parsing logic."""

# TODO: https://stackoverflow.com/questions/8654666/decorator-for-overloading-in-python

import ast
import os
from collections import defaultdict
from pathlib import Path
from typing import (
    Any,
    DefaultDict,
    Dict,
    Generator,
    Mapping,
    NamedTuple,
    Optional,
    Set,
    Union
)

from typing_extensions import Buffer


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

    def __eq__(self, other: object) -> bool:
        return other == self.alias

    def __hash__(self) -> int:
        return hash(self.alias)


def get_ast_from_filepath(filepath: Union[str, Path]) -> ast.AST:
    """
    Args:
        filepath (Union[str, Path]):
            The filepath to a Python module.

    Returns:
        An abstract syntax tree of Python code.
    """
    with open(filepath, "rt") as file:
        return ast.parse(source=file.read(), filename=filepath)


def get_ast_from_source(
    source: Union[str, bytes], filename: Union[str, Buffer, os.PathLike]
) -> ast.AST:
    """
    Args:
        source (Union[str, bytes]):
            Bytes of Python code.

        filename (Union[str, bytes, None]):
            The name of the Python code to parse.

    Returns:
        An abstract syntax tree of Python code.
    """
    return ast.parse(source=source, filename=filename)


def get_imports_from_ast(root: ast.AST) -> DefaultDict[str, Set[AsName]]:
    """
    Args:
        root (ast.AST):
            The abstract syntax tree of Python code.

    Returns:
        A DefaultDict with the fully-qualified string names of Python imports a keys
        and a set of named tuples containing information parsed from the import using the abstract syntax tree.
    """
    imports = defaultdict(set)
    for node in ast.walk(root):
        if isinstance(node, ast.Import):
            module = ""
        elif isinstance(node, ast.ImportFrom):
            module = f"{node.module}."
        else:
            continue
        for alias in node.names:  # type: ignore[attr-defined]
            if alias.asname:
                qualname = f"{module}{alias.name}"
                imports[qualname].add(
                    AsName(qualname=qualname, alias=alias.asname, lineno=node.lineno)
                )
    return imports


def format_error_message(
    filepath: str,
    qualname: str,
    allowed_aliases: Optional[Set[str]],
    actual_alias: AsName,
) -> str:
    if allowed_aliases:
        _allowed: str = (
            f"The only allowed alias{'es are' if len(allowed_aliases) > 1 else ' is'}"
            f" \033[1;32m{allowed_aliases}\033[0m"
        )
    else:
        _allowed = "There are no allowed aliases."

    return (
        f"{filepath}:{actual_alias.lineno}:"
        f" \033[1;34m{qualname}\033[0m"
        f" is aliased as"
        f" \033[1;31m{actual_alias.alias}\033[0m."
        f" {_allowed}"
    )


class DisallowedImportAlias(Exception):
    pass


def evaluate_file(
    allowed_aliases: Mapping[str, Set[str]],
    filepath: Union[Path, str],
    *,
    lazy: bool = False,
) -> Generator[DisallowedImportAlias, None, None]:
    """
    Args:
        allowed_aliases (Mapping[str, Set[str]]):
            A mapping of imports to a set of allowed aliases.

        filepath (Union[Path, str]):
            A Python module to check

        lazy (bool):
            Whether to break early. Defaults to false.

    Return:
        A Generator of DisallowedImportAliases, each containing an error message string.
    """
    root = get_ast_from_filepath(filepath=filepath)
    yield from evaluate(allowed_aliases, root, filename=str(filepath), lazy=lazy)


def evaluate_source(
    allowed_aliases: Dict[str, Set[str]],
    source: Union[str, bytes],
    *,
    filename: str = "<unknown>",
    lazy: bool = False,
) -> Generator[DisallowedImportAlias, None, None]:
    """
    Args:
        allowed_aliases (Dict[str, Set[str]]):
            A mapping of imports to a set of allowed aliases.

        source (Union[str, bytes]):
            A Python module to check.

        filename (str):
            Defaults to '<unknown>'.

        lazy (bool):
            Whether to break early. Defaults to false.

    Return:
        A Generator of DisallowedImportAliases, each containing an error message string.
    """
    root = get_ast_from_source(source=source, filename=filename)
    yield from evaluate(allowed_aliases, root, filename=filename, lazy=lazy)


def evaluate(
    allowed_aliases: Mapping[str, Set[str]],
    root: ast.AST,
    *,
    filename: str = "<unknown>",
    lazy: bool = False,
) -> Generator[DisallowedImportAlias, None, None]:
    """
    Args:
        allowed_aliases (Dict[str, Set[str]]):
            A mapping of imports to a set of allowed aliases.

        root (ast.AST):
            A Python module to check.

        filename (str):
            Defaults to '<unknown>'.

        lazy (bool):
            Whether to break early. Defaults to ``False``.

    Return:
        A Generator of DisallowedImportAliases, each containing an error message string.
    """
    imports = get_imports_from_ast(root=root)
    for qualname, as_names in imports.items():
        if as_names:
            allowed = allowed_aliases.get(qualname)
            if not allowed:
                for actual in as_names:
                    yield DisallowedImportAlias(
                        format_error_message(
                            filepath=filename,
                            qualname=qualname,
                            allowed_aliases=set(),
                            actual_alias=actual,
                        )
                    )
                    if lazy:
                        return
            else:
                if allowed != as_names:
                    for actual in as_names:
                        for a in allowed:
                            if a != actual:
                                yield DisallowedImportAlias(
                                    format_error_message(
                                        filepath=filename,
                                        qualname=qualname,
                                        allowed_aliases=allowed,
                                        actual_alias=actual,
                                    )
                                )
                                if lazy:
                                    return
