import collections.abc
import functools
import inspect
import typing
from math import ceil

from strawberry_vercajk._base.utils import func_has_no_args

__all__ = [
    "Page",
    "Paginator",
]


class Paginator[T]:
    object_list: list[T]

    def __init__(
        self,
        object_list: list[T],
        per_page: int,
        orphans: int = 0,
        allow_empty_first_page: bool = True,
    ) -> None:
        self.object_list = object_list
        self.per_page = int(per_page)
        self.orphans = int(orphans)
        self.allow_empty_first_page = allow_empty_first_page

    def __iter__(self) -> typing.Iterator["Page[T]"]:
        for page_number in self.page_range:
            yield self.page(page_number)

    def get_page(self, number: int) -> "Page[T]":
        number = self.validate_number(number)
        return self.page(number)

    def _get_page(self, *args: typing.Any, **kwargs: typing.Any) -> "Page[T]":  # noqa: ANN401
        return Page(*args, **kwargs)

    def validate_number(self, number: int) -> int:
        # the default implementation makes a db query to check for total count - we don't want that
        return number

    def page(self, number: int) -> "Page[T]":
        """
        Returns a Page object for the given 1-based page number. (Mostly taken from Django's Paginator)
        """
        number = self.validate_number(number)
        bottom = (number - 1) * self.per_page
        top = bottom + self.per_page
        top = min(top, self.count)
        return self._get_page(
            self.object_list[bottom:top],
            number,
            self,
        )

    @functools.cached_property
    def count(self) -> int:
        """Return the total number of objects, across all pages."""
        c = getattr(self.object_list, "count", None)
        if callable(c) and not inspect.isbuiltin(c) and func_has_no_args(c):
            return c()
        return len(self.object_list)

    @property
    def page_range(self) -> range:
        """
        Return a 1-based range of pages for iterating through within
        a template for loop.
        """
        return range(1, self.num_pages + 1)

    @functools.cached_property
    def num_pages(self) -> int:
        """Return the total number of pages."""
        if self.count == 0 and not self.allow_empty_first_page:
            return 0
        hits = max(1, self.count - self.orphans)
        return ceil(hits / self.per_page)


class Page[T](collections.abc.Sequence):
    """
    Page class copied mostly from Django
    """

    number: int
    paginator: Paginator[T]
    object_list: list[T]

    def __init__(self, object_list: list[T], number: int, paginator: Paginator[T]) -> None:
        self.object_list = object_list
        self.number = number
        self.paginator = paginator

    def __repr__(self) -> str:
        return f"<Page {self.number}>"

    def __len__(self) -> int:
        return len(self.object_list)

    def __getitem__(self, index: int | slice) -> T:
        if not isinstance(index, (int, slice)):
            raise TypeError(
                f"Page indices must be integers or slices, not {type(index).__name__}.",
            )
        # The object_list is converted to a list so that if it was a QuerySet
        # it won't be a database hit per __getitem__.
        if not isinstance(self.object_list, list):
            self.object_list = list(self.object_list)
        return self.object_list[index]

    def has_next(self) -> bool:
        return self.number < self.paginator.num_pages

    def has_previous(self) -> bool:
        return self.number > 1

    def has_other_pages(self) -> bool:
        return self.has_previous() or self.has_next()

    def next_page_number(self) -> int:
        return self.paginator.validate_number(self.number + 1)

    def previous_page_number(self) -> int:
        return self.paginator.validate_number(self.number - 1)

    def start_index(self) -> int:
        """
        Return the 1-based index of the first object on this page,
        relative to total objects in the paginator.
        """
        # Special case, return zero if no items.
        if self.paginator.count == 0:
            return 0
        return (self.paginator.per_page * (self.number - 1)) + 1

    def end_index(self) -> int:
        """
        Return the 1-based index of the last object on this page,
        relative to total objects found (hits).
        """
        # Special case for the last page because there can be orphans.
        if self.number == self.paginator.num_pages:
            return self.paginator.count
        return self.number * self.paginator.per_page

    @functools.cached_property
    def items_count(self) -> int:
        """Return the count of objects in total - not only on this page."""
        return self.paginator.count
