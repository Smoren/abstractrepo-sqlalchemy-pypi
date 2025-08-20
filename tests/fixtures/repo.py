import abc
from typing import Optional, List, Type, Generic, Tuple

from abstractrepo.exceptions import ItemNotFoundException, UniqueViolationException
from abstractrepo.specification import SpecificationInterface, Operator, AttributeSpecification
from abstractrepo.repo import CrudRepositoryInterface, ListBasedCrudRepository, AsyncCrudRepositoryInterface, \
    AsyncListBasedCrudRepository, TUpdateSchema, TCreateSchema, TModel, TIdValueType
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy.orm import Query, Session

from abstractrepo_sqlalchemy.repo import SqlAlchemyCrudRepository, AsyncSqlAlchemyCrudRepository
from abstractrepo_sqlalchemy.types import TDbModel
from tests.fixtures.db import TEST_DB

from tests.fixtures.models import News, NewsCreateForm, NewsUpdateForm, User, UserCreateForm, UserUpdateForm, OrmNews, \
    OrmUser


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
    OrmCrudRepository[OrmNews, News, int, NewsCreateForm, NewsUpdateForm],
    NewsRepositoryInterface,
):
    @property
    def model_class(self) -> Type[News]:
        return News

    def create_default_mock_collection(self, items: List[News]) -> None:
        with self._create_session() as sess:
            for item in items:
                sess.add(OrmNews(id=item.id, title=item.title, text=item.text))
            sess.commit()

    def _get_db_model_class(self) -> type[TDbModel]:
        return OrmNews

    def _create_select_query_by_id(self, item_id: int, sess: Session) -> Query[Type[OrmNews]]:
        return sess.query(OrmNews).filter(OrmNews.id == item_id)

    def _convert_db_item_to_schema(self, db_item: OrmNews) -> TModel:
        return News.model_validate({
            'id': db_item.id,
            'title': db_item.title,
            'text': db_item.text,
        })

    def _create_from_schema(self, form: NewsCreateForm) -> OrmNews:
        return OrmNews(**{
            'title': form.title,
            'text': form.text,
        })

    def _update_from_schema(self, db_item: OrmNews, form: NewsUpdateForm) -> None:
        db_item.title = form.title
        db_item.text = form.text

    def _apply_default_filter(self, query: Query[Type[OrmNews]]) -> Query[Type[OrmNews]]:
        return query

    def _apply_default_order(self, query: Query[Type[OrmNews]]) -> Query[Type[OrmNews]]:
        return query.order_by(OrmNews.id)


class AsyncListBasedNewsRepository(
    AsyncListBasedCrudRepository[News, int, NewsCreateForm, NewsUpdateForm],
    AsyncNewsRepositoryInterface,
):
    _next_id: int

    def __init__(self, items: Optional[List[News]] = None):
        super().__init__(items)
        self._next_id = 0

    @property
    def model_class(self) -> Type[News]:
        return News

    async def _create_model(self, form: NewsCreateForm, new_id: int) -> News:
        return News(
            id=new_id,
            title=form.title,
            text=form.text
        )

    async def _update_model(self, model: News, form: NewsUpdateForm) -> News:
        model.title = form.title
        model.text = form.text
        return model

    async def _generate_id(self) -> int:
        self._next_id += 1
        return self._next_id

    def _get_id_filter_specification(self, item_id: int) -> SpecificationInterface[News, bool]:
        return AttributeSpecification('id', item_id, Operator.E)


class SqlAlchemyUserRepository(
    OrmCrudRepository[OrmUser, User, int, UserCreateForm, UserUpdateForm],
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

    def _get_db_model_class(self) -> Type[OrmUser]:
        return OrmUser

    def _create_select_query_by_id(self, item_id: int, sess: Session) -> Query[Type[OrmUser]]:
        return sess.query(OrmUser).filter(OrmUser.id == item_id)

    def _convert_db_item_to_schema(self, db_item: OrmUser) -> User:
        return User(
            id=db_item.id,
            username=db_item.username,
            password=db_item.password,
            display_name=db_item.display_name,
        )

    def _create_from_schema(self, form: UserCreateForm) -> OrmUser:
        return OrmUser(
            username=form.username,
            password=form.password,
            display_name=form.display_name,
        )

    def _update_from_schema(self, db_item: OrmUser, form: UserUpdateForm) -> None:
        db_item.display_name = form.display_name

    def _apply_default_filter(self, query: Query[Type[OrmUser]]) -> Query[Type[OrmUser]]:
        return query

    def _apply_default_order(self, query: Query[Type[OrmUser]]) -> Query[Type[OrmUser]]:
        return query.order_by(OrmUser.id)


class AsyncSqlAlchemyUserRepository(
    AsyncOrmCrudRepository[OrmUser, User, int, UserCreateForm, UserUpdateForm],
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

    def _get_db_model_class(self) -> Type[OrmUser]:
        return OrmUser

    def _create_select_stmt_by_id(self, item_id: int) -> Select[Tuple[OrmUser]]:
        return Select(OrmNews).where(OrmNews.id == item_id)

    def _convert_db_item_to_schema(self, db_item: OrmUser) -> TModel:
        return User(
            id=db_item.id,
            username=db_item.username,
            password=db_item.password,
            display_name=db_item.display_name,
        )

    def _create_from_schema(self, form: UserCreateForm) -> OrmUser:
        return OrmUser(
            username=form.username,
            password=form.password,
            display_name=form.display_name,
        )

    def _update_from_schema(self, db_item: int, form: UserUpdateForm) -> None:
        db_item.display_name = form.display_name

    def _apply_default_filter(self, stmt: Select[Tuple[OrmUser]]) -> Select[Tuple[OrmUser]]:
        return stmt

    def _apply_default_order(self, stmt: Select[Tuple[OrmUser]]) -> Select[Tuple[OrmUser]]:
        return stmt.order_by(OrmUser.id)
