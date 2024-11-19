import socket
import threading
import time
import json

class SellerServer:
    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = []
        self.clients_lock = threading.Lock()
        self.inventory_lock = threading.Lock()
        self.items = ['flour', 'sugar', 'potato', 'oil']
        self.initial_amount = 5  # Starting amount for each item

        # Initialize the item queue with items and their inventories
        self.item_queue = [{'name': item, 'amount_left': self.initial_amount} for item in self.items]
        self.current_item = None
        self.current_amount = 0
        self.sale_end_time = None

    def start_server(self):
        # Initialize server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Seller server started on {self.host}:{self.port}")

        # Start item sale in a separate thread
        threading.Thread(target=self.item_sale_cycle, daemon=True).start()

        try:
            while True:
                client_socket, client_address = self.server_socket.accept()
                print(f"Buyer connected from {client_address}")
                threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
        except KeyboardInterrupt:
            print("Server is shutting down.")
            self.server_socket.close()

    def item_sale_cycle(self):
        while self.item_queue:
            with self.inventory_lock:
                # Get the next item from the queue
                current_item_info = self.item_queue.pop(0)
                self.current_item = current_item_info['name']
                self.current_amount = current_item_info['amount_left']

            self.sale_end_time = time.time() + 60  # 60-second sale period
            print(f"Selling {self.current_item}, {self.current_amount} units available.")

            self.broadcast({
                'type': 'ITEM',
                'item': self.current_item,
                'amount_left': self.current_amount,
                'time_left': 60
            })

            while time.time() < self.sale_end_time and self.current_amount > 0:
                time_left = int(self.sale_end_time - time.time())
                self.broadcast({'type': 'TIME_LEFT', 'time_left': time_left})
                time.sleep(1)

            with self.inventory_lock:
                if self.current_amount > 0:
                    print(f"Time expired. {self.current_amount} units of {self.current_item} unsold.")
                    # Put unsold item back into the queue
                    self.item_queue.append({
                        'name': self.current_item,
                        'amount_left': self.current_amount
                    })
                else:
                    print(f"{self.current_item} sold out.")

            # Reset current item
            self.current_item = None
            self.current_amount = 0
            self.sale_end_time = None

        print("All items have been sold out. Closing the market.")
        # Optionally, you can shut down the server here if desired

    def handle_client(self, client_socket):
        with self.clients_lock:
            self.clients.append(client_socket)
        try:
            while True:
                data = client_socket.recv(1024)
                if not data:
                    break
                messages = data.decode().split('\n')
                for message_str in messages:
                    if message_str:
                        message = json.loads(message_str)
                        self.process_message(client_socket, message)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            with self.clients_lock:
                self.clients.remove(client_socket)
            client_socket.close()

    def process_message(self, client_socket, message):
        msg_type = message.get('type')
        if msg_type == 'JOIN':
            self.send_message(client_socket, {'type': 'WELCOME'})
            
            # Send current item information if an item is being sold
            if self.current_item:
                time_left = max(0, int(self.sale_end_time - time.time())) if self.sale_end_time else 0
                self.send_message(client_socket, {
                    'type': 'ITEM',
                    'item': self.current_item,
                    'amount_left': self.current_amount,
                    'time_left': time_left
                })
        
        elif msg_type == 'LIST':
            with self.inventory_lock:
                inventory_list = {item_info['name']: item_info['amount_left'] for item_info in self.item_queue}
                # Include current item being sold
                if self.current_item:
                    inventory_list[self.current_item] = self.current_amount
            self.send_message(client_socket, {'type': 'LIST_RESPONSE', 'inventory': inventory_list})
        
        elif msg_type == 'BUY':
            item = message.get('item')
            amount = message.get('amount', 1)
            self.handle_purchase(client_socket, item, amount)
        
        elif msg_type == 'LEAVE':
            print(f"Buyer disconnected from {client_socket.getpeername()}")

    def handle_purchase(self, client_socket, item, amount):
        with self.inventory_lock:
            if item == self.current_item and self.current_amount >= amount:
                self.current_amount -= amount
                # Send purchase confirmation to the buyer
                self.send_message(client_socket, {
                    'type': 'CONFIRM',
                    'item': item,
                    'amount_bought': amount
                })
                # Notify all buyers about the updated inventory
                self.broadcast({
                    'type': 'UPDATE',
                    'item': item,
                    'amount_left': self.current_amount
                })
                if self.current_amount == 0:
                    self.broadcast({'type': 'SOLD_OUT', 'item': item})
            else:
                # Send purchase failure message to the buyer
                self.send_message(client_socket, {
                    'type': 'FAIL',
                    'message': 'Purchase failed. Not enough inventory or wrong item.'
                })

    def send_message(self, client_socket, message):
        try:
            client_socket.send((json.dumps(message) + '\n').encode())
        except Exception as e:
            print(f"Error sending message to client: {e}")

    def broadcast(self, message):
        with self.clients_lock:
            for client in self.clients:
                try:
                    client.send((json.dumps(message) + '\n').encode())
                except:
                    pass  # Handle broken connections if necessary





if __name__ == "__main__":
    server = SellerServer()
    server.start_server()
