#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Property Matcher - Match extracted properties with Wikidata entities
"""

from typing import Dict, List, Optional, Tuple
import requests
import time
import urllib3

# Désactiver les warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PropertyMatcher:
    """Classe pour matcher les propriétés extraites avec des entités Wikidata"""
    
    SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
    
    # Délai entre les requêtes (en secondes)
    REQUEST_DELAY = 1.5
    
    # Nombre maximum de tentatives
    MAX_RETRIES = 3
    
    # Timeout pour les requêtes
    REQUEST_TIMEOUT = 15
    
    # Mapping des propriétés vers leurs IDs Wikidata
    PROPERTY_MAPPINGS = {
        # Peintures
        'creator': 'P170',
        'depicts': 'P180',
        'material': 'P186',
        'collection': 'P195',
        'location': 'P276',
        'movement': 'P135',
        'genre': 'P136',
        
        # Personnes
        'occupation': 'P106',
        'birth_place': 'P19',
        'death_place': 'P20',
        'nationality': 'P27',
    }
    
    # QIDs de types à exclure (liste noire)
    EXCLUDED_TYPES = {
        'Q11424',      # film
        'Q5398426',    # série télévisée
        'Q15416',      # émission de télévision
        'Q3305213',    # peinture
        'Q860861',     # sculpture
        'Q47461344',   # œuvre écrite
        'Q7725634',    # œuvre littéraire
        'Q482994',     # album musical
        'Q134556',     # single
        'Q43229',      # organisation
        'Q891723',     # entreprise publique
        'Q5',          # être humain (traité séparément)
        'Q16521',      # taxon
        'Q4167836',    # catégorie Wikimedia
        'Q4167410',    # page d'homonymie
    }
    
    # QIDs de types pertinents (liste blanche - bonus de scoring)
    RELEVANT_TYPES = {
        'Q223557': 0.10,   # objet physique
        'Q14745': 0.10,    # meuble
        'Q42177': 0.10,    # lit (meuble spécifique)
        'Q729': 0.08,      # animal
        'Q16686448': 0.08, # mammifère
        'Q618123': 0.07,   # lieu géographique
        'Q515': 0.07,      # ville
        'Q8502': 0.07,     # montagne
        'Q4022': 0.07,     # rivière
        'Q1792379': 0.09,  # genre artistique
        'Q742333': 0.09,   # peinture d'histoire (genre)
        'Q134307': 0.09,   # portrait (genre)
        'Q1358372': 0.09,  # scène de genre
        'Q151885': 0.05,   # concept
        'Q61788060': 0.06, # activité humaine
        'Q4936952': 0.06,  # partie anatomique
        'Q48422': 0.08,    # cadavre
        'Q3031': 0.08,     # arbre
        'Q12870': 0.08,    # fleur
    }
    
    def __init__(self, reference_file: str = 'data/keyword_reference.json'):
        """
        Initialiser le property matcher
        
        Args:
            reference_file: Chemin vers le fichier JSON de référence manuelle
        """
        self.last_request_time = 0
        self.type_cache = {}  # Cache pour les types d'entités
        self.reference_file = reference_file
        self.keyword_reference = self._load_keyword_reference()
    
    def _load_keyword_reference(self) -> Dict[str, List[Dict]]:
        """
        Charger le fichier de référence manuelle des mots-clés
        Crée le fichier avec un exemple s'il n'existe pas
        
        Returns:
            Dictionnaire {mot-clé: [entités candidates]}
        """
        import os
        import json
        
        # Créer le répertoire data si nécessaire
        os.makedirs(os.path.dirname(self.reference_file), exist_ok=True)
        
        # Si le fichier n'existe pas, créer un exemple
        if not os.path.exists(self.reference_file):
            print(f"Création du fichier de référence: {self.reference_file}")
            example_reference = {
                "scène historique": [
                    {
                        "qid": "Q742333",
                        "label_fr": "peinture d'histoire",
                        "label_en": "history painting",
                        "description": "genre de peinture historique",
                        "confidence": 0.95
                    }
                ],
                "cadavre": [
                    {
                        "qid": "Q48422",
                        "label_fr": "cadavre",
                        "label_en": "corpse",
                        "description": "corps d'un être vivant après sa mort",
                        "confidence": 0.98
                    }
                ],
                "lit": [
                    {
                        "qid": "Q42177",
                        "label_fr": "lit",
                        "label_en": "bed",
                        "description": "meuble pour dormir",
                        "confidence": 0.95
                    }
                ]
            }
            
            with open(self.reference_file, 'w', encoding='utf-8') as f:
                json.dump(example_reference, f, indent=2, ensure_ascii=False)
            
            return example_reference
        
        # Charger le fichier existant
        try:
            with open(self.reference_file, 'r', encoding='utf-8') as f:
                reference = json.load(f)
            print(f"✅ Référence chargée: {len(reference)} mot(s)-clé(s) avec associations manuelles")
            return reference
        except Exception as e:
            print(f"⚠️  Erreur lors du chargement de {self.reference_file}: {e}")
            return {}
    
    def add_keyword_reference(self, keyword: str, qid: str, label_fr: str, 
                             label_en: str = '', description: str = '', 
                             confidence: float = 0.95):
        """
        Ajouter une référence manuelle pour un mot-clé
        
        Args:
            keyword: Mot-clé
            qid: QID Wikidata
            label_fr: Label français
            label_en: Label anglais (optionnel)
            description: Description (optionnel)
            confidence: Score de confiance (0-1)
        """
        import json
        
        if keyword not in self.keyword_reference:
            self.keyword_reference[keyword] = []
        
        # Vérifier si le QID existe déjà
        existing_qids = [e['qid'] for e in self.keyword_reference[keyword]]
        if qid not in existing_qids:
            self.keyword_reference[keyword].append({
                'qid': qid,
                'label_fr': label_fr,
                'label_en': label_en,
                'description': description,
                'confidence': confidence
            })
            
            # Sauvegarder dans le fichier
            with open(self.reference_file, 'w', encoding='utf-8') as f:
                json.dump(self.keyword_reference, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Référence ajoutée: '{keyword}' → {qid} ({label_fr})")
        else:
            print(f"ℹ️  Référence existe déjà: '{keyword}' → {qid}")
    
    def match_all_properties(self, extracted_data: Dict, entity_type: str) -> Dict[str, List[Dict]]:
        """
        Matcher toutes les propriétés pertinentes d'une entité extraite
        
        Args:
            extracted_data: Données extraites (title, creator, keywords, etc.)
            entity_type: Type d'entité (painting, artist, etc.)
            
        Returns:
            Dictionnaire {property_name: [matches]}
        """
        results = {}
        
        if entity_type == 'painting':
            results.update(self._match_painting_properties(extracted_data))
        elif entity_type == 'artist':
            results.update(self._match_artist_properties(extracted_data))
        
        return results
    
    def _match_painting_properties(self, data: Dict) -> Dict[str, List[Dict]]:
        """Matcher les propriétés d'une peinture"""
        results = {}
        
        # 1. Créateur (creator)
        creator = data.get('creator') or data.get('creator_name')
        if creator:
            print(f"  🔍 Recherche du créateur: {creator}")
            creator_birth = data.get('creator_birth', '')
            creator_death = data.get('creator_death', '')
            results['creator'] = self.search_person(creator, creator_birth, creator_death)
            print(f"     → {len(results['creator'])} correspondance(s) trouvée(s)")
        
        # 2. Personnes représentées (depicted_persons)
        depicted_persons = data.get('depicted_persons', [])
        if depicted_persons:
            print(f"  🔍 Recherche de {len(depicted_persons)} personne(s) représentée(s)")
            results['depicted_persons'] = {}
            for person in depicted_persons:
                print(f"     - {person}...")
                matches = self.search_person(person)
                if matches:
                    results['depicted_persons'][person] = matches
                    print(f"       → {len(matches)} correspondance(s)")
        
        # 3. Mots-clés / Concepts (keywords) - Limiter pour éviter trop de requêtes
        keywords = data.get('keywords', [])[:5]  # Limiter à 5 max
        if keywords:
            print(f"  🔍 Recherche de {len(keywords)} mot(s)-clé(s)")
            results['keywords'] = {}
            for keyword in keywords:
                print(f"     - {keyword}...")
                matches = self.search_concept(keyword)
                if matches:
                    results['keywords'][keyword] = matches
                    print(f"       → {len(matches)} correspondance(s)")
                else:
                    print(f"       → Aucune correspondance")
        
        # 4. Matériau (material)
        material = data.get('material')
        if material:
            print(f"  🔍 Recherche du matériau: {material}")
            results['material'] = self.search_material(material)
            print(f"     → {len(results.get('material', []))} correspondance(s)")
        
        # 5. Collection
        collection = data.get('collection')
        if collection:
            print(f"  🔍 Recherche de la collection: {collection}")
            results['collection'] = self.search_collection(collection)
            print(f"     → {len(results.get('collection', []))} correspondance(s)")
        
        # 6. Mouvement artistique
        movement = data.get('movement')
        if movement:
            print(f"  🔍 Recherche du mouvement: {movement}")
            results['movement'] = self.search_movement(movement)
            print(f"     → {len(results.get('movement', []))} correspondance(s)")
        
        return results
    
    def _match_artist_properties(self, data: Dict) -> Dict[str, List[Dict]]:
        """Matcher les propriétés d'un artiste"""
        results = {}
        
        # 1. Occupation
        occupation = data.get('occupation')
        if occupation:
            results['occupation'] = self.search_occupation(occupation)
        
        # 2. Mouvement artistique
        movements = data.get('movements', [])
        if movements:
            results['movements'] = {}
            for movement in movements:
                matches = self.search_movement(movement)
                if matches:
                    results['movements'][movement] = matches
        
        # 3. Nationalité
        nationality = data.get('nationality')
        if nationality:
            results['nationality'] = self.search_country(nationality)
        
        return results
    
    def search_person(self, name: str, birth_year: str = '', death_year: str = '') -> List[Dict]:
        """
        Rechercher une personne dans Wikidata
        
        Args:
            name: Nom de la personne
            birth_year: Année de naissance (optionnel)
            death_year: Année de mort (optionnel)
            
        Returns:
            Liste de correspondances possibles
        """
        name_escaped = name.replace('"', '\\"').strip()
        
        # Générer des variantes du nom pour maximiser les chances
        search_variants = self._generate_name_variants(name_escaped)
        
        all_matches = {}  # Dictionnaire pour éviter les doublons (par QID)
        
        # Essayer chaque variante
        for variant in search_variants:
            print(f"     Recherche variante: '{variant}'")
            
            query = f"""
            SELECT DISTINCT ?item ?itemLabel ?description ?birth ?death ?image WHERE {{
              SERVICE wikibase:mwapi {{
                bd:serviceParam wikibase:api "EntitySearch" .
                bd:serviceParam wikibase:endpoint "www.wikidata.org" .
                bd:serviceParam mwapi:search "{variant}" .
                bd:serviceParam mwapi:language "fr" .
                ?item wikibase:apiOutputItem mwapi:item .
              }}
              ?item wdt:P31 wd:Q5 .  # humain
              OPTIONAL {{ ?item schema:description ?description . FILTER(LANG(?description) = "fr") }}
              OPTIONAL {{ ?item wdt:P569 ?birth . }}
              OPTIONAL {{ ?item wdt:P570 ?death . }}
              OPTIONAL {{ ?item wdt:P18 ?image . }}
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en" . }}
            }}
            LIMIT 10
            """
            
            results = self._execute_sparql(query)
            
            # Ajouter les résultats (éviter doublons)
            for result in results:
                qid = self._extract_qid(result.get('item', ''))
                if qid and qid not in all_matches:
                    result_birth = result.get('birth', '')
                    result_death = result.get('death', '')
                    
                    # Calculer le score de confiance
                    confidence = 0.7  # Base pour résultat du moteur de recherche
                    
                    # Augmenter si les dates correspondent
                    birth_match = False
                    death_match = False
                    
                    if birth_year and result_birth:
                        result_birth_year = self._extract_year(result_birth)
                        if result_birth_year == birth_year:
                            confidence += 0.15
                            birth_match = True
                    
                    if death_year and result_death:
                        result_death_year = self._extract_year(result_death)
                        if result_death_year == death_year:
                            confidence += 0.15
                            death_match = True
                    
                    # Si les deux dates correspondent, haute confiance
                    if birth_match and death_match:
                        confidence = 0.95
                    
                    all_matches[qid] = {
                        'id': qid,
                        'label': result.get('itemLabel', ''),
                        'description': result.get('description', ''),
                        'birth': self._extract_year(result_birth),
                        'death': self._extract_year(result_death),
                        'image': result.get('image', ''),
                        'url': f"https://www.wikidata.org/wiki/{qid}",
                        'confidence': min(confidence, 1.0),
                        'property': 'P170',  # créateur
                        'property_label': 'créateur'
                    }
            
            # Si on a déjà de bons résultats avec dates, pas besoin de toutes les variantes
            if len(all_matches) >= 3:
                high_confidence = [m for m in all_matches.values() if m['confidence'] >= 0.9]
                if high_confidence:
                    break
        
        matches = list(all_matches.values())
        
        # Filtrer par dates si fournies (après recherche pour garder flexibilité)
        if birth_year or death_year:
            filtered_matches = []
            for match in matches:
                # Garder si au moins une date correspond OU si pas de dates dans Wikidata
                if not match['birth'] and not match['death']:
                    # Pas de dates dans Wikidata, on garde avec confiance réduite
                    match['confidence'] *= 0.8
                    filtered_matches.append(match)
                elif (birth_year and match['birth'] == birth_year) or \
                     (death_year and match['death'] == death_year):
                    filtered_matches.append(match)
            
            # Si filtrage trop strict (aucun résultat), garder tous les résultats
            if filtered_matches:
                matches = filtered_matches
        
        # Trier par confiance
        matches.sort(key=lambda x: x['confidence'], reverse=True)
        
        return matches[:10]  # Limiter à 10 meilleurs résultats
    
    def _generate_name_variants(self, name: str) -> List[str]:
        """
        Générer des variantes du nom pour la recherche
        
        Args:
            name: Nom original
            
        Returns:
            Liste de variantes à essayer
        """
        variants = [name]  # Toujours inclure le nom original
        
        # Nettoyer et séparer les parties du nom
        parts = name.split()
        
        if len(parts) >= 2:
            # Cas "NOM Prénom" → essayer "Prénom NOM"
            if parts[0].isupper() and len(parts[0]) > 2:
                # Premier mot en majuscules = probablement le nom de famille
                # Ex: "TOUDOUZE Edouard" → "Edouard TOUDOUZE"
                reversed_name = ' '.join(parts[1:] + [parts[0]])
                variants.append(reversed_name)
                
                # Aussi essayer avec le nom de famille en casse normale
                # Ex: "TOUDOUZE Edouard" → "Edouard Toudouze"
                normalized_lastname = parts[0].capitalize()
                variants.append(' '.join(parts[1:] + [normalized_lastname]))
            
            # Cas "Prénom NOM" → essayer "NOM Prénom"
            elif parts[-1].isupper() and len(parts[-1]) > 2:
                # Dernier mot en majuscules = probablement le nom de famille
                # Ex: "Edouard TOUDOUZE" → "TOUDOUZE Edouard"
                reversed_name = ' '.join([parts[-1]] + parts[:-1])
                variants.append(reversed_name)
            
            # Cas normal "Prénom Nom" → essayer "Nom Prénom"
            else:
                # Ex: "Edouard Toudouze" → "Toudouze Edouard"
                reversed_name = ' '.join([parts[-1]] + parts[:-1])
                if reversed_name not in variants:
                    variants.append(reversed_name)
                
                # Aussi essayer avec le nom en majuscules
                # Ex: "Edouard Toudouze" → "TOUDOUZE Edouard"
                lastname_upper = parts[-1].upper()
                variant_upper = ' '.join([lastname_upper] + parts[:-1])
                if variant_upper not in variants:
                    variants.append(variant_upper)
        
        # Retirer les doublons tout en gardant l'ordre
        seen = set()
        unique_variants = []
        for v in variants:
            if v not in seen:
                seen.add(v)
                unique_variants.append(v)
        
        return unique_variants
    
    def search_concept(self, keyword: str) -> List[Dict]:
        """
        Rechercher un concept/mot-clé dans Wikidata
        Priorité: 1. Référence manuelle, 2. Recherche automatique
        
        Args:
            keyword: Mot-clé à rechercher
            
        Returns:
            Liste de correspondances possibles
        """
        keyword_lower = keyword.lower().strip()
        
        # 1. VÉRIFIER D'ABORD LA RÉFÉRENCE MANUELLE
        manual_matches = []
        if keyword_lower in self.keyword_reference:
            print(f"     ✓ Référence manuelle trouvée pour '{keyword}'")
            for ref in self.keyword_reference[keyword_lower]:
                manual_matches.append({
                    'id': ref['qid'],
                    'label': ref.get('label_fr', ref.get('label_en', '')),
                    'description': ref.get('description', ''),
                    'type': 'Référence manuelle',
                    'image': '',
                    'url': f"https://www.wikidata.org/wiki/{ref['qid']}",
                    'confidence': ref.get('confidence', 0.95),
                    'property': 'P180',
                    'property_label': 'représente (depicts)',
                    'source': 'manual'
                })
        
        # 2. RECHERCHE AUTOMATIQUE (pour compléter)
        auto_matches = []
        
        # Si on a déjà 3+ références manuelles avec haute confiance, ne pas chercher automatiquement
        high_confidence_manual = [m for m in manual_matches if m['confidence'] >= 0.9]
        if len(high_confidence_manual) >= 3:
            print(f"     → {len(manual_matches)} référence(s) manuelle(s) suffisante(s)")
            return manual_matches[:5]
        
        # Sinon, chercher automatiquement pour compléter
        keyword_escaped = keyword.replace('"', '\\"').strip()
        
        query = f"""
        SELECT DISTINCT ?item ?itemLabel ?description ?image ?instanceLabel WHERE {{
          SERVICE wikibase:mwapi {{
            bd:serviceParam wikibase:api "EntitySearch" .
            bd:serviceParam wikibase:endpoint "www.wikidata.org" .
            bd:serviceParam mwapi:search "{keyword_escaped}" .
            bd:serviceParam mwapi:language "fr" .
            ?item wikibase:apiOutputItem mwapi:item .
          }}
          
          # Filtre minimal
          FILTER NOT EXISTS {{ ?item wdt:P31 wd:Q5 . }}
          
          OPTIONAL {{ ?item wdt:P31 ?instance . }}
          OPTIONAL {{ ?item schema:description ?description . FILTER(LANG(?description) = "fr") }}
          OPTIONAL {{ ?item wdt:P18 ?image . }}
          
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en" . }}
        }}
        LIMIT 20
        """
        
        results = self._execute_sparql(query)
        
        # Filtrage post-requête
        manual_qids = {m['id'] for m in manual_matches}  # Éviter les doublons
        
        for result in results:
            qid = self._extract_qid(result.get('item', ''))
            if not qid or qid in manual_qids:
                continue
            
            label = result.get('itemLabel', '')
            instance_label = result.get('instanceLabel', '').lower()
            description = result.get('description', '').lower()
            
            # Filtrer les types non pertinents
            if self._is_irrelevant_type(qid, instance_label, description):
                continue
            
            # Calculer la confiance
            confidence = self._calculate_concept_confidence(keyword, label, instance_label, description)
            
            auto_matches.append({
                'id': qid,
                'label': label,
                'description': result.get('description', ''),
                'type': result.get('instanceLabel', ''),
                'image': result.get('image', ''),
                'url': f"https://www.wikidata.org/wiki/{qid}",
                'confidence': confidence,
                'property': 'P180',
                'property_label': 'représente (depicts)',
                'source': 'automatic'
            })
        
        # 3. COMBINER: Manuels en premier, puis automatiques
        combined_matches = manual_matches + auto_matches
        
        # Trier par confiance (manuels d'abord grâce à leur haute confiance)
        combined_matches.sort(key=lambda x: x['confidence'], reverse=True)
        
        print(f"     → {len(manual_matches)} manuel(s) + {len(auto_matches)} auto = {len(combined_matches[:5])} résultat(s)")
        
        return combined_matches[:5]
    
    def _is_irrelevant_type(self, qid: str, instance_label: str, description: str) -> bool:
        """
        Vérifier si un type est clairement non pertinent pour depicts
        Filtrage basé sur QIDs connus et mots-clés
        """
        # Vérifier directement le QID (le plus rapide)
        if qid in self.EXCLUDED_TYPES:
            return True
        
        # Vérifier les mots-clés dans le label du type
        irrelevant_keywords = [
            'film', 'movie', 'série', 'series', 'saison',
            'album', 'chanson', 'song', 'single',
            'livre', 'book', 'roman', 'novel', 'œuvre littéraire',
            'émission', 'broadcast', 'show', 'épisode',
            'peinture', 'painting', 'tableau',
            'organisation', 'organization', 'entreprise', 'company', 'société',
            'wikimedia', 'homonymie', 'disambiguation',
        ]
        
        instance_lower = instance_label.lower()
        description_lower = description.lower()
        
        for keyword in irrelevant_keywords:
            if keyword in instance_lower:
                # Exception: "lit" ne doit pas exclure "littéraire"
                # On vérifie le contexte
                if keyword == 'livre' and 'meuble' in description_lower:
                    continue
                return True
        
        # Vérifier aussi la description
        if any(word in description_lower for word in ['film de', 'série de', 'album de']):
            return True
        
        return False
    
    def _calculate_concept_confidence(self, keyword: str, label: str, 
                                     instance_label: str, description: str) -> float:
        """
        Calculer le score de confiance pour un concept
        Basé sur correspondance du label, type Wikidata, et contexte
        """
        keyword_lower = keyword.lower()
        label_lower = label.lower()
        
        # Base: correspondance du label
        if label_lower == keyword_lower:
            confidence = 0.9  # Correspondance exacte
        elif keyword_lower in label_lower:
            # Le mot-clé est dans le label
            # Ex: "lit" dans "lit d'enfant"
            if label_lower.startswith(keyword_lower + ' ') or label_lower.startswith(keyword_lower + '-'):
                confidence = 0.85  # Début du label
            else:
                confidence = 0.75  # Ailleurs dans le label
        elif label_lower in keyword_lower:
            confidence = 0.75
        else:
            confidence = 0.65  # Correspondance faible
        
        # Bonus selon le type (via instance_label ou description)
        instance_lower = instance_label.lower()
        description_lower = description.lower()
        
        # Vérifier si c'est un type pertinent connu
        # (On ne peut pas vérifier le QID direct ici, mais on utilise les mots-clés)
        bonus = 0.0
        
        type_keywords = {
            'objet': 0.05,
            'meuble': 0.08,
            'mobilier': 0.08,
            'animal': 0.05,
            'mammifère': 0.05,
            'lieu': 0.04,
            'ville': 0.04,
            'montagne': 0.04,
            'genre': 0.06,  # genre artistique
            'concept': 0.02,
            'activité': 0.03,
            'arbre': 0.04,
            'fleur': 0.04,
            'plante': 0.03,
        }
        
        for keyword, value in type_keywords.items():
            if keyword in instance_lower or keyword in description_lower:
                bonus = max(bonus, value)
        
        confidence += bonus
        
        # Pénalité pour types vagues
        if any(word in instance_lower for word in ['entité', 'élément', 'item', 'chose']):
            confidence -= 0.1
        
        # Pénalité si la description mentionne des types exclus
        if any(word in description_lower for word in ['film', 'série', 'album', 'livre']):
            confidence -= 0.15
        
        return min(max(confidence, 0.4), 1.0)  # Entre 0.4 et 1.0
    
    def search_material(self, material: str) -> List[Dict]:
        """Rechercher un matériau"""
        material_escaped = material.replace('"', '\\"').strip()
        
        # Utiliser le moteur de recherche puis filtrer sur le type
        query = f"""
        SELECT DISTINCT ?item ?itemLabel ?description WHERE {{
          SERVICE wikibase:mwapi {{
            bd:serviceParam wikibase:api "EntitySearch" .
            bd:serviceParam wikibase:endpoint "www.wikidata.org" .
            bd:serviceParam mwapi:search "{material_escaped}" .
            bd:serviceParam mwapi:language "fr" .
            ?item wikibase:apiOutputItem mwapi:item .
          }}
          {{ ?item wdt:P31 wd:Q214609 . }}  # matériau
          UNION
          {{ ?item wdt:P279 wd:Q214609 . }}  # sous-classe de matériau
          OPTIONAL {{ ?item schema:description ?description . FILTER(LANG(?description) = "fr") }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en" . }}
        }}
        LIMIT 5
        """
        
        results = self._execute_sparql(query)
        
        matches = []
        for result in results:
            qid = self._extract_qid(result.get('item', ''))
            if not qid:
                continue
            
            matches.append({
                'id': qid,
                'label': result.get('itemLabel', ''),
                'description': result.get('description', ''),
                'url': f"https://www.wikidata.org/wiki/{qid}",
                'confidence': 0.8,
                'property': 'P186',
                'property_label': 'matériau'
            })
        
        return matches
    
    def search_collection(self, collection: str) -> List[Dict]:
        """Rechercher une collection/musée"""
        collection_escaped = collection.replace('"', '\\"').strip()
        
        query = f"""
        SELECT DISTINCT ?item ?itemLabel ?description WHERE {{
          {{ ?item wdt:P31 wd:Q33506 . }}  # musée
          UNION
          {{ ?item wdt:P31 wd:Q2668072 . }}  # collection
          ?item rdfs:label ?label .
          FILTER(CONTAINS(LCASE(?label), LCASE("{collection_escaped}")))
          FILTER(LANG(?label) = "fr" || LANG(?label) = "en")
          OPTIONAL {{ ?item schema:description ?description . FILTER(LANG(?description) = "fr") }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en" . }}
        }}
        LIMIT 5
        """
        
        results = self._execute_sparql(query)
        
        matches = []
        for result in results:
            qid = self._extract_qid(result.get('item', ''))
            if not qid:
                continue
            
            matches.append({
                'id': qid,
                'label': result.get('itemLabel', ''),
                'description': result.get('description', ''),
                'url': f"https://www.wikidata.org/wiki/{qid}",
                'confidence': 0.8,
                'property': 'P195',
                'property_label': 'collection'
            })
        
        return matches
    
    def search_movement(self, movement: str) -> List[Dict]:
        """Rechercher un mouvement artistique"""
        movement_escaped = movement.replace('"', '\\"').strip()
        
        query = f"""
        SELECT DISTINCT ?item ?itemLabel ?description WHERE {{
          ?item wdt:P31 wd:Q968159 .  # mouvement artistique
          ?item rdfs:label ?label .
          FILTER(CONTAINS(LCASE(?label), LCASE("{movement_escaped}")))
          FILTER(LANG(?label) = "fr" || LANG(?label) = "en")
          OPTIONAL {{ ?item schema:description ?description . FILTER(LANG(?description) = "fr") }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en" . }}
        }}
        LIMIT 5
        """
        
        results = self._execute_sparql(query)
        
        matches = []
        for result in results:
            qid = self._extract_qid(result.get('item', ''))
            if not qid:
                continue
            
            matches.append({
                'id': qid,
                'label': result.get('itemLabel', ''),
                'description': result.get('description', ''),
                'url': f"https://www.wikidata.org/wiki/{qid}",
                'confidence': 0.8,
                'property': 'P135',
                'property_label': 'mouvement'
            })
        
        return matches
    
    def search_occupation(self, occupation: str) -> List[Dict]:
        """Rechercher une occupation"""
        occupation_escaped = occupation.replace('"', '\\"').strip()
        
        query = f"""
        SELECT DISTINCT ?item ?itemLabel ?description WHERE {{
          ?item wdt:P279* wd:Q12737077 .  # occupation
          ?item rdfs:label ?label .
          FILTER(CONTAINS(LCASE(?label), LCASE("{occupation_escaped}")))
          FILTER(LANG(?label) = "fr" || LANG(?label) = "en")
          OPTIONAL {{ ?item schema:description ?description . FILTER(LANG(?description) = "fr") }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en" . }}
        }}
        LIMIT 5
        """
        
        results = self._execute_sparql(query)
        
        matches = []
        for result in results:
            qid = self._extract_qid(result.get('item', ''))
            if not qid:
                continue
            
            matches.append({
                'id': qid,
                'label': result.get('itemLabel', ''),
                'description': result.get('description', ''),
                'url': f"https://www.wikidata.org/wiki/{qid}",
                'confidence': 0.8,
                'property': 'P106',
                'property_label': 'occupation'
            })
        
        return matches
    
    def search_country(self, country: str) -> List[Dict]:
        """Rechercher un pays"""
        country_escaped = country.replace('"', '\\"').strip()
        
        query = f"""
        SELECT DISTINCT ?item ?itemLabel ?description WHERE {{
          ?item wdt:P31 wd:Q6256 .  # pays
          ?item rdfs:label ?label .
          FILTER(CONTAINS(LCASE(?label), LCASE("{country_escaped}")))
          FILTER(LANG(?label) = "fr" || LANG(?label) = "en")
          OPTIONAL {{ ?item schema:description ?description . FILTER(LANG(?description) = "fr") }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en" . }}
        }}
        LIMIT 5
        """
        
        results = self._execute_sparql(query)
        
        matches = []
        for result in results:
            qid = self._extract_qid(result.get('item', ''))
            if not qid:
                continue
            
            matches.append({
                'id': qid,
                'label': result.get('itemLabel', ''),
                'description': result.get('description', ''),
                'url': f"https://www.wikidata.org/wiki/{qid}",
                'confidence': 0.9,
                'property': 'P27',
                'property_label': 'pays de citoyenneté'
            })
        
        return matches
    
    def _execute_sparql(self, query: str) -> List[Dict]:
        """
        Exécuter une requête SPARQL avec gestion des erreurs et retry
        
        Args:
            query: Requête SPARQL
            
        Returns:
            Liste de résultats
        """
        # Respecter le délai entre les requêtes
        elapsed = time.time() - self.last_request_time
        if elapsed < self.REQUEST_DELAY:
            time.sleep(self.REQUEST_DELAY - elapsed)
        
        for attempt in range(self.MAX_RETRIES):
            try:
                self.last_request_time = time.time()
                
                response = requests.get(
                    self.SPARQL_ENDPOINT,
                    params={'query': query, 'format': 'json'},
                    headers={
                        'User-Agent': 'WikidataEnricher/1.0 (Educational purpose)',
                        'Accept': 'application/json'
                    },
                    timeout=self.REQUEST_TIMEOUT,
                    verify=False
                )
                
                # Gérer les erreurs HTTP
                if response.status_code == 429:
                    # Too Many Requests - attendre plus longtemps
                    wait_time = (attempt + 1) * 5
                    print(f"Rate limit atteint, attente de {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                
                data = response.json()
                results = []
                
                for binding in data.get('results', {}).get('bindings', []):
                    result = {}
                    for key, value in binding.items():
                        result[key] = value.get('value', '')
                    results.append(result)
                
                return results
            
            except requests.exceptions.Timeout:
                print(f"Timeout (tentative {attempt + 1}/{self.MAX_RETRIES})")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                else:
                    print("Timeout définitif, résultats vides retournés")
                    return []
            
            except requests.exceptions.RequestException as e:
                print(f"Erreur requête (tentative {attempt + 1}/{self.MAX_RETRIES}): {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                else:
                    print("Erreur définitive, résultats vides retournés")
                    return []
            
            except Exception as e:
                print(f"Erreur inattendue: {e}")
                return []
        
        return []
    
    def _extract_qid(self, uri: str) -> str:
        """Extraire le QID d'une URI Wikidata"""
        import re
        match = re.search(r'Q\d+', uri)
        return match.group(0) if match else ''
    
    def _extract_year(self, date_str: str) -> str:
        """Extraire l'année d'une date"""
        import re
        if not date_str:
            return ''
        match = re.search(r'\b(1[4-9]\d{2}|20[0-2]\d)\b', str(date_str))
        return match.group(0) if match else ''
