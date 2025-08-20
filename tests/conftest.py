import pytest

from tests.fixtures.db import TEST_DB
from tests.fixtures.models import Base


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    TEST_DB.create_tables()
    yield
    TEST_DB.drop_tables()


@pytest.fixture(scope="function", autouse=True)
def db_session():
    with TEST_DB.session() as session:
        yield
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
