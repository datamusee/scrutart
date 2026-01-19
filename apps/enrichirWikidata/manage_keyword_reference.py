#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Outil de gestion des références manuelles de mots-clés
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from property_matcher import PropertyMatcher


def list_references(matcher):
    """Lister toutes les références manuelles"""
    print("\n" + "=" * 70)
    print("RÉFÉRENCES MANUELLES")
    print("=" * 70)
    
    if not matcher.keyword_reference:
        print("\nAucune référence manuelle définie.")
        return
    
    for keyword, entities in sorted(matcher.keyword_reference.items()):
        print(f"\n📌 '{keyword}' ({len(entities)} entité(s)) :")
        for entity in entities:
            print(f"   → {entity['qid']} - {entity['label_fr']}")
            if entity.get('label_en'):
                print(f"      EN: {entity['label_en']}")
            print(f"      Confiance: {entity.get('confidence', 0.95):.0%}")
            if entity.get('description'):
                print(f"      {entity['description'][:60]}...")


def add_reference(matcher):
    """Ajouter une référence manuelle interactivement"""
    print("\n" + "=" * 70)
    print("AJOUTER UNE RÉFÉRENCE MANUELLE")
    print("=" * 70)
    
    keyword = input("\nMot-clé : ").strip()
    if not keyword:
        print("❌ Mot-clé requis")
        return
    
    qid = input("QID Wikidata (ex: Q42177) : ").strip()
    if not qid.startswith('Q'):
        print("❌ QID invalide (doit commencer par Q)")
        return
    
    label_fr = input("Label français : ").strip()
    if not label_fr:
        print("❌ Label français requis")
        return
    
    label_en = input("Label anglais (optionnel) : ").strip()
    description = input("Description (optionnel) : ").strip()
    
    confidence_str = input("Confiance (0-1, défaut 0.95) : ").strip()
    try:
        confidence = float(confidence_str) if confidence_str else 0.95
    except ValueError:
        confidence = 0.95
    
    matcher.add_keyword_reference(
        keyword=keyword.lower(),
        qid=qid,
        label_fr=label_fr,
        label_en=label_en,
        description=description,
        confidence=confidence
    )


def search_and_add(matcher):
    """Rechercher un concept et ajouter une référence"""
    print("\n" + "=" * 70)
    print("RECHERCHER ET AJOUTER")
    print("=" * 70)
    
    keyword = input("\nMot-clé à rechercher : ").strip()
    if not keyword:
        print("❌ Mot-clé requis")
        return
    
    print(f"\n🔍 Recherche de '{keyword}' dans Wikidata...")
    
    # Créer un matcher temporaire sans référence pour cette recherche
    temp_matcher = PropertyMatcher()
    temp_matcher.keyword_reference = {}  # Ignorer les références pour cette recherche
    
    # Recherche automatique uniquement
    matches = temp_matcher.search_concept(keyword)
    
    if not matches:
        print("❌ Aucun résultat trouvé")
        return
    
    print(f"\n{len(matches)} résultat(s) trouvé(s) :\n")
    
    for i, match in enumerate(matches, 1):
        print(f"{i}. {match['label']} ({match['id']})")
        print(f"   Confiance: {match['confidence']:.0%}")
        if match.get('description'):
            print(f"   {match['description'][:70]}...")
        if match.get('type'):
            print(f"   Type: {match['type']}")
        print()
    
    choice = input("Numéro de l'entité à ajouter (0 pour annuler) : ").strip()
    
    try:
        choice_num = int(choice)
        if choice_num == 0:
            print("Annulé")
            return
        
        if 1 <= choice_num <= len(matches):
            selected = matches[choice_num - 1]
            
            # Demander confirmation
            print(f"\n📝 Ajouter '{keyword}' → {selected['id']} ({selected['label']}) ?")
            confirm = input("Confirmer (o/n) : ").strip().lower()
            
            if confirm == 'o':
                matcher.add_keyword_reference(
                    keyword=keyword.lower(),
                    qid=selected['id'],
                    label_fr=selected['label'],
                    label_en='',  # Pas disponible dans la recherche
                    description=selected.get('description', ''),
                    confidence=selected['confidence']
                )
        else:
            print("❌ Numéro invalide")
    except ValueError:
        print("❌ Entrée invalide")


