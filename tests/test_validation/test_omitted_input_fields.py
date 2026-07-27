"""
Fields which are nullable in the GraphQL schema may be left out of the input entirely.
An omitted field is passed to pydantic as absent (not as null), so pydantic decides what happens:
a required field reports a "missing" error, a field with a default gets its default.
"""
import typing

import pydantic
import pytest
import strawberry

import strawberry_vercajk
from strawberry_vercajk import GqlTypeAnnot, InputFactory


def _none_to_empty_string(value: typing.Any) -> typing.Any:
    return "" if value is None else value


@strawberry.type
class OkResponse:
    ok: bool = True


def _build_schema(input_cls: type[strawberry_vercajk.ValidatedInput]) -> strawberry.Schema:
    @strawberry.type
    class Query:
        @strawberry.field
        def test_query(self) -> str:  # not used, but the schema needs at least one query
            return "test"

    @strawberry.type
    class Mutation:
        @strawberry.mutation
        def test_mutation(
                self,
                input: input_cls,
        ) -> typing.Annotated[
            strawberry_vercajk.MutationErrorType | OkResponse,
            strawberry.union(name="TestOmittedResponse"),
        ]:
            errors = input.clean()
            if errors:
                return strawberry_vercajk.MutationErrorType(errors=errors)
            return OkResponse(ok=True)

    return strawberry.Schema(
        query=Query,
        mutation=Mutation,
        types={
            strawberry_vercajk.ErrorType,
        },
    )


MUTATION: str = """
    mutation testMutation($input: %(input_name)s!) {
        testMutation(input: $input) {
            ... on OkResponse {
                __typename
                ok
            }
            ... on MutationError {
                __typename
                errors {
                    location
                    code
                    message
                }
            }
        }
    }
"""


def test_omitted_gql_type_annot_field_reports_missing() -> None:
    class Model(pydantic.BaseModel):
        note: typing.Annotated[str, GqlTypeAnnot(str | None)]

    input_type = InputFactory.make(Model, name="OmittedGqlTypeAnnot")

    input_data = input_type()
    errors = input_data.clean()
    assert len(errors) == 1
    assert errors[0].code == "missing"
    assert errors[0].message == "Field required"
    assert errors[0].location == ["note"]


def test_omitted_field_is_not_the_same_as_explicit_null() -> None:
    """
    A `None` converted to an empty string by a validator is still an accepted value of the field,
    but leaving the field out of the input is not - pydantic never sees a value to convert.
    """
    class Model(pydantic.BaseModel):
        note: typing.Annotated[
            str,
            pydantic.BeforeValidator(_none_to_empty_string),
            GqlTypeAnnot(str | None),
        ]

    input_type = InputFactory.make(Model, name="OmittedVersusNull")

    omitted = input_type()
    errors = omitted.clean()
    assert len(errors) == 1
    assert errors[0].code == "missing"
    assert errors[0].location == ["note"]

    explicit_null = input_type(note=None)
    assert explicit_null.clean() == []
    assert explicit_null.clean_data.note == ""


def test_omitted_optional_annotation_field_reports_missing() -> None:
    class Model(pydantic.BaseModel):
        amount: int | None

    input_type = InputFactory.make(Model, name="OmittedOptionalAnnotation")

    input_data = input_type()
    errors = input_data.clean()
    assert len(errors) == 1
    assert errors[0].code == "missing"
    assert errors[0].location == ["amount"]


def test_omitted_empty_string_literal_union_field_reports_missing() -> None:
    class Model(pydantic.BaseModel):
        note: str | typing.Literal[""]

    input_type = InputFactory.make(Model, name="OmittedLiteralUnion")

    input_data = input_type()
    errors = input_data.clean()
    assert len(errors) == 1
    assert errors[0].code == "missing"
    assert errors[0].location == ["note"]

    explicit_null = input_type(note=None)
    assert explicit_null.clean() == []
    assert explicit_null.clean_data.note == ""


def test_omitted_nullable_list_field_reports_missing() -> None:
    class Model(pydantic.BaseModel):
        tags: list[str] | None

    input_type = InputFactory.make(Model, name="OmittedNullableList")

    input_data = input_type()
    errors = input_data.clean()
    assert len(errors) == 1
    assert errors[0].code == "missing"
    assert errors[0].location == ["tags"]


