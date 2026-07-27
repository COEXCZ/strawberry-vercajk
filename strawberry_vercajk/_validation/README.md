from tests.test_validation.test_readme_examples import UserCreateInputValidatorfrom email.headerregistry import Address

# (Input) Validation
This module provides 
- a way to validate input data in Strawberry
- communicate the validation rules to FE via schema directives
- unified interface for error response types

## Validate input data
Pydantic models are used to validate the input data.

For example, given the following Pydantic models (`strawberry_vercajk.InputValidator` is a thin wrapper on top of pydantic.BaseModel):
```python
import typing
import pydantic
import strawberry_vercajk


@strawberry_vercajk.set_gql_params(name="CompanyInput")
class CompanyInputValidator(strawberry_vercajk.InputValidator):
    name: typing.Annotated[str, pydantic.Field(min_length=5, max_length=50, pattern=r"^[A-Z].*")]


@strawberry_vercajk.set_gql_params(name="AddressInput")
class AddressInputValidator(strawberry_vercajk.InputValidator):
    street: typing.Annotated[str, pydantic.Field(min_length=5, max_length=100)]
    city: typing.Annotated[str, pydantic.Field(min_length=5, max_length=10)]
    postal_code: typing.Annotated[str, pydantic.Field(min_length=5, max_length=10)]


@strawberry_vercajk.set_gql_params(name="UserCreateInput")
class UserCreateInputValidator(strawberry_vercajk.InputValidator):
    name: typing.Annotated[str, pydantic.Field(min_length=5, max_length=100, pattern=r"^[A-Z].*")]
    company: CompanyInputValidator
    addresses: typing.Annotated[list[AddressInputValidator], pydantic.Field(min_length=1)]
    age: typing.Annotated[int, pydantic.Field(ge=0, le=150)]
```

>[!TIP]
> You can use [pydbull](https://github.com/COEXCZ/pydbull) library for converting data objects (such as Django models) 
> to Pydantic models or adding validation rules based on model constraints.

>[!TIP]
> Fields annotated as a union with `typing.Literal[""]` are marked as optional in the generated Strawberry input type.
> The null values are automatically converted to an empty string.

>[!WARNING]
> For fields with union type, only the errors from the first type is returned in the response.
> This means that the most specific type should be the first one in the union.
> For example, non-required email field should be annotated as `pydantic.EmailStr | typing.Literal[""]` and not
> the other way around.

>[!TIP]
> String fields with a default value are marked as optional in the generated Strawberry input type.
> The null values are automatically converted to an empty string.

>[!TIP]
> A field which is nullable in the generated schema may be left out of the input entirely.
> An omitted field is validated as absent, not as null - so a field which is required by the validator
> reports a `missing` ("Field required") error, and a field with a default value gets its default.
>
> Note that omitting a field is therefore not the same as sending `null` for it. For example, given
> ```python
> class UserCreateInputValidator(strawberry_vercajk.InputValidator):
>     note: str | typing.Literal[""]
> ```
> the `note` field is `String` (nullable) in the schema, sending `null` stores an empty string,
> and leaving `note` out returns a `missing` error with `location: ["note"]`.
> Give the validator field a default value if the field should be omittable.


You can create a Strawberry mutation that uses these validators:
```python
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
                strawberry_vercajk.ValidatedInput[UserCreateInputValidator],
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

```
As you can see in the example, the input validation errors are returned as a list of `ErrorInterface` objects from
the `clean` method of the input validator.
If there are no errors, the `clean_data` attribute of the input validator will contain the pydantic model with validated data.

The `user_create` mutation will return a `UserType` object if the input data is valid, or a `MutationErrorType` object if the input data is invalid.
For example, if the first address city is shorter than 5 characters, the response data will look like:
```json
{
  "__typename": "MutationError",
  "errors": [
    {
      "code": "string_too_short",
      "constraints": [
        {
          "code": "MIN_LENGTH",
          "dataType": "INTEGER",
          "value": 5
        }
      ],
      "location": [
        "addresses",
        0,
        "city"
      ],
      "message": "String should have at least 5 characters"
    }
  ]
}
```
Notice that `errors` is an array of error objects, so if there are multiple validation errors, they will all be returned in the response.
>[!TIP] 
> Feel free to use `strawberry_vercajk.InputValidator` as a normal pydantic model. For example, you can use `@pydantic.field_validator` and `@pydantic.model_validator` to add custom validation logic.

## Communicate validation rules to FE via schema directives
In the example above, you can see that we've used `strawberry_vercajk.pydantic_to_input_type` to convert the Pydantic model to a Strawberry input type.

This function also adds `FieldConstraints` directive to each field which has validation rules.
For example, the `UserCreateInputValidator` will be converted to:
```graphql
input UserCreateInput {
  name: String! @FieldConstraints(minLength: 5, maxLength: 100, pattern: "^[A-Z].*")
  company: CompanyInput!
  addresses: [AddressInput!]! @FieldConstraints(minLength: 1)
  age: Int! @FieldConstraints(gte: 0, lte: 150)
}
```

For a way to extract the schema directives on FE, see [FE vercajk repo](https://github.com/COEXCZ/graphql-vercajk).

>[!WARNING]
>Custom directives are not exported to a standard SDL introspection.
>You solve this by adding a custom `schema` query that returns a complete schema (e.g., `strawberry.printer.print_schema(schema)`)
>
>:warning: Make sure to secure this query as you would any other introspection query!


## Setting custom GraphQL types for the Validation models
There are 2 ways to set custom GraphQL types for the validation models.
They can either be set globally for a type via settings (`VALIDATION.PYDANTIC_TO_GQL_INPUT_TYPE` mapping).
See `AppValidationSettings` for more details and default mappings.

Alternatively, you can set the custom type directly per model field by using the `GqlTypeAnnot` annotation.
For example:

```python
class UserUpdateValidator(pydantic.BaseModel):
    id: typing.Annotated[int, strawberry_vercajk.GqlTypeAnnot(strawberry.ID)]
    name: str
```
The `id` field will be converted to `ID` type in the generated Strawberry input type when using `pydantic_to_input_type`.

## Unified interface for error response types
All errors returned by BE should inherit from `straqberry_vercajk.ErrorInterface`.
This ensures that FE can have a fallback `... on ErrorInterface` in case of new errors added by BE.

Extending on the example in [Validate input data](#validate-input-data), if you want to return a response with a 
custom error type (for example, to suggest a different username if the one provided is already taken), 
you can do it like this:
```python
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


@strawberry.type
class Mutation:
    @strawberry.mutation
    def user_create(
            self,
            input: strawberry_vercajk.ValidatedInput[UserCreateInputValidator],
    ) -> typing.Annotated[
        UserCreateErrorType | UserType,
        strawberry.union(name="UserCreateResponse"),
    ]:
        errors = input.clean()
        if not errors and input.clean_data.name == "TAKEN":
            errors.append(
                UsernameTakenErrorType(
                    location=["name"],
                    suggested_username=f"other-{input.clean_data.name}",
                ),
            )
        if errors:
            return UserCreateErrorType(errors=errors)
        ...
```
