#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generic content extractor (fallback)
"""

import re
from typing import Dict, List
from bs4 import BeautifulSoup
from base_extractor import BaseContentExtractor


class GenericExtractor(BaseContentExtractor):
    """Extracteur générique utilisé par défaut"""
    
    name = "Extracteur Générique"
    description = "Extracteur par défaut pour tous les sites"
    supported_domains = []  # Supporte tous les domaines
    
    def can_handle(self, url: str, soup: BeautifulSoup = None) -> bool:
        """Peut toujours traiter une URL (fallback)"""
        return True
    
    def extract(self, url: str, soup: BeautifulSoup) -> Dict:
        """
        Extraire les informations de manière générique
        
        Args:
            url: URL de la page
            soup: BeautifulSoup object
            
        Returns:
            Dictionnaire avec les informations extraites
        """
        # Déterminer le type de contenu
        content_type = self._determine_type(soup, url)
        
        if content_type == 'painting':
            return self._extract_painting_info(soup, url)
        elif content_type == 'artist':
            return self._extract_artist_info(soup, url)
        else:
            return self._extract_generic_info(soup, url)
    
    def _determine_type(self, soup: BeautifulSoup, url: str) -> str:
        """Déterminer le type de contenu (peinture ou artiste)"""
        text = soup.get_text().lower()
        
        # Mots-clés pour une peinture
        painting_keywords = ['peinture', 'tableau', 'œuvre', 'painting', 'artwork', 
                           'created', 'oil on canvas', 'huile sur toile']
        
        # Mots-clés pour un artiste
        artist_keywords = ['peintre', 'artiste', 'né', 'born', 'mort', 'died', 
                          'painter', 'artist', 'biography', 'biographie']
        
        painting_score = sum(1 for kw in painting_keywords if kw in text)
        artist_score = sum(1 for kw in artist_keywords if kw in text)
        
        if painting_score > artist_score:
            return 'painting'
        elif artist_score > painting_score:
            return 'artist'
        else:
            return 'unknown'
    
    def _extract_painting_info(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extraire les informations d'une peinture"""
        info = {
            'type': 'painting',
            'url': url,
            'extractor': self.name,
            'title': '',
            'creator': '',
            'date': '',
            'collection': '',
            'keywords': [],
            'image_url': '',
            'description': ''
        }
        
        # Titre
        title_tag = soup.find('h1')
        if title_tag:
            info['title'] = title_tag.get_text().strip()
        
        # Image
        img_tag = soup.find('img', {'class': re.compile(r'(artwork|painting|main-image)', re.I)})
        if not img_tag:
            img_tag = soup.find('img')
        if img_tag and img_tag.get('src'):
            info['image_url'] = img_tag['src']
        
        # Créateur
        creator_patterns = [
            soup.find('a', {'class': re.compile(r'artist', re.I)}),
            soup.find(text=re.compile(r'(Artist|Artiste|Créateur)', re.I))
        ]
        for pattern in creator_patterns:
            if pattern:
                if hasattr(pattern, 'get_text'):
                    info['creator'] = pattern.get_text().strip()
                else:
                    next_elem = pattern.find_next()
                    if next_elem:
                        info['creator'] = next_elem.get_text().strip()
                break
        
        # Date
        date_match = re.search(r'\b(1[4-9]\d{2}|20[0-2]\d)\b', soup.get_text())
        if date_match:
            info['date'] = date_match.group(0)
        
        # Tags/Mots-clés
        meta_keywords = soup.find('meta', {'name': 'keywords'})
        if meta_keywords and meta_keywords.get('content'):
            info['keywords'] = [tag.strip() for tag in meta_keywords['content'].split(',')]
        
        # Description
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            info['description'] = meta_desc['content']
        
        return info
    
    def _extract_artist_info(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extraire les informations d'un artiste"""
        info = {
            'type': 'artist',
            'url': url,
            'extractor': self.name,
            'name': '',
            'birth_date': '',
            'death_date': '',
            'nationality': '',
            'movements': [],
            'description': ''
        }
        
        # Nom
        title_tag = soup.find('h1')
        if title_tag:
            info['name'] = title_tag.get_text().strip()
        
        # Dates de naissance et de mort
        text = soup.get_text()
        
        birth_pattern = re.search(r'né[e]?\s+(?:le\s+)?(\d{1,2}\s+\w+\s+)?(\d{4})', text, re.IGNORECASE)
        if birth_pattern:
            info['birth_date'] = birth_pattern.group(0)
        
        death_pattern = re.search(r'mort[e]?\s+(?:le\s+)?(\d{1,2}\s+\w+\s+)?(\d{4})', text, re.IGNORECASE)
        if death_pattern:
            info['death_date'] = death_pattern.group(0)
        
        # Description
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            info['description'] = meta_desc['content']
        else:
            # Prendre le premier paragraphe
            first_p = soup.find('p')
            if first_p:
                info['description'] = first_p.get_text().strip()[:500]
        
        return info
    
    def _extract_generic_info(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extraire les informations génériques"""
        return {
            'type': 'unknown',
            'url': url,
            'extractor': self.name,
            'title': soup.find('h1').get_text() if soup.find('h1') else '',
            'description': soup.find('meta', {'name': 'description'})['content'] 
                          if soup.find('meta', {'name': 'description'}) else ''
        }
