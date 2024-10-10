
from datetime import date, datetime
import enum
import typing

import pydantic
import pydantic_core
import strawberry
import strawberry.extensions

import strawberry_vercajk


@strawberry.type
class OkResponse:
    ok: bool = True


@strawberry.type(name="UsernameTakenError")
class UsernameTakenErrorType(strawberry_vercajk.ErrorInterface):
    code: str = "username_taken"
    message: str = "Username is already taken."
    suggested_username: str


@strawberry.type(name="UserCreateError")
class UserCreateErrorType(strawberry_vercajk.MutationErrorInterface):
    errors: list[
        typing.Annotated[
            strawberry_vercajk.ErrorType
            | UsernameTakenErrorType,
            strawberry.union(
                name="UserCreateErrors",
            ),
        ]
    ]


class PayloadData(typing.TypedDict):
    fieldNoValidator: int
    fieldWithCustomValidator: str
    enumField: str
    enumFieldOptional: typing.NotRequired[str | None]
    enumFieldList: list[str]
    dateField: str
    dateTimeField: str
    nestedField: dict
    nestedFieldList: list[dict]


class SomeEnum(enum.Enum):
    VALUE1 = "VALUE1"
    VALUE2 = "VALUE2"


@strawberry.type
class Query:
    @strawberry.field()
    def test_query(self) -> str:  # not used, but the schema needs at least one query
        return "test"


def not_a_word_validator(value: str) -> str:
    if value == "word":
        raise pydantic.ValidationError.from_exception_data(
            "Field validation error",
            line_errors=[
                {
                    "type": pydantic_core.PydanticCustomError(
                        "invalid_value",
                        "Value cannot be 'word'",
                        {},
                    ),
                    "input": value,
                },
            ]
        )
    return value


class NestedInputValidator(strawberry_vercajk.InputValidator):
    field: typing.Annotated[str, pydantic.Field(max_length=5)]


class MutationInputValidator(strawberry_vercajk.InputValidator):
    field_no_validator: int | None = None
    field_with_custom_validator: typing.Annotated[
        str | None,
        pydantic.AfterValidator(not_a_word_validator),
    ] = None
    enum_field: SomeEnum
    enum_field_optional: SomeEnum | None = None
    enum_field_list: list[SomeEnum] = []
    date_field: date
    date_time_field: datetime
    nested_field: NestedInputValidator
    nested_field_list: list[NestedInputValidator]

    @pydantic.field_validator("date_field")
    def date_field_validator(cls, value: date) -> date:
        if value.year < 2000:
            raise pydantic.ValidationError.from_exception_data(
                "Field validation error",
                line_errors=[
                    {
                        "type": pydantic_core.PydanticCustomError(
                            "date_must_be_after_2000",
                            "Date must be after 2000",
                            {},
                        ),
                        "input": value,
                    },
                ]
            )
        return value

    @pydantic.model_validator(mode="after")
    def after_validate(self) -> typing.Self:
        if self.field_no_validator == -1 and self.field_with_custom_validator == "disallowed_combination":
            raise pydantic.ValidationError.from_exception_data(
                "Model validation error",
                line_errors=[
                    {
                        "type": pydantic_core.PydanticCustomError(
                            "disallowed_combination",
                            "Combination of field_no_validator and field_with_custom_validator is not allowed",
                            {},
                        ),
                        "input": {
                            "field_no_validator": self.field_no_validator,
                            "field_with_custom_validator": self.field_with_custom_validator,
                        },
                    },
                ]
            )
        return self


class UserCreateInputValidator(strawberry_vercajk.InputValidator):
    username: typing.Annotated[str, pydantic.Field(max_length=20)]


@strawberry.type
class Mutation:
    @strawberry.mutation
    def test_mutation(
            self,
            input: strawberry_vercajk.pydantic_to_input_type(MutationInputValidator),
    ) -> typing.Annotated[
        strawberry_vercajk.MutationErrorType | OkResponse,
        strawberry.union(name="TestMutationResponse")
    ]:
        errors = input.clean()
        if errors:
            return strawberry_vercajk.MutationErrorType(errors=errors)
        return OkResponse(ok=True)

    @strawberry.mutation
    def user_create(
            self,
            input: strawberry_vercajk.pydantic_to_input_type(UserCreateInputValidator),
    ) -> typing.Annotated[
        UserCreateErrorType | OkResponse,
        strawberry.union(name="UserCreateResponse"),
    ]:
        errors = input.clean()
        if not errors and input.clean_data.username == "TAKEN":
            errors.append(
                UsernameTakenErrorType(
                    location=["username"],
                    suggested_username=f"other-{input.clean_data.username}",
                ),
            )
        if errors:
            return UserCreateErrorType(errors=errors)
        return OkResponse(ok=True)



test_schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    types={
        strawberry_vercajk.ErrorType,
    }
)


TEST_MUTATION: str = """
    mutation testMutation($input: MutationInput!) {
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
                    constraints {
                        code
                        value
                        dataType
                    }
                }
            }
        }
    }
"""

