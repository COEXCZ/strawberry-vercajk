__all__ = [
    "Filter",
    "FilterQ",
    "FilterSet",
    "model_filter",
]

import abc
import dataclasses
import functools
import types
import typing
from datetime import date, datetime
from decimal import Decimal

import pydantic
import pydantic.fields

from strawberry_vercajk._base import utils as base_utils
from strawberry_vercajk._validation.validator import InputValidator

# Add more when needed. See django.db.models.lookups or django.db.models.<FieldClass>.get_lookups().
_DBLookupType = typing.Literal[
    "exact",
    "iexact",
    "contains",
    "icontains",
    "in",
    "gt",
    "gte",
    "lt",
    "lte",
    "startswith",
    "istartswith",
    "endswith",
    "iendswith",
    "range",
    "isnull",
    "regex",
    "iregex",
    "date",
    "year",
    "month",
    "day",
    "week_day",
    "iso_week_day",
    "week",
    "iso_year",
    "quarter",
    "overlap",
]
_DB_LOOKUPS: set[typing.LiteralString] = set(typing.get_args(_DBLookupType))

_FILTER_MODEL_ATTR_NAME: typing.LiteralString = "__VERCAJK_MODEL"
_FILTERS_FILTERSET_ATTR_NAME: typing.LiteralString = "__VERCAJK_FILTERS"

FilterQValueT = str | int | float | Decimal | date | datetime


@dataclasses.dataclass
class FilterQ:
    field: str | None = None
    lookup: _DBLookupType | None = None
    value: FilterQValueT | typing.Iterable[FilterQValueT] | None = None
    _left: typing.Self | None = None
    _right: typing.Self | None = None
    _operator: typing.Literal["AND", "OR", "NOT"] | None = None

    def __and__(self, other: typing.Self) -> typing.Self:
        # Skip for no-op filters
        left = self if not self.is_noop else None
        if left is None:
            return other
        right = other if not other.is_noop else None
        if right is None:
            return left

        return FilterQ(_left=left, _right=right, _operator="AND" if not other.is_noop else None)

    def __or__(self, other: typing.Self) -> typing.Self:
        # Skip for no-op filters
        left = self if not self.is_noop else None
        if left is None:
            return other
        right = other if not other.is_noop else None
        if right is None:
            return left

        return FilterQ(_left=left, _right=right, _operator="OR")

    def __invert__(self) -> typing.Self:
        # Negating a no-op stays a no-op; there is nothing to invert.
        if self.is_noop:
            return self
        # Double negation cancels out: ~~x == x.
        if self.is_not:
            return self._left
        # Wrap the whole (possibly compound) expression as the operand of a unary NOT node.
        return FilterQ(_left=self, _operator="NOT")

    def __bool__(self) -> bool:
        return not self.is_noop

    @property
    def is_noop(self) -> bool:
        """No operation should be performed."""
        return self.field is None and self.left is None and self.right is None

    @property
    def left(self) -> typing.Self:
        return self._left

    @property
    def right(self) -> typing.Self:
        return self._right

    @property
    def is_and(self) -> bool:
        return self._operator == "AND"

    @property
    def is_or(self) -> bool:
        return self._operator == "OR"

    @property
    def is_not(self) -> bool:
        return self._operator == "NOT"


def model_filter[T: "FilterSet"](
    model: type,
) -> typing.Callable[[type[T]], type[T]]:
    @functools.wraps(model_filter)
    def wrapper(
        filterset_cls: type[T],
    ) -> type[T]:
        setattr(filterset_cls, _FILTER_MODEL_ATTR_NAME, model)
        filterset_cls._initialize_filters()  # noqa: SLF001
        return filterset_cls

    return wrapper


