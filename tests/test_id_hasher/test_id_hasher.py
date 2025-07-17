import pydantic
import pytest
from faker import Faker
import dataclasses
import typing
import strawberry.types.scalar

import strawberry_vercajk
from strawberry_vercajk._id_hasher.exceptions import (
    InvalidHashIDPrefixError, HashIDNotRegisteredError,
    HashIDAlreadyRegisteredError,
)

faker = Faker()


def clean_hashid_registry(*prefixes: str) -> None:
    """
    Cleans hasHashIDRegistry in-between tests.
    We can't wipe it completely, because it affects other tests.
    """
    for prefix in prefixes:
        if model := strawberry_vercajk.HashIDRegistry.get_model_by_prefix(prefix):
            del strawberry_vercajk.HashIDRegistry._MODEL_TO_PREFIX_REGISTRY[model]
            del strawberry_vercajk.HashIDRegistry._MODEL_TO_GQL_SCALAR_NAME_REGISTRY[model]
            del strawberry_vercajk.HashIDRegistry._REGISTRY[model]
        if prefix in strawberry_vercajk.HashIDRegistry._PREFIX_TO_MODEL_REGISTRY:
            del strawberry_vercajk.HashIDRegistry._PREFIX_TO_MODEL_REGISTRY[prefix]


def test_underscore_in_prefix_not_allowed() -> None:
    # no underscores allowed
    with pytest.raises(InvalidHashIDPrefixError) as e:
        @strawberry_vercajk.hash_id_register(prefix="prefix_with_underscore")
        class SomeModel:
            id: int
    assert str(e.value) == "Hash ID prefix `prefix_with_underscore` must be lowercase and alphabetical."


def test_spaces_in_prefix_not_allowed() -> None:
    with pytest.raises(InvalidHashIDPrefixError) as e:
        @strawberry_vercajk.hash_id_register(prefix="prefix with spaces")
        class SomeModel:
            id: int

        assert str(e.value) == "Hash ID prefix `prefix with spaces` must be lowercase and alphabetical."


def test_special_characters_in_prefix_not_allowed() -> None:
    with pytest.raises(InvalidHashIDPrefixError) as e:
        @strawberry_vercajk.hash_id_register(prefix="prefix!")
        class SomeModel:
            id: int
        assert str(e.value) == "Hash ID prefix `prefix!` must be lowercase and alphabetical."


def test_numbers_in_prefix_not_allowed() -> None:
    with pytest.raises(InvalidHashIDPrefixError) as e:
        @strawberry_vercajk.hash_id_register(prefix="prefix123")
        class SomeModel:
            id: int
        assert str(e.value) == "Hash ID prefix `prefix123` must be lowercase and alphabetical."


def test_uppercase_letters_in_prefix_not_allowed() -> None:
    with pytest.raises(InvalidHashIDPrefixError) as e:
        @strawberry_vercajk.hash_id_register(prefix="Uppercase")
        class SomeModel:
            id: int
        assert str(e.value) == "Hash ID prefix `UPPERCASE` must be lowercase and alphabetical."


def test_dashes_in_prefix_not_allowed() -> None:
    with pytest.raises(InvalidHashIDPrefixError) as e:
        @strawberry_vercajk.hash_id_register(prefix="prefix-with-dashes")
        class SomeModel:
            id: int
        assert str(e.value) == "Hash ID prefix `prefix-with-dashes` must be lowercase and alphabetical."


def test_hash_id_register_pydantic_model() -> None:
    name: typing.LiteralString = "SomePydanticModelHashIDScalarName"

    @strawberry_vercajk.hash_id_register(prefix="pyd", gql_scalar_name=name)
    class SomePydanticModel(pydantic.BaseModel):
        id: int

    hash_id_scalar: strawberry.types.scalar.ScalarWrapper = strawberry_vercajk.HashID(SomePydanticModel)
    assert isinstance(hash_id_scalar, strawberry.types.scalar.ScalarWrapper)
    assert hash_id_scalar._scalar_definition.name == name
    clean_hashid_registry("pyd")


def test_hash_id_register_dataclass() -> None:
    name: typing.LiteralString = "SomeDataclassHashIDScalarName"

    @strawberry_vercajk.hash_id_register(prefix="dcls", gql_scalar_name=name)
    @dataclasses.dataclass
    class SomeDataclass:
        id: int

    hash_id_scalar: strawberry.types.scalar.ScalarWrapper = strawberry_vercajk.HashID(SomeDataclass)
    assert isinstance(hash_id_scalar, strawberry.types.scalar.ScalarWrapper)
    assert hash_id_scalar._scalar_definition.name == name
    clean_hashid_registry("dcls")


def test_hash_id_registering_the_same_prefix_twice_raises_error() -> None:
    prefix = "prefix"
    @strawberry_vercajk.hash_id_register(prefix=prefix)
    class SomeModel:
        id: int

    with pytest.raises(HashIDAlreadyRegisteredError) as e:
        @strawberry_vercajk.hash_id_register(prefix=prefix)
        class SomeOtherModel:
            id: int

    clean_hashid_registry(prefix)


