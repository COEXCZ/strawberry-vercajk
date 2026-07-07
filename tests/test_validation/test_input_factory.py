import typing
from decimal import Decimal

import pydantic
import pydantic_core
import strawberry
from strawberry.schema_directive import StrawberrySchemaDirective, Location
from strawberry.types.base import StrawberryOptional, StrawberryList

import strawberry_vercajk
from strawberry_vercajk import InputFactory, FieldConstraintsDirective


def test_input_factory_make_input() -> None:
    class Model(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(description="Name of the model", deprecated="Deprecation reason")]

    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert definition.name == "Model"
    assert len(definition.fields) == 1
    assert definition.fields[0].name == "name"
    assert definition.fields[0].description == "Name of the model"
    assert definition.fields[0].type_annotation.annotation is str
    assert definition.fields[0].deprecation_reason == "Deprecation reason"


def test_input_factory_make_is_cached() -> None:
    class Model(pydantic.BaseModel):
        name: str

    gql_input = InputFactory.make(Model)
    assert InputFactory._REGISTRY[Model] == gql_input
    gql_input_cached = InputFactory.make(Model)
    assert gql_input == gql_input_cached


def test_input_factory_make_with_nested_input() -> None:
    class NestedModel(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(description="Name of the nested model")]

    class Model(pydantic.BaseModel):
        nested: typing.Annotated[NestedModel, pydantic.Field(description="Descr.", deprecated="Deprecation reason")]


    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert definition.name == "Model"
    assert len(definition.fields) == 1
    assert definition.fields[0].name == "nested"
    assert definition.fields[0].type_annotation.annotation is InputFactory.make(NestedModel)
    assert definition.fields[0].description == "Descr."
    assert definition.fields[0].deprecation_reason == "Deprecation reason"
    assert definition.fields[0].type.__strawberry_definition__.name == "NestedModel"
    assert len(definition.fields[0].type.__strawberry_definition__.fields) == 1
    assert definition.fields[0].type.__strawberry_definition__.fields[0].name == "name"
    assert definition.fields[0].type.__strawberry_definition__.fields[0].type is str
    assert definition.fields[0].type.__strawberry_definition__.fields[0].description == "Name of the nested model"


def test_input_factory_make_with_nested_input_optional() -> None:
    class NestedModel(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(description="Name of the nested model")]

    class Model(pydantic.BaseModel):
        nested: typing.Annotated[NestedModel | None, pydantic.Field(description="Descr.", deprecated="Deprecation reason")]


    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert definition.name == "Model"
    assert len(definition.fields) == 1
    assert definition.fields[0].name == "nested"
    assert definition.fields[0].type_annotation.annotation == InputFactory.make(NestedModel) | None
    assert definition.fields[0].description == "Descr."
    assert definition.fields[0].deprecation_reason == "Deprecation reason"
    assert definition.fields[0].type.of_type.__strawberry_definition__.name == "NestedModel"
    assert len(definition.fields[0].type.of_type.__strawberry_definition__.fields) == 1
    assert definition.fields[0].type.of_type.__strawberry_definition__.fields[0].name == "name"
    assert definition.fields[0].type.of_type.__strawberry_definition__.fields[0].type is str
    assert definition.fields[0].type.of_type.__strawberry_definition__.fields[0].description == "Name of the nested model"


def test_input_factory_make_with_nested_input_list() -> None:
    class NestedModel(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(description="Name of the nested model")]

    class Model(pydantic.BaseModel):
        nested: typing.Annotated[list[NestedModel], pydantic.Field(description="Descr.", deprecated="Deprecation reason")]


    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert definition.name == "Model"
    assert len(definition.fields) == 1
    assert definition.fields[0].name == "nested"
    assert definition.fields[0].type_annotation.annotation == list[InputFactory.make(NestedModel)]
    assert definition.fields[0].description == "Descr."
    assert definition.fields[0].deprecation_reason == "Deprecation reason"
    assert definition.fields[0].type.of_type.__strawberry_definition__.name == "NestedModel"
    assert len(definition.fields[0].type.of_type.__strawberry_definition__.fields) == 1
    assert definition.fields[0].type.of_type.__strawberry_definition__.fields[0].name == "name"
    assert definition.fields[0].type.of_type.__strawberry_definition__.fields[0].type is str
    assert definition.fields[0].type.of_type.__strawberry_definition__.fields[0].description == "Name of the nested model"


