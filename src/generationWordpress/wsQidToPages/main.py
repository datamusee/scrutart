"""
installé dans
https://trials.grains-de-culture.fr/
décrit dans sites/trials.grains-de-culture.fr
pour tester que ça devrait pouvoir fonctionner
"""
import requests
from SPARQLWrapper import SPARQLWrapper, JSON
from markupsafe import escape
from simulate_publish_to_wordpress import simulate_publish_to_wordpress
from multilingual_support import get_paintings, get_artist_label, generate_html

import os
from flask import Flask, request, render_template, jsonify, send_from_directory, url_for
import copy
import threading
import time
import json
import traceback
import logging

# --- Logger configuration ---

logger = logging.getLogger("TaskChain")
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')

# Console output
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# File output
file_handler = logging.FileHandler("task_chain.log")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


# --- Retry modifier pour task_2 ---
def retry_modifier_task_2(prev_input, attempt):
    new_input = prev_input.copy()
    if "maxsize" in new_input:
        new_input["maxsize"] = int(new_input["maxsize"]/2)
    else:
        new_input["maxsize"] = 10
    logger.info(f"↻ Retry {attempt} task_2 avec paramètres ajustés: {new_input}")
    return new_input

# --- Thread unitaire pour une tâche ---
class TaskThread(threading.Thread):
    def __init__(self, task_func, input_data):
        super().__init__()
        self.task_func = task_func
        self.input_data = input_data
        self.result = None
        self.exception = None

    def run(self):
        try:
            self.result = self.task_func["process"](self.input_data)
        except Exception as e:
            self.exception = {
                "message": str(e),
                "traceback": traceback.format_exc()
            }

retry_modifiers = [None, retry_modifier_task_2, None]


# --- Affichage final ---
#logger.info("📦 Résultat final :")
# logger.info(json.dumps(result, indent=2))

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


# --- Transitions ---

def transition_1_to_2(result_1):
    return result_1

def transition_2_to_3(result_2):
    return result_2

# --- Runner séquentiel dans un seul thread ---

class TaskChainRunner(threading.Thread):
    def __init__(self, steps, transitions, retry_modifiers, initial_input):
        super().__init__()
        self.steps = steps
        self.transitions = transitions
        self.retry_modifiers = retry_modifiers
        self.initial_input = initial_input
        self.results = {}
        self.success = True
        self.error = None

    def run(self):
        input_data = self.initial_input
        self.results = run_task_chain(self.steps, self.transitions, self.retry_modifiers, self.initial_input)


# --- Configuration ---
transitions = [transition_1_to_2, transition_2_to_3]
initial_input = {}

# --- Exécution avec timeout et retries ---
def run_task_chain(steps, transitions, retry_modifiers, initial_input, timeout=30, max_retries=2):
    results = {}
    input_data = initial_input
    for i, step in enumerate(steps):
        step["status"] = []
        if not "process" in step: continue
        task_name = str(step["process"])
        attempts = []
        success = False
        qid = input_data["qid"]
        current_input = input_data

        for attempt in range(max_retries + 1):
            logger.info(f"Lancement de {task_name} (essai {attempt + 1})")
            lang = None
            if "args" in step and "lang" in step["args"]:
                lang = step["args"]["lang"]
                input_data["lang"] = lang
            maxsize = 100
            if "args" in step and "maxsize" in step["args"]:
                maxsize = step["args"]["maxsize"]
                input_data["maxsize"] = maxsize
            msgStart = step["msgStart"].replace("__QID__", qid)
            if lang: msgStart = msgStart.replace("__LANG__", lang)
            step["status"].append(msgStart)
            t = TaskThread(step, current_input)
            t.start()
            t.join(timeout)

            if t.is_alive():
                logger.warning(f"Timeout de {task_name} à l’essai {attempt + 1}")
                t.join()
                attempts.append({
                    "input": current_input,
                    "timeout": True
                })
                if attempt < max_retries and retry_modifiers[i]:
                    current_input = retry_modifiers[i](current_input, attempt + 1)
                continue

            if t.exception:
                logger.error(f"✗ Exception dans {task_name}: {t.exception['message']}")
                logger.debug(t.exception["traceback"])
                return {
                    "success": False,
                    "failed_task": task_name,
                    "error": t.exception,
                    "attempts": attempts,
                    "results": results
                }

            msgEnd = step["msgEnd"].replace("__QID__", qid)
            if lang: msgEnd = msgEnd.replace("__LANG__", lang)
            if "galId" in t.result: msgEnd = msgEnd.replace("__IDGAL__", t.result["galId"])
            if "imageCount" in t.result: msgEnd = msgEnd.replace("__IMAGECOUNT__", str(t.result["imageCount"]))
            if "filename" in t.result: msgEnd = msgEnd.replace("__FILENAME__", t.result["filename"])
            if "url" in t.result: msgEnd = msgEnd.replace("__FILEPATH__", t.result["url"])
            step["status"].append(msgEnd)
            logger.info(f"{task_name} réussie : {t.result}")
            attempts.append({
                "input": current_input,
                "output": t.result,
                "timeout": False
            })
            results[task_name] = t.result
            input_data = transitions[i](t.result) if i < len(transitions) else input_data
            success = True
            break

        if not success:
            logger.error(f"{task_name} a échoué après {max_retries + 1} tentatives.")
            return {
                "success": False,
                "failed_task": task_name,
                "attempts": attempts,
                "results": results
            }

    step = { "status": ["END_PIPELINE"]}
    steps.append(step)
    return {
        "success": True,
        "results": results
    }

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
    if not "maxsize" in inputdict:
        inputdict["maxsize"] = 100
    maxsize = inputdict["maxsize"]
    # imageList = get_paintings(qid, maxsize) #[{ "url":"toto", "title": "Titre de toto"}]
    imageList = [{ "url":"toto", "title": "Titre de toto"} for i in range(1, 48)]
    if imageList:
        inputdict["imageList"] = imageList
        inputdict["imageCount"] = len(imageList)
    time.sleep(60)
    return inputdict

