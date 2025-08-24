import asyncio

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session, async_sessionmaker, create_async_engine
from contextlib import contextmanager, asynccontextmanager
from .models import Base


class Database:
    def __init__(self, db_url="sqlite:///:memory:", async_db_url="sqlite+aiosqlite:///:memory:"):
        self.engine = create_engine(db_url, connect_args={"check_same_thread": False})
        self.async_engine = create_async_engine(
            async_db_url,
            connect_args={"check_same_thread": False},
            echo=False
        )

        self._enable_foreign_keys_sync()
        self._enable_foreign_keys_async()

        self.session_factory = sessionmaker(bind=self.engine)
        self.scoped_session = scoped_session(self.session_factory)
        self.async_scoped_session = async_scoped_session(
            async_sessionmaker(
                bind=self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False
            ),
            scopefunc=asyncio.current_task,
        )

    def create_tables(self):
        Base.metadata.create_all(self.engine)

    def drop_tables(self):
        Base.metadata.drop_all(self.engine)

    async def async_create_tables(self):
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def async_drop_tables(self):
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    @contextmanager
    def session(self):
        session = self.scoped_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            self.scoped_session.remove()

    @asynccontextmanager
    async def async_session(self):
        session = self.async_scoped_session()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
            await self.async_scoped_session.remove()

    def _enable_foreign_keys_sync(self):
        """Включение проверки FK для синхронного движка"""

        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    def _enable_foreign_keys_async(self):
        """Включение проверки FK для асинхронного движка"""

        @event.listens_for(self.async_engine.sync_engine, "connect")
        def set_sqlite_pragma_async(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()


TEST_DB = Database()
