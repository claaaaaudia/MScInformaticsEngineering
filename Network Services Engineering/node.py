import socket
import threading
import json
import time
import sys
from message import Message
from table import Parent, Child

class Node:
    def __init__(self, node_id, bootstrap_host, bootstrap_port=5000, node_port=6000, udp_port=7000):
        self.node_id = node_id
        self.bootstrap_host = bootstrap_host
        self.bootstrap_port = bootstrap_port
        self.node_port = node_port
        self.udp_port = udp_port
        self.neighbors = []
        self.alive_neighbors = []
        self.running = True
        self.rtt_measurements = {}
        self.rtt_pending = {}
        self.message_cache = set()
        self.past_measurements = []
        self.parent_table = []
        self.child_table = []  # Track children subscribed to streams
        self.frames_received = 0 
        
        # TCP socket for control messages on fixed port
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.tcp_socket.bind(('0.0.0.0', node_port))
        self.tcp_socket.listen(5)
        self.tcp_port = node_port
        
        # UDP socket for stream data
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)  # 4MB
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)  # 4MB
        self.udp_socket.bind(('0.0.0.0', udp_port))
        
        print(f"NÃ³ {self.node_id} iniciado na porta TCP {self.tcp_port} e UDP {self.udp_port}")
        
    def register(self):
        """Register with bootstrapper"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.bootstrap_host, self.bootstrap_port))
            
            registration_msg = Message.create_registration(self.node_id, self.tcp_port)
            sock.send(registration_msg.to_bytes())

            sock.settimeout(100)
            response_data = sock.recv(1024)
            response_msg = Message.from_bytes(response_data)

            if response_msg and response_msg.content.get("status") == "success":
                self.neighbors = response_msg.content.get("neighbors", [])
                print(f"Received {len(self.neighbors)} neighbors from bootstrapper: {self.neighbors}")
            else:
                error_msg = response_msg.content.get("message", "Unknown error") if response_msg else "No response"
                print(f"Registration failed: {error_msg}")
                return False
            
            sock.close()
            return True
        except Exception as e:
            print(f"Error registering with bootstrapper: {e}")
            return False

    def ping_neighbor(self, neighbor_ip, timeout=100):
        """Ping a neighbor to check if it's alive"""
        try:
            print(f"Pinging neighbor {neighbor_ip}")
            ping_msg = Message.create_ping(self.node_id)
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.settimeout(timeout)
            sock.connect((neighbor_ip, self.node_port))
            sock.send(ping_msg.to_bytes())
            
            response = sock.recv(1024)
            sock.close()
            
            if response:
                if neighbor_ip not in self.alive_neighbors:
                    self.alive_neighbors.append(neighbor_ip)
                    print(f"\n{'*'*60}")
                    print(f"Node {self.node_id}: Neighbor {neighbor_ip} is now alive!")
                    print(f"Updated alive neighbors: {self.alive_neighbors}")
                    print(f"{'*'*60}\n")
                else:
                    print(f"Neighbor {neighbor_ip} is alive")
            
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            print(f"Neighbor {neighbor_ip} did not respond: {e}")
        except Exception as e:
            print(f"Error pinging neighbor {neighbor_ip}: {e}")

    def check_alive_neighbors(self):
        """Check which neighbors from the list are alive"""
        print(f"Checking {len(self.neighbors)} neighbors...")
        self.alive_neighbors = []
        
        for neighbor_ip in self.neighbors:
            self.ping_neighbor(neighbor_ip)
        
        print(f"Found {len(self.alive_neighbors)} alive neighbors: {self.alive_neighbors}")

    def send_message_to_neighbors(self, message):
        """Send a Message object to all alive neighbors"""
        for neighbor_ip in self.alive_neighbors[:]:
            try:
                message.send_tcp(neighbor_ip, self.node_port)
            except Exception as e:
                print(f"Failed to send message to {neighbor_ip}: {e}")

    def measure_rtt_to_neighbor(self, neighbor_ip, timeout=100):
        """Measure RTT to a specific neighbor using TCP"""
        try:
            print(f"Starting RTT measurement to {neighbor_ip}...")
            start_time = time.time()
            
            rtt_msg = Message(
                msg_type=Message.TYPE_RTT_SEND,
                node_id=self.node_id,
                origin=self.node_id
            )
            
            self.rtt_pending[neighbor_ip] = start_time
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.settimeout(timeout)
            sock.connect((neighbor_ip, self.node_port))
            sock.send(rtt_msg.to_bytes())
            
            response_data = sock.recv(1024)
            sock.close()
            
            if response_data:
                response_msg = Message.from_bytes(response_data)
                if response_msg and response_msg.msg_type == Message.TYPE_RTT_REPLY:
                    rtt = (time.time() - start_time) * 1000
                    self.rtt_measurements[neighbor_ip] = rtt
                    print(f"RTT to {neighbor_ip}: {rtt:.2f} ms")
                    return rtt
            
            print(f"Invalid response from {neighbor_ip}")
            self.rtt_measurements[neighbor_ip] = float('inf')
            return float('inf')
                
        except socket.timeout:
            print(f"Timeout waiting for RTT response from {neighbor_ip}")
            self.rtt_measurements[neighbor_ip] = float('inf')
            return float('inf')
        except Exception as e:
            print(f"Error measuring RTT to {neighbor_ip}: {e}")
            self.rtt_measurements[neighbor_ip] = float('inf')
            return float('inf')
        finally:
            if neighbor_ip in self.rtt_pending:
                del self.rtt_pending[neighbor_ip]
    
    def measure_rtt_to_specified_neighbors(self, neighbors_to_measure):
        """Measure RTT to specified neighbors"""
        if not neighbors_to_measure:
            print("No neighbors to measure RTT for")
            return {}
        
        print(f"\nMeasuring RTT to {len(neighbors_to_measure)} neighbors: {neighbors_to_measure}")
        
        if len(neighbors_to_measure) == 1:
            results = {}
            for neighbor_ip in neighbors_to_measure:
                results[neighbor_ip] = self.measure_rtt_to_neighbor(neighbor_ip)
            return results
        else:
            results = {}
            threads = []
            results_lock = threading.Lock()
            
            def measure_and_store(neighbor_ip):
                rtt = self.measure_rtt_to_neighbor(neighbor_ip)
                with results_lock:
                    results[neighbor_ip] = rtt
            
            for neighbor_ip in neighbors_to_measure:
                thread = threading.Thread(target=measure_and_store, args=(neighbor_ip,))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
            
            return results

    def listen_for_messages(self):
        """Listens to other nodes' TCP control messages"""
        while self.running:
            try:
                self.tcp_socket.settimeout(1)
                conn, addr = self.tcp_socket.accept()
                
                # Handle each connection in separate thread
                handler = threading.Thread(
                    target=self._handle_tcp_connection,
                    args=(conn, addr),
                    daemon=True
                )
                handler.start()
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Failed to receive message: {e}")

    def _handle_tcp_connection(self, conn, addr):
        """Handle individual TCP connection in separate thread"""
        try:
            data = conn.recv(4096)
            message = Message.from_bytes(data)
            if message:
                self.handle_p2p_message(message, addr, conn)
            else:
                conn.close()
        except Exception as e:
            print(f"Error handling connection from {addr}: {e}")
            try:
                conn.close()
            except:
                pass

    def listen_for_stream_data(self):
        """Listen for UDP stream data and forward to children"""
        print(f"Started UDP listener on port {self.udp_port}")
        
        while self.running:
            try:
                self.udp_socket.settimeout(1)
                data, addr = self.udp_socket.recvfrom(65536)
                
                if data and len(data) > 4:
                    try:
                        # Parse packet format: [4 bytes header size][header JSON][video data]
                        header_size = int.from_bytes(data[:4], 'big')
                        
                        if len(data) >= 4 + header_size:
                            header_json = data[4:4+header_size]
                            video_data = data[4+header_size:]
                            
                            try:
                                stream_info = json.loads(header_json.decode('utf-8'))
                                stream_id = stream_info.get('stream_id', '')
                                frame_num = stream_info.get('frame_number', 0)
                                
                                self.frames_received += 1
                                
                                if self.frames_received % 100 == 0:  # Log every 100 frames
                                    print(f"[UDP] Received stream {stream_id} frame {frame_num} from {addr[0]}")
                                
                                # Forward to children subscribed to this stream
                                self.forward_stream_data(stream_id, data)
                                
                            except json.JSONDecodeError:
                                print(f"Invalid JSON header from {addr[0]}")
                        
                    except Exception as e:
                        print(f"Error parsing stream packet from {addr[0]}: {e}")
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Error receiving stream data: {e}")

    def forward_stream_data(self, stream_id, data):
        """Forward stream data to children subscribed to this stream"""
        forwarded = 0
        for child in self.child_table:
            if child.stream_id == stream_id and child.state == "A":  # Active state
                try:
                    self.udp_socket.sendto(data, (child.node_child, self.udp_port))
                    forwarded += 1
                except Exception as e:
                    print(f"Error forwarding stream to {child.node_child}: {e}")
        
        if forwarded > 0 and self.frames_received % 100 == 0:  # Log every 100 frames
            print(f"Forwarded stream {stream_id} to {forwarded} children")

    def count_active_children_for_stream(self, stream_id):
        """Count how many active children are subscribed to a specific stream"""
        count = 0
        for child in self.child_table:
            if child.stream_id == stream_id and child.state == "A":
                count += 1
        return count

    def get_parent_for_stream(self, stream_id):
        """Get the parent node for a specific stream from parent table"""
        for entry in self.parent_table:
            # Check if this parent can provide the requested stream
            if stream_id == entry.stream_id:
                return entry.node_parent
        return None

    def is_stream_active(self, stream_id):
        """Check if we're actively receiving a stream"""
        return len([c for c in self.child_table if c.stream_id == stream_id and c.state == "A"]) > 0

    def propagate_join_to_parent(self, stream_id, parent_ip=None):
        """Propagate JOIN message to parent for this stream"""

        if parent_ip is None:
            parent_ip = self.get_parent_for_stream(stream_id)

        if parent_ip:
            try:
                join_msg = Message.create_join(self.node_id, stream_id, self.udp_port)
                join_msg.send_tcp(parent_ip, self.node_port)
                print(f"Propagated JOIN to parent {parent_ip} for stream {stream_id}")
                
                # Update parent table entry
                for entry in self.parent_table:
                    if entry.node_parent == parent_ip and stream_id == entry.stream_id:
                        entry.state = "A"
                        break
                        
            except Exception as e:
                print(f"Error propagating JOIN to parent {parent_ip}: {e}")
        else:
            print(f"No active parent found for stream {stream_id} to propagate JOIN")

    def propagate_leave_to_parent(self, stream_id):
        """Propagate LEAVE message to parent for this stream"""
        parent_ip = self.get_parent_for_stream(stream_id)
        if parent_ip:
            try:
                leave_msg = Message.create_leave(self.node_id, stream_id)
                leave_msg.send_tcp(parent_ip, self.node_port)
                print(f"Propagated LEAVE to parent {parent_ip} for stream {stream_id}")
                
                # Update parent table entry
                for entry in self.parent_table:
                    if entry.node_parent == parent_ip and stream_id == entry.stream_id:
                        entry.state = "D"
                        break
                        
            except Exception as e:
                print(f"Error propagating LEAVE to parent {parent_ip}: {e}")
        else:
            print(f"No active parent found for stream {stream_id} to propagate LEAVE")

    def update_table(self, parent_id, flood_id, latency, streams):
        """Updates the parent table when receiving a flood message - one entry per stream"""
        origin, flood_current = flood_id.split("_", 1)
        
        # Create one entry for each stream in the flood
        for stream_id in streams:
            new_entry = Parent(
                node_parent=parent_id, 
                flood_id=flood_id, 
                stream_id=stream_id,
                state="D",  # Default to inactive
                latency=latency
            )
            added_entry = False

            # Remove outdated measurements from past_measurements
            for entry in self.past_measurements[:]:
                entry_origin, flood_num = entry.flood_id.split("_", 1)
                if entry_origin == origin and flood_num != flood_current and entry.stream_id == stream_id:
                    self.past_measurements.remove(entry)

            # Check if we already have an entry for this stream from this origin
            for entry in self.parent_table[:]:
                entry_origin, flood_num = entry.flood_id.split("_", 1)
                
                if entry_origin == origin and entry.stream_id == stream_id:
                    added_entry = True
                    
                    if flood_num != flood_current:
                        # Newer flood received - check if this is our current parent
                        is_current_parent = (entry.node_parent == parent_id and entry.state == "A")
                        
                        # Replace entry
                        self.parent_table.remove(entry)
                        
                        # Preserve active state if it's the same parent
                        if is_current_parent:
                            new_entry.state = "A"
                            print(f"Received newer flood {flood_current} from current parent {parent_id} for stream {stream_id}.")
                            print(f"Preserving active state.")
                        else:
                            new_entry.state = "D"
                            print(f"Received newer flood {flood_current} from origin {origin} for stream {stream_id}.")
                            print(f"Replacing outdated entry (flood {flood_num}).")
                        
                        self.parent_table.append(new_entry)
                        print(f"New latency: {latency:.2f} ms")
                    
                    else:
                        # Same flood, check if this path is better
                        if latency < entry.latency:
                            old_latency = entry.latency
                            is_current = (entry.state == "A")  # Is the current entry active?
                            
                            self.parent_table.remove(entry)
                            self.past_measurements.append(entry)
                            
                            # If the current parent is active, mark the new one as active too
                            if is_current:
                                new_entry.state = "A"
                                print(f"Found better parent for stream {stream_id} (flood {flood_id})!")
                                print(f"Previous latency: {old_latency:.2f} ms (via {entry.node_parent})")
                                print(f"New latency: {latency:.2f} ms (via {parent_id})")
                                print(f"Switching to new parent.")
                            else:
                                print(f"Found better alternative for stream {stream_id}")
                                print(f"Current best: {entry.latency:.2f} ms via {entry.node_parent}")
                                print(f"Alternative: {latency:.2f} ms via {parent_id}")
                            
                            self.parent_table.append(new_entry)
                        else:
                            # This path is worse or equal, just store it as a past measurement
                            self.past_measurements.append(new_entry)
                            print(f"Received measurement for stream {stream_id}: {latency:.2f} ms via {parent_id} \n Not better than current best: {entry.latency:.2f} ms via {entry.node_parent}")

            if not added_entry:
                self.parent_table.append(new_entry)
                print(f"First flood received from origin {origin} for stream {stream_id}.")
                print(f"Adding parent: {parent_id} with latency {latency:.2f} ms")

        self.print_parent_table()
        
    def print_parent_table(self):
        """Print the parent table in a formatted way"""
        if not self.parent_table:
            print("\n Parent Table: EMPTY")
            return
        
        print("\n" + "="*80)
        print(f" PARENT TABLE - Node {self.node_id}")
        print("="*80)
        print(f"{'Parent IP':<20} {'Flood ID':<15} {'Stream ID':<25} {'State':<8} {'Latency (ms)':<15}")
        print("-"*80)
        
        for entry in self.parent_table:
            latency_str = f"{entry.latency:.2f}" if entry.latency != float('inf') else "INF"
            stream_str = entry.stream_id[:22] + "..." if len(entry.stream_id) > 25 else entry.stream_id
            state_str = "A" if entry.state == "A" else "D"
            print(f"{entry.node_parent:<20} {entry.flood_id:<15} {stream_str:<25} {state_str:<8} {latency_str:<15}")
        
        print("="*80 + "\n")

    def print_child_table(self):
        """Print the child table in a formatted way"""
        if not self.child_table:
            print("\n Child Table: EMPTY")
            return
        
        print("\n" + "="*80)
        print(f" CHILD TABLE - Node {self.node_id}")
        print("="*80)
        print(f"{'Child IP':<20} {'Stream ID':<25} {'State':<10}")
        print("-"*80)
        
        active_count = 0
        total_count = 0
        streams = {}
        
        for child in self.child_table:
            total_count += 1
            if child.state == "A":
                active_count += 1
                if child.stream_id not in streams:
                    streams[child.stream_id] = 0
                streams[child.stream_id] += 1
            
            stream_str = child.stream_id[:22] + "..." if len(child.stream_id) > 25 else child.stream_id
            state_str = "A" if child.state == "A" else "D"
            print(f"{child.node_child:<20} {stream_str:<25} {state_str:<10}")
        
        print("-"*80)
        print(f"Total children: {total_count}")
        print(f"Active children: {active_count}")
        if streams:
            print("Active streams: " + ", ".join([f"{stream}: {count}" for stream, count in streams.items()]))
        print("="*80 + "\n")

    def count_child_stats(self):
        """Count active and total children"""
        active = 0
        total = 0
        streams = {}
        
        for child in self.child_table:
            total += 1
            if child.state == "A":
                active += 1
                if child.stream_id not in streams:
                    streams[child.stream_id] = 0
                streams[child.stream_id] += 1
        
        return active, total, streams

    def handle_parent_shutdown(self, shutting_down_ip, parent_ip):
        """Handle a parent node shutting down.
        
        Simple rule: If the dead node was our parent (for any stream, active or not),
        we inherit its parent to maintain tree connectivity.
        (Override in Client class for client-specific behavior)
        """
        print(f"\n{'!'*60}")
        print(f"HANDLING PARENT SHUTDOWN - Node {self.node_id}")
        print(f"{'!'*60}")
        print(f"Shutting down node: {shutting_down_ip}")
        print(f"Dead node's parent: {parent_ip}")
        
        # Ensure parent_ip is a single string, not a list
        dead_parent_parent = parent_ip
        if isinstance(dead_parent_parent, list):
            if dead_parent_parent:
                dead_parent_parent = dead_parent_parent[0]  # Use first alternative
                print(f"Multiple alternatives provided, using first: {dead_parent_parent}")
            else:
                dead_parent_parent = None
        
        # Remove dead node from neighbors and alive_neighbors lists
        if shutting_down_ip in self.neighbors:
            self.neighbors.remove(shutting_down_ip)
            print(f"Removed {shutting_down_ip} from neighbors list")
        if shutting_down_ip in self.alive_neighbors:
            self.alive_neighbors.remove(shutting_down_ip)
            print(f"Removed {shutting_down_ip} from alive_neighbors list")
        
        # Remove the dead node from our children table (if we had it as a child)
        for child in self.child_table[:]:
            if child.node_child == shutting_down_ip:
                self.child_table.remove(child)
                print(f"Removed dead node {shutting_down_ip} from our children table")
        
        # Find which streams had the dead node as parent (any state)
        affected_streams = {}  # stream_id -> (original_state, flood_id)
        for entry in self.parent_table[:]:
            if entry.node_parent == shutting_down_ip:
                affected_streams[entry.stream_id] = (entry.state, entry.flood_id)
                self.parent_table.remove(entry)
                print(f"Stream {entry.stream_id} was using {shutting_down_ip} (state: {entry.state})")
        
        # If this node had the dead node as a parent, inherit the dead node's parent
        if affected_streams:
            print(f"\nDead node WAS a parent for {len(affected_streams)} stream(s)")
            print(f"Inheriting dead node's parent: {dead_parent_parent}")
            
            if dead_parent_parent:
                # Add new parent to alive_neighbors if not already there
                if dead_parent_parent not in self.alive_neighbors:
                    self.alive_neighbors.append(dead_parent_parent)
                    print(f"Added {dead_parent_parent} to alive_neighbors")
                # Send ping to notify the new parent of the connection
                self.ping_neighbor(dead_parent_parent)
                
                # Connect to dead parent's parent for all affected streams
                # Preserve original state: only set to "A" if it was "A" before
                for stream_id, (original_state, flood_id) in affected_streams.items():
                    new_state = original_state  # Keep original state (A or D)
                    print(f"  Stream {stream_id}: Connecting to {dead_parent_parent} (preserving state: {original_state})")
                    
                    new_entry = Parent(
                        node_parent=dead_parent_parent,
                        flood_id=flood_id,  # Use same flood as the dead parent had
                        stream_id=stream_id,
                        state=new_state,  # Preserve original state
                        latency=float('inf')  # Will be updated when floods arrive
                    )
                    self.parent_table.append(new_entry)
                    
                    # Only propagate JOIN if stream was previously active
                    if original_state == "A":
                        self.propagate_join_to_parent(stream_id, parent_ip=dead_parent_parent)
            else:
                print(f"  No parent info available - waiting for flood messages")
            
            print(f"{'!'*60}\n")
            return
        
        # Otherwise, check if we're a neighbor of the dead node with children
        print(f"Dead node was NOT a parent of this node")
        
        if self.child_table:
            active_child_streams = set()
            for child in self.child_table:
                if child.state == "A":
                    active_child_streams.add(child.stream_id)
            
            if active_child_streams:
                print(f"But we have {len(active_child_streams)} active streams with children")
                print(f"As a neighbor of the dead node, connecting to its parent for connectivity")
                
                if dead_parent_parent:
                    for stream_id in active_child_streams:
                        # Check if we already have a parent for this stream
                        current_parent = self.get_parent_for_stream(stream_id)
                        if current_parent:
                            print(f"  Stream {stream_id}: Already have parent {current_parent}, skipping")
                            continue
                        
                        print(f"  Stream {stream_id}: Connecting to dead node's parent {dead_parent_parent}")
                        new_entry = Parent(
                            node_parent=dead_parent_parent,
                            flood_id=f"fallback_from_{shutting_down_ip}",
                            stream_id=stream_id,
                            state="A",
                            latency=float('inf')
                        )
                        self.parent_table.append(new_entry)
                        self.propagate_join_to_parent(stream_id, parent_ip=dead_parent_parent)
                else:
                    print(f"  No dead parent info available - waiting for floods")
        
        print(f"{'!'*60}\n")

    def handle_p2p_message(self, message, addr, conn):
        """Handle all P2P messages""" 
        try:
            if message.msg_type == Message.TYPE_PING:
                pong_msg = Message(
                    msg_type=Message.TYPE_PONG,
                    node_id=self.node_id
                )
                conn.send(pong_msg.to_bytes())
                conn.close()
                
                pinger_ip = addr[0]
                if pinger_ip not in self.alive_neighbors:
                    self.alive_neighbors.append(pinger_ip)
                    print(f"\n{'*'*60}")
                    print(f"Node {self.node_id}: Neighbor {pinger_ip} is now alive!")
                    print(f"Updated alive neighbors: {self.alive_neighbors}")
                    print(f"{'*'*60}\n")
                
                return
            
            elif message.msg_type == Message.TYPE_RTT_SEND:
                print(f"Received RTT request from {addr[0]}")
                rtt_reply = Message(
                    msg_type=Message.TYPE_RTT_REPLY,
                    node_id=self.node_id,
                    origin=self.node_id
                )
                conn.send(rtt_reply.to_bytes())
                conn.close()
                print(f"Sent RTT reply to {addr[0]}")
                return
            
            elif message.msg_type == Message.TYPE_SHUTDOWN:
                conn.close()
                neighbor_ip = addr[0]
                
                parent_ip = None
                if message.content:
                    parent_ip = message.content.get("parent_ip")
                
                if neighbor_ip in self.alive_neighbors:
                    self.alive_neighbors.remove(neighbor_ip)
                
                # Handle parent shutdown with explicit parent IP
                self.handle_parent_shutdown(neighbor_ip, parent_ip)
                print(f"Neighbor {neighbor_ip} has shutdown!")
                # Print parent table after shutdown handling for clarity
                self.print_parent_table()
                return
            
            elif message.msg_type == Message.TYPE_JOIN:
                conn.close()
                stream_id = message.content.get("stream_id", "")
                udp_port = message.content.get("udp_port", self.udp_port)
                child_ip = addr[0]
                
                print(f"\n{'='*60}")
                print(f"JOIN REQUEST - Node {self.node_id}")
                print(f"{'='*60}")
                print(f"From: {child_ip}")
                print(f"Stream: {stream_id}")
                print(f"UDP Port: {udp_port}")
                
                # Count active children BEFORE adding this one
                active_before = self.count_active_children_for_stream(stream_id)
                
                # Check if this child already exists in table (checking both IP and stream)
                child_exists = False
                for child in self.child_table:
                    if child.node_child == child_ip and child.stream_id == stream_id:
                        # Child already exists - only reactivate if it was deactivated
                        if child.state == "D":
                            child.state = "A"
                            print(f"Reactivated existing child {child_ip} for stream {stream_id}")
                        else:
                            print(f"Child {child_ip} for stream {stream_id} is already active")
                        child_exists = True
                        break
                
                # Add new child only if it doesn't exist
                if not child_exists:
                    new_child = Child(node_child=child_ip, stream_id=stream_id, state="A")
                    self.child_table.append(new_child)
                    print(f"Added new child {child_ip} to child table for stream {stream_id}")
                else:
                    # Double-check: count active children for this exact stream to avoid duplicates
                    active_count = 0
                    for c in self.child_table:
                        if c.stream_id == stream_id and c.state == "A" and c.node_child == child_ip:
                            active_count += 1
                    if active_count > 1:
                        print(f"WARNING: Multiple active entries for same child {child_ip} detected - cleaning up")
                        # Keep only the first one, mark others as deactivated
                        found_first = False
                        for c in self.child_table:
                            if c.stream_id == stream_id and c.node_child == child_ip:
                                if not found_first:
                                    c.state = "A"
                                    found_first = True
                                else:
                                    c.state = "D"
                
                # Print updated child table
                self.print_child_table()
                
                # Only propagate JOIN if this is the first active child for this stream
                if active_before == 0:
                    print(f"First child for stream {stream_id} - propagating JOIN to parent")
                    self.propagate_join_to_parent(stream_id)
                else:
                    print(f"Already have {active_before} active children for stream {stream_id} - no need to propagate")
                
                print(f"{'='*60}\n")
                return
            
            elif message.msg_type == Message.TYPE_LEAVE:
                conn.close()
                stream_id = message.content.get("stream_id", "")
                child_ip = addr[0]
                
                print(f"\n{'='*60}")
                print(f"LEAVE REQUEST - Node {self.node_id}")
                print(f"{'='*60}")
                print(f"From: {child_ip}")
                print(f"Stream: {stream_id}")
                
                # Find and deactivate the child (change state to "D")
                child_found = False
                for child in self.child_table:
                    if child.node_child == child_ip and child.stream_id == stream_id:
                        child.state = "D"
                        child_found = True
                        print(f"Deactivated child {child_ip} for stream {stream_id}")
                        break
                
                if not child_found:
                    print(f"Warning: Child {child_ip} not found in table for stream {stream_id}")
                
                # Print updated child table
                self.print_child_table()
                
                # Count remaining active children for this stream
                active_remaining = self.count_active_children_for_stream(stream_id)
                
                # Only propagate LEAVE if no more active children for this stream
                if active_remaining == 0:
                    print(f"No more active children for stream {stream_id} - propagating LEAVE to parent")
                    self.propagate_leave_to_parent(stream_id)
                else:
                    print(f"Still have {active_remaining} active children for stream {stream_id} - not propagating LEAVE")
                
                print(f"{'='*60}\n")
                return
            
            elif message.msg_type == Message.TYPE_FLOOD:
                conn.close()
                
                print(f"\n{'='*60}")
                print(f"Node {self.node_id} received FLOOD")
                print(f"{'='*60}")
                
                if message.content:
                    flood_id = message.content.get("flood_id", "unknown")
                    latency = message.content.get("latency", "unknown")
                    streams = message.content.get("streams", [])
                    sender_ip = addr[0]
                    
                    print(f"Flood ID: {flood_id}")
                    print(f"From: {sender_ip}")
                    print(f"Latency: {latency} ms")
                    print(f"Streams: {streams if streams else 'None'}")
                    
                    # Check if we've already seen this exact flood from this parent
                    origin, flood_num = flood_id.split("_", 1)
                    already_seen = False
                    
                    # Check parent table
                    for entry in self.parent_table:
                        entry_origin, entry_flood = entry.flood_id.split("_", 1)
                        if entry_origin == origin and entry_flood == flood_num and entry.node_parent == sender_ip:
                            already_seen = True
                            print(f"Already processed this flood from {sender_ip} - dropping to prevent loop")
                            break
                    
                    # Check past measurements if not found
                    if not already_seen:
                        for entry in self.past_measurements:
                            entry_origin, entry_flood = entry.flood_id.split("_", 1)
                            if entry_origin == origin and entry_flood == flood_num and entry.node_parent == sender_ip:
                                already_seen = True
                                print(f"Already measured this flood from {sender_ip} - dropping to prevent loop")
                                break
                    
                    if already_seen:
                        print(f"{'='*60}\n")
                        return

                    # Update table with this path for each stream
                    if streams:
                        self.update_table(sender_ip, flood_id, latency, streams)
                    
                        # Check if we have children waiting for any of these streams
                        for stream_id in streams:
                            waiting_children = [c for c in self.child_table if c.stream_id == stream_id and c.state == "A"]
                            if waiting_children and not self.get_parent_for_stream(stream_id):
                                print(f"Auto-JOINING stream {stream_id} for {len(waiting_children)} waiting children")
                                self.propagate_join_to_parent(stream_id)
                    
                    print(f"\nPhase 1: Measuring RTT to our neighbors...")
                    
                    # Get neighbors to contact: all alive neighbors except sender
                    neighbors_to_contact = [ip for ip in self.alive_neighbors if ip != sender_ip]
                    
                    # Get current best parents for this flood and remove them from forwarding
                    origin, flood_num = flood_id.split("_", 1)
                    for entry in self.parent_table:
                        entry_origin, entry_flood = entry.flood_id.split("_", 1)
                        if entry_origin == origin and entry_flood == flood_num:
                            if entry.node_parent in neighbors_to_contact:
                                neighbors_to_contact.remove(entry.node_parent)
                                print(f"  Excluding parent {entry.node_parent} (already in parent table for stream {entry.stream_id})")
                    
                    # Remove any past measurement entries for this flood
                    for entry in self.past_measurements:
                        entry_origin, entry_flood = entry.flood_id.split("_", 1)
                        if entry_origin == origin and entry_flood == flood_num:
                            if entry.node_parent in neighbors_to_contact:
                                neighbors_to_contact.remove(entry.node_parent)
                                print(f"  Excluding neighbor {entry.node_parent} (already in past measurements for stream {entry.stream_id})")
                    
                    rtt_results = self.measure_rtt_to_specified_neighbors(neighbors_to_contact)
                    
                    if neighbors_to_contact:
                        print(f"\nPhase 2: Forwarding to {len(neighbors_to_contact)} neighbors...")
                        forwarded_count = 0
                        
                        for neighbor_ip in neighbors_to_contact:
                            try:
                                # Calculate total latency for this path
                                neighbor_rtt = rtt_results.get(neighbor_ip, float("inf"))
                                total_latency = message.content.get("latency", 0) + neighbor_rtt
                                
                                forward_content = {
                                    **message.content,
                                    "latency": total_latency,
                                }
                                
                                forward_msg = Message(
                                    msg_type=Message.TYPE_FLOOD,
                                    node_id=self.node_id,
                                    content=forward_content,
                                    msg_id=message.msg_id,
                                )
                                
                                forward_msg.send_tcp(neighbor_ip, self.node_port)
                                forwarded_count += 1
                                
                                if neighbor_rtt == float('inf'):
                                    print(f"  To {neighbor_ip}: No RTT measurement (unreachable)")
                                else:
                                    print(f"  To {neighbor_ip}: RTT {neighbor_rtt:.2f} ms, Total: {total_latency:.2f} ms")
                                
                            except Exception as e:
                                print(f"  Failed to forward to {neighbor_ip}: {e}")
                        
                        print(f"\nFlood forwarded to {forwarded_count}/{len(neighbors_to_contact)} neighbors")
                    else:
                        print(f"\nNo neighbors to forward to")
                    
                    print(f"{'='*60}\n")
                
                return
            
            else:
                print(f"Received unknown message type: {message.msg_type}")
                conn.close()
                
        except Exception as e:
            print(f"Error processing message: {e}")
            conn.close()

    def start_node(self):
        """Initiate node"""
        if not self.register():
            print(f"Error registering with the bootstrapper.")
            return


        # Start TCP listener
        tcp_listener_thread = threading.Thread(target=self.listen_for_messages, daemon=True)
        tcp_listener_thread.start()

        # Start UDP listener
        udp_listener_thread = threading.Thread(target=self.listen_for_stream_data, daemon=True)
        udp_listener_thread.start()
        
        print(f"\n{'*'*60}")
        print(f"Node {self.node_id} completely initialized")
        print(f"TCP Port: {self.tcp_port}")
        print(f"UDP Port: {self.udp_port}")
        print(f"Alive neighbors: {self.alive_neighbors}")
        print(f"Child table status:")
        self.print_child_table()
        print(f"{'*'*60}\n")
        
        self.check_alive_neighbors()

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\nStopping node {self.node_id}")
            self.stop_node()

    def stop_node(self):
        """Stops node"""
        self.running = False
        
        # Send LEAVE for all active streams
        active_streams = {}
        for child in self.child_table:
            if child.state == "A":
                active_streams[child.stream_id] = True
        
        for stream_id in active_streams:
            self.propagate_leave_to_parent(stream_id)
        
        try:
            # Get this node's parent to send in shutdown message
            parent_ip = None
            if self.parent_table:
                parent_ip = self.parent_table[0].node_parent
            
            # Include alive neighbors and parent IP in shutdown message
            shutdown_msg = Message.create_shutdown(self.node_id, self.alive_neighbors, parent_ip)
            self.send_message_to_neighbors(shutdown_msg)
        except Exception as e:
            print(f"Error warning neighbors: {e}")
        
        self.tcp_socket.close()
        self.udp_socket.close()
        print(f"Node {self.node_id} stopped")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python3 node.py <node_id> <bootstrapper_ip> [node_port] [udp_port]")
        sys.exit(1)

    node_id = sys.argv[1]
    bootstrap_ip = sys.argv[2]
    node_port = int(sys.argv[3]) if len(sys.argv) > 3 else 6000
    udp_port = int(sys.argv[4]) if len(sys.argv) > 4 else 7000
    
    node = Node(node_id, bootstrap_ip, bootstrap_port=5000, node_port=node_port, udp_port=udp_port)
    node.start_node()