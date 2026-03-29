"""
Database utilities for Dify Plugin Daemon.

Provides async database connection management using SQLAlchemy with support
for PostgreSQL and MySQL databases.
"""

from typing import Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine,
    async_scoped_session,
)
from sqlalchemy.pool import NullPool
import structlog

logger = structlog.get_logger(__name__)


class DatabaseManager:
    """Manages async database connections and sessions."""

    def __init__(
        self,
        db_type: str,
        username: str,
        password: str,
        host: str,
        port: int,
        database: str,
        ssl_mode: str = "disable",
        max_idle_conns: int = 10,
        max_open_conns: int = 100,
        conn_max_lifetime: int = 3600,
        conn_max_idle_time: int = 1800,
    ):
        self.db_type = db_type
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.database = database
        self.ssl_mode = ssl_mode
        self.max_idle_conns = max_idle_conns
        self.max_open_conns = max_open_conns
        self.conn_max_lifetime = conn_max_lifetime
        self.conn_max_idle_time = conn_max_idle_time

        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self.db_url: Optional[str] = None

    def _build_connection_string(self) -> str:
        """Build the database connection string."""
        if self.db_type in ["postgresql", "pgbouncer"]:
            driver = "asyncpg"
            base_url = f"postgresql+{driver}://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
            if self.ssl_mode == "require":
                base_url += "?ssl=require"
            else:
                base_url += "?ssl=disable"
            return base_url
        elif self.db_type in ["mysql", "oceanbase", "seekdb"]:
            driver = "aiomysql"
            return f"mysql+{driver}://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")

    async def init(self) -> None:
        """Initialize the database engine and session factory."""
        self.db_url = self._build_connection_string()
        logger.info("initializing database connection", db_type=self.db_type, host=self.host, port=self.port)

        # Configure pool settings based on database type
        if self.db_type == "pgbouncer":
            # PgBouncer doesn't support prepared statements well
            self.engine = create_async_engine(
                self.db_url,
                poolclass=NullPool,
                echo=False,
                future=True,
            )
        else:
            from sqlalchemy.pool import QueuePool
            self.engine = create_async_engine(
                self.db_url,
                poolclass=QueuePool,
                pool_size=self.max_idle_conns,
                max_overflow=self.max_open_conns - self.max_idle_conns,
                pool_recycle=self.conn_max_lifetime,
                pool_pre_ping=True,
                echo=False,
                future=True,
            )

        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        logger.info("database connection initialized successfully")

    async def close(self) -> None:
        """Close the database engine."""
        if self.engine:
            await self.engine.dispose()
            logger.info("database connection closed")

    def get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get the session factory."""
        if not self.session_factory:
            raise RuntimeError("Database not initialized. Call init() first.")
        return self.session_factory

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session for dependency injection."""
        if not self.session_factory:
            raise RuntimeError("Database not initialized. Call init() first.")

        session = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    if _db_manager is None:
        raise RuntimeError("Database manager not initialized")
    return _db_manager


def init_db_manager(config) -> DatabaseManager:
    """Initialize the global database manager."""
    global _db_manager
    _db_manager = DatabaseManager(
        db_type=config.db_type,
        username=config.db_username,
        password=config.db_password,
        host=config.db_host,
        port=config.db_port,
        database=config.db_database,
        ssl_mode=config.db_ssl_mode,
        max_idle_conns=config.db_max_idle_conns,
        max_open_conns=config.db_max_open_conns,
        conn_max_lifetime=config.db_conn_max_lifetime,
        conn_max_idle_time=config.db_conn_max_idle_time,
    )
    return _db_manager
