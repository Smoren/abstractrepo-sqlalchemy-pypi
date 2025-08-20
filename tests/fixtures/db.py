from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
from .models import Base


class Database:
    def __init__(self, db_url="sqlite:///:memory:"):
        self.engine = create_engine(db_url, connect_args={"check_same_thread": False})
        self.session_factory = sessionmaker(bind=self.engine)
        self.scoped_session = scoped_session(self.session_factory)

    def create_tables(self):
        """Создание таблиц"""
        Base.metadata.create_all(self.engine)

    def drop_tables(self):
        """Удаление таблиц"""
        Base.metadata.drop_all(self.engine)

    @contextmanager
    def session(self):
        """Менеджер контекста для сессии"""
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


# Глобальный экземпляр для тестов
TEST_DB = Database()
