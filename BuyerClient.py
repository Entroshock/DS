import socket
import threading
import json

class BuyerClient:
    def __init__(self, name, host='localhost', port=5000):
        self.name = name
        self.host = host
        self.port = port
        self.client_socket = None
        self.is_running = threading.Event()  # Add a thread-safe flag to control running state

    def connect_to_market(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.host, self.port))
        print(f"{self.name} connected to the market.")

        # Send JOIN message
        self.send_message({'type': 'JOIN', 'name': self.name})

        # Set running flag to true
        self.is_running.set()

        # Start listener thread
        listener_thread = threading.Thread(target=self.listen_to_server, daemon=True)
        listener_thread.start()

        # User input loop
        try:
            while self.is_running.is_set():
                command = input(f"{self.name}> ").strip()
                if command.upper() == 'LEAVE':
                    self.send_message({'type': 'LEAVE'})
                    print("Leaving the market.")
                    self.is_running.clear()  # Signal threads to stop
                    break
                elif command.upper() == 'LIST':
                    self.send_message({'type': 'LIST'})
                elif command.upper().startswith('BUY'):
                    parts = command.split()
                    if len(parts) == 3:
                        item = parts[1]
                        amount = int(parts[2])
                        self.send_message({'type': 'BUY', 'item': item, 'amount': amount})
                    else:
                        print("Usage: BUY <item> <amount>")
                else:
                    print("Commands: LIST, BUY <item> <amount>, LEAVE")
        except KeyboardInterrupt:
            print("\nInterrupted. Leaving the market.")
        finally:
            self.cleanup()

    def cleanup(self):
        """Safely close the socket and stop threads"""
        self.is_running.clear()
        if self.client_socket:
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            finally:
                self.client_socket.close()

    def send_message(self, message):
        try:
            if self.client_socket:
                self.client_socket.send((json.dumps(message) + '\n').encode())
        except Exception as e:
            print(f"Error sending message to server: {e}")
            self.cleanup()

    def listen_to_server(self):
        buffer = ''
        try:
            while self.is_running.is_set():
                data = self.client_socket.recv(1024)
                if not data:
                    break
                
                buffer += data.decode()
                while '\n' in buffer:
                    message_str, buffer = buffer.split('\n', 1)
                    if message_str:
                        message = json.loads(message_str)
                        self.process_server_message(message)
        except Exception as e:
            if self.is_running.is_set():
                print(f"Error in listening thread: {e}")
        finally:
            self.cleanup()

    def process_server_message(self, message):
        # (Keep the previous implementation from the last response)
        msg_type = message.get('type')
        
        if msg_type == 'WELCOME':
            print(f"Connected to the market successfully.")
        
        elif msg_type == 'LIST_RESPONSE':
            print("\n--- Current Market Inventory ---")
            inventory = message.get('inventory', {})
            if inventory:
                for item, amount in inventory.items():
                    print(f"{item.capitalize()}: {amount} units")
            else:
                print("No items in inventory.")
            print("------------------------------\n")
        
        elif msg_type == 'ITEM':
            print(f"\nNow selling: {message['item'].capitalize()} ({message['amount_left']} units)")
            print(f"Sale ends in {message['time_left']} seconds\n")
        
        elif msg_type == 'CONFIRM':
            print(f"\nPurchase confirmed: {message['amount_bought']} {message['item']} bought successfully!")
        
        elif msg_type == 'UPDATE':
            print(f"\nUpdated inventory: {message['item'].capitalize()} - {message['amount_left']} units left")
        
        elif msg_type == 'SOLD_OUT':
            print(f"\n{message['item'].capitalize()} is now sold out!")
        
        elif msg_type == 'FAIL':
            print(f"\nPurchase failed: {message.get('message', 'Unknown error')}")

if __name__ == "__main__":
    name = input("Enter your buyer name: ")
    buyer = BuyerClient(name)
    buyer.connect_to_market()