import socket
import threading
import json
import time
import sys
import os
import subprocess
import struct
from node import Node
from message import Message
from table import Parent

# Note: before initializing the client, the command is required: export DISPLAY=:0.0

class Client(Node):
    def __init__(self, node_id, bootstrap_host, stream_id, bootstrap_port=5000, node_port=6000, udp_port=7000):
        super().__init__(node_id, bootstrap_host, bootstrap_port, node_port, udp_port)
        self.stream_id = stream_id
        self.current_parent = None
        self.frames_received = 0
        self.bytes_received = 0
        self.last_frame_time = None
        self.receiving = False
        self.joined = False
        self.ffplay_process = None
        self.ffplay_started = False
        self.ffplay_pipe = None  # For piping data to ffplay

        # Robust receive buffer for UDP app-layer packets
        self._recv_buffer = bytearray()
        self._recv_lock = threading.Lock()
        self._reset_frame_tracking = False  # Flag to reset frame number tracking

        print(f"Client {self.node_id} initialized")
        print(f"  - Watching stream: {self.stream_id}")
        print(f"  - UDP Port for streaming: {self.udp_port}")

    def start_ffplay_pipe(self):
        """Start ffplay with pipe input for continuous streaming"""
        if self.ffplay_started and self.ffplay_process and self.ffplay_process.poll() is None:
            # already running
            return

        # If we have a dead process, clean it up
        try:
            if self.ffplay_process:
                try:
                    self.ffplay_process.kill()
                except:
                    pass
                self.ffplay_process = None
                self.ffplay_started = False
                self.ffplay_pipe = None
        except Exception:
            pass

        try:
            # Try to find ffplay executable
            ffplay_paths = ['ffplay', '/usr/bin/ffplay', '/usr/local/bin/ffplay']
            ffplay_exec = None

            for path in ffplay_paths:
                try:
                    result = subprocess.run([path, '-version'],
                                            capture_output=True,
                                            timeout=5)
                    if result.returncode == 0:
                        ffplay_exec = path
                        break
                except:
                    continue

            if not ffplay_exec:
                print("[ffplay] ERROR: ffplay not found")
                return

            # ffplay command for MJPEG stream from pipe
            ffplay_cmd = [
                ffplay_exec,
                '-window_title', f'Stream: {self.stream_id} - Client: {self.node_id}',
                '-f', 'mjpeg',  # Input format is MJPEG
                '-i', 'pipe:0',  # Read from stdin
                '-framerate', '30',
                '-autoexit',
                '-loglevel', 'warning'
            ]

            print(f"\n{'@'*60}")
            print(f"STARTING FFPLAY PLAYER")
            print(f"{'@'*60}\n")

            # Start ffplay with stdin pipe
            self.ffplay_process = subprocess.Popen(
                ffplay_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            self.ffplay_pipe = self.ffplay_process.stdin

            # Check if process started
            time.sleep(0.5)
            if self.ffplay_process.poll() is not None:
                print(f"[ffplay] ERROR: ffplay exited immediately (rc={self.ffplay_process.poll()})")
                self.ffplay_started = False
                self.ffplay_pipe = None
                return

            self.ffplay_started = True
            print(f"[ffplay] ffplay player started (PID: {self.ffplay_process.pid})")

        except Exception as e:
            print(f"[ffplay] ERROR starting ffplay: {e}")
            import traceback
            traceback.print_exc()
            self.ffplay_started = False
            self.ffplay_pipe = None

    def _ensure_ffplay(self):
        """Ensure ffplay is running; start it if not."""
        if not (self.ffplay_started and self.ffplay_process and self.ffplay_process.poll() is None):
            print("[ffplay] Not running - (re)starting ffplay")
            self.start_ffplay_pipe()
            # small sleep to let it come up
            time.sleep(0.2)

    def write_to_ffplay_pipe(self, video_data):
        """Write video data to ffplay's stdin pipe"""
        # Ensure ffplay is available
        self._ensure_ffplay()

        if self.ffplay_pipe and not self.ffplay_pipe.closed:
            try:
                # Write each JPEG frame directly to ffplay
                self.ffplay_pipe.write(video_data)
                self.ffplay_pipe.flush()
            except BrokenPipeError:
                print("[ffplay] Pipe broken, ffplay may have crashed. Will restart on next frame.")
                self.ffplay_started = False
                try:
                    if self.ffplay_pipe:
                        self.ffplay_pipe.close()
                except:
                    pass
                self.ffplay_pipe = None
                self.ffplay_process = None
            except Exception as e:
                print(f"[ffplay] Error writing to pipe: {e}")
                # best-effort restart later
                self.ffplay_started = False
                try:
                    if self.ffplay_pipe:
                        self.ffplay_pipe.close()
                except:
                    pass
                self.ffplay_pipe = None
                self.ffplay_process = None
        else:
            # no pipe - try starting and writing again next time
            self.ffplay_started = False
            self.ffplay_pipe = None
            self.ffplay_process = None

    def listen_for_stream_data(self):
        """Listen for UDP stream data and send to ffplay (robust buffered parser)"""
        print(f"Started UDP listener on port {self.udp_port}")
        print(f"Listening for stream: {self.stream_id}")

        packet_count = 0
        last_frame_time = time.time()
        last_frame_number = None
        seen_loops = 0

        # Ensure socket timeout set (non-blocking-ish)
        try:
            self.udp_socket.settimeout(1.0)
        except Exception:
            pass

        while self.running:
            try:
                try:
                    data, addr = self.udp_socket.recvfrom(65536)
                except socket.timeout:
                    # Regular heartbeat
                    # If we haven't received frames in a while, log as watchdog
                    if self.receiving and (time.time() - (self.last_frame_time or 0)) > 5:
                        print("[CLIENT] WARNING: No frames received for >5s")
                    continue

                if not data:
                    continue

                packet_count += 1
                if packet_count <= 10:
                    print(f"Packet {packet_count}: {len(data)} bytes from {addr[0]}")

                # Append datagram to per-client recv buffer and try to parse as many app-packets as possible
                with self._recv_lock:
                    self._recv_buffer += data

                    # parse loop
                    while True:
                        # Need at least 4 bytes for header size
                        if len(self._recv_buffer) < 4:
                            break

                        # Peek 4-byte header size (big-endian)
                        header_size = int.from_bytes(self._recv_buffer[0:4], 'big')

                        # Sanity: header_size shouldn't be ridiculously large
                        if header_size <= 0 or header_size > 65536:
                            # Corrupt header_size -> attempt resync by dropping one byte
                            print(f"[CLIENT] Corrupt header_size={header_size}, resyncing (dropping 1 byte)")
                            del self._recv_buffer[0]
                            continue

                        # Need header bytes present
                        if len(self._recv_buffer) < 4 + header_size:
                            # wait for more bytes from next recv
                            break

                        # Extract header JSON bytes
                        header_json_bytes = bytes(self._recv_buffer[4:4 + header_size])

                        # Try to parse header JSON
                        try:
                            header = json.loads(header_json_bytes.decode('utf-8'))
                        except Exception as e:
                            # If header can't be parsed, drop first byte and try to resync
                            print(f"[CLIENT] Failed to parse header JSON ({e}). Resyncing by dropping 1 byte.")
                            del self._recv_buffer[0]
                            continue

                        data_size = int(header.get("data_size", 0))
                        total_packet_len = 4 + header_size + data_size

                        # If we don't yet have the full JPEG/data bytes, wait for more datagrams
                        if len(self._recv_buffer) < total_packet_len:
                            break

                        # We have a full app-packet: extract jpeg bytes
                        jpeg_start = 4 + header_size
                        jpeg_end = jpeg_start + data_size
                        video_data = bytes(self._recv_buffer[jpeg_start:jpeg_end])

                        # Remove processed bytes from buffer
                        del self._recv_buffer[0:total_packet_len]

                        # Process this packet
                        stream_id = header.get('stream_id', '')
                        frame_no = header.get('frame_number', None)

                        if stream_id != self.stream_id:
                            # Not our stream -> ignore
                            # (We might still have other app-packets queued, so continue loop)
                            continue

                        # First-frame actions
                        if not self.receiving:
                            print(f"\n{'@'*60}")
                            print(f"STARTED RECEIVING STREAM!")
                            print(f"Stream ID: {self.stream_id}")
                            print(f"From: {addr[0]}")
                            print(f"{'@'*60}\n")
                            self.receiving = True

                        # Check if we need to reset frame tracking (after buffer clear on parent switch)
                        if self._reset_frame_tracking:
                            last_frame_number = None
                            self._reset_frame_tracking = False
                            print("[CLIENT] Reset frame number tracking after parent switch")

                        # Simple frame validation: discard backwards jumps (shouldn't happen with monotonic server counter)
                        if last_frame_number is not None and frame_no is not None:
                            if frame_no < last_frame_number:
                                # Frame went backward - this is now a serious error, log it
                                print(f"[CLIENT] WARNING: Frame went backward ({last_frame_number} -> {frame_no})")
                                # Still skip to avoid jitter from misordered packets
                                continue

                        # Write to ffplay (restarts if crashed)
                        self.write_to_ffplay_pipe(video_data)

                        # Update stats
                        self.frames_received += 1
                        self.bytes_received += len(video_data)
                        self.last_frame_time = time.time()
                        last_frame_number = frame_no

                        # occasional logging
                        if self.frames_received % 50 == 0:
                            current_time = time.time()
                            time_diff = current_time - last_frame_time
                            fps = 50 / time_diff if time_diff > 0 else 0
                            mb_received = self.bytes_received / (1024 * 1024)
                            print(f"[STREAMING] Frame {self.frames_received} | FPS(avg): {fps:.1f} | Data: {mb_received:.2f} MB")
                            last_frame_time = current_time

                # end with recv_lock

            except Exception as e:
                # don't let any exception kill the listener thread
                if self.running:
                    print(f"Error in UDP listener: {e}")
                    import traceback
                    traceback.print_exc()
                # slight back-off to avoid a hot loop on persistent errors
                time.sleep(0.1)

    def handle_p2p_message(self, message, addr, conn):
        """Handle P2P messages (override to stop the flood)"""
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
                
                # Handle parent shutdown - inherit dead node's parent
                self.handle_parent_shutdown(neighbor_ip, parent_ip)
                print(f"Neighbor {neighbor_ip} has shutdown!")
                return

            elif message.msg_type == Message.TYPE_FLOOD:
                conn.close()

                if message.content:
                    flood_id = message.content.get("flood_id", "unknown")
                    latency = message.content.get("latency", "unknown")
                    streams = message.content.get("streams", [])

                    if self.stream_id in streams:
                        print(f"\n{'='*60}")
                        print(f"Client {self.node_id} received FLOOD")
                        print(f"{'='*60}")
                        print(f"From: {addr[0]}")
                        print(f"Latency: {latency} ms")
                        print(f"Contains our stream: {self.stream_id}")

                        self.update_table(addr[0], flood_id, latency, streams)
                        self.check_and_switch_parent()

                        print(f"{'='*60}\n")

                return

            else:
                print(f"Received unknown message type: {message.msg_type}")
                conn.close()

        except Exception as e:
            print(f"Error processing message: {e}")
            conn.close()

    def print_statistics(self):
        """Periodically print reception statistics"""
        last_frames = 0
        last_bytes = 0
        last_time = time.time()

        time.sleep(10)

        while self.running:
            time.sleep(10)

            current_time = time.time()
            time_diff = current_time - last_time

            print(f"\n{'='*60}")
            print(f"CLIENT {self.node_id} STATUS")
            print(f"{'='*60}")
            print(f"Stream: {self.stream_id}")
            print(f"Current parent: {self.current_parent}")
            print(f"Joined: {self.joined}")
            print(f"Receiving: {self.receiving}")

            ffplay_running = self.ffplay_started and self.ffplay_process and self.ffplay_process.poll() is None
            print(f"ffplay running: {ffplay_running}")

            if self.frames_received > 0:
                frames_diff = self.frames_received - last_frames
                bytes_diff = self.bytes_received - last_bytes

                fps = frames_diff / time_diff if time_diff > 0 else 0
                bitrate = (bytes_diff * 8) / (time_diff * 1024 * 1024) if time_diff > 0 else 0

                print(f"Total frames: {self.frames_received}")
                print(f"Total data: {self.bytes_received / (1024*1024):.2f} MB")
                print(f"Current FPS: {fps:.2f}")
                print(f"Current bitrate: {bitrate:.2f} Mbps")

                last_frames = self.frames_received
                last_bytes = self.bytes_received
                last_time = current_time
            elif self.joined:
                print(f"\nWARNING: Joined but no frames received!")
                print(f"Parent: {self.current_parent}")
                print(f"Check if parent is streaming...")

            if self.parent_table:
                print(f"\nParent table for {self.stream_id}:")
                for entry in self.parent_table:
                    if entry.stream_id == self.stream_id:
                        state_str = "ACTIVE" if entry.state == "A" else "INACTIVE"
                        current_str = " (CURRENT)" if entry.node_parent == self.current_parent else ""
                        print(f"  {entry.node_parent}: {entry.latency:.2f} ms [{state_str}]{current_str}")

            print(f"{'='*60}\n")

    def start_node(self):
        """Start client node"""
        if not self.register():
            print(f"Error registering with the bootstrapper.")
            return

        self.check_alive_neighbors()

        # Start TCP listener
        tcp_listener_thread = threading.Thread(target=self.listen_for_messages, daemon=True)
        tcp_listener_thread.start()

        # Start UDP listener
        udp_listener_thread = threading.Thread(target=self.listen_for_stream_data, daemon=True)
        udp_listener_thread.start()

        # Start statistics printer
        stats_thread = threading.Thread(target=self.print_statistics, daemon=True)
        stats_thread.start()

        print(f"\n{'*'*60}")
        print(f"Client {self.node_id} initialized")
        print(f"TCP Port: {self.tcp_port}")
        print(f"UDP Port: {self.udp_port}")
        print(f"Stream ID: {self.stream_id}")
        print(f"ffplay will auto-start when stream begins")
        print(f"Waiting for floods...")
        print(f"{'*'*60}\n")

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\nStopping client {self.node_id}")
            self.stop_node()

    def stop_node(self):
        """Clean shutdown"""
        self.running = False

        # Send LEAVE if we have a parent
        if self.current_parent and self.joined:
            try:
                self.send_leave_request(self.current_parent)
            except Exception as e:
                print(f"Error sending LEAVE: {e}")

        # Close ffplay
        if self.ffplay_process:
            try:
                if self.ffplay_pipe:
                    try:
                        self.ffplay_pipe.close()
                    except:
                        pass
                self.ffplay_process.terminate()
                self.ffplay_process.wait(timeout=3)
                print("ffplay player closed")
            except:
                try:
                    self.ffplay_process.kill()
                except:
                    pass

        # Close sockets
        try:
            self.tcp_socket.close()
        except:
            pass
        try:
            self.udp_socket.close()
        except:
            pass

        print(f"\n{'='*60}")
        print(f"CLIENT {self.node_id} FINAL STATISTICS")
        print(f"{'='*60}")
        print(f"Stream: {self.stream_id}")
        print(f"Total frames: {self.frames_received}")
        print(f"Total data: {self.bytes_received / (1024*1024):.2f} MB")
        print(f"{'='*60}\n")

    def check_and_switch_parent(self):
        if not self.parent_table:
            print("No parents available in table yet")
            return

        best_entry = None
        best_latency = float('inf')

        for entry in self.parent_table:
            if entry.stream_id == self.stream_id:
                if entry.latency < best_latency:
                    best_latency = entry.latency
                    best_entry = entry

        if not best_entry:
            print(f"No parent found for stream {self.stream_id}")
            return

        best_parent_ip = best_entry.node_parent

        if not self.current_parent:
            print(f"\n{'#'*60}")
            print(f"FIRST JOIN - No current parent")
            print(f"Best parent: {best_parent_ip}")
            print(f"Latency: {best_entry.latency:.2f} ms")
            print(f"{'#'*60}\n")

            self.send_join_request(best_parent_ip)
            self.current_parent = best_parent_ip
            self.update_parent_table_state(best_parent_ip, "A")
            self.joined = True
            return

        if self.current_parent != best_parent_ip:
            print(f"\n{'#'*60}")
            print(f"PARENT SWITCH DETECTED")
            print(f"{'#'*60}")
            print(f"Stream: {self.stream_id}")
            print(f"Current parent: {self.current_parent}")
            print(f"New better parent: {best_parent_ip}")
            print(f"Latency improvement: {best_entry.latency:.2f} ms")
            print(f"{'#'*60}\n")

            self.send_leave_request(self.current_parent)
            self.send_join_request(best_parent_ip)

            old_parent = self.current_parent
            self.current_parent = best_parent_ip

            self.update_parent_table_state(old_parent, "D")
            self.update_parent_table_state(best_parent_ip, "A")

            # Clear receive buffer to discard old frames from previous parent
            with self._recv_lock:
                self._recv_buffer.clear()
                self._reset_frame_tracking = True
            
            print(f"Switched from {old_parent} to {best_parent_ip}")
            print(f"Cleared receive buffer to avoid frame jitter")

        elif self.current_parent == best_parent_ip:
            for entry in self.parent_table:
                if entry.node_parent == best_parent_ip and entry.stream_id == self.stream_id:
                    if entry.state == "D":
                        print(f"\nSame parent {best_parent_ip} but state is D - rejoining")
                        self.send_join_request(best_parent_ip)
                        entry.state = "A"
                    break

    def update_parent_table_state(self, parent_ip, state):
        """Update state for a specific parent in the table"""
        for entry in self.parent_table:
            if entry.node_parent == parent_ip and entry.stream_id == self.stream_id:
                entry.state = state
                print(f"Updated {parent_ip} state to {state}")

    def send_join_request(self, parent_ip):
        """Send JOIN request to parent via TCP"""
        try:
            join_msg = Message.create_join(self.node_id, self.stream_id, self.udp_port)
            success = join_msg.send_tcp(parent_ip, self.node_port)
            if success:
                print(f"Sent JOIN to {parent_ip} for stream {self.stream_id}")
            else:
                print(f"Failed to send JOIN to {parent_ip}")
            return success
        except Exception as e:
            print(f"Error sending JOIN to {parent_ip}: {e}")
            return False

    def send_leave_request(self, parent_ip):
        """Send LEAVE request to old parent via TCP"""
        try:
            leave_msg = Message.create_leave(self.node_id, self.stream_id)
            success = leave_msg.send_tcp(parent_ip, self.node_port)
            if success:
                print(f"Sent LEAVE to {parent_ip}")
            else:
                print(f"Failed to send LEAVE to {parent_ip}")
            return success
        except Exception as e:
            print(f"Error sending LEAVE to {parent_ip}: {e}")
            return False


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 client.py <node_id> <bootstrapper_ip> <stream_id> [node_port] [udp_port]")
        sys.exit(1)

    node_id = sys.argv[1]
    bootstrap_ip = sys.argv[2]
    stream_id = sys.argv[3]
    node_port = int(sys.argv[4]) if len(sys.argv) > 4 else 6000
    udp_port = int(sys.argv[5]) if len(sys.argv) > 5 else 7000

    client = Client(node_id, bootstrap_ip, stream_id, node_port=node_port, udp_port=udp_port)
    client.start_node()