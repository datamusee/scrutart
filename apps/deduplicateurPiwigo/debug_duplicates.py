#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour déboguer la détection des doublons Piwigo
"""

import re
import json

def extract_creator(description):
    """Extrait le nom du créateur depuis la description (dans la balise <a>)"""
    if not description:
        return None
    
    # Recherche de "Créateur:" suivi d'une balise <a>
    match = re.search(r'Créateur\s*:\s*<a[^>]*>([^<]+)</a>', description, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Fallback: recherche sans balise HTML
    match = re.search(r'Créateur\s*:\s*([^\n<,;]+)', description, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    return None

def test_extract_creator():
    """Teste l'extraction du créateur avec différents formats"""
    test_cases = [
        ('Créateur: Jean Dupont', 'Jean Dupont'),
        ('Créateur : Marie Martin', 'Marie Martin'),
        ('Créateur: <a href="#">Pierre Durant</a>', 'Pierre Durant'),
        ('Créateur : <a href="http://example.com">Sophie Leblanc</a>', 'Sophie Leblanc'),
        ('Description longue\nCréateur: <a>Test User</a>\nAutre info', 'Test User'),
        ('Pas de créateur ici', None),
        ('', None),
        ('Créateur:<a href="/tag/123">Artiste 123</a>', 'Artiste 123'),
    ]
    
    print("=== Test d'extraction du créateur ===\n")
    for description, expected in test_cases:
        result = extract_creator(description)
        status = "✓" if result == expected else "✗"
        print(f"{status} Description: {description[:50]}...")
        print(f"  Attendu: {expected}")
        print(f"  Obtenu:  {result}")
        print()

def find_duplicates_test(images):
    """Version de test de find_duplicates avec debug complet"""
    groups = {}
    
    print(f"\n=== Analyse de {len(images)} images ===\n")
    
    for image in images:
        creator = extract_creator(image.get('comment', ''))
        title = image.get('name', '').strip()
        
        print(f"Image ID: {image.get('id')}")
        print(f"  Titre: '{title}'")
        print(f"  Description: {image.get('comment', '')[:100]}...")
        print(f"  Créateur extrait: '{creator}'")
        
        if creator and title:
            # Normalisation pour la comparaison
            key = (
                ' '.join(creator.lower().split()),
                ' '.join(title.lower().split())
            )
            print(f"  Clé de groupement: {key}")
            
            if key not in groups:
                groups[key] = []
            groups[key].append(image)
        else:
            print(f"  ⚠️  Ignorée (créateur ou titre manquant)")
        print()
    
    duplicates = [group for group in groups.values() if len(group) > 1]
    
    print(f"\n=== Résumé ===")
    print(f"Images analysées: {len(images)}")
    print(f"Groupes créés: {len(groups)}")
    print(f"Groupes avec doublons: {len(duplicates)}")
    print()
    
    for i, group in enumerate(duplicates):
        print(f"Groupe {i+1}: {len(group)} images")
        print(f"  Titre: '{group[0].get('name')}'")
        print(f"  Créateur: '{extract_creator(group[0].get('comment', ''))}'")
        print(f"  IDs: {[img.get('id') for img in group]}")
        print()
    
    return duplicates

def test_with_sample_data():
    """Teste avec des données d'exemple"""
    print("\n" + "="*60)
    print("TEST AVEC DONNÉES D'EXEMPLE")
    print("="*60)
    
    sample_images = [
        {
            'id': 1,
            'name': 'Coucher de soleil',
            'comment': 'Créateur: <a href="#">Jean Dupont</a>'
        },
        {
            'id': 2,
            'name': 'Coucher de soleil',
            'comment': 'Créateur: <a href="#">Jean Dupont</a>'
        },
        {
            'id': 3,
            'name': 'Montagne',
            'comment': 'Créateur: <a href="#">Jean Dupont</a>'
        },
        {
            'id': 4,
            'name': 'Coucher de soleil',
            'comment': 'Créateur: <a href="#">Marie Martin</a>'
        },
        {
            'id': 5,
            'name': 'Plage',
            'comment': 'Pas de créateur'
        },
    ]
    
    duplicates = find_duplicates_test(sample_images)
    
    print("\n✓ Test terminé!")
    print(f"  Attendu: 1 groupe de doublons (images 1 et 2)")
    print(f"  Obtenu: {len(duplicates)} groupe(s) de doublons")

def analyze_real_data():
    """Permet d'analyser des vraies données depuis un fichier JSON"""
    print("\n" + "="*60)
    print("ANALYSE DE DONNÉES RÉELLES")
    print("="*60 + "\n")
    
    filename = input("Entrez le nom du fichier JSON contenant les images (ou ENTER pour skip): ").strip()
    
    if not filename:
        print("Analyse ignorée.\n")
        return
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            images = json.load(f)
        
        print(f"\n{len(images)} images chargées depuis {filename}\n")
        duplicates = find_duplicates_test(images)
        
        if duplicates:
            print(f"\n✓ {len(duplicates)} groupe(s) de doublons trouvés!")
        else:
            print("\n✗ Aucun doublon trouvé. Vérifiez:")
            print("  - Que les descriptions contiennent bien 'Créateur:'")
            print("  - Que les titres sont identiques (attention à la casse)")
            print("  - Que les créateurs sont identiques")
    
    except FileNotFoundError:
        print(f"\n✗ Fichier '{filename}' non trouvé.")
    except json.JSONDecodeError:
        print(f"\n✗ Erreur de lecture du fichier JSON.")
    except Exception as e:
        print(f"\n✗ Erreur: {e}")

if __name__ == '__main__':
    print("\n" + "="*60)
    print("OUTIL DE DÉBOGAGE - DÉTECTION DES DOUBLONS PIWIGO")
    print("="*60 + "\n")
    
    # Test 1: Extraction du créateur
    test_extract_creator()
    
    # Test 2: Données d'exemple
    test_with_sample_data()
    
    # Test 3: Données réelles (optionnel)
    analyze_real_data()
    
    print("\n" + "="*60)
    print("Tests terminés!")
    print("="*60 + "\n")
