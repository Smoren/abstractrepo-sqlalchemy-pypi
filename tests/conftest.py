import pytest

from tests.fixtures.db import TEST_DB


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Настройка базы данных для всей сессии тестов"""
    TEST_DB.create_tables()
    yield
    TEST_DB.drop_tables()


@pytest.fixture(scope="function", autouse=True)
def db_session():
    """Сессия для каждого теста (и для каждого parametrize)"""
    with TEST_DB.session() as session:
        # Начинаем транзакцию
        transaction = session.begin_nested()  # SAVEPOINT для изоляции
        yield session
        # Откатываем транзакцию
        transaction.rollback()
