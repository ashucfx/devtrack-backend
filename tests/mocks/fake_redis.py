import fnmatch
import time
from typing import Any


class FakePipeline:
    """Mock Redis Pipeline supporting sliding-window log commands."""

    def __init__(self, fake_redis: "FakeAsyncRedis") -> None:
        self.fake_redis = fake_redis
        self.commands: list[tuple[str, tuple, dict]] = []

    async def __aenter__(self) -> "FakePipeline":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    def zremrangebyscore(self, key: str, min_score: float, max_score: float) -> "FakePipeline":
        self.commands.append(("zremrangebyscore", (key, min_score, max_score), {}))
        return self

    def zadd(self, key: str, mapping: dict[str, float]) -> "FakePipeline":
        self.commands.append(("zadd", (key, mapping), {}))
        return self

    def zcard(self, key: str) -> "FakePipeline":
        self.commands.append(("zcard", (key,), {}))
        return self

    def expire(self, key: str, seconds: int) -> "FakePipeline":
        self.commands.append(("expire", (key, seconds), {}))
        return self

    async def execute(self) -> list[Any]:
        results = []
        for cmd, args, kwargs in self.commands:
            method = getattr(self.fake_redis, f"_{cmd}")
            res = method(*args, **kwargs)
            results.append(res)
        self.commands.clear()
        return results


class FakeAsyncRedis:
    """In-memory async Redis stand-in for deterministic local unit tests."""

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._zsets: dict[str, dict[str, float]] = {}
        self._ttls: dict[str, float] = {}

    async def ping(self) -> bool:
        return True

    async def get(self, key: str) -> str | None:
        self._cleanup_expired(key)
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self._store[key] = value
        if ex:
            self._ttls[key] = time.time() + ex
        elif key in self._ttls:
            del self._ttls[key]
        return True

    async def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                count += 1
            if k in self._zsets:
                del self._zsets[k]
                count += 1
            if k in self._ttls:
                del self._ttls[k]
        return count

    async def scan(
        self, cursor: int = 0, match: str | None = None, count: int = 100
    ) -> tuple[int, list[str]]:
        _ = (cursor, count)
        all_keys = list(self._store.keys()) + list(self._zsets.keys())
        matched = [k for k in all_keys if fnmatch.fnmatch(k, match)] if match else all_keys
        return 0, matched

    def pipeline(self, transaction: bool = True) -> FakePipeline:
        _ = transaction
        return FakePipeline(self)

    def _zremrangebyscore(self, key: str, min_score: float, max_score: float) -> int:
        if key not in self._zsets:
            return 0
        zset = self._zsets[key]
        to_del = [m for m, s in zset.items() if min_score <= s <= max_score]
        for m in to_del:
            del zset[m]
        return len(to_del)

    def _zadd(self, key: str, mapping: dict[str, float]) -> int:
        if key not in self._zsets:
            self._zsets[key] = {}
        self._zsets[key].update(mapping)
        return len(mapping)

    def _zcard(self, key: str) -> int:
        return len(self._zsets.get(key, {}))

    def _expire(self, key: str, seconds: int) -> bool:
        self._ttls[key] = time.time() + seconds
        return True

    def _cleanup_expired(self, key: str) -> None:
        if key in self._ttls and time.time() > self._ttls[key]:
            self._store.pop(key, None)
            self._zsets.pop(key, None)
            self._ttls.pop(key, None)

    async def aclose(self) -> None:
        self._store.clear()
        self._zsets.clear()
        self._ttls.clear()
