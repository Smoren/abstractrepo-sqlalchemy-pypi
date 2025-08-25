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

from abstractrepo_sqlalchemy.types import TDbModelType


class SqlAlchemySpecificationInterface(
    Generic[TDbModelType],
    SpecificationInterface[TDbModelType, SQLColumnExpression[bool]],
    abc.ABC
):
    """Abstract base class for SQLAlchemy-specific specifications.

    This interface extends `SpecificationInterface` to work with SQLAlchemy database
    models (`TDbModelClass`) and produce SQLAlchemy `SQLColumnExpression[bool]` results,
    which can be used directly in SQLAlchemy query filters.

    Type Parameters:
        TDbModelType: The SQLAlchemy database model type.
    """
    @abc.abstractmethod
    def is_satisfied_by(self, model: TDbModelType) -> SQLColumnExpression[bool]:
        """Evaluates the specification against the given SQLAlchemy database model class.

        Args:
            model: The SQLAlchemy database model class.

        Returns:
            A SQLAlchemy `SQLColumnExpression[bool]` that represents the result of evaluating the specification.
        """
        raise NotImplementedError()


class SqlAlchemyAndSpecification(
    Generic[TDbModelType],
    BaseAndSpecification[TDbModelType, SQLColumnExpression[bool]],
    SqlAlchemySpecificationInterface[TDbModelType],
):
    """A SQLAlchemy-specific implementation of an AND logical specification.

    This specification combines multiple SQLAlchemy-compatible specifications
    with a logical AND operation. All contained specifications must evaluate
    to true for this specification to be satisfied.

    Type Parameters:
        TDbModelType: The SQLAlchemy database model type.
    """
    def is_satisfied_by(self, model: TDbModelType) -> SQLColumnExpression[bool]:
        """Combines the contained specifications with a SQLAlchemy AND operation.

        Args:
            model: The SQLAlchemy database model class.

        Returns:
            A SQLAlchemy `SQLColumnExpression[bool]` representing the combined AND condition.
        """
        return and_(*[spec.is_satisfied_by(model) for spec in self.specifications])


class SqlAlchemyOrSpecification(
    Generic[TDbModelType],
    BaseOrSpecification[TDbModelType, SQLColumnExpression[bool]],
    SqlAlchemySpecificationInterface[TDbModelType],
):
    """A SQLAlchemy-specific implementation of an OR logical specification.

    This specification combines multiple SQLAlchemy-compatible specifications
    with a logical OR operation. At least one contained specification must evaluate
    to true for this specification to be satisfied.

    Type Parameters:
        TDbModelType: The SQLAlchemy database model type.
    """
    def is_satisfied_by(self, model: TDbModelType) -> SQLColumnExpression[bool]:
        """Combines the contained specifications with a SQLAlchemy OR operation.

        Args:
            model: The SQLAlchemy database model class.

        Returns:
            A SQLAlchemy `SQLColumnExpression[bool]` representing the combined OR condition.
        """
        return or_(*[spec.is_satisfied_by(model) for spec in self.specifications])


class SqlAlchemyNotSpecification(
    Generic[TDbModelType],
    BaseNotSpecification[TDbModelType, SQLColumnExpression[bool]],
    SqlAlchemySpecificationInterface[TDbModelType],
):
    """A SQLAlchemy-specific implementation of a NOT logical specification.

    This specification negates the result of its contained SQLAlchemy-compatible specification.

    Type Parameters:
        TDbModelType: The SQLAlchemy database model type.
    """
    def is_satisfied_by(self, model: TDbModelType) -> SQLColumnExpression[bool]:
        """Negates the contained specification using SQLAlchemy's `not_` operator.

        Args:
            model: The SQLAlchemy database model class.

        Returns:
            A SQLAlchemy `SQLColumnExpression[bool]` representing the negated condition.
        """
        return not_(self.specification.is_satisfied_by(model))


class SqlAlchemyAttributeSpecification(
    Generic[TDbModelType],
    BaseAttributeSpecification[TDbModelType, SQLColumnExpression[bool]],
    SqlAlchemySpecificationInterface[TDbModelType],
):
    """A SQLAlchemy-specific implementation of an attribute-based specification.

    This specification evaluates a SQLAlchemy database model based on the value
    of a specific attribute and a given comparison operator, producing a
    SQLAlchemy-compatible expression.

    Type Parameters:
        TDbModelType: The SQLAlchemy database model type.
    """
    def is_satisfied_by(self, model: TDbModelType) -> SQLColumnExpression[bool]:
        """Generates an SQLAlchemy column expression for the attribute comparison.

        Args:
            model: The SQLAlchemy database model class.

        Returns:
            A SQLAlchemy `SQLColumnExpression[bool]` representing the comparison condition.

        Raises:
            ValueError: If the attribute value type is not compatible with the operator (e.g., IN/NOT_IN with non-list).
            TypeError: If an unsupported operator is provided.
        """
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
    def _get_db_model_attr(model: TDbModelType, attr_name: str) -> ColumnElement:
        """Retrieves a SQLAlchemy ColumnElement from a given model by attribute name.

        Args:
            model: The SQLAlchemy database model instance.
            attr_name: The name of the attribute to retrieve.

        Returns:
            A SQLAlchemy ColumnElement corresponding to the attribute.
        """
        return getattr(model, attr_name)


class SqlAlchemySpecificationConverter(
    Generic[TDbModelType],
    SpecificationConverterInterface[object, bool, TDbModelType, SQLColumnExpression[bool]],
):
    """Converts generic `SpecificationInterface` instances into SQLAlchemy-specific specifications.

    This converter traverses the abstract specification tree and transforms each node
    (And, Or, Not, Attribute specifications) into its corresponding SQLAlchemy-compatible
    representation. This allows for applying abstract business logic specifications
    directly to SQLAlchemy queries.

    Type Parameters:
        TDbModelType: The SQLAlchemy database model type.
    """
    def convert(
        self,
        specification: SpecificationInterface[object, bool],
    ) -> SpecificationInterface[TDbModelType, SQLColumnExpression[bool]]:
        """Converts a generic `SpecificationInterface` to a SQLAlchemy-compatible specification.

        This method recursively converts the given specification and its nested
        components into SQLAlchemy-specific specification types.

        Args:
            specification: The generic specification to convert.

        Returns:
            A SQLAlchemy-compatible `SpecificationInterface` that can be used in queries.

        Raises:
            TypeError: If an unsupported specification type is encountered.
        """
        if isinstance(specification, AndSpecification):
            return SqlAlchemyAndSpecification[TDbModelType](*[self.convert(spec) for spec in specification.specifications])
        if isinstance(specification, OrSpecification):
            return SqlAlchemyOrSpecification[TDbModelType](*[self.convert(spec) for spec in specification.specifications])
        if isinstance(specification, NotSpecification):
            return SqlAlchemyNotSpecification[TDbModelType](self.convert(specification.specification))
        if isinstance(specification, AttributeSpecification):
            return SqlAlchemyAttributeSpecification[TDbModelType](
                specification.attribute_name,
                specification.attribute_value,
                specification.operator,
            )
        raise TypeError(f'Unsupported specification type: {type(specification)}')
