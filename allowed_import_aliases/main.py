"""Main entrypoint."""

import argparse
import os
import pathlib
import sys as s
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from functools import partial
from typing import (
    DefaultDict,
    Generator,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from allowed_import_aliases.parse import DisallowedImportAlias, evaluate_file


def _serial(
    allowed_aliases: Mapping[str, Set[str]],
    filenames: Iterable[Union[pathlib.Path, str]],
) -> Iterator[Generator[DisallowedImportAlias, None, None]]:
    """
    Evaluate files serially.

    Args:
        allowed_aliases:
            Key-value pair of fully-qualified name and one or more acceptable aliases.
        filenames:
            Python files to evaluate.

    Returns:
        An Iterator of Generators, each producing a ``DisallowedImportAlias`` exception.
    """
    return (
        evaluate_file(allowed_aliases=allowed_aliases, filepath=filename)
        for filename in filenames
    )


def _multithread(
    allowed_aliases: Mapping[str, Set[str]],
    filenames: Iterable[Union[pathlib.Path, str]],
    max_workers: Optional[int] = None,
) -> Iterator[Generator[DisallowedImportAlias, None, None]]:
    """
    Evaluate files using one or more threads.

    Args:
        allowed_aliases:
            Key-value pair of fully-qualified name and one or more acceptable aliases.
        filenames:
            Python files to evaluate.
        max_workers:
            The number of workers to use.

    Returns:
        An Iterator of Generators, each producing a ``DisallowedImportAlias`` exception.
    """
    with ThreadPoolExecutor(
        max_workers=max_workers,
        thread_name_prefix="python-import-alias-",
        initializer=None,
    ) as thread_pool_executor:
        return thread_pool_executor.map(
            partial(evaluate_file, allowed_aliases),
            filenames,
        )


def _multiprocess(
    allowed_aliases: Mapping[str, Set[str]],
    filenames: Iterable[Union[pathlib.Path, str]],
    max_workers: Optional[int] = None,
) -> Iterator[Generator[DisallowedImportAlias, None, None]]:
    """
    Evaluate files using one or more processes.

    Args:
        allowed_aliases:
            Key-value pair of fully-qualified name and one or more acceptable aliases.
        filenames:
            Python files to evaluate.
        max_workers:
            The number of workers to use.

    Returns:
        An Iterator of Generators, each producing a ``DisallowedImportAlias`` exception.
    """
    with ProcessPoolExecutor(
        max_workers=max_workers,
        initializer=None,
    ) as process_pool_executor:
        return process_pool_executor.map(
            partial(evaluate_file, allowed_aliases),
            filenames,
        )


def _validate_args(
    t: Optional[List[int]],
    p: Optional[List[int]],
) -> Tuple[Optional[int], Optional[int]]:
    """
    Args:
        t: The argument passed to ``-t``.
        p: The argument passed to ``-p``.

    Returns:
        A tuple of two integers.
    """
    if t is not None and p is not None:
        raise ValueError("-t and -p are mutually exclusive.")

    if t is None:
        _t = None
    else:
        if len(t) > 1:
            raise ValueError("-t can only accept one integer argument.")
        _t = t[0]
        if not isinstance(_t, int):
            raise ValueError("-t can only accept one integer argument.")
        if _t < 0:
            raise ValueError("-t cannot take a value less than 0.")

    if p is None:
        _p = None
    else:
        if len(p) > 1:
            raise ValueError("-p can only accept one integer argument.")
        _p = p[0]
        if not isinstance(_p, int):
            raise ValueError("-p can only accept one integer argument.")
        if _p < 0:
            raise ValueError("-p cannot take a value less than 0.")
    return _t, _p


def main(argv: Optional[Sequence[str]] = None) -> int:
    print(f"{s.argv=}")
    parser = argparse.ArgumentParser()
    parser.add_argument("filenames", nargs="*")
    parser.add_argument(
        "-a",
        nargs="*",
        action="append",
        metavar=("qualname", "as_name(s)"),
        help="Key-value pair of fully-qualified name and one or more acceptable aliases",
    )
    parser.add_argument(
        "-t",
        type=int,
        action="store",
        required=False,
        nargs=1,
        default=None,
        help="""
            The number of workers to use.
            If equal to 0, the default number of workers is used.
        """,
    )
    parser.add_argument(
        "-p",
        type=int,
        action="store",
        choices=(range(0, (os.cpu_count() or 0) + 1)),
        help="""
            The number of workers to use.
            If equal to 0, it will default to the number of processors on the machine.
        """,
        required=False,
        nargs=1,
        default=None,
    )
    args = parser.parse_args(argv)
    allowed_aliases: DefaultDict[str, Set[str]] = defaultdict(set)
    t, p = _validate_args(t=args.t, p=args.p)

    try:
        for arguments in args.a:
            qualname, *aliases = arguments[0].strip().split(" ")
            allowed_aliases[qualname].update(aliases)
    except TypeError as e:
        raise Exception(f"{args}") from e

    if t is not None:
        problems = _multithread(
            allowed_aliases=allowed_aliases,
            filenames=args.filenames,
            max_workers=t or None,
        )
    elif p is not None:
        problems = _multiprocess(
            allowed_aliases=allowed_aliases,
            filenames=args.filenames,
            max_workers=p or None,
        )
    else:
        problems = _serial(allowed_aliases=allowed_aliases, filenames=args.filenames)

    problems = [prob for prob in problems]
    print(f"{problems=}")

    exit_code: int = 0
    for problem in problems:  # type: Generator
        try:
            p = next(problem)
            print(p)
            exit_code = 1
        except StopIteration:
            break
        for q in problem:  # type: DisallowedImportAlias
            print(q)
    return exit_code


if __name__ == "__main__":
    main()
