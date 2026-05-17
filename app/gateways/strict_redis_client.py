from __future__ import annotations

import hashlib
from typing import Iterable, List, Optional

from redis import StrictRedis


class StrictRedisClient:
    def __init__(
            self,
            master_urls: Iterable[str],
            slave_urls: Iterable[str],
            decode_responses: bool = True,
            socket_connect_timeout_seconds: float = 5.0,
            socket_timeout_seconds: float = 5.0,
            read_from_slaves: bool = False,
    ) -> None:
        self.master_urls = [url.strip() for url in master_urls if url and url.strip()]
        self.slave_urls = [url.strip() for url in slave_urls if url and url.strip()]
        if not self.master_urls:
            raise ValueError("At least one Redis master URL is required.")
        self.decode_responses = decode_responses
        self.socket_connect_timeout_seconds = socket_connect_timeout_seconds
        self.socket_timeout_seconds = socket_timeout_seconds
        self.read_from_slaves = read_from_slaves
        self.master_clients = self.create_clients(self.master_urls)
        self.slave_clients = self.create_clients(self.slave_urls)

    def create_clients(self, urls: Iterable[str]) -> List[StrictRedis]:
        return [
            StrictRedis.from_url(
                url,
                decode_responses=self.decode_responses,
                socket_connect_timeout=self.socket_connect_timeout_seconds,
                socket_timeout=self.socket_timeout_seconds,
            )
            for url in urls
        ]

    def select_index_for_key(self, key: str, client_count: int) -> int:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return int(digest, 16) % client_count

    def select_master_client(self, key: str) -> StrictRedis:
        return self.master_clients[self.select_index_for_key(key, len(self.master_clients))]

    def select_slave_client(self, key: str) -> Optional[StrictRedis]:
        if not self.read_from_slaves or not self.slave_clients:
            return None
        return self.slave_clients[self.select_index_for_key(key, len(self.slave_clients))]

    def get(self, key: str):
        slave_client = self.select_slave_client(key)
        if slave_client is not None:
            value = slave_client.get(key)
            if value is not None:
                return value
        return self.select_master_client(key).get(key)

    def set(self, key: str, value: str) -> None:
        self.select_master_client(key).set(key, value)

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        self.select_master_client(key).setex(key, max(1, int(ttl_seconds)), value)

    def delete(self, key: str) -> None:
        self.select_master_client(key).delete(key)

    def getdel(self, key: str):
        redis_client = self.select_master_client(key)
        if hasattr(redis_client, "getdel"):
            return redis_client.getdel(key)
        value = redis_client.get(key)
        redis_client.delete(key)
        return value

    def ping(self) -> bool:
        for master_client in self.master_clients:
            master_client.ping()
        for slave_client in self.slave_clients:
            slave_client.ping()
        return True

    def close(self) -> None:
        for redis_client in [*self.master_clients, *self.slave_clients]:
            redis_client.close()
