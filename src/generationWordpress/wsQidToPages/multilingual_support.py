from SPARQLWrapper import SPARQLWrapper, JSON
from markupsafe import escape

def get_artist_label(qid, lang='fr'):
    """Récupère le label de l’artiste dans la langue donnée."""
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    sparql.setQuery(f"""
    SELECT ?label WHERE {{
      wd:{qid} rdfs:label ?label.
      FILTER(LANG(?label) = "{lang}")
    }} LIMIT 1
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    if results['results']['bindings']:
        return results['results']['bindings'][0]['label']['value']
    return qid

def get_paintings(qid, lang='fr', limit=20):
    """Retourne une liste d'œuvres dans la langue donnée."""
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    sparql.setQuery(f"""
    SELECT ?item ?itemLabel ?image WHERE {{
      ?item wdt:P170 wd:{qid};
            wdt:P31/wdt:P279* wd:Q3305213.
      OPTIONAL {{ ?item wdt:P18 ?image }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{lang},en". }}
    }} LIMIT {limit}
    """)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    paintings = []
    for r in results["results"]["bindings"]:
        paintings.append({
            'label': r["itemLabel"]["value"],
            'url': r["item"]["value"],
            'image': r.get("image", {}).get("value")
        })
    return paintings

def generate_html(artist_name, paintings, lang='fr'):
    intro = {
        'fr': f"<h1>Œuvres de {artist_name}</h1><p>Voici une sélection de ses œuvres peintes :</p>",
        'en': f"<h1>Works by {artist_name}</h1><p>Here is a selection of their painted works:</p>"
    }
    html = f"<html><head><meta charset='utf-8'></head><body>{intro[lang]}<ul>"
    for p in paintings:
        html += "<li>"
        if p["image"]:
            html += f"<img src='{p['image']}' width='150'><br>"
        html += f"<a href='{p['url']}' target='_blank'>{escape(p['label'])}</a></li>\n"
    html += "</ul></body></html>"
    return html