USER_CREATE_MUTATION: str = """
    mutation userCreate($input: UserCreateInput!) {
        userCreate(input: $input) {
            ... on OkResponse {
                __typename
                ok
            }
            ... on UserCreateError {
                __typename
                errors {
                    ... on ErrorInterface {
                        location
                        code
                        message
                        constraints {
                            code
                            value
                            dataType
                        }
                    }
                }
            }
        }
    }
"""


USER_CREATE_MUTATION_WITH_EXTRA_ERROR: str = """
    mutation userCreate($input: UserCreateInput!) {
        userCreate(input: $input) {
            ... on OkResponse {
                __typename
                ok
            }
            ... on UserCreateError {
                __typename
                errors {
                    ... on UsernameTakenError {  # <-- EXTRA
                        suggestedUsername
                    }
                    ... on ErrorInterface {
                        location
                        code
                        message
                        constraints {
                            code
                            value
                            dataType
                        }
                    }
                }
            }
        }
    }
"""

def get_valid_input() -> PayloadData:
    return  {
        "fieldNoValidator": 1,
        "fieldWithCustomValidator": "not_a_word",
        "enumField": SomeEnum.VALUE1.name,
        "enumFieldOptional": None,
        "enumFieldList": [SomeEnum.VALUE2.name],
        "dateField": "2021-01-01",
        "dateTimeField": "2021-01-01T00:00:00",
        "nestedField": {
            "field": "ABCD",
        },
        "nestedFieldList": [
            {
                "field": "ABCD1",
            },
            {
                "field": "ABCD2",
            },
        ],
    }


def test_valid_input() -> None:
    resp = test_schema.execute_sync(
        query=TEST_MUTATION,
        variable_values={
            "input": get_valid_input(),
        },
    )
    assert resp.data["testMutation"]["__typename"] is "OkResponse"
    assert resp.data["testMutation"]["ok"] is True


def test_invalid_field_method_custom_validator() -> None:
    resp = test_schema.execute_sync(
        query=TEST_MUTATION,
        variable_values={
            "input": {
                **get_valid_input(),
                "dateField": "1999-01-01",
            },
        },
    )
    assert resp.data["testMutation"]["__typename"] is "MutationError"
    assert len(resp.data["testMutation"]["errors"]) == 1
    assert resp.data["testMutation"]["errors"][0]["code"] == "date_must_be_after_2000"
    assert resp.data["testMutation"]["errors"][0]["message"] == "Date must be after 2000"
    assert resp.data["testMutation"]["errors"][0]["location"] == ["dateField"]
    assert resp.data["testMutation"]["errors"][0]["constraints"] == []


def test_invalid_model_validator() -> None:
    input_data = get_valid_input()
    input_data["fieldNoValidator"] = -1
    input_data["fieldWithCustomValidator"] = "disallowed_combination"
    resp = test_schema.execute_sync(
        query=TEST_MUTATION,
        variable_values={
            "input": input_data,
        },
    )
    assert resp.data["testMutation"]["__typename"] is "MutationError"
    assert len(resp.data["testMutation"]["errors"]) == 1
    assert resp.data["testMutation"]["errors"][0]["code"] == "disallowed_combination"
    assert resp.data["testMutation"]["errors"][0]["message"] == "Combination of field_no_validator and field_with_custom_validator is not allowed"
    assert resp.data["testMutation"]["errors"][0]["location"] == []
    assert resp.data["testMutation"]["errors"][0]["constraints"] == []


def test_field_with_custom_validator_in_annotation_invalid() -> None:
    input_data = get_valid_input()
    input_data["fieldWithCustomValidator"] = "word"
    resp = test_schema.execute_sync(
        query=TEST_MUTATION,
        variable_values={
            "input": input_data,
        },
    )
    assert resp.data["testMutation"]["__typename"] is "MutationError"
    assert len(resp.data["testMutation"]["errors"]) == 1
    assert resp.data["testMutation"]["errors"][0]["code"] == "invalid_value"
    assert resp.data["testMutation"]["errors"][0]["message"] == "Value cannot be 'word'"
    assert resp.data["testMutation"]["errors"][0]["location"] == ["fieldWithCustomValidator"]
    assert resp.data["testMutation"]["errors"][0]["constraints"] == []


def test_nested_validator_field_invalid() -> None:
    input_data = get_valid_input()
    input_data["nestedField"]["field"] = "ABCDEF"
    resp = test_schema.execute_sync(
        query=TEST_MUTATION,
        variable_values={
            "input": input_data,
        },
    )
    assert resp.data["testMutation"]["__typename"] is "MutationError"
    assert len(resp.data["testMutation"]["errors"]) == 1
    assert resp.data["testMutation"]["errors"][0]["code"] == "string_too_long"
    assert resp.data["testMutation"]["errors"][0]["message"] == "String should have at most 5 characters"
    assert resp.data["testMutation"]["errors"][0]["location"] == ["nestedField", "field"]
    assert resp.data["testMutation"]["errors"][0]["constraints"] == [{"code": "MAX_LENGTH", "value": 5, "dataType": "INTEGER"}]


