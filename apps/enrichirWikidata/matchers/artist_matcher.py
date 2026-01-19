#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wikidata matcher for artists
"""

from typing import Dict, List
from base_matcher import BaseWikidataMatcher
import re


class ArtistMatcher(BaseWikidataMatcher):
    """Matcher pour trouver des artistes dans Wikidata"""
    
    name = "Artist Matcher"
    description = "Trouve des correspondances pour les artistes/peintres via SPARQL"
    supported_types = ["artist", "painter"]
    
    def can_handle(self, entity_type: str, extracted_data: Dict) -> bool:
        """Vérifie si ce matcher peut traiter cette entité"""
        return entity_type.lower() in self.supported_types
    
    def find_matches(self, extracted_data: Dict) -> List[Dict]:
        """
        Trouver des artistes correspondants dans Wikidata
        
        Args:
            extracted_data: Données extraites contenant name, birth_date, death_date, etc.
            
        Returns:
            Liste de correspondances avec scores de confiance
        """
        matches = []
        
        name = extracted_data.get('name', '') or extracted_data.get('creator', '')
        birth_date = extracted_data.get('birth_date', '') or extracted_data.get('creator_birth', '')
        death_date = extracted_data.get('death_date', '') or extracted_data.get('creator_death', '')
        
        if not name:
            return matches
        
        # Extraire les années
        birth_year = self._extract_year(birth_date)
        death_year = self._extract_year(death_date)
        
        # Stratégie 1: Recherche par nom et dates (la plus précise)
        if birth_year or death_year:
            dated_matches = self._search_by_name_and_dates(name, birth_year, death_year)
            matches.extend(dated_matches)
        
        # Stratégie 2: Recherche par nom seulement
        if len(matches) < 3:
            name_matches = self._search_by_name(name)
            # Éviter les doublons
            existing_ids = {m['id'] for m in matches}
            for match in name_matches:
                if match['id'] not in existing_ids:
                    matches.append(match)
        
        # Trier par score de confiance décroissant
        matches.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        # Limiter à 10 résultats
        return matches[:10]
    
    def _search_by_name_and_dates(self, name: str, birth_year: str = '', death_year: str = '') -> List[Dict]:
        """Recherche par nom et dates"""
        # Nettoyer le nom
        name_clean = name.strip().replace('"', '\\"')
        
        # Construire les filtres de dates
        date_filters = []
        if birth_year:
            date_filters.append(f"YEAR(?birth) = {birth_year}")
        if death_year:
            date_filters.append(f"YEAR(?death) = {death_year}")
        
        date_filter_str = ""
        if date_filters:
            date_filter_str = "FILTER(" + " || ".join(date_filters) + ")"
        
        query = f"""
        SELECT DISTINCT ?item ?itemLabel ?birth ?death ?image ?occupationLabel WHERE {{
          ?item wdt:P31 wd:Q5 .  # humain
          ?item wdt:P106 ?occupation .
          ?occupation wdt:P279* wd:Q483501 .  # artiste ou sous-classe
          ?item rdfs:label ?label .
          FILTER(CONTAINS(LCASE(?label), LCASE("{name_clean}")))
          FILTER(LANG(?label) = "fr" || LANG(?label) = "en")
          OPTIONAL {{ ?item wdt:P569 ?birth . }}
          OPTIONAL {{ ?item wdt:P570 ?death . }}
          OPTIONAL {{ ?item wdt:P18 ?image . }}
          {date_filter_str}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en" . }}
        }}
        LIMIT 10
        """
        
        results = self.execute_sparql_query(query)
        
        matches = []
        for result in results:
            item_id = self._extract_qid(result.get('item', ''))
            if not item_id:
                continue
            
            result_birth = result.get('birth', '')
            result_death = result.get('death', '')
            
            # Calculer le score de confiance
            confidence = 0.7  # Base
            
            # Augmenter si les dates correspondent
            dates_match = 0
            if birth_year and result_birth and birth_year in result_birth:
                dates_match += 1
            if death_year and result_death and death_year in result_death:
                dates_match += 1
            
            if dates_match == 2:
                confidence = 0.95
            elif dates_match == 1:
                confidence = 0.85
            
            # Augmenter si le nom correspond bien
            if self._names_match(name, result.get('itemLabel', '')):
                confidence = min(confidence + 0.05, 1.0)
            
            match = {
                'id': item_id,
                'label': result.get('itemLabel', ''),
                'birth': self._format_date(result_birth),
                'death': self._format_date(result_death),
                'occupation': result.get('occupationLabel', ''),
                'image': result.get('image', ''),
                'url': f"https://www.wikidata.org/wiki/{item_id}",
                'match_type': 'name_dates',
                'confidence': confidence
            }
            
            matches.append(match)
        
        return matches
    
    def _search_by_name(self, name: str) -> List[Dict]:
        """Recherche par nom seulement"""
        name_clean = name.strip().replace('"', '\\"')
        
        query = f"""
        SELECT DISTINCT ?item ?itemLabel ?birth ?death ?image ?occupationLabel WHERE {{
          ?item wdt:P31 wd:Q5 .  # humain
          ?item wdt:P106 ?occupation .
          ?occupation wdt:P279* wd:Q483501 .  # artiste ou sous-classe
          ?item rdfs:label "{name_clean}"@fr .
          OPTIONAL {{ ?item wdt:P569 ?birth . }}
          OPTIONAL {{ ?item wdt:P570 ?death . }}
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
                'birth': self._format_date(result.get('birth', '')),
                'death': self._format_date(result.get('death', '')),
                'occupation': result.get('occupationLabel', ''),
                'image': result.get('image', ''),
                'url': f"https://www.wikidata.org/wiki/{item_id}",
                'match_type': 'name_only',
                'confidence': 0.6  # Confiance plus faible sans dates
            }
            
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
    
    def _format_date(self, date_str: str) -> str:
        """Formater une date pour l'affichage"""
        if not date_str:
            return ''
        
        # Extraire juste l'année si c'est une date complète
        year = self._extract_year(date_str)
        return year if year else date_str
    
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
        
        # Vérifier les noms de famille (premier mot)
        parts1 = name1_lower.split()
        parts2 = name2_lower.split()
        
        if parts1 and parts2:
            # Format "NOM Prénom" ou "Prénom NOM"
            # Vérifier si au moins un mot correspond
            for p1 in parts1:
                for p2 in parts2:
                    if len(p1) > 2 and len(p2) > 2 and p1 == p2:
                        return True
        
        return False
