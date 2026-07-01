from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # Enforce HTTPS
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent Clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy - restrict browser features to self or none
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(self)"

        # Content Security Policy (compatible with Google OAuth, Google Fonts, and Google Analytics)
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://accounts.google.com https://apis.google.com https://*.googletagmanager.com https://*.google-analytics.com; "
            "style-src 'self' 'unsafe-inline' https://accounts.google.com https://fonts.googleapis.com; "
            "font-src 'self' data: https://fonts.gstatic.com; "
            "img-src 'self' data: blob: https://*.googleapis.com https://*.googleusercontent.com https://*.google-analytics.com https://*.analytics.google.com; "
            "connect-src 'self' https://accounts.google.com https://oauth2.googleapis.com https://*.google-analytics.com https://*.analytics.google.com https://*.googletagmanager.com; "
            "frame-src https://accounts.google.com;"
        )
        response.headers["Content-Security-Policy"] = csp

        return response
