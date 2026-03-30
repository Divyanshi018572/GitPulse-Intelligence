import os
import diskcache

# Ensure the .local_cache directory exists in the root folder, ignored by git
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".local_cache")

# Initialize the persistent cache
# This replaces the in-memory dict, ensuring APIs aren't wasted on restarts
cache = diskcache.Cache(CACHE_DIR)

def cache_get(key: str):
    """Retrieve value from disk cache. Expiration is handled automatically by diskcache."""
    return cache.get(key)

def cache_set(key: str, value, ttl: int = 60):
    """Store value in disk cache for 'ttl' seconds"""
    cache.set(key, value, expire=ttl)
