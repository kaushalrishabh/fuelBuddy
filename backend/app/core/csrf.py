from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

CSRF_HEADER = "X-FuelBuddy-Client"
MUTATING_METHODS = {"POST", "PUT", "PATCH"}


class CSRFHeaderMiddleware(BaseHTTPMiddleware):
    """Requires a custom header on state-changing requests.

    A cross-site form/script can't set custom headers on a simple request,
    so this blocks CSRF even though the auth cookie is SameSite=None.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method in MUTATING_METHODS and CSRF_HEADER not in request.headers:
            return JSONResponse({"detail": "Missing required client header"}, status_code=403)
        return await call_next(request)
