import json
import time
import socket

class Message:
    """Handles message creation, serialization, and sending"""
    
    # Message types
    TYPE_REGISTRATION = "registration"
    TYPE_SHUTDOWN = "shutdown"
    TYPE_PING = "ping"
    TYPE_PONG = "pong"
    TYPE_FLOOD = "flood"
    TYPE_RTT_SEND = "rtt_send"
    TYPE_RTT_REPLY = "rtt_reply"
    TYPE_JOIN = "join"
    TYPE_LEAVE = "leave"
    
    def __init__(self, msg_type, node_id, content=None, msg_id=None, origin=None):
        """
        Initialize a message:
            msg_type: Type of message (shutdown, neighbor_update, etc.)
            node_id: ID of the node sending the message
            content: Optional message content
            msg_id: Optional unique message ID (auto-generated if not provided)
            origin: Optional origin node ID (defaults to node_id)
        """
        self.msg_type = msg_type
        self.node_id = node_id
        self.content = content
        self.msg_id = msg_id if msg_id else f"{node_id}_{time.time()}"
        self.origin = origin if origin else node_id
        self.timestamp = time.time()
    
    def to_dict(self):
        """Convert message to dictionary"""
        msg_dict = {
            "type": self.msg_type,
            "node_id": self.node_id,
            "msg_id": self.msg_id,
            "origin": self.origin,
            "timestamp": self.timestamp
        }
        
        if self.content is not None:
            msg_dict["content"] = self.content
        
        return msg_dict
    
    def to_json(self):
        """Serialize message to JSON string"""
        return json.dumps(self.to_dict())
    
    def to_bytes(self):
        """Serialize message to bytes"""
        return self.to_json().encode("utf-8")
    
    @staticmethod
    def from_bytes(data):
        """
        Deserialize message from bytes
        
        Args:
            data: Bytes containing JSON message
            
        Returns:
            Message object or None if deserialization fails
        """
        try:
            msg_dict = json.loads(data.decode("utf-8"))
            return Message.from_dict(msg_dict)
        except Exception as e:
            print(f"Error deserializing message: {e}")
            return None
    
    @staticmethod
    def from_dict(msg_dict):
        """
        Create Message object from dictionary
        
        Args:
            msg_dict: Dictionary containing message data
            
        Returns:
            Message object
        """
        msg = Message(
            msg_type=msg_dict.get("type"),
            node_id=msg_dict.get("node_id"),
            content=msg_dict.get("content"),
            msg_id=msg_dict.get("msg_id"),
            origin=msg_dict.get("origin")
        )
        msg.timestamp = msg_dict.get("timestamp", time.time())
        return msg
    
    @staticmethod
    def create_registration(node_id, port):
        """Create a registration message for bootstrapper"""
        content = {
            "node_id": node_id,
            "port": port
        }
        return Message(Message.TYPE_REGISTRATION, node_id, content=content)
    
    @staticmethod
    def create_shutdown(node_id, alive_neighbors=None, parent_ip=None):
        """Create a shutdown notification message with alive neighbors and parent IP"""
        content = {
            "alive_neighbors": alive_neighbors if alive_neighbors else [],
            "parent_ip": parent_ip  # Explicitly send the parent IP
        }
        return Message(Message.TYPE_SHUTDOWN, node_id, content=content)
    
    @staticmethod
    def create_ping(node_id):
        """Create a ping message"""
        return Message(Message.TYPE_PING, node_id)
    
    @staticmethod
    def create_join(node_id, stream_id, udp_port):
        """Create a JOIN message for stream subscription"""
        content = {
            "stream_id": stream_id,
            "udp_port": udp_port
        }
        return Message(Message.TYPE_JOIN, node_id, content=content)
    
    @staticmethod
    def create_leave(node_id, stream_id):
        """Create a LEAVE message to unsubscribe from stream"""
        content = {
            "stream_id": stream_id
        }
        return Message(Message.TYPE_LEAVE, node_id, content=content)
    
    def create_rtt(node_id, neighbor):
        """Check round-trip-time"""
        content = {}
        return Message(Message.TYPE_RTT_SEND, node_id)
    
    def create_rtt_reply(node_id):
        """Create an RTT reply message"""
        return Message(Message.TYPE_RTT_REPLY, node_id)
    
    def send_tcp(self, ip, port, timeout=100):
        """
        Send this message via TCP (all control messages use TCP):
            ip: Destination IP address
            port: Destination port
            timeout: Connection timeout in seconds
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.settimeout(timeout)
            sock.connect((ip, int(port)))
            sock.send(self.to_bytes())
            sock.close()
            return True
        except Exception as e:
            print(f"Error sending TCP message to {ip}:{port}: {e}")
            return False
    
    def __str__(self):
        """String representation of message"""
        return f"Message(type={self.msg_type}, id={self.msg_id}, from={self.origin})"
    
    def __repr__(self):
        return self.__str__()