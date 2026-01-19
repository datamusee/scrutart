#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour les matchers Wikidata
"""

import sys
import os
import json

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from matcher_manager import MatcherManager


def test_painting_matcher():
    """Tester le matcher de peintures"""
    print("=" * 60)
    print("Test du Matcher de Peintures")
    print("=" * 60)
    
    # Données extraites d'exemple (Duguesclin sur son lit de mort)
    extracted_data = {
        'type': 'painting',
        'title': 'Duguesclin sur son lit de mort',
        'creator': 'TOUDOUZE Edouard',
        'creator_birth': '1848',
        'creator_death': '1907',
        'date': '1904'
    }
    
    print("\nDonnées extraites :")
    print(json.dumps(extracted_data, indent=2, ensure_ascii=False))
    
    print("\nRecherche de correspondances dans Wikidata...")
    
    manager = MatcherManager('matchers')
    matches = manager.find_matches('painting', extracted_data)
    
    print(f"\n{len(matches)} correspondance(s) trouvée(s) :\n")
    
    for i, match in enumerate(matches, 1):
        print(f"{i}. {match.get('label', 'Sans titre')}")
        print(f"   ID: {match['id']}")
        print(f"   URL: {match['url']}")
        print(f"   Créateur: {match.get('creator', 'N/A')}")
        print(f"   Date: {match.get('date', 'N/A')}")
        print(f"   Confiance: {match.get('confidence', 0):.2%}")
        print(f"   Type de match: {match.get('match_type', 'N/A')}")
        if match.get('image'):
            print(f"   Image: {match['image'][:60]}...")
        print()


def test_artist_matcher():
    """Tester le matcher d'artistes"""
    print("=" * 60)
    print("Test du Matcher d'Artistes")
    print("=" * 60)
    
    # Données extraites d'exemple
    extracted_data = {
        'type': 'artist',
        'name': 'TOUDOUZE Edouard',
        'birth_date': '1848',
        'death_date': '1907'
    }
    
    print("\nDonnées extraites :")
    print(json.dumps(extracted_data, indent=2, ensure_ascii=False))
    
    print("\nRecherche de correspondances dans Wikidata...")
    
    manager = MatcherManager('matchers')
    matches = manager.find_matches('artist', extracted_data)
    
    print(f"\n{len(matches)} correspondance(s) trouvée(s) :\n")
    
    for i, match in enumerate(matches, 1):
        print(f"{i}. {match.get('label', 'Sans nom')}")
        print(f"   ID: {match['id']}")
        print(f"   URL: {match['url']}")
        print(f"   Naissance: {match.get('birth', 'N/A')}")
        print(f"   Mort: {match.get('death', 'N/A')}")
        print(f"   Occupation: {match.get('occupation', 'N/A')}")
        print(f"   Confiance: {match.get('confidence', 0):.2%}")
        print(f"   Type de match: {match.get('match_type', 'N/A')}")
        if match.get('image'):
            print(f"   Image: {match['image'][:60]}...")
        print()


def test_matchers_list():
    """Tester le listage des matchers"""
    print("=" * 60)
    print("Matchers Disponibles")
    print("=" * 60)
    
    manager = MatcherManager('matchers')
    matchers = manager.list_matchers()
    
    print(f"\n{len(matchers)} matcher(s) disponible(s) :\n")
    
    for matcher in matchers:
        print(f"- {matcher['name']}")
        print(f"  Description: {matcher['description']}")
        print(f"  Types supportés: {', '.join(matcher['supported_types'])}")
        print()


if __name__ == '__main__':
    print("\n🔍 Tests des Matchers Wikidata\n")
    
    # Test 1: Lister les matchers
    test_matchers_list()
    
    # Test 2: Tester le matcher de peintures
    input("Appuyez sur Entrée pour tester le matcher de peintures...")
    test_painting_matcher()
    
    # Test 3: Tester le matcher d'artistes  
    input("Appuyez sur Entrée pour tester le matcher d'artistes...")
    test_artist_matcher()
    
    print("\n✅ Tests terminés !")
