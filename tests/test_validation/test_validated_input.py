import typing

import pydantic
import pytest

import strawberry_vercajk


def test_validated_input() -> None:
    class Model(pydantic.BaseModel):
        name: str
        age: int

    input_type = strawberry_vercajk.pydantic_to_input_type(Model)

    input_data = input_type(name="John", age=20)
    errors = input_data.clean()
    assert errors == []
    assert type(input_data.clean_data) is Model
    assert input_data.clean_data.model_dump() == {"name": "John", "age": 20}


def test_validated_input_with_constraints_ok() -> None:
    class Model(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(max_length=10)]
        age: int

    input_type = strawberry_vercajk.pydantic_to_input_type(Model)

    input_data = input_type(name="John", age=20)
    errors = input_data.clean()
    assert errors == []
    assert type(input_data.clean_data) is Model
    assert input_data.clean_data.model_dump() == {"name": "John", "age": 20}


def test_validated_input_with_constraints_error() -> None:
    class Model(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(max_length=2)]
        age: typing.Annotated[int, pydantic.Field(lt=10)]

    input_type = strawberry_vercajk.pydantic_to_input_type(Model)

    input_data = input_type(name="John Doe", age=20)
    errors = input_data.clean()
    assert len(errors) == 2
    assert type(errors[0]) is strawberry_vercajk.ErrorType
    assert type(errors[1]) is strawberry_vercajk.ErrorType
    assert errors[0].code == "string_too_long"
    assert errors[0].message == "String should have at most 2 characters"
    assert errors[0].location == ["name"]
    assert errors[0].constraints == [
        strawberry_vercajk.ErrorConstraintType(
            code=strawberry_vercajk.ErrorConstraintChoices.MAX_LENGTH,
            value="2",
            data_type=strawberry_vercajk.ConstraintDataType.INTEGER,
        )
    ]
    assert errors[1].code == "less_than"
    assert errors[1].message == "Input should be less than 10"
    assert errors[1].location == ["age"]
    assert errors[1].constraints == [
        strawberry_vercajk.ErrorConstraintType(
            code=strawberry_vercajk.ErrorConstraintChoices.LT,
            value="10",
            data_type=strawberry_vercajk.ConstraintDataType.INTEGER,
        )
    ]

    with pytest.raises(ValueError) as err:
        assert input_data.clean_data
    assert str(err.value) == "The data did not pass the validation."


def test_validated_input_with_nested_ok() -> None:
    class NestedModel(pydantic.BaseModel):
        name: str

    class Model(pydantic.BaseModel):
        nested: NestedModel

    input_type = strawberry_vercajk.pydantic_to_input_type(Model)

    input_data = input_type(nested={"name": "John"})
    errors = input_data.clean()
    assert errors == []
    assert type(input_data.clean_data) is Model
    assert type(input_data.clean_data.nested) is NestedModel
    assert input_data.clean_data.model_dump() == {"nested": {"name": "John"}}


def test_validated_input_with_nested_error() -> None:
    class NestedModel(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(max_length=2)]

    class Model(pydantic.BaseModel):
        nested: NestedModel

    input_type = strawberry_vercajk.pydantic_to_input_type(Model)

    input_data = input_type(nested={"name": "John Doe"})
    errors = input_data.clean()
    assert len(errors) == 1
    assert type(errors[0]) is strawberry_vercajk.ErrorType
    assert errors[0].code == "string_too_long"
    assert errors[0].message == "String should have at most 2 characters"
    assert errors[0].location == ["nested", "name"]
    assert errors[0].constraints == [
        strawberry_vercajk.ErrorConstraintType(
            code=strawberry_vercajk.ErrorConstraintChoices.MAX_LENGTH,
            value="2",
            data_type=strawberry_vercajk.ConstraintDataType.INTEGER,
        )
    ]

    with pytest.raises(ValueError) as err:
        assert input_data.clean_data
    assert str(err.value) == "The data did not pass the validation."


def test_validated_input_with_list_ok() -> None:
    class Model(pydantic.BaseModel):
        names: list[str]

    input_type = strawberry_vercajk.pydantic_to_input_type(Model)

    input_data = input_type(names=["John", "Doe"])
    errors = input_data.clean()
    assert errors == []
    assert type(input_data.clean_data) is Model
    assert input_data.clean_data.model_dump() == {"names": ["John", "Doe"]}


def test_validated_input_with_list_error() -> None:
    class Model(pydantic.BaseModel):
        names: typing.Annotated[list[str], pydantic.Field(min_length=2)]

    input_type = strawberry_vercajk.pydantic_to_input_type(Model)

    input_data = input_type(names=["John"])
    errors = input_data.clean()
    assert len(errors) == 1
    assert type(errors[0]) is strawberry_vercajk.ErrorType
    assert errors[0].code == "too_short"
    assert errors[0].message == "List should have at least 2 items after validation, not 1"
    assert errors[0].location == ["names"]
    assert errors[0].constraints == [
        strawberry_vercajk.ErrorConstraintType(
            code=strawberry_vercajk.ErrorConstraintChoices.MIN_LENGTH,
            value="2",
            data_type=strawberry_vercajk.ConstraintDataType.INTEGER,
        )
    ]

    with pytest.raises(ValueError) as err:
        assert input_data.clean_data
    assert str(err.value) == "The data did not pass the validation."


