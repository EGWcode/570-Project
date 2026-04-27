# redis_config.py
#
#     FLOW - Enterprise Restaurant Management System
#     CSC 570 Sp 26'
#     Created by Day Ekoi - April 21-23, 2026
#
# Manages the Redis connection for the FLOW system.
# Provides helpers for cache operations, table status tracking,
# and real-time order pub/sub used by the staff and manager interfaces.
#
# Functions:
#   - get_redis()               : returns the shared Redis client
#   - cache_set()               : stores a key/value with optional TTL
#   - cache_get()               : retrieves a cached value
#   - cache_delete()            : removes a cached key
#   - set_table_status()        : caches a table's occupancy status
#   - get_table_status()        : returns cached table status
#   - publish_order_update()    : publishes order status change to branch channel

import os, json
import redis
from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB   = int(os.getenv("REDIS_DB", 0))

_client = None


def get_redis():
    """Returns the shared Redis client, creating it on first call."""
    global _client
    if _client is None:
        _client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=3
        )
    return _client


def cache_set(key, value, ttl=300):
    """Stores a value in Redis with an optional TTL in seconds (default 5 min)."""
    try:
        get_redis().set(key, value, ex=ttl)
        return True
    except Exception:
        return False


def cache_get(key):
    """Returns a cached value, or None if missing or Redis is unavailable."""
    try:
        return get_redis().get(key)
    except Exception:
        return None


def cache_delete(key):
    """Removes a key from the cache."""
    try:
        get_redis().delete(key)
        return True
    except Exception:
        return False


def set_table_status(branch_id, table_number, status):
    """Caches a table's occupancy status with a 1-hour TTL."""
    return cache_set(f"table:{branch_id}:{table_number}", status, ttl=3600)


def get_table_status(branch_id, table_number):
    """Returns the cached occupancy status for a table, defaults to 'available'."""
    return cache_get(f"table:{branch_id}:{table_number}") or "available"


def publish_order_update(branch_id, order_id, status):
    """Publishes an order status change to the branch-specific orders channel."""
    try:
        msg = json.dumps({"order_id": order_id, "status": status})
        get_redis().publish(f"orders:{branch_id}", msg)
        return True
    except Exception:
        return False
