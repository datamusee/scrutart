import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
import requests

app = Flask(__name__)

# Dictionnaire pour stocker les tâches en cours
tasks = {}


def buildPage(qid, label, uri, task_id):
    """
    Fonction qui construit le contenu de la page basé sur l'entité Wikidata
    Simule un traitement long
    """
    try:
        # Mise à jour du statut
        tasks[task_id]['status'] = 'processing'
        tasks[task_id]['progress'] = 10

        to_process = f"""
        {{
            "categoryName": {label},
            "qid": {qid},
            "piwigoCategory": 461,
            "listimagespath": "D:/wamp64/www/givingsense.eu/datamusee/scrutart/src/generationWordpress/data/fr/20250926/listeImages_{qid}_{label.replace(" ","").replace("-", "")}.json"
        }}
        """
        # Simulation d'un traitement long
        time.sleep(2)  # Remplacez par votre vraie logique
        tasks[task_id]['progress'] = 50

        # Exemple de logique - remplacez par votre propre implémentation
        page_content = to_process + f"""
# Page générée pour {label}

**Identifiant Wikidata :** {qid}
**URI :** {uri}
**Date de génération :** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Informations sur l'entité

Cette page a été générée automatiquement pour l'entité Wikidata {qid}.
L'artiste "{label}" peut être consulté directement sur Wikidata à l'adresse suivante :
{uri}

## Actions possibles

- Consulter la page Wikidata
- Extraire des informations supplémentaires
- Générer un rapport détaillé

---
Contenu généré par l'application Flask Wikidata Artist Search
        """

        time.sleep(2)  # Simulation de traitement supplémentaire
        tasks[task_id]['progress'] = 100

        # Mise à jour avec le résultat final
        tasks[task_id].update({
            'status': 'completed',
            'page_content': page_content,
            'completed_at': datetime.now().isoformat()
        })

    except Exception as e:
        tasks[task_id].update({
            'status': 'error',
            'error': str(e),
            'completed_at': datetime.now().isoformat()
        })


@app.route('/traiterUri', methods=['POST'])
def traiter_uri():
    """Route pour traiter l'URI sélectionnée de façon asynchrone"""
    uri = request.form.get('uri')
    qid = request.form.get('qid')
    label = request.form.get('label')

    if not uri:
        return jsonify({'error': 'URI manquant'}), 400

    # Génération d'un ID unique pour la tâche
    task_id = f"{qid}_{int(time.time())}"

    # Initialisation de la tâche
    tasks[task_id] = {
        'status': 'pending',
        'qid': qid,
        'label': label,
        'uri': uri,
        'created_at': datetime.now().isoformat(),
        'progress': 0
    }

    # Lancement du traitement en arrière-plan
    thread = threading.Thread(target=buildPage, args=(qid, label, uri, task_id))
    thread.daemon = True
    thread.start()

    return render_template('processing.html',
                           task_id=task_id,
                           qid=qid,
                           label=label,
                           uri=uri)


@app.route('/api/task/<task_id>')
def get_task_status(task_id):
    """API pour récupérer le statut d'une tâche"""
    if task_id not in tasks:
        return jsonify({'error': 'Tâche non trouvée'}), 404

    return jsonify(tasks[task_id])


@app.route('/result/<task_id>')
def show_result(task_id):
    """Affiche le résultat final d'une tâche"""
    if task_id not in tasks:
        return render_template('index.html', error="Tâche non trouvée")

    task = tasks[task_id]

    if task['status'] != 'completed':
        return render_template('processing.html',
                               task_id=task_id,
                               qid=task['qid'],
                               label=task['label'],
                               uri=task['uri'])

    return render_template('processed.html', result=task)


def search_wikidata_entities(search_term, limit=5):
    """
    Recherche des entités sur Wikidata correspondant au terme de recherche
    """
    url = "https://www.wikidata.org/w/api.php"
    params = {
        'action': 'wbsearchentities',
        'search': search_term,
        'language': 'fr',
        'format': 'json',
        'limit': limit,
        'type': 'item'
    }

    headers = {
        'User-Agent': 'Grains de Culture WikidataArtistSearch/1.0 (https://grains-de-culture.fr/) Python/Flask'
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        results = []
        for item in data.get('search', []):
            entity = {
                'qid': item.get('id'),
                'label': item.get('label', ''),
                'description': item.get('description', ''),
                'uri': f"https://www.wikidata.org/entity/{item.get('id')}",
                'concepturi': item.get('concepturi', '')
            }
            results.append(entity)

        return results
    except requests.RequestException as e:
        print(f"Erreur lors de la recherche Wikidata: {e}")
        return []

@app.route('/')
def index():
    """Page d'accueil avec le formulaire de recherche"""
    return render_template('index.html')


@app.route('/search', methods=['POST'])
def search():
    """Route pour effectuer la recherche d'artiste"""
    artist_name = request.form.get('artist_name', '').strip()

    if not artist_name:
        return render_template('index.html', error="Veuillez entrer un nom d'artiste")

    # Rechercher sur Wikidata
    entities = search_wikidata_entities(artist_name)

    if not entities:
        return render_template('index.html',
                               error=f"Aucun résultat trouvé pour '{artist_name}'",
                               search_term=artist_name)

    return render_template('results.html',
                           entities=entities,
                           search_term=artist_name)


@app.route('/validate', methods=['POST'])
def validate():
    """Route pour valider une entité sélectionnée"""
    qid = request.form.get('qid')
    label = request.form.get('label')
    uri = request.form.get('uri')

    if not qid:
        return jsonify({'error': 'QID manquant'}), 400

    # Stocker la validation (ici on retourne juste les infos)
    return render_template('validated.html',
                           qid=qid,
                           label=label,
                           uri=uri)


@app.route('/api/search')
def api_search():
    """API endpoint pour la recherche (optionnel)"""
    search_term = request.args.get('q', '')
    limit = request.args.get('limit', 5, type=int)

    if not search_term:
        return jsonify({'error': 'Paramètre q manquant'}), 400

    entities = search_wikidata_entities(search_term, limit)
    return jsonify({'results': entities})


if __name__ == '__main__':
    app.run(debug=False)
