import ast

import allowed_import_aliases


def test_get_ast_from_filepath(tmp_path):
    filepath = tmp_path / "test_file.py"
    with open(filepath, "w") as f:
        f.write("def add_numbers(a, b):\n\treturn a + b")
    result_ast = allowed_import_aliases.parse.get_ast_from_filepath(filepath=filepath)
    assert isinstance(result_ast, ast.AST)


def test_get_ast_from_source_string():
    result_ast = allowed_import_aliases.parse.get_ast_from_source(
        source="def add_numbers(a, b):\n\treturn a + b",
        filename="test.py",
    )
    assert isinstance(result_ast, ast.AST)


def test_get_ast_from_source_bytes():
    result_ast = allowed_import_aliases.parse.get_ast_from_source(
        source="def add_numbers(a, b):\n\treturn a + b".encode("utf-8"),
        filename="test.py",
    )
    assert isinstance(result_ast, ast.AST)


def test_get_imports_from_ast():
    result_ast = allowed_import_aliases.parse.get_ast_from_source(
        source="import datetime.datetime as dt\n\ndef now():\n\treturn dt.now()",
        filename="test.py",
    )
    imports = allowed_import_aliases.parse.get_imports_from_ast(result_ast)
    assert imports == {"datetime.datetime": {"dt"}}


def test_get_imports_from_ast_from_import():
    result_ast = allowed_import_aliases.parse.get_ast_from_source(
        source="from datetime import datetime as dt\n\ndef now():\n\treturn dt.now()",
        filename="test.py",
    )
    imports = allowed_import_aliases.parse.get_imports_from_ast(result_ast)
    assert imports == {"datetime.datetime": {"dt"}}


def test_get_imports_from_ast_no_import():
    result_ast = allowed_import_aliases.parse.get_ast_from_source(
        source="print('Hello, world!')\n",
        filename="test.py",
    )
    imports = allowed_import_aliases.parse.get_imports_from_ast(result_ast)
    assert imports == {}


def test_get_imports_from_ast_empty():
    result_ast = allowed_import_aliases.parse.get_ast_from_source(
        source="",
        filename="test.py",
    )
    imports = allowed_import_aliases.parse.get_imports_from_ast(result_ast)
    assert imports == {}


def test_asname_eq():
    as_name = allowed_import_aliases.parse.AsName(
        qualname="datetime.datetime",
        alias="dt",
        lineno=1,
    )
    assert "dt" == as_name


def test_asname_hash():
    as_name = allowed_import_aliases.parse.AsName(
        qualname="datetime.datetime",
        alias="dt",
        lineno=1,
    )
    assert hash("dt") == as_name.__hash__()


def test_evaluate_lazy():
    root = allowed_import_aliases.parse.get_ast_from_source(
        source="import datetime.datetime as dt\nimport math as m\nimport pandas as pd\n",
        filename="<str>"
    )
    evaluations = tuple(
        allowed_import_aliases.parse.evaluate(
            allowed_aliases={"datetime.datetime": {"dt"}},
            root=root,
            filename="<str>",
            lazy=True,
        )
    )
    assert len(evaluations) == 1


def test_evaluate():
    root = allowed_import_aliases.parse.get_ast_from_source(
        source="import datetime.datetime as dt\nimport math as m\nimport pandas as pd\n",
        filename="<str>"
    )
    evaluations = tuple(
        allowed_import_aliases.parse.evaluate(
            allowed_aliases={"datetime.datetime": {"dt"}},
            root=root,
            filename="<str>",
            lazy=False,
        )
    )
    assert len(evaluations) == 2


def test_evaluate_2():
    root = allowed_import_aliases.parse.get_ast_from_source(
        source="import pandas as pd\n",
        filename="<str>"
    )
    evaluations = tuple(
        allowed_import_aliases.parse.evaluate(
            allowed_aliases={"pandas": {"pd"}},
            root=root,
            filename="<str>",
            lazy=False,
        )
    )
    assert len(evaluations) == 0


def test_evaluate_2_lazy():
    root = allowed_import_aliases.parse.get_ast_from_source(
        source="import pandas as pd\n",
        filename="<str>"
    )
    evaluations = tuple(
        allowed_import_aliases.parse.evaluate(
            allowed_aliases={"pandas": {"pd"}},
            root=root,
            filename="<str>",
            lazy=True,
        )
    )
    assert len(evaluations) == 0



def test_evaluate_no_allowances_with_asname():
    root = allowed_import_aliases.parse.get_ast_from_source(
        source="import pandas as pd\n",
        filename="<str>"
    )
    evaluations = tuple(
        allowed_import_aliases.parse.evaluate(
            allowed_aliases={},
            root=root,
            filename="<str>",
            lazy=False,
        )
    )
    assert len(evaluations) == 1


def test_evaluate_no_allowances_no_asname():
    root = allowed_import_aliases.parse.get_ast_from_source(
        source="import pandas\n",
        filename="<str>"
    )
    evaluations = tuple(
        allowed_import_aliases.parse.evaluate(
            allowed_aliases={},
            root=root,
            filename="<str>",
            lazy=False,
        )
    )
    assert len(evaluations) == 0


def test_evaluate_with_allowance_no_asname():
    root = allowed_import_aliases.parse.get_ast_from_source(
        source="import pandas\n",
        filename="<str>"
    )
    evaluations = tuple(
        allowed_import_aliases.parse.evaluate(
            allowed_aliases={"pandas": {"pd"}},
            root=root,
            filename="<str>",
            lazy=False,
        )
    )
    assert len(evaluations) == 0


def test_evaluate_with_allowance_with_asname():
    root = allowed_import_aliases.parse.get_ast_from_source(
        source="import pandas as pa\n",
        filename="<str>"
    )
    evaluations = tuple(
        allowed_import_aliases.parse.evaluate(
            allowed_aliases={"pandas": {"pd"}},
            root=root,
            filename="<str>",
            lazy=False,
        )
    )
    assert len(evaluations) == 1


def test_evaluate_with_allowance_with_asname_lazy():
    root = allowed_import_aliases.parse.get_ast_from_source(
        source="import pandas as pa\n",
        filename="<str>"
    )
    evaluations = tuple(
        allowed_import_aliases.parse.evaluate(
            allowed_aliases={"pandas": {"pd"}},
            root=root,
            filename="<str>",
            lazy=True,
        )
    )
    assert len(evaluations) == 1


def test_evaluate_file(tmp_path):
    p = tmp_path / "test.py"
    with p.open("w") as f:
        f.write("import datetime.datetime as dt\nimport math as m\nimport pandas as pd\n")
    evaluations = tuple(
        allowed_import_aliases.parse.evaluate_file(
            allowed_aliases={"datetime.datetime": {"dt"}},
            filepath=p,
            lazy=False,
        )
    )
    assert len(evaluations) == 2


def test_evaluate_source():
    evaluations = tuple(
        allowed_import_aliases.parse.evaluate_source(
            allowed_aliases={"datetime.datetime": {"dt"}},
            source="import datetime.datetime as dt\nimport math as m\nimport pandas as pd\n",
            filename="test.py",
            lazy=False,
        )
    )
    assert len(evaluations) == 2


def test_format_error_message():
    as_name = allowed_import_aliases.parse.AsName(
        qualname="pandas",
        alias="pa",
        lineno=1,
    )
    message = allowed_import_aliases.parse.format_error_message(
        filepath="test.py",
        qualname="pandas",
        allowed_aliases={"pd"},
        actual_alias=as_name
    )
    assert isinstance(message, str)
