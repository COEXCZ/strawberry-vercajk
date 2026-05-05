__all__ = [
    "InputValidator",
    "ValidatedInput",
    "build_errors",
    "pydantic_to_input_type",
    "set_gql_params",
    "validation_context",
]
import contextlib
import contextvars
import functools
import logging
import typing
import warnings

import pydantic
from strawberry.utils.str_converters import to_camel_case

from strawberry_vercajk._base.types import UNSET
from strawberry_vercajk._validation import constants, gql_types

if typing.TYPE_CHECKING:
    import strawberry.types.base

logger = logging.getLogger(__name__)
_validation_context_var = contextvars.ContextVar("_validation_context_var", default=None)


@contextlib.contextmanager
def validation_context(value: dict[str, typing.Any]) -> typing.Iterator[None]:
    token: contextvars.Token = _validation_context_var.set(value)
    try:
        yield
    finally:
        _validation_context_var.reset(token)


def set_gql_params[V](
    *,
    name: str | None = None,
    is_partial: bool = False,
) -> typing.Callable[[type[V]], type[V]]:
    """
    Decorator to set gql params on the input type, used when converting pydantic validators to strawberry input types
    via `pydantic_to_input_type` (or `InputFactory.make`).
    :param name: The name of the gql type.
    :param is_partial: When True, non-required fields use UNSET defaults so that
        `model_dump(exclude_unset=True)` works correctly (PATCH semantics).
    """

    def wrapper(validator: type[V]) -> type[V]:
        if name is not None:
            setattr(validator, constants.INPUT_VALIDATOR_GQL_NAME, name)
        setattr(validator, constants.INPUT_IS_PARTIAL, is_partial)
        return validator

    return wrapper


class ValidatedInput[CleanDataType: "pydantic.BaseModel"]:
    """A class to be used to validate input data. Used on `strawberry.experimental.pydantic.input` types."""

    __clean_data: CleanDataType | None = UNSET
    __errors: list["gql_types.ErrorInterface"] = UNSET
    __original_error: pydantic.ValidationError | None = UNSET
    __provided_field_names: frozenset[str] = UNSET
    __strawberry_definition__: typing.ClassVar["strawberry.types.base.StrawberryObjectDefinition"]
    # _pydantic_type: type[CleanDataType]  # set by strawberry - use `get_validator` method instead

    @classmethod
    def install_tracking_init(cls) -> None:
        original_init = cls.__init__

        @functools.wraps(original_init)
        def tracking_init(self: "ValidatedInput", **kwargs: typing.Any) -> None:  # noqa: ANN401
            original_init(self, **kwargs)
            self.provided_field_names = frozenset(kwargs)

        cls.__init__ = tracking_init

    @property
    def provided_field_names(self) -> frozenset[str]:
        if self.__provided_field_names is UNSET:
            raise ValueError("You must call `install_tracking_init` before accessing `provided_field_names`.")
        return self.__provided_field_names

    @provided_field_names.setter
    def provided_field_names(self, value: frozenset[str]) -> None:
        if self.__provided_field_names is not UNSET:
            raise AttributeError("Cannot re-set provided_field_names attribute - it is read-only.")
        self.__provided_field_names = value

    @classmethod
    def __class_getitem__(cls, item: type[CleanDataType] | typing.TypeVar) -> type["ValidatedInput[CleanDataType]"]:
        if isinstance(item, typing.TypeVar):
            # Type checking - workaround for cases as
            # `def pydantic_to_input_type[T: "pydantic.BaseModel"](...) -> type[ValidatedInput[T]]: ...`
            return cls
        return pydantic_to_input_type(item)

    def clean(
        self,
        context: dict | None = None,
    ) -> list["gql_types.ErrorInterface"]:
        """
        Cleans (validates) the input data and returns the (potential) errors.
        """
        if context is None:
            context = {}

        if self.__clean_data is UNSET:
            with validation_context(context):
                try:
                    # The `to_pydantic` method is used by strawberry to convert the input data to a pydantic model,
                    # but we need to override it.
                    # See `to_pydantic` method in `InputFactory.make` for more details.
                    cleaned_data: CleanDataType = self.to_pydantic(is_inner=False)
                except pydantic.ValidationError as e:
                    self.clean_data = None
                    self.original_error = e
                    self.errors = build_errors(e)
                else:
                    self.errors = []
                    self.original_error = None
                    self.clean_data = cleaned_data
        return self.errors

    @property
    def clean_data(self) -> CleanDataType:
        if self.__clean_data is UNSET:
            raise ValueError("You must call `clean` before accessing `clean_data`.")
        if self.__clean_data is None:
            raise ValueError("The data did not pass the validation.")
        return self.__clean_data

    @clean_data.setter
    def clean_data(self, value: CleanDataType) -> None:
        if self.__clean_data is not UNSET:
            raise AttributeError("Cannot re-set clean_data attribute - it is read-only.")
        self.__clean_data = value

    @property
    def errors(self) -> list["gql_types.ErrorInterface"]:
        if self.__errors is UNSET:
            raise ValueError("You must call `clean` method before accessing `errors`.")
        return self.__errors

    @errors.setter
    def errors(self, value: list["gql_types.ErrorInterface"]) -> None:
        if self.__errors is not UNSET:
            raise AttributeError("Cannot re-set errors attribute - it is read-only.")
        self.__errors = value

    @property
    def original_error(self) -> pydantic.ValidationError | None:
        if self.__original_error is UNSET:
            raise ValueError("You must call `clean` method before accessing `original_error`.")
        return self.__original_error

    @original_error.setter
    def original_error(self, value: pydantic.ValidationError) -> None:
        if self.__original_error is not UNSET:
            raise AttributeError("Cannot re-set original_error attribute - it is read-only.")
        self.__original_error = value

    @classmethod
    def get_validator(cls) -> type[CleanDataType]:
        try:
            return getattr(cls, constants.INPUT_VALIDATOR_ATTR_NAME)
        except AttributeError as e:
            raise AttributeError(
                f"Cannot find validator on {cls.__name__}. "
                f"Make sure to use `{cls.__name__}[ValidatorCls]` to create the input type from the ValidatorCls.",
            ) from e


