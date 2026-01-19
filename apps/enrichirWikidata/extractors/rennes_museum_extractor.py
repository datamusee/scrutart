#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Content extractor for Musée des Beaux-Arts de Rennes
"""

import re
from typing import Dict, List
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from base_extractor import BaseContentExtractor


class RennesMuseumExtractor(BaseContentExtractor):
    """Extracteur pour les collections du Musée des Beaux-Arts de Rennes"""
    
    name = "Musée de Rennes"
    description = "Extracteur pour collections.mba.rennes.fr"
    supported_domains = ["collections.mba.rennes.fr"]
    
    def can_handle(self, url: str, soup: BeautifulSoup = None) -> bool:
        """Vérifie si l'URL correspond au musée de Rennes"""
        parsed = urlparse(url)
        return parsed.netloc in self.supported_domains
    
    def extract(self, url: str, soup: BeautifulSoup) -> Dict:
        """
        Extraire les informations d'une œuvre du musée de Rennes
        
        Args:
            url: URL de l'œuvre
            soup: BeautifulSoup object
            
        Returns:
            Dictionnaire avec les informations extraites
        """
        info = {
            'type': 'painting',
            'url': url,
            'extractor': self.name,
            'title': '',
            'creator': '',
            'creator_birth': '',
            'creator_death': '',
            'date': '',
            'material': '',
            'height': '',
            'width': '',
            'dimensions': {},
            'keywords': [],
            'depicted_persons': [],
            'domain': '',
            'object_type': '',
            'description': '',
            'image_url': ''
        }
        
        # Extraire le type d'objet et le domaine
        info['object_type'] = self._extract_object_type(soup)
        info['domain'] = self._extract_domain(soup)
        
        # Déterminer s'il s'agit d'une peinture
        if info['object_type'] and 'tableau' in info['object_type'].lower():
            info['type'] = 'painting'
        elif info['domain'] and 'peinture' in info['domain'].lower():
            info['type'] = 'painting'
        
        # Titre
        info['title'] = self._extract_title(soup)
        
        # Créateur et dates
        creator_info = self._extract_creator(soup)
        info.update(creator_info)
        
        # Date de création
        info['date'] = self._extract_creation_date(soup)
        
        # Matériau
        info['material'] = self._extract_material(soup)
        
        # Dimensions
        dimensions = self._extract_dimensions(soup)
        info.update(dimensions)
        
        # Mots-clés / Concepts
        info['keywords'] = self._extract_keywords(soup)
        
        # Personnes représentées
        info['depicted_persons'] = self._extract_depicted_persons(soup)
        
        # Image
        info['image_url'] = self._extract_image(soup)
        
        # Description
        info['description'] = self._extract_description(soup)
        
        return info
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extraire le titre de l'œuvre"""
        # Chercher dans les balises h1
        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()
        
        # Chercher dans les métadonnées
        title_meta = soup.find('meta', {'property': 'og:title'})
        if title_meta and title_meta.get('content'):
            return title_meta['content'].strip()
        
        return ''
    
    def _extract_object_type(self, soup: BeautifulSoup) -> str:
        """Extraire le type d'objet (ex: Tableau)"""
        # Chercher "Type d'objet" ou "Dénomination"
        patterns = [
            r"Type\s*d['\"]objet\s*[:\-]\s*(.+)",
            r'Dénomination\s*[:\-]\s*(.+)',
        ]
        
        text = soup.get_text()
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return ''
    
    def _extract_domain(self, soup: BeautifulSoup) -> str:
        """Extraire le domaine (ex: Peinture)"""
        pattern = r'Domaine\s*[:\-]\s*(.+?)(?:\n|$)'
        text = soup.get_text()
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ''
    
    def _extract_creator(self, soup: BeautifulSoup) -> Dict:
        """Extraire le créateur et ses dates"""
        result = {
            'creator': '',
            'creator_birth': '',
            'creator_death': ''
        }
        
        # Chercher le créateur avec pattern: NOM Prénom, né en XXXX et mort en YYYY
        pattern = r'([A-ZÉÈÊ]+\s+[A-Za-zéèêàâîôùûç]+(?:\s+[A-Za-zéèêàâîôùûç]+)?),?\s*né\s+en\s+(\d{4})\s+et\s+mort\s+en\s+(\d{4})'
        text = soup.get_text()
        match = re.search(pattern, text)
        
        if match:
            result['creator'] = match.group(1).strip()
            result['creator_birth'] = match.group(2)
            result['creator_death'] = match.group(3)
        else:
            # Essayer un pattern plus simple
            creator_pattern = r'(?:Auteur|Créateur|Artiste)\s*[:\-]\s*([A-ZÉÈÊ]+\s+[A-Za-zéèêàâîôùûç]+)'
            match = re.search(creator_pattern, text, re.IGNORECASE)
            if match:
                result['creator'] = match.group(1).strip()
        
        return result
    
    def _extract_creation_date(self, soup: BeautifulSoup) -> str:
        """Extraire la date de création"""
        patterns = [
            r'Date\s+de\s+création\s*[:\-]\s*(\d{4})',
            r'Création\s*[:\-]\s*(\d{4})',
            r'Année\s*[:\-]\s*(\d{4})',
        ]
        
        text = soup.get_text()
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return ''
    
    def _extract_material(self, soup: BeautifulSoup) -> str:
        """Extraire le matériau"""
        patterns = [
            r'Matière\s*[:\-]\s*(.+?)(?:\n|,)',
            r'Matériau\s*[:\-]\s*(.+?)(?:\n|,)',
            r'Technique\s*[:\-]\s*(.+?)(?:\n|,)',
        ]
        
        text = soup.get_text()
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return ''
    
    def _extract_dimensions(self, soup: BeautifulSoup) -> Dict:
        """Extraire les dimensions (hauteur, largeur)"""
        result = {
            'height': '',
            'width': '',
            'dimensions': {}
        }
        
        # Pattern pour hauteur et largeur en cm
        # Ex: "hauteur 550cm et sa largeur 780 cm"
        # ou "Dimensions : H. 550 cm ; L. 780 cm"
        
        text = soup.get_text()
        
        # Pattern 1: hauteur XXX cm
        height_match = re.search(r'hauteur\s+(\d+)\s*cm', text, re.IGNORECASE)
        if height_match:
            result['height'] = height_match.group(1) + ' cm'
            result['dimensions']['height'] = height_match.group(1)
        
        # Pattern 2: largeur XXX cm
        width_match = re.search(r'largeur\s+(\d+)\s*cm', text, re.IGNORECASE)
        if width_match:
            result['width'] = width_match.group(1) + ' cm'
            result['dimensions']['width'] = width_match.group(1)
        
        # Pattern 3: H. XXX cm ; L. YYY cm
        dim_pattern = r'H\.\s*(\d+)\s*cm\s*;\s*L\.\s*(\d+)\s*cm'
        dim_match = re.search(dim_pattern, text, re.IGNORECASE)
        if dim_match:
            result['height'] = dim_match.group(1) + ' cm'
            result['width'] = dim_match.group(2) + ' cm'
            result['dimensions']['height'] = dim_match.group(1)
            result['dimensions']['width'] = dim_match.group(2)
        
        return result
    
    def _extract_keywords(self, soup: BeautifulSoup) -> List[str]:
        """Extraire les concepts clés / mots-clés"""
        keywords = []
        
        # Chercher une section de mots-clés ou concepts
        # Pattern: "Concepts clés : mot1, mot2, mot3"
        pattern = r'(?:Concepts?\s+clés?|Mots?-clés?)\s*[:\-]\s*(.+?)(?:\n\n|\n[A-Z]|$)'
        text = soup.get_text()
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        
        if match:
            concepts_text = match.group(1)
            # Séparer par virgules et nettoyer
            keywords = [k.strip() for k in concepts_text.split(',')]
            keywords = [k for k in keywords if k and len(k) > 2]
        
        # Chercher aussi dans les métadonnées
        meta_keywords = soup.find('meta', {'name': 'keywords'})
        if meta_keywords and meta_keywords.get('content'):
            meta_kw = [k.strip() for k in meta_keywords['content'].split(',')]
            keywords.extend(meta_kw)
        
        # Supprimer les doublons
        keywords = list(set(keywords))
        
        return keywords
    
    def _extract_depicted_persons(self, soup: BeautifulSoup) -> List[str]:
        """Extraire les personnes représentées"""
        persons = []
        
        # Pattern: "Personne représentée : Nom"
        pattern = r'Personne\s+représentée\s*[:\-]\s*(.+?)(?:\n|$)'
        text = soup.get_text()
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            person_text = match.group(1).strip()
            # Peut contenir plusieurs noms séparés par des virgules
            persons = [p.strip() for p in person_text.split(',')]
        
        return persons
    
    def _extract_image(self, soup: BeautifulSoup) -> str:
        """Extraire l'URL de l'image principale"""
        # Chercher l'image Open Graph
        og_image = soup.find('meta', {'property': 'og:image'})
        if og_image and og_image.get('content'):
            return og_image['content']
        
        # Chercher une image avec classe spécifique
        img = soup.find('img', {'class': re.compile(r'(main|primary|artwork|object)', re.I)})
        if img and img.get('src'):
            return img['src']
        
        # Chercher la première image de grande taille
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if 'thumb' not in src.lower() and 'icon' not in src.lower():
                return src
        
        return ''
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extraire la description de l'œuvre"""
        # Chercher dans les métadonnées
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content']
        
        # Chercher dans une balise de description
        desc = soup.find('div', {'class': re.compile(r'description', re.I)})
        if desc:
            return desc.get_text().strip()
        
        return ''
