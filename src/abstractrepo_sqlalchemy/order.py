from typing import List, Generic

from abstractrepo.order import OrderOptions, OrderOption, OrderDirection, NonesOrder, OrderOptionsConverterInterface
from sqlalchemy import UnaryExpression, asc, desc

from abstractrepo_sqlalchemy.types import TDbModel


class SqlAlchemyOrderOptions(Generic[TDbModel], OrderOptions):
    """A specialized OrderOptions class for SQLAlchemy, providing conversion to SQLAlchemy expressions.

    This class extends `OrderOptions` from `abstractrepo` and adds the capability
    to convert the defined ordering criteria into SQLAlchemy `UnaryExpression` objects,
    which can be used directly in `order_by()` clauses.

    Type Parameters:
        TDbModel: The SQLAlchemy database model type.
    """
    def to_expression(self, model: type[TDbModel]) -> List[UnaryExpression]:
        return [self._get_expression(item, model) for item in self._options]

    @staticmethod
    def _get_expression(item: OrderOption, model: type[TDbModel]) -> UnaryExpression:
        """Converts a single OrderOption into a SQLAlchemy UnaryExpression.

        Args:
            item: The OrderOption instance to convert.
            model: The SQLAlchemy database model class.

        Returns:
            A SQLAlchemy UnaryExpression representing the ordering criterion.
        """
        column = getattr(model, item.attribute)

        query = asc(column) if item.direction == OrderDirection.ASC else desc(column)
        query = query.nulls_first() if item.nones == NonesOrder.FIRST else query.nulls_last()

        return query


class SqlAlchemyOrderOptionsConverter(Generic[TDbModel], OrderOptionsConverterInterface):
    """Converts generic `OrderOptions` into `SqlAlchemyOrderOptions`.

    This converter is responsible for adapting the abstract `OrderOptions`
    from `abstractrepo` into the SQLAlchemy-specific `SqlAlchemyOrderOptions`,
    which can then be used to generate SQLAlchemy ordering expressions.

    Type Parameters:
        TDbModel: The SQLAlchemy database model type.
    """
    def convert(self, order: OrderOptions) -> SqlAlchemyOrderOptions:
        """Converts an `OrderOptions` instance to a `SqlAlchemyOrderOptions` instance.

        Args:
            order: The `OrderOptions` instance to convert.

        Returns:
            A `SqlAlchemyOrderOptions` instance containing the converted order options.
        """
        return SqlAlchemyOrderOptions[TDbModel](*order.options)
