import abc
from typing import List, Type, Generic, Tuple

from abstractrepo.exceptions import ItemNotFoundException
from abstractrepo.specification import AttributeSpecification
from abstractrepo.repo import CrudRepositoryInterface, AsyncCrudRepositoryInterface, \
    TUpdateSchema, TCreateSchema, TModel, TIdValueType
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import Query, Session

from abstractrepo_sqlalchemy.repo import SqlAlchemyCrudRepository, AsyncSqlAlchemyCrudRepository
from abstractrepo_sqlalchemy.types import TDbModel
from tests.fixtures.db import TEST_DB

from tests.fixtures.models import News, NewsCreateForm, NewsUpdateForm, User, UserCreateForm, UserUpdateForm, NewsTable, \
    UserTable


class OrmCrudRepository(
    Generic[TDbModel, TModel, TIdValueType, TCreateSchema, TUpdateSchema],
    SqlAlchemyCrudRepository[TDbModel, TModel, TIdValueType, TCreateSchema, TUpdateSchema],
    abc.ABC,
):
    def _create_session(self) -> Session:
        return TEST_DB.session()


class AsyncOrmCrudRepository(
    Generic[TDbModel, TModel, TIdValueType, TCreateSchema, TUpdateSchema],
    AsyncSqlAlchemyCrudRepository[TDbModel, TModel, TIdValueType, TCreateSchema, TUpdateSchema],
    abc.ABC,
):
    def _create_session(self) -> AsyncSession:
        return TEST_DB.async_session()


class NewsRepositoryInterface(CrudRepositoryInterface[News, int, NewsCreateForm, NewsUpdateForm], abc.ABC):
    pass


class AsyncNewsRepositoryInterface(AsyncCrudRepositoryInterface[News, int, NewsCreateForm, NewsUpdateForm], abc.ABC):
    pass


class UserRepositoryInterface(CrudRepositoryInterface[User, int, UserCreateForm, UserUpdateForm], abc.ABC):
    def get_by_username(self, username: str) -> User:
        raise NotImplementedError()


class AsyncUserRepositoryInterface(AsyncCrudRepositoryInterface[User, int, UserCreateForm, UserUpdateForm], abc.ABC):
    pass


class SqlAlchemyNewsRepository(
    OrmCrudRepository[NewsTable, News, int, NewsCreateForm, NewsUpdateForm],
    NewsRepositoryInterface,
):
    @property
    def model_class(self) -> Type[News]:
        return News

    def create_default_mock_collection(self, items: List[News]) -> None:
        with self._create_session() as sess:
            for item in items:
                sess.add(NewsTable(id=item.id, title=item.title, text=item.text))
            sess.commit()

    @property
    def _db_model_class(self) -> type[NewsTable]:
        return NewsTable

    def _apply_id_filter_condition(self, query: Query[Type[NewsTable]], item_id: int) -> Query[Type[NewsTable]]:
        return query.filter(NewsTable.id == item_id)

    def _convert_db_item_to_model(self, db_item: NewsTable) -> News:
        return News(
            id=db_item.id,
            author_id=db_item.author_id,
            title=db_item.title,
            text=db_item.text,
        )

    def _create_db_item(self, form: NewsCreateForm) -> NewsTable:
        return NewsTable(
            author_id=form.author_id,
            title=form.title,
            text=form.text,
        )

    def _update_db_item(self, db_item: NewsTable, form: NewsUpdateForm) -> None:
        db_item.title = form.title
        db_item.text = form.text

    def _apply_default_filter(self, query: Query[Type[NewsTable]]) -> Query[Type[NewsTable]]:
        return query

    def _apply_default_order(self, query: Query[Type[NewsTable]]) -> Query[Type[NewsTable]]:
        return query.order_by(NewsTable.id)


