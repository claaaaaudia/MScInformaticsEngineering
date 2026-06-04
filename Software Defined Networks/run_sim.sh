#!/bin/bash
# SPDX-License-Identifier: ANCL-1.0
# Copyright (c) 2026  jfpereira <d12267@di.uminho.pt> — di.uminho.pt
# Academic use only · no commercial use · see LICENSE
# AI-assisted development: Claude (Anthropic)
set -e

# =========================================================================
echo "Clean..."
sudo pkill -f run_controller.py 2>/dev/null || true
sudo mn -c 2>/dev/null
sleep 2
# =========================================================================

mkdir -p logs
mkdir -p build
mkdir -p mininet/run-time

# ── 1. Compile P4 programs ────────────────────────────────────────────────────
echo "Compiling P4 programs..."
p4c-bm2-ss --std p4-16 p4/l2switch.p4 -o build/l2switch.json --p4runtime-files build/l2switch.p4info.txt
#p4c-bm2-ss --std p4-16 p4/d2_fwd_firewall.p4 -o build/d2_fwd_firewall.json --p4runtime-files build/d2_fwd_firewall.p4info.txt

p4c-bm2-ss --std p4-16 p4/d2_slicing.p4 -o build/d2_slicing.json --p4runtime-files build/d2_slicing.p4info.txt
echo "Compilation done."

# ── 2. Build cNF Docker images ───────────────────────────────────────────────
echo "Building ARP proxy image..."
docker build -t arp-proxy ./cNF/arp_proxy
echo "ARP proxy image ready."

echo "Building DHCP server image..."
docker build -t dhcp-server ./cNF/dhcp_server
echo "DHCP server image ready."

echo "Building Traffic Shaping image..."
docker build -t traffic-shaping ./cNF/Traffic_Shaping
echo "Traffic Shaping image ready."

# ── 3. Launch Mininet in a new terminal ───────────────────────────────────────
if ! command -v xfce4-terminal >/dev/null 2>&1; then
    echo "Error: xfce4-terminal not found. Install it with: sudo apt-get install xfce4-terminal"
    exit 1
fi

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

echo "Starting Mininet in a new terminal..."
setsid xfce4-terminal --title "Mininet" -e "bash -c 'cd ${SCRIPT_DIR} && sudo python3 mininet/my_topo.py; sudo pkill dhclient; sudo mn -c; docker stop arp-proxy dhcp-server traffic-shaping 2>/dev/null || true; pkill -f run_controller.py 2>/dev/null || true; exit'" &

# ── 4. Wait for all three switch gRPC ports to be ready ──────────────────────
wait_for_port() {
    local port=$1
    until nc -z 127.0.0.1 "$port" 2>/dev/null; do
        sleep 0.5
    done
}

echo "Waiting for switches to start..."
wait_for_port 50051 && echo "  d1 ready (port 50051)"
wait_for_port 50052 && echo "  d2 ready (port 50052)"
wait_for_port 50053 && echo "  d3 ready (port 50053)"

# ── 5. Connect ARP proxy cNF to d2 port 3 ────────────────────────────────────
echo "Setting up ARP proxy cNF..."

# Clean up any leftover veth pair or container from a previous run
sudo ip link del veth-arp0 2>/dev/null || true
docker rm -f arp-proxy 2>/dev/null || true

# Create veth pair and bring both ends up
sudo ip link add veth-arp0 type veth peer name veth-arp1
sudo ip link set veth-arp0 up
sudo ip link set veth-arp1 up

# Add veth-arp0 to d2 as port 3 via the Thrift runtime API (d2 thrift port = 9091)
echo "port_add veth-arp0 3" | simple_switch_CLI --thrift-port 9091

# Start the ARP proxy container in a new terminal (logs visible, no network yet)
setsid xfce4-terminal --title "ARP Proxy" -e "bash -c 'docker run --name arp-proxy --network none --sysctl net.ipv6.conf.all.disable_ipv6=1 --rm -it arp-proxy; exit'" &

# Wait for the container to be running before wiring the veth
until docker inspect -f '{{.State.Running}}' arp-proxy 2>/dev/null | grep -q true; do
    sleep 0.2
done

# Move veth-arp1 into the container's network namespace
CONTAINER_PID=$(docker inspect -f '{{.State.Pid}}' arp-proxy)
sudo ip link set veth-arp1 netns "$CONTAINER_PID"

