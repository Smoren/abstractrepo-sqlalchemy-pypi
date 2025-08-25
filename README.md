# AbstractRepo Implementation for SqlAlchemy

[![PyPI package](https://img.shields.io/badge/pip%20install-abstractrepo--sqlalchemy-brightgreen)](https://pypi.org/project/abstractrepo-sqlalchemy/)
[![version number](https://img.shields.io/pypi/v/abstractrepo-sqlalchemy?color=green&label=version)](https://github.com/Smoren/abstractrepo-sqlalchemy-pypi/releases)
[![Coverage Status](https://coveralls.io/repos/github/Smoren/abstractrepo-sqlalchemy-pypi/badge.svg?branch=master)](https://coveralls.io/github/Smoren/abstractrepo-sqlalchemy-pypi?branch=master)
[![PyPI Downloads](https://static.pepy.tech/badge/abstractrepo-sqlalchemy)](https://pepy.tech/projects/abstractrepo-sqlalchemy)
[![Actions Status](https://github.com/Smoren/abstractrepo-sqlalchemy-pypi/workflows/Test/badge.svg)](https://github.com/Smoren/abstractrepo-sqlalchemy-pypi/actions)
[![License](https://img.shields.io/github/license/Smoren/abstractrepo-sqlalchemy-pypi)](https://github.com/Smoren/abstractrepo-sqlalchemy-pypi/blob/master/LICENSE)

The **AbstractRepo SQLAlchemy** library provides a concrete implementation of the [AbstractRepo](https://github.com/Smoren/abstractrepo-pypi) 
interfaces for [SQLAlchemy](https://www.sqlalchemy.org/), a popular SQL toolkit and Object-Relational Mapper (ORM) for Python. It seamlessly integrates 
the abstract repository pattern with SQLAlchemy's powerful features, enabling developers to build robust and maintainable data access layers.

This implementation leverages SQLAlchemy's Core and ORM components to provide both synchronous and asynchronous repository patterns. 
It is designed to work with any database dialect supported by SQLAlchemy, including PostgreSQL, MySQL, SQLite, and more.

## Key Features

* **SQLAlchemy Integration:** Built on top of SQLAlchemy for reliable and efficient database interactions.
* **CRUD Operations:** Full support for Create, Read, Update, and Delete operations.
* **Asynchronous Support:** Provides an asynchronous repository implementation for use with `asyncio` and SQLAlchemy's async capabilities.
* **Specification Pattern:** Translates abstract specifications into SQLAlchemy query expressions.
* **Type-Safe:** Utilizes Python's type hinting for improved code quality and developer experience.
* **Extensible:** Easily extendable to support custom query logic and advanced SQLAlchemy features.

## Installation

To get started with `AbstractRepo SQLAlchemy`, install it using pip:

```shell
pip install abstractrepo-sqlalchemy
```

## Table of Contents

* [Core Components and Usage](#core-components-and-usage)
    * [Repository Interface](#repository-interface)
    * [Specifications](#specifications)
    * [Ordering](#ordering)
    * [Pagination](#pagination)
    * [Exception Handling](#exception-handling)
* [Examples](#examples)
    * [Complete Synchronous Example](#complete-synchronous-example)
    * [Complete Asynchronous Example](#complete-asynchronous-example)
* [Best Practices](#best-practices)
* [Dependencies](#dependencies)
* [License](#license)

## Core Components and Usage

### Repository Interface

The `SqlAlchemyCrudRepository` and `AsyncSqlAlchemyCrudRepository` classes provide concrete implementations of the 
`CrudRepositoryInterface` and `AsyncCrudRepositoryInterface` respectively, bridging the `AbstractRepo` pattern with SQLAlchemy.

These classes require you to define how your Pydantic business models map to SQLAlchemy database models and how 
CRUD operations are performed at the database level. You achieve this by implementing several abstract methods and properties:

| Name                         | Description                                                                            |
|------------------------------|----------------------------------------------------------------------------------------|
| `model_class`                | Returns the Pydantic business model class.                                             |
| `_db_model_class`            | Returns the SQLAlchemy database model class.                                           |
| `_create_session`            | Provides an SQLAlchemy session (synchronous `Session` or asynchronous `AsyncSession`). |
| `_apply_id_filter_condition` | Applies a filter condition for a given item ID to the SQLAlchemy query/statement.      |
| `_convert_db_item_to_model`  | Converts a SQLAlchemy database item to your Pydantic business model.                   |
| `_create_db_item`            | Creates a SQLAlchemy database item from a Pydantic creation form.                      |
| `_update_db_item`            | Updates an existing SQLAlchemy database item using data from a Pydantic update form.   |
| `_apply_default_filter`      | Applies any default filter conditions to the SQLAlchemy query/statement.               |
| `_apply_default_order`       | Applies any default ordering to the SQLAlchemy query/statement.                        |

These classes are generic and can be used with any model class (e.g. Pydantic). Generics are used to specify the types 
of the following:

| Name            | Description                                                            |
|-----------------|------------------------------------------------------------------------|
| `TDbModel`      | The SQLAlchemy database model class.                                   |
| `TModel`        | The Pydantic business model class.                                     |
| `TIdValueType`  | The type of the model's identifier (primary key) attribute.            |
| `TCreateSchema` | The Pydantic model used for creating a new instance of `TModel`.       |
| `TUpdateSchema` | The Pydantic model used for updating an existing instance of `TModel`. |

### Specifications

**AbstractRepo SQLAlchemy** seamlessly integrates with the **Specification Pattern** from `abstractrepo`. 
This allows you to define complex query criteria in a type-safe and reusable manner, which are then translated into 
SQLAlchemy query expressions.

The following specification types are supported:

* `AttributeSpecification`
* `AndSpecification`
* `OrSpecification`
* `NotSpecification`

For detailed information please refer to the [Specifications section in the abstractrepo README](https://github.com/Smoren/abstractrepo-pypi#specifications).

**AbstractRepo SQLAlchemy** handles the internal conversion of these generic specifications into SQLAlchemy-specific filter 
conditions. You primarily use these specifications when calling `get_collection` or `count`.

### Ordering

**AbstractRepo SQLAlchemy** supports flexible ordering of query results using the `OrderOption` and `OrderOptions` 
classes provided by `abstractrepo`. These are translated directly into SQLAlchemy's `order_by()` clauses.

For a comprehensive understanding of `OrderOption` and `OrderOptions`, please consult the [Ordering section in the abstractrepo README](https://github.com/Smoren/abstractrepo-pypi#ordering).

### Pagination

Efficient handling of large datasets is achieved through pagination, implemented in `abstractrepo-sqlalchemy` using the 
`PagingOptions` class from `abstractrepo`. This translates directly to SQLAlchemy's `limit()` and `offset()` methods.

For details on `PagingOptions` (including `limit` and `offset`), refer to the [Pagination section in the abstractrepo README](https://github.com/Smoren/abstractrepo-pypi#pagination).

### Exception Handling

`abstractrepo-sqlalchemy` utilizes the custom exceptions defined in `abstractrepo` to provide clear and consistent error handling. These include:

* `ItemNotFoundException`: Raised when an item is not found.
* `UniqueViolationException`: Raised on unique constraint violations.

For more details on these exceptions and their usage, please see the [Exception Handling section in the abstractrepo README](https://github.com/Smoren/abstractrepo-pypi#exception-handling).

## Examples

### Complete Synchronous Example

```python
import abc
from typing import Type, Optional
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base, Session, Query
from pydantic import BaseModel

from abstractrepo.repo import CrudRepositoryInterface
from abstractrepo.specification import AttributeSpecification, AndSpecification
from abstractrepo.exceptions import ItemNotFoundException
from abstractrepo_sqlalchemy.repo import SqlAlchemyCrudRepository

Base = declarative_base()
DbSession = sessionmaker()

# Define SQLAlchemy model
class UserTable(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)


# Define Pydantic business model
class User(BaseModel):
    id: int
    username: str
    password: str
    display_name: str

# Define Pydantic models for CRUD operations
class UserCreateForm(BaseModel):
    username: str
    password: str
    display_name: str

class UserUpdateForm(BaseModel):
    display_name: Optional[str] = None
    username: Optional[str] = None

# Define the repository interface
class UserRepositoryInterface(CrudRepositoryInterface[User, int, UserCreateForm, UserUpdateForm], abc.ABC):
    pass

# Implement the repository using SqlAlchemyCrudRepository
class SqlAlchemyUserRepository(
    SqlAlchemyCrudRepository[UserTable, User, int, UserCreateForm, UserUpdateForm],
    UserRepositoryInterface,
):
    def get_by_username(self, username: str) -> User:
        """Example method to retrieve a user by username."""
        items = self.get_collection(AttributeSpecification('username', username))
        if len(items) == 0:
            raise ItemNotFoundException(User)
        return items[0]

    @property
    def model_class(self) -> Type[User]:
        return User

    @property
    def _db_model_class(self) -> Type[UserTable]:
        return UserTable

    def _apply_id_filter_condition(self, query: Query[UserTable], item_id: int) -> Query[UserTable]:
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

    def _apply_default_filter(self, query: Query[UserTable]) -> Query[UserTable]:
        return query

    def _apply_default_order(self, query: Query[UserTable]) -> Query[UserTable]:
        return query.order_by(UserTable.id)

    def _create_session(self) -> sessionmaker[Session]:
        return DbSession()

# Initialize the repository
repo = SqlAlchemyUserRepository()

# Create a new user
user = UserCreateForm(username="john_doe", password="password123", display_name="John Doe")
created_user = repo.create(user)

# Retrieve a user by username
retrieved_user = repo.get_by_username("john_doe")

# Update a user
updated_user = UserUpdateForm(display_name="John Doe Jr.")
updated_user = repo.update(created_user.id, updated_user)

# Delete a user
repo.delete(created_user.id)

# List all users
users = repo.get_collection()

# List users using a filter
filtered_users = repo.get_collection(AndSpecification(
    AttributeSpecification('display_name', 'John Doe'),
    AttributeSpecification('username', 'john_doe'),
))
```

### Complete Asynchronous Example

```python
import abc
from typing import Type, Optional, Tuple
from sqlalchemy import Column, Integer, String, Select
from sqlalchemy.orm import sessionmaker, declarative_base, Session, Query
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from pydantic import BaseModel

from abstractrepo.repo import AsyncCrudRepositoryInterface, TModel
from abstractrepo.specification import AttributeSpecification, AndSpecification
from abstractrepo.exceptions import ItemNotFoundException
from abstractrepo_sqlalchemy.repo import SqlAlchemyCrudRepository, AsyncSqlAlchemyCrudRepository

Base = declarative_base()
AsyncDbSession = async_sessionmaker()

# Define SQLAlchemy model
class UserTable(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)

# Define Pydantic business model
class User(BaseModel):
    id: int
    username: str
    password: str
    display_name: str

# Define Pydantic models for CRUD operations
class UserCreateForm(BaseModel):
    username: str
    password: str
    display_name: str

class UserUpdateForm(BaseModel):
    display_name: Optional[str] = None
    username: Optional[str] = None

# Define the repository interface
class AsyncUserRepositoryInterface(AsyncCrudRepositoryInterface[User, int, UserCreateForm, UserUpdateForm], abc.ABC):
    pass

# Implement the repository using SqlAlchemyCrudRepository
class AsyncSqlAlchemyUserRepository(
    AsyncSqlAlchemyCrudRepository[UserTable, User, int, UserCreateForm, UserUpdateForm],
    AsyncUserRepositoryInterface,
):
    async def get_by_username(self, username: str) -> User:
        """Example method to retrieve a user by username."""
        items = await self.get_collection(AttributeSpecification('username', username))
        if len(items) == 0:
            raise ItemNotFoundException(User)
        return items[0]

    @property
    def model_class(self) -> Type[User]:
        return User

    @property
    def _db_model_class(self) -> Type[UserTable]:
        return UserTable

    def _apply_id_filter_condition(self, stmt: Select[Tuple[UserTable]], item_id: int) -> Select[Tuple[UserTable]]:
        return stmt.where(UserTable.id == item_id)

    def _convert_db_item_to_model(self, db_item: UserTable) -> TModel:
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

    def _create_session(self) -> async_sessionmaker[AsyncSession]:
        return AsyncDbSession()

async def custom_async_code():
    # Initialize the repository
    repo = AsyncSqlAlchemyUserRepository()

    # Create a new user
    user = UserCreateForm(username="john_doe", password="password123", display_name="John Doe")
    created_user = await repo.create(user)

    # Retrieve a user by username
    retrieved_user = await repo.get_by_username("john_doe")

    # Update a user
    updated_user = UserUpdateForm(display_name="John Doe Jr.")
    updated_user = await repo.update(created_user.id, updated_user)

    # Delete a user
    await repo.delete(created_user.id)

    # List all users
    users = await repo.get_collection()

    # List users using a filter
    filtered_users = await repo.get_collection(AndSpecification(
        AttributeSpecification('display_name', 'John Doe'),
        AttributeSpecification('username', 'john_doe'),
    ))
```

## Best Practices

* **Define Clear Interfaces:** Always define an abstract interface for your repository (e.g., `UserRepositoryInterface`) that extends `CrudRepositoryInterface` or `AsyncCrudRepositoryInterface`. This promotes loose coupling and makes your code easier to test and maintain.
* **Separate Concerns:** Keep your SQLAlchemy models (`UserTable`) separate from your business models (Pydantic `User`). The repository acts as the bridge between these two layers, converting data as needed.
* **Implement Abstract Methods:** When implementing `SqlAlchemyCrudRepository` or `AsyncSqlAlchemyCrudRepository`, ensure you correctly implement all abstract methods (`_db_model_class`, `_model_class`, `_apply_id_filter_condition`, `_convert_db_item_to_model`, `_create_db_item`, `_update_db_item`, `_apply_default_filter`, `_apply_default_order`, `_create_session`). These methods are crucial for the repository's functionality.
* **Session Management:** The `_create_session` method is responsible for providing a SQLAlchemy session. For synchronous repositories, use `sessionmaker()`. For asynchronous repositories, use `async_sessionmaker()` and ensure your session is properly managed (e.g., using `async with self._create_session() as session:` for async operations).
* **Custom Queries:** For queries that go beyond simple CRUD and specification-based filtering (e.g., complex joins, aggregations), add custom methods to your repository interface and implement them directly within your concrete repository class. These methods should leverage SQLAlchemy's powerful query capabilities.
* **Error Handling:** Utilize the custom exceptions provided by `abstractrepo` (e.g., `ItemNotFoundException`, `UniqueViolationException`) for consistent error handling across your application.
* **Type Hinting:** Leverage Python's type hinting extensively. It improves code readability, enables better IDE support, and helps catch errors early.

## Dependencies

* Python 3.7+
* abstractrepo >= 1.4.2
* sqlalchemy >= 2.0.0

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more information.
