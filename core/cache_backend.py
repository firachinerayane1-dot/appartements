"""Cache failures must not prevent booking or rendering pages."""
import logging
from django.core.cache.backends.redis import RedisCache
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

class ResilientRedisCache(RedisCache):
    def get(self, key, default=None, version=None):
        try:
            return super().get(key, default, version)
        except RedisError:
            logger.warning('Redis unavailable: cache read skipped')
            return default

    def set(self, key, value, timeout=300, version=None):
        try:
            return super().set(key, value, timeout, version)
        except RedisError:
            logger.warning('Redis unavailable: cache write skipped')
            return False

    def delete(self, key, version=None):
        try:
            return super().delete(key, version)
        except RedisError:
            logger.warning('Redis unavailable: cache invalidation skipped')
            return False
