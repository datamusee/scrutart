import time
import asyncio
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from threading import Thread

# Initialisation de Flask
app = Flask(__name__)

# Configuration de Flask-Limiter
limiter = Limiter(get_remote_address, app=app)

# Simuler un traitement asynchrone des requêtes
task_status = {}


async def process_request_async(task_id):
    """Fonction asynchrone pour simuler le traitement d'une requête API"""
    # await asyncio.sleep(15)  # Simule un délai pour l'appel API
    task_status[task_id] = "Terminé"


def run_async(func, *args):
    """Utiliser un thread pour exécuter la fonction asynchrone dans un événement boucle asyncio"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(func(*args))


@app.route('/make_request', methods=['POST'])
@limiter.limit("5 per second")  # Limite de 5 requêtes par seconde
def make_request():
    """Route pour recevoir la requête du client et commencer le traitement"""
    data = request.get_json()
    task_id = data.get('task_id')

    # Vérifier si l'ID de tâche est fourni
    if not task_id:
        return jsonify({"error": "task_id is required"}), 400

    # Démarrer le traitement en arrière-plan dans un thread
    #thread = Thread(target=run_async, args=(process_request_async, task_id))
    #thread.start()

    # Retourner immédiatement un message au client
    return jsonify({"message": "Votre requête est en cours de traitement", "task_id": task_id}), 202

@app.route('/', methods=['GET'])
def home():
    return """web api manager avec limiteur de nombre de requêtes par seconde"""

@app.route('/check_status/<task_id>', methods=['GET'])
# async def check_status(task_id):
def check_status(task_id):
    """Route pour vérifier l'état de la tâche en cours (polling asynchrone)"""
    status = task_status.get(task_id, "Inconnu")
    if status == "Terminé":
        return jsonify({"task_id": task_id, "status": "Traitement terminé"})
    else:
        return jsonify({"task_id": task_id, "status": "Traitement en cours"}), 202


if __name__ == "__main__":
    app.run(debug=False)
