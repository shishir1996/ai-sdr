from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Optional


ALLOWED_ORIGINS = [
    "https://outreacai.offdx.in",
    "https://ai-sdr-mauve.vercel.app",
    "http://localhost:3000",
]


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, is_production: bool = False, frontend_url: str = "http://localhost:3000"):
        super().__init__(app)
        self.is_production = is_production

    async def dispatch(self, request: Request, call_next) -> Response:
        origin = request.headers.get("origin", "")
        if origin in ALLOWED_ORIGINS:
            if request.method == "OPTIONS":
                response = Response()
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT"
                response.headers["Access-Control-Allow-Headers"] = "content-type,authorization"
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Private-Network"] = "true"
                response.headers["Access-Control-Max-Age"] = "600"
                return response

            response = await call_next(request)
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Private-Network"] = "true"
            response.headers["Access-Control-Expose-Headers"] = "X-Request-ID"
        else:
            response = await call_next(request)

        if self.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
            response.headers["Content-Security-Policy"] = (
                f"default-src 'self'; "
                f"script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                f"style-src 'self' 'unsafe-inline'; "
                f"img-src 'self' data: blob: https:; "
                f"font-src 'self' data:; "
                f"connect-src 'self' https://api.outreacai.offdx.in; "
                f"frame-src 'self'; "
                f"object-src 'none'"
            )
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        else:
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"

        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        return response


def get_cors_origins(is_production: bool, frontend_url: str) -> list[str]:
    return ALLOWED_ORIGINS
