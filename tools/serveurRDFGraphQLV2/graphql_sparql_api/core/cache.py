# ============================================================================
# core/cache.py - Système de cache
# ============================================================================

"""
Système de cache pour les requêtes et le schéma
"""

import os
import json
import hashlib
from typing import Any, Optional


class CacheManager:
    """Gestionnaire de cache"""

    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def get_cache_key(self, query: str) -> str:
        """Génère une clé de cache à partir d'une requête"""
        return hashlib.sha256(query.encode()).hexdigest()

    def get(self, query: str, cache_type: str = 'sparql') -> Optional[Any]:
        """Récupère un résultat du cache"""
        cache_key = self.get_cache_key(query)
        cache_file = os.path.join(self.cache_dir, f"{cache_type}_{cache_key}.json")

        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def set(self, query: str, result: Any, cache_type: str = 'sparql'):
        """Sauvegarde un résultat dans le cache"""
        cache_key = self.get_cache_key(query)
        cache_file = os.path.join(self.cache_dir, f"{cache_type}_{cache_key}.json")

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

    def clear(self):
        """Vide le cache"""
        import shutil
        shutil.rmtree(self.cache_dir)
        os.makedirs(self.cache_dir)
