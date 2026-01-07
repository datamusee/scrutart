import json


def separer_elements_avec_pointvirgule(fichier_entree, fichier_sortie):
    """
    Lit un fichier JSON, sépare les éléments contenant des ';',
    et sauvegarde le résultat dans un nouveau fichier.

    Args:
        fichier_entree: Chemin du fichier JSON à traiter
        fichier_sortie: Chemin du fichier JSON de sortie
    """
    # Lire le fichier JSON
    with open(fichier_entree, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Nouvelle liste pour stocker les éléments traités
    nouvelle_liste = []

    # Traiter chaque élément
    for element in data:
        if isinstance(element, str) and ';' in element:
            # Séparer la chaîne au niveau des ';'
            sous_elements = element.split(';')
            # Nettoyer les espaces et ajouter chaque sous-élément
            for sous_element in sous_elements:
                sous_element_propre = sous_element.strip()
                if sous_element_propre:  # Ignorer les chaînes vides
                    nouvelle_liste.append(sous_element_propre)
        else:
            # Garder l'élément tel quel
            nouvelle_liste.append(element)

    # éliminer les doublons
    nouvelle_liste = list(set(nouvelle_liste))

    # Sauvegarder dans le fichier de sortie
    with open(fichier_sortie, 'w', encoding='utf-8') as f:
        json.dump(nouvelle_liste, f, ensure_ascii=False, indent=2)

    print(f"Traitement terminé !")
    print(f"Nombre d'éléments avant : {len(data)}")
    print(f"Nombre d'éléments après : {len(nouvelle_liste)}")

    return nouvelle_liste


# Exemple d'utilisation
if __name__ == "__main__":
    # Remplacer par vos noms de fichiers
    fichier_entree = "denominations_distinctes.json"
    fichier_sortie = "objets_culturels_traites_t1.json"

    try:
        resultat = separer_elements_avec_pointvirgule(fichier_entree, fichier_sortie)
        print("\nExemple des premiers éléments traités :")
        for i, elem in enumerate(resultat[:5]):
            print(f"  {i + 1}. {elem}")
    except FileNotFoundError:
        print(f"Erreur : Le fichier '{fichier_entree}' n'a pas été trouvé.")
    except json.JSONDecodeError:
        print(f"Erreur : Le fichier '{fichier_entree}' n'est pas un JSON valide.")
    except Exception as e:
        print(f"Erreur inattendue : {e}")