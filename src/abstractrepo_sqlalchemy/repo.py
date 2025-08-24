from typing import List, Generic, Optional, Type, Tuple
import abc

from sqlalchemy import select, delete, update, Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query, Session
from sqlalchemy.exc import NoResultFound, IntegrityError

from abstractrepo.exceptions import ItemNotFoundException, UniqueViolationException, RelationViolationException
from abstractrepo.order import OrderOptions
from abstractrepo.paging import PagingOptions
from abstractrepo.repo import CrudRepositoryInterface, TModel, TCreateSchema, TUpdateSchema, TIdValueType, \
    AsyncCrudRepositoryInterface
from abstractrepo.specification import SpecificationInterface

from abstractrepo_sqlalchemy.order import SqlAlchemyOptionsConverter
from abstractrepo_sqlalchemy.specification import SqlAlchemySpecificationConverter
from abstractrepo_sqlalchemy.types import TDbModel


class SqlAlchemyCrudRepository(
    Generic[TDbModel, TModel, TIdValueType, TCreateSchema, TUpdateSchema],
    CrudRepositoryInterface[TModel, TIdValueType, TCreateSchema, TUpdateSchema],
    abc.ABC,
):
    def get_collection(
        self,
        filter_spec: Optional[SpecificationInterface[TModel, bool]] = None,
        order_options: Optional[OrderOptions] = None,
        paging_options: Optional[PagingOptions] = None,
    ) -> List[TModel]:
        with self._create_session() as sess:
            query = sess.query(self._get_db_model_class())
            query = self._apply_filter(query, filter_spec)
            query = self._apply_order(query, order_options)
            query = self._apply_paging(query, paging_options)
            return [self._convert_db_item_to_schema(db_item) for db_item in query.all()]

    def count(self, filter_spec: Optional[SpecificationInterface[TModel, bool]] = None) -> int:
        with self._create_session() as sess:
            query = sess.query(self._get_db_model_class())
            query = self._apply_filter(query, filter_spec)
            return query.count()

    def get_item(self, item_id: TIdValueType) -> TModel:
        with self._create_session() as sess:
            try:
                db_item = self._apply_id_filter_condition(self._create_select_query(sess), item_id).one()
                return self._convert_db_item_to_schema(db_item)
            except NoResultFound:
                sess.rollback()
                raise ItemNotFoundException(self._get_db_model_class(), item_id)

    def exists(self, item_id: TIdValueType) -> bool:
        with self._create_session() as sess:
            return self._apply_id_filter_condition(self._create_select_query(sess), item_id).count() > 0

    def create(self, form: TCreateSchema) -> TModel:
        with self._create_session() as sess:
            try:
                db_item = self._create_from_schema(form)
                sess.add(db_item)
                sess.commit()
                sess.refresh(db_item)
                return self._convert_db_item_to_schema(db_item)
            except IntegrityError as e:
                sess.rollback()
                self._check_violations(e, form, 'create')

    def update(self, item_id: TIdValueType, form: TUpdateSchema) -> TModel:
        with self._create_session() as sess:
            try:
                db_item = self._apply_id_filter_condition(self._create_select_query(sess), item_id).one()
                self._update_from_schema(db_item, form)
                sess.add(db_item)
                sess.commit()
                sess.refresh(db_item)
                return self._convert_db_item_to_schema(db_item)
            except NoResultFound:
                sess.rollback()
                raise ItemNotFoundException(self._get_db_model_class(), item_id)
            except IntegrityError as e:
                sess.rollback()
                self._check_violations(e, form, 'update')

    def delete(self, item_id: TIdValueType) -> TModel:
        with self._create_session() as sess:
            try:
                db_item = self._apply_id_filter_condition(self._create_select_query(sess), item_id).one()
                sess.delete(db_item)
                sess.commit()
                return self._convert_db_item_to_schema(db_item)
            except NoResultFound:
                sess.rollback()
                raise ItemNotFoundException(self._get_db_model_class(), item_id)

    def _apply_filter(self, query: Query[Type[TDbModel]], filter_spec: SpecificationInterface) -> Query[Type[TDbModel]]:
        if filter_spec is None:
            return self._apply_default_filter(query)

        condition = SqlAlchemySpecificationConverter[TDbModel]() \
            .convert(filter_spec) \
            .is_satisfied_by(self._get_db_model_class())

        return query.filter(condition)

    def _apply_order(self, query: Query[Type[TDbModel]], order_options: Optional[OrderOptions] = None) -> Query[Type[TDbModel]]:
        if order_options is None:
            return self._apply_default_order(query)

        order_options = SqlAlchemyOptionsConverter[TDbModel]().convert(order_options)
        return query.order_by(*order_options.to_expression(self._get_db_model_class()))

    def _apply_paging(self, query: Query[Type[TDbModel]], paging_options: Optional[PagingOptions] = None) -> Query[Type[TDbModel]]:
        if paging_options is None:
            return query

        # TODO use converter
        if paging_options.limit is not None:
            query = query.limit(paging_options.limit)
        if paging_options.offset is not None:
            query = query.offset(paging_options.offset)

        return query

    @abc.abstractmethod
    def _create_session(self) -> Session:
        raise NotImplementedError()

    @abc.abstractmethod
    def _get_db_model_class(self) -> Type[TDbModel]:
        raise NotImplementedError()

    @abc.abstractmethod
    def _apply_id_filter_condition(self, query: Query[Type[TDbModel]], item_id: TIdValueType) -> Query[Type[TDbModel]]:
        raise NotImplementedError()

    @abc.abstractmethod
    def _convert_db_item_to_schema(self, db_item: TDbModel) -> TModel:
        raise NotImplementedError()

    @abc.abstractmethod
    def _create_from_schema(self, form: TCreateSchema) -> TDbModel:
        raise NotImplementedError()

    @abc.abstractmethod
    def _update_from_schema(self, db_item: TDbModel, form: TUpdateSchema) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def _apply_default_filter(self, query: Query[Type[TDbModel]]) -> Query[Type[TDbModel]]:
        raise NotImplementedError()

    @abc.abstractmethod
    def _apply_default_order(self, query: Query[Type[TDbModel]]) -> Query[Type[TDbModel]]:
        raise NotImplementedError()

    def _create_select_query(self, sess: Session) -> Query[Type[TDbModel]]:
        return sess.query(self._get_db_model_class())

    def _check_violations(self, e: IntegrityError, form: object, action: str) -> None:
        error_msg = str(e.orig).lower()
        if "unique" in error_msg or "duplicate" in error_msg:
            raise UniqueViolationException(self.model_class, action, form)
        elif "foreign" in error_msg or "reference" in error_msg:
            raise RelationViolationException(self.model_class, action, form)
        raise e  # pragma: no cover


