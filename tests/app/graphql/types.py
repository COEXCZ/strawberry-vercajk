import enum
import typing

import pydantic
import strawberry
import strawberry.django

__all__ = [
    "ColorType",
    "FruitType",
    "FruitVarietyType",
    "FruitPlantType",
    "FruitEaterType",
    "FruitEaterSortEnum",
    "FruitVarietySortEnum",
    "FruitEaterFilterSet",
    "FruitVarietyFilterSet",
]

from django.db.models import QuerySet, F, Model, Q, OrderBy

import strawberry_vercajk.core as strawberry_vercajk
from tests.app import models
from tests.app.models import FruitPlant


@strawberry_vercajk.model_sort_enum(models.FruitEater)
class FruitEaterSortEnum(enum.StrEnum):
    ID = "id"
    NAME = "name"
    FAVOURITE_FRUIT_NAME = "favourite_fruit__name"


@strawberry_vercajk.model_sort_enum(models.Fruit)
class FruitSortEnum(enum.StrEnum):
    ID = "id"
    NAME = "name"
    COLOR_NAME = "color__name"
    PLANT_NAME = "plant__name"


@strawberry_vercajk.model_sort_enum(models.FruitVariety)
class FruitVarietySortEnum(enum.StrEnum):
    ID = "id"
    NAME = "name"


@strawberry_vercajk.model_filter(models.FruitEater)
class FruitEaterFilterSet(strawberry_vercajk.FilterSet):
    name: typing.Annotated[
        str | None,
        strawberry_vercajk.Filter(
            model_field="name",
            lookup="icontains",
        ),
    ] = None


@strawberry_vercajk.model_filter(models.FruitVariety)
class FruitVarietyFilterSet(strawberry_vercajk.FilterSet):
    name: typing.Annotated[
        str | None,
        strawberry_vercajk.Filter(
            model_field="name",
            lookup="icontains",
        ),
    ] = None


@strawberry_vercajk.model_filter(models.Fruit)
class FruitFilterSet(strawberry_vercajk.FilterSet):
    ids: typing.Annotated[
        list[int] | None,
        strawberry_vercajk.Filter(model_field="id", lookup="in"),
        pydantic.Field(
            description="Search by ids.",
        ),
    ] = None
    name: typing.Annotated[str | None, strawberry_vercajk.Filter(model_field="name", lookup="icontains")] = None


@strawberry.django.type(models.Fruit)
class FruitType:
    id: int
    name: str
    color: "ColorType|None"
    plant: "FruitPlantType|None"
    varieties: list["FruitVarietyType"]
    eaters: list["FruitEaterType"]

    @strawberry.field
    def eaters_with_params(
            self: "models.Fruit",
            info: "strawberry.Info",
            page: "strawberry_vercajk.PageInput|None" = strawberry.UNSET,
            sort: "strawberry_vercajk.SortInput[FruitEaterSortEnum]|None" = strawberry.UNSET,
            filters: strawberry_vercajk.pydantic_to_input_type(FruitEaterFilterSet) = strawberry.UNSET,
    ) -> strawberry_vercajk.ListInnerType["FruitEaterType"]:
        filters.clean()
        qs = models.FruitEater.objects.filter(favourite_fruit_id=self.pk)
        handler = strawberry_vercajk.DjangoListResponseHandler(qs, info)
        qs = handler.apply_filters(qs, filters.clean_data)
        qs = handler.apply_sorting(qs, sort)
        qs_page = handler.apply_pagination(qs, page)
        items_count = qs_page.items_count
        return strawberry_vercajk.ListInnerType[FruitEaterType](
            pagination=strawberry_vercajk.PageInnerMetadataType(
                current_page=page.page_number,
                page_size=page.page_size,
                items_count=items_count,
                has_next_page=qs_page.has_next(),
                has_previous_page=qs_page.has_previous(),
            ),
            items=qs_page.object_list,
        )

    @strawberry.field
    def varieties_with_params(
            self: "models.Fruit",
            info: "strawberry.Info",
            page: "strawberry_vercajk.PageInput|None" = strawberry.UNSET,
            sort: "strawberry_vercajk.SortInput[FruitVarietySortEnum]|None" = strawberry.UNSET,
            filters: strawberry_vercajk.pydantic_to_input_type(FruitVarietyFilterSet) = strawberry.UNSET,
    ) -> strawberry_vercajk.ListInnerType["FruitVarietyType"]:
        filters.clean()
        qs = models.FruitVariety.objects.filter(fruits__id=self.pk)
        handler = strawberry_vercajk.DjangoListResponseHandler(qs, info)
        qs = handler.apply_filters(qs, filters.clean_data)
        qs = handler.apply_sorting(qs, sort)
        qs_page = handler.apply_pagination(qs, page)
        items_count = qs_page.items_count
        return strawberry_vercajk.ListInnerType[FruitVarietyType](
            pagination=strawberry_vercajk.PageInnerMetadataType(
                current_page=page.page_number,
                page_size=page.page_size,
                items_count=items_count,
                has_next_page=qs_page.has_next(),
                has_previous_page=qs_page.has_previous(),
            ),
            items=qs_page.object_list,
        )


@strawberry.django.type(models.FruitVariety)
class FruitVarietyType:
    id: int
    name: str
    fruits: list["FruitType"]

    @strawberry.field
    def fruits_with_params(
            self: "models.FruitVariety",
            info: "strawberry.Info",
            page: "strawberry_vercajk.PageInput|None" = strawberry.UNSET,
            sort: "strawberry_vercajk.SortInput[FruitSortEnum]|None" = strawberry.UNSET,
            filters: strawberry_vercajk.pydantic_to_input_type(FruitFilterSet) = strawberry.UNSET,
    ) -> strawberry_vercajk.ListInnerType["FruitType"]:
        filters.clean()
        qs = models.Fruit.objects.filter(varieties__id=self.pk)
        handler = strawberry_vercajk.DjangoListResponseHandler(qs, info)
        qs = handler.apply_filters(qs, filters.clean_data)
        qs = handler.apply_sorting(qs, sort)
        qs_page = handler.apply_pagination(qs, page)
        items_count = qs_page.items_count
        return strawberry_vercajk.ListInnerType[FruitType](
            pagination=strawberry_vercajk.PageInnerMetadataType(
                current_page=page.page_number,
                page_size=page.page_size,
                items_count=items_count,
                has_next_page=qs_page.has_next(),
                has_previous_page=qs_page.has_previous(),
            ),
            items=qs_page.object_list,
        )


@strawberry.django.type(FruitPlant)
class FruitPlantType:
    id: int
    name: str
    fruit: FruitType | None


@strawberry.django.type(models.Color)
class ColorType:
    id: int
    name: str
    fruits: list[FruitType]


@strawberry.django.type(models.FruitEater)
class FruitEaterType:
    id: int
    name: str
    favourite_fruit: FruitType | None
