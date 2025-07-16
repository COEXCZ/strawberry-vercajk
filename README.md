# Strawberry vercajk
An opinionated toolkit for creating easy-to-work-with GraphQL APIs using https://github.com/strawberry-graphql/strawberry and Django.

## Installation
```bash
pip install strawberry-vercajk
```

with django support:
```bash
pip install strawberry-vercajk[django]
```

## Settings
In your Django settings file, add the following settings:
```python
from strawberry_vercajk.core import StrawberryVercajkSettings

STRAWBERRY_VERCAJK: StrawberryVercajkSettings = {
    ...
}
```

Or if you are not using Django, you can call the following function in your app entrypoint:
```python
from strawberry_vercajk.core import StrawberryVercajkSettings, configure_strawberry_vercajk
configure_strawberry_vercajk(StrawberryVercajkSettings(
    # Your configuration here
))
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
