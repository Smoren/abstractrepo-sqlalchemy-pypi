import pickle
from typing import Tuple, List

import pytest

from abstractrepo.specification import SpecificationInterface, AttributeSpecification, Operator
from tests.fixtures.models import News
from tests.fixtures.repo import SqlAlchemyNewsRepository, AsyncSqlAlchemyNewsRepository
from tests.fixtures.utils import dumps
from tests.providers.filter import data_provider_for_news_filter, data_provider_for_news_collection, \
    data_provider_for_news_collection_async


@pytest.mark.parametrize("items", data_provider_for_news_collection(101, with_no_text_item=True))
@pytest.mark.parametrize("test_case", data_provider_for_news_filter())
def test_filter(items: List[News], test_case: Tuple[SpecificationInterface[News, bool], List[News]]):
    filter_spec, expected = test_case
    repo = SqlAlchemyNewsRepository()
    repo.create_default_mock_collection(items)
    actual = repo.get_collection(filter_spec=filter_spec)
    actual_count = repo.count(filter_spec=filter_spec)
    assert dumps(actual) == dumps(expected)
    assert actual_count == len(expected)


@pytest.mark.asyncio
@pytest.mark.parametrize("items", data_provider_for_news_collection_async(101, with_no_text_item=True))
@pytest.mark.parametrize("test_case", data_provider_for_news_filter())
async def test_filter_async(items: List[News], test_case: Tuple[SpecificationInterface[News, bool], List[News]]):
    filter_spec, expected = test_case
    repo = AsyncSqlAlchemyNewsRepository()
    await repo.create_default_mock_collection(items)
    actual = await repo.get_collection(filter_spec=filter_spec)
    actual_count = await repo.count(filter_spec=filter_spec)
    assert dumps(actual) == dumps(expected)
    assert actual_count == len(expected)


@pytest.mark.parametrize("items", data_provider_for_news_collection(100))
def test_filter_errors(items: List[News]):
    repo = SqlAlchemyNewsRepository()
    repo.create_default_mock_collection(items)

    with pytest.raises(ValueError):
        repo.get_collection(AttributeSpecification('id', 12, Operator.IN))

    with pytest.raises(ValueError):
        repo.get_collection(AttributeSpecification('id', 12, Operator.NOT_IN))

    with pytest.raises(TypeError):
        repo.get_collection(AttributeSpecification('id', 12, 'UnsupportedOperator'))

    with pytest.raises(TypeError):
        repo.get_collection({})


@pytest.mark.asyncio
@pytest.mark.parametrize("items", data_provider_for_news_collection_async(100))
async def test_filter_errors_async(items: List[News]):
    repo = AsyncSqlAlchemyNewsRepository()
    await repo.create_default_mock_collection(items)

    with pytest.raises(ValueError):
        await repo.get_collection(AttributeSpecification('id', 12, Operator.IN))

    with pytest.raises(ValueError):
        await repo.get_collection(AttributeSpecification('id', 12, Operator.NOT_IN))

    with pytest.raises(TypeError):
        await repo.get_collection(AttributeSpecification('id', 12, 'UnsupportedOperator'))

    with pytest.raises(TypeError):
        await repo.get_collection({})
