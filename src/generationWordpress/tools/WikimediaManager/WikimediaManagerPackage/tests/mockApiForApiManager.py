import time

from flask import Flask, jsonify
import json

app = Flask(__name__)


@app.route('/mockapi/test/<int:i>')
def test_with_index(i):
    """Endpoint qui retourne l'index passé en paramètre"""
    return jsonify({"index": i})


@app.route('/mockapi/test')
def test_basic():
    """Endpoint de test basique"""
    return jsonify({"data": "test"})


@app.route('/mockapi/unicode')
def unicode_endpoint():
    """Endpoint qui retourne un objet vide"""
    return jsonify({})


@app.route('/mockapi/thread/<thread_id>/req/<int:i>')
def thread_request(thread_id, i):
    """Endpoint pour les threads avec ID et index de requête"""
    return jsonify({})


@app.route('/mockapi/large/<int:i>')
def large_endpoint(i):
    """Endpoint pour les données volumineuses"""
    return jsonify({})

@app.route('/mockapi/delay/<int:delay>')
def slow_endpoint(delay):
    """Endpoint pour provoquer un timeout"""
    time.sleep(delay)
    return jsonify({})


@app.route('/mockapi/empty')
def empty_endpoint():
    """Endpoint qui retourne un objet vide"""
    return jsonify({})


@app.route('/mockapi')
def minimal_endpoint():
    """Endpoint qui retourne un objet vide"""
    return jsonify({"message":"appel réussi de mockapi", "args": { "test": "completion"}})


# Route optionnelle pour la racine
@app.route('/')
def index():
    """Page d'accueil avec la liste des endpoints disponibles"""
    endpoints = [
        "GET /mockapi/test/{i} - Retourne {'index': i}",
        "GET /mockapi/test - Retourne {'data': 'test'}",
        "GET /mockapi/unicode - Retourne {}",
        "GET /mockapi/thread/{thread_id}/req/{i} - Retourne {}",
        "GET /mockapi/large/{i} - Retourne {}",
        "GET /mockapi/empty - Retourne {}"
    ]

    return jsonify({
        "message": "MockAPI Flask Server",
        "endpoints": endpoints
    })


# Gestion d'erreur 404
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


# Gestion d'erreur 500
@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    # Configuration pour le développement
    app.run(
        debug=False,  # Mode debug activé
        host='0.0.0.0',  # Accessible depuis l'extérieur
        port=5010  # Port par défaut
    )