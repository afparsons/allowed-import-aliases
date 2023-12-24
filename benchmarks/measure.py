"""Benchmark serial, multithreaded, and multiprocessed file evaluation."""

import ast
import pathlib
import pkgutil
import sys
import tempfile
from time import perf_counter_ns
from typing import Callable, Set, Mapping, Generator, Union, Tuple, Iterable, List, TypeVar

if sys.version_info < (3, 10):
    from typing_extensions import ParamSpec
else:
    from typing import ParamSpec

import allowed_import_aliases


P = ParamSpec("P")
R = TypeVar("R")

# Union[int, str, bytes, os.PathLike[str], os.PathLike[bytes]]


def parse_ast(filepath: str) -> ast.Module:
    """
    Parse a Python file.

    Args:
        filepath (str):
            The filepath of a file to parse.
    Returns:
        A parsed ast.Module.
    """
    with open(filepath, "rt") as file:
        return ast.parse(file.read(), filename=filepath)


def _get_top_level_functions(
    body: Iterable[ast.stmt],
) -> Generator[Union[ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef], None, None]:
    """
    Yield ast.stmt if they are one of {ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef}.

    Args:
        body:
            An iterable of ast.stmt

    Returns:
        A generator; each item is an importable definition.
    """
    return (
        item
        for item in body
        if isinstance(
            item,
            (
                ast.ClassDef,
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    )


def get_importables_from_module(filepath: str) -> Generator[Union[ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef], None, None]:
    """

    Args:
        filepath:
            The filepath to a Python module from which to extract importable definitions.

    Returns:
        A Python module's importable definitions.
    """
    tree = parse_ast(filepath)
    yield from _get_top_level_functions(tree.body)


def build_imports_from_builtins() -> List[Tuple[str, str, str]]:
    """
    Construct a list of tuples containing import statements from ``sys.builtin_module_names``.

    Returns:
        A list of tuples containing an import statement, an allowed import alias, and a disallowed import alias.
    """
    imports = []
    for module in sys.builtin_module_names:
        module = module.lstrip("_")
        filepath = pkgutil.get_loader(module)
        try:
            for stmt in get_importables_from_module(filepath.path):
                imports.append(
                    (
                        f"import {module}.{stmt.name}",  # import statement
                        f"as {module}_{stmt.name}",  # allowed alias
                        f"as {stmt.name}_{module}",  # disallowed alias
                    )
                )
        except AttributeError:
            pass
    return imports


_IMPORTS: List[Tuple[str, str, str]] = build_imports_from_builtins()


def build_temp_package(max_modules: int = 1000) -> Generator[str, None, None]:
    """
    Construct a Python package containing ``max_modules`` number of modules.
    """
    with tempfile.TemporaryDirectory() as temporary_directory:
        with pathlib.Path(temporary_directory, "__init__.py").open("w") as f:
            f.write("\n")

        for i in range(max_modules):
            with pathlib.Path(temporary_directory, f"module_{i}.py").open("w") as f:
                f.writelines((f"{import_statement} {bad_alias}\n" for import_statement, _, bad_alias in _IMPORTS))
        yield temporary_directory



class BuildTempPackage:
    """
    A context manager used to build a dummy Python package under a temporary directory.
    """
    def _write_modules(self, modules: int, imports: int):
        with pathlib.Path(self.td.name, "__init__.py").open("w") as f:
            f.write("\n")

        for i in range(modules):
            with pathlib.Path(self.td.name, f"module_{i}.py").open("w") as f:
                f.writelines((f"{import_statement} {bad_alias}\n" for import_statement, _, bad_alias in _IMPORTS[:imports]))

    def __init__(self, modules: int, imports: int):
        self.td = tempfile.TemporaryDirectory()
        self._write_modules(modules=modules, imports=imports)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.td.cleanup()


def benchmark(
    handler: Union[
        allowed_import_aliases.main._serial,
        allowed_import_aliases.main._multithread,
        allowed_import_aliases.main._multiprocess,
    ],
    allowed_aliases: Mapping[str, Set[str]],
    filenames: Iterable[Union[pathlib.Path, str]],
) -> Tuple[str, int]:
    """
    Time the execution of a file evaluator.

    Args:
        handler:
            A Callable wrapping the evaluate_files function.
        allowed_aliases:
            Key-value pair of fully-qualified name and one or more acceptable aliases.
        filenames:
            Python files to evaluate.
    Returns:

    """
    start = perf_counter_ns()
    for _ in handler(allowed_aliases, filenames):
        pass
    stop = perf_counter_ns()
    return (
        handler.__name__,
        stop - start,
    )


def run_benchmarks() -> Generator[Tuple[Tuple[str, int], int, int], None, None]:
    handlers = (
        allowed_import_aliases.main._serial,
        allowed_import_aliases.main._multithread,
        allowed_import_aliases.main._multiprocess,
    )
    for modules in (2**m for m in range(11)):  # type: int
        for imports in (2**m for m in range(9)):  # type: int
            with BuildTempPackage(modules=modules, imports=imports) as temp_package:
                filepaths = pathlib.Path(temp_package.td.name).glob(pattern="*.py")
                for handler in handlers:
                    result = benchmark(
                        handler,
                        allowed_aliases={},
                        filenames=filepaths,
                    )
                    yield result, modules, imports


def plot_sns(results: Iterable[Tuple[Tuple[str, int], int, int]]):
    import seaborn as sns
    import pandas as pd
    import matplotlib.pyplot as plt

    sns.set_theme(rc={"figure.figsize": (12, 6)})

    data = pd.DataFrame(
        data=((r[0][0][1:], r[0][1], r[1], r[2]) for r in results),
        columns=["parallelization", "nanoseconds", "num_modules", "num_imports"],
    )

    figure, axes = plt.subplots(ncols=2)

    sns.scatterplot(
        data=data,
        x="num_modules",
        y="nanoseconds",
        hue="parallelization",
        style="parallelization",
        ax=axes[0],
    )

    sns.scatterplot(
        data=data,
        x="num_imports",
        y="nanoseconds",
        hue="parallelization",
        style="parallelization",
        ax=axes[1],
    )

    for ax in axes:
        ax.set_xticks(sorted(data["num_imports"].unique()))
        ax.set_xscale("log", base=2)

    figure.savefig("./output/measure.svg")


def plot_plotly(results: Iterable[Tuple[Tuple[str, int], int, int]]):
    import plotly.express as px
    import pandas as pd

    data = pd.DataFrame(
        data=((r[0][0][1:], r[0][1], r[1], r[2]) for r in results),
        columns=["parallelization", "nanoseconds", "num_modules", "num_imports"],
    )

    figure = px.scatter_3d(
        data_frame=data,
        x="num_modules",
        y="num_imports",
        z="nanoseconds",
        color="parallelization",
        symbol="parallelization",
        hover_data=(
            "num_modules",
            "num_imports",
            "nanoseconds",
            "parallelization",
        ),
        opacity=0.5,
    )

    figure.update_layout(
        scene={
            "xaxis": {
                "type": "category"
            },
            "yaxis": {
                "type": "category"
            },
        }
    )

    figure.write_html("./output/measure.html")


if __name__ == "__main__":
    plot_plotly(run_benchmarks())
