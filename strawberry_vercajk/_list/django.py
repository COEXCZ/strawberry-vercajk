import typing
import warnings

import django.db.models
import strawberry
from django.core.paginator import UnorderedObjectListWarning

from strawberry_vercajk import Paginator
from strawberry_vercajk._list.processor import BaseListRespHandler

if typing.TYPE_CHECKING:
    from strawberry_vercajk import FilterQ, FilterSet, SortInput


def get_django_filter_q(filter_q: "FilterQ", /) -> django.db.models.Q:
    from strawberry_vercajk import FilterQ

    def _evaluate_filter(fq: "FilterQ") -> django.db.models.Q:
        if fq.is_and:
            return _evaluate_filter(fq.left) & _evaluate_filter(fq.right)
        if fq.is_or:
            return _evaluate_filter(fq.left) | _evaluate_filter(fq.right)
        if fq.is_not:
            q = FilterQ(field=fq.field, lookup=fq.lookup, value=fq.value)
            return ~_evaluate_filter(q)
        if fq.is_noop:
            return django.db.models.Q()
        return django.db.models.Q(**{f"{fq.field}__{fq.lookup}": fq.value})

    return _evaluate_filter(filter_q)


def get_django_order_by(sort: "SortInput", /) -> list[django.db.models.OrderBy]:
    s: list[django.db.models.OrderBy] = []
    for o in sort.ordering:
        f = django.db.models.F(o.field.value)
        if o.nulls == "first":
            f = f.asc(nulls_first=True) if o.direction.is_asc else f.desc(nulls_first=True)
        elif o.nulls == "last":
            f = f.asc(nulls_last=True) if o.direction.is_asc else f.desc(nulls_last=True)
        else:
            f = f.asc() if o.direction.is_asc else f.desc()
        s.append(f)
    return s


class DjangoModelPaginator[T: "django.db.models.Model"](Paginator):
    object_list: django.db.models.QuerySet[T]

    def __init__(
        self,
        object_list: list[T],
        per_page: int,
        orphans: int = 0,
        allow_empty_first_page: bool = True,
    ) -> None:
        super().__init__(object_list, per_page, orphans, allow_empty_first_page)
        self._check_object_list_is_ordered()

    def _check_object_list_is_ordered(self) -> None:
        """
        Warn if self.object_list is unordered (typically a QuerySet).
        """
        ordered = getattr(self.object_list, "ordered", None)
        if ordered is not None and not ordered:
            obj_list_repr = (
                f"{self.object_list.model} {self.object_list.__class__.__name__}"
                if hasattr(self.object_list, "model")
                else f"{self.object_list!r}"
            )
            warnings.warn(
                f"Pagination may yield inconsistent results with an unordered object_list: {obj_list_repr}.",
                UnorderedObjectListWarning,
                stacklevel=3,
            )


class DjangoListResponseHandler[T: "django.db.models.Model"](BaseListRespHandler[T]):
    paginator_cls = DjangoModelPaginator

    @typing.override
    def apply_sorting(
        self,
        items: django.db.models.QuerySet[T],
        sort: "SortInput|None" = strawberry.UNSET,
    ) -> django.db.models.QuerySet[T]:
        if sort is strawberry.UNSET:
            return items
        return items.order_by(*get_django_order_by(sort))

    @typing.override
    def apply_filters(
        self,
        items: django.db.models.QuerySet[T],
        filters: "FilterSet|None" = strawberry.UNSET,
    ) -> django.db.models.QuerySet[T]:
        if filters is strawberry.UNSET:
            return items
        q = get_django_filter_q(filters.get_filter_q())
        return items.filter(q)