class AsyncSqlAlchemyCrudRepository(
    Generic[TDbModel, TModel, TIdValueType, TCreateSchema, TUpdateSchema],
    AsyncCrudRepositoryInterface[TModel, TIdValueType, TCreateSchema, TUpdateSchema],
    abc.ABC,
):
    async def get_collection(
        self,
        filter_spec: Optional[SpecificationInterface[TModel, bool]] = None,
        order_options: Optional[OrderOptions] = None,
        paging_options: Optional[PagingOptions] = None,
    ) -> List[TModel]:
        async with self._create_session() as sess:
            stmt = select(self._get_db_model_class())
            stmt = self._apply_filter(stmt, filter_spec)
            stmt = self._apply_order(stmt, order_options)
            stmt = self._apply_paging(stmt, paging_options)

            result = await sess.execute(stmt)
            db_items = result.scalars().all()
            return [self._convert_db_item_to_schema(db_item) for db_item in db_items]

    async def count(self, filter_spec: Optional[SpecificationInterface[TModel, bool]] = None) -> int:
        async with self._create_session() as sess:
            stmt = select(self._get_db_model_class())
            stmt = self._apply_filter(stmt, filter_spec)

            result = await sess.execute(stmt)
            return len(result.scalars().all())

    async def get_item(self, item_id: TIdValueType) -> TModel:
        async with self._create_session() as sess:
            try:
                stmt = self._apply_id_filter_condition(self._create_select_stmt(), item_id)
                result = await sess.execute(stmt)
                db_item = result.scalar_one()
                return self._convert_db_item_to_schema(db_item)
            except NoResultFound:
                await sess.rollback()
                raise ItemNotFoundException(self._get_db_model_class(), item_id)

    async def exists(self, item_id: TIdValueType) -> bool:
        async with self._create_session() as sess:
            stmt = self._apply_id_filter_condition(self._create_select_stmt(), item_id)
            result = await sess.execute(stmt)
            return result.scalar_one_or_none() is not None

    async def create(self, form: TCreateSchema) -> TModel:
        async with self._create_session() as sess:
            try:
                db_item = self._create_from_schema(form)
                sess.add(db_item)
                await sess.commit()
                await sess.refresh(db_item)
                return self._convert_db_item_to_schema(db_item)
            except IntegrityError as e:
                await sess.rollback()
                self._check_violations(e, form, 'create')

    async def update(self, item_id: TIdValueType, form: TUpdateSchema) -> TModel:
        async with self._create_session() as sess:
            try:
                stmt = self._apply_id_filter_condition(self._create_select_stmt(), item_id)
                result = await sess.execute(stmt)
                db_item = result.scalar_one()
                self._update_from_schema(db_item, form)
                await sess.commit()
                await sess.refresh(db_item)
                return self._convert_db_item_to_schema(db_item)
            except NoResultFound:
                await sess.rollback()
                raise ItemNotFoundException(self._get_db_model_class(), item_id)
            except IntegrityError as e:
                await sess.rollback()
                self._check_violations(e, form, 'update')

    async def delete(self, item_id: TIdValueType) -> TModel:
        async with self._create_session() as sess:
            try:
                stmt = self._apply_id_filter_condition(self._create_select_stmt(), item_id)
                result = await sess.execute(stmt)
                db_item = result.scalar_one()
                await sess.delete(db_item)
                await sess.commit()
                return self._convert_db_item_to_schema(db_item)
            except NoResultFound:
                await sess.rollback()
                raise ItemNotFoundException(self._get_db_model_class(), item_id)

    def _apply_filter(self, stmt: Select[Tuple[TDbModel]], filter_spec: SpecificationInterface) -> Select[Tuple[TDbModel]]:
        if filter_spec is None:
            return self._apply_default_filter(stmt)

        condition = SqlAlchemySpecificationConverter[TDbModel]() \
            .convert(filter_spec) \
            .is_satisfied_by(self._get_db_model_class())

        return stmt.where(condition)

    def _apply_order(self, stmt: Select[Tuple[TDbModel]], order_options: Optional[OrderOptions] = None) -> Select[Tuple[TDbModel]]:
        if order_options is None:
            return self._apply_default_order(stmt)

        order_options = SqlAlchemyOptionsConverter[TDbModel]().convert(order_options)
        return stmt.order_by(*order_options.to_expression(self._get_db_model_class()))

    def _apply_paging(self, stmt: Select[Tuple[TDbModel]], paging_options: Optional[PagingOptions] = None) -> Select[Tuple[TDbModel]]:
        if paging_options is None:
            return stmt

        # TODO use converter
        if paging_options.limit is not None:
            stmt = stmt.limit(paging_options.limit)
        if paging_options.offset is not None:
            stmt = stmt.offset(paging_options.offset)

        return stmt

    @abc.abstractmethod
    def _create_session(self) -> AsyncSession:
        raise NotImplementedError()

    @abc.abstractmethod
    def _get_db_model_class(self) -> Type[TDbModel]:
        raise NotImplementedError()

    @abc.abstractmethod
    def _apply_id_filter_condition(self, stmt: Select[Tuple[TDbModel]], item_id: TIdValueType) -> Select[Tuple[TDbModel]]:
        raise NotImplementedError()

    @abc.abstractmethod
    def _convert_db_item_to_schema(self, db_item: TDbModel) -> TModel:
        raise NotImplementedError()

    @abc.abstractmethod
    def _create_from_schema(self, form: TCreateSchema) -> TDbModel:
        raise NotImplementedError()

    @abc.abstractmethod
    def _update_from_schema(self, db_item: TDbModel, form: TUpdateSchema) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def _apply_default_filter(self, stmt: Select[Tuple[TDbModel]]) -> Select[Tuple[TDbModel]]:
        raise NotImplementedError()

    @abc.abstractmethod
    def _apply_default_order(self, stmt: Select[Tuple[TDbModel]]) -> Select[Tuple[TDbModel]]:
        raise NotImplementedError()

    def _create_select_stmt(self) -> Select[Tuple[TDbModel]]:
        return Select(self._get_db_model_class())

    def _check_violations(self, e: IntegrityError, form: object, action: str) -> None:
        error_msg = str(e.orig).lower()
        if "unique" in error_msg or "duplicate" in error_msg:
            raise UniqueViolationException(self.model_class, action, form)
        elif "foreign" in error_msg or "reference" in error_msg:
            raise RelationViolationException(self.model_class, action, form)
        raise e  # pragma: no cover
