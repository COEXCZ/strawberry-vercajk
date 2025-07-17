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
    assert len(definition.fields[0].type_annotation.annotation._type_definition.fields) == 2
    assert definition.fields[0].type_annotation.annotation._type_definition.fields[0].name == "something"
    assert definition.fields[0].type_annotation.annotation._type_definition.fields[1].name == "num"
    assert definition.fields[0].type_annotation.annotation._type_definition.fields[0].type_annotation.annotation is str
    assert definition.fields[0].type_annotation.annotation._type_definition.fields[1].type_annotation.annotation is int

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