def test_input_factory_make_with_nested_input_list_optional() -> None:
    class NestedModel(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(description="Name of the nested model")]

    class Model(pydantic.BaseModel):
        nested: typing.Annotated[list[NestedModel] | None, pydantic.Field(description="Descr.", deprecated="Deprecation reason")]


    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert definition.name == "Model"
    assert len(definition.fields) == 1
    assert definition.fields[0].name == "nested"
    assert definition.fields[0].type_annotation.annotation == list[InputFactory.make(NestedModel)] | None
    assert definition.fields[0].description == "Descr."
    assert definition.fields[0].deprecation_reason == "Deprecation reason"
    assert definition.fields[0].type.of_type.of_type.__strawberry_definition__.name == "NestedModel"
    assert len(definition.fields[0].type.of_type.of_type.__strawberry_definition__.fields) == 1
    assert definition.fields[0].type.of_type.of_type.__strawberry_definition__.fields[0].name == "name"
    assert definition.fields[0].type.of_type.of_type.__strawberry_definition__.fields[0].type is str
    assert definition.fields[0].type.of_type.of_type.__strawberry_definition__.fields[0].description == "Name of the nested model"


def test_input_factory_make_with_nested_input_list_optional_nested_optional() -> None:
    class NestedModel(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(description="Name of the nested model")]

    class Model(pydantic.BaseModel):
        nested: typing.Annotated[list[NestedModel | None] | None, pydantic.Field(description="Descr.", deprecated="Deprecation reason")]

    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert definition.name == "Model"
    assert len(definition.fields) == 1
    assert definition.fields[0].name == "nested"
    assert definition.fields[0].type_annotation.annotation == list[InputFactory.make(NestedModel) | None] | None
    assert definition.fields[0].description == "Descr."
    assert definition.fields[0].deprecation_reason == "Deprecation reason"
    assert definition.fields[0].type.of_type.of_type.of_type.__strawberry_definition__.name == "NestedModel"
    assert len(definition.fields[0].type.of_type.of_type.of_type.__strawberry_definition__.fields) == 1
    assert definition.fields[0].type.of_type.of_type.of_type.__strawberry_definition__.fields[0].name == "name"
    assert definition.fields[0].type.of_type.of_type.of_type.__strawberry_definition__.fields[0].type is str
    assert definition.fields[0].type.of_type.of_type.of_type.__strawberry_definition__.fields[0].description == "Name of the nested model"


def test_input_factory_input_has_constraints_directive() -> None:
    class Model(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(min_length=1)]

    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert len(definition.fields) == 1
    assert len(definition.fields[0].directives) == 1
    directive: FieldConstraintsDirective = definition.fields[0].directives[0]
    directive_schema: "StrawberrySchemaDirective" = directive.__strawberry_directive__
    assert directive_schema.graphql_name == "FieldConstraints"
    assert directive_schema.locations == [Location.INPUT_FIELD_DEFINITION]
    assert directive_schema.repeatable is True
    assert directive_schema.origin is FieldConstraintsDirective
    assert directive.min_length == 1


def test_input_factory_field_without_constraints_does_not_have_constraints_directive() -> None:
    class Model(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(description="Name of the model")]

    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert len(definition.fields) == 1
    assert len(definition.fields[0].directives) == 0


