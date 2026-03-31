import socket
import threading
import json
import time
import sys
import os
import subprocess
from node import Node
from message import Message

class Server(Node):
    def __init__(self, node_id, bootstrap_host, config_file='server_configs/server_config.json', bootstrap_port=5000, node_port=6000, udp_port=7000):
        super().__init__(node_id, bootstrap_host, bootstrap_port, node_port, udp_port)
        self.flood_count = 0
        self.streams = {}  # stream_id -> {"video_file": path, "streaming": bool, "thread": thread, "format": format}
        self.config_file = self.resolve_config_path(config_file)
        self.stream_frame_counters = {}  # stream_id -> frame_number (persists across pauses)
        
        # Load streams from config file on initialization
        self.load_streams_from_config()

    def resolve_config_path(self, config_file):
        """Resolve server config path, defaulting plain filenames to server_configs/."""
        if os.path.isabs(config_file) or os.path.dirname(config_file):
            return config_file

        base_dir = os.path.dirname(os.path.abspath(__file__))
        candidate = os.path.join(base_dir, "server_configs", config_file)
        if os.path.exists(candidate):
            return candidate

        return config_file
    
    def detect_video_format(self, video_file):
        """Detect video format based on file extension and content"""
        ext = os.path.splitext(video_file)[1].lower()
        
        if ext in ['.mjpeg', '.mjpg']:
            return 'mjpeg'
        elif ext in ['.mp4', '.m4v']:
            return 'mp4'
        else:
            # Try to detect from file content or default to mjpeg
            print(f"Warning: Unknown extension '{ext}' for {video_file}, defaulting to MJPEG")
            return 'mjpeg'
    
    def load_streams_from_config(self):
        """Load streams from configuration file on boot"""
        try:
            if not os.path.exists(self.config_file):
                print(f"Warning: Config file '{self.config_file}' not found. No streams loaded.")
                return
            
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            if "streams" not in config:
                print("Warning: No 'streams' section found in config file.")
                return
            
            streams_config = config["streams"]
            loaded_count = 0
            
            for stream_config in streams_config:
                stream_id = stream_config.get("stream_id")
                video_file = stream_config.get("video_file")
                
                if not stream_id or not video_file:
                    print(f"Warning: Skipping invalid stream config - missing stream_id or video_file")
                    continue
                
                if stream_id in self.streams:
                    print(f"Warning: Stream '{stream_id}' already exists, skipping")
                    continue
                
                # Detect video format
                video_format = self.detect_video_format(video_file)
                
                # Check if video file exists
                if not os.path.exists(video_file):
                    print(f"Warning: Video file '{video_file}' not found for stream '{stream_id}'")
                    # Add anyway, but streaming will fail if attempted
                
                self.streams[stream_id] = {
                    "video_file": video_file,
                    "streaming": False,
                    "thread": None,
                    "format": video_format
                }
                loaded_count += 1
                print(f"Loaded stream: {stream_id} -> {video_file} ({video_format.upper()})")
            
            print(f"\n{'#'*60}")
            print(f"STREAMS LOADED FROM CONFIG")
            print(f"Config file: {self.config_file}")
            print(f"Streams loaded: {loaded_count}")
            print(f"{'#'*60}\n")
            
        except json.JSONDecodeError as e:
            print(f"Error parsing config file '{self.config_file}': {e}")
        except Exception as e:
            print(f"Error loading streams from config: {e}")
    
    def handle_p2p_message(self, message, addr, conn):
        """Override to ignore floods from other servers and handle JOIN requests""" 
        try:
            if message.msg_type == Message.TYPE_PING:
                print(f"Received PING from {addr[0]}")
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
                    print(f"Server {self.node_id}: Neighbor {pinger_ip} is now alive!")
                    print(f"Updated alive neighbors: {self.alive_neighbors}")
                    print(f"{'#'*60}\n")
                
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
                return
            
            elif message.msg_type == Message.TYPE_JOIN:
                conn.close()
                stream_id = message.content.get("stream_id", "")
                child_ip = addr[0]
                
                print(f"\n{'='*60}")
                print(f"SERVER JOIN REQUEST")
                print(f"{'='*60}")
                print(f"From: {child_ip}")
                print(f"Stream: {stream_id}")
                
                # Check if this stream exists
                if stream_id in self.streams:
                    # Check if child already exists
                    child_exists = False
                    for child in self.child_table:
                        if child.node_child == child_ip and child.stream_id == stream_id:
                            child.state = "A"
                            child_exists = True
                            print(f"Reactivated child {child_ip} for stream {stream_id}")
                            break
                    
                    if not child_exists:
                        from table import Child
                        new_child = Child(node_child=child_ip, stream_id=stream_id, state="A")
                        self.child_table.append(new_child)
                        print(f"Added child {child_ip} to server's child table")
                    
                    # Start streaming if not already streaming
                    if not self.streams[stream_id]["streaming"]:
                        print(f"Starting stream for {stream_id} immediately")
                        self.start_streaming(stream_id)
                    else:
                        print(f"Stream {stream_id} is already streaming")
                    
                    # Print child table status
                    self.print_child_table()
                    
                else:
                    print(f"ERROR: JOIN request for unknown stream {stream_id}")
                    print(f"Available streams: {list(self.streams.keys())}")
                
                print(f"{'='*60}\n")
                return
            
            elif message.msg_type == Message.TYPE_LEAVE:
                conn.close()
                stream_id = message.content.get("stream_id", "")
                child_ip = addr[0]
                
                print(f"\n{'='*60}")
                print(f"SERVER LEAVE REQUEST")
                print(f"{'='*60}")
                print(f"From: {child_ip}")
                print(f"Stream: {stream_id}")
                
                # Deactivate the child
                for child in self.child_table:
                    if child.node_child == child_ip and child.stream_id == stream_id:
                        child.state = "D"
                        print(f"Deactivated child {child_ip}")
                        break
                
                # Check if we should stop streaming
                active_children = self.count_active_children_for_stream(stream_id)
                if active_children == 0 and stream_id in self.streams and self.streams[stream_id]["streaming"]:
                    print(f"No more active children - stopping stream {stream_id}")
                    self.streams[stream_id]["streaming"] = False
                
                # Print child table status
                self.print_child_table()
                print(f"{'='*60}\n")
                return
            
            else:
                print(f"Received unknown message type: {message.msg_type}")
                conn.close()
                
        except Exception as e:
            print(f"Error processing message: {e}")
            conn.close()
        
    def initiate_flood(self):
        """Server initiates flood with current RTT measurements and active stream info"""
        print(f"\n{'='*60}")
        print(f"Server {self.node_id} INITIATING PERIODIC FLOOD")
        print(f"{'='*60}")

        self.flood_count += 1
        
        # Get list of ALL streams (not just active ones)
        all_streams = list(self.streams.keys())
        
        print(f"Available streams: {all_streams if all_streams else 'None'}")
        print(f"Phase 1: Measuring RTT to {len(self.alive_neighbors)} neighbors...")
        rtt_results = self.measure_rtt_to_specified_neighbors(self.alive_neighbors)
        
        flood_content = {
            "timestamp": time.time(),
            "flood_id": f"{self.node_id}_{self.flood_count}",
            "streams": all_streams  # Include list of all available streams
        }
        
        flood_msg = Message(
            msg_type=Message.TYPE_FLOOD,
            node_id=self.node_id,
            content=flood_content,
            msg_id=flood_content["flood_id"]
        )
        
        print(f"\nPhase 2: Sending flood to neighbors...")
        sent_count = 0
        for neighbor_ip in self.alive_neighbors:
            try:
                neighbor_content = {
                    **flood_content,
                    "latency": rtt_results.get(neighbor_ip, float('inf'))
                }
                
                neighbor_msg = Message(
                    msg_type=Message.TYPE_FLOOD,
                    node_id=self.node_id,
                    content=neighbor_content,
                    msg_id=flood_msg.msg_id
                )
                
                neighbor_msg.send_tcp(neighbor_ip, self.tcp_port)
                sent_count += 1
                print(f"  To {neighbor_ip}: RTT {rtt_results.get(neighbor_ip, float('inf')):.2f} ms")
            except Exception as e:
                print(f"  Failed to send to {neighbor_ip}: {e}")
        
        print(f"\nFlood initiated successfully to {sent_count}/{len(self.alive_neighbors)} neighbors")
        print(f"Flood ID: {flood_content['flood_id']}")
        print(f"{'='*60}\n")
    
    def flood_periodically(self, interval=30):
        """Periodically initiate floods from the server"""
        time.sleep(10)  # Wait for initialization
        
        print(f"\n{'*'*60}")
        print(f"Server {self.node_id} periodic flood scheduler started")
        print(f"Will initiate floods every {interval} seconds")
        print(f"{'*'*60}\n")
        
        flood_count = 0
        while self.running:
            try:
                flood_count += 1
                print(f"\n[Flood #{flood_count}]")
                self.initiate_flood()
                time.sleep(interval)
            except Exception as e:
                print(f"Error during periodic flood: {e}")
                time.sleep(5)
    
    def start_streaming(self, stream_id):
        """Start streaming video to children"""
        if stream_id not in self.streams:
            print(f"ERROR: Stream {stream_id} does not exist!")
            return False
        
        # Check if already streaming (thread is alive and running)
        if self.streams[stream_id]["streaming"]:
            print(f"Stream {stream_id} is already streaming")
            return False
        
        # Check if thread exists and is still alive from a previous session
        existing_thread = self.streams[stream_id]["thread"]
        if existing_thread and existing_thread.is_alive():
            print(f"Stream {stream_id} thread is still alive, reusing it")
            # Re-enable streaming flag
            self.streams[stream_id]["streaming"] = True
            return True
        
        # Check if video file exists
        video_file = self.streams[stream_id]["video_file"]
        if not os.path.exists(video_file):
            print(f"ERROR: Video file '{video_file}' not found for stream {stream_id}")
            return False
        
        self.streams[stream_id]["streaming"] = True
        
        # Choose streaming method based on format
        video_format = self.streams[stream_id]["format"]
        if video_format == 'mp4':
            stream_thread = threading.Thread(target=self.stream_mp4_video, args=(stream_id,), daemon=True)
        else:
            stream_thread = threading.Thread(target=self.stream_mjpeg_video, args=(stream_id,), daemon=True)
        
        self.streams[stream_id]["thread"] = stream_thread
        stream_thread.start()
        print(f"Started streaming thread for {stream_id} ({video_format.upper()})")
        return True
    
    def stream_mjpeg_video(self, stream_id):
        """Stream MJPEG video file via UDP to all active children (robust looping)."""
        stream_info = self.streams.get(stream_id)
        if not stream_info:
            print(f"ERROR: Stream {stream_id} not found!")
            return

        video_file = stream_info["video_file"]

        print(f"\n{'#'*60}")
        print(f"STARTING MJPEG VIDEO STREAM")
        print(f"Stream ID: {stream_id}")
        print(f"Video file: {video_file}")
        print(f"{'#'*60}\n")

        loop_count = 0
        
        # Initialize frame counter if not exists, otherwise resume from where we left off
        if stream_id not in self.stream_frame_counters:
            self.stream_frame_counters[stream_id] = 0
        
        frame_number = self.stream_frame_counters[stream_id]
        print(f"[STREAM {stream_id}] Resuming from frame {frame_number}")

        try:
            while stream_info["streaming"] and self.running:
                loop_count += 1
                buffer = b''
                frames_this_loop = 0
                bytes_read = 0
                hit_eof = False

                print(f"\n[STREAM {stream_id}] ===== VIDEO LOOP #{loop_count} =====")

                try:
                    if not os.path.exists(video_file):
                        print(f"[STREAM {stream_id}] ERROR: Video file does not exist!")
                        stream_info["streaming"] = False
                        break

                    with open(video_file, 'rb') as video:
                        video.seek(0)

                        chunk_size = 65536
                        while stream_info["streaming"] and self.running:
                            chunk = video.read(chunk_size)
                            if not chunk:
                                hit_eof = True
                                print(f"[STREAM {stream_id}] EOF reached: frames_this_loop={frames_this_loop}")
                                break

                            bytes_read += len(chunk)
                            buffer += chunk

                            # Extract complete JPEG frames
                            while True:
                                start_idx = buffer.find(b'\xff\xd8')
                                if start_idx == -1:
                                    break
                                end_idx = buffer.find(b'\xff\xd9', start_idx + 2)
                                if end_idx == -1:
                                    break

                                frame_data = buffer[start_idx:end_idx + 2]
                                buffer = buffer[end_idx + 2:]

                                # Build packet
                                stream_packet = {
                                    "stream_id": stream_id,
                                    "frame_number": frame_number,
                                    "timestamp": time.time(),
                                    "data_size": len(frame_data)
                                }
                                header_json = json.dumps(stream_packet).encode('utf-8')
                                header_size = len(header_json)
                                packet = header_size.to_bytes(4, 'big') + header_json + frame_data

                                active_children = [c for c in self.child_table if c.state == "A" and c.stream_id == stream_id]

                                if active_children:
                                    for child in active_children:
                                        try:
                                            self.udp_socket.sendto(packet, (child.node_child, self.udp_port))
                                        except Exception as e:
                                            print(f"[STREAM {stream_id}] Error sending to {child.node_child}: {e}")

                                    frames_this_loop += 1
                                    if frame_number % 100 == 0 and frame_number > 0:
                                        print(f"[STREAM {stream_id}] Sent frame {frame_number} to {len(active_children)} children")
                                else:
                                    if frames_this_loop > 100:
                                        print(f"[STREAM {stream_id}] No active children, stopping stream.")
                                        stream_info["streaming"] = False
                                        break

                                frame_number += 1
                                time.sleep(0.033)

                    if hit_eof and stream_info["streaming"] and self.running:
                        active_children = [c for c in self.child_table if c.state == "A" and c.stream_id == stream_id]
                        if not active_children:
                            print(f"[STREAM {stream_id}] No active children at EOF; stopping stream.")
                            stream_info["streaming"] = False
                            break

                        print(f"[STREAM {stream_id}] *** LOOPING BACK TO START *** ({len(active_children)} children)")
                        time.sleep(0.05)
                        continue

                    if not hit_eof:
                        print(f"[STREAM {stream_id}] Exiting streaming loop")
                        break

                except FileNotFoundError:
                    print(f"[STREAM {stream_id}] ERROR: Video file not found!")
                    stream_info["streaming"] = False
                    break
                except Exception as e:
                    print(f"[STREAM {stream_id}] Exception: {e}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(0.5)
                    continue

        except Exception as e:
            print(f"[STREAM {stream_id}] Fatal streaming error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Save frame counter for next session
            self.stream_frame_counters[stream_id] = frame_number
            print(f"\n[STREAM {stream_id}] ===== STREAMING STOPPED =====")
            print(f"[STREAM {stream_id}] Saved frame counter at {frame_number}")
            stream_info["streaming"] = False

    def stream_mp4_video(self, stream_id):
        """Stream MP4 video file by converting to MJPEG on-the-fly using ffmpeg"""
        stream_info = self.streams.get(stream_id)
        if not stream_info:
            print(f"ERROR: Stream {stream_id} not found!")
            return

        video_file = stream_info["video_file"]

        print(f"\n{'#'*60}")
        print(f"STARTING MP4 VIDEO STREAM")
        print(f"Stream ID: {stream_id}")
        print(f"Video file: {video_file}")
        print(f"{'#'*60}\n")

        loop_count = 0

        try:
            while stream_info["streaming"] and self.running:
                loop_count += 1
                print(f"\n[STREAM {stream_id}] ===== VIDEO LOOP #{loop_count} =====")

                process = None
                try:
                    if not os.path.exists(video_file):
                        print(f"[STREAM {stream_id}] ERROR: Video file does not exist!")
                        stream_info["streaming"] = False
                        break

                    # Check if ffmpeg is available
                    try:
                        ffmpeg_check = subprocess.run(['ffmpeg', '-version'], 
                                                     capture_output=True, 
                                                     timeout=5)
                        if ffmpeg_check.returncode != 0:
                            print(f"[STREAM {stream_id}] ERROR: ffmpeg not working properly!")
                            stream_info["streaming"] = False
                            break
                    except FileNotFoundError:
                        print(f"[STREAM {stream_id}] ERROR: ffmpeg not found! Please install ffmpeg.")
                        print("  Ubuntu/Debian: sudo apt-get install ffmpeg")
                        print("  macOS: brew install ffmpeg")
                        stream_info["streaming"] = False
                        break

                    # Use ffmpeg to convert MP4 to MJPEG stream
                    ffmpeg_cmd = [
                        'ffmpeg',
                        '-re',  # Read at native frame rate
                        '-i', video_file,
                        '-f', 'mjpeg',
                        '-q:v', '5',  # Quality (2-31, lower is better)
                        '-r', '30',   # Frame rate
                        '-loglevel', 'error',  # Only show errors
                        'pipe:1'
                    ]

                    print(f"[STREAM {stream_id}] Starting ffmpeg process...")
                    print(f"[STREAM {stream_id}] Command: {' '.join(ffmpeg_cmd)}")

                    process = subprocess.Popen(
                        ffmpeg_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        bufsize=10**8
                    )

                    # Check if process started successfully
                    time.sleep(0.5)
                    if process.poll() is not None:
                        stderr_output = process.stderr.read().decode('utf-8', errors='ignore')
                        print(f"[STREAM {stream_id}] ERROR: ffmpeg failed to start!")
                        print(f"[STREAM {stream_id}] ffmpeg error: {stderr_output}")
                        stream_info["streaming"] = False
                        break

                    print(f"[STREAM {stream_id}] ffmpeg started successfully (PID: {process.pid})")

                    buffer = b''
                    frame_number = 0
                    bytes_read = 0
                    last_log_time = time.time()

                    while stream_info["streaming"] and self.running:
                        # Check if ffmpeg process is still running
                        if process.poll() is not None:
                            stderr_output = process.stderr.read().decode('utf-8', errors='ignore')
                            if stderr_output:
                                print(f"[STREAM {stream_id}] ffmpeg terminated with error: {stderr_output}")
                            else:
                                print(f"[STREAM {stream_id}] ffmpeg finished (EOF)")
                            break

                        chunk = process.stdout.read(65536)
                        if not chunk:
                            print(f"[STREAM {stream_id}] No more data from ffmpeg")
                            break

                        bytes_read += len(chunk)
                        buffer += chunk

                        # Log progress every 5 seconds
                        if time.time() - last_log_time > 5:
                            print(f"[STREAM {stream_id}] Reading from ffmpeg: {bytes_read / (1024*1024):.2f} MB, {frame_number} frames")
                            last_log_time = time.time()

                        # Extract complete JPEG frames
                        while True:
                            start_idx = buffer.find(b'\xff\xd8')
                            if start_idx == -1:
                                break
                            end_idx = buffer.find(b'\xff\xd9', start_idx + 2)
                            if end_idx == -1:
                                break

                            frame_data = buffer[start_idx:end_idx + 2]
                            buffer = buffer[end_idx + 2:]

                            # Build packet
                            stream_packet = {
                                "stream_id": stream_id,
                                "frame_number": frame_number,
                                "timestamp": time.time(),
                                "data_size": len(frame_data)
                            }
                            header_json = json.dumps(stream_packet).encode('utf-8')
                            header_size = len(header_json)
                            packet = header_size.to_bytes(4, 'big') + header_json + frame_data

                            active_children = [c for c in self.child_table if c.state == "A" and c.stream_id == stream_id]

                            if active_children:
                                for child in active_children:
                                    try:
                                        self.udp_socket.sendto(packet, (child.node_child, self.udp_port))
                                    except Exception as e:
                                        print(f"[STREAM {stream_id}] Error sending to {child.node_child}: {e}")

                                if frame_number % 100 == 0 and frame_number > 0:
                                    print(f"[STREAM {stream_id}] Sent frame {frame_number} to {len(active_children)} children")
                                elif frame_number < 10:
                                    # Log first few frames for debugging
                                    print(f"[STREAM {stream_id}] Sent frame {frame_number} ({len(frame_data)} bytes) to {len(active_children)} children")
                            else:
                                if frame_number > 100:
                                    print(f"[STREAM {stream_id}] No active children, stopping stream.")
                                    stream_info["streaming"] = False
                                    break

                            frame_number += 1

                    print(f"[STREAM {stream_id}] Finished streaming {frame_number} frames, {bytes_read / (1024*1024):.2f} MB")

                    # Clean up ffmpeg process
                    if process:
                        try:
                            process.stdout.close()
                            process.stderr.close()
                            process.terminate()
                            process.wait(timeout=5)
                        except:
                            try:
                                process.kill()
                            except:
                                pass

                    # Check if we should loop
                    if stream_info["streaming"] and self.running:
                        active_children = [c for c in self.child_table if c.state == "A" and c.stream_id == stream_id]
                        if not active_children:
                            print(f"[STREAM {stream_id}] No active children at EOF; stopping stream.")
                            stream_info["streaming"] = False
                            break

                        print(f"[STREAM {stream_id}] *** LOOPING BACK TO START *** ({len(active_children)} children)")
                        time.sleep(0.1)
                        continue
                    else:
                        break

                except FileNotFoundError as e:
                    print(f"[STREAM {stream_id}] ERROR: File not found - {e}")
                    stream_info["streaming"] = False
                    break
                except Exception as e:
                    print(f"[STREAM {stream_id}] Exception: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    # Clean up process if it exists
                    if process:
                        try:
                            process.kill()
                        except:
                            pass
                    
                    time.sleep(0.5)
                    continue

        except Exception as e:
            print(f"[STREAM {stream_id}] Fatal streaming error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print(f"\n[STREAM {stream_id}] ===== STREAMING STOPPED =====")
            stream_info["streaming"] = False
    
    def start_node(self):
        """Override start_node for server-specific functionality"""
        if not self.register():
            print(f"Error registering with the bootstrapper.")
            return

        self.check_alive_neighbors()

        # Start listening for TCP messages
        tcp_listener_thread = threading.Thread(target=self.listen_for_messages, daemon=True)
        tcp_listener_thread.start()

        # Start listening for UDP (for forwarding)
        udp_listener_thread = threading.Thread(target=self.listen_for_stream_data, daemon=True)
        udp_listener_thread.start()

        print(f"\n{'*'*60}")
        print(f"Server {self.node_id} completely initialized")
        print(f"TCP Port: {self.tcp_port}")
        print(f"UDP Port: {self.udp_port}")
        print(f"Alive neighbors: {self.alive_neighbors}")
        print(f"Available streams:")
        for stream_id, info in self.streams.items():
            print(f"  - {stream_id}: {info['video_file']} ({info['format'].upper()})")
        print(f"{'*'*60}\n")

        # Start the periodic flood thread
        flood_thread = threading.Thread(target=self.flood_periodically, daemon=True)
        flood_thread.start()

        # Server runs without command interface
        try:
            while self.running:
                # Periodically log status
                time.sleep(30)
                print(f"\n[Server Status] Streams: {len(self.streams)}, "
                      f"Active children: {len([c for c in self.child_table if c.state == 'A'])}")
                      
        except KeyboardInterrupt:
            print(f"\nStopping server {self.node_id}")
            self.stop_node()

    def stop_node(self):
        """Stop server and all streaming"""
        # Stop all streams
        for stream_id in list(self.streams.keys()):
            if self.streams[stream_id]["streaming"]:
                self.streams[stream_id]["streaming"] = False
        
        self.running = False
        
        try:
            # Get this server's parent to send in shutdown message
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
        print(f"Server {self.node_id} stopped")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 server.py <node_id> <bootstrapper_ip> [config_file] [node_port] [udp_port]")
        print("  config_file: JSON file with stream configuration (default: server_configs/server_config.json)")
        sys.exit(1)

    node_id = sys.argv[1]
    bootstrap_ip = sys.argv[2]
    config_file = sys.argv[3] if len(sys.argv) > 3 else 'server_configs/server_config.json'
    node_port = int(sys.argv[4]) if len(sys.argv) > 4 else 6000
    udp_port = int(sys.argv[5]) if len(sys.argv) > 5 else 7000
    
    server = Server(node_id, bootstrap_ip, config_file=config_file, node_port=node_port, udp_port=udp_port)
    server.start_node()