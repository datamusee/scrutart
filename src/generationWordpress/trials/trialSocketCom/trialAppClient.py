import socketio

# Créer une instance du client Socket.IO
sio = socketio.Client()
client_id = "client123"  # Identifiant unique pour ce client

# Gérer les événements
@sio.on('message')
def on_message(data):
    print(f"Message received: {data['data']}")

@sio.on('connect')
def on_connect():
    print("Connected to server")
    # Envoyer le client_id au serveur pour s'enregistrer
    sio.emit('register', {'client_id': client_id})

@sio.on('disconnect')
def on_disconnect():
    print("Disconnected from server")

if __name__ == "__main__":
    server_url = "http://localhost:5000"
    sio.connect(server_url)
    sio.wait()
