import json
import re
from collections import defaultdict


def extraire_techniques_materiaux(texte):
    """Extrait les techniques (entre parenthèses) et matériaux (hors parenthèses)"""
    techniques = []
    materiaux = []

    # Extraire le contenu entre parenthèses
    parentheses = re.findall(r'\(([^)]+)\)', texte)
    for contenu in parentheses:
        # Séparer par virgule et nettoyer
        tech = [t.strip() for t in contenu.split(',')]
        techniques.extend(tech)

    # Enlever tout ce qui est entre parenthèses pour garder le reste
    texte_sans_parentheses = re.sub(r'\([^)]*\)', '', texte)

    # Extraire les matériaux (ce qui reste)
    if texte_sans_parentheses.strip():
        # Enlever les # au début et séparer par virgule
        texte_nettoye = texte_sans_parentheses.strip().lstrip('#')
        mat = [m.strip() for m in texte_nettoye.split(',') if m.strip()]
        materiaux.extend(mat)

    return techniques, materiaux


def grouper_materiaux(materiaux_dict):
    """Groupe les matériaux similaires"""
    groupes = defaultdict(list)

    # Définir les groupes connus
    groupe_papier = ['papier', 'canson', 'carton', 'papier vergé', 'papier vélin',
                     'papier de soie', 'papier kraft', 'papier japon']
    groupe_metal = ['acier', 'fer', 'bronze', 'cuivre', 'laiton', 'aluminium',
                    'métal', 'alliage', 'or', 'argent']
    groupe_textile = ['coton', 'lin', 'toile', 'soie', 'laine', 'velours',
                      'tissu', 'doublure', 'piqué']
    groupe_bois = ['bois', 'chêne', 'pin', 'acajou', 'contreplaqué']

    # Mapper chaque matériau à son groupe
    for materiau in materiaux_dict.keys():
        mat_lower = materiau.lower()

        # Vérifier si le matériau appartient à un groupe connu
        if any(mot in mat_lower for mot in groupe_papier):
            groupes['papier'].append(materiau)
        elif any(mot in mat_lower for mot in groupe_metal):
            groupes['métal'].append(materiau)
        elif any(mot in mat_lower for mot in groupe_textile):
            groupes['textile'].append(materiau)
        elif any(mot in mat_lower for mot in groupe_bois):
            groupes['bois'].append(materiau)
        else:
            groupes['autre'].append(materiau)

    return dict(groupes)


def grouper_techniques(techniques_dict):
    """Groupe les techniques similaires"""
    groupes = defaultdict(list)

    # Définir les groupes de techniques
    groupe_peinture = ['aquarelle', 'huile', 'acrylique', 'gouache', 'tempera']
    groupe_dessin = ['crayon', 'fusain', 'sanguine', 'pastel', 'crayon gras',
                     'graphite', 'pierre noire']
    groupe_encre = ['encre', 'encre de chine', 'sépia']
    groupe_gravure = ['gravure', 'eau-forte', 'lithographie', 'sérigraphie']

    for technique in techniques_dict.keys():
        tech_lower = technique.lower()

        if any(mot in tech_lower for mot in groupe_peinture):
            groupes['peinture'].append(technique)
        elif any(mot in tech_lower for mot in groupe_dessin):
            groupes['dessin'].append(technique)
        elif any(mot in tech_lower for mot in groupe_encre):
            groupes['encre'].append(technique)
        elif any(mot in tech_lower for mot in groupe_gravure):
            groupes['gravure'].append(technique)
        else:
            groupes['autre'].append(technique)

    return dict(groupes)


def traiter_fichier(chemin_entree, chemin_sortie):
    """Traite le fichier JSON d'entrée et crée le fichier de sortie"""

    # Lire le fichier d'entrée
    with open(chemin_entree, 'r', encoding='utf-8') as f:
        donnees = json.load(f)

    # Dictionnaires pour compter les occurrences
    techniques_count = defaultdict(int)
    materiaux_count = defaultdict(int)

    # Traiter chaque entrée
    for texte in donnees:
        if not texte or texte.strip() == '':
            continue

        texte = texte.lower()
        techniques, materiaux = extraire_techniques_materiaux(texte)

        for tech in techniques:
            if tech:
                techniques_count[tech] += 1

        for mat in materiaux:
            if mat:
                materiaux_count[mat] += 1

    # Créer les groupes
    groupes_materiaux = grouper_materiaux(materiaux_count)
    groupes_techniques = grouper_techniques(techniques_count)

    # Créer la structure finale
    resultat = {
        "techniques": dict(techniques_count),
        "materiaux": dict(materiaux_count),
        "groupes_techniques": groupes_techniques,
        "groupes_materiaux": groupes_materiaux
    }

    # Écrire le résultat
    with open(chemin_sortie, 'w', encoding='utf-8') as f:
        json.dump(resultat, f, ensure_ascii=False, indent=2)

    print(f"Traitement terminé. Résultat sauvegardé dans {chemin_sortie}")
    print(f"\nStatistiques:")
    print(f"- {len(techniques_count)} techniques uniques")
    print(f"- {len(materiaux_count)} matériaux uniques")
    print(f"- {len(groupes_techniques)} groupes de techniques")
    print(f"- {len(groupes_materiaux)} groupes de matériaux")


# Exemple d'utilisation
if __name__ == "__main__":
    # Remplacez ces chemins par vos fichiers
    traiter_fichier('techniques_distinctes.json', 'separation_techniques_materiaux.json')