def test_nested_validator_list_field_invalid() -> None:
    input_data = get_valid_input()
    input_data["nestedFieldList"][1]["field"] = "ABCDEF"
    resp = test_schema.execute_sync(
        query=TEST_MUTATION,
        variable_values={
            "input": input_data,
        },
    )
    assert resp.data["testMutation"]["__typename"] is "MutationError"
    assert len(resp.data["testMutation"]["errors"]) == 1
    assert resp.data["testMutation"]["errors"][0]["code"] == "string_too_long"
    assert resp.data["testMutation"]["errors"][0]["message"] == "String should have at most 5 characters"
    assert resp.data["testMutation"]["errors"][0]["location"] == ["nestedFieldList", 1, "field"]
    assert resp.data["testMutation"]["errors"][0]["constraints"] == [{"code": "MAX_LENGTH", "value": 5, "dataType": "INTEGER"}]


def test_multiple_nested_fields_invalid() -> None:
    input_data = get_valid_input()
    input_data["nestedField"]["field"] = "ABCDEF"
    input_data["nestedFieldList"][1]["field"] = "ABCDEF"
    resp = test_schema.execute_sync(
        query=TEST_MUTATION,
        variable_values={
            "input": input_data,
        },
    )
    assert resp.data["testMutation"]["__typename"] is "MutationError"
    assert len(resp.data["testMutation"]["errors"]) == 2
    assert resp.data["testMutation"]["errors"][0]["code"] == "string_too_long"
    assert resp.data["testMutation"]["errors"][0]["message"] == "String should have at most 5 characters"
    assert resp.data["testMutation"]["errors"][0]["location"] == ["nestedField", "field"]
    assert resp.data["testMutation"]["errors"][0]["constraints"] == [{"code": "MAX_LENGTH", "value": 5, "dataType": "INTEGER"}]
    assert resp.data["testMutation"]["errors"][1]["code"] == "string_too_long"
    assert resp.data["testMutation"]["errors"][1]["message"] == "String should have at most 5 characters"
    assert resp.data["testMutation"]["errors"][1]["location"] == ["nestedFieldList", 1, "field"]
    assert resp.data["testMutation"]["errors"][1]["constraints"] == [{"code": "MAX_LENGTH", "value": 5, "dataType": "INTEGER"}]


def test_user_create_ok() -> None:
    resp = test_schema.execute_sync(
        query=USER_CREATE_MUTATION,
        variable_values={
            "input": {
                "username": "not_taken",
            },
        },
    )
    assert resp.data["userCreate"]["__typename"] is "OkResponse"
    assert resp.data["userCreate"]["ok"] is True


def test_user_create_taken() -> None:
    resp = test_schema.execute_sync(
        query=USER_CREATE_MUTATION,
        variable_values={
            "input": {
                "username": "TAKEN",
            },
        },
    )
    assert resp.data["userCreate"]["__typename"] is "UserCreateError"
    assert len(resp.data["userCreate"]["errors"]) == 1
    assert resp.data["userCreate"]["errors"][0]["code"] == "username_taken"
    assert resp.data["userCreate"]["errors"][0]["message"] == "Username is already taken."
    assert resp.data["userCreate"]["errors"][0]["location"] == ["username"]
    assert resp.data["userCreate"]["errors"][0]["constraints"] == []


def test_user_create_taken_with_extra_error() -> None:
    resp = test_schema.execute_sync(
        query=USER_CREATE_MUTATION_WITH_EXTRA_ERROR,
        variable_values={
            "input": {
                "username": "TAKEN",
            },
        },
    )
    assert resp.data["userCreate"]["__typename"] is "UserCreateError"
    assert len(resp.data["userCreate"]["errors"]) == 1
    assert resp.data["userCreate"]["errors"][0]["code"] == "username_taken"
    assert resp.data["userCreate"]["errors"][0]["message"] == "Username is already taken."
    assert resp.data["userCreate"]["errors"][0]["location"] == ["username"]
    assert resp.data["userCreate"]["errors"][0]["suggestedUsername"] == "other-TAKEN"
    assert resp.data["userCreate"]["errors"][0]["constraints"] == []


def test_user_create_invalid() -> None:
    resp = test_schema.execute_sync(
        query=USER_CREATE_MUTATION,
        variable_values={
            "input": {
                "username": "TOO_LONG_USERNAME_TOO_LONG_USERNAME",
            },
        },
    )
    assert resp.data["userCreate"]["__typename"] is "UserCreateError"
    assert len(resp.data["userCreate"]["errors"]) == 1
    assert resp.data["userCreate"]["errors"][0]["code"] == "string_too_long"
    assert resp.data["userCreate"]["errors"][0]["message"] == "String should have at most 20 characters"
    assert resp.data["userCreate"]["errors"][0]["location"] == ["username"]
    assert resp.data["userCreate"]["errors"][0]["constraints"] == [{"code": "MAX_LENGTH", "value": 20, "dataType": "INTEGER"}]
