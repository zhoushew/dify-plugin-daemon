"""
Main FastAPI application for Dify Plugin Daemon.

This is the main entry point that sets up the FastAPI application,
configures middleware, and starts the server.
"""

import asyncio
import signal
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import uvicorn

from app.config import Config
from app.utils import setup_logging, get_logger, LoggerMiddleware, RecoveryMiddleware
from app.db import init_db_manager, get_db_manager
from app.core import (
    init_redis_manager,
    get_redis_manager,
    init_telemetry,
    init_routine_pool,
    get_routine_pool,
)
from app.api.controllers import (
    health_router,
    collect_active_requests,
    collect_active_dispatch_requests,
)

logger = get_logger(__name__)


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    if _config is None:
        raise RuntimeError("Configuration not initialized")
    return _config


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    
    Handles initialization and cleanup of all resources.
    """
    logger.info("starting dify plugin daemon")

    # Initialize configuration
    global _config
    _config = Config()
    _config.set_default()
    
    try:
        _config.validate()
    except ValueError as e:
        logger.error("invalid configuration", error=str(e))
        raise

    # Initialize logging
    log_closer = setup_logging(
        log_level=_config.log_level,
        log_format=_config.log_output_format,
        log_file=_config.log_file,
    )

    # Initialize routine pool
    routine_pool = init_routine_pool(size=_config.routine_pool_size)
    await routine_pool.init()

    # Initialize database
    db_manager = init_db_manager(_config)
    await db_manager.init()

    # Initialize Redis
    redis_manager = init_redis_manager(_config)
    await redis_manager.init()

    # Initialize OpenTelemetry
    telemetry_shutdown = init_telemetry(_config)

    logger.info(
        "dify plugin daemon started",
        host=_config.server_host,
        port=_config.server_port,
        platform=_config.platform,
    )

    yield

    # Cleanup
    logger.info("shutting down dify plugin daemon")

    # Shutdown routine pool
    await routine_pool.shutdown()

    # Close database connections
    await db_manager.close()

    # Close Redis connections
    await redis_manager.close()

    # Shutdown telemetry
    if telemetry_shutdown:
        telemetry_shutdown()

    # Close log file
    if log_closer:
        log_closer()

    logger.info("dify plugin daemon shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="Dify Plugin Daemon",
        description="Dify Plugin Daemon API - Python implementation",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom middleware
    app.middleware("http")(collect_active_requests)
    
    # Add recovery middleware
    app.add_middleware(RecoveryMiddleware)
    
    # Add logging middleware (skip health check endpoint)
    app.add_middleware(LoggerMiddleware, skip_paths=["/health/check"])

    # Include routers
    app.include_router(health_router)

    # Add 404 handler
    @app.on_event("startup")
    async def startup_event():
        logger.info("application startup complete")

    return app


# Create the application instance
app = create_app()


def main():
    """Main entry point for running the server."""
    import os
    
    # Get config to determine host/port
    config = Config()
    config.set_default()
    
    try:
        config.validate()
    except ValueError as e:
        print(f"Invalid configuration: {e}")
        # Set defaults for startup
        config.server_host = os.getenv("SERVER_HOST", "0.0.0.0")
        config.server_port = int(os.getenv("SERVER_PORT", "5001"))

    uvicorn.run(
        "app.main:app",
        host=config.server_host,
        port=config.server_port,
        reload=False,
        log_level=config.log_level.lower(),
    )


if __name__ == "__main__":
    main()