def test_input_factory_field_constraints_directive_values() -> None:
    class Model(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(min_length=1, max_length=10, pattern=r"^\w+$")]
        age: typing.Annotated[int, pydantic.Field(gt=0, le=100, multiple_of=2)]
        cash: typing.Annotated[Decimal, pydantic.Field(max_digits=5, decimal_places=2, multiple_of=0.5, ge=0)]

    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert len(definition.fields) == 3
    name_directive: FieldConstraintsDirective = definition.fields[0].directives[0]
    assert name_directive.min_length == 1
    assert name_directive.max_length == 10
    assert name_directive.pattern == r"^\w+$"
    assert name_directive.gt is None
    assert name_directive.gte is None
    assert name_directive.lt is None
    assert name_directive.lte is None
    assert name_directive.max_digits is None
    assert name_directive.decimal_places is None
    assert name_directive.multiple_of is None

    age_directive: FieldConstraintsDirective = definition.fields[1].directives[0]
    assert age_directive.min_length is None
    assert age_directive.max_length is None
    assert age_directive.pattern is None
    assert age_directive.gt == 0
    assert age_directive.gte is None
    assert age_directive.lt is None
    assert age_directive.lte == 100
    assert age_directive.max_digits is None
    assert age_directive.decimal_places is None
    assert age_directive.multiple_of == 2

    cash_directive: FieldConstraintsDirective = definition.fields[2].directives[0]
    assert cash_directive.min_length is None
    assert cash_directive.max_length is None
    assert cash_directive.pattern is None
    assert cash_directive.gt is None
    assert cash_directive.gte == 0
    assert cash_directive.lt is None
    assert cash_directive.lte is None
    assert cash_directive.max_digits == 5
    assert cash_directive.decimal_places == 2
    assert cash_directive.multiple_of == 0.5


def _none_to_empty_str(v: typing.Any) -> str:
    if v is None:
        return ""
    return v

def test_input_factory_converts_empty_str_literal_union_to_optional() -> None:
    class Model(pydantic.BaseModel):
        website: pydantic.HttpUrl | typing.Literal[""] = ""
        website_annotated: typing.Annotated[
            pydantic.HttpUrl | typing.Literal[""],
            pydantic.Field(description="Website of the model")
        ] = ""

    gql_input_cls = InputFactory.make(Model)
    definition = gql_input_cls.__strawberry_definition__
    assert len(definition.fields) == 2

    # Check the graphql input field is marked as optional
    assert type(definition.fields[0].type_annotation.annotation) is StrawberryOptional
    assert type(definition.fields[1].type_annotation.annotation) is StrawberryOptional

    # check None value is converted to empty string
    gql_input = gql_input_cls(website=None, website_annotated=None)
    gql_input.clean()
    assert gql_input.clean_data.website == ""
    assert gql_input.clean_data.website_annotated == ""

    # check unset value is the default empty string
    gql_input = gql_input_cls()
    gql_input.clean()
    assert gql_input.clean_data.website == ""
    assert gql_input.clean_data.website_annotated == ""

    # check url value
    gql_input = gql_input_cls(website="https://example.com", website_annotated="https://example2.com")
    gql_input.clean()
    assert gql_input.clean_data.website == pydantic.HttpUrl("https://example.com")
    assert gql_input.clean_data.website_annotated == pydantic.HttpUrl("https://example2.com")


def test_input_factory_mark_string_with_default_as_optional() -> None:
    class Model(pydantic.BaseModel):
        name: str = ""
        name_annotated: typing.Annotated[str, pydantic.Field(description="Name of the model")] = ""
        name_no_default: str

    gql_input_cls = InputFactory.make(Model)
    definition = gql_input_cls.__strawberry_definition__
    assert len(definition.fields) == 3

    # Check the graphql input field is marked as optional
    assert type(definition.fields[0].type_annotation.annotation) is StrawberryOptional
    assert type(definition.fields[1].type_annotation.annotation) is StrawberryOptional
    assert definition.fields[2].type_annotation.annotation is str

    # check None value is converted to empty string
    gql_input = gql_input_cls(name=None, name_annotated=None, name_no_default="something")
    gql_input.clean()
    assert gql_input.clean_data.name == ""
    assert gql_input.clean_data.name_annotated == ""
    assert gql_input.clean_data.name_no_default == "something"

    # check unset value is the default empty string
    gql_input = gql_input_cls(name_no_default="something")
    gql_input.clean()
    assert gql_input.clean_data.name == ""
    assert gql_input.clean_data.name_annotated == ""
    assert gql_input.clean_data.name_no_default == "something"

    # check url value
    gql_input = gql_input_cls(name="John", name_annotated="Doe", name_no_default="something")
    gql_input.clean()
    assert gql_input.clean_data.name == "John"
    assert gql_input.clean_data.name_annotated == "Doe"
    assert gql_input.clean_data.name_no_default == "something"


