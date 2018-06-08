from typing import (
    Dict,
    Any,
)


class RedisClient(object):

    def __init__(self, *args, **kwargs):
        self.__data: Dict[str, str] = {}

    @classmethod
    def from_url(cls, _: str) -> 'RedisClient':
        return cls()

    def ping(self) -> None:
        pass

    def get(self, key: str) -> Any:
        return self.__data.get(key, None)

    def set(self, key: str, value: Any) -> None:
        self.__data[key] = value
