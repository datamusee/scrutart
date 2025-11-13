import json
import requests
import time
from typing import Dict, List, Optional


class WikidataMatcher:
    def __init__(self):
        self.endpoint = "https://query.wikidata.org/sparql"
        self.headers = {
            'User-Agent': 'MaterialTechniqueBot/1.0',
            'Accept': 'application/json'
        }

    def query_wikidata(self, sparql_query: str) -> Optional[Dict]:
        """Exécute une requête SPARQL sur Wikidata"""
        try:
            response = requests.get(
                self.endpoint,
                params={'query': sparql_query, 'format': 'json'},
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            time.sleep(0.25)
            return response.json()
        except Exception as e:
            print(f"  ⚠ Erreur requête: {e}")
            return None

    def recherche_exacte(self, terme: str) -> List[Dict]:
        """Recherche exacte du label, retourne TOUS les résultats"""
        print(f"  → Recherche exacte du label '{terme}'...")

        query = f"""
        SELECT DISTINCT ?item ?itemLabel ?itemDescription ?class ?classLabel WHERE {{
          ?item rdfs:label "{terme}"@fr .
          OPTIONAL {{ ?item wdt:P31 ?class . }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en". }}
        }}
        LIMIT 50
        """

        result = self.query_wikidata(query)
        if not result or 'results' not in result:
            return []

        items = []
        for binding in result.get('results', {}).get('bindings', []):
            item = {
                'qid': binding['item']['value'].split('/')[-1],
                'label': binding.get('itemLabel', {}).get('value', ''),
                'description': binding.get('itemDescription', {}).get('value', ''),
                'class': binding.get('class', {}).get('value', '').split('/')[-1] if 'class' in binding else None,
                'class_label': binding.get('classLabel', {}).get('value', '') if 'classLabel' in binding else '',
                'url': binding['item']['value']
            }
            items.append(item)

        print(f"  → {len(items)} résultat(s) trouvé(s)")
        return items

    def est_technique(self, qid: str) -> bool:
        """Vérifie si un QID est une technique artistique"""
        query = f"""
        ASK {{
          {{
            wd:{qid} wdt:P31/wdt:P279* wd:Q11028 .  # technique de peinture
          }} UNION {{
            wd:{qid} wdt:P31/wdt:P279* wd:Q11633 .  # technique de dessin
          }} UNION {{
            wd:{qid} wdt:P31/wdt:P279* wd:Q2743826 .  # technique artistique
          }} UNION {{
            wd:{qid} wdt:P31/wdt:P279* wd:Q21029893 .  # technique d'impression
          }} UNION {{
            wd:{qid} wdt:P31/wdt:P279* wd:Q17514 .  # instrument de dessin
          }} UNION {{
            wd:{qid} wdt:P31/wdt:P279* wd:Q239707 .  # instrument d'écriture
          }} UNION {{
            wd:{qid} wdt:P31/wdt:P279* wd:Q11629 .  # peinture
          }} UNION {{
            wd:{qid} wdt:P366 wd:Q11633 .  # usage: dessin
          }} UNION {{
            wd:{qid} wdt:P366 wd:Q11629 .  # usage: peinture
          }} UNION {{
            wd:{qid} wdt:P366 wd:Q180490 .  # usage: calligraphie
          }} UNION {{
            wd:{qid} wdt:P366 wd:Q11036 .  # usage: beaux-arts
          }} UNION {{
            wd:{qid} wdt:P366 wd:Q174705 .  # usage: gravure
          }}
        }}
        """

        result = self.query_wikidata(query)
        if result and 'boolean' in result:
            return result['boolean']
        return False

    def est_materiau(self, qid: str) -> bool:
        """Vérifie si un QID est un matériau"""
        query = f"""
        ASK {{
          {{
            wd:{qid} wdt:P31/wdt:P279* wd:Q214609 .  # matériau
          }} UNION {{
            wd:{qid} wdt:P31/wdt:P279* wd:Q167270 .  # matière première
          }} UNION {{
            wd:{qid} wdt:P31/wdt:P279* wd:Q161179 .  # pigment
          }} UNION {{
            wd:{qid} wdt:P31/wdt:P279* wd:Q56428308 .  # médium artistique
          }}
        }}
        """

        result = self.query_wikidata(query)
        if result and 'boolean' in result:
            return result['boolean']
        return False

    def chercher_materiau(self, terme: str) -> List[Dict]:
        """Cherche un matériau: recherche exacte puis filtre"""

        # Étape 1: Recherche exacte
        resultats = self.recherche_exacte(terme)

        if not resultats:
            # Étape 2: Si aucun résultat, essayer recherche partielle
            print(f"  → Recherche partielle...")
            query = f"""
            SELECT DISTINCT ?item ?itemLabel ?itemDescription WHERE {{
              ?item rdfs:label ?label .
              FILTER(CONTAINS(LCASE(?label), LCASE("{terme}")))
              FILTER(LANG(?label) = "fr")
              {{
                ?item wdt:P31/wdt:P279* wd:Q214609 .
              }} UNION {{
                ?item wdt:P31/wdt:P279* wd:Q167270 .
              }} UNION {{
                ?item wdt:P31/wdt:P279* wd:Q161179 .
              }}
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en". }}
            }}
            LIMIT 10
            """
            result = self.query_wikidata(query)
            return self._parse_simple_results(result)

        # Étape 3: Filtrer les résultats pour garder les matériaux
        print(f"  → Filtrage des matériaux...")
        materiaux = []
        for item in resultats:
            if self.est_materiau(item['qid']):
                print(f"    ✓ {item['qid']} est un matériau")
                materiaux.append(item)
            else:
                print(f"    ✗ {item['qid']} n'est pas un matériau")

        if materiaux:
            return materiaux

        # Si aucun résultat filtré, retourner tous les résultats
        print(f"  → Aucun matériau trouvé, retour de tous les résultats")
        return resultats

    def chercher_technique(self, terme: str) -> List[Dict]:
        """Cherche une technique: recherche exacte puis filtre"""

        # Étape 1: Recherche exacte
        resultats = self.recherche_exacte(terme)

        if not resultats:
            # Étape 2: Si aucun résultat, essayer recherche partielle
            print(f"  → Recherche partielle...")
            query = f"""
            SELECT DISTINCT ?item ?itemLabel ?itemDescription WHERE {{
              ?item rdfs:label ?label .
              FILTER(CONTAINS(LCASE(?label), LCASE("{terme}")))
              FILTER(LANG(?label) = "fr")
              {{
                ?item wdt:P31/wdt:P279* wd:Q11028 .
              }} UNION {{
                ?item wdt:P31/wdt:P279* wd:Q11633 .
              }} UNION {{
                ?item wdt:P31/wdt:P279* wd:Q2743826 .
              }} UNION {{
                ?item wdt:P31/wdt:P279* wd:Q17514 .
              }}
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en". }}
            }}
            LIMIT 10
            """
            result = self.query_wikidata(query)
            return self._parse_simple_results(result)

        # Étape 3: Filtrer les résultats pour garder les techniques
        print(f"  → Filtrage des techniques...")
        techniques = []
        for item in resultats:
            if self.est_technique(item['qid']):
                print(f"    ✓ {item['qid']} est une technique")
                techniques.append(item)
            else:
                print(f"    ✗ {item['qid']} n'est pas une technique")

        if techniques:
            return techniques

        # Si aucun résultat filtré, retourner tous les résultats
        print(f"  → Aucune technique trouvée, retour de tous les résultats")
        return resultats

    def _parse_simple_results(self, result: Optional[Dict]) -> List[Dict]:
        """Parse les résultats simples sans classes"""
        if not result or 'results' not in result:
            return []

        items = []
        for binding in result.get('results', {}).get('bindings', []):
            item = {
                'qid': binding['item']['value'].split('/')[-1],
                'label': binding.get('itemLabel', {}).get('value', ''),
                'description': binding.get('itemDescription', {}).get('value', ''),
                'url': binding['item']['value']
            }
            items.append(item)
        return items

    def sauvegarder_resultat(self, resultat: Dict, chemin: str):
        """Sauvegarde le résultat dans un fichier"""
        with open(chemin, 'w', encoding='utf-8') as f:
            json.dump(resultat, f, ensure_ascii=False, indent=2)
        print(f"  💾 Sauvegarde effectuée")

    def charger_resultat_existant(self, chemin: str) -> Optional[Dict]:
        """Charge un résultat existant s'il existe"""
        try:
            with open(chemin, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return None

    def traiter_fichier(self, chemin_entree: str, chemin_sortie: str, frequence_sauvegarde: int = 5):
        """Traite le fichier JSON et ajoute les entités Wikidata

        Args:
            chemin_entree: Fichier JSON d'entrée
            chemin_sortie: Fichier JSON de sortie
            frequence_sauvegarde: Nombre d'éléments traités entre chaque sauvegarde
        """

        with open(chemin_entree, 'r', encoding='utf-8') as f:
            donnees = json.load(f)

        # Tenter de charger un résultat existant
        resultat = self.charger_resultat_existant(chemin_sortie)

        if resultat:
            print("\n" + "=" * 60)
            print("REPRISE D'UN TRAITEMENT EXISTANT")
            print("=" * 60)
            tech_deja = len(resultat.get('techniques', {}))
            mat_deja = len(resultat.get('materiaux', {}))
            print(f"✓ {tech_deja} techniques déjà traitées")
            print(f"✓ {mat_deja} matériaux déjà traités")
        else:
            resultat = {
                "techniques": {},
                "materiaux": {},
                "groupes_techniques": {},
                "groupes_materiaux": {}
            }
            print("\n" + "=" * 60)
            print("NOUVEAU TRAITEMENT")
            print("=" * 60)

        # Traiter les techniques individuelles
        print("\n" + "=" * 60)
        print("RECHERCHE DES TECHNIQUES")
        print("=" * 60)
        if 'techniques' in donnees:
            compteur = 0
            for i, (technique, count) in enumerate(donnees['techniques'].items(), 1):
                # Vérifier si déjà traité
                if technique in resultat['techniques']:
                    print(f"\n[{i}/{len(donnees['techniques'])}] {technique} (déjà traité)")
                    continue

                print(f"\n[{i}/{len(donnees['techniques'])}] {technique}")
                matches = self.chercher_technique(technique)
                resultat['techniques'][technique] = {
                    'occurrences': count,
                    'wikidata': matches
                }
                if matches:
                    print(f"  ✓ RÉSULTAT: {matches[0]['qid']} - {matches[0]['label']}")
                    if matches[0].get('description'):
                        print(f"             {matches[0]['description']}")
                else:
                    print(f"  ✗ AUCUN RÉSULTAT")

                # Sauvegarde périodique
                compteur += 1
                if compteur % frequence_sauvegarde == 0:
                    self.sauvegarder_resultat(resultat, chemin_sortie)

        # Traiter les matériaux individuels
        print("\n" + "=" * 60)
        print("RECHERCHE DES MATÉRIAUX")
        print("=" * 60)
        if 'materiaux' in donnees:
            compteur = 0
            for i, (materiau, count) in enumerate(donnees['materiaux'].items(), 1):
                # Vérifier si déjà traité
                if materiau in resultat['materiaux']:
                    print(f"\n[{i}/{len(donnees['materiaux'])}] {materiau} (déjà traité)")
                    continue

                print(f"\n[{i}/{len(donnees['materiaux'])}] {materiau}")
                matches = self.chercher_materiau(materiau)
                resultat['materiaux'][materiau] = {
                    'occurrences': count,
                    'wikidata': matches
                }
                if matches:
                    print(f"  ✓ RÉSULTAT: {matches[0]['qid']} - {matches[0]['label']}")
                    if matches[0].get('description'):
                        print(f"             {matches[0]['description']}")
                else:
                    print(f"  ✗ AUCUN RÉSULTAT")

                # Sauvegarde périodique
                compteur += 1
                if compteur % frequence_sauvegarde == 0:
                    self.sauvegarder_resultat(resultat, chemin_sortie)

        # Traiter les groupes de techniques
        print("\n" + "=" * 60)
        print("RECHERCHE DES GROUPES DE TECHNIQUES")
        print("=" * 60)
        if 'groupes_techniques' in donnees:
            for groupe, items in donnees['groupes_techniques'].items():
                # Vérifier si déjà traité
                if groupe in resultat['groupes_techniques']:
                    print(f"\n[Groupe] {groupe} (déjà traité)")
                    continue

                print(f"\n[Groupe] {groupe}")
                matches = self.chercher_technique(groupe)
                resultat['groupes_techniques'][groupe] = {
                    'items': items,
                    'wikidata': matches
                }
                if matches:
                    print(f"  ✓ RÉSULTAT: {matches[0]['qid']} - {matches[0]['label']}")
                self.sauvegarder_resultat(resultat, chemin_sortie)

        # Traiter les groupes de matériaux
        print("\n" + "=" * 60)
        print("RECHERCHE DES GROUPES DE MATÉRIAUX")
        print("=" * 60)
        if 'groupes_materiaux' in donnees:
            for groupe, items in donnees['groupes_materiaux'].items():
                # Vérifier si déjà traité
                if groupe in resultat['groupes_materiaux']:
                    print(f"\n[Groupe] {groupe} (déjà traité)")
                    continue

                print(f"\n[Groupe] {groupe}")
                matches = self.chercher_materiau(groupe)
                resultat['groupes_materiaux'][groupe] = {
                    'items': items,
                    'wikidata': matches
                }
                if matches:
                    print(f"  ✓ RÉSULTAT: {matches[0]['qid']} - {matches[0]['label']}")
                self.sauvegarder_resultat(resultat, chemin_sortie)

        # Sauvegarder le résultat final
        self.sauvegarder_resultat(resultat, chemin_sortie)

        print("\n" + "=" * 60)
        print("RÉSULTAT")
        print("=" * 60)

        tech_trouvees = sum(1 for t in resultat['techniques'].values() if t['wikidata'])
        mat_trouves = sum(1 for m in resultat['materiaux'].values() if m['wikidata'])

        print(f"✓ Fichier sauvegardé: {chemin_sortie}")
        print(f"✓ Techniques trouvées: {tech_trouvees}/{len(resultat['techniques'])}")
        print(f"✓ Matériaux trouvés: {mat_trouves}/{len(resultat['materiaux'])}")


# Exemple d'utilisation
if __name__ == "__main__":
    matcher = WikidataMatcher()
    # frequence_sauvegarde=5 signifie qu'on sauvegarde tous les 5 éléments traités
    matcher.traiter_fichier('separation_techniques_materiaux.json', 'wikidata_techniques_materiaux.json', frequence_sauvegarde=50)