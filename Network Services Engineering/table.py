import socket
import threading
import json
import time
import sys

class Parent:
    def __init__(self, node_parent = "", flood_id = "", stream_id = "", state = "D", latency = 0.0):
        self.node_parent = node_parent
        self.flood_id = flood_id
        self.stream_id = stream_id
        self.state = state
        self.latency = latency

class Child:
    def __init__(self, node_child = "", stream_id = "", state = "D"):
        self.node_child = node_child
        self.state = state
        self.stream_id = stream_id