def build_page_wp(inputdict, templateHtmlPath="templates/modelePage.html"): # qid, lang, galid):
    qid = inputdict["qid"]
    task_dir = os.path.join(FILES_DIR, qid)
    os.makedirs(task_dir, exist_ok=True)
    lang = inputdict["lang"]
    galid = inputdict["galId"]
    page = f"""Page pour l'entité {qid}, en langue {lang}, associée à la galerie {galid}"""
    filename = f"{qid}_lang_{lang}.html"
    file_path = os.path.join(task_dir, filename)
    template = f"Contenu généré pour __QID__, fichier __INDEX__\n"
    with open(templateHtmlPath) as ft:
        template = ft.read()
    with open(file_path, 'w') as f:
        f.write(template.replace("__QID__", qid).replace("__LANG__", str(lang)))
    inputdict["url"] = f"/files/{qid}/{filename}"
    inputdict["filename"] = filename
    return inputdict

pipeline_steps = [
    { "process": get_gallery_id, "msgStart":"""Recherche de galerie pour __QID__""",
      "msgEnd":"""Pour __QID__, ID galerie __IDGAL__""", "status": [] },
    { "process": get_image_list, "msgStart":"""Recherche de liste d'images pour __QID__""",
      "args": { "maxsize": 100 },
      "msgEnd":"""Pour __QID__, taille de la liste d'images __IMAGECOUNT__""", "status": [] },
    { "process": build_page_wp, "msgStart":"""Construction de page pour __QID__ (langue: __LANG__)""",
      "args": { "lang":"fr" },
      "msgEnd": """<a href="__FILEPATH__">__FILENAME__</a>""", "status": [] },
    {"process": build_page_wp, "msgStart": """Construction de page pour __QID__ (langue: __LANG__)""",
     "args": {"lang": "en"},
     "msgEnd": """<a href="__FILEPATH__">__FILENAME__</a>""", "status": []},
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


def get_paintings(qid, limit=100):
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


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start():
    qid = request.form.get('qid') or request.json.get('qid')
    pipe = copy.deepcopy(pipeline_steps)
    if not qid or not qid.startswith('Q') or not qid[1:].isdigit():
        return jsonify({'error': 'Identifiant invalide'}), 400
    if not is_painter(qid):
        return jsonify({'error': 'Identifiant invalide; à ce jour, cette page ne concerne que les peintres'}), 400
    initial_input = { "qid": qid }
    step = { "status": ["END_PIPELINE"]}
    pipe.append(step)
    # Ne pas relancer si déjà en cours
    if qid not in ptasks:
        ptasks[qid] = pipe
        runner = TaskChainRunner(ptasks[qid], transitions, retry_modifiers, initial_input)
        ptasks[qid] = runner
        runner.start()
        runner.join()

    return jsonify({'message': f"Traitement lancé pour {qid}", 'qid': qid})


@app.route('/pipestatus/<qid>')
def pipestatus(qid):
    if qid not in ptasks:
        return jsonify({'status': 'not_started', 'files': []})
    runner = ptasks[qid]
    # récupération pour affichage des status des étapes du runner
    status_msgs = [
        ", ".join(step["status"]) for step in runner.steps
    ]
    # --- Affichage des résultats ---
    """
    if pipeline.success:
        print("\n✅ Toutes les tâches ont réussi.")
    else:
        print("\n❌ Une erreur est survenue.")
        print(json.dumps(pipeline.error, indent=2))
    print("\n📦 Résultats complets :")
    print(json.dumps(pipeline.results, indent=2))
    """
    return jsonify({'pipestatus': 'running', 'msgs': status_msgs})

@app.route('/files/<qid>/<filename>')
def download_file(qid, filename):
    # affichage d'un fichier généré
    return send_from_directory(os.path.join(FILES_DIR, qid), filename)


if __name__ == '__main__':
    app.run(debug=False)

