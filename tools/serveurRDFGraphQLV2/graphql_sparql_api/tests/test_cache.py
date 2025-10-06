import pytest
from core.cache import CacheManager

def test_cache_set_and_get(temp_dir):
    cache = CacheManager(temp_dir)
    query = "SELECT * WHERE { ?s ?p ?o }"
    result = [{'s': 'test', 'p': 'test', 'o': 'test'}]
    
    cache.set(query, result)
    cached = cache.get(query)
    
    assert cached == result

def test_cache_not_found(temp_dir):
    cache = CacheManager(temp_dir)
    result = cache.get("non-existent-query")
    
    assert result is None
