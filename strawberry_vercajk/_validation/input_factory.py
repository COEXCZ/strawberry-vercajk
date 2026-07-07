__all__ = [
    "GqlTypeAnnot",
    "InputFactory",
]
import dataclasses
import types
import typing

import pydantic
import pydantic_core
import pydbull
import strawberry
from strawberry.experimental.pydantic.conversion import convert_strawberry_class_to_pydantic_model
from strawberry.types.lazy_type import LazyType as StrawberryLazyType

from strawberry_vercajk._app_settings import app_settings
from strawberry_vercajk._validation import constants, directives
from strawberry_vercajk._validation.validator import ValidatedInput

# GraphQL doesn't support working with larger integers than this.
# We could define custom scalar, but for now it's not necessary.
# See https://github.com/graphql/graphql-spec/issues/73.
DIRECTIVE_MAX: int = 2_147_483_647
DIRECTIVE_MIN: int = -DIRECTIVE_MAX


def _none_to_empty_string(value: typing.Any) -> typing.Any:  # noqa: ANN401
    return "" if value is None else value


class GqlTypeAnnot:
    """
    Annotate a pydantic model with a GraphQL type.

    Example:
    -------
        class UserValidator(pydantic.BaseModel):
            id: typing.Annotated[int, GqlTypeAnnot(strawberry.ID)]
            name: str

    Now when creating a GraphQL input type from `UserValidator` via `InputFactory.make(UserValidator)`,
    the `id` field will be annotated with `strawberry.ID` in the GraphQL schema.

    """

    def __init__(self, gql_type: type | types.UnionType, /) -> None:
        self.gql_type = gql_type


@dataclasses.dataclass(frozen=True)
class _SelfReferenceLazyType(StrawberryLazyType):
    """
    A strawberry `LazyType` used for self-referential (and mutually-recursive) input fields.

    When a validator has a field typed as itself - directly, in a list, or via another validator
    that points back to it - the strawberry input type does not exist yet while its own fields are
    being built. Instead of recursing into `InputFactory.make` (which would never terminate), such a
    field is annotated with this lazy type. It resolves to the finished input type from
    `InputFactory._REGISTRY` once strawberry actually needs it (e.g. at schema-build time), by which
    point the type has been fully built and registered.
    """

    validator: "type[pydantic.BaseModel] | None" = None

    @typing.override
    def resolve_type(self) -> type:
        # By the time strawberry resolves this lazy type the validator has finished building, so
        # `make` returns the already-built input type straight from its registry cache.
        return InputFactory.make(self.validator)


