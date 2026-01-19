#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wikidata matcher for paintings
"""

from typing import Dict, List
from base_matcher import BaseWikidataMatcher
import re


class PaintingMatcher(BaseWikidataMatcher):
    """Matcher pour trouver des peintures dans Wikidata"""
    
    name = "Painting Matcher"
    description = "Trouve des correspondances pour les peintures via SPARQL"
    supported_types = ["painting"]
    
    def can_handle(self, entity_type: str, extracted_data: Dict) -> bool:
        """Vérifie si ce matcher peut traiter cette entité"""
        return entity_type.lower() in self.supported_types
    
    def find_matches(self, extracted_data: Dict) -> List[Dict]:
        """
        Trouver des peintures correspondantes dans Wikidata
        
        Args:
            extracted_data: Données extraites contenant title, creator, date, etc.
            
        Returns:
            Liste de correspondances avec scores de confiance
        """
        matches = []
        
        title = extracted_data.get('title', '').strip()
        creator = extracted_data.get('creator', '').strip()
        date = extracted_data.get('date', '').strip()
        
        if not title:
            return matches
        
        # Stratégie 1: Recherche par titre exact
        if title:
            exact_matches = self._search_by_title_exact(title, creator, date)
            matches.extend(exact_matches)
        
        # Stratégie 2: Recherche par titre partiel si peu de résultats
        if len(matches) < 3 and title:
            partial_matches = self._search_by_title_partial(title, creator, date)
            # Éviter les doublons
            existing_ids = {m['id'] for m in matches}
            for match in partial_matches:
                if match['id'] not in existing_ids:
                    matches.append(match)
        
        # Stratégie 3: Recherche par créateur et date si disponibles
        if len(matches) < 5 and creator and date:
            creator_matches = self._search_by_creator_and_date(creator, date, title)
            existing_ids = {m['id'] for m in matches}
            for match in creator_matches:
                if match['id'] not in existing_ids:
                    matches.append(match)
        
        # Trier par score de confiance décroissant
        matches.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        # Limiter à 10 résultats
        return matches[:10]
    
    def _search_by_title_exact(self, title: str, creator: str = '', date: str = '') -> List[Dict]:
        """Recherche par titre exact"""
        # Échapper les guillemets pour SPARQL
        title_escaped = title.replace('"', '\\"')
        
        # Extraire l'année si possible
        year = self._extract_year(date)
        
        query = f"""
        SELECT DISTINCT ?item ?itemLabel ?creatorLabel ?date ?image WHERE {{
          ?item wdt:P31/wdt:P279* wd:Q3305213 .  # instance de peinture
          ?item rdfs:label "{title_escaped}"@fr .
          OPTIONAL {{ ?item wdt:P170 ?creator . }}
          OPTIONAL {{ ?item wdt:P571 ?date . }}
          OPTIONAL {{ ?item wdt:P18 ?image . }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en" . }}
        }}
        LIMIT 5
        """
        
        results = self.execute_sparql_query(query)
        
        matches = []
        for result in results:
            item_id = self._extract_qid(result.get('item', ''))
            if not item_id:
                continue
            
            match = {
                'id': item_id,
                'label': result.get('itemLabel', ''),
                'creator': result.get('creatorLabel', ''),
                'date': result.get('date', ''),
                'image': result.get('image', ''),
                'url': f"https://www.wikidata.org/wiki/{item_id}",
                'match_type': 'exact_title',
                'confidence': 0.95  # Haute confiance pour correspondance exacte
            }
            
            # Ajuster le score si créateur correspond
            if creator and result.get('creatorLabel', ''):
                if self._names_match(creator, result.get('creatorLabel', '')):
                    match['confidence'] = 0.98
            
            # Ajuster le score si date correspond
            if year and result.get('date', ''):
                if year in result.get('date', ''):
                    match['confidence'] = min(match['confidence'] + 0.02, 1.0)
            
            matches.append(match)
        
        return matches
    
    def _search_by_title_partial(self, title: str, creator: str = '', date: str = '') -> List[Dict]:
        """Recherche par titre partiel (contient)"""
        # Nettoyer et préparer le titre pour la recherche
        title_clean = self._clean_title_for_search(title)
        
        query = f"""
        SELECT DISTINCT ?item ?itemLabel ?creatorLabel ?date ?image WHERE {{
          ?item wdt:P31/wdt:P279* wd:Q3305213 .  # instance de peinture
          ?item rdfs:label ?label .
          FILTER(CONTAINS(LCASE(?label), LCASE("{title_clean}")))
          FILTER(LANG(?label) = "fr" || LANG(?label) = "en")
          OPTIONAL {{ ?item wdt:P170 ?creator . }}
          OPTIONAL {{ ?item wdt:P571 ?date . }}
          OPTIONAL {{ ?item wdt:P18 ?image . }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en" . }}
        }}
        LIMIT 5
        """
        
        results = self.execute_sparql_query(query)
        
        matches = []
        for result in results:
            item_id = self._extract_qid(result.get('item', ''))
            if not item_id:
                continue
            
            match = {
                'id': item_id,
                'label': result.get('itemLabel', ''),
                'creator': result.get('creatorLabel', ''),
                'date': result.get('date', ''),
                'image': result.get('image', ''),
                'url': f"https://www.wikidata.org/wiki/{item_id}",
                'match_type': 'partial_title',
                'confidence': 0.7  # Confiance moyenne pour correspondance partielle
            }
            
            # Ajuster le score selon la qualité de la correspondance
            if creator and result.get('creatorLabel', ''):
                if self._names_match(creator, result.get('creatorLabel', '')):
                    match['confidence'] = 0.85
            
            matches.append(match)
        
        return matches
    
    def _search_by_creator_and_date(self, creator: str, date: str, title: str = '') -> List[Dict]:
        """Recherche par créateur et date"""
        year = self._extract_year(date)
        if not year:
            return []
        
        # Nettoyer le nom du créateur
        creator_parts = creator.split()
        creator_lastname = creator_parts[0] if creator_parts else creator
        
        query = f"""
        SELECT DISTINCT ?item ?itemLabel ?creatorLabel ?date ?image WHERE {{
          ?item wdt:P31/wdt:P279* wd:Q3305213 .  # instance de peinture
          ?item wdt:P170 ?creator .
          ?creator rdfs:label ?creatorLabel .
          FILTER(CONTAINS(LCASE(?creatorLabel), LCASE("{creator_lastname}")))
          FILTER(LANG(?creatorLabel) = "fr" || LANG(?creatorLabel) = "en")
          OPTIONAL {{ ?item wdt:P571 ?date . FILTER(YEAR(?date) = {year}) }}
          OPTIONAL {{ ?item wdt:P18 ?image . }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en" . }}
        }}
        LIMIT 5
        """
        
        results = self.execute_sparql_query(query)
        
        matches = []
        for result in results:
            item_id = self._extract_qid(result.get('item', ''))
            if not item_id:
                continue
            
            match = {
                'id': item_id,
                'label': result.get('itemLabel', ''),
                'creator': result.get('creatorLabel', ''),
                'date': result.get('date', ''),
                'image': result.get('image', ''),
                'url': f"https://www.wikidata.org/wiki/{item_id}",
                'match_type': 'creator_date',
                'confidence': 0.6  # Confiance plus faible car basé sur créateur/date
            }
            
            # Augmenter le score si le titre correspond aussi
            if title and result.get('itemLabel', ''):
                if self._titles_similar(title, result.get('itemLabel', '')):
                    match['confidence'] = 0.8
            
            matches.append(match)
        
        return matches
    
    def _extract_qid(self, uri: str) -> str:
        """Extraire le QID d'une URI Wikidata"""
        match = re.search(r'Q\d+', uri)
        return match.group(0) if match else ''
    
    def _extract_year(self, date_str: str) -> str:
        """Extraire l'année d'une chaîne de date"""
        if not date_str:
            return ''
        
        # Chercher un nombre de 4 chiffres qui ressemble à une année
        match = re.search(r'\b(1[4-9]\d{2}|20[0-2]\d)\b', str(date_str))
        return match.group(0) if match else ''
    
    def _clean_title_for_search(self, title: str) -> str:
        """Nettoyer le titre pour la recherche"""
        # Retirer les caractères spéciaux qui pourraient poser problème
        title = title.replace('"', '').replace("'", "")
        # Garder seulement les mots principaux (enlever articles courts)
        words = title.split()
        if len(words) > 3:
            # Garder les mots de plus de 3 caractères
            words = [w for w in words if len(w) > 3]
        return ' '.join(words) if words else title
    
    def _names_match(self, name1: str, name2: str) -> bool:
        """Vérifier si deux noms correspondent"""
        name1_lower = name1.lower().strip()
        name2_lower = name2.lower().strip()
        
        # Correspondance exacte
        if name1_lower == name2_lower:
            return True
        
        # Vérifier si l'un contient l'autre
        if name1_lower in name2_lower or name2_lower in name1_lower:
            return True
        
        # Vérifier les noms de famille
        parts1 = name1_lower.split()
        parts2 = name2_lower.split()
        
        # Si le premier mot (nom de famille) correspond
        if parts1 and parts2 and parts1[0] == parts2[0]:
            return True
        
        return False
    
    def _titles_similar(self, title1: str, title2: str) -> bool:
        """Vérifier si deux titres sont similaires"""
        title1_lower = title1.lower().strip()
        title2_lower = title2.lower().strip()
        
        # Correspondance exacte
        if title1_lower == title2_lower:
            return True
        
        # Extraire les mots significatifs (> 3 lettres)
        words1 = set(w for w in title1_lower.split() if len(w) > 3)
        words2 = set(w for w in title2_lower.split() if len(w) > 3)
        
        if not words1 or not words2:
            return False
        
        # Si au moins 50% des mots correspondent
        common = words1.intersection(words2)
        similarity = len(common) / max(len(words1), len(words2))
        
        return similarity >= 0.5
