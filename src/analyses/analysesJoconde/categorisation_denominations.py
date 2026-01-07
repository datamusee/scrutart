import json
import re
from collections import Counter


def categoriser_element(element):
    """
    Catégorise un élément artistique/culturel en fonction de mots-clés.
    Retourne une liste de catégories applicables.
    """
    element_lower = element.lower()
    categories = []

    # Dictionnaire de mots-clés pour chaque catégorie
    regles_categorisation = {
        'peinture': ['peinture', 'tableau', 'toile', 'fresque', 'aquarelle', 'huile', 'acrylique', 'gouache'],
        'sculpture': ['sculpture', 'statue', 'buste', 'relief', 'modelage', 'taille'],
        'dessin': ['dessin', 'croquis', 'esquisse', 'pastel', 'fusain', 'crayon', 'encre'],
        'photographie': ['photo', 'photographie', 'cliché', 'daguerréotype'],
        'gravure': ['gravure', 'estampe', 'lithographie', 'sérigraphie', 'eau-forte'],
        'céramique': ['céramique', 'poterie', 'porcelaine', 'faïence', 'grès', 'terre cuite'],
        'verre': ['verre', 'vitrail', 'cristal', 'verrerie'],
        'textile': ['textile', 'tissu', 'tapisserie', 'broderie', 'dentelle', 'étoffe'],
        'vêtement': ['vêtement', 'habit', 'costume', 'robe', 'chemise', 'pantalon', 'manteau', 'chapeau', 'chaussure'],
        'bijou': ['bijou', 'bijouterie', 'joaillerie', 'collier', 'bracelet', 'bague', 'boucle', 'pendentif'],
        'meuble': ['meuble', 'mobilier', 'chaise', 'table', 'armoire', 'commode', 'lit', 'buffet', 'fauteuil', 'siège'],
        'objet de décoration': ['décoration', 'décoratif', 'ornement', 'vase', 'lampe', 'chandelier', 'miroir',
                                'cadre'],
        'objet de cuisine': ['cuisine', 'culinaire', 'ustensile', 'casserole', 'plat', 'assiette', 'couverts', 'bol'],
        'instrument de musique': ['instrument', 'musique', 'musical', 'violon', 'piano', 'guitare', 'flûte', 'tambour'],
        'livre': ['livre', 'manuscrit', 'ouvrage', 'volume', 'codex', 'incunable'],
        'document': ['document', 'parchemin', 'papier', 'carte', 'plan', 'affiche'],
        'monnaie': ['monnaie', 'pièce', 'médaille', 'numismatique'],
        'arme': ['arme', 'épée', 'sabre', 'lance', 'bouclier', 'armure'],
        'outil': ['outil', 'outillage', 'instrument', 'ustensile'],
        'objet religieux': ['religieux', 'sacré', 'liturgique', 'reliquaire', 'croix', 'icône', 'calice'],
        'jouet': ['jouet', 'jeu', 'poupée', 'figurine'],
    }

    # Vérifier chaque catégorie
    for categorie, mots_cles in regles_categorisation.items():
        for mot_cle in mots_cles:
            if mot_cle in element_lower:
                if categorie not in categories:
                    categories.append(categorie)
                break

    # Si aucune catégorie spécifique n'est trouvée, catégoriser comme "art visuel" ou "objet"
    if not categories:
        # Mots-clés généraux pour l'art visuel
        art_visuel_keywords = ['art', 'œuvre', 'oeuvre', 'création', 'artistique']
        if any(keyword in element_lower for keyword in art_visuel_keywords):
            categories.append('art visuel')
        else:
            categories.append('objet')

    return categories


def creer_json_categorise(fichier_entree, fichier_sortie):
    """
    Crée un JSON avec chaque élément comme clé associée à un dictionnaire
    contenant ses catégories, plus une liste récapitulative des catégories.
    """
    # Lire le fichier JSON d'entrée
    with open(fichier_entree, 'r', encoding='utf-8') as f:
        liste_elements = json.load(f)

    # Créer le dictionnaire principal
    resultat = {}
    toutes_categories = []

    # Traiter chaque élément
    for element in liste_elements:
        if isinstance(element, str):
            categories = categoriser_element(element)
            resultat[element] = {
                "category": categories
            }
            toutes_categories.extend(categories)

    # Compter les occurrences de chaque catégorie
    compteur_categories = Counter(toutes_categories)

    # Créer la liste des catégories avec leur nombre
    category_list = [
        {"name": cat, "count": count}
        for cat, count in sorted(compteur_categories.items(), key=lambda x: x[1], reverse=True)
    ]

    # Construire le JSON final
    json_final = {
        "items": resultat,
        "category_list": category_list
    }

    # Sauvegarder
    with open(fichier_sortie, 'w', encoding='utf-8') as f:
        json.dump(json_final, f, ensure_ascii=False, indent=2)

    print(f"Catégorisation terminée !")
    print(f"Nombre d'éléments traités : {len(resultat)}")
    print(f"Nombre de catégories distinctes : {len(category_list)}")
    print(f"\nRépartition des catégories :")
    for cat_info in category_list[:10]:  # Afficher les 10 premières
        print(f"  - {cat_info['name']}: {cat_info['count']} élément(s)")

    return json_final


# Exemple d'utilisation
if __name__ == "__main__":
    fichier_entree = "objets_culturels_traites_t1.json"
    fichier_sortie = "objets_culturels_categorises.json"

    try:
        resultat = creer_json_categorise(fichier_entree, fichier_sortie)

        # Afficher quelques exemples
        print(f"\nExemples d'éléments catégorisés :")
        for i, (element, info) in enumerate(list(resultat["items"].items())[:5]):
            print(f"  '{element}' -> {info['category']}")

    except FileNotFoundError:
        print(f"Erreur : Le fichier '{fichier_entree}' n'a pas été trouvé.")
    except json.JSONDecodeError:
        print(f"Erreur : Le fichier '{fichier_entree}' n'est pas un JSON valide.")
    except Exception as e:
        print(f"Erreur inattendue : {e}")