def test_omitted_field_with_default_uses_the_default() -> None:
    class Model(pydantic.BaseModel):
        region: str = "default region"
        note: str | None = None

    input_type = InputFactory.make(Model, name="OmittedWithDefault")

    input_data = input_type()
    assert input_data.clean() == []
    assert input_data.clean_data.region == "default region"
    assert input_data.clean_data.note is None


def test_omitted_non_null_field_raises() -> None:
    """A field which is non-null in the GraphQL schema stays a required argument of the input type."""
    class Model(pydantic.BaseModel):
        city: str
        street: str | None

    input_type = InputFactory.make(Model, name="OmittedNonNull")

    with pytest.raises(TypeError):
        input_type(street=None)


def test_omitted_field_in_nested_input_reports_nested_location() -> None:
    class NestedModel(pydantic.BaseModel):
        city: str
        postal_code: str | None

    class Model(pydantic.BaseModel):
        address: NestedModel

    nested_input_type = InputFactory.make(NestedModel, name="OmittedNestedAddress")
    input_type = InputFactory.make(Model, name="OmittedNested")

    input_data = input_type(address=nested_input_type(city="Prague"))
    errors = input_data.clean()
    assert len(errors) == 1
    assert errors[0].code == "missing"
    assert errors[0].location == ["address", "postalCode"]


def test_omitted_field_in_nested_input_list_reports_index_in_location() -> None:
    class NestedModel(pydantic.BaseModel):
        city: str
        postal_code: str | None

    class Model(pydantic.BaseModel):
        addresses: list[NestedModel]

    nested_input_type = InputFactory.make(NestedModel, name="OmittedNestedListAddress")
    input_type = InputFactory.make(Model, name="OmittedNestedList")

    input_data = input_type(
        addresses=[
            nested_input_type(city="Prague", postal_code="11000"),
            nested_input_type(city="Brno"),
        ],
    )
    errors = input_data.clean()
    assert len(errors) == 1
    assert errors[0].code == "missing"
    assert errors[0].location == ["addresses", 1, "postalCode"]


def test_omitted_fields_on_multiple_levels_are_all_reported() -> None:
    class NestedModel(pydantic.BaseModel):
        city: str
        postal_code: str | None

    class Model(pydantic.BaseModel):
        name: str | None
        address: NestedModel

    nested_input_type = InputFactory.make(NestedModel, name="OmittedMultiLevelAddress")
    input_type = InputFactory.make(Model, name="OmittedMultiLevel")

    input_data = input_type(address=nested_input_type(city="Prague"))
    errors = input_data.clean()
    assert len(errors) == 2
    assert errors[0].code == "missing"
    assert errors[0].location == ["name"]
    assert errors[1].code == "missing"
    assert errors[1].location == ["address", "postalCode"]


def test_omitted_field_in_mutation_returns_validation_error() -> None:
    class NestedModel(pydantic.BaseModel):
        city: str
        postal_code: str | None

    class Model(pydantic.BaseModel):
        name: str
        address: NestedModel

    InputFactory.make(NestedModel, name="OmittedMutationAddressInput")
    input_type = InputFactory.make(Model, name="OmittedMutationInput")
    schema = _build_schema(input_type)

    resp = schema.execute_sync(
        query=MUTATION % {"input_name": "OmittedMutationInput"},
        variable_values={
            "input": {
                "name": "John",
                "address": {"city": "Prague"},
            },
        },
    )
    assert resp.errors is None
    assert resp.data["testMutation"]["__typename"] == "MutationError"
    assert len(resp.data["testMutation"]["errors"]) == 1
    assert resp.data["testMutation"]["errors"][0]["code"] == "missing"
    assert resp.data["testMutation"]["errors"][0]["message"] == "Field required"
    assert resp.data["testMutation"]["errors"][0]["location"] == ["address", "postalCode"]


def test_nullable_input_fields_have_no_schema_default() -> None:
    """
    Being able to omit a field is not expressed as a schema default - the field stays without one,
    so that graphql-core forwards the omission instead of filling a value in.
    """
    class Model(pydantic.BaseModel):
        street: str | None
        note: typing.Annotated[str, GqlTypeAnnot(str | None)]
        region: str = ""

    input_type = InputFactory.make(Model, name="OmittedSchemaDefaults")
    sdl = _build_schema(input_type).as_str()

    assert "street: String\n" in sdl
    assert "note: String\n" in sdl
    assert 'region: String = ""' in sdl
