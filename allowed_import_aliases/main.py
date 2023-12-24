"""Main entrypoint."""

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import partial
import os
from typing import Iterator, DefaultDict, Generator, Optional, Sequence, Set, Mapping, Iterable, Union
import pathlib

from allowed_import_aliases.parse import evaluate_file, DisallowedImportAlias


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
            partial(evaluate_file, allowed_aliases), filenames,
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
            partial(evaluate_file, allowed_aliases), filenames,
        )


def _validate_args(t: Optional[int], p: Optional[int]) -> None:
    """
    Args:
        t: The argument passed to ``-t``.
        p: The argument passed to ``-p``.

    Returns:
        None.
    """
    if t is not None and p is not None:
        raise ValueError("-t and -p are mutually exclusive.")
    if t is not None and t < 0:
        raise ValueError("-t cannot take a value less than 0.")
    if p is not None and p < 0:
        raise ValueError("-p cannot take a value less than 0.")


def main(argv: Optional[Sequence[str]] = None) -> int:
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
        choices=(range(0, os.cpu_count()+1)),
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
    _validate_args(t=args.t, p=args.p)

    try:
        for arguments in args.a:
            qualname, *aliases = arguments[0].strip().split(" ")
            allowed_aliases[qualname].update(aliases)
    except TypeError as e:
        raise Exception(f"{args}") from e

    if args.t is not None:
        problems = _multithread(
            max_workers=args.t or None,
            allowed_aliases=allowed_aliases,
            filenames=args.filenames,
        )
    elif args.p is not None:
        problems = _multiprocess(
            max_workers=args.p or None,
            allowed_aliases=allowed_aliases,
            filenames=args.filenames,
        )
    else:
        problems = _serial(allowed_aliases=allowed_aliases, filenames=args.filenames)

    exit_code: int = 0
    for problem in problems:  # type: Generator
        try:
            p = next(problem)
            print(p)
            exit_code = 1
        except StopIteration:
            break
        for p in problem:  # type: DisallowedImportAlias
            print(p)
    return exit_code


if __name__ == "__main__":
    main()
