from SPARQLWrapper import SPARQLWrapper, JSON, POST
import os
import json
from typing import Dict, Any
import unidecode
from graphene import ObjectType, Field, String, Schema, List as GList, Mutation, Boolean as GrapheneBoolean
import graphene
from graphql import GraphQLError


class SchemaGenerator():
    def __init__(self, sparql_client, type_to_graph, cache_file: str):
        self.sparql_client = sparql_client
        self.cache_file = cache_file
        self.type_to_graph = type_to_graph

    def sanitize_name(self, name: str) -> str:
        # Nettoie un nom pour GraphQL#
        import re
        name = unidecode.unidecode(name)
        name = re.sub(r'[^a-zA-Z0-9_]', '', name)
        parts = name.split('_')
        if len(parts) > 1:
            result = parts[0].lower() + ''.join(p.capitalize() for p in parts[1:] if p)
        else:
            result = name
        if not result or not result[0].isalpha():
            result = 'field' + result
        return result or 'unknown'

    def load_graph_mapping_cache(self) -> Dict[str, Any]:
        """Charge le mapping depuis le cache"""
        cache_file = 'graph_mapping_cache.json'
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                return json.load(f)
        return {
            'type_to_graph': {},
            'graph_to_types': {},
            'violations': [],
            'manual_overrides': {}
        }

    def merge_graph_mappings(self, auto: Dict, manual: Dict) -> Dict:
        """Fusionne les mappings auto et manuels avec priorité au manuel"""
        merged_type_to_graph = auto.get('type_to_graph', {}).copy()
        merged_type_to_graph.update(manual.get('manual_overrides', {}))

        return {
            'type_to_graph': merged_type_to_graph,
            'graph_to_types': auto.get('graph_to_types', {}),
            'violations': auto.get('violations', []),
            'manual_overrides': manual.get('manual_overrides', {})
        }

    def get_graph_for_type_improved(self, type_name: str, type_uri: str) -> str:
        """
        Détermine le graphe nommé pour un type
        Ordre de priorité:
        1. Config statique TYPE_TO_GRAPH
        2. Manual overrides dans le cache
        3. Mapping automatique
        4. Graphe par défaut
        """
        # 1. Config statique
        if type_name in self.type_to_graph:
            return self.type_to_graph[type_name]

        # 2. Charger les mappings
        graph_mapping = self.load_graph_mapping_cache()
        merged = self.merge_graph_mappings(graph_mapping, graph_mapping)

        # 3. Mapping automatique ou manuel
        if type_uri in merged['type_to_graph']:
            return merged['type_to_graph'][type_uri]

        # 4. Fallback sur le schéma
        schema_cache = self.load_schema_cache()
        auto = schema_cache.get('auto_generated', {})
        manual = schema_cache.get('manual', {})
        merged_schema = self.merge_schema_definitions(auto, manual)

        if type_uri in merged_schema:
            graphs = merged_schema[type_uri].get('graphs', [])
            if graphs and graphs[0]:
                return graphs[0]

        # 5. Par défaut
        return 'http://example.org/graphs/default'

    def graphql_type_from_rdf_type(self, rdf_type: str):
        # Convertit un type RDF en type GraphQL#
        mapping = {
            'string': String,
            'int': graphene.Int,
            'float': graphene.Float,
            'datetime': graphene.DateTime,
            'date': String,
            'reference': String
        }
        return mapping.get(rdf_type, String)

    def detect_rdf_types(self) -> Dict[str, Any]:
        query = '''
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        
        SELECT DISTINCT ?type ?label WHERE {
            {
                ?instance rdf:type ?type .
                OPTIONAL { ?type rdfs:label ?label }
            } UNION {
                ?instance wdt:P31 ?type .
                OPTIONAL { ?type rdfs:label ?label }
            }
            FILTER(?type != rdf:Property && ?type != rdfs:Class)
        }
        LIMIT 100
        '''
        
        results = self.sparql_client.query(query)
        types_info = {}
        
        for result in results:
            type_uri = result['type']
            label = result.get('label', type_uri.split('/')[-1].split('#')[-1])
            
            if type_uri not in types_info:
                types_info[type_uri] = {
                    'uri': type_uri,
                    'label': label,
                    'graphs': [],
                    'properties': {}
                }
        
        # Détecter les propriétés pour chaque type
        for type_uri in types_info.keys():
            types_info[type_uri]['properties'] = self.detect_properties_for_type(type_uri)
        
        return types_info
    
    def detect_properties_for_type(self, type_uri: str) -> Dict[str, Any]:
        query = f'''
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT DISTINCT ?property ?propertyLabel ?valueType WHERE {{
            {{
                ?instance wdt:P31 <{type_uri}> .
                ?instance ?property ?value .
            }} UNION {{
                ?instance rdf:type <{type_uri}> .
                ?instance ?property ?value .
            }}
            
            OPTIONAL {{ ?property rdfs:label ?propertyLabel }}
            
            BIND(
                IF(isLiteral(?value),
                    IF(datatype(?value) = <http://www.w3.org/2001/XMLSchema#integer>, "int",
                    IF(datatype(?value) = <http://www.w3.org/2001/XMLSchema#float>, "float",
                    IF(datatype(?value) = <http://www.w3.org/2001/XMLSchema#dateTime>, "datetime",
                    "string"))),
                    "reference"
                ) AS ?valueType
            )
        }}
        # LIMIT 100
        '''
        
        results = self.sparql_client.query(query)
        properties = {}
        
        for result in results:
            prop_uri = result['property']
            prop_label = result.get('propertyLabel', prop_uri.split('/')[-1].split('#')[-1])
            value_type = result['valueType']
            
            if prop_uri not in properties:
                properties[prop_uri] = {
                    'uri': prop_uri,
                    'label': prop_label,
                    'type': value_type
                }
        
        return properties
    
    def generate_schema(self) -> Dict[str, Any]:
        """Génère le schéma GraphQL à partir des types RDF détectés"""

        print("Détection des types RDF...")
        types_info = self.detect_rdf_types()

        print(f"Types détectés: {len(types_info)}")

        # Détecter les propriétés pour chaque type
        for type_uri, type_info in types_info.items():
            print(f"Détection des propriétés pour {type_info['label']}...")
            type_info['properties'] = self.detect_properties_for_type(type_uri)

        schema = {
            'auto_generated': types_info,
            'manual': {}
        }

        return schema

    def save_schema(self, schema: Dict[str, Any]):
        with open(self.cache_file, 'w') as f:
            json.dump(schema, f, indent=2)
    
    def load_schema_cache(self) -> Dict[str, Any]:
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        return {'auto_generated': {}, 'manual': {}}
    
    # @staticmethod
    def merge_schema_definitions(self, auto: Dict, manual: Dict) -> Dict:
        merged = auto.copy()
        for uri, manual_def in manual.items():
            if uri in merged:
                merged[uri]['properties'].update(manual_def.get('properties', {}))
            else:
                merged[uri] = manual_def
        return merged

    def create_advanced_resolver_fixed(self, type_name: str, type_uri: str, single: bool = True):
        """
        Résolveur corrigé avec mapping cohérent des propriétés
        """
        def resolver(root, info, id=None, use_cache=False):
            """Résolveur avec support des sous-objets et mapping correct"""
            # ✅ Récupérer use_cache depuis le contexte si non fourni explicitement
            if use_cache is None:
                use_cache = info.context.get('use_cache', True) if hasattr(info, 'context') else True

            try:
                # Charger le schéma pour avoir le mapping URI -> nom GraphQL
                schema_cache = self.load_schema_cache()
                auto = schema_cache.get('auto_generated', {})
                manual = schema_cache.get('manual', {})
                merged = self.merge_schema_definitions(auto, manual)

                # Créer un mapping bidirectionnel prop_uri <-> graphql_name
                prop_uri_to_name = {}
                prop_name_to_uri = {}

                if type_uri in merged:
                    for prop_uri, prop_info in merged[type_uri].get('properties', {}).items():
                        graphql_name = self.sanitize_name(prop_info['label'])
                        prop_uri_to_name[prop_uri] = graphql_name
                        prop_name_to_uri[graphql_name] = prop_uri

                # Analyser les champs demandés
                selection_set = info.field_nodes[0].selection_set
                requested_fields = {}

                if selection_set:
                    for selection in selection_set.selections:
                        field_name = selection.name.value
                        if selection.selection_set:
                            subfields = [s.name.value for s in selection.selection_set.selections]
                            requested_fields[field_name] = subfields
                        else:
                            requested_fields[field_name] = None

                print(f"  → Résolveur {type_name}: champs demandés = {list(requested_fields.keys())}")
                print(f"  → Mapping disponible: {list(prop_uri_to_name.values())}")

                if single and id:
                    # REQUÊTE POUR UN OBJET SPÉCIFIQUE
                    query = f"""
                    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                    PREFIX wdt: <http://www.wikidata.org/prop/direct/>

                    SELECT ?property ?value WHERE {{
                        {{
                            <{id}> wdt:P31 <{type_uri}> .
                            <{id}> ?property ?value .
                        }} UNION {{
                            <{id}> rdf:type <{type_uri}> .
                            <{id}> ?property ?value .
                        }}
                    }}
                    """

                    print(f"🔍 Query {type_name}(id={id}) - Cache: {use_cache}")
                    results = self.sparql_client.query(query, use_cache=use_cache)
                    obj = {'id': id}

                    for result in results:
                        prop_uri = result['property']
                        value = result['value']

                        # UTILISER LE MAPPING
                        prop_name = prop_uri_to_name.get(prop_uri)

                        if not prop_name:
                            continue  # Ignorer les propriétés non dans le schéma

                        # Gérer les références
                        if isinstance(value, str) and value.startswith('http'):
                            if prop_name in requested_fields and requested_fields[prop_name]:
                                obj[prop_name] = self.resolve_subobject(value, requested_fields[prop_name])
                            else:
                                obj[prop_name] = value
                        else:
                            obj[prop_name] = value

                    print(f"  ✓ Objet single résolu: {obj}")
                    return obj

                else:
                    # REQUÊTE POUR TOUS LES OBJETS (LISTE)
                    # Étape 1: Récupérer tous les IDs
                    instances_query = f"""
                    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                    PREFIX wdt: <http://www.wikidata.org/prop/direct/>

                    SELECT DISTINCT ?instance WHERE {{
                        {{
                            ?instance wdt:P31 <{type_uri}> .
                        }} UNION {{
                            ?instance rdf:type <{type_uri}> .
                        }}
                    }}
                    #LIMIT 100
                    """

                    print(f"🔍 Query all{type_name}s - Cache: {use_cache}")
                    instances_results = self.sparql_client.query(instances_query, use_cache=use_cache)
                    print(f"  → {len(instances_results)} instances trouvées")

                    objects = []

                    # Si seulement 'id' est demandé, retourner directement
                    if requested_fields == {'id': None} or not requested_fields:
                        return [{'id': r['instance']} for r in instances_results]

                    # Étape 2: Pour chaque instance, récupérer les propriétés demandées
                    requested_uris = []
                    for field_name in requested_fields.keys():
                        if field_name != 'id':
                            prop_uri = prop_name_to_uri.get(field_name)
                            if prop_uri:
                                requested_uris.append(f"<{prop_uri}>")

                    if not requested_uris:
                        # Aucune propriété connue demandée
                        return [{'id': r['instance']} for r in instances_results]

                    # Étape 3: Requête optimisée pour TOUTES les instances
                    # Utiliser VALUES pour récupérer toutes les données en une seule requête
                    instances_values = ' '.join([f"<{r['instance']}>" for r in instances_results])

                    batch_query = f"""
                    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

                    SELECT ?instance ?property ?value WHERE {{
                        VALUES ?instance {{ {instances_values} }}
                        ?instance ?property ?value .
                        FILTER(?property IN ({', '.join(requested_uris)}))
                    }}
                    """

                    print(f"  → Requête batch pour propriétés: {requested_uris}")
                    batch_results = self.sparql_client.query(batch_query, use_cache=use_cache)
                    print(f"  → {len(batch_results)} triplets récupérés")

                    # Étape 4: Organiser les résultats par instance
                    instances_data = {}
                    for r in instances_results:
                        instances_data[r['instance']] = {'id': r['instance']}

                    for result in batch_results:
                        instance_id = result['instance']
                        prop_uri = result['property']
                        value = result['value']

                        # MAPPING URI -> nom GraphQL
                        prop_name = prop_uri_to_name.get(prop_uri)

                        if prop_name and prop_name in requested_fields:
                            if isinstance(value, str) and value.startswith('http'):
                                if requested_fields[prop_name]:
                                    instances_data[instance_id][prop_name] = self.resolve_subobject(
                                        value, requested_fields[prop_name]
                                    )
                                else:
                                    instances_data[instance_id][prop_name] = value
                            else:
                                instances_data[instance_id][prop_name] = value

                    objects = list(instances_data.values())
                    print(f"  ✓ {len(objects)} objets liste résolus")

                    return objects

            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                print(f"❌ Erreur dans le résolveur {type_name}: {error_detail}")
                raise GraphQLError(f"Resolver error for {type_name}: {str(e)}")

        return resolver

    def create_advanced_mutation(self, type_name: str, type_uri: str):
        """Crée une mutation avancée avec support des relations"""

        class AdvancedMutation(Mutation):
            class Arguments:
                id = String(required=True, description="URI de l'entité")
                data = String(required=True, description="Données JSON de l'entité")
                replace = graphene.Boolean(default_value=False, description="Remplacer ou fusionner")

            success = Field(String)
            entity = Field(String)
            created = Field(graphene.Boolean)

            def mutate(root, info, id, data, replace=False):
                """Effectue la mutation avec gestion des relations"""
                try:
                    data_dict = json.loads(data)
                    graph = self.get_graph_for_type_improved(type_name, type_uri)

                    # Vérifier si l'entité existe déjà
                    check_query = f"""
                    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                    PREFIX wdt: <http://www.wikidata.org/prop/direct/>

                    ASK WHERE {{
                        {{
                            <{id}> wdt:P31 <{type_uri}> .
                        }} UNION {{
                            <{id}> rdf:type <{type_uri}> .
                        }}
                    }}
                    """

                    exists = self.sparql_client.ask(check_query)

                    # Si replace=True et que l'entité existe, la supprimer d'abord
                    if replace and exists:
                        delete_query = f"""
                        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

                        DELETE WHERE {{
                            GRAPH <{graph}> {{
                                <{id}> ?p ?o .
                            }}
                        }}
                        """
                        self.sparql_client.update(delete_query)

                    # Construire les triples à insérer
                    triples = []
                    triples.append(f"<{id}> rdf:type <{type_uri}> .")

                    # Charger le schéma pour déterminer les types de propriétés
                    schema_cache = self.load_schema_cache()
                    auto = schema_cache.get('auto_generated', {})
                    manual = schema_cache.get('manual', {})
                    merged_schema = self.merge_schema_definitions(auto, manual)

                    type_info = merged_schema.get(type_uri, {})
                    properties_info = type_info.get('properties', {})

                    for prop, value in data_dict.items():
                        # Trouver l'URI de la propriété
                        prop_uri = None
                        for p_uri, p_info in properties_info.items():
                            if self.sanitize_name(p_info['label']) == prop:
                                prop_uri = p_uri
                                break

                        if not prop_uri:
                            # Propriété inconnue, utiliser un namespace par défaut
                            prop_uri = f"http://example.org/prop/{prop}"

                        # Déterminer si c'est une référence ou un littéral
                        if isinstance(value, str) and value.startswith('http'):
                            # C'est une référence à un autre objet
                            triples.append(f"<{id}> <{prop_uri}> <{value}> .")
                        elif isinstance(value, bool):
                            triples.append(
                                f'<{id}> <{prop_uri}> "{str(value).lower()}"^^<http://www.w3.org/2001/XMLSchema#boolean> .')
                        elif isinstance(value, int):
                            triples.append(
                                f'<{id}> <{prop_uri}> "{value}"^^<http://www.w3.org/2001/XMLSchema#integer> .')
                        elif isinstance(value, float):
                            triples.append(
                                f'<{id}> <{prop_uri}> "{value}"^^<http://www.w3.org/2001/XMLSchema#double> .')
                        else:
                            # Littéral string
                            escaped_value = str(value).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                            triples.append(f'<{id}> <{prop_uri}> "{escaped_value}" .')

                    # Insérer les données
                    insert_query = f"""
                    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

                    INSERT DATA {{
                        GRAPH <{graph}> {{
                            {' '.join(triples)}
                        }}
                    }}
                    """

                    self.sparql_client.update(insert_query)

                    return AdvancedMutation(
                        success="Entity created/updated successfully",
                        entity=id,
                        created=not exists
                    )
                except Exception as e:
                    raise GraphQLError(f"Mutation failed: {str(e)}")

        return AdvancedMutation

    def create_delete_mutation(self, type_name: str, type_uri: str):
        """Crée une mutation de suppression pour un type"""

        class DeleteMutation(Mutation):
            class Arguments:
                id = String(required=True, description="URI de l'entité à supprimer")

            success = Field(String)
            deleted_id = Field(String)

            def mutate(root, info, id):
                """Supprime une entité du graphe"""
                try:
                    graph = self.get_graph_for_type_improved(type_name, type_uri)

                    # Supprimer tous les triples où l'entité est sujet
                    delete_query = f"""
                    DELETE WHERE {{
                        GRAPH <{graph}> {{
                            <{id}> ?p ?o .
                        }}
                    }}
                    """

                    self.sparql_client.update(delete_query)

                    return DeleteMutation(
                        success="Entity deleted successfully",
                        deleted_id=id
                    )
                except Exception as e:
                    raise GraphQLError(f"Delete failed: {str(e)}")

        return DeleteMutation

    def build_graphql_schema(self, schema_generator):
        """Construit le schéma GraphQL complet avec Query et Mutation"""

        # Charger le schéma depuis le cache
        schema_cache = self.load_schema_cache()
        auto = schema_cache.get('auto_generated', {})
        manual = schema_cache.get('manual', {})
        merged_schema = self.merge_schema_definitions(auto, manual)

        if not merged_schema:
            print("⚠️  Aucun type détecté dans le schéma. Création d'un schéma minimal.")

            # Créer un schéma minimal si aucun type n'est détecté
            class MinimalQuery(ObjectType):
                hello = String()

                def resolve_hello(root, info):
                    return "Le schéma est vide. Utilisez /schema/refresh pour détecter les types RDF."

            return Schema(query=MinimalQuery)

        # Construire les types GraphQL
        graphql_types = {}

        for type_uri, type_info in merged_schema.items():
            type_name = self.sanitize_name(type_info['label'])

            # Préparer les champs pour ce type
            fields = {
                'id': Field(String, description="URI de l'entité"),
            }

            for prop_uri, prop_info in type_info.get('properties', {}).items():
                prop_name = self.sanitize_name(prop_info['label'])
                prop_type = self.graphql_type_from_rdf_type(prop_info['type'])
                fields[prop_name] = Field(prop_type, description=prop_uri)

            # Créer le type dynamiquement
            graphql_type = type(type_name, (ObjectType,), fields)
            graphql_types[type_name] = graphql_type

        # Construire la classe Query dynamiquement
        query_fields = {}
        mutation_fields = {}

        for type_uri, type_info in merged_schema.items():
            type_name = self.sanitize_name(type_info['label'])

            if type_name not in graphql_types:
                continue

            graphql_type = graphql_types[type_name]

            # Ajouter les champs de requête
            # 1. Requête pour un seul objet par ID
            single_field_name = f'get{type_name}'
            query_fields[single_field_name] = Field(
                graphql_type,
                id=String(required=True),
                use_cache=graphene.Boolean(default_value=False),
                resolver=self.create_advanced_resolver_fixed(type_name, type_uri, single=True)
            )

            # 2. Requête pour tous les objets du type
            list_field_name = f'all{type_name}s'
            query_fields[list_field_name] = Field(
                GList(graphql_type),
                use_cache=graphene.Boolean(default_value=False),
                resolver=self.create_advanced_resolver_fixed(type_name, type_uri, single=False)
            )

            # Ajouter les mutations
            create_mutation = self.create_advanced_mutation(type_name, type_uri)
            mutation_fields[f'create{type_name}'] = create_mutation.Field()

            delete_mutation = self.create_delete_mutation(type_name, type_uri)
            mutation_fields[f'delete{type_name}'] = delete_mutation.Field()

        # Si aucune query n'a été créée, ajouter une query par défaut
        if not query_fields:
            query_fields['hello'] = Field(
                String,
                resolver=lambda root, info: "Aucun type RDF détecté. Utilisez /schema/refresh"
            )

        # Créer les classes Query et Mutation dynamiquement
        Query = type('Query', (ObjectType,), query_fields)

        if mutation_fields:
            Mutations = type('Mutations', (ObjectType,), mutation_fields)
            schema = Schema(query=Query, mutation=Mutations)
        else:
            schema = Schema(query=Query)

        print(f"✓ Schéma GraphQL construit avec {len(query_fields)} queries et {len(mutation_fields)} mutations")

        return schema

    def detect_type_to_graph_mapping(self) -> Dict[str, str]:
        """
        Détecte automatiquement le mapping type -> graphe nommé
        Hypothèse: chaque type n'est défini (sujet) que dans un seul graphe
        """

        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>

        SELECT DISTINCT ?type ?graph (COUNT(DISTINCT ?instance) as ?count) WHERE {
            GRAPH ?graph {
                {
                    ?instance rdf:type ?type .
                } UNION {
                    ?instance wdt:P31 ?type .
                }
            }
            FILTER(?type != rdf:Property && ?type != <http://www.w3.org/2000/01/rdf-schema#Class>)
        }
        GROUP BY ?type ?graph
        ORDER BY ?type ?graph
        """

        results = self.sparql_client.query(query)

        type_to_graphs = {}
        graph_to_types = {}
        violations = []

        for result in results:
            type_uri = result['type']
            graph_uri = result['graph']
            count = int(result['count'])

            if type_uri not in type_to_graphs:
                type_to_graphs[type_uri] = []

            type_to_graphs[type_uri].append({
                'graph': graph_uri,
                'instance_count': count
            })

            if graph_uri not in graph_to_types:
                graph_to_types[graph_uri] = []
            graph_to_types[graph_uri].append(type_uri)

        # Détecter les violations (type dans plusieurs graphes)
        final_mapping = {}
        for type_uri, graphs_info in type_to_graphs.items():
            if len(graphs_info) > 1:
                # Violation: le type est dans plusieurs graphes
                violations.append({
                    'type': type_uri,
                    'graphs': [g['graph'] for g in graphs_info],
                    'counts': {g['graph']: g['instance_count'] for g in graphs_info}
                })
                # Prendre le graphe avec le plus d'instances
                main_graph = max(graphs_info, key=lambda x: x['instance_count'])
                final_mapping[type_uri] = main_graph['graph']
            else:
                final_mapping[type_uri] = graphs_info[0]['graph']

        return {
            'type_to_graph': final_mapping,
            'graph_to_types': graph_to_types,
            'violations': violations
        }

    def create_resolver(self, type_name: str, type_uri: str, sparql_client, single: bool):
        # Crée un résolveur pour un type#
        from graphql import GraphQLError

        def resolver(root, info, id=None, use_cache=False):
            try:
                if single and id:
                    query = f'''
                    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    
                    SELECT ?property ?value WHERE {{
                        {{
                            <{id}> wdt:P31 <{type_uri}> .
                            <{id}> ?property ?value .
                        }} UNION {{
                            <{id}> rdf:type <{type_uri}> .
                            <{id}> ?property ?value .
                        }}
                    }}
                    # LIMIT 100
                    '''

                    results = sparql_client.query(query, use_cache=use_cache)
                    obj = {'id': id}
                    for r in results:
                        prop = r['property'].split('/')[-1].split('#')[-1]
                        obj[prop] = r['value']
                    return obj
                else:
                    query = f'''
                    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
                    PREFIX wdt: <http://www.wikidata.org/prop/direct/>
    
                    SELECT DISTINCT ?instance WHERE {{
                        {{
                            ?instance wdt:P31 <{type_uri}> .
                        }} UNION {{
                            ?instance rdf:type <{type_uri}> .
                        }}
                    }}
                    # LIMIT 100
                    '''

                    results = sparql_client.query(query, use_cache=use_cache)
                    return [{'id': r['instance']} for r in results]

            except Exception as e:
                print(f"Resolver error for {type_name}: {e}")
                raise GraphQLError(f"Resolver error: {str(e)}")

        return resolver

