import typing

import django.db.models
import strawberry

from strawberry_vercajk._list.processor import BaseListRespHandler

if typing.TYPE_CHECKING:
    from strawberry_vercajk import FilterQ, FilterSet, SortInput


def get_django_filter_q(filter_q: "FilterQ", /) -> django.db.models.Q:
    def _evaluate_filter(fq: "FilterQ") -> django.db.models.Q:
        if fq.is_and:
            return _evaluate_filter(fq.left) & _evaluate_filter(fq.right)
        if fq.is_or:
            return _evaluate_filter(fq.left) | _evaluate_filter(fq.right)
        if fq.is_not:
            return ~_evaluate_filter(fq.left)
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


class DjangoListResponseHandler[T: "django.db.models.Model"](BaseListRespHandler[T]):
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
