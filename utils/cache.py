# utils/cache.py
import redis
import json
from functools import wraps
from datetime import timedelta

class CacheManager:
    def __init__(self, redis_url: str):
        self.redis_client = redis.from_url(redis_url)
        
    def cache_result(self, key_prefix: str, ttl: int = 300):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = f"{key_prefix}:{str(args)}:{str(kwargs)}"
                
                # Try to get from cache
                cached = self.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Store in cache
                self.redis_client.setex(
                    cache_key,
                    ttl,
                    json.dumps(result)
                )
                
                return result
            return wrapper
        return decorator
