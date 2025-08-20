import pytest
import pytest_asyncio

from tests.fixtures.db import TEST_DB
from tests.fixtures.models import Base


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    TEST_DB.create_tables()
    yield
    TEST_DB.drop_tables()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_async_database():
    await TEST_DB.async_create_tables()
    yield
    await TEST_DB.async_drop_tables()


@pytest.fixture(scope="function", autouse=True)
def db_session():
    with TEST_DB.session() as session:
        yield
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def async_db_session():
    async with TEST_DB.async_session() as session:
        yield
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()
