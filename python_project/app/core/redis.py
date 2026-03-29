"""
Redis utilities for Dify Plugin Daemon.

Provides async Redis connection management with support for sentinel and SSL.
"""

from typing import Optional, Any
import structlog
import redis.asyncio as redis
from redis.asyncio.sentinel import Sentinel

logger = structlog.get_logger(__name__)


class RedisManager:
    """Manages async Redis connections."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        password: Optional[str] = None,
        username: Optional[str] = None,
        db: int = 0,
        use_ssl: bool = False,
        ssl_cert_reqs: Optional[str] = None,
        ssl_ca_certs: Optional[str] = None,
        # Sentinel configuration
        use_sentinel: bool = False,
        sentinels: Optional[str] = None,
        sentinel_service_name: Optional[str] = None,
        sentinel_username: Optional[str] = None,
        sentinel_password: Optional[str] = None,
        sentinel_socket_timeout: Optional[float] = None,
    ):
        self.host = host
        self.port = port
        self.password = password
        self.username = username
        self.db = db
        self.use_ssl = use_ssl
        self.ssl_cert_reqs = ssl_cert_reqs
        self.ssl_ca_certs = ssl_ca_certs

        self.use_sentinel = use_sentinel
        self.sentinels_str = sentinels
        self.sentinel_service_name = sentinel_service_name
        self.sentinel_username = sentinel_username
        self.sentinel_password = sentinel_password
        self.sentinel_socket_timeout = sentinel_socket_timeout

        self.client: Optional[redis.Redis] = None
        self.sentinel: Optional[Sentinel] = None

    def _parse_sentinels(self) -> list[tuple[str, int]]:
        """Parse sentinels string into list of (host, port) tuples."""
        if not self.sentinels_str:
            return []
        
        result = []
        for item in self.sentinels_str.split(","):
            item = item.strip()
            if ":" in item:
                host, port = item.rsplit(":", 1)
                result.append((host, int(port)))
            else:
                logger.warning(f"invalid sentinel format: {item}, expected host:port")
        return result

    async def init(self) -> None:
        """Initialize the Redis client."""
        logger.info("initializing redis connection", use_sentinel=self.use_sentinel)

        if self.use_sentinel:
            # Use Redis Sentinel
            sentinels = self._parse_sentinels()
            if not sentinels:
                raise ValueError("No sentinels configured")

            self.sentinel = Sentinel(
                sentinels,
                socket_timeout=self.sentinel_socket_timeout or 0.1,
                password=self.sentinel_password,
                username=self.sentinel_username,
            )
            self.client = self.sentinel.master_for(
                self.sentinel_service_name or "mymaster",
                socket_timeout=0.1,
                password=self.password,
                username=self.username,
                db=self.db,
            )
        else:
            # Direct connection
            ssl_kwargs = {}
            if self.use_ssl:
                ssl_kwargs["ssl"] = True
                if self.ssl_cert_reqs:
                    ssl_kwargs["ssl_cert_reqs"] = self.ssl_cert_reqs
                if self.ssl_ca_certs:
                    ssl_kwargs["ssl_ca_certs"] = self.ssl_ca_certs

            self.client = redis.Redis(
                host=self.host or "localhost",
                port=self.port or 6379,
                password=self.password,
                username=self.username,
                db=self.db,
                **ssl_kwargs,
            )

        # Test connection
        try:
            await self.client.ping()
            logger.info("redis connection established successfully")
        except Exception as e:
            logger.error("failed to connect to redis", error=str(e))
            raise

    async def close(self) -> None:
        """Close the Redis connection."""
        if self.client:
            await self.client.close()
            logger.info("redis connection closed")

    def get_client(self) -> redis.Redis:
        """Get the Redis client instance."""
        if not self.client:
            raise RuntimeError("Redis not initialized. Call init() first.")
        return self.client


# Global Redis manager instance
_redis_manager: Optional[RedisManager] = None


def get_redis_manager() -> RedisManager:
    """Get the global Redis manager instance."""
    if _redis_manager is None:
        raise RuntimeError("Redis manager not initialized")
    return _redis_manager


def init_redis_manager(config) -> RedisManager:
    """Initialize the global Redis manager."""
    global _redis_manager
    _redis_manager = RedisManager(
        host=config.redis_host,
        port=config.redis_port,
        password=config.redis_password,
        username=config.redis_username,
        db=config.redis_db,
        use_ssl=config.redis_use_ssl,
        ssl_cert_reqs=config.redis_ssl_cert_reqs,
        ssl_ca_certs=config.redis_ssl_ca_certs,
        use_sentinel=config.redis_use_sentinel,
        sentinels=config.redis_sentinels,
        sentinel_service_name=config.redis_sentinel_service_name,
        sentinel_username=config.redis_sentinel_username,
        sentinel_password=config.redis_sentinel_password,
        sentinel_socket_timeout=config.redis_sentinel_socket_timeout,
    )
    return _redis_manager
