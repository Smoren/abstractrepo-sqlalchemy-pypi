from mock_alchemy.mocking import UnifiedAlchemyMagicMock

from tests.fixtures.models import Base


class MyUnifiedAlchemyMagicMock(UnifiedAlchemyMagicMock):
    _next_id = 1

    def refresh(self, item: Base) -> None:
        if hasattr(item, 'id'):
            item.id = self._next_id
            self._next_id += 1
            self.commit()
