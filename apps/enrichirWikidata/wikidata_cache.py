#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wikidata Cache System - Cache permanent pour les requêtes Wikidata
"""

import json
import os
import hashlib
from typing import Dict, Optional, Any
from datetime import datetime


class WikidataCache:
    """Système de cache permanent pour les requêtes Wikidata"""
    
    def __init__(self, cache_dir: str = 'data/wikidata_cache'):
        """
        Initialiser le cache
        
        Args:
            cache_dir: Répertoire pour stocker le cache
        """
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, 'wikidata_cache.json')
        self.cache: Dict[str, Any] = {}
        
        # Créer le répertoire si nécessaire
        os.makedirs(cache_dir, exist_ok=True)
        
        # Charger le cache existant
        self._load_cache()
    
    def _load_cache(self):
        """Charger le cache depuis le fichier"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                print(f"Cache Wikidata chargé: {len(self.cache)} entrées")
            except Exception as e:
                print(f"Erreur lors du chargement du cache: {e}")
                self.cache = {}
        else:
            self.cache = {}
    
    def _save_cache(self):
        """Sauvegarder le cache dans le fichier"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde du cache: {e}")
    
    def _generate_key(self, query_type: str, query_params: Dict) -> str:
        """
        Générer une clé unique pour une requête
        
        Args:
            query_type: Type de requête (search, entity, etc.)
            query_params: Paramètres de la requête
            
        Returns:
            Clé de cache unique
        """
        # Créer une chaîne représentant la requête
        query_str = f"{query_type}:{json.dumps(query_params, sort_keys=True)}"
        
        # Générer un hash
        return hashlib.md5(query_str.encode()).hexdigest()
    
    def get(self, query_type: str, query_params: Dict) -> Optional[Any]:
        """
        Récupérer une entrée du cache
        
        Args:
            query_type: Type de requête
            query_params: Paramètres de la requête
            
        Returns:
            Données en cache ou None si non trouvé
        """
        key = self._generate_key(query_type, query_params)
        
        if key in self.cache:
            entry = self.cache[key]
            # Mettre à jour le dernier accès
            entry['last_accessed'] = datetime.now().isoformat()
            self._save_cache()
            return entry['data']
        
        return None
    
    def set(self, query_type: str, query_params: Dict, data: Any):
        """
        Ajouter une entrée au cache
        
        Args:
            query_type: Type de requête
            query_params: Paramètres de la requête
            data: Données à mettre en cache
        """
        key = self._generate_key(query_type, query_params)
        
        self.cache[key] = {
            'query_type': query_type,
            'query_params': query_params,
            'data': data,
            'created_at': datetime.now().isoformat(),
            'last_accessed': datetime.now().isoformat()
        }
        
        self._save_cache()
    
    def clear(self):
        """Vider le cache"""
        self.cache = {}
        self._save_cache()
        print("Cache Wikidata vidé")
    
    def get_stats(self) -> Dict:
        """
        Obtenir des statistiques sur le cache
        
        Returns:
            Dictionnaire avec les statistiques
        """
        return {
            'total_entries': len(self.cache),
            'cache_file': self.cache_file,
            'size_bytes': os.path.getsize(self.cache_file) if os.path.exists(self.cache_file) else 0
        }
    
    def search_in_cache(self, search_term: str) -> list:
        """
        Rechercher dans le cache les entrées contenant un terme
        
        Args:
            search_term: Terme à rechercher
            
        Returns:
            Liste des entrées correspondantes
        """
        results = []
        search_lower = search_term.lower()
        
        for key, entry in self.cache.items():
            params = entry.get('query_params', {})
            data = entry.get('data', {})
            
            # Convertir en chaîne pour chercher
            params_str = json.dumps(params).lower()
            data_str = json.dumps(data).lower()
            
            if search_lower in params_str or search_lower in data_str:
                results.append({
                    'key': key,
                    'query_type': entry.get('query_type'),
                    'query_params': params,
                    'created_at': entry.get('created_at')
                })
        
        return results