# Rename to veth-arp (matches arp_proxy.yaml) and bring it up inside the container
sudo nsenter -t "$CONTAINER_PID" -n ip link set veth-arp1 name veth-arp
sudo nsenter -t "$CONTAINER_PID" -n ip link set veth-arp up

echo "ARP proxy cNF ready on d2 port 3."

# ── 6. Connect DHCP server cNF to d2 port 4 ──────────────────────────────────
echo "Setting up DHCP server cNF..."

# Clean up any leftover veth pair or container from a previous run
sudo ip link del veth-dhcp0 2>/dev/null || true
docker rm -f dhcp-server 2>/dev/null || true

# Create veth pair and bring both ends up
sudo ip link add veth-dhcp0 type veth peer name veth-dhcp1
sudo ip link set veth-dhcp0 up
sudo ip link set veth-dhcp1 up

# Add veth-dhcp0 to d2 as port 4 via the Thrift runtime API (d2 thrift port = 9091)
echo "port_add veth-dhcp0 4" | simple_switch_CLI --thrift-port 9091

# Start the DHCP server container in a new terminal (logs visible, no network yet)
setsid xfce4-terminal --title "DHCP Server" -e "bash -c 'docker run --name dhcp-server --network none --sysctl net.ipv6.conf.all.disable_ipv6=1 --rm -it dhcp-server; exit'" &

# Wait for the container to be running before wiring the veth
until docker inspect -f '{{.State.Running}}' dhcp-server 2>/dev/null | grep -q true; do
    sleep 0.2
done

# Move veth-dhcp1 into the container's network namespace
CONTAINER_PID=$(docker inspect -f '{{.State.Pid}}' dhcp-server)
sudo ip link set veth-dhcp1 netns "$CONTAINER_PID"

# Rename to veth-dhcp (matches dhcp_server.yaml) and bring it up inside the container
sudo nsenter -t "$CONTAINER_PID" -n ip link set veth-dhcp1 name veth-dhcp
sudo nsenter -t "$CONTAINER_PID" -n ip link set veth-dhcp up

echo "DHCP server cNF ready on d2 port 4."


# ── 7. Connect Traffic Shaping cNF to d2 port 5 ──────────────────────────────
echo "Setting up Traffic Shaping cNF..."

# Clean up any leftover veth pair or container from a previous run
sudo ip link del veth-ts0 2>/dev/null || true
docker rm -f traffic-shaping 2>/dev/null || true

sudo ip link add veth-ts0 type veth peer name veth-ts1
sudo ip link set veth-ts0 up
sudo ip link set veth-ts1 up

sleep 1
# Add veth-ts0 to d2 as port 5 via the Thrift runtime API
echo "port_add veth-ts0 5" | simple_switch_CLI --thrift-port 9091 2>/dev/null || true

# Start the Traffic Shaping container in a new terminal 
setsid xfce4-terminal --title "Traffic Shaping" -e "bash -c 'docker run --name traffic-shaping --network none --sysctl net.ipv6.conf.all.disable_ipv6=1 --cap-add NET_ADMIN --rm -it traffic-shaping; exit'" &

# Wire veth in background
(
    sleep 2
    for i in {1..30}; do
        if docker inspect -f '{{.State.Running}}' traffic-shaping 2>/dev/null | grep -q true; then
            CONTAINER_PID=$(docker inspect -f '{{.State.Pid}}' traffic-shaping 2>/dev/null)
            if [ -n "$CONTAINER_PID" ] && [ "$CONTAINER_PID" != "0" ] && [ -d "/proc/$CONTAINER_PID" ]; then
                sudo ip link set veth-ts1 netns "$CONTAINER_PID" 2>/dev/null
                sudo nsenter -t "$CONTAINER_PID" -n ip link set veth-ts1 name veth-ts 2>/dev/null
                sudo nsenter -t "$CONTAINER_PID" -n ip link set veth-ts up 2>/dev/null
                echo "[INFO] Traffic Shaping veth attached on d2 port 5."
                break
            fi
        fi
        sleep 0.5
    done
) &


# ── 8. Launch the controller ──────────────────────────────────────────────────
echo "Starting controller..."

setsid xfce4-terminal --title "Controller" -e "bash -c 'cd ${SCRIPT_DIR} && python3 controller/run_controller.py --buildDir build --plugins self_learning slicing_app slicing_counting table_surveyor; exit'" &