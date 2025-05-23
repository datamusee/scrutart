from flask import Flask, render_template, request
import requests
import json

from src.generationWordpress.PageBuilder import  PageBuilder


TYPES = {
    "creator": "Creator",
    "movement": "Art Movement",
    "painting": "Painting",
    "museum": "Museum"
}

LANGUAGES = ["en", "fr", "es", "de", "it"]

# TODO passer par mon proxy pour limiter les appels à WDQS

app = Flask(__name__)

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "WikidataToJSONLDBot/1.0 (contact@example.com)"}
WIKIDATA_ENTITY_BASE = "https://www.wikidata.org/wiki/"

def sparql_query(query):
    response = requests.get(SPARQL_ENDPOINT, params={"query": query, "format": "json"}, headers=HEADERS)
    return response.json()

def detect_type(qid):
    query = f"""
    SELECT ?instance ?occupation ?subclass WHERE {{
      wd:{qid} wdt:P31 ?instance .
      OPTIONAL {{ wd:{qid} wdt:P106 ?occupation . }}
      OPTIONAL {{ ?instance wdt:P279 ?subclass . }}
    }}
    """
    results = sparql_query(query)["results"]["bindings"]
    instances = [r['instance']['value'].split('/')[-1] for r in results if 'instance' in r]
    occupations = [r['occupation']['value'].split('/')[-1] for r in results if 'occupation' in r]
    subclasses = [r['subclass']['value'].split('/')[-1] for r in results if 'subclass' in r]

    if 'Q5' in instances and ('Q1028181' in occupations or 'Q483501' in occupations):
        return "painter"
    elif any(i in instances for i in ['Q3305213', 'Q838948', 'Q4502142']):
        return "painting"
    elif any(i in instances for i in ['Q33506', 'Q207694', 'Q23413']):
        return "museum"
    elif any(i in instances + subclasses for i in ['Q968159', 'Q21198342']):
        return "art_movement"
    else:
        return "unknown"

def get_entity_data(qid):
    query = f"""
    SELECT ?label ?description ?image ?birthDate ?deathDate ?countryLabel ?website WHERE {{
      wd:{qid} rdfs:label ?label .
      FILTER(LANG(?label) = "en")
      OPTIONAL {{ wd:{qid} schema:description ?description . FILTER(LANG(?description) = "en") }}
      OPTIONAL {{ wd:{qid} wdt:P18 ?image . }}
      OPTIONAL {{ wd:{qid} wdt:P569 ?birthDate . }}
      OPTIONAL {{ wd:{qid} wdt:P570 ?deathDate . }}
      OPTIONAL {{ wd:{qid} wdt:P17 ?country . }}
      OPTIONAL {{ wd:{qid} wdt:P856 ?website . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 1
    """
    return sparql_query(query)

def build_jsonld(qid, data):
    bindings = data['results']['bindings'][0]
    get = lambda k: bindings.get(k, {}).get('value')
    entity_type = detect_type(qid)

    jsonld = {
        "@context": "https://schema.org",
        "name": get('label'),
        "description": get('description'),
        "sameAs": f"{WIKIDATA_ENTITY_BASE}{qid}"
    }

    if entity_type == "painter":
        jsonld["@type"] = "Person"
        jsonld["jobTitle"] = "Painter"
        jsonld["birthDate"] = get('birthDate')
        jsonld["deathDate"] = get('deathDate')
        if get('countryLabel'): jsonld["nationality"] = get('countryLabel')
        if get('image'): jsonld["image"] = get('image')

    elif entity_type == "painting":
        jsonld["@type"] = "VisualArtwork"
        jsonld["genre"] = "Painting"
        if get('image'): jsonld["image"] = get('image')

    elif entity_type == "museum":
        jsonld["@type"] = "Museum"
        if get('website'): jsonld["url"] = get('website')
        if get('image'): jsonld["image"] = get('image')

    elif entity_type == "art_movement":
        jsonld["@type"] = "CreativeWork"
        jsonld["genre"] = "Art Movement"

    else:
        jsonld["@type"] = "Thing"

    return jsonld

@app.route('/wdtjsonld', methods=['GET', 'POST'])
def wdtjsonld_interface():
    result = None
    qid = ""
    if request.method == 'POST':
        qid = request.form.get('qid', '').strip()
        if qid.startswith("Q"):
            data = get_entity_data(qid)
            result = build_jsonld(qid, data)
    return render_template('jsonLdBuilder.html', result=result, qid=qid)

@app.route('/pagebuilder', methods=['GET', 'POST'])
def pagebuilder_interface():
    qid = type_ = lang = rendered = None
    raw = ""

    if request.method == 'POST':
        wtypetable = {
            "creator":"Q1028181",
            "genre": None,
            "movement": None,
            "painting": None,
        }
        qid = request.form.get('qid', '').strip()
        type_ = request.form.get('type')
        qtype = wtypetable.get(type_, None)
        lang = request.form.get('lang')
        if qtype:
            pbuild = PageBuilder(qtype, lang=lang)
        if qid and qtype and lang:
            raw = pbuild.generatePage(qid, None)
            rendered = raw  # rendu de base (affiché tel quel), ou peut être converti depuis Markdown par ex.

    return render_template('pageBuilder.html', qid=qid, type_=type_, lang=lang,
                           raw=raw, rendered=rendered, types=TYPES, languages=LANGUAGES)

if __name__ == '__main__':
    app.run(debug=False)

