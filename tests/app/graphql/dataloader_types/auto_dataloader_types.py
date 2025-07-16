import strawberry
import strawberry.django

import strawberry_vercajk.core as strawberry_vercajk
from strawberry_vercajk._dataloaders import auto_dataloader_field
from tests.app import models
from tests.app.graphql.types import (
    FruitVarietyFilterSet, FruitEaterFilterSet, FruitEaterSortEnum,
    FruitVarietySortEnum, FruitFilterSet, FruitSortEnum,
)


@strawberry.django.type(models.Color)
class ColorAutoDataLoaderType:
    id: int
    name: str
    fruits: list["FruitAutoDataLoaderType"] = auto_dataloader_field()


@strawberry.django.type(models.FruitPlant)
class FruitPlantAutoDataLoaderType:
    id: int
    name: str
    fruit: "FruitAutoDataLoaderType|None" = auto_dataloader_field()


@strawberry.django.type(models.FruitVariety)
class FruitVarietyAutoDataLoaderType:
    id: int
    name: str
    fruits: list["FruitAutoDataLoaderType"] = auto_dataloader_field()
    fruits_with_params: strawberry_vercajk.ListInnerType["FruitAutoDataLoaderType"] = auto_dataloader_field(
        field_name="fruits",
        filters=strawberry_vercajk.pydantic_to_input_type(FruitFilterSet),
        page=strawberry_vercajk.PageInput,
        sort=strawberry_vercajk.SortInput[FruitSortEnum],
    )


@strawberry.django.type(models.FruitEater)
class FruitEaterAutoDataLoaderType:
    id: int
    name: str
    favourite_fruit: "FruitAutoDataLoaderType|None" = auto_dataloader_field()


@strawberry.django.type(models.Fruit)
class FruitAutoDataLoaderType:
    """Uses auto dataloader fields."""
    id: int
    name: str
    color: "ColorAutoDataLoaderType|None" = auto_dataloader_field()
    plant: "FruitPlantAutoDataLoaderType|None" = auto_dataloader_field()
    varieties: list[FruitVarietyAutoDataLoaderType] = auto_dataloader_field()
    varieties_with_params: strawberry_vercajk.ListInnerType[FruitVarietyAutoDataLoaderType] = auto_dataloader_field(
        field_name="varieties",
        filters=strawberry_vercajk.pydantic_to_input_type(FruitVarietyFilterSet),
        page=strawberry_vercajk.PageInput,
        sort=strawberry_vercajk.SortInput[FruitVarietySortEnum],
    )
    eaters: list[FruitEaterAutoDataLoaderType] = auto_dataloader_field()
    eaters_with_params: strawberry_vercajk.ListInnerType[FruitEaterAutoDataLoaderType] = auto_dataloader_field(
        field_name="eaters",
        filters=strawberry_vercajk.pydantic_to_input_type(FruitEaterFilterSet),
        page=strawberry_vercajk.PageInput,
        sort=strawberry_vercajk.SortInput[FruitEaterSortEnum],
    )
