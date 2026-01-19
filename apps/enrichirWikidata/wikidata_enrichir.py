#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wikidata Enrichir with caching and concept mapping
"""

import requests
from typing import Dict, List, Optional
from wikidata_cache import WikidataCache


class WikidataEnrichir:
    """Classe pour gérer l'interaction avec Wikidata avec cache"""
    
    def __init__(self, username: str, password: str, use_cache: bool = True):
        """
        Initialiser l'enrichisseur Wikidata
        
        Args:
            username: Nom d'utilisateur Wikidata
            password: Mot de passe
            use_cache: Utiliser le cache (True par défaut)
        """
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.sparql_endpoint = "https://query.wikidata.org/sparql"
        self.api_endpoint = "https://www.wikidata.org/w/api.php"
        self.logged_in = False
        
        # Initialiser le cache
        self.use_cache = use_cache
        self.cache = WikidataCache() if use_cache else None
    
    def login(self) -> bool:
        """Connexion à Wikidata"""
        # Note: Pour une vraie application, utiliser OAuth
        self.logged_in = True
        return True
    
    def search_entity(self, name: str, entity_type: str = "item", language: str = "fr") -> List[Dict]:
        """
        Rechercher des entités Wikidata correspondantes
        
        Args:
            name: Nom à rechercher
            entity_type: Type d'entité (item, property)
            language: Langue de recherche
        
        Returns:
            Liste de dictionnaires contenant les résultats
        """
        # Vérifier le cache
        cache_params = {
            'action': 'search',
            'name': name,
            'type': entity_type,
            'language': language
        }
        
        if self.cache:
            cached_result = self.cache.get('search_entity', cache_params)
            if cached_result is not None:
                print(f"Cache hit pour recherche: {name}")
                return cached_result
        
        # Faire la requête API
        params = {
            'action': 'wbsearchentities',
            'format': 'json',
            'language': language,
            'search': name,
            'type': entity_type,
            'limit': 10
        }
        
        try:
            response = self.session.get(self.api_endpoint, params=params)
            data = response.json()
            
            results = []
            for item in data.get('search', []):
                entity_id = item['id']
                # Récupérer plus de détails sur l'entité
                details = self.get_entity_details(entity_id)
                results.append(details)
            
            # Mettre en cache
            if self.cache:
                self.cache.set('search_entity', cache_params, results)
            
            return results
        except Exception as e:
            print(f"Erreur lors de la recherche: {e}")
            return []
    
    def get_entity_details(self, entity_id: str) -> Dict:
        """
        Récupérer les détails d'une entité Wikidata
        
        Args:
            entity_id: ID de l'entité (ex: Q123)
        
        Returns:
            Dictionnaire avec les détails de l'entité
        """
        # Vérifier le cache
        cache_params = {'entity_id': entity_id}
        
        if self.cache:
            cached_result = self.cache.get('entity_details', cache_params)
            if cached_result is not None:
                print(f"Cache hit pour entité: {entity_id}")
                return cached_result
        
        # Faire la requête API
        params = {
            'action': 'wbgetentities',
            'format': 'json',
            'ids': entity_id,
            'languages': 'fr|en'
        }
        
        try:
            response = self.session.get(self.api_endpoint, params=params)
            data = response.json()
            
            if 'entities' in data and entity_id in data['entities']:
                entity = data['entities'][entity_id]
                
                # Extraire les informations clés
                labels = entity.get('labels', {})
                descriptions = entity.get('descriptions', {})
                claims = entity.get('claims', {})
                
                result = {
                    'id': entity_id,
                    'label': labels.get('fr', labels.get('en', {})).get('value', ''),
                    'description': descriptions.get('fr', descriptions.get('en', {})).get('value', ''),
                    'url': f"https://www.wikidata.org/wiki/{entity_id}",
                    'properties': {}
                }
                
                # Extraire quelques propriétés importantes
                important_props = {
                    'P31': 'instance de',
                    'P106': 'occupation',
                    'P135': 'mouvement',
                    'P170': 'créateur',
                    'P571': 'date de création',
                    'P569': 'date de naissance',
                    'P570': 'date de mort',
                    'P18': 'image',
                    'P276': 'lieu',
                    'P195': 'collection',
                    'P180': 'représente',
                    'P186': 'matériau',
                    'P2048': 'hauteur',
                    'P2049': 'largeur'
                }
                
                for prop_id, prop_label in important_props.items():
                    if prop_id in claims:
                        values = []
                        for claim in claims[prop_id]:
                            if 'mainsnak' in claim and 'datavalue' in claim['mainsnak']:
                                value = claim['mainsnak']['datavalue']['value']
                                if isinstance(value, dict):
                                    if 'id' in value:  # Item
                                        values.append(value['id'])
                                    elif 'time' in value:  # Time
                                        values.append(value['time'])
                                    elif 'amount' in value:  # Quantity
                                        values.append(value['amount'])
                                else:
                                    values.append(str(value))
                        
                        if values:
                            result['properties'][prop_label] = values
                
                # Mettre en cache
                if self.cache:
                    self.cache.set('entity_details', cache_params, result)
                
                return result
        except Exception as e:
            print(f"Erreur lors de la récupération des détails: {e}")
        
        return {}
    
    def search_concept(self, concept: str, language: str = "fr") -> Optional[Dict]:
        """
        Rechercher un concept/mot-clé dans Wikidata
        
        Args:
            concept: Concept à rechercher
            language: Langue de recherche
        
        Returns:
            Première entité correspondante ou None
        """
        results = self.search_entity(concept, language=language)
        
        if results and len(results) > 0:
            return results[0]  # Retourner la première correspondance
        
        return None
    
    def map_concepts_to_wikidata(self, concepts: List[str], language: str = "fr") -> Dict[str, Optional[Dict]]:
        """
        Mapper une liste de concepts vers des entités Wikidata
        
        Args:
            concepts: Liste de concepts à mapper
            language: Langue de recherche
        
        Returns:
            Dictionnaire {concept: entité_wikidata}
        """
        mapping = {}
        
        for concept in concepts:
            print(f"Recherche du concept: {concept}")
            entity = self.search_concept(concept, language)
            mapping[concept] = entity
        
        return mapping
    
    def search_person(self, name: str, birth_year: Optional[str] = None, 
                     death_year: Optional[str] = None) -> List[Dict]:
        """
        Rechercher une personne dans Wikidata
        
        Args:
            name: Nom de la personne
            birth_year: Année de naissance (optionnel)
            death_year: Année de mort (optionnel)
        
        Returns:
            Liste des personnes correspondantes
        """
        # Rechercher l'entité
        results = self.search_entity(name)
        
        # Filtrer les résultats pour ne garder que les personnes
        persons = []
        for result in results:
            # Vérifier si c'est une personne (instance de humain Q5)
            instance_of = result.get('properties', {}).get('instance de', [])
            if 'Q5' in instance_of or 'human' in str(instance_of).lower():
                # Vérifier les dates si fournies
                if birth_year or death_year:
                    birth = result.get('properties', {}).get('date de naissance', [''])[0]
                    death = result.get('properties', {}).get('date de mort', [''])[0]
                    
                    match = True
                    if birth_year and birth_year not in str(birth):
                        match = False
                    if death_year and death_year not in str(death):
                        match = False
                    
                    if match:
                        persons.append(result)
                else:
                    persons.append(result)
        
        return persons
    
    def create_entity(self, data: Dict) -> Optional[str]:
        """
        Créer une nouvelle entité Wikidata
        
        Args:
            data: Données de l'entité à créer
        
        Returns:
            ID de l'entité créée ou None
        """
        if not self.logged_in:
            if not self.login():
                return None
        
        # Note: Implémentation simplifiée
        # Dans une vraie application, utiliser l'API Wikidata pour créer l'entité
        print(f"Création d'entité: {data}")
        return "Q_NEW_ID"
    
    def add_claims(self, entity_id: str, claims: List[Dict]) -> bool:
        """
        Ajouter des déclarations à une entité
        
        Args:
            entity_id: ID de l'entité
            claims: Liste de déclarations à ajouter
        
        Returns:
            True si succès, False sinon
        """
        if not self.logged_in:
            if not self.login():
                return False
        
        # Note: Implémentation simplifiée
        print(f"Ajout de déclarations à {entity_id}: {claims}")
        return True
    
    def get_cache_stats(self) -> Dict:
        """
        Obtenir les statistiques du cache
        
        Returns:
            Dictionnaire avec les statistiques
        """
        if self.cache:
            return self.cache.get_stats()
        return {'cache_enabled': False}
