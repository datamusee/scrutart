# ============================================================================
# utils/helpers.py - Fonctions utilitaires
# ============================================================================

"""
Fonctions utilitaires
"""

import unidecode


def sanitize_name(name: str) -> str:
    """Nettoie un nom pour qu'il soit valide en GraphQL (camelCase)"""
    name = unidecode.unidecode(name)
    parts = name.replace('-', '_').split('_')

    if len(parts) > 1:
        result = parts[0].lower() + ''.join(p.capitalize() for p in parts[1:] if p)
    else:
        result = parts[0]

    result = ''.join(c if c.isalnum() else '' for c in result)

    if result and not result[0].isalpha():
        result = 'field' + result

    return result or 'unknown'


def get_graph_for_type(type_name: str, type_uri: str, config, schema) -> str:
    """Détermine le graphe nommé pour un type"""
    # Config statique
    if type_name in config.TYPE_TO_GRAPH:
        return config.TYPE_TO_GRAPH[type_name]

    # Chercher dans le schéma
    if type_uri in schema:
        graphs = schema[type_uri].get('graphs', [])
        if graphs and graphs[0]:
            return graphs[0]

    return 'http://example.org/graphs/default'

