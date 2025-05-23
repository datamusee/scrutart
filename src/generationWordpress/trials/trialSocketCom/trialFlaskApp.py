from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
socketio = SocketIO(app)

# Dictionnaire pour stocker les client_id associés à leurs sessions
clients = {}

@app.route('/')
def index():
    return "Socket.IO server running with client_id support"

@socketio.on('connect')
def handle_connect():
    print("Client connected")

@socketio.on('register')
def handle_register(data):
    """
    Enregistre un client avec un client_id donné.
    """
    client_id = data.get('client_id')
    if client_id:
        clients[client_id] = request.sid  # Associe le client_id au socket ID
        join_room(client_id)  # Ajoute le client à une "room" identifiée par client_id
        print(f"Client registered with client_id: {client_id}")
        emit('message', {'data': f'You are registered with client_id: {client_id}'}, room=client_id)

@socketio.on('disconnect')
def handle_disconnect():
    """
    Supprime le client_id lors de la déconnexion.
    """
    disconnected_client = None
    for client_id, sid in list(clients.items()):
        if sid == request.sid:
            disconnected_client = client_id
            del clients[client_id]
            leave_room(client_id)
            break
        print(f"Client disconnected: {disconnected_client}")

@app.route('/send_message', methods=['POST'])
def send_message():
    """
    Envoie un message à un client spécifique identifié par son client_id.
    """
    data = request.json
    client_id = data.get('client_id')
    message = data.get('message')

    if client_id in clients:
        emit('message', {'data': message}, room=client_id, namespace='/')
        return {"status": "Message sent", "client_id": client_id}, 200
    else:
        return {"error": "Client not found"}, 404

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