@dataclasses.dataclass
class FilterInterface:
    @abc.abstractmethod
    def get_filter_q(
        self,
        value: typing.Any,  # noqa: ANN401
    ) -> FilterQ:
        """
        Get the filter expression for the filter.
        :param value: Value to filter by
        :return: final filter expression
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_filters(self) -> list["Filter"]:
        """
        Get all filters of this filter.
        If the filter is a combination of multiple filters, it returns all of them.
        For example, if the filter is defined as `Filter1 & (Filter2() | Filter3())`,
        it returns [Filter1(), Filter2(), Filter3()].
        """
        raise NotImplementedError

    def __or__(self, other: "FilterInterface") -> typing.Self:
        """
        Return a new filter interface which is a combination of this and the other.
        This allows for the use of the | operator.

        Example:
        -------
            q: Annotated[
                str | None,
                base_inputs.list.Filter(model_field="first_name", lookup="icontains") |
                base_inputs.list.Filter(model_field="last_name", lookup="icontains"),
                pydantic.Field(
                    default=None,
                    description="Icontains search in first name or last name.",
                ),
            ]

        """

        @dataclasses.dataclass
        class OrFilter(FilterInterface):
            filter1: "FilterInterface"
            filter2: "FilterInterface"

            def get_filter_q(
                self,
                value: typing.Any,  # noqa: ANN401
            ) -> FilterQ:
                return self.filter1.get_filter_q(value) | self.filter2.get_filter_q(value)

            def get_filters(self) -> list["Filter"]:
                return self.filter1.get_filters() + self.filter2.get_filters()

        return OrFilter(self, other)

    def __and__(self, other: "FilterInterface") -> typing.Self:
        """
        Return a new filter interface which is a combination of this and the other.
        This allows for the use of the & operator.

        Example:
        -------
            both_first_and_last_name_icontains: Annotated[
                str | None,
                base_inputs.list.Filter(model_field="first_name", lookup="icontains") |
                base_inputs.list.Filter(model_field="last_name", lookup="icontains"),
                pydantic.Field(
                    default=None,
                    description="Both first and last name of user must contain given string.",
                ),
            ]

        """

        @dataclasses.dataclass
        class AndFilter(FilterInterface):
            filter1: "FilterInterface"
            filter2: "FilterInterface"

            def get_filter_q(
                self,
                value: typing.Any,  # noqa: ANN401
            ) -> FilterQ:
                return self.filter1.get_filter_q(value) & self.filter2.get_filter_q(value)

            def get_filters(self) -> list["Filter"]:
                return self.filter1.get_filters() + self.filter2.get_filters()

        return AndFilter(self, other)

    def __invert__(self) -> typing.Self:
        """
        Return a new filter interface which is a negation of the original.
        This allows for the use of the ~ operator.

        Example:
        -------
            is_active: Annotated[
                bool | None,
                ~base_inputs.list.Filter(model_field="is_blacklisted", lookup="exact"),
                pydantic.Field(
                    default=None,
                    description="Filter by whether the object is active (i.e., is not blacklisted).",
                )
            ]

        """

        @dataclasses.dataclass
        class NegationFilter(FilterInterface):
            filter: "FilterInterface"

            def get_filter_q(
                self,
                value: typing.Any,  # noqa: ANN401
            ) -> FilterQ:
                return ~self.filter.get_filter_q(value)

            def get_filters(self) -> list["Filter"]:
                return self.filter.get_filters()

        return NegationFilter(self)


class Filter(FilterInterface):
    """
    Filter for an input field inside a Filterset.
    It should be used as an annotation on the field.
    For example:
        @model_filter(models.User)
        class UserFilterset(Filterset):
            q: typing.Annotated[
                str | None,
                Filter(model_field="first_name", lookup="icontains") |   <--- here
                Filter(model_field="last_name", lookup="icontains"),      <--- and here
                pydantic.Field(
                    default=None,
                    description="Icontains search in first name or last name.",
                )
            ]
            ... other filters
    """

    def __init__(
        self,
        model_field: str | None = None,
        lookup: _DBLookupType | None = None,
        *,
        check_field_exists: bool = True,
        prepare_value: typing.Callable[[typing.Any], typing.Any] | None = None,
    ) -> None:
        """
        :param model_field: Name of the model field to filter by. If not specified, it will be inferred from the name.
        :param lookup: Lookup to use for the filter. If not specified, it will be inferred from the field type or name.
        :param check_field_exists: Whether to check if the field exists on the model. Default is True.
        :param prepare_value: Function to prepare the value received from FE before passing it to the filter.
        """
        self.check_field_exists = check_field_exists
        self._model_field = model_field
        self._lookup = lookup
        self._prepare_value = prepare_value

        # assigned by the filter
        self.__field_name: typing.LiteralString | None = None
        self.__field_type: type | None = None
        self.__filterset_cls: type[FilterSet] | None = None

    def __str__(self) -> str:
        return (
            f"({type(self).__name__}) "
            f"{self.__filterset_cls.__name__ if self.__filterset_cls else ''}."
            f"{self.__field_name if self.__field_name else ''}"
        )

    @property
    def field_name(self) -> typing.LiteralString:
        """Name of the field on the filterset"""
        if self.__field_name is None:
            raise ImproperlyInitializedFilterError(self)
        return self.__field_name

    @property
    def filterset_cls(self) -> type["FilterSet"]:
        if self.__filterset_cls is None:
            raise ImproperlyInitializedFilterError(self)
        return self.__filterset_cls

    @functools.cached_property
    def is_list(self) -> bool:
        if self.filterset_field_type is list:
            # e.g., when the field is annotated as a list | None
            # Should not happen, because we're already checking for this in FilterSet._check_field_type
            return True
        if typing.get_origin(self.filterset_field_type) is list:
            # e.g., when the field is annotated as list[str]
            return True
        if typing.get_origin(self.filterset_field_type) is typing.Literal:
            # e.g., when the field is annotated as Literal["S1", "S2", ...]
            return False
        inner_types: tuple[type, ...] = typing.get_args(self.filterset_field_type)
        if not inner_types:
            # e.g., when the field is annotated just as str
            return False
        # If there are inner types, it must be a union with None (i.e., is Optional).
        # This is also checked in FilterSet._check_field_type
        non_null_types: list[type] = [t for t in inner_types if t is not type(None)]
        if len(non_null_types) == 0:
            # I'm not really sure if this can happen, because None | None annotation is not allowed, but just in case
            raise FilterFieldTypeNotSupportedError(
                f"`{self.filterset_cls.__name__}.{self.field_name}` filter "
                f"does not support union types other than`<type> | None`, i.e., optional field..",
            )
        if len(non_null_types) > 1:
            # e.g., when the field is annotated as str | int | None
            raise FilterFieldTypeNotSupportedError(
                f"`{self.filterset_cls.__name__}.{self.field_name}` filter "
                f"does not support union types other than `<type> | None`, i.e., optional field..",
            )
        non_null_type: type = non_null_types[0]
        if non_null_type is list:
            raise FilterFieldTypeNotSupportedError(
                f"`{self}` filter annotated as `{self.filterset_field_type}` is not supported. You must specify "
                f"the type of the list, for example `list[str]`.",
            )
            # e.g., when the field is annotated as list | None
        return typing.get_origin(non_null_type) is list  # True when the field is annotated as list[str] | None

    @functools.cached_property
    def lookup(self) -> _DBLookupType:
        """
        Get the lookup to use for the filter. If not specified, it will be inferred from the field type of name.
        :return: Expression to use for the filter.
        """
        if self._lookup:
            return self._lookup

        suffix_inferred_lookup: str | None = self.field_name.split("_")[-1]
        if suffix_inferred_lookup not in _DB_LOOKUPS:
            suffix_inferred_lookup = None
        if self.is_list:
            if suffix_inferred_lookup and suffix_inferred_lookup not in ["in", "overlap"]:
                raise FilterFieldLookupAmbiguousError(
                    f"\n{self.filterset_cls.__name__}.{self.field_name} filter `{type(self).__name__}` has\n"
                    f"an inferred lookup `{suffix_inferred_lookup}` which does not support list as input,\n"
                    f"yet the field is annotated as `{self.filterset_field_type}`.",
                )
            return "in"
        return typing.cast("_DBLookupType", suffix_inferred_lookup or "exact")

    @property
    def model_field(self) -> typing.LiteralString:
        """Field name on the model"""
        if self._model_field:
            return self._model_field
        return typing.cast("typing.LiteralString", self.field_name.removesuffix(f"_{self.lookup}"))

    def get_filter_q(
        self,
        value: typing.Any,  # noqa: ANN401
    ) -> FilterQ:
        """Get the filter expression for the filter."""
        cleaned_value = self.prepare_value(value)
        return FilterQ(
            field=self.model_field,
            lookup=self.lookup,
            value=cleaned_value,
        )

    def get_filters(self) -> list[typing.Self]:
        return [self]

    def prepare_value(self, value: typing.Any) -> typing.Any:  # noqa: ANN401
        if self._prepare_value is None:
            return value
        return self._prepare_value(value)

    @property
    def filterset_field(self) -> "pydantic.fields.FieldInfo":
        return self.filterset_cls.__pydantic_fields__[self.field_name]

    @property
    def filterset_field_type(self) -> type:
        return self.filterset_field.annotation

    @field_name.setter
    def field_name(self, value: typing.LiteralString) -> None:
        self.__field_name = value

    @filterset_cls.setter
    def filterset_cls(self, value: type["FilterSet"]) -> None:
        self.__filterset_cls = value

    def _check_model_field_exists(self) -> None:
        """Checks if the field exists on the model."""
        model_cls = self.filterset_cls.get_model()
        if dataclasses.is_dataclass(model_cls):
            return base_utils.check_dataclass_field_exists(model_cls, self.model_field)
        if issubclass(model_cls, pydantic.BaseModel):
            return base_utils.check_pydantic_field_exists(model_cls, self.model_field)

        try:
            import django.db.models

            if issubclass(model_cls, django.db.models.Model):
                return base_utils.check_django_field_exists(model_cls, self.model_field)
        except ImportError:
            pass

        raise TypeError(f"Unexpected model type {model_cls} in {self.filterset_cls().__name__} FilterSet.")

    def _check_lookup_is_resolvable(self) -> None:
        """Checks if the lookup is resolvable for the field type."""
        if self.is_list and self.lookup not in ["in", "overlap"]:
            raise FilterFieldLookupAmbiguousError(
                f"`{self.filterset_cls.__name__}.{self.field_name}` filter `{type(self).__name__}` has "
                f"a lookup `{self.lookup}` which does not support list as input, yet "
                f"the field is annotated as `{self.filterset_field_type}`.",
            )


class FilterSet(InputValidator):
    """
    Filterset for filtering a list of objects.
    It should be used together with the `model_filter` decorator.
    For example:

        @model_filter(models.User)
        class UserFilterset(Filterset):
            q: typing.Annotated[
                str | None,
                Filter(model_field="first_name", lookup="icontains") |
                Filter(model_field="last_name", lookup="icontains"),
                pydantic.Field(
                    default=None,
                    description="Icontains search in first name or last name.",
                )
            ]
            ... other filters ...
    """

    def __hash__(self) -> int:
        return hash(tuple([type(self), *list(self.model_dump().items())]))  # noqa: C409

    def get_filter_q(self) -> FilterQ:
        """Perform the filtering."""
        filters = self.get_filters()
        fq = FilterQ()
        for field_name, field_filter in filters.items():
            field_filter: FilterInterface
            input_value = getattr(self, field_name)
            # Ideally, we'd like to check for strawberry.UNSET instead of None.
            # But it doesn't work for some reason and None is always passed.
            # We may need to handle this some way in the future...
            if input_value is None:
                continue
            fq &= field_filter.get_filter_q(input_value)
        return fq

    @classmethod
    def get_filters(cls) -> dict[typing.LiteralString, FilterInterface]:
        """
        Get all filters of this filterset.
        :return: Dict of filters, where key is the field name and value are filters.
        """
        if not hasattr(cls, _FILTERS_FILTERSET_ATTR_NAME):
            raise ImproperlyInitializedFilterSetError(cls)
        return getattr(cls, _FILTERS_FILTERSET_ATTR_NAME)

    @classmethod
    def get_model(cls) -> type:
        """The model for this filterset. It is set by the `model_filter` decorator."""
        if not hasattr(cls, _FILTER_MODEL_ATTR_NAME):
            raise ImproperlyInitializedFilterSetError(cls)
        return getattr(cls, _FILTER_MODEL_ATTR_NAME)

    @classmethod
    def _initialize_filters(cls) -> None:
        """
        Initiate and check the filters for this filterset.
        It assigns the necessary attributes to the Filter annotations,
        checks if the filters are properly annotated, whether the model fields exist, and so on.
        This method is called automatically by the `model_filter` decorator and should not be called manually.
        """
        ret: dict[str, FilterInterface] = {}
        for field_name, field in cls.__pydantic_fields__.items():
            cls._check_field_type(field.annotation)
            field_filters: list[FilterInterface] = []
            for annotation in field.metadata:
                if not cls._is_filter_annotation(annotation):
                    continue
                annotation: FilterInterface
                for filter_ in annotation.get_filters():
                    filter_.filterset_cls = cls
                    filter_.field_name = field_name
                    filter_._check_lookup_is_resolvable()  # noqa: SLF001
                    if filter_.check_field_exists:
                        filter_._check_model_field_exists()  # noqa: SLF001
                field_filters.append(annotation)

            if not field_filters:
                raise MissingFilterAnnotationError(
                    f"\nField `{cls.__name__}.{field_name}` must be annotated with at exactly one filter. "
                    f"Example: `{cls.__name__}.{field_name}: typing.Annotated[str, Filter()] = ...`",
                )
            if len(field_filters) > 1:
                raise MoreThanOneFilterAnnotationError(
                    f"\nField `{cls.__name__}.{field_name}` must be annotated with exactly one filter.\n"
                    f"Instead, it is annotated with {len(field_filters)} filters.\n"
                    f"If you want to filter by multiple fields, you can combine filters using `|` (or), `&` (and), "
                    f"`~` (not) operators.",
                )
            ret[field_name] = field_filters[0]
        setattr(cls, _FILTERS_FILTERSET_ATTR_NAME, ret)

    @classmethod
    def _is_filter_annotation(cls, annotation: object | type) -> bool:
        """Checks if some the annotation is a Filter annotation (and not for instance pydantic validator)."""
        # The Filter should always be an instance, not a class (i.e., it should be used as `Filter()`, not `Filter`).
        try:
            not_an_instance: bool = issubclass(annotation, FilterInterface)
        except TypeError:
            not_an_instance = False
        if not_an_instance:
            raise FilterFieldNotAnInstanceError(
                f"`{Filter.__name__}` on `{cls.__name__}` must be used as an instance. "
                f"Please use `{annotation.__name__}()` instead.",
            )

        # Can be some other annotation. For example, pydantic validators.
        return isinstance(annotation, FilterInterface)

    @classmethod
    def _check_field_type(cls, field_annotation: type) -> None:
        if field_annotation is type(None):
            # case when the field is annotated as None
            raise FilterFieldTypeNotSupportedError(
                f"`{cls.__name__}` filter annotated as `{field_annotation}` is not supported.",
            )
        if field_annotation is list:
            # case when the field is annotated as a list
            raise FilterFieldTypeNotSupportedError(
                f"`{cls.__name__}` filter annotated as `{field_annotation}` is not supported. You must specify "
                f"the type of the list, for example `list[str]`.",
            )
        field_origin_type = typing.get_origin(field_annotation)  # for example, list[str] -> list; str -> None
        if all(ft is not types.UnionType for ft in [field_annotation, field_origin_type]):
            return

        # If the field type is a union, it must be a union with None (i.e., is Optional).
        # Otherwise, we don't support such a field (at least not at the moment).
        field_union_types = typing.get_args(field_annotation)
        allowed_number_of_union_types: int = 2
        if len(field_union_types) != allowed_number_of_union_types or type(None) not in field_union_types:
            raise FilterFieldTypeNotSupportedError(
                f"`{cls.__name__}` filter annotated as `{field_annotation}` is not supported. "
                f"We do not support complex union types other than `<type> | None`, i.e., optional field.",
            )


# Exceptions
class FilterFieldTypeNotSupportedError(Exception):
    pass


class FilterFieldModelFieldMismatchError(Exception):
    pass


class FilterFieldLookupAmbiguousError(Exception):
    pass


class FilterFieldNotAnInstanceError(Exception):
    pass


@dataclasses.dataclass
class ImproperlyInitializedFilterSetError(Exception):
    filter_set_cls: type[FilterSet]

    def __str__(self) -> str:
        return (
            f"`{self.filter_set_cls.__name__}` is not properly initialized. "
            f"Did you forget to use `@{model_filter.__name__}` decorator on it?"
        )


@dataclasses.dataclass
class ImproperlyInitializedFilterError(Exception):
    filter: Filter

    def __str__(self) -> str:
        return (
            f"`{self.filter}` is not properly initialized. "
            f"Did you forget to use `@{model_filter.__name__}` decorator on its FilterSet?"
        )


class MissingFilterAnnotationError(Exception):
    pass


class MoreThanOneFilterAnnotationError(Exception):
    pass