def test_input_factory_make_with_hashed_id_field() -> None:
    class Model(pydantic.BaseModel):
        name: strawberry_vercajk.HashedID

    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert definition.fields[0].type_annotation.annotation is strawberry.ID


def test_input_factory_make_with_hashed_id_field_optional() -> None:
    class Model(pydantic.BaseModel):
        name: strawberry_vercajk.HashedID | None = None

    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert type(definition.fields[0].type_annotation.annotation) is StrawberryOptional
    assert definition.fields[0].type_annotation.annotation.of_type is strawberry.ID


def test_input_factory_make_with_hashed_id_field_annotated() -> None:
    class Model(pydantic.BaseModel):
        name: typing.Annotated[strawberry_vercajk.HashedID, pydantic.Field(description="Name of the model")]

    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert definition.fields[0].description == "Name of the model"
    assert definition.fields[0].type_annotation.annotation is strawberry.ID


def test_input_factory_make_with_hashed_id_field_annotated_optional() -> None:
    class Model(pydantic.BaseModel):
        name: typing.Annotated[strawberry_vercajk.HashedID | None, pydantic.Field(description="Name of the model")]

    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert definition.fields[0].description == "Name of the model"
    assert type(definition.fields[0].type_annotation.annotation) is StrawberryOptional
    assert definition.fields[0].type_annotation.annotation.of_type is strawberry.ID


def test_input_factory_make_with_hashed_id_field_list() -> None:
    class Model(pydantic.BaseModel):
        name: list[strawberry_vercajk.HashedID]

    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert type(definition.fields[0].type_annotation.annotation) is StrawberryList
    assert definition.fields[0].type_annotation.annotation.of_type is strawberry.ID


def test_input_factory_make_with_hashed_id_field_list_optional() -> None:
    class Model(pydantic.BaseModel):
        name: list[strawberry_vercajk.HashedID] | None = None

    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert type(definition.fields[0].type_annotation.annotation) is StrawberryOptional
    assert type(definition.fields[0].type_annotation.annotation.of_type) is StrawberryList
    assert definition.fields[0].type_annotation.annotation.of_type.of_type is strawberry.ID


def test_input_factory_make_with_hashed_id_field_list_optional_optional() -> None:
    class Model(pydantic.BaseModel):
        name: list[strawberry_vercajk.HashedID | None] | None = None

    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert type(definition.fields[0].type_annotation.annotation) is StrawberryOptional
    assert type(definition.fields[0].type_annotation.annotation.of_type) is StrawberryList
    assert type(definition.fields[0].type_annotation.annotation.of_type.of_type) is StrawberryOptional
    assert definition.fields[0].type_annotation.annotation.of_type.of_type.of_type is strawberry.ID


def test_input_factory_with_annotated_nested_validator_field_required() -> None:
    class NestedValidator(pydantic.BaseModel):
        something: str
        num: int

    def _something_cannot_be_pepa(v: NestedValidator) -> NestedValidator:
        if v.something == "pepa":
            raise pydantic.ValidationError("Something cannot be pepa")
        return v

    NotPepaValidatorField = typing.Annotated[
        NestedValidator,
        pydantic.AfterValidator(_something_cannot_be_pepa),
    ]

    class Model(pydantic.BaseModel):
        nested: NotPepaValidatorField

    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert len(definition.fields) == 1
    assert definition.fields[0].name == "nested"
    assert len(definition.fields[0].type_annotation.annotation.__strawberry_definition__.fields) == 2
    assert definition.fields[0].type_annotation.annotation.__strawberry_definition__.fields[0].name == "something"
    assert definition.fields[0].type_annotation.annotation.__strawberry_definition__.fields[1].name == "num"
    assert definition.fields[0].type_annotation.annotation.__strawberry_definition__.fields[0].type_annotation.annotation is str
    assert definition.fields[0].type_annotation.annotation.__strawberry_definition__.fields[1].type_annotation.annotation is int

