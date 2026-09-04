"""FastAPI performance middleware."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from energy_core.performance.context import PerformanceContext, clear_performance_context, set_performance_context
from energy_core.performance.logging_context import request_id_var
from energy_core.performance.store import RequestMetric, get_performance_store

logger = logging.getLogger(__name__)


class PerformanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in {"/health", "/api/system/performance"}:
            return await call_next(request)

        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())[:12]
        request_id_var.set(request_id)
        route = request.url.path
        ctx = PerformanceContext(request_id=request_id, route=route)
        set_performance_context(ctx)
        start = time.perf_counter()

        response: Response | None = None
        try:
            response = await call_next(request)
        except BaseException:
            raise
        finally:
            total_ms = (time.perf_counter() - start) * 1000.0
            response_bytes = 0
            if response is not None:
                body = getattr(response, "body", None)
                if isinstance(body, (bytes, bytearray)):
                    response_bytes = len(body)
            metric = RequestMetric(
                request_id=request_id,
                route=route,
                total_ms=total_ms,
                db_ms=ctx.db_ms,
                cache_ms=ctx.cache_ms,
                external_ms=ctx.external_ms,
                calculation_ms=ctx.calculation_ms,
                serialization_ms=ctx.serialization_ms,
                query_count=ctx.query_count,
                response_bytes=response_bytes,
                cache_hit=ctx.cache_hit,
                site_id=ctx.site_id,
                timestamp=time.time(),
            )
            get_performance_store().record_request(metric)
            logger.info(
                "perf requestId=%s route=%s totalMs=%.1f dbMs=%.1f externalMs=%.1f queries=%d cacheHit=%s",
                request_id,
                route,
                total_ms,
                ctx.db_ms,
                ctx.external_ms,
                ctx.query_count,
                ctx.cache_hit,
            )
            clear_performance_context()

        if response is not None:
            response.headers["X-Request-Id"] = request_id
        return response  # type: ignore[return-value]
