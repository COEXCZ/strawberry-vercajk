__all__ = [
    "OrderingDirection",
    "OrderingNullsPosition",
    "model_sort_enum",
]

import dataclasses
import enum
import functools
import typing

import pydantic
import strawberry

from strawberry_vercajk._base import utils as base_utils

_SORT_MODEL_ATTR_NAME: typing.LiteralString = "__VERCAJK_MODEL"


def model_sort_enum[T: "enum.StrEnum"](
    model: type,
) -> typing.Callable[[type[T]], type[T]]:
    @functools.wraps(model_sort_enum)
    def wrapper(
        sort_enum_class: type[T],
    ) -> type[T]:
        def _check_field_exists(sort_value: str) -> None:
            """Checks if the field exists on the model."""
            if issubclass(model, pydantic.BaseModel):
                return base_utils.check_pydantic_field_exists(model, sort_value)

            try:
                import django.db.models
                from strawberry_vercajk.django.utils import check_django_field_exists

                if issubclass(model, django.db.models.Model):
                    return check_django_field_exists(model, sort_value)
            except ImportError:
                pass

            raise TypeError(f"Unexpected model type {model} in {sort_enum_class.__name__} field sort enum.")

        for sort_enum in sort_enum_class:
            _check_field_exists(sort_value=sort_enum.value)
        return sort_enum_class

    return wrapper


class OrderingDirection(enum.Enum):
    ASC = strawberry.enum_value("ASC", description="Ascending order, i.e. 1, 2, 3... or a, b, c...")
    DESC = strawberry.enum_value("DESC", description="Descending order, i.e. 3, 2, 1... or c, b, a...")

    @property
    def is_asc(self) -> bool:
        return self == OrderingDirection.ASC

    @property
    def is_desc(self) -> bool:
        return self == OrderingDirection.DESC


class OrderingNullsPosition(enum.Enum):
    LAST = strawberry.enum_value("LAST", description="Null values are last in the ordering.")
    FIRST = strawberry.enum_value("FIRST", description="Null values are first in the ordering.")

    @property
    def is_asc(self) -> bool:
        return self == OrderingDirection.ASC

    @property
    def is_desc(self) -> bool:
        return self == OrderingDirection.DESC


@dataclasses.dataclass
class ImproperlyInitializedFieldSortEnumError(Exception):
    sort_enum_cls: type[enum.StrEnum]

    def __str__(self) -> str:
        return (
            f"`{self.sort_enum_cls.__name__}` is not properly initialized. "
            f"Did you forget to use `@{model_sort_enum.__name__}` decorator on it?"
        )
