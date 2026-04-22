import time
from functools import wraps
from threading import Lock

_store: dict[str, tuple[float, object]] = {}
_lock = Lock()


def ttl_cache(ttl_seconds: float):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = f"{fn.__name__}:{args}:{sorted(kwargs.items())}"
            now = time.time()
            with _lock:
                cached = _store.get(key)
                if cached and cached[0] > now:
                    return cached[1]
            value = fn(*args, **kwargs)
            with _lock:
                _store[key] = (now + ttl_seconds, value)
            return value
        return wrapper
    return decorator
