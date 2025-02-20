import socketio

class SocketClient:
    def __init__(self, server_url):
        # Initialize the Socket.IO client
        self.server_url = server_url
        self.sio = socketio.Client()
        self._setup_event_handlers()

    def _setup_event_handlers(self):
        # Set up event handlers
        @self.sio.event
        def connect():
            print("Connected to server.")

        @self.sio.event
        def disconnect():
            print("Disconnected from server.")

        @self.sio.event
        def message(data):
            print(f"Message received: {data}")

    def connect(self):
        # Connect to the server
        try:
            self.sio.connect(self.server_url)
        except Exception as e:
            print(f"Failed to connect to {self.server_url}: {e}")

    def disconnect(self):
        # Disconnect from the server
        self.sio.disconnect()

    def send_message(self, event, data):
        # Send a custom event with data to the server
        if self.sio.connected:
            self.sio.emit(event, data)
        else:
            print("Client is not connected to the server.")

    def on_event(self, event, handler):
        # Dynamically set up a custom event handler
        self.sio.on(event, handler)

# Example usage
if __name__ == "__main__":
    # client = SocketClient("http://127.0.0.1:5000")
    client = SocketClient("https://https://webapimanager.grains-de-culture.fr")

    # Custom handler for a specific event
    def custom_handler(data):
        print(f"Custom event received: {data}")

    # Register custom handler
    client.on_event("custom_event_response", custom_handler)

    # Connect to the server
    client.connect()

    # Send a custom event
    client.send_message("custom_event", {"message": "Hello, server!"})

    # Wait for a while to handle events (for demonstration)
    import time
    time.sleep(5)

    # Disconnect from the server
    client.disconnect()
