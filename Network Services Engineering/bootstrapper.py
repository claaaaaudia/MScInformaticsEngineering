import socket
import threading
import json
import time
import sys
import os
from message import Message


class Bootstrapper:
    def __init__(self, config_file='overlay_configs/config.json', host='0.0.0.0', port=5000):
        self.config_file = self.resolve_config_path(config_file)
        self.nodes = {}  # node_id -> (ip, port, last_seen)
        self.overlay_config = self.load_config()
        self.running = True
        self.host = host
        self.port = port

        # TCP socket for receiving registrations and sending updates
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        print(f"Bootstrapper running on {self.host}:{self.port}")
        print(f"Using config file: {self.config_file}")

    def resolve_config_path(self, config_file):
        """Resolve overlay config path, defaulting plain filenames to overlay_configs/."""
        if os.path.isabs(config_file) or os.path.dirname(config_file):
            return config_file

        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidate = os.path.join(base_dir, "overlay_configs", config_file)
        if os.path.exists(candidate):
            return candidate

        return config_file

    def load_config(self):
        """Load overlay configuration"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print(f"Successfully loaded config from {self.config_file}")
                return config
        except FileNotFoundError:
            print(f"Warning: Config file '{self.config_file}' not found. Using empty config.")
            return {"neighbors": {}}
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in config file '{self.config_file}': {e}")
            return {"neighbors": {}}

    def get_neighbors_from_config(self, node_name, node_ip):
        """Get neighbor IPs from config using (node_name, ip) tuple as key"""
        # Create the key in the format "(node_name, ip)"
        key = f"({node_name}, {node_ip})"
        return self.overlay_config.get("neighbors", {}).get(key, [])

    def handle_registration(self, message, client_address):
        """Process node registration using Message object"""
        try:
            # Extract node_id and port from message content
            node_id = message.content.get("node_id")
            port = message.content.get("port")
            
            # Get the client's IP from the address tuple
            client_ip = client_address[0]
            
            print(f"Node {node_id} registering from {client_ip}:{port}") 
            
            # Get ALL neighbors for this node_id across all IP addresses
            all_neighbors = []
            for key, neighbors in self.overlay_config.get("neighbors", {}).items():
                # Check if this key contains the node_id
                # Key format is "(node_name, ip)"
                if key.startswith(f"({node_id},"):
                    all_neighbors.extend(neighbors)
            
            # Remove duplicates while preserving order
            neighbor_ips = list(dict.fromkeys(all_neighbors))
            
            print(f"Found {len(neighbor_ips)} neighbors for {node_id}: {neighbor_ips}")
            
            # Create response message
            response_content = {
                "status": "success",
                "neighbors": neighbor_ips
            }
            response_msg = Message(
                msg_type="registration_response",
                node_id="bootstrapper",
                content=response_content
            )
            
            return response_msg.to_bytes()

        except Exception as e:
            print(f"Error processing registration: {e}")
            error_msg = Message(
                msg_type="registration_response",
                node_id="bootstrapper",
                content={"status": "error", "message": str(e)}
            )
            return error_msg.to_bytes()

    def handle_connection(self, conn, addr):
        """Handle individual client connection"""
        try:
            data = conn.recv(1024)
            if not data:
                return
            
            # Try to parse as Message object
            message = Message.from_bytes(data)
            if message and message.msg_type == Message.TYPE_REGISTRATION:
                response = self.handle_registration(message, addr)
                conn.send(response)

        except Exception as e:
            print(f"Error handling client {addr}: {e}")
        finally:
            conn.close()

    def start_boot(self):
        """Start bootstrap server"""
        print("Bootstrapper started, waiting for connections...")
        
        while self.running:
            try:
                self.sock.settimeout(1)
                conn, addr = self.sock.accept()
                
                # Handle each client in a separate thread
                client_thread = threading.Thread(
                    target=self.handle_connection,
                    args=(conn, addr),
                    daemon=True
                )
                client_thread.start()

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Bootstrapper error: {e}")

    def stop(self):
        """Stop the bootstrapper"""
        self.running = False
        self.sock.close()
        print("Bootstrapper stopped")

if __name__ == "__main__":
    # Parse command line arguments
    config_file = 'overlay_configs/config.json'  # default
    
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    
    print(f"\n{'='*60}")
    print(f"BOOTSTRAPPER STARTING")
    print(f"Config file: {config_file}")
    print(f"{'='*60}\n")
    
    server = Bootstrapper(config_file=config_file)
    try:
        server.start_boot()
    except KeyboardInterrupt:
        print("\nStopping bootstrapper...")
        server.stop()