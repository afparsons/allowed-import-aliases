# allowed-import-aliases
Whitelist Python import aliases. Intended for use with [pre-commit](https://pre-commit.com/).

---

## Installation

```shell
pip install .
```

## Usage

```yaml
# .pre-commit-config.yaml

- repo: https://github.com/afparsons/allowed-import-aliases
  rev: 0.1.0
  hooks:
    - id: allowed-import-aliases
      args:
        - -p 4
        - -a pandas pd
        - -a pyspark.sql.functions psf
        - -a foo.bar fb baz
```

Arguments 

| Option | Argument type | Description                                                                                                                             |
|--------|---------------|-----------------------------------------------------------------------------------------------------------------------------------------|
| `-t`   | integer       | Whether to use `concurrent.futures.ThreadPoolExecutor`, and if so, how many workers to use.                                             |
| `-p`   | integer       | Whether to use `concurrent.futures.ProcessPoolExecutor`, and if so, how many workers to use.                                            |
| `-a`   | strings       | The first string corresponds to the import, and all successive space-delimited strings correspond to acceptable aliases for the import. |

## Credits

Inspired by Dr. David Weirich
