# test_eventlet_flask_socketio.py
import eventlet
eventlet.monkey_patch()

from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

@app.route('/')
def index():
    return 'Hello from Flask-SocketIO with Eventlet!'

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
