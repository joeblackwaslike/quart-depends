import logging

from quart_depends import Depends
from quart_depends import inject


logger = logging.getLogger(__name__)


class DBSession:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.closed = False
        self.committed = False
        self.rolled_back = False
        self._queue = []

    def add(self, item):
        self._queue.append(item)

    def commit(self):
        logger.info("Committing transaction", items=self._queue)
        self._queue.clear()
        self.committed = True

    def rollback(self):
        logger.info("Rolling back transaction", items=self._queue)
        self._queue.clear()
        self.rolled_back = True

    def close(self):
        self.closed = True


class TestGenerators:
    def test_generator_dependency(self):
        def dependency():
            db = DBSession("sqlite://")
            try:
                yield db
            finally:
                db.close()

        @inject
        def view(db: DBSession = Depends(dependency)):
            db.add(1)
            db.add(2)
            db.commit()
            return db

        db = view()

        assert db.committed is True
        assert db.closed is True
        assert db.rolled_back is False

    async def test_generator_dependency_async(self):
        async def dependency():
            db = DBSession("sqlite://")
            try:
                yield db
            finally:
                db.close()

        @inject
        async def view(db: DBSession = Depends(dependency)):
            db.add(1)
            db.add(2)
            db.commit()
            return db

        db = await view()

        assert db.committed is True
        assert db.closed is True
        assert db.rolled_back is False
