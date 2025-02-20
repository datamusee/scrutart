from flask import Flask
import socketio

# Crée une instance Socket.IO
sio = socketio.Server(cors_allowed_origins="*")  # Autoriser les connexions depuis toutes les origines
app = Flask(__name__)  # L'application Flask principale

# Enregistrez l'application Flask avec Socket.IO
app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)

@app.route("/")
def index():
    return "Serveur Flask avec Socket.IO intégré!"

# Gestionnaire d'événement Socket.IO pour les connexions
@sio.event
def connect(sid, environ):
    print(f"Client connecté : {sid}")
    sio.emit("message", {"message": "Bienvenue sur le serveur!"}, to=sid)

# Gestionnaire d'événement Socket.IO pour les déconnexions
@sio.event
def disconnect(sid):
    print(f"Client déconnecté : {sid}")

# Gestionnaire d'événement Socket.IO personnalisé
@sio.event
def custom_event(sid, data):
    print(f"Événement personnalisé reçu de {sid} : {data}")
    sio.emit("custom_event_response", {"response": "Données reçues!", "data": data}, to=sid)

# Exposez l'application Flask (pour les environnements WSGI)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


app = Flask(__name__)  # L'application Flask principale

# Enregistrez l'application Flask avec Socket.IO
app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)

@app.route("/")
def index():
    return "Serveur Flask avec Socket.IO intégré!"

# Gestionnaire d'événement Socket.IO pour les connexions
@sio.event
def connect(sid, environ):
    print(f"Client connecté : {sid}")
    sio.emit("message", {"message": "Bienvenue sur le serveur!"}, to=sid)

# Gestionnaire d'événement Socket.IO pour les déconnexions
@sio.event
def disconnect(sid):
    print(f"Client déconnecté : {sid}")

# Gestionnaire d'événement Socket.IO personnalisé
@sio.event
def custom_event(sid, data):
    print(f"Événement personnalisé reçu de {sid} : {data}")
    sio.emit("custom_event_response", {"response": "Données reçues!", "data": data}, to=sid)

# Exposez l'application Flask (pour les environnements WSGI)
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