def test_input_factory_with_annotated_nested_validator_field_not_required_with_default() -> None:
    class NestedValidator(pydantic.BaseModel):
        something: str
        num: int

    def _something_cannot_be_pepa(v: NestedValidator) -> NestedValidator:
        if v.something == "pepa":
            raise pydantic.ValidationError("Something cannot be pepa")
        return v

    NotPepaValidatorField = typing.Annotated[
        NestedValidator,
        pydantic.AfterValidator(_something_cannot_be_pepa),
    ]

    class Model(pydantic.BaseModel):
        nested: NotPepaValidatorField | None = None

    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert len(definition.fields) == 1
    # check that the nested validator was recognised and registered by the InputFactory
    assert NestedValidator in InputFactory._REGISTRY


def test_input_factory_with_annotated_nested_validator_field_with_another_annotation() -> None:
    class NestedValidator(pydantic.BaseModel):
        something: str
        num: int

    def _something_cannot_be_pepa(v: NestedValidator) -> NestedValidator:
        if v.something == "pepa":
            raise pydantic_core.PydanticCustomError(
                "something_cannot_be_pepa",
                "Something cannot be pepa",
            )
        return v

    NotPepaValidatorField = typing.Annotated[
        NestedValidator,
        pydantic.AfterValidator(_something_cannot_be_pepa),
    ]

    class Model(pydantic.BaseModel):
        nested: typing.Annotated[
            NotPepaValidatorField | None,
            pydantic.Field(description="Descr.", deprecated="Deprecation reason")
        ] = None

    gql_input = InputFactory.make(Model)
    definition = gql_input.__strawberry_definition__
    assert len(definition.fields) == 1
    # check that the nested validator was recognised and registered by the InputFactory
    assert NestedValidator in InputFactory._REGISTRY

    input_data = gql_input(nested={"something": "sth", "num": 1})
    errors = input_data.clean()
    assert not errors
    input_data = gql_input(nested={"something": "pepa", "num": 1})
    errors = input_data.clean()
    assert len(errors) == 1
    assert errors[0].code == "something_cannot_be_pepa"
    assert errors[0].location == ["nested",]


def _sdl_for_input(input_type: type) -> str:
    """Build a minimal schema exposing `input_type` and return its SDL."""

    @strawberry.type
    class Query:
        ok: bool = True

    @strawberry.type
    class Mutation:
        @strawberry.mutation
        def run(self, data: input_type) -> bool:  # noqa: ANN001
            return True

    return strawberry.Schema(query=Query, mutation=Mutation).as_str()


def _resolve_leaf(strawberry_type: typing.Any) -> typing.Any:  # noqa: ANN401
    """Unwrap StrawberryOptional/StrawberryList/LazyType down to the concrete input type."""
    while True:
        if isinstance(strawberry_type, (StrawberryOptional, StrawberryList)):
            strawberry_type = strawberry_type.of_type
        elif hasattr(strawberry_type, "resolve_type"):
            strawberry_type = strawberry_type.resolve_type()
        else:
            return strawberry_type


