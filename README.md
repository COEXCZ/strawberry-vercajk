# Strawberry vercajk
An opinionated toolkit for creating easy-to-work-with GraphQL APIs using https://github.com/strawberry-graphql/strawberry and Django.

## Installation
```bash
pip install strawberry-vercajk
```

## Settings
In your Django settings file, add the following settings:
```python
from strawberry_vercajk import StrawberryVercajkSettings

STRAWBERRY_VERCAJK: StrawberryVercajkSettings = {
    ...
}
```
See StrawberryVercajkSettings for configuration options.

## Documentation
- [(Input) Validation docs](./strawberry_vercajk/_validation/README.md)


## Contributing
Pull requests for any improvements are welcome.

[Poetry](https://github.com/sdispater/poetry) is used to manage dependencies.
To get started follow these steps:

```shell
git clone https://github.com/coexcz/strawberry-vercajk
cd strawberry_vercajk
poetry install
poetry run pytest
```

### Pre commit

We have a configuration for
[pre-commit](https://github.com/pre-commit/pre-commit), to add the hook run the
following command:

```shell
pre-commit install
```
