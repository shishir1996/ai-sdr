from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Optional


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, is_production: bool = False, frontend_url: str = "http://localhost:3000"):
        super().__init__(app)
        self.is_production = is_production
        self.frontend_url = frontend_url.rstrip("/")

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        if self.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
            response.headers["Content-Security-Policy"] = (
                f"default-src 'self'; "
                f"script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                f"style-src 'self' 'unsafe-inline'; "
                f"img-src 'self' data: blob: https:; "
                f"font-src 'self' data:; "
                f"connect-src 'self' {self.frontend_url}; "
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
    frontend_url = frontend_url.rstrip("/")
    if is_production:
        return [
            frontend_url,
            frontend_url.replace("https://", "https://api."),
            "http://localhost:3000",
        ]
    return [frontend_url, "http://localhost:3000"]
