import dataclasses
import inspect

import pydantic

from strawberry_vercajk._base import exceptions


def check_pydantic_field_exists(model: type["pydantic.BaseModel"], field_path: str) -> None:
    """
    Checks if the field exists on the pydantic model.
    :param model: Pydantic model
    :param field_path: Field name, potentially with a related model path (e.g. `related_model.field`)
    :raises ModelFieldDoesNotExistError: If the field does not exist on the model.
    """
    field_path_sep: list[str] = field_path.split(".")
    pyd_model = model
    for field in field_path_sep:
        try:
            model_field = pyd_model.__pydantic_fields__[field]
        except KeyError as e:
            raise exceptions.ModelFieldDoesNotExistError(
                root_model=model,
                full_field_path=field_path,
                model=pyd_model,
                field=field,
            ) from e
        if isinstance(model_field, pydantic.BaseModel):
            pyd_model = model_field


def check_dataclass_field_exists(model: type, field_path: str) -> None:
    """
    Checks if the field exists on the dataclass model.
    :param model: Dataclass model
    :param field_path: Field name, potentially with a related model path (e.g. `related_model.field`)
    :raises ModelFieldDoesNotExistError: If the field does not exist on the model.
    """
    field_path_sep: list[str] = field_path.split(".")
    dataclass_model = model
    for field_name in field_path_sep:
        field_name__field = {f.name: f for f in dataclasses.fields(dataclass_model)}
        if field_name not in field_name__field:
            raise exceptions.ModelFieldDoesNotExistError(
                root_model=model,
                full_field_path=field_path,
                model=dataclass_model,
                field=field_name,
            )
        if dataclasses.is_dataclass(field_name__field[field_name].type):
            dataclass_model = field_name__field[field_name].type


def func_has_no_args(func: callable) -> bool:
    """
    Returns True if `func` takes no *required* arguments
    (optionally allowing an instance `self` for methods).
    """
    sig = inspect.signature(func)
    for name, param in sig.parameters.items():
        # skip varargs and kwargs
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        # skip the first 'self' on instance methods
        if name == "self":
            continue
        # any other parameter (positional-only or keyword-or-positional)
        return False
    return True
