import json
import re


def extraire_chaines(sujet_represente):
    """
    Extrait les chaînes séparées par des virgules,
    en ignorant les virgules entre parenthèses.
    """
    if not sujet_represente:
        return []

    # Pattern pour capturer les éléments en tenant compte des parenthèses
    # On utilise une expression régulière qui gère les parenthèses imbriquées
    chaines = []
    niveau_parentheses = 0
    element_actuel = ""

    for char in sujet_represente:
        if char == '(':
            niveau_parentheses += 1
            element_actuel += char
        elif char == ')':
            niveau_parentheses -= 1
            element_actuel += char
        elif char == ',' and niveau_parentheses == 0:
            # C'est un séparateur valide
            if element_actuel.strip():
                chaines.append(element_actuel.strip())
            element_actuel = ""
        else:
            element_actuel += char

    # Ajouter le dernier élément
    if element_actuel.strip():
        chaines.append(element_actuel.strip())

    return chaines


def traiter_fichier_json(fichier_entree, fichier_sortie_principal, fichier_sortie_denominations):
    """
    Traite le fichier JSON d'entrée et génère deux fichiers de sortie.
    """
    # Lire le fichier JSON d'entrée
    with open(fichier_entree, 'r', encoding='utf-8') as f:
        donnees = json.load(f)

    dictionnaire_resultat = {}
    denominations_distinctes = set()

    # Traiter chaque élément de la liste
    for element in donnees:
        sujet_represente = element.get('sujet_represente', '')
        denomination = element.get('denomination', '')

        # Ajouter la dénomination au set des valeurs distinctes
        if denomination:
            denominations_distinctes.add(denomination)

        # Extraire les chaînes du sujet_represente
        chaines = extraire_chaines(sujet_represente)

        # Créer ou compléter les entrées du dictionnaire
        for chaine in chaines:
            if chaine not in dictionnaire_resultat:
                dictionnaire_resultat[chaine] = {
                    "source": [],
                    "type_creation": []
                }

            # Ajouter la source (valeur complète de sujet_represente)
            if sujet_represente not in dictionnaire_resultat[chaine]["source"]:
                dictionnaire_resultat[chaine]["source"].append(sujet_represente)

            # Ajouter le type_creation (denomination)
            if denomination and denomination not in dictionnaire_resultat[chaine]["type_creation"]:
                dictionnaire_resultat[chaine]["type_creation"].append(denomination)

    # Sauvegarder le dictionnaire principal avec UTF-8 lisible
    with open(fichier_sortie_principal, 'w', encoding='utf-8') as f:
        json.dump(dictionnaire_resultat, f, ensure_ascii=False, indent=2)

    # Sauvegarder les dénominations distinctes
    liste_denominations = sorted(list(denominations_distinctes))
    with open(fichier_sortie_denominations, 'w', encoding='utf-8') as f:
        json.dump(liste_denominations, f, ensure_ascii=False, indent=2)

    print(f"Traitement terminé !")
    print(f"- Dictionnaire principal sauvegardé dans : {fichier_sortie_principal}")
    print(f"- {len(dictionnaire_resultat)} clés créées")
    print(f"- Dénominations distinctes sauvegardées dans : {fichier_sortie_denominations}")
    print(f"- {len(denominations_distinctes)} dénominations distinctes trouvées")


# Exemple d'utilisation
if __name__ == "__main__":
    fichier_entree = "D:/wamp64/www/givingsense.eu/datamusee/data/joconde/base-joconde-extrait.json"
    fichier_sortie_principal = "resultat_principal.json"
    fichier_sortie_denominations = "denominations_distinctes.json"

    traiter_fichier_json(fichier_entree, fichier_sortie_principal, fichier_sortie_denominations)