def remove_reference(matcher):
    """Supprimer une référence manuelle"""
    print("\n" + "=" * 70)
    print("SUPPRIMER UNE RÉFÉRENCE")
    print("=" * 70)
    
    list_references(matcher)
    
    keyword = input("\nMot-clé : ").strip().lower()
    if keyword not in matcher.keyword_reference:
        print(f"❌ Aucune référence pour '{keyword}'")
        return
    
    entities = matcher.keyword_reference[keyword]
    
    if len(entities) == 1:
        qid = entities[0]['qid']
        confirm = input(f"Supprimer {qid} ? (o/n) : ").strip().lower()
        if confirm == 'o':
            del matcher.keyword_reference[keyword]
    else:
        print(f"\nPlusieurs entités pour '{keyword}' :")
        for i, entity in enumerate(entities, 1):
            print(f"{i}. {entity['qid']} - {entity['label_fr']}")
        
        choice = input("\nNuméro à supprimer (0 pour tout supprimer) : ").strip()
        try:
            choice_num = int(choice)
            if choice_num == 0:
                del matcher.keyword_reference[keyword]
                print(f"✅ Toutes les références pour '{keyword}' supprimées")
            elif 1 <= choice_num <= len(entities):
                entities.pop(choice_num - 1)
                if not entities:
                    del matcher.keyword_reference[keyword]
                print(f"✅ Référence supprimée")
            else:
                print("❌ Numéro invalide")
                return
        except ValueError:
            print("❌ Entrée invalide")
            return
    
    # Sauvegarder
    with open(matcher.reference_file, 'w', encoding='utf-8') as f:
        json.dump(matcher.keyword_reference, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Fichier sauvegardé")


def export_reference(matcher):
    """Exporter les références dans un format lisible"""
    output_file = 'keyword_reference_export.txt'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("RÉFÉRENCES MANUELLES WIKIDATA\n")
        f.write("=" * 70 + "\n\n")
        
        for keyword, entities in sorted(matcher.keyword_reference.items()):
            f.write(f"Mot-clé: {keyword}\n")
            f.write("-" * 70 + "\n")
            for entity in entities:
                f.write(f"  QID: {entity['qid']}\n")
                f.write(f"  Label FR: {entity['label_fr']}\n")
                if entity.get('label_en'):
                    f.write(f"  Label EN: {entity['label_en']}\n")
                if entity.get('description'):
                    f.write(f"  Description: {entity['description']}\n")
                f.write(f"  Confiance: {entity.get('confidence', 0.95):.0%}\n")
                f.write(f"  URL: https://www.wikidata.org/wiki/{entity['qid']}\n")
                f.write("\n")
            f.write("\n")
    
    print(f"\n✅ Références exportées vers: {output_file}")


def main():
    """Menu principal"""
    matcher = PropertyMatcher()
    
    while True:
        print("\n" + "=" * 70)
        print("GESTIONNAIRE DE RÉFÉRENCES WIKIDATA")
        print("=" * 70)
        print("\n1. Lister les références")
        print("2. Ajouter une référence manuellement")
        print("3. Rechercher et ajouter")
        print("4. Supprimer une référence")
        print("5. Exporter les références")
        print("0. Quitter")
        
        choice = input("\nChoix : ").strip()
        
        if choice == '1':
            list_references(matcher)
        elif choice == '2':
            add_reference(matcher)
        elif choice == '3':
            search_and_add(matcher)
        elif choice == '4':
            remove_reference(matcher)
        elif choice == '5':
            export_reference(matcher)
        elif choice == '0':
            print("\nAu revoir!")
            break
        else:
            print("❌ Choix invalide")
        
        input("\nAppuyez sur Entrée pour continuer...")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrompu par l'utilisateur")
        sys.exit(0)
