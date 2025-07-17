try:
    import django
except ImportError:
    raise RuntimeError(
        "Django support in strawberry-vercajk requires the 'django' extra: pip install strawberry-vercajk[django]"
    )

from strawberry_vercajk._list.django import DjangoListResponseHandler
from strawberry_vercajk._base.query_logger import QueryLogger
