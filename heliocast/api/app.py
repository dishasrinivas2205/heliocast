"""
FastAPI Application Entrypoint for HelioCast-L1.
Configures CORS, lifespan logging, OpenAPI metadata, and routes.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from heliocast import __version__
from heliocast.api.routes import router
from heliocast.logging import get_logger

logger = get_logger("heliocast.api.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("HelioCast-L1 Scientific API Server starting up.")
    yield
    logger.info("HelioCast-L1 Scientific API Server shutting down.")


def create_app() -> FastAPI:
    """Create and configure the FastAPI server."""
    app = FastAPI(
        title="HelioCast-L1 Space Weather API",
        description="ISRO Aditya-L1 Solar Flare Nowcasting & Precursor Forecasting REST Services",
        version=__version__,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,   # Must be False when allow_origins=["*"]
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    # Static frontend mounting — serve the cockpit UI
    from fastapi.staticfiles import StaticFiles
    # Try frontend/ first (production build output), fall back to root
    frontend_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
    )
    if os.path.exists(frontend_dir) and os.path.exists(os.path.join(frontend_dir, "index.html")):
        app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
    else:
        # Fallback: serve from project root
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        if os.path.exists(os.path.join(root_dir, "index.html")):
            app.mount("/", StaticFiles(directory=root_dir, html=True), name="frontend")

    return app


app = create_app()
