#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base class for content extractors
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
from bs4 import BeautifulSoup
import requests
import urllib3

# Désactiver les avertissements SSL (pour certificats auto-signés)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class BaseContentExtractor(ABC):
    """Classe de base abstraite pour tous les extracteurs de contenu"""
    
    # Nom de l'extracteur (à définir dans chaque sous-classe)
    name: str = "Base Extractor"
    
    # Description de l'extracteur
    description: str = "Base abstract extractor"
    
    # Domaines supportés (liste de patterns ou vide pour tous)
    supported_domains: list = []
    
    def __init__(self):
        """Initialiser l'extracteur"""
        pass
    
    @abstractmethod
    def can_handle(self, url: str, soup: BeautifulSoup = None) -> bool:
        """
        Déterminer si cet extracteur peut traiter cette URL
        
        Args:
            url: URL à vérifier
            soup: BeautifulSoup object (optionnel, peut être None)
            
        Returns:
            True si l'extracteur peut traiter cette URL
        """
        pass
    
    @abstractmethod
    def extract(self, url: str, soup: BeautifulSoup) -> Dict:
        """
        Extraire les informations de la page
        
        Args:
            url: URL de la page
            soup: BeautifulSoup object de la page
            
        Returns:
            Dictionnaire avec les informations extraites
        """
        pass
    
    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        Récupérer et parser une page web
        
        Args:
            url: URL à récupérer
            
        Returns:
            BeautifulSoup object ou None en cas d'erreur
        """
        try:
            # Désactiver la vérification SSL si nécessaire (pour les certificats auto-signés)
            response = requests.get(url, timeout=10, verify=False)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"Erreur lors de la récupération de {url}: {e}")
            return None
    
    def extract_from_url(self, url: str) -> Dict:
        """
        Méthode principale pour extraire depuis une URL
        
        Args:
            url: URL à traiter
            
        Returns:
            Dictionnaire avec les informations extraites ou erreur
        """
        soup = self.fetch_page(url)
        if soup is None:
            return {
                'error': 'Impossible de récupérer la page',
                'url': url
            }
        
        try:
            return self.extract(url, soup)
        except Exception as e:
            return {
                'error': f'Erreur lors de l\'extraction: {str(e)}',
                'url': url
            }
    
    def get_info(self) -> Dict:
        """
        Obtenir les informations sur cet extracteur
        
        Returns:
            Dictionnaire avec name, description, supported_domains
        """
        return {
            'name': self.name,
            'description': self.description,
            'supported_domains': self.supported_domains
        }
