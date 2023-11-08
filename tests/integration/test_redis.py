import logging

import pytest
import redis

from quart_depends import Depends, inject

redis_dsn = "redis://localhost:6379/0"

logger = logging.getLogger(__name__)

client = redis.Redis.from_url(redis_dsn, decode_responses=True, protocol=3)


def get_client() -> redis.Redis:
    yield client


@inject
def view(client: redis.Redis = Depends(get_client)):
    client.set("x", "foo")
    return client.get("x")


class TestRedis:
    @pytest.fixture(autouse=True)
    def client_mock(self, mocker):
        mocker.patch.object(client, "connection")
        mocker.patch.object(client, "connection_pool")

    def test_sync_client_dependency(self):
        result = view()
        assert result
