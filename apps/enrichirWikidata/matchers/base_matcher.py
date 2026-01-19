#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base class for Wikidata matchers
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import requests


class BaseWikidataMatcher(ABC):
    """Classe de base abstraite pour tous les matchers Wikidata"""
    
    # Nom du matcher (à définir dans chaque sous-classe)
    name: str = "Base Matcher"
    
    # Description du matcher
    description: str = "Base abstract matcher"
    
    # Types d'entités supportés (painting, artist, etc.)
    supported_types: list = []
    
    # Endpoint SPARQL Wikidata
    SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
    
    def __init__(self):
        """Initialiser le matcher"""
        pass
    
    @abstractmethod
    def can_handle(self, entity_type: str, extracted_data: Dict) -> bool:
        """
        Déterminer si ce matcher peut traiter ce type d'entité
        
        Args:
            entity_type: Type d'entité (painting, artist, etc.)
            extracted_data: Données extraites de l'URL
            
        Returns:
            True si le matcher peut traiter cette entité
        """
        pass
    
    @abstractmethod
    def find_matches(self, extracted_data: Dict) -> List[Dict]:
        """
        Trouver des entités Wikidata correspondantes
        
        Args:
            extracted_data: Données extraites de l'URL
            
        Returns:
            Liste de correspondances possibles avec scores de confiance
        """
        pass
    
    def execute_sparql_query(self, query: str) -> List[Dict]:
        """
        Exécuter une requête SPARQL sur Wikidata
        
        Args:
            query: Requête SPARQL
            
        Returns:
            Liste de résultats
        """
        try:
            response = requests.get(
                self.SPARQL_ENDPOINT,
                params={'query': query, 'format': 'json'},
                headers={'User-Agent': 'WikidataEnricher/1.0'},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for binding in data.get('results', {}).get('bindings', []):
                result = {}
                for key, value in binding.items():
                    result[key] = value.get('value', '')
                results.append(result)
            
            return results
        
        except Exception as e:
            print(f"Erreur SPARQL: {e}")
            return []
    
    def get_entity_details(self, qid: str) -> Dict:
        """
        Récupérer les détails d'une entité via SPARQL
        
        Args:
            qid: ID Wikidata (ex: Q12345)
            
        Returns:
            Dictionnaire avec les détails de l'entité
        """
        query = f"""
        SELECT ?label ?description ?image WHERE {{
          wd:{qid} rdfs:label ?label .
          OPTIONAL {{ wd:{qid} schema:description ?description . }}
          OPTIONAL {{ wd:{qid} wdt:P18 ?image . }}
          FILTER(LANG(?label) = "fr" || LANG(?label) = "en")
          FILTER(LANG(?description) = "fr" || LANG(?description) = "en")
        }}
        LIMIT 1
        """
        
        results = self.execute_sparql_query(query)
        
        if results:
            result = results[0]
            return {
                'id': qid,
                'label': result.get('label', ''),
                'description': result.get('description', ''),
                'image': result.get('image', ''),
                'url': f"https://www.wikidata.org/wiki/{qid}"
            }
        
        return {}
    
    def calculate_confidence_score(self, extracted_data: Dict, wikidata_entity: Dict) -> float:
        """
        Calculer un score de confiance pour une correspondance
        
        Args:
            extracted_data: Données extraites
            wikidata_entity: Entité Wikidata candidate
            
        Returns:
            Score de confiance entre 0 et 1
        """
        # Implémentation par défaut simple
        # Les sous-classes peuvent override pour un calcul plus sophistiqué
        score = 0.5
        
        # Comparer les titres/noms
        extracted_title = extracted_data.get('title', '') or extracted_data.get('name', '')
        wikidata_label = wikidata_entity.get('label', '')
        
        if extracted_title and wikidata_label:
            extracted_lower = extracted_title.lower().strip()
            wikidata_lower = wikidata_label.lower().strip()
            
            if extracted_lower == wikidata_lower:
                score = 1.0
            elif extracted_lower in wikidata_lower or wikidata_lower in extracted_lower:
                score = 0.8
        
        return score
    
    def get_info(self) -> Dict:
        """
        Obtenir les informations sur ce matcher
        
        Returns:
            Dictionnaire avec name, description, supported_types
        """
        return {
            'name': self.name,
            'description': self.description,
            'supported_types': self.supported_types
        }
