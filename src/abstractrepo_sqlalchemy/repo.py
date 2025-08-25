from typing import List, Generic, Optional, Type, Tuple
import abc

from sqlalchemy import select, Select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Query, Session, sessionmaker
from sqlalchemy.exc import NoResultFound, IntegrityError

from abstractrepo.exceptions import ItemNotFoundException, UniqueViolationException, RelationViolationException
from abstractrepo.order import OrderOptions
from abstractrepo.paging import PagingOptions
from abstractrepo.repo import CrudRepositoryInterface, TModel, TCreateSchema, TUpdateSchema, TIdValueType, \
    AsyncCrudRepositoryInterface
from abstractrepo.specification import SpecificationInterface

from abstractrepo_sqlalchemy.order import SqlAlchemyOrderOptionsConverter
from abstractrepo_sqlalchemy.specification import SqlAlchemySpecificationConverter
from abstractrepo_sqlalchemy.types import TDbModel


class SqlAlchemyCrudRepository(
    Generic[TDbModel, TModel, TIdValueType, TCreateSchema, TUpdateSchema],
    CrudRepositoryInterface[TModel, TIdValueType, TCreateSchema, TUpdateSchema],
    abc.ABC,
):
    """Abstract Base Class for synchronous SQLAlchemy CRUD repository operations.

    This class provides a concrete implementation of the `CrudRepositoryInterface`
    using SQLAlchemy's ORM for synchronous database interactions. It requires
    subclasses to implement several abstract methods to define the mapping
    between Pydantic business models and SQLAlchemy database models, and to
    handle specific SQLAlchemy query logic.

    Type Parameters:
        TDbModel: The SQLAlchemy database model type.
        TModel: The Pydantic business model type managed by the repository.
        TIdValueType: The type of the unique identifier (primary key) for the model.
        TCreateSchema: The type of the schema used for creating new models.
        TUpdateSchema: The type of the schema used for updating existing models.
    """
    def get_collection(
        self,
        filter_spec: Optional[SpecificationInterface[TModel, bool]] = None,
        order_options: Optional[OrderOptions] = None,
        paging_options: Optional[PagingOptions] = None,
    ) -> List[TModel]:
        """Retrieves a collection of items based on filtering, sorting, and pagination options.

        Args:
            filter_spec: An optional SpecificationInterface instance to filter the collection.
            order_options: An optional OrderOptions instance to specify the sorting order.
            paging_options: An optional PagingOptions instance to control pagination.

        Returns:
            A list of TModel instances matching the criteria.
        """
        with self._create_session() as sess:
            query = sess.query(self._db_model_class)
            query = self._apply_filter(query, filter_spec)
            query = self._apply_order(query, order_options)
            query = self._apply_paging(query, paging_options)
            return [self._convert_db_item_to_model(db_item) for db_item in query.all()]

    def count(self, filter_spec: Optional[SpecificationInterface[TModel, bool]] = None) -> int:
        """Returns the total count of items matching the given filter specification.

        Args:
            filter_spec: An optional SpecificationInterface instance to filter the items.

        Returns:
            The number of items matching the filter.
        """
        with self._create_session() as sess:
            query = sess.query(self._db_model_class)
            query = self._apply_filter(query, filter_spec)
            return query.count()

    def get_item(self, item_id: TIdValueType) -> TModel:
        """Retrieves a single item by its unique identifier.

        Args:
            item_id: The unique identifier of the item to retrieve.

        Returns:
            The TModel instance corresponding to the item_id.

        Raises:
            ItemNotFoundException[TIdValueType]: If no item with the specified ID is found.
        """
        with self._create_session() as sess:
            try:
                db_item = self._apply_id_filter_condition(self._create_select_query(sess), item_id).one()
                return self._convert_db_item_to_model(db_item)
            except NoResultFound:
                sess.rollback()
                raise ItemNotFoundException(self._db_model_class, item_id)

    def exists(self, item_id: TIdValueType) -> bool:
        """Checks if an item with the specified ID exists in the repository.

        Args:
            item_id: The unique identifier of the item to check.

        Returns:
            True if an item with the specified ID exists, False otherwise.
        """
        with self._create_session() as sess:
            return self._apply_id_filter_condition(self._create_select_query(sess), item_id).count() > 0

    def create(self, form: TCreateSchema) -> TModel:
        """Creates a new item in the repository using the provided creation form.

        Args:
            form: The TCreateSchema instance containing data for the new item.

        Returns:
            The newly created TModel instance.

        Raises:
            UniqueConstraintViolation: If a unique constraint violation occurs.
            RelationshipConstraintViolation: If a relationship constraint violation occurs.
        """
        with self._create_session() as sess:
            try:
                db_item = self._create_db_item(form)
                sess.add(db_item)
                sess.commit()
                sess.refresh(db_item)
                return self._convert_db_item_to_model(db_item)
            except IntegrityError as e:
                sess.rollback()
                self._check_violations(e, form, 'create')

    def update(self, item_id: TIdValueType, form: TUpdateSchema) -> TModel:
        """Updates an existing item identified by its ID with data from the update form.

        Args:
            item_id: The unique identifier of the item to update.
            form: The TUpdateSchema instance containing data for updating the item.

        Returns:
            The updated TModel instance.

        Raises:
            ItemNotFoundException[TIdValueType]: If no item with the specified ID is found.
            UniqueConstraintViolation: If a unique constraint violation occurs.
            RelationshipConstraintViolation: If a relationship constraint violation occurs.
        """
        with self._create_session() as sess:
            try:
                db_item = self._apply_id_filter_condition(self._create_select_query(sess), item_id).one()
                self._update_db_item(db_item, form)
                sess.add(db_item)
                sess.commit()
                sess.refresh(db_item)
                return self._convert_db_item_to_model(db_item)
            except NoResultFound:
                sess.rollback()
                raise ItemNotFoundException(self._db_model_class, item_id)
            except IntegrityError as e:
                sess.rollback()
                self._check_violations(e, form, 'update')

    def delete(self, item_id: TIdValueType) -> TModel:
        """Deletes an item from the repository by its ID.

        Args:
            item_id: The unique identifier of the item to delete.

        Returns:
            The deleted TModel instance.

        Raises:
            ItemNotFoundException[TIdValueType]: If no item with the specified ID is found.
        """
        with self._create_session() as sess:
            try:
                db_item = self._apply_id_filter_condition(self._create_select_query(sess), item_id).one()
                sess.delete(db_item)
                sess.commit()
                return self._convert_db_item_to_model(db_item)
            except NoResultFound:
                sess.rollback()
                raise ItemNotFoundException(self._db_model_class, item_id)

    @property
    @abc.abstractmethod
    def _db_model_class(self) -> Type[TDbModel]:
        """Abstract property to return the SQLAlchemy database model class.

        This property must be implemented by subclasses to specify the SQLAlchemy
        model that corresponds to the `TDbModel` type parameter.

        Returns:
            The Type object representing the SQLAlchemy database model class.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def _create_session(self) -> sessionmaker[Session]:
        """Abstract method to create and return a SQLAlchemy session.

        This method must be implemented by subclasses to provide a configured
        SQLAlchemy session (e.g., `sessionmaker(bind=engine)`).

        Returns:
            A sessionmaker instance for synchronous SQLAlchemy sessions.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def _apply_id_filter_condition(self, query: Query[TDbModel], item_id: TIdValueType) -> Query[TDbModel]:
        """Applies a filter condition for a given item ID to the SQLAlchemy query.

        This method must be implemented by subclasses to define how to filter
        a SQLAlchemy query based on the unique identifier of a database item.

        Args:
            query: The SQLAlchemy Query object to which the filter condition will be applied.
            item_id: The unique identifier of the item.

        Returns:
            The modified SQLAlchemy Query object with the ID filter applied.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def _convert_db_item_to_model(self, db_item: TDbModel) -> TModel:
        """Converts a SQLAlchemy database item to the business model.

        This method must be implemented by subclasses to define the conversion
        logic from the SQLAlchemy database model instance to the business model instance.

        Args:
            db_item: The SQLAlchemy database model instance.

        Returns:
            The converted business model instance.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def _create_db_item(self, form: TCreateSchema) -> TDbModel:
        """Creates a SQLAlchemy database item from a creation form object.

        This method must be implemented by subclasses to define how to instantiate
        a SQLAlchemy database model from the provided creation schema.

        Args:
            form: The TCreateSchema instance containing data for the new database item.

        Returns:
            The newly created SQLAlchemy database model instance.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def _update_db_item(self, db_item: TDbModel, form: TUpdateSchema) -> None:
        """Updates an existing SQLAlchemy database item using data from an update form object.

        This method must be implemented by subclasses to define how to apply
        updates from the Pydantic update schema to the SQLAlchemy database model instance.

        Args:
            db_item: The SQLAlchemy database model instance to be updated.
            form: The TUpdateSchema instance containing data for updating the database item.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def _apply_default_filter(self, query: Query[TDbModel]) -> Query[TDbModel]:
        """Applies any default filter conditions to the SQLAlchemy query.

        This method must be implemented by subclasses to apply common or default
        filtering logic to the query before any specific filters are applied.

        Args:
            query: The SQLAlchemy Query object.

        Returns:
            The modified SQLAlchemy Query object with default filters applied.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def _apply_default_order(self, query: Query[TDbModel]) -> Query[TDbModel]:
        """Applies any default ordering to the SQLAlchemy query.

        This method must be implemented by subclasses to apply common or default
        ordering logic to the query.

        Args:
            query: The SQLAlchemy Query object.

        Returns:
            The modified SQLAlchemy Query object with default ordering applied.
        """
        raise NotImplementedError()

    def _apply_filter(self, query: Query[TDbModel], filter_spec: SpecificationInterface) -> Query[TDbModel]:
        """Applies a filter condition to the SQLAlchemy query based on the given filter specification.

        Args:
            query: The SQLAlchemy Query object.
            filter_spec: The filter specification to apply.

        Returns:
            The modified SQLAlchemy Query object with the filter condition applied.
        """
        query = self._apply_default_filter(query)

        if filter_spec is None:
            return query

        condition = SqlAlchemySpecificationConverter[Type[TDbModel]]() \
            .convert(filter_spec) \
            .is_satisfied_by(self._db_model_class)

        return query.filter(condition)

    def _apply_order(self, query: Query[TDbModel], order_options: Optional[OrderOptions] = None) -> Query[TDbModel]:
        """Applies an ordering to the SQLAlchemy query based on the given order options.

        Args:
            query: The SQLAlchemy Query object.
            order_options: The order options to apply.

        Returns:
            The modified SQLAlchemy Query object with the order applied.
        """
        if order_options is None:
            return self._apply_default_order(query)

        order_options = SqlAlchemyOrderOptionsConverter[TDbModel]().convert(order_options)
        return query.order_by(*order_options.to_expression(self._db_model_class))

    def _apply_paging(self, query: Query[TDbModel], paging_options: Optional[PagingOptions] = None) -> Query[TDbModel]:
        """Applies paging to the SQLAlchemy query based on the given paging options.

        Args:
            query: The SQLAlchemy Query object.
            paging_options: The paging options to apply.

        Returns:
            The modified SQLAlchemy Query object with the paging applied.
        """
        if paging_options is None:
            return query

        # TODO use converter
        if paging_options.limit is not None:
            query = query.limit(paging_options.limit)
        if paging_options.offset is not None:
            query = query.offset(paging_options.offset)

        return query

    def _create_select_query(self, sess: Session) -> Query[TDbModel]:
        """Creates a select query for the given session.

        Args:
            sess: The SQLAlchemy session.

        Returns:
            The created SQLAlchemy Query object.
        """
        return sess.query(self._db_model_class)

    def _check_violations(self, e: IntegrityError, form: object, action: str) -> None:
        """Checks for violations in the given exception and raises the appropriate exception.

        Args:
            e: The IntegrityError exception.
            form: The form object.
            action: The action that caused the exception.

        Raises:
            UniqueViolationException: If a unique constraint violation occurs.
            RelationViolationException: If a relationship constraint violation occurs.
        """
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
    """Abstract Base Class for asynchronous SQLAlchemy CRUD repository operations.

    This class provides a concrete implementation of the `AsyncCrudRepositoryInterface`
    using SQLAlchemy 2.0+ and `asyncio` for asynchronous database interactions.
    It requires subclasses to implement several abstract methods to define the mapping
    between Pydantic business models and SQLAlchemy database models, and to
    handle specific SQLAlchemy query logic.

    Type Parameters:
        TDbModel: The SQLAlchemy database model type.
        TModel: The Pydantic business model type managed by the repository.
        TIdValueType: The type of the unique identifier (primary key) for the model.
        TCreateSchema: The type of the schema used for creating new models.
        TUpdateSchema: The type of the schema used for updating existing models.
    """
    async def get_collection(
        self,
        filter_spec: Optional[SpecificationInterface[TModel, bool]] = None,
        order_options: Optional[OrderOptions] = None,
        paging_options: Optional[PagingOptions] = None,
    ) -> List[TModel]:
        """Retrieves a collection of items based on filtering, sorting, and pagination options.

        Args:
            filter_spec: An optional SpecificationInterface instance to filter the collection.
            order_options: An optional OrderOptions instance to specify the sorting order.
            paging_options: An optional PagingOptions instance to control pagination.

        Returns:
            A list of TModel instances matching the criteria.
        """
        async with self._create_session() as sess:
            stmt = select(self._db_model_class)
            stmt = self._apply_filter(stmt, filter_spec)
            stmt = self._apply_order(stmt, order_options)
            stmt = self._apply_paging(stmt, paging_options)

            result = await sess.execute(stmt)
            db_items = result.scalars().all()
            return [self._convert_db_item_to_model(db_item) for db_item in db_items]

    async def count(self, filter_spec: Optional[SpecificationInterface[TModel, bool]] = None) -> int:
        """Returns the total count of items matching the given filter specification.

        Args:
            filter_spec: An optional SpecificationInterface instance to filter the items.

        Returns:
            The number of items matching the filter.
        """
        async with self._create_session() as sess:
            stmt = select(self._db_model_class)
            stmt = self._apply_filter(stmt, filter_spec)

            result = await sess.execute(stmt)
            return len(result.scalars().all())

    async def get_item(self, item_id: TIdValueType) -> TModel:
        """Retrieves a single item by its unique identifier.

        Args:
            item_id: The unique identifier of the item to retrieve.

        Returns:
            The TModel instance corresponding to the item_id.

        Raises:
            ItemNotFoundException[TIdValueType]: If no item with the specified ID is found.
        """
        async with self._create_session() as sess:
            try:
                stmt = self._apply_id_filter_condition(self._create_select_stmt(), item_id)
                result = await sess.execute(stmt)
                db_item = result.scalar_one()
                return self._convert_db_item_to_model(db_item)
            except NoResultFound:
                await sess.rollback()
                raise ItemNotFoundException(self._db_model_class, item_id)

    async def exists(self, item_id: TIdValueType) -> bool:
        """Checks if an item with the specified ID exists in the repository.

        Args:
            item_id: The unique identifier of the item to check.

        Returns:
            True if an item with the specified ID exists, False otherwise.
        """
        async with self._create_session() as sess:
            stmt = self._apply_id_filter_condition(self._create_select_stmt(), item_id)
            result = await sess.execute(stmt)
            return result.scalar_one_or_none() is not None

    async def create(self, form: TCreateSchema) -> TModel:
        """Creates a new item in the repository using the provided creation form.

        Args:
            form: The TCreateSchema instance containing data for the new item.

        Returns:
            The newly created TModel instance.

        Raises:
            UniqueConstraintViolation: If a unique constraint violation occurs.
            RelationshipConstraintViolation: If a relationship constraint violation occurs.
        """
        async with self._create_session() as sess:
            try:
                db_item = self._create_db_item(form)
                sess.add(db_item)
                await sess.commit()
                await sess.refresh(db_item)
                return self._convert_db_item_to_model(db_item)
            except IntegrityError as e:
                await sess.rollback()
                self._check_violations(e, form, 'create')

    async def update(self, item_id: TIdValueType, form: TUpdateSchema) -> TModel:
        """Updates an existing item identified by its ID with data from the update form.

        Args:
            item_id: The unique identifier of the item to update.
            form: The TUpdateSchema instance containing data for updating the item.

        Returns:
            The updated TModel instance.

        Raises:
            ItemNotFoundException[TIdValueType]: If no item with the specified ID is found.
            UniqueConstraintViolation: If a unique constraint violation occurs.
            RelationshipConstraintViolation: If a relationship constraint violation occurs.
        """
        async with self._create_session() as sess:
            try:
                stmt = self._apply_id_filter_condition(self._create_select_stmt(), item_id)
                result = await sess.execute(stmt)
                db_item = result.scalar_one()
                self._update_db_item(db_item, form)
                await sess.commit()
                await sess.refresh(db_item)
                return self._convert_db_item_to_model(db_item)
            except NoResultFound:
                await sess.rollback()
                raise ItemNotFoundException(self._db_model_class, item_id)
            except IntegrityError as e:
                await sess.rollback()
                self._check_violations(e, form, 'update')

    async def delete(self, item_id: TIdValueType) -> TModel:
        """Deletes an item from the repository by its ID.

        Args:
            item_id: The unique identifier of the item to delete.

        Returns:
            The deleted TModel instance.

        Raises:
            ItemNotFoundException[TIdValueType]: If no item with the specified ID is found.
        """
        async with self._create_session() as sess:
            try:
                stmt = self._apply_id_filter_condition(self._create_select_stmt(), item_id)
                result = await sess.execute(stmt)
                db_item = result.scalar_one()
                await sess.delete(db_item)
                await sess.commit()
                return self._convert_db_item_to_model(db_item)
            except NoResultFound:
                await sess.rollback()
                raise ItemNotFoundException(self._db_model_class, item_id)

    @property
    @abc.abstractmethod
    def _db_model_class(self) -> Type[TDbModel]:
        """Abstract property to return the SQLAlchemy database model class.

        This property must be implemented by subclasses to specify the SQLAlchemy
        model that corresponds to the `TDbModel` type parameter.

        Returns:
            The Type object representing the SQLAlchemy database model class.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def _create_session(self) -> async_sessionmaker[AsyncSession]:
        """Abstract method to create and return an asynchronous SQLAlchemy session.

        This method must be implemented by subclasses to provide a configured
        asynchronous SQLAlchemy session (e.g., `async_sessionmaker(bind=engine)`).

        Returns:
            An async_sessionmaker instance for asynchronous SQLAlchemy sessions.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def _apply_id_filter_condition(self, stmt: Select[Tuple[TDbModel]], item_id: TIdValueType) -> Select[Tuple[TDbModel]]:
        """Applies a filter condition for a given item ID to the SQLAlchemy select statement.

        This method must be implemented by subclasses to define how to filter
        a SQLAlchemy select statement based on the unique identifier of a database item.

        Args:
            stmt: The SQLAlchemy Select statement to which the filter condition will be applied.
            item_id: The unique identifier of the item.

        Returns:
            The modified SQLAlchemy Select statement with the ID filter applied.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def _convert_db_item_to_model(self, db_item: TDbModel) -> TModel:
        """Converts a SQLAlchemy database item to the business model.

        This method must be implemented by subclasses to define the conversion
        logic from the SQLAlchemy database model instance to the business model instance.

        Args:
            db_item: The SQLAlchemy database model instance.

        Returns:
            The converted business model instance.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def _create_db_item(self, form: TCreateSchema) -> TDbModel:
        """Creates a SQLAlchemy database item from a creation form object.

        This method must be implemented by subclasses to define how to instantiate
        a SQLAlchemy database model from the provided creation schema.

        Args:
            form: The TCreateSchema instance containing data for the new database item.

        Returns:
            The newly created SQLAlchemy database model instance.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def _update_db_item(self, db_item: TDbModel, form: TUpdateSchema) -> None:
        """Updates an existing SQLAlchemy database item using data from an update form object.

        This method must be implemented by subclasses to define how to apply
        updates from the Pydantic update schema to the SQLAlchemy database model instance.

        Args:
            db_item: The SQLAlchemy database model instance to be updated.
            form: The TUpdateSchema instance containing data for updating the database item.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def _apply_default_filter(self, stmt: Select[Tuple[TDbModel]]) -> Select[Tuple[TDbModel]]:
        """Applies any default filter conditions to the SQLAlchemy select statement.

        This method must be implemented by subclasses to apply common or default
        filtering logic to the select statement before any specific filters are applied.

        Args:
            stmt: The SQLAlchemy Select statement.

        Returns:
            The modified SQLAlchemy Select statement with default filters applied.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def _apply_default_order(self, stmt: Select[Tuple[TDbModel]]) -> Select[Tuple[TDbModel]]:
        """Applies any default ordering to the SQLAlchemy select statement.

        This method must be implemented by subclasses to apply common or default
        ordering logic to the select statement.

        Args:
            stmt: The SQLAlchemy Select statement.

        Returns:
            The modified SQLAlchemy Select statement with default ordering applied.
        """
        raise NotImplementedError()

    def _apply_filter(self, stmt: Select[Tuple[TDbModel]], filter_spec: SpecificationInterface) -> Select[Tuple[TDbModel]]:
        """Applies a filter condition to the SQLAlchemy select statement based on the given filter specification.

        Args:
            stmt: The SQLAlchemy Select statement.
            filter_spec: The filter specification to apply.

        Returns:
            The modified SQLAlchemy Select statement with the filter condition applied.
        """
        if filter_spec is None:
            return self._apply_default_filter(stmt)

        condition = SqlAlchemySpecificationConverter[Type[TDbModel]]() \
            .convert(filter_spec) \
            .is_satisfied_by(self._db_model_class)

        return stmt.where(condition)

    def _apply_order(self, stmt: Select[Tuple[TDbModel]], order_options: Optional[OrderOptions] = None) -> Select[Tuple[TDbModel]]:
        """Applies an ordering to the SQLAlchemy select statement based on the given order options.

        Args:
            stmt: The SQLAlchemy Select statement.
            order_options: The order options to apply.

        Returns:
            The modified SQLAlchemy Select statement with the order applied.
        """
        if order_options is None:
            return self._apply_default_order(stmt)

        order_options = SqlAlchemyOrderOptionsConverter[TDbModel]().convert(order_options)
        return stmt.order_by(*order_options.to_expression(self._db_model_class))

    def _apply_paging(self, stmt: Select[Tuple[TDbModel]], paging_options: Optional[PagingOptions] = None) -> Select[Tuple[TDbModel]]:
        """Applies paging to the SQLAlchemy select statement based on the given paging options.

        Args:
            stmt: The SQLAlchemy Select statement.
            paging_options: The paging options to apply.

        Returns:
            The modified SQLAlchemy Select statement with the paging applied.
        """
        if paging_options is None:
            return stmt

        # TODO use converter
        if paging_options.limit is not None:
            stmt = stmt.limit(paging_options.limit)
        if paging_options.offset is not None:
            stmt = stmt.offset(paging_options.offset)

        return stmt

    def _create_select_stmt(self) -> Select[Tuple[TDbModel]]:
        """Creates a select statement for the given database model class.

        Returns:
            The created SQLAlchemy Select statement.
        """
        return Select(self._db_model_class)

    def _check_violations(self, e: IntegrityError, form: object, action: str) -> None:
        """Checks for violations in the given exception and raises the appropriate exception.

        Args:
            e: The IntegrityError exception.
            form: The form object.
            action: The action that caused the exception.

        Raises:
            UniqueViolationException: If a unique constraint violation occurs.
            RelationViolationException: If a relationship constraint violation occurs.
        """
        error_msg = str(e.orig).lower()
        if "unique" in error_msg or "duplicate" in error_msg:
            raise UniqueViolationException(self.model_class, action, form)
        elif "foreign" in error_msg or "reference" in error_msg:
            raise RelationViolationException(self.model_class, action, form)
        raise e  # pragma: no cover
