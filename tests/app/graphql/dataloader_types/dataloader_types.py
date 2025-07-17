import enum
import typing

import strawberry
import strawberry.django

from strawberry_vercajk import (
    PageInput, model_sort_enum, SortInput, model_filter, FilterSet, Filter,
    pydantic_to_input_type,
)
from strawberry_vercajk._dataloaders import PKDataLoader, FKDataLoader, M2MDataLoader
from tests.app import models
from tests.app.graphql.types import FruitEaterSortEnum, FruitEaterFilterSet


class FruitDataLoader(PKDataLoader):
    Config = {
        "model": models.Fruit,
    }


class ColorPKDataLoader(PKDataLoader):
    Config = {
        "model": models.Color,
    }


class FruitReverseOneToOneDataLoader(FKDataLoader):
    Config = {
        "field_descriptor": models.FruitPlant.fruit,
    }


class FruitPlantPKDataLoader(PKDataLoader):
    Config = {
        "model": models.FruitPlant,
    }


class FruitEatersReverseFKDataLoader(FKDataLoader):
    Config = {
        "field_descriptor": models.FruitEater.favourite_fruit,
    }


class FruitPlantFruitReverseOneToOneDataLoader(FKDataLoader):
    Config = {
        "field_descriptor": models.Fruit.plant,
    }


class FruitVarietiesM2MDataLoader(M2MDataLoader):
    Config = {
        "field_descriptor": models.Fruit.varieties,
        "query_origin": models.Fruit,
    }


class FruitVarietyFruitsM2MDataLoader(M2MDataLoader):
    Config = {
        "field_descriptor": models.Fruit.varieties,
        "query_origin": models.FruitVariety,  # from which model of the two is the query originated
    }


@strawberry.django.type(models.Color)
class ColorTypeDataLoadersType:
    """Uses the simplest form of dataloaders."""

    id: int
    name: str

    @strawberry.field
    def fruits(self: "models.Color", info: "strawberry.Info") -> list["FruitTypeDataLoaders"]:
        return ColorPKDataLoader(info=info).load(self.pk)


@strawberry.django.type(models.FruitEater)
class FruitEaterDataLoadersType:
    """Uses the simplest form of dataloaders."""

    id: int
    name: str

    @strawberry.field
    def favourite_fruit(self: "models.FruitEater", info: "strawberry.Info") -> "FruitTypeDataLoaders|None":
        return FruitDataLoader(info=info).load(self.favourite_fruit_id)


@strawberry.django.type(models.FruitPlant)
class FruitPlantDataLoadersType:
    """Uses the simplest form of dataloaders."""

    id: int
    name: str

    @strawberry.field
    def fruit(self: "models.FruitPlant", info: "strawberry.Info") -> "FruitTypeDataLoaders|None":
        return FruitReverseOneToOneDataLoader(info=info).load(self.pk)


@strawberry.django.type(models.FruitVariety)
class FruitVarietyDataLoadersType:
    """Uses the simplest form of dataloaders."""

    id: int
    name: str

    @strawberry.field
    def fruits(self: "models.FruitVariety", info: "strawberry.Info") -> list["FruitTypeDataLoaders"]:
        return FruitVarietyFruitsM2MDataLoader(info=info).load(self.pk)


@strawberry.django.type(models.Fruit)
class FruitTypeDataLoaders:
    """Uses the simplest form of dataloaders."""

    id: int
    name: str

    @strawberry.field
    def color(self: "models.Fruit", info: "strawberry.Info") -> ColorTypeDataLoadersType | None:
        return ColorPKDataLoader(info=info).load(self.color_id)

    @strawberry.field
    def plant(self: "models.Fruit", info: "strawberry.Info") -> FruitPlantDataLoadersType | None:
        return FruitPlantPKDataLoader(info=info).load(self.plant_id)

    @strawberry.field
    def eaters(self: "models.Fruit", info: "strawberry.Info") -> list[FruitEaterDataLoadersType]:
        return FruitEatersReverseFKDataLoader(info=info).load(self.pk)

    @strawberry.field
    def eaters_with_params(
            self: "models.Fruit",
            info: "strawberry.Info",
            page: "PageInput|None" = strawberry.UNSET,
            sort: "SortInput[FruitEaterSortEnum]|None" = strawberry.UNSET,
            filters: pydantic_to_input_type(FruitEaterFilterSet) | None = strawberry.UNSET,
    ) -> list[FruitEaterDataLoadersType]:
        errors = filters.clean()
        return FruitEatersReverseFKDataLoader(info=info).load(self.pk)

    @strawberry.field
    def varieties(self: "models.Fruit", info: "strawberry.Info") -> list[FruitVarietyDataLoadersType]:
        return FruitVarietiesM2MDataLoader(info=info).load(self.pk)
