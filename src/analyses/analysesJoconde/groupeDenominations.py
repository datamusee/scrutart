import json
import re
from collections import defaultdict


def extraire_mot_cle(nom_item):
    """
    Extrait le mot-clé principal d'un nom d'item.
    Exemples:
    - "tableau" -> "tableau"
    - "tableau (recto verso)" -> "tableau"
    - "bague à intaille" -> "bague"
    - "bague épiscopale (?)" -> "bague"
    """
    # Enlever le contenu entre parenthèses
    nom_nettoye = re.sub(r'\s*\([^)]*\)', '', nom_item)

    # Enlever le contenu entre crochets
    nom_nettoye = re.sub(r'\s*\[[^\]]*\]', '', nom_nettoye)

    # Enlever les points d'interrogation
    nom_nettoye = nom_nettoye.replace('?', '')

    # Prendre le premier mot (avant "à", "de", "en", etc.)
    mots_separateurs = [' à ', ' de ', ' en ', ' du ', ' des ', ' avec ', ' sans ']
    for sep in mots_separateurs:
        if sep in nom_nettoye:
            nom_nettoye = nom_nettoye.split(sep)[0]
            break

    # Nettoyer les espaces
    mot_cle = nom_nettoye.strip().lower()

    return mot_cle


def regrouper_elements(fichier_entree, fichier_sortie):
    """
    Lit un fichier JSON, regroupe les éléments de la clé 'items' par mot-clé,
    attribue à chaque élément ses groupes, et sauvegarde le résultat.
    """
    # Charger le fichier JSON
    with open(fichier_entree, 'r', encoding='utf-8') as f:
        donnees = json.load(f)

    # Vérifier que la clé 'items' existe
    if 'items' not in donnees:
        raise ValueError("Le fichier JSON doit contenir une clé 'items'")

    items = donnees['items']

    # Créer un dictionnaire pour stocker les groupes
    groupes_dict = defaultdict(list)

    # Analyser chaque élément dans 'items'
    for nom_item, details in items.items():
        mot_cle = extraire_mot_cle(nom_item)
        groupes_dict[mot_cle].append(nom_item)

    # Attribuer le(s) groupe(s) à chaque élément
    items_avec_groupes = {}
    for nom_item, details in items.items():
        mot_cle = extraire_mot_cle(nom_item)
        items_avec_groupes[nom_item] = {
            **details,
            "groupes": [mot_cle]  # Pour l'instant un seul groupe, extensible
        }

    # Créer la liste des groupes triée par nombre d'items décroissant
    liste_groupes = sorted(groupes_dict.items(), key=lambda x: len(x[1]), reverse=True)

    # Créer le dictionnaire des groupes avec leurs détails
    groupes_detailles = {}
    for groupe, items_du_groupe in groupes_dict.items():
        groupes_detailles[groupe] = {
            "count": len(items_du_groupe),
            "items": items_du_groupe
        }

    # Préparer le résultat en conservant toutes les clés existantes
    resultat = {**donnees}
    resultat['items'] = items_avec_groupes
    resultat['groupes'] = groupes_detailles

    # Sauvegarder le résultat
    with open(fichier_sortie, 'w', encoding='utf-8') as f:
        json.dump(resultat, f, ensure_ascii=False, indent=2)

    # Afficher les informations sur la console
    print(f"✓ Traitement terminé!")
    print(f"✓ {len(items)} éléments traités")
    print(f"✓ Nombre de groupes trouvés: {len(liste_groupes)}")
    print(f"✓ Résultat sauvegardé dans '{fichier_sortie}'")

    # Afficher la liste complète des groupes triée par nombre d'items
    print("\n--- Liste des groupes (par nombre d'items décroissant) ---")
    for i, (groupe, items_du_groupe) in enumerate(liste_groupes, 1):
        nb_items = len(items_du_groupe)
        print(f"{i:3d}. {groupe} ({nb_items} élément{'s' if nb_items > 1 else ''})")


# Exemple d'utilisation
if __name__ == "__main__":
    # Remplacez ces noms de fichiers par les vôtres
    fichier_entree = "objets_culturels_categorises.json"
    fichier_sortie = "denominations_groupes.json"

    try:
        regrouper_elements(fichier_entree, fichier_sortie)
    except FileNotFoundError:
        print(f"❌ Erreur: Le fichier '{fichier_entree}' n'existe pas.")
        print("\nCréation d'un fichier exemple...")

        # Créer un fichier exemple
        exemple = {
            "titre": "Collection d'objets",
            "date": "2025",
            "items": {
                "appeau à pluvier": {
                    "category": ["objet"]
                },
                "tableau": {
                    "category": ["art"]
                },
                "tableau (recto verso)": {
                    "category": ["art"]
                },
                "bague à intaille": {
                    "category": ["bijou"]
                },
                "bague épiscopale (?)": {
                    "category": ["bijou"]
                }
            }
        }

        with open(fichier_entree, 'w', encoding='utf-8') as f:
            json.dump(exemple, f, ensure_ascii=False, indent=2)

        print(f"✓ Fichier exemple '{fichier_entree}' créé.")
        print("Relancez le programme pour le traiter.")
    except Exception as e:
        print(f"❌ Erreur: {e}")