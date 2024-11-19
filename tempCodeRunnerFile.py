def send_message(self, message):
    try:
        self.client_socket.send((json.dumps(message) + '\n').encode())
    except Exception as e:
        print(f"Error sending message to server: {e}")