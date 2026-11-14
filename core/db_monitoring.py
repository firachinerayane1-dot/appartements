"""Time database executions without retaining SQL or user parameters."""
from contextlib import ExitStack
from hashlib import sha256
import logging
from time import perf_counter

from django.conf import settings
from django.db import connections

logger = logging.getLogger('core.slow_queries')


class SlowQueryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        threshold = settings.DB_SLOW_QUERY_MS
        if threshold <= 0:
            return self.get_response(request)

        def measure(execute, sql, params, many, context):
            start = perf_counter()
            try:
                return execute(sql, params, many, context)
            finally:
                duration = (perf_counter() - start) * 1000
                if duration >= threshold:
                    match = getattr(request, 'resolver_match', None)
                    logger.warning(
                        'Slow query database=%s view=%s duration_ms=%.2f fingerprint=%s',
                        context['connection'].alias,
                        getattr(match, 'view_name', None) or 'unresolved',
                        duration, sha256(sql.encode()).hexdigest()[:16],
                    )

        with ExitStack() as stack:
            for connection in connections.all():
                stack.enter_context(connection.execute_wrapper(measure))
            return self.get_response(request)