class AsyncSqlAlchemyNewsRepository(
    AsyncSqlAlchemyCrudRepository[NewsTable, News, int, NewsCreateForm, NewsUpdateForm],
    AsyncNewsRepositoryInterface,
):
    @property
    def model_class(self) -> Type[News]:
        return News

    async def create_default_mock_collection(self, items: List[News]) -> None:
        async with self._create_session() as sess:
            for item in items:
                sess.add(NewsTable(id=item.id, title=item.title, text=item.text))
            await sess.commit()

    def _create_session(self) -> AsyncSession:
        return TEST_DB.async_session()

    @property
    def _db_model_class(self) -> Type[NewsTable]:
        return NewsTable

    def _apply_id_filter_condition(self, stmt: Select[Tuple[TDbModel]], item_id: int) -> Select[Tuple[NewsTable]]:
        return stmt.filter(NewsTable.id == item_id)

    def _convert_db_item_to_model(self, db_item: NewsTable) -> News:
        return News(
            id=db_item.id,
            author_id=db_item.author_id,
            title=db_item.title,
            text=db_item.text,
        )

    def _create_db_item(self, form: NewsCreateForm) -> NewsTable:
        return NewsTable(
            author_id=form.author_id,
            title=form.title,
            text=form.text,
        )

    def _update_db_item(self, db_item: NewsTable, form: NewsUpdateForm) -> None:
        db_item.title = form.title
        db_item.text = form.text

    def _apply_default_filter(self, stmt: Select[Tuple[NewsTable]]) -> Select[Tuple[NewsTable]]:
        return stmt

    def _apply_default_order(self, stmt: Select[Tuple[NewsTable]]) -> Select[Tuple[NewsTable]]:
        return stmt.order_by(NewsTable.id)


class SqlAlchemyUserRepository(
    OrmCrudRepository[UserTable, User, int, UserCreateForm, UserUpdateForm],
    UserRepositoryInterface,
):
    def get_by_username(self, username: str) -> User:
        items = self.get_collection(AttributeSpecification('username', username))
        if len(items) == 0:
            raise ItemNotFoundException(User)

        return items[0]

    @property
    def model_class(self) -> Type[User]:
        return User

    def _username_exists(self, username: str) -> bool:
        return self.count(AttributeSpecification('username', username)) > 0

    @property
    def _db_model_class(self) -> Type[UserTable]:
        return UserTable

    def _apply_id_filter_condition(self, query: Query[Type[UserTable]], item_id: int) -> Query[Type[UserTable]]:
        return query.filter(UserTable.id == item_id)

    def _convert_db_item_to_model(self, db_item: UserTable) -> User:
        return User(
            id=db_item.id,
            username=db_item.username,
            password=db_item.password,
            display_name=db_item.display_name,
        )

    def _create_db_item(self, form: UserCreateForm) -> UserTable:
        return UserTable(
            username=form.username,
            password=form.password,
            display_name=form.display_name,
        )

    def _update_db_item(self, db_item: UserTable, form: UserUpdateForm) -> None:
        if form.display_name is not None:
            db_item.display_name = form.display_name
        if form.username is not None:
            db_item.username = form.username

    def _apply_default_filter(self, query: Query[Type[UserTable]]) -> Query[Type[UserTable]]:
        return query

    def _apply_default_order(self, query: Query[Type[UserTable]]) -> Query[Type[UserTable]]:
        return query.order_by(UserTable.id)


class AsyncSqlAlchemyUserRepository(
    AsyncOrmCrudRepository[UserTable, User, int, UserCreateForm, UserUpdateForm],
    AsyncUserRepositoryInterface,
):
    async def get_by_username(self, username: str) -> User:
        items = await self.get_collection(AttributeSpecification('username', username))
        if len(items) == 0:
            raise ItemNotFoundException(User)

        return items[0]

    @property
    def model_class(self) -> Type[User]:
        return User

    async def _username_exists(self, username: str) -> bool:
        count = await self.count(AttributeSpecification('username', username))
        return count > 0

    @property
    def _db_model_class(self) -> Type[UserTable]:
        return UserTable

    def _apply_id_filter_condition(self, stmt: Select[Tuple[UserTable]], item_id: int) -> Select[Tuple[UserTable]]:
        return stmt.where(UserTable.id == item_id)

    def _convert_db_item_to_model(self, db_item: UserTable) -> User:
        return User(
            id=db_item.id,
            username=db_item.username,
            password=db_item.password,
            display_name=db_item.display_name,
        )

    def _create_db_item(self, form: UserCreateForm) -> UserTable:
        return UserTable(
            username=form.username,
            password=form.password,
            display_name=form.display_name,
        )

    def _update_db_item(self, db_item: int, form: UserUpdateForm) -> None:
        if form.display_name is not None:
            db_item.display_name = form.display_name
        if form.username is not None:
            db_item.username = form.username

    def _apply_default_filter(self, stmt: Select[Tuple[UserTable]]) -> Select[Tuple[UserTable]]:
        return stmt

    def _apply_default_order(self, stmt: Select[Tuple[UserTable]]) -> Select[Tuple[UserTable]]:
        return stmt.order_by(UserTable.id)