def test_hash_id_registering_the_equally_named_model_twice_without_specifying_gql_scalar_name_raises_error() -> None:
    prefix_1, prefix_2, prefix_3 = "prefixone", "prefixtwo", "prefixthree"
    @strawberry_vercajk.hash_id_register(prefix=prefix_1)
    class SomeModel:
        id: int

    with pytest.raises(HashIDAlreadyRegisteredError) as e:
        @strawberry_vercajk.hash_id_register(prefix=prefix_2)
        class SomeModel:
            id: int

    # this works, because the gql_scalar_name is different
    @strawberry_vercajk.hash_id_register(prefix=prefix_3, gql_scalar_name=faker.word())
    class SomeModel:
        id: int

    clean_hashid_registry(prefix_1, prefix_2, prefix_3)


def test_registering_the_same_gql_scalar_name_twice_raises_error() -> None:
    name = faker.word()
    prefix_1, prefix_2 = "prefixone", "prefixtwo"
    @strawberry_vercajk.hash_id_register(prefix=prefix_1, gql_scalar_name=name)
    class SomeModel:
        id: int

    with pytest.raises(HashIDAlreadyRegisteredError) as e:
        @strawberry_vercajk.hash_id_register(prefix=prefix_2, gql_scalar_name=name)
        class SomeOtherModel:
            id: int

    clean_hashid_registry(prefix_1, prefix_2)



def test_hash_id_value_serializer() -> None:
    prefix = "prefix"

    @strawberry_vercajk.hash_id_register(prefix=prefix)
    @dataclasses.dataclass
    class SomeModel:
        id: int

    instance = SomeModel(id=123)
    hash_id_scalar: strawberry.types.scalar.ScalarWrapper = strawberry_vercajk.HashID(SomeModel)
    hashed_id: str = hash_id_scalar._scalar_definition.serialize(instance.id)
    parsed_id: int = hash_id_scalar._scalar_definition.parse_value(hashed_id)
    assert hashed_id.startswith(f"{prefix}_")
    assert len(hashed_id) >= len(f"{prefix}_") + 5  # assume >=5 characters in the non-prefixed hash id
    assert parsed_id == instance.id  # reverse operation should return the same value
    clean_hashid_registry(prefix)


def test_trying_to_get_hash_id_for_unregistered_model_raises_error() -> None:
    class SomeModel:
        id: int

    with pytest.raises(HashIDNotRegisteredError) as e:
        strawberry_vercajk.HashID(SomeModel)


def test_getting_id_hasher_of_non_registered_model_raises_error() -> None:
    class SomeModel:
        id: int

    with pytest.raises(HashIDNotRegisteredError) as e:
        strawberry_vercajk.IDHasher(SomeModel)

    prefix = "prefix"
    @strawberry_vercajk.hash_id_register(prefix=prefix)
    class SomeModel:
        id: int
    # registered does not raise
    strawberry_vercajk.IDHasher(SomeModel)
    clean_hashid_registry(prefix)


def test_gql_scalar_factory() -> None:
    prefix = "prefix"
    name = faker.word()

    @strawberry_vercajk.hash_id_register(prefix=prefix, gql_scalar_name=name)
    class SomeModel:
        id: int

    hash_id_scalar = strawberry_vercajk.IDHasher.gql_scalar_factory(SomeModel, prefix, name=name)
    assert isinstance(hash_id_scalar, strawberry.types.scalar.ScalarWrapper)
    hashed_id: str = hash_id_scalar._scalar_definition.serialize(123)
    parsed_id: int = hash_id_scalar._scalar_definition.parse_value(hashed_id)
    assert hashed_id.startswith(f"{prefix}_")
    assert len(hashed_id) >= len(f"{prefix}_") + 5  # assume >=5 characters in the non-prefixed hash id
    assert parsed_id == 123  # reverse operation should return the same value

    # check to/from_hash_id methods return the same value as the scalar serializer/parser
    assert strawberry_vercajk.IDHasher(SomeModel).to_hash_id(123) == hashed_id
    assert strawberry_vercajk.IDHasher(SomeModel).from_hash_id(hashed_id) == 123
    clean_hashid_registry(prefix)


def test_from_hash_id_parses_correct_value() -> None:
    prefix = "prefix"

    @strawberry_vercajk.hash_id_register(prefix=prefix)
    class SomeModel:
        id: int

    hasher = strawberry_vercajk.IDHasher(SomeModel)
    hashed_id = hasher.to_hash_id(123)
    assert hasher.from_hash_id(hashed_id) == 123
    clean_hashid_registry(prefix)


def test_to_hash_id_includes_model_prefix() -> None:
    prefix = "prefix"

    @strawberry_vercajk.hash_id_register(prefix=prefix)
    class SomeModel:
        id: int

    hasher = strawberry_vercajk.IDHasher(SomeModel)
    assert hasher.to_hash_id(123).startswith(f"{prefix}_")
    clean_hashid_registry(prefix)