def test_input_factory_make_with_self_referential_list_field() -> None:
    """
    A model with a field typed as a list of itself produces a self-referential input type
    instead of crashing with a RecursionError.
    """
    class NodeModel(pydantic.BaseModel):
        name: str | None = None
        children: "list[NodeModel] | None" = None

    NodeModel.model_rebuild()

    gql_input = InputFactory.make(NodeModel)
    definition = gql_input.__strawberry_definition__
    assert definition.name == "NodeModel"
    fields = {f.name: f for f in definition.fields}
    assert set(fields) == {"name", "children"}
    # the `children` field resolves back to the very same input type
    assert _resolve_leaf(fields["children"].type) is gql_input

    sdl = _sdl_for_input(gql_input)
    assert "input NodeModel {" in sdl
    assert "children: [NodeModel!]" in sdl


def test_input_factory_make_with_self_referential_optional_field() -> None:
    """
    A model with a direct (non-list) optional self-reference produces a self-referential
    input type instead of crashing with a RecursionError.
    """
    class NodeModel(pydantic.BaseModel):
        name: str | None = None
        parent: "NodeModel | None" = None

    NodeModel.model_rebuild()

    gql_input = InputFactory.make(NodeModel)
    definition = gql_input.__strawberry_definition__
    fields = {f.name: f for f in definition.fields}
    assert set(fields) == {"name", "parent"}
    assert _resolve_leaf(fields["parent"].type) is gql_input

    sdl = _sdl_for_input(gql_input)
    assert "input NodeModel {" in sdl
    assert "parent: NodeModel" in sdl


def test_input_factory_make_with_mutual_recursion() -> None:
    """
    Two models that reference each other (A -> B -> A) produce mutually-referential input
    types instead of crashing with a RecursionError.
    """
    class AModel(pydantic.BaseModel):
        name: str | None = None
        children: "list[BModel] | None" = None

    class BModel(pydantic.BaseModel):
        name: str | None = None
        parents: "list[AModel] | None" = None

    AModel.model_rebuild()
    BModel.model_rebuild()

    a_input = InputFactory.make(AModel)
    b_input = InputFactory.make(BModel)
    assert AModel in InputFactory._REGISTRY
    assert BModel in InputFactory._REGISTRY

    a_fields = {f.name: f for f in a_input.__strawberry_definition__.fields}
    b_fields = {f.name: f for f in b_input.__strawberry_definition__.fields}
    assert _resolve_leaf(a_fields["children"].type) is b_input
    assert _resolve_leaf(b_fields["parents"].type) is a_input

    sdl = _sdl_for_input(a_input)
    assert "input AModel {" in sdl
    assert "input BModel {" in sdl
    assert "children: [BModel!]" in sdl
    assert "parents: [AModel!]" in sdl


def test_input_factory_self_referential_to_pydantic_roundtrip() -> None:
    """
    A self-referential input round-trips arbitrarily-nested values back into nested pydantic
    instances via `to_pydantic()`.
    """
    class NodeModel(pydantic.BaseModel):
        name: str | None = None
        children: "list[NodeModel] | None" = None

    NodeModel.model_rebuild()

    gql_input = InputFactory.make(NodeModel)
    input_data = gql_input(
        name="root",
        children=[
            gql_input(name="a", children=[gql_input(name="a1", children=None)]),
            gql_input(name="b", children=None),
        ],
    )
    errors = input_data.clean()
    assert errors == []
    clean_data = input_data.clean_data
    assert type(clean_data) is NodeModel
    assert type(clean_data.children[0]) is NodeModel
    assert type(clean_data.children[0].children[0]) is NodeModel
    assert clean_data.model_dump() == {
        "name": "root",
        "children": [
            {"name": "a", "children": [{"name": "a1", "children": None}]},
            {"name": "b", "children": None},
        ],
    }


def test_input_factory_self_referential_nested_validation_error() -> None:
    """
    An invalid value on a deeply-nested node of a self-referential input surfaces an error with the
    full nested location, proving the whole tree is validated at once (not just the root node).
    """
    class NodeModel(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(max_length=3)]
        children: "list[NodeModel] | None" = None

    NodeModel.model_rebuild()

    gql_input = InputFactory.make(NodeModel)
    input_data = gql_input(
        name="ok",
        children=[gql_input(name="way-too-long", children=None)],
    )
    errors = input_data.clean()
    assert len(errors) == 1
    assert errors[0].code == "string_too_long"
    assert errors[0].location == ["children", 0, "name"]


