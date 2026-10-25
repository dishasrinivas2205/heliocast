"""
FastAPI Application Entrypoint for HelioCast-L1.
Configures CORS, lifespan logging, OpenAPI metadata, and routes.
"""

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
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    # Static frontend mounting (Aether Deep Field Solar Observatory)
    import os
    from fastapi.staticfiles import StaticFiles
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
    if os.path.exists(frontend_dir):
        app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    return app


app = create_app()
