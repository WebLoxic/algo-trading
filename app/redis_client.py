# app/redis_client.py
import os
import json
import redis
from typing import Optional, Dict

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

# single redis client for sync usage
_redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

PUBSUB_CHANNEL = "signals"

def ping() -> bool:
    try:
        return _redis.ping()
    except Exception:
        return False

def set_last_signal(instrument_token: str, payload: Dict, expire_seconds: Optional[int] = 300):
    """
    Store last signal in Redis as JSON string. Optional TTL (default 5 minutes).
    Key: last_signal:{instrument_token}
    """
    key = f"last_signal:{instrument_token}"
    _redis.set(key, json.dumps(payload))
    if expire_seconds:
        _redis.expire(key, int(expire_seconds))

def get_last_signal(instrument_token: str) -> Optional[Dict]:
    key = f"last_signal:{instrument_token}"
    v = _redis.get(key)
    if not v:
        return None
    try:
        return json.loads(v)
    except Exception:
        return None

def publish_signal(payload: Dict):
    """
    Publish a signal to the pubsub channel (fast notifications).
    """
    try:
        _redis.publish(PUBSUB_CHANNEL, json.dumps(payload))
    except Exception:
        # optional: log
        pass

def list_keys(pattern: str = "last_signal:*"):
    return _redis.keys(pattern)

