"""
API controllers for Dify Plugin Daemon.

Provides FastAPI route handlers for health checks, plugin management,
and other endpoints.
"""

import asyncio
from typing import Any
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
import structlog

logger = structlog.get_logger(__name__)

# Global counters for active requests
_active_requests = 0
_active_dispatch_requests = 0
_request_lock = asyncio.Lock()


async def collect_active_requests(request: Request, call_next):
    """Middleware to track active requests."""
    global _active_requests
    async with _request_lock:
        _active_requests += 1
    try:
        response = await call_next(request)
        return response
    finally:
        async with _request_lock:
            _active_requests -= 1


async def collect_active_dispatch_requests(request: Request, call_next):
    """Middleware to track active dispatch requests."""
    global _active_dispatch_requests
    async with _request_lock:
        _active_dispatch_requests += 1
    try:
        response = await call_next(request)
    finally:
        async with _request_lock:
            _active_dispatch_requests -= 1
    return response


def get_active_requests() -> int:
    """Get the number of active requests."""
    return _active_requests


def get_active_dispatch_requests() -> int:
    """Get the number of active dispatch requests."""
    return _active_dispatch_requests


# Health check router
health_router = APIRouter()


@health_router.get("/health/check")
async def health_check(config: Any = None) -> JSONResponse:
    """
    Health check endpoint.
    
    Returns system status including routine pool status, version info,
    platform, and active request counts.
    """
    from app.core.routine_pool import get_routine_status
    
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "pool_status": get_routine_status(),
            "version": "0.1.0",  # Would come from manifest
            "build_time": "unknown",  # Would come from build metadata
            "platform": config.platform if config else "local",
            "active_requests": _active_requests,
            "active_dispatch_requests": _active_dispatch_requests,
        }
    )


# Base controller utilities
class BaseController:
    """Base controller with common utilities."""

    @staticmethod
    def success(data: Any = None, message: str = "success") -> JSONResponse:
        """Return a success response."""
        return JSONResponse(
            status_code=200,
            content={"code": "success", "message": message, "data": data}
        )

    @staticmethod
    def error(message: str, code: str = "error", status_code: int = 400) -> JSONResponse:
        """Return an error response."""
        return JSONResponse(
            status_code=status_code,
            content={"code": code, "message": message}
        )
