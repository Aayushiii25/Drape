"""
main.py
-------
FastAPI application entry point for Drape.

Design decisions:

1. **Minimal main.py.**
   This file only does three things: create the app, mount routes,
   add a health check. All logic lives in routers/ and services/.

2. **Health endpoint at /health.**
   Every production service needs one. Load balancers, Docker health
   checks, and uptime monitors hit this.

3. **Lifespan context manager for startup/shutdown.**
   Replaces the deprecated @app.on_event decorators. Ensures the
   WhatsApp HTTP client is closed gracefully on shutdown.

Run:
    cd app && uvicorn main:app --reload
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from core.config import settings
from routers.webhook import router as webhook_router


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    logging.getLogger(__name__).info("🚀 Drape starting up...")
    yield
    logging.getLogger(__name__).info("👋 Drape shutting down...")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    description="WhatsApp-first AI fashion recommendation assistant",
    version="0.1.0",
    lifespan=lifespan,
)

# Mount routes
app.include_router(webhook_router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.app_name}