class InputValidator(pydantic.BaseModel):
    """A class used to validate input data."""

    model_config = pydantic.ConfigDict(
        arbitrary_types_allowed=True,
        frozen=True,  # makes the instance immutable - once the data is validated, it should not be changed directly
    )

    # noinspection PyMissingConstructor,PyMethodParameters
    def __init__(__pydantic_self__, **data: typing.Any) -> None:  # noqa: N805 ANN401
        """
        Override __init__ to add a validation context (see validation_context context manager).
        Copied from:
        https://docs.pydantic.dev/latest/concepts/validators/#using-validation-context-with-basemodel-initialization
        """
        __pydantic_self__.__pydantic_validator__.validate_python(
            data,
            self_instance=__pydantic_self__,
            context=_validation_context_var.get(),
        )


def pydantic_to_input_type[T: "pydantic.BaseModel"](  # TODO - remove and internally use InputFactory directly
    validator_cls: type[T],
    /,
    name: typing.LiteralString | None = None,
) -> type[ValidatedInput[T]]:
    """
    Return a strawberry input type for given validator.
    """
    warnings.warn(
        "Use `ValidatedInput[<validatorCls>]` instead of `pydantic_to_input_type(<validatorCls>)`. "
        "This function will be removed in the future. "
        "To set the gql name, use `@set_gql_params(name='...')` decorator on the `validatorCls`.",
        DeprecationWarning,
        stacklevel=2,
    )
    from strawberry_vercajk._validation.input_factory import InputFactory

    return InputFactory.make(validator_cls, name=name)


def build_errors(exc: "pydantic.ValidationError") -> list["gql_types.ErrorInterface"]:
    errors: list[gql_types.ErrorInterface] = []
    locations_with_type_union_errors: set[tuple[str, ...]] = set()
    for error in exc.errors():
        error_ctx = error.get("ctx", {})
        loc = error.get("loc", [])
        constraints: list[gql_types.ErrorConstraintType] = []
        for ctx_code, ctx_value in error_ctx.items():
            if ctx_code not in gql_types.ErrorConstraintChoices:
                continue
            ctx_code: gql_types.ErrorConstraintChoices = gql_types.ErrorConstraintChoices(ctx_code)  # noqa: PLW2901
            constraints.append(
                gql_types.ErrorConstraintType(
                    code=ctx_code,
                    value=str(ctx_value),
                    data_type=ctx_code.get_data_type(),
                ),
            )

        location: list[str | int] = []
        loc_len = len(loc)
        has_type_union_error: bool = False
        for l_idx, l in enumerate(loc, 1):  # noqa: E741
            if l_idx == loc_len and isinstance(l, str) and "[" in l:
                # A special case, when the pydantic field is a union of types which have more validators,
                # the last location element is the validator in which the error occurred.
                # For example, if we have a field
                #   email: pydantic.EmailStr | typing.Literal[""]
                # and we pass in a value "some_invalid_email", pydantic will throw two errors with these locations:
                #   - ("email", "function-after[Validate(), str]")
                #   - ("email", "literal['']")
                # We don't want to include the last part of the location in the error message.
                # From my observation, the last part always seems to include "[" character, which can
                # never be in the field name - using this to determine if we should skip the last part.
                # See test_specific_validator_stripped_from_error_location.
                has_type_union_error = True
                continue
            if isinstance(l, str):
                location.append(to_camel_case(l))
            else:
                location.append(l)

        if has_type_union_error:
            if tuple(location) in locations_with_type_union_errors:
                # See comment above.
                # We only keep the first error for the same location from the errors caused by type union.
                # This is so we don't confuse the user with multiple errors for the same field which may even be
                # contradictory in some cases.
                # This relies on the programmer to place the more specific validators first in the union, so
                # for example, `email: pydantic.EmailStr | typing.Literal[""]` and not the other way around.
                continue
            locations_with_type_union_errors.add(tuple(location))

        errors.append(
            gql_types.ErrorType(
                code=error["type"],
                message=error["msg"],
                location=location,
                constraints=constraints,
            ),
        )
    return errors
