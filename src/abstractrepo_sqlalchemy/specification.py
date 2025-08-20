import abc
from typing import Generic

from sqlalchemy import and_, or_, not_, ColumnElement
from sqlalchemy.sql.elements import SQLColumnExpression

from abstractrepo.specification import (
    SpecificationInterface, AndSpecification, OrSpecification,
    NotSpecification, SpecificationConverterInterface, AttributeSpecification,
    Operator, BaseAndSpecification, BaseOrSpecification, BaseNotSpecification,
    BaseAttributeSpecification,
)

from abstractrepo_sqlalchemy.types import TDbModel


class SqlAlchemySpecificationInterface(
    Generic[TDbModel],
    SpecificationInterface[TDbModel, SQLColumnExpression[bool]],
    abc.ABC
):
    @abc.abstractmethod
    def is_satisfied_by(self, model: TDbModel) -> SQLColumnExpression[bool]:
        raise NotImplementedError()


class SqlAlchemyAndSpecification(
    Generic[TDbModel],
    BaseAndSpecification[TDbModel, SQLColumnExpression[bool]],
    SqlAlchemySpecificationInterface[TDbModel],
):
    def is_satisfied_by(self, model: TDbModel) -> SQLColumnExpression[bool]:
        return and_(*[spec.is_satisfied_by(model) for spec in self.specifications])


class SqlAlchemyOrSpecification(
    Generic[TDbModel],
    BaseOrSpecification[TDbModel, SQLColumnExpression[bool]],
    SqlAlchemySpecificationInterface[TDbModel],
):
    def is_satisfied_by(self, model: TDbModel) -> SQLColumnExpression[bool]:
        return or_(*[spec.is_satisfied_by(model) for spec in self.specifications])


class SqlAlchemyNotSpecification(
    Generic[TDbModel],
    BaseNotSpecification[TDbModel, SQLColumnExpression[bool]],
    SqlAlchemySpecificationInterface[TDbModel],
):
    def is_satisfied_by(self, model: TDbModel) -> SQLColumnExpression[bool]:
        return not_(self.specification.is_satisfied_by(model))


class SqlAlchemyAttributeSpecification(
    Generic[TDbModel],
    BaseAttributeSpecification[TDbModel, SQLColumnExpression[bool]],
    SqlAlchemySpecificationInterface[TDbModel],
):
    def is_satisfied_by(self, model: TDbModel) -> SQLColumnExpression[bool]:
        model_attr = self._get_db_model_attr(model, self.attribute_name)
        if self.operator == Operator.E:
            return model_attr.__eq__(self.attribute_value)
        if self.operator == Operator.NE:
            return model_attr.__ne__(self.attribute_value)
        if self.operator == Operator.GT:
            return model_attr > self.attribute_value
        if self.operator == Operator.LT:
            return model_attr < self.attribute_value
        if self.operator == Operator.GTE:
            return model_attr >= self.attribute_value
        if self.operator == Operator.LTE:
            return model_attr <= self.attribute_value
        if self.operator == Operator.LIKE:
            return model_attr.like(self.attribute_value)
        if self.operator == Operator.ILIKE:
            return model_attr.ilike(self.attribute_value)
        if self.operator == Operator.IN:
            if isinstance(self.attribute_value, list):
                return model_attr.in_(self.attribute_value)
            raise ValueError('Attribute value must be a list')
        if self.operator == Operator.NOT_IN:
            if isinstance(self.attribute_value, list):
                return model_attr.not_in(self.attribute_value)
            raise ValueError('Attribute value must be a list')
        raise TypeError(f'Unsupported operator: {self.operator}')

    @staticmethod
    def _get_db_model_attr(model: TDbModel, attr_name: str) -> ColumnElement:
        return getattr(model, attr_name)


class SqlAlchemySpecificationConverter(
    Generic[TDbModel],
    SpecificationConverterInterface[object, bool, TDbModel, SQLColumnExpression[bool]],
):
    def convert(
        self,
        specification: SpecificationInterface[TDbModel, bool],
    ) -> SpecificationInterface[TDbModel, SQLColumnExpression[bool]]:
        if isinstance(specification, AndSpecification):
            return SqlAlchemyAndSpecification[TDbModel](*[self.convert(spec) for spec in specification.specifications])
        if isinstance(specification, OrSpecification):
            return SqlAlchemyOrSpecification[TDbModel](*[self.convert(spec) for spec in specification.specifications])
        if isinstance(specification, NotSpecification):
            return SqlAlchemyNotSpecification[TDbModel](self.convert(specification.specification))
        if isinstance(specification, AttributeSpecification):
            return SqlAlchemyAttributeSpecification[TDbModel](
                specification.attribute_name,
                specification.attribute_value,
                specification.operator,
            )
        raise TypeError(f'Unsupported specification type: {type(specification)}')
