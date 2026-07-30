from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import api_router
from app.auth.middleware import SecurityHeadersMiddleware, limiter
# Importing app.auth.jwt (transitively, via app.auth.dependencies -> the auth/me
# endpoints already wired into api_router) loads/validates the RS256 key pair at
# import time and raises RuntimeError immediately if the keys are missing, so a
# misconfigured deployment fails fast at boot rather than on first request.
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(title=settings.PROJECT_NAME, debug=settings.DEBUG)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware order (Starlette applies them outermost-last-added, i.e. the last
# `add_middleware` call wraps everything added before it and therefore runs
# first on the way in / last on the way out):
#   1. CORSMiddleware (innermost) - handles preflight/CORS headers closest to
#      the actual route handling.
#   2. SlowAPIMiddleware - rate-limit bookkeeping/headers.
#   3. SecurityHeadersMiddleware (outermost) - stamps hardening headers on
#      every response, including CORS/rate-limit error responses, so nothing
#      added later can skip them.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def root() -> dict[str, str]:
    return {"project": settings.PROJECT_NAME, "status": "running"}
