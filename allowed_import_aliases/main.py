"""Main entrypoint."""

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import partial
import os
from typing import DefaultDict, Optional, Sequence, Set

from allowed_import_aliases.parse import evaluate_file, DisallowedImportAlias


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("filenames", nargs="*")
    parser.add_argument(
        "-t",
        type=int,
        action="store",
        required=False,
        nargs=1,
        default=None,
    )
    parser.add_argument(
        "-p",
        type=int,
        action="store",
        choices=(range(0, os.cpu_count()+1)),
        help="",
        required=False,
        nargs=1,
        default=None,
    )
    parser.add_argument(
        "-a",
        nargs="*",
        action="append",
        metavar=("qualname", "as_name(s)"),
        help="Key-value pair of fully-qualified name and one or more acceptable aliases",
    )
    args = parser.parse_args(argv)
    allowed_aliases: DefaultDict[str, Set[str]] = defaultdict(set)

    # TODO: do we need to validate these? Negative values?
    if args.t is not None and args.p is not None:
        raise ValueError("-t and -p are mutually exclusive.")

    try:
        for arguments in args.a:
            print(f"{arguments=}")
            qualname, *aliases = arguments[0].strip().split(" ")
            allowed_aliases[qualname].update(aliases)
    except TypeError as e:
        print(f"{e=}")
        raise Exception(f"{args}") from e

    if args.t is not None:
        print("A")
        with ThreadPoolExecutor(
            max_workers=args.t or None,
            thread_name_prefix="python-import-alias-",
            initializer=None,
        ) as thread_pool_executor:
            problems = thread_pool_executor.map(
                partial(evaluate_file, allowed_aliases),
                args.filenames,
            )
    elif args.p is not None:
        print("B")
        with ProcessPoolExecutor(
            max_workers=args.p or None,
            initializer=None,
        ) as process_pool_executor:
            problems = process_pool_executor.map(
                partial(evaluate_file, allowed_aliases),
                args.filenames,
            )
    else:
        print("C")
        problems = map(
            partial(evaluate_file, allowed_aliases),
            args.filenames,
        )
        print(f"{problems=}")

    try:
        problem = next(problems)
        print(f"1 {problem=}")
        for p in problem:  # type: DisallowedImportAlias
            print("Problem:", p)
    except StopIteration:
        return 0

    for problem in problems:
        print(f"2 {problem=}")
        for p in problem:  # type: DisallowedImportAlias
            print("Problem:", p)
    return 1


if __name__ == "__main__":
    main()
