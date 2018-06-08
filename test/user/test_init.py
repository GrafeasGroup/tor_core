import pytest
import unittest
from unittest.mock import patch

from ..mock_redis import RedisClient
import redis

from tor_core.users import (
    User,
    UserConnectionError,
    UserError,
)


class BadRedisClient(RedisClient):
    def ping(self) -> None:
        raise redis.exceptions.ConnectionError()


class InitUserTest(unittest.TestCase):
    """
    Tests how the `tor_core.users.User` model initializes with a Redis
    connection
    """

    @patch('tor_core.users.redis.StrictRedis.from_url', side_effect=RedisClient,
           spec=RedisClient)
    def test_default_init(self, mock_redis):
        u = User('my_username')

        mock_redis.assert_called_once()

        assert u.username == 'my_username'
        assert u.get('username') == 'my_username', \
            'Does not populate default data structure'

    @patch('tor_core.users.redis.StrictRedis.from_url', side_effect=RedisClient,
           spec=RedisClient)
    def test_redisconn_init(self, mock_redis):
        client = RedisClient()
        u = User('my_username', redis_conn=client)

        mock_redis.assert_not_called()

        assert u.username == 'my_username'
        assert u.get('username') == 'my_username', \
            'Does not populate default data structure'

    @patch('tor_core.users.redis.StrictRedis.from_url', side_effect=RedisClient,
           spec=RedisClient)
    def test_no_userdata_init(self, mock_redis):
        redis = RedisClient()
        u = User('my_username', redis_conn=redis, create_if_not_found=False)
        mock_redis.assert_not_called()

        assert u.username == 'my_username'

        with pytest.raises(AttributeError):
            u.get('username')

    @patch('tor_core.users.redis.StrictRedis.from_url', side_effect=RedisClient,
           spec=RedisClient)
    def test_no_username_init(self, mock_redis):
        client = RedisClient()
        with pytest.raises(UserError):
            User(redis_conn=client)

    @patch('tor_core.users.redis.StrictRedis.from_url',
           side_effect=BadRedisClient, spec=BadRedisClient)
    def test_bad_redis_connection_init(self, mock_redis):
        with pytest.raises(UserConnectionError):
            User('my_username')