def test_input_factory_self_reference_via_validated_input() -> None:
    """
    The public `ValidatedInput[Model]` entry point (the one from the original bug report) builds a
    self-referential model without crashing, and the in-progress tracking set is left clean.
    """
    class NodeModel(pydantic.BaseModel):
        name: str | None = None
        children: "list[NodeModel] | None" = None

    NodeModel.model_rebuild()

    input_type = strawberry_vercajk.ValidatedInput[NodeModel]
    input_data = input_type(name="root", children=[input_type(name="leaf", children=None)])
    errors = input_data.clean()
    assert errors == []
    assert type(input_data.clean_data) is NodeModel
    assert input_data.clean_data.children[0].name == "leaf"
    # the build finished cleanly - nothing left marked as "in progress"
    assert NodeModel not in InputFactory._BUILDING


def test_input_factory_make_with_three_way_mutual_recursion() -> None:
    """
    A three-model cycle (A -> B -> C -> A) resolves every cross-reference instead of crashing with a
    RecursionError, proving the in-progress tracking handles cycles longer than a single hop.
    """
    class ANode(pydantic.BaseModel):
        child: "list[BNode] | None" = None

    class BNode(pydantic.BaseModel):
        child: "list[CNode] | None" = None

    class CNode(pydantic.BaseModel):
        back: "list[ANode] | None" = None

    ANode.model_rebuild()
    BNode.model_rebuild()
    CNode.model_rebuild()

    a_input = InputFactory.make(ANode)
    b_input = InputFactory.make(BNode)
    c_input = InputFactory.make(CNode)

    a_fields = {f.name: f for f in a_input.__strawberry_definition__.fields}
    b_fields = {f.name: f for f in b_input.__strawberry_definition__.fields}
    c_fields = {f.name: f for f in c_input.__strawberry_definition__.fields}
    assert _resolve_leaf(a_fields["child"].type) is b_input
    assert _resolve_leaf(b_fields["child"].type) is c_input
    assert _resolve_leaf(c_fields["back"].type) is a_input

    sdl = _sdl_for_input(a_input)
    assert "input ANode {" in sdl
    assert "input BNode {" in sdl
    assert "input CNode {" in sdl


def test_input_factory_make_with_typing_self_field() -> None:
    """
    A model that expresses its self-reference with `typing.Self` builds a working self-referential
    input type and round-trips nested values.

    Unlike a string forward-ref (`"list[NodeModel]"`), pydantic keeps the annotation as the `Self`
    special form rather than substituting the model class, so this never enters the
    `_BUILDING`/`_SelfReferenceLazyType` path - strawberry's native `strawberry.auto` resolution
    handles it. This test locks in that the `typing.Self` spelling keeps working.
    """
    class NodeModel(pydantic.BaseModel):
        name: str | None = None
        children: "list[typing.Self] | None" = None

    NodeModel.model_rebuild()

    gql_input = InputFactory.make(NodeModel)
    definition = gql_input.__strawberry_definition__
    assert definition.name == "NodeModel"
    fields = {f.name: f for f in definition.fields}
    assert set(fields) == {"name", "children"}
    # the `children` field resolves back to the very same input type
    assert _resolve_leaf(fields["children"].type) is gql_input

    sdl = _sdl_for_input(gql_input)
    assert "input NodeModel {" in sdl
    assert "children: [NodeModel!]" in sdl

    # nested values round-trip back into nested pydantic instances
    input_data = gql_input(
        name="root",
        children=[gql_input(name="leaf", children=None)],
    )
    errors = input_data.clean()
    assert errors == []
    clean_data = input_data.clean_data
    assert type(clean_data) is NodeModel
    assert type(clean_data.children[0]) is NodeModel
    assert clean_data.model_dump() == {
        "name": "root",
        "children": [{"name": "leaf", "children": None}],
    }