class InputFactory:
    """
    Factory for creating GraphQL input type from InputValidator type
    """

    _REGISTRY: typing.ClassVar[dict[type["pydantic.BaseModel"], type["ValidatedInput"]]] = {}
    _BUILDING: typing.ClassVar[set[type["pydantic.BaseModel"]]] = set()
    """Validators whose input type is currently being built. Used to detect and break self-references
    and mutual recursion - see `_SelfReferenceLazyType`."""

    @classmethod
    def make[T: pydantic.BaseModel](
        cls,
        input_validator: type[T],
        *,
        name: typing.LiteralString | None = None,
    ) -> type[ValidatedInput[T]]:
        """
        Take a pydantic models and return a `ValidatedInput` GraphQL type.
        Take all fields from the validator and create a strawberry input with all fields annotated by `strawberry.auto`.
        :param input_validator: pydantic.BaseModel subclass
        :param name: Name of the returned GraphQL type
        """
        if input_validator in cls._REGISTRY:
            return cls._REGISTRY[input_validator]

        if name is None:
            name = cls._get_gql_name(input_validator)

        # Mark this validator as "being built" so that a self-reference (or a mutually-recursive
        # reference back to it) short-circuits to a lazy annotation instead of recursing into `make`
        # forever. See `_SelfReferenceLazyType` and `_get_field_annotation`.
        cls._BUILDING.add(input_validator)
        try:
            fields = input_validator.__pydantic_fields__.copy()
            for field_info in fields.values():
                # If the field is also a pydantic model, we need to create a GraphQL input for it as well.
                # Validators that are already being built are skipped here - they are handled as lazy
                # self-references when the field annotation is computed.
                nested_input_validator = cls.__get_input_validator(field_info.annotation)
                if nested_input_validator is not None and nested_input_validator not in cls._BUILDING:
                    cls.make(nested_input_validator)

            input_fields: list[tuple[str, type, strawberry.field]] = []
            field_convertors_any: bool = False
            for field_name, field_info in fields.items():
                # Get the annotation type for the strawberry input field
                field_type, field_convertors = cls._get_field_annotation(
                    field_info.annotation,
                    is_required=field_info.is_required(),
                    field_metadata=field_info.metadata,
                )
                field_convertors_any = field_convertors_any or field_convertors
                if field_convertors:
                    input_validator.__pydantic_fields__[field_name].metadata.extend(field_convertors)

                # Extract constraints from the field so we can add them to the directive for FE to use.
                field_constraints_directive = cls.extract_constrains(input_validator, field_info)

                # Create the strawberry field
                if field_constraints_directive:
                    strawberry_field = strawberry.field(
                        directives=[
                            field_constraints_directive,
                        ],
                        deprecation_reason=field_info.deprecated,
                    )
                else:
                    strawberry_field = strawberry.field(
                        deprecation_reason=field_info.deprecated,
                    )
                input_fields.append((field_name, field_type, strawberry_field))

            # If any field has a new convertor, we need to rebuild the model.
            if field_convertors_any:
                input_validator.model_rebuild(force=True)

            # Create the strawberry input class
            input_cls = type(
                name,
                (ValidatedInput,),
                {name: value for name, annot, value in input_fields},
            )
            input_cls.__annotations__ = {name: annot for name, annot, value in input_fields}
            gql_input = typing.cast(
                "type[ValidatedInput[T]]",
                strawberry.experimental.pydantic.input(input_validator, name=name)(input_cls),
            )
            gql_input.to_pydantic = cls.to_pydantic
            setattr(gql_input, constants.INPUT_VALIDATOR_ATTR_NAME, input_validator)
            cls._REGISTRY[input_validator] = gql_input
            return gql_input
        finally:
            cls._BUILDING.discard(input_validator)

    @classmethod
    def _get_gql_name(cls, input_validator: type["pydantic.BaseModel"]) -> "typing.LiteralString":
        """Return the GraphQL type name used for the given validator."""
        if hasattr(input_validator, constants.INPUT_VALIDATOR_GQL_NAME):
            return getattr(input_validator, constants.INPUT_VALIDATOR_GQL_NAME)
        return typing.cast("typing.LiteralString", input_validator.__name__.removesuffix("Validator"))

    @classmethod
    def _lazy_self_reference(cls, input_validator: type["pydantic.BaseModel"]) -> StrawberryLazyType:
        """Build a lazy annotation pointing at the (possibly still in-progress) input type."""
        return _SelfReferenceLazyType(
            type_name=cls._get_gql_name(input_validator),
            module=__name__,
            validator=input_validator,
        )

    @classmethod
    def _get_field_annotation(  # noqa: C901 PLR0911 PLR0912
        cls,
        field_type: type,
        /,
        is_required: bool,
        field_metadata: list | None = None,
    ) -> tuple[type, list[pydantic.BeforeValidator | pydantic.AfterValidator]]:
        """
        Get the annotation for a strawberry field.
        If the new annotation requires a before/after validation convertor, it is returned as well.

        We use this method because we may want to convert some pydantic types to different GraphQL input types.
        For example
            - We convert `str` to `Optional[str]` if the field has a default value, so that the FE doesn't
              have to send an empty string to indicate "empty" instead of null as everywhere else.
            - We also convert `typing.Literal[""]` to `None` so that the field appears as optional in the gql schema.
              We then convert None back to empty string when data is received.
            - We replace more complex or custom pydantic types with types understandable by strawberry.
              See `app_settings.VALIDATION.PYDANTIC_TO_GQL_INPUT_TYPE` and `GqlTypeAnnot` for more details.

        """
        # TODO - this function is a bit too complex and should probably be refactored or split up.
        for meta in field_metadata or []:
            if isinstance(meta, GqlTypeAnnot):
                return meta.gql_type, []

        field_type = cls._get_origin_type_from_annotated_type(field_type)
        if field_type in cls._BUILDING:
            # Self-referential (or mutually-recursive) field: the target input type is still being
            # built, so emit a lazy reference to it instead of recursing into `make`.
            return cls._lazy_self_reference(field_type), []

        type_map = app_settings.VALIDATION.PYDANTIC_TO_GQL_INPUT_TYPE
        if field_type in type_map:
            # If the gql input type for this exact type is defined in settings - use it.
            return type_map[field_type], []

        if field_type is str and not is_required:
            # Mark string fields which have a default value as not required.
            # This is just so that FE doesn't have a "special case" where they have to send an empty string
            # to these fields to indicate "empty" instead of null as everywhere else.
            return str | None, [pydantic.BeforeValidator(_none_to_empty_string)]

        if typing.get_origin(field_type) in [typing.Union, types.UnionType]:
            ret_types: list[type] = []
            convertors: list[pydantic.BeforeValidator | pydantic.AfterValidator] = []
            is_auto: bool = True  # whether "strawberry.auto" should be used
            for internal_type in typing.get_args(field_type):
                internal_origin_type = cls._get_origin_type_from_annotated_type(internal_type)
                if internal_origin_type is typing.Literal[""]:
                    # Replace typing.Literal[""] with NoneType
                    #  - let the field appear as optional in the gql schema
                    #  - convert None back to empty string when data is received
                    is_auto = False
                    ret_types.append(types.NoneType)
                    convertors.append(pydantic.BeforeValidator(_none_to_empty_string))
                elif internal_origin_type in type_map:
                    # Some type in the union has a defined gql input type in settings -> use it.
                    is_auto = False
                    ret_types.append(type_map[internal_origin_type])
                elif typing.get_origin(internal_type) is list:
                    # E.g., if field_type is `list[str] | None`
                    annot, _ = cls._get_field_annotation(internal_type, is_required=True)
                    if annot is not strawberry.auto:
                        is_auto = False
                    ret_types.append(annot)
                elif internal_origin_type in cls._BUILDING:
                    # Self-referential / mutually-recursive member of the union, e.g. `Node | None`.
                    is_auto = False
                    ret_types.append(cls._lazy_self_reference(internal_origin_type))
                else:
                    # "Normal" type -> e.g., if field_type is `str | None`
                    ret_types.append(internal_type)

            if is_auto:
                # All types in the union are simple types, which strawberry can handle itself -> strawberry.auto
                return strawberry.auto, []
            return typing.Union[*ret_types], convertors

        if typing.get_origin(field_type) is list:
            list_args = typing.get_args(field_type)
            if len(list_args) != 1:
                raise ValueError(f"List type must have exactly one argument, got {list_args}")
            # Could be a list of unions -> recursively get the inner type
            inner_annotation, field_convertors = cls._get_field_annotation(list_args[0], is_required=True)
            if inner_annotation is strawberry.auto:
                # Is a list of simple types (which strawberry can handle itself) -> return strawberry.auto
                return strawberry.auto, field_convertors
            return list[inner_annotation], field_convertors
        return strawberry.auto, []

    @classmethod
    def __get_input_validator(cls, annotation: type) -> type[pydantic.BaseModel] | None:
        try:
            return cls.__get_from_complex_type(annotation, pydantic.BaseModel)
        except TypeError:
            return None

    @classmethod
    def __get_from_complex_type[T](cls, from_type: type, type_: type[T]) -> type[T]:
        """
        Get the type from a complex type.
        For example, if `t` is `enum.Enum`, this method will return SomeEnum for 'from_type' of types
         - `SomeEnum`
         - `SomeEnum | None`
         - `Optional[SomeEnum]`
         - `list[SomeEnum]`
         - `list[SomeEnum | None]`
         - `typing.Annotated[SomeEnum | None, ...]`
         - `typing.Annotated[SomeEnum, ...] | None`
        :param from_type: The type to get the type from
        :param type_: The type to get
        :raises TypeError: if the type is not found
        """
        if typing.get_origin(from_type) in [types.UnionType, typing.Union, typing.Annotated]:
            for internal_type in typing.get_args(from_type):
                try:
                    return cls.__get_from_complex_type(internal_type, type_)
                except TypeError:
                    pass
        if typing.get_origin(from_type) is list:
            for args in typing.get_args(from_type):
                try:
                    return cls.__get_from_complex_type(args, type_)
                except TypeError:
                    pass
        if issubclass(from_type, type_):  # may raise TypeError
            return from_type
        raise TypeError

    @classmethod
    def _get_origin_type_from_annotated_type(cls, t: type) -> type:
        """
        Get the origin type from an annotated type.
        For example, if `t` is `Annotated[str, ...]`, this method will return `str`.
        :param t: The type to get the origin type from
        """
        if typing.get_origin(t) is typing.Annotated:
            return cls._get_origin_type_from_annotated_type(typing.get_args(t)[0])
        return t

    @classmethod
    def extract_constrains(
        cls,
        input_validator: pydantic.BaseModel,
        field_info: "pydantic.fields.FieldInfo",
    ) -> directives.FieldConstraintsDirective:
        def clean_value(value: typing.Any) -> typing.Any:  # noqa: ANN401
            if value is pydantic_core.PydanticUndefined:
                return None
            if isinstance(value, int):
                return min(max(DIRECTIVE_MIN, value), DIRECTIVE_MAX)
            return value

        pydantic_adapter = pydbull.PydanticAdapter(type(input_validator))
        return directives.FieldConstraintsDirective(
            gt=clean_value(pydantic_adapter.get_greater_than(field_info)),
            gte=clean_value(pydantic_adapter.get_greater_than_or_equal(field_info)),
            lt=clean_value(pydantic_adapter.get_less_than(field_info)),
            lte=clean_value(pydantic_adapter.get_less_than_or_equal(field_info)),
            min_length=clean_value(pydantic_adapter.get_min_length(field_info)),
            max_length=clean_value(pydantic_adapter.get_max_length(field_info)),
            max_digits=clean_value(pydantic_adapter.get_decimal_max_digits(field_info)),
            decimal_places=clean_value(pydantic_adapter.get_decimal_places(field_info)),
            pattern=clean_value(pydantic_adapter.get_pattern(field_info)),
            multiple_of=clean_value(pydantic_adapter.get_multiple_of(field_info)),
        )

    @staticmethod
    def to_pydantic(
        self: "ValidatedInput",  # noqa: PLW0211
        is_inner: bool = True,
        **kwargs,
    ) -> dict | pydantic.BaseModel:
        """
        Overrides the default strawberry `to_pydantic` method (see `to_pydantic_default` in strawberry).
        The reason for this is that we need to validate the whole pydantic object at once.
        The default strawberry method converts the input data to a pydantic model field by field (if nested).
        This raises the pydantic validation error on the first error, and therefore fails with a single exception
        on the first nested pydantic object which is invalid and doesn't validate further.
        For this reason, we don't convert the nested pydantic objects to pydantic models but keep them as
        dictionaries and then insert this dictionary into the parent (outermost) pydantic object.
        This way, pydantic validates the whole object at once, and we get all validation errors.
        """
        instance_kwargs = {
            f.name: convert_strawberry_class_to_pydantic_model(
                getattr(self, f.name),
            )
            for f in dataclasses.fields(self)
        }
        instance_kwargs.update(kwargs)
        if not is_inner:
            return self.get_validator()(**instance_kwargs)
        return instance_kwargs
