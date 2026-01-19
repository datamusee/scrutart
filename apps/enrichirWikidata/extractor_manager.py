#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extractor Manager - Gère le chargement dynamique des extracteurs
"""

import os
import importlib.util
import inspect
from typing import List, Dict, Optional, Type
from base_extractor import BaseContentExtractor
from bs4 import BeautifulSoup


class ExtractorManager:
    """Gestionnaire pour charger et sélectionner les extracteurs de contenu"""
    
    def __init__(self, extractors_dir: str = 'extractors'):
        """
        Initialiser le gestionnaire d'extracteurs
        
        Args:
            extractors_dir: Répertoire contenant les extracteurs
        """
        self.extractors_dir = extractors_dir
        self.extractors: List[BaseContentExtractor] = []
        self.extractor_classes: Dict[str, Type[BaseContentExtractor]] = {}
        
        # Charger tous les extracteurs disponibles
        self.load_extractors()
    
    def load_extractors(self):
        """Charger dynamiquement tous les extracteurs depuis le répertoire"""
        if not os.path.exists(self.extractors_dir):
            os.makedirs(self.extractors_dir)
            print(f"Répertoire {self.extractors_dir} créé")
            return
        
        # Parcourir tous les fichiers Python dans le répertoire
        for filename in os.listdir(self.extractors_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                self._load_extractor_from_file(filename)
        
        # Trier les extracteurs : les spécialisés d'abord, le générique en dernier
        self.extractors.sort(key=lambda e: (
            len(e.supported_domains) == 0,  # Generic en dernier
            e.name
        ))
        
        print(f"{len(self.extractors)} extracteur(s) chargé(s)")
        for ext in self.extractors:
            print(f"  - {ext.name}: {ext.description}")
    
    def _load_extractor_from_file(self, filename: str):
        """
        Charger un extracteur depuis un fichier Python
        
        Args:
            filename: Nom du fichier à charger
        """
        filepath = os.path.join(self.extractors_dir, filename)
        module_name = filename[:-3]  # Enlever .py
        
        try:
            # Charger le module dynamiquement
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Trouver toutes les classes qui héritent de BaseContentExtractor
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, BaseContentExtractor) and 
                        obj is not BaseContentExtractor):
                        # Instancier et ajouter l'extracteur
                        extractor = obj()
                        self.extractors.append(extractor)
                        self.extractor_classes[extractor.name] = obj
                        print(f"Extracteur chargé: {extractor.name}")
        
        except Exception as e:
            print(f"Erreur lors du chargement de {filename}: {e}")
    
    def get_extractor_for_url(self, url: str, soup: BeautifulSoup = None) -> Optional[BaseContentExtractor]:
        """
        Trouver le meilleur extracteur pour une URL donnée
        
        Args:
            url: URL à traiter
            soup: BeautifulSoup object (optionnel)
            
        Returns:
            L'extracteur approprié ou None
        """
        # Essayer chaque extracteur dans l'ordre
        for extractor in self.extractors:
            if extractor.can_handle(url, soup):
                return extractor
        
        return None
    
    def get_extractor_by_name(self, name: str) -> Optional[BaseContentExtractor]:
        """
        Obtenir un extracteur par son nom
        
        Args:
            name: Nom de l'extracteur
            
        Returns:
            L'extracteur ou None si non trouvé
        """
        for extractor in self.extractors:
            if extractor.name == name:
                return extractor
        return None
    
    def list_extractors(self) -> List[Dict]:
        """
        Lister tous les extracteurs disponibles
        
        Returns:
            Liste de dictionnaires avec les infos des extracteurs
        """
        return [extractor.get_info() for extractor in self.extractors]
    
    def extract_from_url(self, url: str, extractor_name: Optional[str] = None) -> Dict:
        """
        Extraire le contenu d'une URL avec l'extracteur approprié
        
        Args:
            url: URL à traiter
            extractor_name: Nom de l'extracteur à utiliser (optionnel)
            
        Returns:
            Dictionnaire avec les informations extraites
        """
        # Si un extracteur spécifique est demandé
        if extractor_name:
            extractor = self.get_extractor_by_name(extractor_name)
            if extractor:
                return extractor.extract_from_url(url)
            else:
                return {
                    'error': f"Extracteur '{extractor_name}' non trouvé",
                    'url': url
                }
        
        # Sinon, trouver automatiquement l'extracteur approprié
        extractor = self.get_extractor_for_url(url)
        
        if extractor:
            return extractor.extract_from_url(url)
        else:
            return {
                'error': 'Aucun extracteur disponible pour cette URL',
                'url': url
            }
