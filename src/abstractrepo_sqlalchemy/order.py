from typing import List, Generic

from abstractrepo.order import OrderOptions, OrderOption, OrderDirection, NonesOrder, OrderOptionsConverterInterface
from sqlalchemy import UnaryExpression, asc, desc

from abstractrepo_sqlalchemy.types import TDbModel


class SqlAlchemyOrderOptions(Generic[TDbModel], OrderOptions):
    def to_expression(self, model: type[TDbModel]) -> List[UnaryExpression]:
        return [self._get_expression(item, model) for item in self._options]

    @staticmethod
    def _get_expression(item: OrderOption, model: type[TDbModel]) -> UnaryExpression:
        column = getattr(model, item.attribute)

        query = asc(column) if item.direction == OrderDirection.ASC else desc(column)
        # TODO use default nones order
        query = query.nulls_first() if item.nones == NonesOrder.FIRST else query.nulls_last()

        return query


class SqlAlchemyOptionsConverter(Generic[TDbModel], OrderOptionsConverterInterface):
    def convert(self, order: OrderOptions) -> SqlAlchemyOrderOptions:
        return SqlAlchemyOrderOptions[TDbModel](*order.options)
