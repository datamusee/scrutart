import requests
from SPARQLWrapper import SPARQLWrapper, JSON
from markupsafe import escape
from simulate_file_generation import simulate_file_generation
from simulate_publish_to_wordpress import simulate_publish_to_wordpress
from multilingual_support import get_paintings, get_artist_label, generate_html

import os
import json

import threading
import time
from flask import Flask, request, render_template, jsonify, send_from_directory, url_for

app = Flask(__name__)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
FILES_DIR = os.path.join(BASE_DIR, 'static', 'files')
os.makedirs(FILES_DIR, exist_ok=True)

# En mémoire : état des tâches
tasks = {}
# En mémoire : état des tâches du pipeline
ptasks = {}

import threading
import time
import json
import traceback

# --- Tâches ---

def task_1(input_data):
    time.sleep(1)
    return {"value": 10, "status": "done"}

def task_2(input_data):
    time.sleep(1)
    if input_data["value"] == 10:
        raise ValueError("Erreur dans task_2 (valeur interdite)")
    return {"value": input_data["value"] * 3, "status": "done"}

def task_3(input_data):
    time.sleep(1)
    return {"value": input_data["value"] + 5, "status": "done"}

# --- Transitions ---

def transition_1_to_2(result_1):
    return result_1

def transition_2_to_3(result_2):
    return result_2

# --- Runner séquentiel dans un seul thread ---

class TaskChainRunner(threading.Thread):
    def __init__(self, steps, transitions, initial_input):
        super().__init__()
        self.steps = steps
        self.transitions = transitions
        self.initial_input = initial_input
        self.results = {}
        self.success = True
        self.error = None

    def run(self):
        input_data = self.initial_input
        qid = input_data["qid"]
        for i, step in enumerate(self.steps):
            if not "process" in step: continue
            task_name = str(step["process"])
            try:
                print(f"→ Démarrage {task_name}")
                lang = None
                if "lang" in step:
                    lang = step["lang"]
                    input_data["lang"] = lang
                msgStart = step["msgStart"].replace("__QID__", qid)
                if lang: msgStart = msgStart.replace("__LANG__", lang)
                step["status"].append(msgStart)
                result = step["process"](input_data)
                self.results[task_name] = result
                print(f"✓ {task_name} terminé : {result}")
                if i < len(self.transitions):
                    input_data = self.transitions[i](result)
                msgEnd = step["msgEnd"].replace("__QID__", qid)
                if lang: msgEnd = msgEnd.replace("__LANG__", lang)
                if "galId" in result: msgEnd = msgEnd.replace("__IDGAL__", result["galId"])
                step["status"].append(msgEnd)
            except Exception as e:
                self.success = False
                self.error = {
                    "task": task_name,
                    "message": str(e),
                    "traceback": traceback.format_exc()
                }
                print(f"✗ Erreur dans {task_name} : {e}")
                break

# --- Configuration ---

# tasks = [task_1, task_2, task_3]
transitions = [transition_1_to_2, transition_2_to_3]
initial_input = {}

# --- Exécution dans un seul thread ---

def get_gallery_id(inputdict):
    qid = inputdict["qid"]
    # gestion d'erreur fantaisite à titre d'exemple
    if qid == "Q0":
        raise ValueError(f"Erreur dans tache {get_gallery_id.__name__} (valeur d'entrée interdite)")
    inputdict["galId"] = f"id de galerie pour entité {qid}"
    return inputdict

def get_image_list(inputdict):
    qid = inputdict["qid"]
    imageList = [{ "url":"toto", "title": "Titre de toto"}]
    inputdict["imageList"] = imageList
    return inputdict

def build_page_wp(inputdict): # qid, lang, galid):
    qid = inputdict["qid"]
    lang = inputdict["lang"]
    galid = inputdict["galId"]
    page = f"""Page pour l'entité {qid}, en langue {lang}, associée à la galerie {galid}"""
    inputdict["page"] = page
    return inputdict

pipeline_steps = [
    { "process": get_gallery_id, "msgStart":"""Recherche de galerie pour __QID__""",
      "msgEnd":"""Pour __QID__, ID galerie __IDGAL__""", "status": [] },
    { "process": get_image_list, "msgStart":"""Recherche de liste d'images pour __QID__""",
      "msgEnd":"""Pour __QID__, taille de la liste d'images __IMAGECOUNT__""", "status": [] },
    { "process": build_page_wp, "msgStart":"""Construction de page pour __QID__ (langue: __LANG__)""", "lang":"fr",
      "msgEnd":"""Page pour __QID__, associé à la galerie __IDGAL__, reliés à __IMAGECOUNT__ images""", "status": [] },
    {"process": build_page_wp, "msgStart": """Construction de page pour __QID__ (langue: __LANG__)""", "lang": "en",
     "msgEnd": """Page pour __QID__, associé à la galerie __IDGAL__, reliés à __IMAGECOUNT__ images""", "status": []},
    {"process": build_page_wp, "msgStart": """Construction de page pour __QID__ (langue: __LANG__)""", "lang": "es",
     "msgEnd": """Page pour __QID__, associé à la galerie __IDGAL__, reliés à __IMAGECOUNT__ images""", "status": []},
]

