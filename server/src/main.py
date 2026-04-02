from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .auth.router import router as auth_router
from .constants import API_DESCRIPTION, API_TITLE, API_VERSION, ENABLE_DEBUG, ORIGIN_URL, PORT
from .database import get_session, init_db
from .logging_config import setup_logging
from .middleware.rate_limit import RATE_LIMIT_ENABLED, limiter
from .middleware.request_log import RequestLoggingMiddleware
from .middleware.security_headers import SecurityHeadersMiddleware
from .routers import analytics, classes, config, ingestion, ml, open_day, students, subjects, teachers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and create default admin on startup."""
    setup_logging()
    init_db()

    # Ensure at least one admin user exists
    from .auth.service import AuthService
    with next(get_session()) as session:
        AuthService(session).ensure_default_admin()
        AuthService(session).ensure_rbac_seed()

    yield


app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    lifespan=lifespan,
    # Disable auto-generated docs in non-debug mode
    docs_url="/docs" if ENABLE_DEBUG else None,
    redoc_url="/redoc" if ENABLE_DEBUG else None,
    openapi_url="/openapi.json" if ENABLE_DEBUG else None,
)

# Rate limiting (disabled via RATE_LIMIT_ENABLED=false in test environments)
if RATE_LIMIT_ENABLED:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

# Security headers (add first so every response gets them)
app.add_middleware(SecurityHeadersMiddleware)

# Request logging
app.add_middleware(RequestLoggingMiddleware)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ORIGIN_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(auth_router)

# Application routers
app.include_router(config.router)
app.include_router(ingestion.router)
app.include_router(classes.router)
app.include_router(teachers.router)
app.include_router(students.router)
app.include_router(analytics.router)
app.include_router(subjects.router)
app.include_router(open_day.router)
app.include_router(ml.router)

if ENABLE_DEBUG:
    from .routers import debug
    app.include_router(debug.router)


@app.get("/")
async def root():
    return {"message": API_TITLE}


@app.get("/health")
async def health():
    return {"status": "ok"}


def main():
    # bind all interfaces for containerized runtime.
    uvicorn.run(app, host="0.0.0.0", port=PORT)  # nosec B104


if __name__ == "__main__":
    main()
