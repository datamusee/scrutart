#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour le Property Matcher
"""

import sys
import os
import json

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from property_matcher import PropertyMatcher


def test_painting_properties():
    """Tester le matching des propriétés d'une peinture"""
    print("=" * 70)
    print("Test du Property Matching pour une Peinture")
    print("=" * 70)
    
    # Données extraites d'exemple (Duguesclin sur son lit de mort)
    # IMPORTANT: Limiter les mots-clés pour éviter trop de requêtes
    extracted_data = {
        'type': 'painting',
        'title': 'Duguesclin sur son lit de mort',
        'creator': 'TOUDOUZE Edouard',
        'creator_birth': '1848',
        'creator_death': '1907',
        'date': '1904',
        'material': 'Toile',
        'keywords': ['scène historique', 'cadavre', 'lit'],  # Limité à 3 pour le test
        'depicted_persons': ['Bertrand Du Guesclin']
    }
    
    print("\nDonnées extraites :")
    print(json.dumps(extracted_data, indent=2, ensure_ascii=False))
    print("\n⚠️  Note: Traitement limité à 3 mots-clés pour respecter les limites de Wikidata")
    
    print("\n" + "=" * 70)
    print("Recherche des correspondances Wikidata pour chaque propriété...")
    print("(Délai de 1.5s entre chaque requête pour respecter les limites)")
    print("=" * 70)
    
    matcher = PropertyMatcher()
    property_matches = matcher.match_all_properties(extracted_data, 'painting')
    
    # Afficher les résultats pour chaque propriété
    
    # 1. Créateur
    if 'creator' in property_matches:
        print("\n📍 CRÉATEUR")
        print("-" * 70)
        for match in property_matches['creator'][:3]:  # Top 3
            print(f"\n  {match['label']} ({match['id']})")
            print(f"  Confiance: {match['confidence']:.0%}")
            if match.get('birth'):
                print(f"  Naissance: {match['birth']}")
            if match.get('death'):
                print(f"  Mort: {match['death']}")
            print(f"  URL: {match['url']}")
    
    # 2. Personnes représentées
    if 'depicted_persons' in property_matches:
        print("\n👤 PERSONNES REPRÉSENTÉES")
        print("-" * 70)
        for person, matches in property_matches['depicted_persons'].items():
            print(f"\n  Recherche pour: {person}")
            for match in matches[:2]:  # Top 2
                print(f"    → {match['label']} ({match['id']}) - {match['confidence']:.0%}")
                if match.get('description'):
                    print(f"      {match['description'][:80]}...")
    
    # 3. Mots-clés
    if 'keywords' in property_matches:
        print("\n🔑 MOTS-CLÉS")
        print("-" * 70)
        for keyword, matches in property_matches['keywords'].items():
            print(f"\n  Recherche pour: '{keyword}'")
            if matches:
                for match in matches[:2]:  # Top 2
                    print(f"    → {match['label']} ({match['id']}) - {match['confidence']:.0%}")
                    if match.get('description'):
                        print(f"      {match['description'][:80]}...")
            else:
                print(f"    ✗ Aucune correspondance trouvée")
    
    # 4. Matériau
    if 'material' in property_matches:
        print("\n🎨 MATÉRIAU")
        print("-" * 70)
        for match in property_matches['material'][:2]:
            print(f"  → {match['label']} ({match['id']}) - {match['confidence']:.0%}")
    
    # Sauvegarder les résultats complets
    output_file = "test_property_matching_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(property_matches, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Résultats complets sauvegardés dans: {output_file}")
    
    # Statistiques
    print("\n" + "=" * 70)
    print("STATISTIQUES")
    print("=" * 70)
    
    total_properties = 0
    total_matches = 0
    
    for prop, matches in property_matches.items():
        if isinstance(matches, dict):  # keywords, depicted_persons
            total_properties += len(matches)
            for item_matches in matches.values():
                total_matches += len(item_matches)
        elif isinstance(matches, list):  # creator, material, etc.
            total_properties += 1
            total_matches += len(matches)
    
    print(f"Propriétés traitées: {total_properties}")
    print(f"Correspondances trouvées: {total_matches}")
    print("=" * 70)


def test_single_property():
    """Tester le matching d'une propriété individuelle"""
    print("\n" + "=" * 70)
    print("Test de Recherche Individuelle")
    print("=" * 70)
    
    matcher = PropertyMatcher()
    
    # Test 1: Recherche de personne
    print("\n1. Recherche de personne: 'Édouard Toudouze'")
    matches = matcher.search_person("Édouard Toudouze", "1848", "1907")
    for match in matches[:3]:
        print(f"   {match['label']} - {match['id']} - {match['confidence']:.0%}")
    
    # Test 2: Recherche de concept
    print("\n2. Recherche de concept: 'scène historique'")
    matches = matcher.search_concept("scène historique")
    for match in matches[:3]:
        print(f"   {match['label']} - {match['id']} - {match['confidence']:.0%}")
    
    # Test 3: Recherche de matériau
    print("\n3. Recherche de matériau: 'toile'")
    matches = matcher.search_material("toile")
    for match in matches[:3]:
        print(f"   {match['label']} - {match['id']} - {match['confidence']:.0%}")


def test_name_variants():
    """Tester les différentes variantes de noms"""
    print("\n" + "=" * 70)
    print("Test des Variantes de Noms")
    print("=" * 70)
    
    matcher = PropertyMatcher()
    
    # Test 1: NOM Prénom
    print("\n1. Test 'TOUDOUZE Edouard' (NOM Prénom)")
    matches1 = matcher.search_person("TOUDOUZE Edouard", "1848", "1907")
    print(f"   Résultats: {len(matches1)}")
    if matches1:
        print(f"   Meilleur: {matches1[0]['label']} - {matches1[0]['confidence']:.0%}")
    
    # Test 2: Prénom NOM
    print("\n2. Test 'Edouard TOUDOUZE' (Prénom NOM)")
    matches2 = matcher.search_person("Edouard TOUDOUZE", "1848", "1907")
    print(f"   Résultats: {len(matches2)}")
    if matches2:
        print(f"   Meilleur: {matches2[0]['label']} - {matches2[0]['confidence']:.0%}")
    
    # Test 3: Prénom Nom (casse normale)
    print("\n3. Test 'Édouard Toudouze' (Prénom Nom)")
    matches3 = matcher.search_person("Édouard Toudouze", "1848", "1907")
    print(f"   Résultats: {len(matches3)}")
    if matches3:
        print(f"   Meilleur: {matches3[0]['label']} - {matches3[0]['confidence']:.0%}")
    
    # Vérifier que toutes les variantes trouvent la même entité
    if matches1 and matches2 and matches3:
        qid1 = matches1[0]['id']
        qid2 = matches2[0]['id']
        qid3 = matches3[0]['id']
        
        if qid1 == qid2 == qid3:
            print(f"\n✅ Toutes les variantes trouvent la même entité: {qid1}")
        else:
            print(f"\n⚠️  Résultats différents:")
            print(f"   Variante 1: {qid1}")
            print(f"   Variante 2: {qid2}")
            print(f"   Variante 3: {qid3}")


if __name__ == '__main__':
    print("\n🔍 Tests du Property Matching\n")
    
    # Test principal
    test_painting_properties()
    
    # Test des variantes de noms
    input("\nAppuyez sur Entrée pour tester les variantes de noms...")
    test_name_variants()
    
    # Tests individuels
    input("\nAppuyez sur Entrée pour tester des recherches individuelles...")
    test_single_property()
    
    print("\n✅ Tous les tests terminés !\n")
