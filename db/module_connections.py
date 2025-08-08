"""
Modular Database Connection System

Provides efficient, shared database connections for bot modules while
minimizing memory usage through connection pooling and resource sharing.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator, Dict, Any, Set
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text

from .config import get_database_config, DatabaseConfig


logger = logging.getLogger(__name__)


class SharedConnectionPool:
    """
    Shared connection pool that minimizes memory usage across modules.
    """
    
    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
        self._config: Optional[DatabaseConfig] = None
        self._connected_modules: Set[str] = set()
        self._reference_count = 0
        self._lock = asyncio.Lock()
        
    async def get_engine(self, module_name: str) -> AsyncEngine:
        """Get shared engine instance, creating if needed."""
        async with self._lock:
            if self._engine is None:
                await self._initialize()
            
            self._connected_modules.add(module_name)
            self._reference_count += 1
            logger.debug(f"Module {module_name} connected. Active modules: {len(self._connected_modules)}")
            
            return self._engine
    
    async def get_session_factory(self, module_name: str) -> async_sessionmaker:
        """Get shared session factory."""
        async with self._lock:
            if self._session_factory is None:
                await self._initialize()
            
            return self._session_factory
    
    async def release_module(self, module_name: str) -> None:
        """Release module's connection resources."""
        async with self._lock:
            if module_name in self._connected_modules:
                self._connected_modules.remove(module_name)
                self._reference_count -= 1
                logger.debug(f"Module {module_name} disconnected. Active modules: {len(self._connected_modules)}")
                
                # If no modules are using the pool, clean up
                if self._reference_count <= 0:
                    await self._cleanup()
    
    async def _initialize(self) -> None:
        """Initialize shared database resources."""
        if self._engine is not None:
            return
            
        self._config = get_database_config()
        
        # Create shared engine with optimized pool settings
        self._engine = create_async_engine(
            self._config.database_url,
            pool_size=self._config.db_pool_size,
            max_overflow=self._config.db_max_overflow,
            pool_timeout=30,
            pool_recycle=3600,  # Recycle connections every hour
            echo=False,
        )
        
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        # Test connection
        async with self._engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        logger.info("Shared database connection pool initialized")
    
    async def _cleanup(self) -> None:
        """Cleanup shared resources when no modules are using them."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Shared database connection pool cleaned up")
    
    async def health_check(self) -> bool:
        """Check health of shared connection pool."""
        if self._engine is None:
            return False
            
        try:
            async with self._engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Shared pool health check failed: {e}")
            return False


# Global shared connection pool
_shared_pool = SharedConnectionPool()


class ModuleDatabaseManager:
    """
    Database manager for individual bot modules.
    Uses shared connection pool to minimize memory usage.
    """
    
    def __init__(self, module_name: str):
        self.module_name = module_name
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
        self._is_connected = False
        
    async def setup(self) -> None:
        """Setup module's database connection using shared pool."""
        if self._is_connected:
            return
            
        try:
            self._engine = await _shared_pool.get_engine(self.module_name)
            self._session_factory = await _shared_pool.get_session_factory(self.module_name)
            self._is_connected = True
            
            logger.info(f"Database connection established for module: {self.module_name}")
            
        except Exception as e:
            logger.error(f"Failed to setup database for module {self.module_name}: {e}")
            raise
    
    async def cleanup(self) -> None:
        """Cleanup module's database resources."""
        if self._is_connected:
            await _shared_pool.release_module(self.module_name)
            self._engine = None
            self._session_factory = None
            self._is_connected = False
            
            logger.info(f"Database connection cleaned up for module: {self.module_name}")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session for the module."""
        if not self._is_connected:
            await self.setup()
            
        if self._session_factory is None:
            raise RuntimeError(f"Database not initialized for module: {self.module_name}")
        
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    async def health_check(self) -> bool:
        """Check health of module's database connection."""
        return await _shared_pool.health_check()
    
    async def get_database_info(self) -> Dict[str, Any]:
        """
        Get database information and statistics.
        
        Returns:
            Dict containing database info
        """
        try:
            async with self.get_session() as session:
                # Get basic database info
                version_result = await session.execute(text("SELECT version()"))
                version = version_result.scalar()
                
                # Get connection count
                conn_result = await session.execute(text("""
                    SELECT count(*) as connection_count 
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                """))
                connection_count = conn_result.scalar()
                
                # Get database size
                size_result = await session.execute(text("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as db_size
                """))
                db_size = size_result.scalar()
                
                # Get config from shared pool
                config = _shared_pool._config
                
                return {
                    "version": version,
                    "connection_count": connection_count,
                    "database_size": db_size,
                    "database_name": config.db_name if config else "unknown",
                    "host": config.db_host if config else "unknown",
                    "port": config.db_port if config else "unknown",
                    "pool_size": config.db_pool_size if config else "unknown",
                    "max_overflow": config.db_max_overflow if config else "unknown",
                    "module_name": self.module_name,
                }
                
        except Exception as e:
            logger.error(f"Failed to get database info for module {self.module_name}: {e}")
            return {"error": str(e), "module_name": self.module_name}
    
    @property
    def is_connected(self) -> bool:
        """Check if module is connected to database."""
        return self._is_connected
    
    @property
    def engine(self) -> Optional[AsyncEngine]:
        """Get the shared engine instance."""
        return self._engine


async def get_module_database_manager(module_name: str) -> ModuleDatabaseManager:
    """
    Get a database manager for a specific module.
    
    This is the main entry point for modules to get database access.
    """
    manager = ModuleDatabaseManager(module_name)
    await manager.setup()
    return manager


# Module managers cache (using weak references to allow garbage collection)
_module_managers: Dict[str, ModuleDatabaseManager] = {}


def get_cached_module_manager(module_name: str) -> Optional[ModuleDatabaseManager]:
    """Get cached module manager if it exists."""
    return _module_managers.get(module_name)


async def get_or_create_module_manager(module_name: str) -> ModuleDatabaseManager:
    """Get existing or create new module manager."""
    if module_name in _module_managers:
        manager = _module_managers[module_name]
        if manager.is_connected:
            return manager
    
    # Create new manager
    manager = await get_module_database_manager(module_name)
    _module_managers[module_name] = manager
    return manager


async def cleanup_all_modules() -> None:
    """Cleanup all module database connections."""
    for manager in _module_managers.values():
        await manager.cleanup()
    
    _module_managers.clear()
    logger.info("All module database connections cleaned up")
