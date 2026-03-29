"""
Routine pool for managing concurrent task execution.

Provides a configurable pool of worker routines similar to Go's goroutine pools,
using Python's asyncio for async concurrency.
"""

import asyncio
from typing import Optional, Callable, Any, Coroutine
from dataclasses import dataclass, field
import structlog
import time

logger = structlog.get_logger(__name__)


@dataclass
class RoutineStats:
    """Statistics for the routine pool."""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    active_tasks: int = 0
    queue_size: int = 0
    avg_execution_time_ms: float = 0.0


class RoutinePool:
    """
    Async routine pool for managing concurrent task execution.
    
    Similar to Go's goroutine pools (like ants), this manages a fixed number
    of worker coroutines that process tasks from a queue.
    """

    def __init__(self, size: int = 100):
        self.size = size
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._stats = RoutineStats()
        self._execution_times: list[float] = []
        self._max_execution_times = 1000
        self._running = False
        self._lock = asyncio.Lock()

    async def init(self) -> None:
        """Initialize the routine pool."""
        self._semaphore = asyncio.Semaphore(self.size)
        self._running = True
        logger.info("routine pool initialized", size=self.size)

    async def shutdown(self) -> None:
        """Shutdown the routine pool."""
        self._running = False
        logger.info("routine pool shutdown")

    async def submit(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        *args,
        **kwargs,
    ) -> Any:
        """
        Submit a task to the pool.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the function execution
        """
        if not self._running:
            raise RuntimeError("Routine pool is not running")

        async with self._semaphore:
            async with self._lock:
                self._stats.active_tasks += 1
                self._stats.total_tasks += 1

            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                
                elapsed_ms = (time.time() - start_time) * 1000
                self._update_stats(success=True, execution_time_ms=elapsed_ms)
                
                return result
            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                self._update_stats(success=False, execution_time_ms=elapsed_ms)
                logger.error("task failed in routine pool", error=str(e), exc_info=e)
                raise
            finally:
                async with self._lock:
                    self._stats.active_tasks -= 1

    def _update_stats(self, success: bool, execution_time_ms: float) -> None:
        """Update pool statistics."""
        if success:
            self._stats.completed_tasks += 1
        else:
            self._stats.failed_tasks += 1

        # Track execution times for average calculation
        self._execution_times.append(execution_time_ms)
        if len(self._execution_times) > self._max_execution_times:
            self._execution_times.pop(0)

        # Update average
        if self._execution_times:
            self._stats.avg_execution_time_ms = sum(self._execution_times) / len(self._execution_times)

    def get_stats(self) -> RoutineStats:
        """Get current pool statistics."""
        return self._stats

    @property
    def available_slots(self) -> int:
        """Get the number of available slots in the pool."""
        if not self._semaphore:
            return 0
        return self._semaphore._value


# Global routine pool instance
_routine_pool: Optional[RoutinePool] = None


def get_routine_pool() -> RoutinePool:
    """Get the global routine pool instance."""
    if _routine_pool is None:
        raise RuntimeError("Routine pool not initialized")
    return _routine_pool


def init_routine_pool(size: int = 100) -> RoutinePool:
    """Initialize the global routine pool."""
    global _routine_pool
    _routine_pool = RoutinePool(size=size)
    return _routine_pool


def get_routine_status() -> dict[str, Any]:
    """Get routine pool status as a dictionary."""
    if _routine_pool is None:
        return {"status": "not_initialized"}
    
    stats = _routine_pool.get_stats()
    return {
        "size": _routine_pool.size,
        "available_slots": _routine_pool.available_slots,
        "total_tasks": stats.total_tasks,
        "completed_tasks": stats.completed_tasks,
        "failed_tasks": stats.failed_tasks,
        "active_tasks": stats.active_tasks,
        "avg_execution_time_ms": round(stats.avg_execution_time_ms, 2),
        "running": _routine_pool._running,
    }
