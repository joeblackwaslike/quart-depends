import logging
from datetime import datetime, timezone

import pytest
import sqlalchemy
import sqlalchemy.ext.asyncio
import sqlalchemy.orm
from sqlalchemy.orm import Mapped, mapped_column

from quart_depends import Depends, inject

sa = sqlalchemy

logger = logging.getLogger(__name__)

db_url = "sqlite:///file:mem.db?mode=memory&cache=shared&uri=true"
metadata = sa.MetaData()
engine = sa.create_engine(db_url, connect_args={"check_same_thread": False}, echo=True)
Session = sa.orm.sessionmaker(bind=engine, expire_on_commit=False)

async_db_url = "sqlite+aiosqlite:///file:mem.db?mode=memory&cache=shared&uri=true"
async_engine = sa.ext.asyncio.create_async_engine(
    async_db_url,
    connect_args={"check_same_thread": False},
    echo=True,
)
AsyncSession = sa.ext.asyncio.async_sessionmaker(bind=async_engine, expire_on_commit=False)


def get_session() -> sa.orm.Session:
    with Session() as session:
        yield session


async def get_async_session() -> sa.ext.asyncio.AsyncSession:
    async with AsyncSession() as session:
        yield session


class Base(sa.orm.DeclarativeBase):
    pass


user = sa.Table(
    "user",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("name", sa.String),
)


class User(Base):
    __tablename__ = "user_orm"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column()
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


@pytest.fixture(autouse=True, scope="session")
def setup_sa_events():
    def do_connect(dbapi_connection, connection_record):
        # disable pysqlite's emitting of the BEGIN statement entirely.
        # also stops it from emitting COMMIT before any DDL.
        dbapi_connection.isolation_level = None

    if not sa.event.contains(engine, "connect", do_connect):
        sa.event.listen(engine, "connect", do_connect)

    if not sa.event.contains(async_engine.sync_engine, "connect", do_connect):
        sa.event.listen(async_engine.sync_engine, "connect", do_connect)

    def do_begin(conn_):
        # emit our own BEGIN
        conn_.exec_driver_sql("BEGIN")

    if not sa.event.contains(engine, "begin", do_begin):
        sa.event.listen(engine, "begin", do_begin)

    if not sa.event.contains(async_engine.sync_engine, "begin", do_begin):
        sa.event.listen(async_engine.sync_engine, "begin", do_begin)


@inject
def view(session: sa.orm.Session = Depends(get_session)):
    with session.begin():
        session.execute(sa.insert(user).values(name="test"))
        session.execute(sa.insert(user).values(name="test2"))

    result = session.execute(sa.select(user).where(user.c.name == "test")).one()
    return result


@inject
async def async_view(session: sa.ext.asyncio.AsyncSession = Depends(get_async_session)):
    async with session.begin():
        await session.execute(sa.insert(user).values(name="test"))
        await session.execute(sa.insert(user).values(name="test2"))

    result = (await session.execute(sa.select(user).where(user.c.name == "test"))).one()
    return result


class TestDatabase:
    @pytest.fixture(autouse=True, scope="session")
    def init_db(self):
        metadata.create_all(engine)

    @pytest.fixture(autouse=True)
    def rollback_sync(self):
        with engine.connect() as conn:
            with conn.begin() as trans:
                with conn.begin_nested():
                    prev_bind = Session.kw["bind"]
                    Session.configure(bind=conn, join_transaction_mode="create_savepoint")
                    yield conn
                    Session.configure(bind=prev_bind)
                trans.rollback()

    def test_sync_session_dependency(self):
        result = view()
        assert result == (1, "test")

    def test_sync_session_dependency_again(self):
        result = view()
        assert result == (1, "test")


class TestAsyncDatabase:
    @pytest.fixture(autouse=True, scope="session")
    async def init_db(self):
        async with async_engine.connect() as conn:
            async with conn.begin():

                def sync_call(conn: sa.Connection):
                    metadata.create_all(bind=conn)

                return await conn.run_sync(sync_call)

    @pytest.fixture(autouse=True)
    async def rollback_async(self):
        async with async_engine.connect() as conn:
            async with conn.begin() as trans:
                async with conn.begin_nested():
                    prev_bind = AsyncSession.kw["bind"]
                    AsyncSession.configure(bind=conn, join_transaction_mode="create_savepoint")
                    yield conn
                    AsyncSession.configure(bind=prev_bind)
                await trans.rollback()

    async def test_async_session_dependency(self):
        result = await async_view()
        assert result == (1, "test")

    async def test_async_session_dependency_again(self):
        result = await async_view()
        assert result == (1, "test")

        # import pdb; pdb.set_trace()


# async def test_generator_dependency_async(self):
#     async def dependency():
#         db = DBSession("sqlite://")
#         try:
#             yield db
#         finally:
#             db.close()

#     @inject
#     async def view(db: DBSession = Depends(dependency)):
#         db.add(1)
#         db.add(2)
#         db.commit()
#         return db

#     db = await view()

#     assert db.committed == True
#     assert db.closed == True
#     assert db.rolled_back == False
