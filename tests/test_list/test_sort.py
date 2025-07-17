import enum
import typing

import pytest

from strawberry_vercajk._base.exceptions import ModelFieldDoesNotExistError
from strawberry_vercajk._list.sort import model_sort_enum
from tests.app import models


def test_sort_enum_ok() -> None:
    @model_sort_enum(models.Fruit)
    class FruitSortEnum(enum.StrEnum):
        NAME = "name"


def test_sort_enum_with_existing_related_model_field_ok() -> None:
    @model_sort_enum(models.FruitEater)
    class FruitEaterSortEnum(enum.StrEnum):
        PLANT_NAME = "favourite_fruit__plant__name"


def test_sort_enum_with_nonexistent_field_raises_error() -> None:
    with pytest.raises(ModelFieldDoesNotExistError) as exc_info:
        @model_sort_enum(models.Fruit)
        class FruitSortEnum(enum.StrEnum):
            NAME = "nonexistent_field"

    assert exc_info.value.field == "nonexistent_field"
    assert exc_info.value.full_field_path == "nonexistent_field"
    assert exc_info.value.model == models.Fruit
    assert exc_info.value.root_model == models.Fruit
    assert str(exc_info.value) == 'The `nonexistent_field` of `Fruit` does not exist.'


def test_sort_enum_with_nonexistent_related_model_field_raises_error() -> None:
    with pytest.raises(ModelFieldDoesNotExistError) as exc_info:
        @model_sort_enum(models.FruitEater)
        class FruitEaterSortEnum(enum.StrEnum):
            PLANT_NAME = "favourite_fruit__plant__non_existent"

    assert exc_info.value.field == "non_existent"
    assert exc_info.value.full_field_path == "favourite_fruit__plant__non_existent"
    assert exc_info.value.model == models.FruitPlant
    assert exc_info.value.root_model == models.FruitEater
