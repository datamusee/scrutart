#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Matcher Manager - Gère le chargement dynamique des matchers Wikidata
"""

import os
import importlib.util
import inspect
from typing import List, Dict, Optional, Type
from base_matcher import BaseWikidataMatcher


class MatcherManager:
    """Gestionnaire pour charger et sélectionner les matchers Wikidata"""
    
    def __init__(self, matchers_dir: str = 'matchers'):
        """
        Initialiser le gestionnaire de matchers
        
        Args:
            matchers_dir: Répertoire contenant les matchers
        """
        self.matchers_dir = matchers_dir
        self.matchers: List[BaseWikidataMatcher] = []
        self.matcher_classes: Dict[str, Type[BaseWikidataMatcher]] = {}
        
        # Charger tous les matchers disponibles
        self.load_matchers()
    
    def load_matchers(self):
        """Charger dynamiquement tous les matchers depuis le répertoire"""
        if not os.path.exists(self.matchers_dir):
            os.makedirs(self.matchers_dir)
            print(f"Répertoire {self.matchers_dir} créé")
            return
        
        # Parcourir tous les fichiers Python dans le répertoire
        for filename in os.listdir(self.matchers_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                self._load_matcher_from_file(filename)
        
        print(f"{len(self.matchers)} matcher(s) chargé(s)")
        for matcher in self.matchers:
            print(f"  - {matcher.name}: {matcher.description}")
            print(f"    Types supportés: {', '.join(matcher.supported_types)}")
    
    def _load_matcher_from_file(self, filename: str):
        """
        Charger un matcher depuis un fichier Python
        
        Args:
            filename: Nom du fichier à charger
        """
        filepath = os.path.join(self.matchers_dir, filename)
        module_name = filename[:-3]  # Enlever .py
        
        try:
            # Charger le module dynamiquement
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Trouver toutes les classes qui héritent de BaseWikidataMatcher
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, BaseWikidataMatcher) and 
                        obj is not BaseWikidataMatcher):
                        # Instancier et ajouter le matcher
                        matcher = obj()
                        self.matchers.append(matcher)
                        self.matcher_classes[matcher.name] = obj
                        print(f"Matcher chargé: {matcher.name}")
        
        except Exception as e:
            print(f"Erreur lors du chargement de {filename}: {e}")
    
    def get_matcher_for_type(self, entity_type: str, extracted_data: Dict) -> Optional[BaseWikidataMatcher]:
        """
        Trouver le meilleur matcher pour un type d'entité
        
        Args:
            entity_type: Type d'entité (painting, artist, etc.)
            extracted_data: Données extraites
            
        Returns:
            Le matcher approprié ou None
        """
        # Essayer chaque matcher dans l'ordre
        for matcher in self.matchers:
            if matcher.can_handle(entity_type, extracted_data):
                return matcher
        
        return None
    
    def get_matcher_by_name(self, name: str) -> Optional[BaseWikidataMatcher]:
        """
        Obtenir un matcher par son nom
        
        Args:
            name: Nom du matcher
            
        Returns:
            Le matcher ou None si non trouvé
        """
        for matcher in self.matchers:
            if matcher.name == name:
                return matcher
        return None
    
    def list_matchers(self) -> List[Dict]:
        """
        Lister tous les matchers disponibles
        
        Returns:
            Liste de dictionnaires avec les infos des matchers
        """
        return [matcher.get_info() for matcher in self.matchers]
    
    def list_matchers_for_type(self, entity_type: str) -> List[Dict]:
        """
        Lister les matchers compatibles avec un type d'entité
        
        Args:
            entity_type: Type d'entité
            
        Returns:
            Liste de matchers compatibles
        """
        compatible = []
        for matcher in self.matchers:
            if entity_type.lower() in matcher.supported_types:
                compatible.append(matcher.get_info())
        return compatible
    
    def find_matches(self, entity_type: str, extracted_data: Dict, 
                    matcher_name: Optional[str] = None) -> List[Dict]:
        """
        Trouver des correspondances Wikidata pour une entité
        
        Args:
            entity_type: Type d'entité
            extracted_data: Données extraites
            matcher_name: Nom du matcher à utiliser (optionnel)
            
        Returns:
            Liste de correspondances trouvées
        """
        # Si un matcher spécifique est demandé
        if matcher_name:
            matcher = self.get_matcher_by_name(matcher_name)
            if matcher and matcher.can_handle(entity_type, extracted_data):
                return matcher.find_matches(extracted_data)
            else:
                print(f"Matcher '{matcher_name}' non trouvé ou incompatible")
                return []
        
        # Sinon, trouver automatiquement le matcher approprié
        matcher = self.get_matcher_for_type(entity_type, extracted_data)
        
        if matcher:
            print(f"Utilisation du matcher: {matcher.name}")
            return matcher.find_matches(extracted_data)
        else:
            print(f"Aucun matcher disponible pour le type: {entity_type}")
            return []
