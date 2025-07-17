import enum

import pytest
import strawberry

from strawberry_vercajk import pydantic_to_input_type
from strawberry_vercajk.django import DjangoListResponseHandler
from strawberry_vercajk._list.graphql import PageInput, SortInput, ListType
from strawberry_vercajk._list.sort import model_sort_enum
from tests.app import factories, models
from tests.app.graphql import types
from tests.app.graphql.types import FruitFilterSet
from tests.base import get_list_query, ListQueryKwargs


@model_sort_enum(models.Fruit)
class FruitsSortEnum(enum.StrEnum):
    ID = "id"
    NAME = "name"


@strawberry.type
class Query:
    @strawberry.field()
    def fruits(
        self,
        info: strawberry.Info,
        page: PageInput | None = strawberry.UNSET,
        sort: SortInput[FruitsSortEnum] | None = strawberry.UNSET,
        filters: pydantic_to_input_type(FruitFilterSet) | None = strawberry.UNSET,
    ) -> ListType[types.FruitType]:
        handler = DjangoListResponseHandler[models.Fruit](models.Fruit.objects.all(), info)
        resp = handler.process(page=page, sort=sort, filters=filters)
        return resp


test_schema = strawberry.Schema(
    query=Query,
    mutation=None,
)



@pytest.mark.django_db()
def test_page() -> None:
    factories.FruitFactory.create_batch(11)
    q = get_list_query(
        query_name="fruits",
        page={
            "pageNumber": 1,
            "pageSize": 5
        },
        sort=[{"field": FruitsSortEnum.NAME.name, "direction": "ASC"}],
        fields=[
            "id",
            "name",
        ],
    )
    resp = test_schema.execute_sync(q)

    assert resp.errors is None
    assert resp.data is not None
    assert resp.data["fruits"]["pagination"]["currentPage"] == 1
    assert resp.data["fruits"]["pagination"]["itemsCount"] == 5
    assert resp.data["fruits"]["pagination"]["totalItemsCount"] == 11
    assert resp.data["fruits"]["pagination"]["pageSize"] == 5
    assert resp.data["fruits"]["pagination"]["totalPagesCount"] == 3
    assert resp.data["fruits"]["pagination"]["hasPreviousPage"] is False
    assert resp.data["fruits"]["pagination"]["hasNextPage"] is True
    assert len(resp.data["fruits"]["items"]) == 5


@pytest.mark.django_db()
def test_sort() -> None:
    factories.FruitFactory.create(name="Apple")
    factories.FruitFactory.create(name="Banana")
    q_kwargs: ListQueryKwargs = {
        "query_name": "fruits",
        "page": {
            "pageNumber": 1,
            "pageSize": 10
        },
        "sort": [{"field": FruitsSortEnum.NAME.name, "direction": "ASC"}],
        "fields": [
            "id",
            "name",
        ],
    }
    q = get_list_query(**q_kwargs)
    resp = test_schema.execute_sync(q)
    assert resp.data["fruits"]["items"][0]["name"] == "Apple"

    q_kwargs["sort"][0]["direction"] = "DESC"
    q = get_list_query(**q_kwargs)
    resp = test_schema.execute_sync(q)
    assert resp.data["fruits"]["items"][0]["name"] == "Banana"


@pytest.mark.django_db()
def test_filter_by_id() -> None:
    factories.FruitFactory.create_batch(11)

    q = get_list_query(
        query_name="fruits",
        page={
            "pageNumber": 1,
            "pageSize": 10
        },
        filters={
            "ids": [1, 2]
        },
        fields=[
            "id",
            "name",
        ],
    )
    resp = test_schema.execute_sync(q)
    assert resp.errors is None
    assert resp.data is not None
    assert len(resp.data["fruits"]["items"]) == 2
    assert resp.data["fruits"]["items"][0]["id"] == 1
    assert resp.data["fruits"]["items"][1]["id"] == 2


@pytest.mark.django_db()
def test_filter_by_name() -> None:
    fruits = factories.FruitFactory.create_batch(10)
    icontains = fruits[0].name[:3]
    q = get_list_query(
        query_name="fruits",
        page={
            "pageNumber": 1,
            "pageSize": 10
        },
        filters={
            "name": icontains,
        },
        fields=[
            "id",
            "name",
        ],
    )
    resp = test_schema.execute_sync(q)
    assert resp.errors is None
    assert resp.data is not None
    for fruit in resp.data["fruits"]["items"]:
        assert icontains in fruit["name"]

    # fruits not in response should not contain the icontains string
    fruit_ids_in_resp = [fruit["id"] for fruit in resp.data["fruits"]["items"]]
    for fruit in fruits:
        if fruit.pk not in fruit_ids_in_resp:
            assert icontains not in fruit.name



@pytest.mark.django_db()
def test_filter_by_multiple_fields() -> None:
    fruits = factories.FruitFactory.create_batch(10)
    icontains = fruits[0].name[:3]
    q = get_list_query(
        query_name="fruits",
        page={
            "pageNumber": 1,
            "pageSize": 10
        },
        filters={
            "name": icontains,
            "ids": [fruits[0].pk],
        },
        fields=[
            "id",
            "name",
        ],
    )
    resp = test_schema.execute_sync(q)
    assert resp.errors is None
    assert resp.data is not None
    assert len(resp.data["fruits"]["items"]) == 1
    assert resp.data["fruits"]["items"][0]["id"] == fruits[0].pk