def test_multiple_nested_inputs_with_errors() -> None:
    class NestedModel(pydantic.BaseModel):
        name: typing.Annotated[str, pydantic.Field(max_length=2)]

    class NestedModel2(pydantic.BaseModel):
        age: typing.Annotated[int, pydantic.Field(lt=10)]

    class Model(pydantic.BaseModel):
        nested: NestedModel
        nested2: NestedModel2

    input_type = strawberry_vercajk.pydantic_to_input_type(Model)
    input_data = input_type(nested={"name": "John Doe"}, nested2={"age": 20})
    errors = input_data.clean()
    assert len(errors) == 2
    assert type(errors[0]) is strawberry_vercajk.ErrorType
    assert errors[0].code == "string_too_long"
    assert errors[0].message == "String should have at most 2 characters"
    assert errors[0].location == ["nested", "name"]
    assert errors[0].constraints == [
        strawberry_vercajk.ErrorConstraintType(
            code=strawberry_vercajk.ErrorConstraintChoices.MAX_LENGTH,
            value="2",
            data_type=strawberry_vercajk.ConstraintDataType.INTEGER,
        )
    ]
    assert type(errors[1]) is strawberry_vercajk.ErrorType
    assert errors[1].code == "less_than"
    assert errors[1].message == "Input should be less than 10"
    assert errors[1].location == ["nested2", "age"]
    assert errors[1].constraints == [
        strawberry_vercajk.ErrorConstraintType(
            code=strawberry_vercajk.ErrorConstraintChoices.LT,
            value="10",
            data_type=strawberry_vercajk.ConstraintDataType.INTEGER,
        )
    ]


def test_specific_validator_stripped_from_error_location() -> None:
    """
    A special case, when the pydantic field is a union of types which have more validators,
    the last location element is the validator in which the error occurred.
    For example, if we have a field
      email: pydantic.EmailStr | typing.Literal[""]
    and we pass in a value "some_invalid_email", pydantic will throw two errors with these locations:
      - ("email", "literal['']")
      - ("email", "function-after[Validate(), str]")
    We don't want to include the last part of the location in the error message.
    From my observation, the last part always seems to include "[" character, which can
    never be in the field name - using this to determine if we should skip the last part.
    """
    class Model(pydantic.BaseModel):
        url: pydantic.HttpUrl | typing.Literal[""] = ""

    input_type = strawberry_vercajk.pydantic_to_input_type(Model)

    input_data = input_type(url="some_invalid_url")
    errors = input_data.clean()
    assert len(errors) == 1  # only the first error should be kept, other are discarded as would only be confusing
    assert errors[0].location == ["url"]
    assert errors[0].code == "url_parsing"
    assert input_data.original_error.error_count() == 2  # both errors are still in the original error
    assert {error["type"] for error in input_data.original_error.errors()} == {"url_parsing", "literal_error"}


def test_hashed_id_annotated_field_invalid_value() -> None:
    class Model(pydantic.BaseModel):
        some_id: strawberry_vercajk.HashedID

    input_type = strawberry_vercajk.pydantic_to_input_type(Model)
    input_data = input_type(some_id="prefix_abc123def456ghi7")
    errors = input_data.clean()
    assert len(errors) == 1
    assert isinstance(input_data.original_error, pydantic.ValidationError)
    assert errors[0].location == ["someId"]
    assert errors[0].code == "invalid_id"
    assert errors[0].message == "Invalid ID prefix_abc123def456ghi7."
    assert input_data.original_error.error_count() == 1
    assert input_data.original_error.errors()[0]["loc"] == ("some_id",)
    assert input_data.original_error.errors()[0]["msg"] == "Invalid ID prefix_abc123def456ghi7."
    assert input_data.original_error.errors()[0]["type"] == "invalid_id"


def test_hashed_id_annotated_field_valid_value() -> None:
    prefix: typing.LiteralString = "prefix"
    @strawberry_vercajk.hash_id_register(prefix)
    class HashedIDRegisteredModel(pydantic.BaseModel):
        pass

    class Model(pydantic.BaseModel):
        some_id: strawberry_vercajk.HashedID
        some_id_list: list[strawberry_vercajk.HashedID]
        some_id_optional: strawberry_vercajk.HashedID | None
        some_id_annotated: typing.Annotated[strawberry_vercajk.HashedID, pydantic.Field(description="Some ID")]

    input_type = strawberry_vercajk.pydantic_to_input_type(Model)
    input_data = input_type(
        some_id=f"{prefix}_abc123def456ghi7",
        some_id_list=[f"{prefix}_abc123def456ghi7", f"{prefix}_abc123def456ghi7"],
        some_id_optional=None,
        some_id_annotated=f"{prefix}_abc123def456ghi7",
    )
    errors = input_data.clean()
    assert len(errors) == 0
    assert input_data.original_error is None
    assert isinstance(input_data.clean_data.some_id, strawberry_vercajk.HashedID)
    assert len(input_data.clean_data.some_id_list) == 2
    assert isinstance(input_data.clean_data.some_id_list[0], strawberry_vercajk.HashedID)
    assert input_data.clean_data.some_id_optional is None
    assert isinstance(input_data.clean_data.some_id_annotated, strawberry_vercajk.HashedID)


def test_validator_via_class_getitem() -> None:
    class Model(pydantic.BaseModel):
        a: int
        b: int

    input_type = strawberry_vercajk.ValidatedInput[Model]
    input_data = input_type(a=1, b=2)
    errors = input_data.clean()
    assert len(errors) == 0
    assert input_data.original_error is None
    assert type(input_data.clean_data) is Model
    assert input_data.clean_data.a == 1
    assert input_data.clean_data.b == 2


def test_set_gql_params_gql_name() -> None:
    @strawberry_vercajk.set_gql_params(name="SomeName")
    class Model(pydantic.BaseModel):
        a: int
        b: int

    input_type = strawberry_vercajk.ValidatedInput[Model]
    assert input_type.__strawberry_definition__.name == "SomeName"
