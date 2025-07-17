import typing

import pydantic
import strawberry
import strawberry_vercajk


class CompanyInputValidator(strawberry_vercajk.InputValidator):
    name: typing.Annotated[str, pydantic.Field(min_length=5, max_length=50, pattern=r"^[A-Z].*")]


class AddressInputValidator(strawberry_vercajk.InputValidator):
    street: typing.Annotated[str, pydantic.Field(min_length=5, max_length=100)]
    city: typing.Annotated[str, pydantic.Field(min_length=5, max_length=10)]
    postal_code: typing.Annotated[str, pydantic.Field(min_length=5, max_length=10)]


class UserCreateInputValidator(strawberry_vercajk.InputValidator):
    name: typing.Annotated[str, pydantic.Field(min_length=5, max_length=100, pattern=r"^[A-Z].*")]
    company: CompanyInputValidator
    addresses: typing.Annotated[list[AddressInputValidator], pydantic.Field(min_length=1)]
    age: typing.Annotated[int, pydantic.Field(ge=0, le=150)]


@strawberry.type(name="Company")
class CompanyType:
    name: str


@strawberry.type(name="Address")
class AddressType:
    street: str
    city: str
    postal_code: str


@strawberry.type(name="User")
class UserType:
    name: str
    company: CompanyType
    addresses: list[AddressType]
    age: int


@strawberry.type
class Query:
    @strawberry.field()
    def hello(self) -> str:
        return "Hello, world!"


@strawberry.type
class Mutation:
    @strawberry.mutation(
        extensions=[],
    )
    def user_create(
            self,
            inp: typing.Annotated[
                strawberry_vercajk.pydantic_to_input_type(UserCreateInputValidator),
                strawberry.argument(name="input"),
            ],
    ) -> typing.Annotated[
        strawberry_vercajk.MutationErrorType | UserType,
        strawberry.union(name="UserCreateResponse"),
    ]:
        errors = inp.clean()
        if errors:
            return strawberry_vercajk.MutationErrorType(errors=errors)
        clean_data = inp.clean_data

        # For illustration purposes only, you may instead want to save the user to the database, etc.
        return UserType(
            name=clean_data.name,
            company=CompanyType(name=clean_data.company.name),
            addresses=[
                AddressType(
                    street=address.street,
                    city=address.city,
                    postal_code=address.postal_code,
                )
                for address in clean_data.addresses
            ],
            age=clean_data.age,
        )


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    types=[
        strawberry_vercajk.MutationErrorInterface,
        strawberry_vercajk.ErrorType,
    ]
)


USER_CREATE_MUTATION = """
mutation userCreate($input: UserCreateInput!) {
    userCreate(input: $input) {
        ... on User {
            __typename
            name
            age
            company {
                name
            }
            addresses {
                street
                city
                postalCode
            }
        }
        ... on MutationError {
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


def test_user_create_mutation_valid() -> None:
    result = schema.execute_sync(
        USER_CREATE_MUTATION,
        variable_values={
            "input": {
                "name": "John Doe",
                "company": {
                    "name": "ACME Inc.",
                },
                "addresses": [
                    {
                        "street": "Main street",
                        "city": "Prahaha",
                        "postalCode": "12345",
                    },
                ],
                "age": 42,
            },
        },
    )

    assert not result.errors
    assert result.data == {
        "userCreate": {
            "__typename": "User",
            "name": "John Doe",
            "age": 42,
            "company": {
                "name": "ACME Inc.",
            },
            "addresses": [
                {
                    "street": "Main street",
                    "city": "Prahaha",
                    "postalCode": "12345",
                },
            ],
        },
    }


def test_user_create_mutation_invalid_user_name() -> None:
    result = schema.execute_sync(
        USER_CREATE_MUTATION,
        variable_values={
            "input": {
                "name": "ABC",
                "company": {
                    "name": "ACME Inc.",
                },
                "addresses": [
                    {
                        "street": "Main street",
                        "city": "Prahaha",
                        "postalCode": "12345",
                    },
                ],
                "age": 42,
            },
        },
    )

    assert not result.errors
    assert result.data == {
        "userCreate": {
            "__typename": "MutationError",
            "errors": [
                {
                    "location": ["name"],
                    "code": "string_too_short",
                    "message": "String should have at least 5 characters",
                    "constraints": [
                        {
                            "code": "MIN_LENGTH",
                            "value": "5",
                            "dataType": "INTEGER",
                        },
                    ],
                },
            ],
        },
    }



def test_user_create_mutation_invalid_address_city() -> None:
    result = schema.execute_sync(
        USER_CREATE_MUTATION,
        variable_values={
            "input": {
                "name": "John Doe",
                "company": {
                    "name": "ACME Inc.",
                },
                "addresses": [
                    {
                        "street": "Main street",
                        "city": "ABC",
                        "postalCode": "12345",
                    },
                ],
                "age": 42,
            },
        },
    )

    assert not result.errors
    assert result.data == {
        "userCreate": {
            "__typename": "MutationError",
            "errors": [
                {
                    "location": ["addresses", 0, "city"],
                    "code": "string_too_short",
                    "message": "String should have at least 5 characters",
                    "constraints": [
                        {
                            "code": "MIN_LENGTH",
                            "value": "5",
                            "dataType": "INTEGER",
                        },
                    ],
                },
            ],
        },
    }
