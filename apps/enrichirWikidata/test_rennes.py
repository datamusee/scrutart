#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour l'extracteur du Musée de Rennes
"""

import sys
import os

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extractors.rennes_museum_extractor import RennesMuseumExtractor
import json

def test_rennes_extractor():
    """Tester l'extracteur avec l'URL exemple"""
    
    print("=" * 60)
    print("Test de l'extracteur Musée de Rennes")
    print("=" * 60)
    
    url = "https://collections.mba.rennes.fr/ark:/10946/0021068"
    
    print(f"\nURL à traiter: {url}")
    print("\nExtraction en cours...\n")
    
    # Créer l'extracteur
    extractor = RennesMuseumExtractor()
    
    # Vérifier si l'extracteur peut traiter l'URL
    if not extractor.can_handle(url):
        print("❌ L'extracteur ne peut pas traiter cette URL")
        return
    
    print("✓ L'extracteur peut traiter cette URL")
    
    # Extraire les informations
    result = extractor.extract_from_url(url)
    
    # Afficher les résultats
    print("\n" + "=" * 60)
    print("RÉSULTATS DE L'EXTRACTION")
    print("=" * 60 + "\n")
    
    if 'error' in result:
        print(f"❌ Erreur: {result['error']}")
        return
    
    # Afficher les informations principales
    print(f"Type: {result.get('type', 'N/A')}")
    print(f"Titre: {result.get('title', 'N/A')}")
    print(f"Type d'objet: {result.get('object_type', 'N/A')}")
    print(f"Domaine: {result.get('domain', 'N/A')}")
    
    print(f"\nCréateur: {result.get('creator', 'N/A')}")
    if result.get('creator_birth'):
        print(f"  Naissance: {result['creator_birth']}")
    if result.get('creator_death'):
        print(f"  Mort: {result['creator_death']}")
    
    print(f"\nDate de création: {result.get('date', 'N/A')}")
    print(f"Matériau: {result.get('material', 'N/A')}")
    
    if result.get('height'):
        print(f"Hauteur: {result['height']}")
    if result.get('width'):
        print(f"Largeur: {result['width']}")
    
    keywords = result.get('keywords', [])
    if keywords:
        print(f"\nMots-clés ({len(keywords)}):")
        for kw in keywords[:10]:  # Afficher les 10 premiers
            print(f"  - {kw}")
        if len(keywords) > 10:
            print(f"  ... et {len(keywords) - 10} autres")
    
    persons = result.get('depicted_persons', [])
    if persons:
        print(f"\nPersonnes représentées:")
        for person in persons:
            print(f"  - {person}")
    
    # Sauvegarder le résultat complet dans un fichier JSON
    output_file = "test_rennes_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Résultat complet sauvegardé dans: {output_file}")
    print("\n" + "=" * 60)


if __name__ == '__main__':
    test_rennes_extractor()
