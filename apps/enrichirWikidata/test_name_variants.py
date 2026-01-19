#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Outil pour tester la génération de variantes de noms
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from property_matcher import PropertyMatcher


def test_name_generation():
    """Tester la génération de variantes pour différents noms"""
    
    matcher = PropertyMatcher()
    
    test_cases = [
        "TOUDOUZE Edouard",
        "Edouard TOUDOUZE",
        "Édouard Toudouze",
        "Toudouze Édouard",
        "Vincent VAN GOGH",
        "VAN GOGH Vincent",
        "Leonardo da Vinci",
        "REMBRANDT van Rijn",
        "Pablo PICASSO",
        "Claude MONET",
        "Pierre-Auguste RENOIR",
    ]
    
    print("=" * 80)
    print("Test de Génération de Variantes de Noms")
    print("=" * 80)
    
    for name in test_cases:
        print(f"\n📝 Nom original: '{name}'")
        variants = matcher._generate_name_variants(name)
        print(f"   Variantes générées ({len(variants)}):")
        for i, variant in enumerate(variants, 1):
            print(f"      {i}. '{variant}'")


def interactive_test():
    """Mode interactif pour tester n'importe quel nom"""
    
    matcher = PropertyMatcher()
    
    print("\n" + "=" * 80)
    print("Mode Interactif - Génération de Variantes")
    print("=" * 80)
    print("\nEntrez un nom pour voir ses variantes (ou 'quit' pour quitter)")
    
    while True:
        name = input("\nNom: ").strip()
        
        if name.lower() in ['quit', 'exit', 'q']:
            break
        
        if not name:
            continue
        
        variants = matcher._generate_name_variants(name)
        print(f"\nVariantes générées ({len(variants)}):")
        for i, variant in enumerate(variants, 1):
            print(f"   {i}. '{variant}'")


if __name__ == '__main__':
    # Test automatique
    test_name_generation()
    
    # Mode interactif
    try:
        interactive_test()
    except KeyboardInterrupt:
        print("\n\nAu revoir!")
