import abc
from typing import Optional, List, Type, Generic

from abstractrepo.exceptions import ItemNotFoundException, UniqueViolationException
from abstractrepo.specification import SpecificationInterface, Operator, AttributeSpecification
from abstractrepo.repo import CrudRepositoryInterface, ListBasedCrudRepository, AsyncCrudRepositoryInterface, \
    AsyncListBasedCrudRepository, TUpdateSchema, TCreateSchema, TModel, TIdValueType

from sqlalchemy.orm import Query, Session

from abstractrepo_sqlalchemy.repo import SqlAlchemyCrudRepository
from abstractrepo_sqlalchemy.types import TDbModel
from tests.fixtures.db import TEST_DB

from tests.fixtures.models import News, NewsCreateForm, NewsUpdateForm, User, UserCreateForm, UserUpdateForm, OrmNews


class OrmCrudRepository(
    Generic[TDbModel, TModel, TIdValueType, TCreateSchema, TUpdateSchema],
    SqlAlchemyCrudRepository[TDbModel, TModel, TIdValueType, TCreateSchema, TUpdateSchema],
    abc.ABC,
):
    def _create_session(self) -> Session:
        return TEST_DB.session()


class NewsRepositoryInterface(CrudRepositoryInterface[News, int, NewsCreateForm, NewsUpdateForm], abc.ABC):
    pass


class AsyncNewsRepositoryInterface(AsyncCrudRepositoryInterface[News, int, NewsCreateForm, NewsUpdateForm], abc.ABC):
    pass


class UserRepositoryInterface(CrudRepositoryInterface[User, int, UserCreateForm, UserUpdateForm], abc.ABC):
    pass


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


class ListBasedUserRepository(
    ListBasedCrudRepository[User, int, UserCreateForm, UserUpdateForm],
    UserRepositoryInterface,
):
    _next_id: int

    def __init__(self, items: Optional[List[User]] = None):
        super().__init__(items)
        self._next_id = 0

    def get_by_username(self, username: str) -> User:
        items = self.get_collection(AttributeSpecification('username', username))
        if len(items) == 0:
            raise ItemNotFoundException(User)

        return items[0]

    @property
    def model_class(self) -> Type[User]:
        return User

    def _create_model(self, form: UserCreateForm, new_id: int) -> User:
        if self._username_exists(form.username):
            raise UniqueViolationException(User, 'create', form)

        return User(
            id=new_id,
            username=form.username,
            password=form.password,
            display_name=form.display_name,
        )

    def _update_model(self, model: User, form: UserUpdateForm) -> User:
        model.display_name = form.display_name
        return model

    def _username_exists(self, username: str) -> bool:
        return self.count(AttributeSpecification('username', username)) > 0

    def _generate_id(self) -> int:
        self._next_id += 1
        return self._next_id

    def _get_id_filter_specification(self, item_id: int) -> SpecificationInterface[User, bool]:
        return AttributeSpecification('id', item_id, Operator.E)


class AsyncListBasedUserRepository(
    AsyncListBasedCrudRepository[User, int, UserCreateForm, UserUpdateForm],
    AsyncUserRepositoryInterface,
):
    _next_id: int

    def __init__(self, items: Optional[List[User]] = None):
        super().__init__(items)
        self._next_id = 0

    async def get_by_username(self, username: str) -> User:
        items = await self.get_collection(AttributeSpecification('username', username))
        if len(items) == 0:
            raise ItemNotFoundException(User)

        return items[0]

    @property
    def model_class(self) -> Type[User]:
        return User

    async def _create_model(self, form: UserCreateForm, new_id: int) -> User:
        if await self._username_exists(form.username):
            raise UniqueViolationException(User, 'create', form)

        return User(
            id=new_id,
            username=form.username,
            password=form.password,
            display_name=form.display_name,
        )

    async def _update_model(self, model: User, form: UserUpdateForm) -> User:
        model.display_name = form.display_name
        return model

    async def _username_exists(self, username: str) -> bool:
        count = await self.count(AttributeSpecification('username', username))
        return count > 0

    async def _generate_id(self) -> int:
        self._next_id += 1
        return self._next_id

    def _get_id_filter_specification(self, item_id: int) -> SpecificationInterface[User, bool]:
        return AttributeSpecification('id', item_id, Operator.E)
