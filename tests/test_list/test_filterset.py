import typing

import pytest

import strawberry_vercajk
from strawberry_vercajk._base.exceptions import ModelFieldDoesNotExistError
from strawberry_vercajk._list.filter import (
    model_filter, FilterSet, Filter, FilterFieldTypeNotSupportedError,
    FilterFieldNotAnInstanceError, FilterFieldLookupAmbiguousError, MissingFilterAnnotationError,
    MoreThanOneFilterAnnotationError,
)
from tests.app import models


def test_filterset_ok() -> None:
    @model_filter(models.Fruit)
    class FruitFilterSet(FilterSet):
        name: typing.Annotated[str | None, Filter(model_field="name", lookup="icontains")] = None


def test_filterset_with_nonexistent_field_raises_error() -> None:
    with pytest.raises(ModelFieldDoesNotExistError) as exc_info:
        @model_filter(models.Fruit)
        class FruitFilterSet(FilterSet):
            name: typing.Annotated[str | None, Filter(model_field="nonexistent_field", lookup="icontains")] = None

    assert exc_info.value.field == "nonexistent_field"
    assert exc_info.value.full_field_path == "nonexistent_field"
    assert exc_info.value.model == models.Fruit
    assert exc_info.value.root_model == models.Fruit
    assert str(exc_info.value) == 'The `nonexistent_field` of `Fruit` does not exist.'


def test_filterset_with_nonexistent_related_model_field_raises_error() -> None:
    with pytest.raises(ModelFieldDoesNotExistError) as exc_info:
        @model_filter(models.FruitEater)
        class FruitEaterFilterSet(FilterSet):
            non_existent: typing.Annotated[str | None, Filter(
                model_field="favourite_fruit__plant__non_existent",
                lookup="icontains")
            ] = None

    assert exc_info.value.field == "non_existent"
    assert exc_info.value.full_field_path == "favourite_fruit__plant__non_existent"
    assert exc_info.value.model == models.FruitPlant
    assert exc_info.value.root_model == models.FruitEater
    assert str(exc_info.value)


def test_filterset_with_nonexistent_related_model_field_does_not_raise_an_error_if_check_field_exists_false() -> None:
    @model_filter(models.FruitEater)
    class FruitEaterFilterSet(FilterSet):
        non_existent: typing.Annotated[str | None, Filter(
            model_field="favourite_fruit__plant__non_existent",
            lookup="icontains",
            check_field_exists=False,
        ),
        ] = None


def test_filter_field_annotated_as_none_raises_error() -> None:
    with pytest.raises(FilterFieldTypeNotSupportedError) as exc_info:
        @model_filter(models.FruitEater)
        class FruitEaterFilterSet(FilterSet):
            name: typing.Annotated[None, Filter(
                model_field="name",
                lookup="icontains")
            ] = None


def test_filter_field_annotated_as_list_without_type_raises_error() -> None:
    with pytest.raises(FilterFieldTypeNotSupportedError) as exc_info:
        @model_filter(models.FruitEater)
        class FruitEaterFilterSet(FilterSet):
            name: typing.Annotated[list, Filter(
                model_field="name",
                lookup="icontains")
            ] = None


def test_filter_field_annotated_as_a_union_of_types_raises_error() -> None:
    with pytest.raises(FilterFieldTypeNotSupportedError) as exc_info:
        @model_filter(models.FruitEater)
        class FruitEaterFilterSet(FilterSet):
            name: typing.Annotated[int | str, Filter(
                model_field="name",
                lookup="icontains")
            ] = None


def test_filter_field_not_an_instance_of_filter_raises_error() -> None:
    with pytest.raises(FilterFieldNotAnInstanceError) as exc_info:
        @model_filter(models.FruitEater)
        class FruitEaterFilterSet(FilterSet):
            name: typing.Annotated[str, Filter] = None


def test_filter_is_a_list_with_invalid_lookup_raises_error() -> None:
    with pytest.raises(FilterFieldLookupAmbiguousError) as exc_info:
        @model_filter(models.FruitEater)
        class FruitEaterFilterSet(FilterSet):
            name: typing.Annotated[
                list[str] | None,
                Filter(model_field="name", lookup="exact")  # needs to be `in` or `overlap` for list
            ] = None


def test_no_filter_annotation_raises_error() -> None:
    with pytest.raises(MissingFilterAnnotationError) as exc_info:
        @model_filter(models.FruitEater)
        class FruitEaterFilterSet(FilterSet):
            name: str | None = None


def test_multiple_filters_annotation_raises_error() -> None:
    with pytest.raises(MoreThanOneFilterAnnotationError) as exc_info:
        @model_filter(models.FruitEater)
        class FruitEaterFilterSet(FilterSet):
            name: typing.Annotated[
                str | None,
                Filter(model_field="name", lookup="exact"),
                Filter(model_field="name", lookup="exact"),
            ] = None


def test_filterq_is_noop_false() -> None:
    q = strawberry_vercajk.FilterQ(field="name", lookup="exact", value="pepa")
    assert not q.is_noop


def test_filterq_is_noop_true() -> None:
    q = strawberry_vercajk.FilterQ()
    assert q.is_noop


def test_filterq_is_noop_true_if_negated_empty() -> None:
    q = ~strawberry_vercajk.FilterQ()
    assert q.is_noop


def test_filterq_is_noop_false_if_noop_and_noop() -> None:
    q = strawberry_vercajk.FilterQ()
    q &= strawberry_vercajk.FilterQ()
    assert q.is_noop


def test_filterq_is_noop_false_if_noop_or_noop() -> None:
    q = strawberry_vercajk.FilterQ()
    q |= strawberry_vercajk.FilterQ()
    assert q.is_noop


def test_filterq_is_noop_false_if_noop_and_op() -> None:
    q = strawberry_vercajk.FilterQ()
    q &= strawberry_vercajk.FilterQ(field="name", lookup="exact", value="pepa")
    assert not q.is_noop


def test_filterq_is_noop_false_if_noop_or_op() -> None:
    q = strawberry_vercajk.FilterQ()
    q |= strawberry_vercajk.FilterQ(field="name", lookup="exact", value="pepa")
    assert not q.is_noop


def test_filterq_is_noop_false_if_op_and_noop() -> None:
    q = strawberry_vercajk.FilterQ(field="name", lookup="exact", value="pepa")
    q &= strawberry_vercajk.FilterQ()
    assert not q.is_noop


def test_filterq_is_noop_false_if_op_or_noop() -> None:
    q = strawberry_vercajk.FilterQ(field="name", lookup="exact", value="pepa")
    q |= strawberry_vercajk.FilterQ()
    assert not q.is_noop

def test_filterq_is_noop_false_complex() -> None:
    fields = [
        ("name", "pepa"),
        ("description", "josefov"),
    ]
    q = strawberry_vercajk.FilterQ()
    for field_name, field_value in fields:
        q |= strawberry_vercajk.FilterQ(
            field=field_name,
            lookup="exact",
            value=field_value,
        ) & strawberry_vercajk.FilterQ(
            field=field_name,
            lookup="in",
            value=field_value,
        )
    assert not q.is_noop


def test_filter_field_annotated_as_literal() -> None:
    @model_filter(models.FruitEater)
    class FruitEaterFilterSet(FilterSet):
        field: typing.Annotated[
            typing.Literal["VALUE_1", "VALUE_2", "VALUE_3"],
            Filter(
                model_field="name",
                lookup="icontains",
            )
        ] = None