def is_painter(qid):
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    sparql.setQuery(f"""
    ASK {{
      wd:{qid} wdt:P31 wd:Q5;
               wdt:P106 wd:Q1028181.
    }}
    """)
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()['boolean']


def get_paintings(qid, limit=200):
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    sparql.setQuery(f"""
    SELECT ?item ?itemLabel ?image WHERE {{
      ?item wdt:P170 wd:{qid};
            wdt:P31/wdt:P279* wd:Q3305213.
      OPTIONAL {{ ?item wdt:P18 ?image }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fr,en". }}
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



def simulate_exec_pipeline(qid: str, templateHtmlPath="templates/modelePage.html"):
    """Simule un traitement long générant des fichiers texte."""
    task_dir = os.path.join(FILES_DIR, qid)
    os.makedirs(task_dir, exist_ok=True)
    ptasks[qid] = []

    for step in pipeline_steps:
        if "langs" in step:
            for lang in step["langs"]:
                msgStart = step["msgStart"].replace("__QID__", qid).replace("__LANG__", lang)
                step["status"].append(msgStart)
                step["process"](qid, lang, 0)
                msgEnd = step["msgEnd"].replace("__QID__", qid).replace("__LANG__", lang)
                step["status"].append(msgEnd)
        else:
            msgStart = step["msgStart"].replace("__QID__", qid)
            step["status"].append(msgStart)
            step["process"](qid)
            msgEnd = step["msgEnd"].replace("__QID__", qid)
            step["status"].append(msgEnd)
        ptasks[qid].append(step)
    step = { "status": ["END_PIPELINE"]}
    ptasks[qid].append(step)


def simulate_file_generation(qid: str, templateHtmlPath="templates/modelePage.html"):
    """Simule un traitement long générant des fichiers texte."""
    task_dir = os.path.join(FILES_DIR, qid)
    os.makedirs(task_dir, exist_ok=True)
    tasks[qid] = []

    for lang in ["fr", "en", "es"]:  # 5 fichiers générés progressivement
        time.sleep(2)  # Simule un délai
        filename = f"{qid}_lang_{lang}.html"
        file_path = os.path.join(task_dir, filename)
        template = f"Contenu généré pour __QID__, fichier __INDEX__\n"
        with open(templateHtmlPath) as ft:
            template = ft.read()
        with open(file_path, 'w') as f:
            f.write(template.replace("__QID__", qid).replace("__LANG__", str(lang)))
        tasks[qid].append(filename)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start():
    qid = request.form.get('qid') or request.json.get('qid')
    if not qid or not qid.startswith('Q') or not qid[1:].isdigit():
        return jsonify({'error': 'Identifiant invalide'}), 400
    initial_input = { "qid": qid }
    # reset status of steps
    for step in pipeline_steps: step["status"] = []
    step = { "status": ["END_PIPELINE"]}
    pipeline_steps.append(step)
    # Ne pas relancer si déjà en cours
    if qid not in ptasks:
        runner = TaskChainRunner(pipeline_steps, transitions, initial_input)
        ptasks[qid] = runner
        runner.start()
        runner.join()

    return jsonify({'message': f"Traitement lancé pour {qid}", 'qid': qid})


@app.route('/pipestatus/<qid>')
def pipestatus(qid):
    if qid not in ptasks:
        return jsonify({'status': 'not_started', 'files': []})
    runner = ptasks[qid]
    status_msgs = [
        ", ".join(step["status"]) for step in runner.steps
    ]
    # --- Affichage des résultats ---
    if runner.success:
        print("\n✅ Toutes les tâches ont réussi.")
    else:
        print("\n❌ Une erreur est survenue.")
        print(json.dumps(runner.error, indent=2))
    print("\n📦 Résultats complets :")
    print(json.dumps(runner.results, indent=2))

    return jsonify({'pipestatus': 'running', 'msgs': status_msgs})

@app.route('/files/<qid>/<filename>')
def download_file(qid, filename):
    return send_from_directory(os.path.join(FILES_DIR, qid), filename)


if __name__ == '__main__':
    app.run(debug=False)

