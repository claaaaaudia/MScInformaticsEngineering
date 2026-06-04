#!/usr/bin/env python3
# SPDX-License-Identifier: ANCL-1.0
# Copyright (c) 2026  jfpereira <d12267@di.uminho.pt> — di.uminho.pt
# Academic use only · no commercial use · see LICENSE
# AI-assisted development: Claude (Anthropic)

import time
import ipaddress
import yaml
from scapy.all import BOOTP, DHCP, Ether, IP, UDP, sendp, sniff

# DHCP PROTOCOL NOTES
# -------------------
# The DHCP exchange follows a four-step handshake:
#   1. Discover  — client broadcasts: "I need an IP" (client has no IP yet)
#   2. Offer     — server replies with an available IP
#   3. Request   — client broadcasts: "I accept that IP" (broadcast so other servers hear it)
#   4. Ack       — server confirms the assignment
#
# Broadcast vs unicast:
#   - Discover and Request are always sent by the client in broadcast (Ethernet + IP)
#     because the client has no IP address yet and cannot receive unicast IP packets.
#   - Offer and initial Ack are sent by the server in broadcast for the same reason.
#   - Renewal Ack (client already has an IP, sends Request with ciaddr set) can be
#     sent unicast directly to the client.
#   - NAK is always broadcast — the client's IP may be wrong or absent.
#
# Common pitfalls:
#   - Race condition: if two clients send Discover before any Ack is processed,
#     get_next_ip() returns the same IP to both. Reserve the IP at Offer time, not Ack time.
#   - INIT-REBOOT: dhclient caches leases and may skip Discover on restart, sending
#     a Request directly for a previously assigned IP. The server must handle this
#     gracefully — Ack if the IP is still available, NAK otherwise.
#   - Offer mismatch: the IP in the Request is chosen by the client, not the server.
#     A client could request an IP different from what was offered. Always validate
#     that the requested IP matches your offer before sending an Ack.
#   - Stale offers: if a client never sends a Request after receiving an Offer, the
#     offered IP is blocked forever unless offers have a timeout.


def load_config(path):
    with open(path) as f:
        config = yaml.safe_load(f)
    return config


def build_pool(config):
    subnet    = config["subnet"]
    mask      = config["subnet_mask"]
    server_ip = config["server_ip"]
    gateway   = config["gateway"]

    network = ipaddress.IPv4Network(f"{subnet}/{mask}", strict=False)

    # Build pool: all host addresses in the subnet
    pool = {}
    for ip in network.hosts():
        pool[str(ip)] = {"mac": None, "reserved": False}

    # Reserve: network address and broadcast are not in hosts(), but
    # reserve server_ip and gateway explicitly
    for reserved_ip in [server_ip, gateway]:
        if reserved_ip in pool:
            pool[reserved_ip]["reserved"] = True

    # Apply static reservations from config
    for entry in config.get("reservations", []):
        ip  = entry["ip"]
        mac = entry["mac"].lower()
        if ip in pool:
            pool[ip]["mac"]      = mac
            pool[ip]["reserved"] = True

    return pool


def get_next_ip(pool, offered_pool):
    offered_ips = {v["ip"] for v in offered_pool.values()}

    for ip, entry in pool.items():
        if entry["reserved"]:
            continue
        if entry["mac"] is not None:
            continue
        if ip in offered_ips:
            continue
        return ip

    return None


def handle_dhcp(packet, interface, config, pool, offered_pool):
    if not packet.haslayer(DHCP):
        return

    dhcp_options = {opt[0]: opt[1] for opt in packet[DHCP].options if isinstance(opt, tuple)}
    msg_type = dhcp_options.get("message-type")
    if msg_type is None:
        return

    client_mac = packet[Ether].src.lower()
    xid        = packet[BOOTP].xid

    server_ip  = config["server_ip"]
    gateway    = config["gateway"]
    dns        = config["dns"]
    lease_time = config["lease_time"]

    # ── DHCP Discover ─────────────────────────────────────────────────────────
    if msg_type == 1:
        # Check if this client already has a static reservation
        offered_ip = None
        for ip, entry in pool.items():
            if entry.get("mac") == client_mac and entry["reserved"]:
                offered_ip = ip
                break

        # If no static reservation, pick the next free IP and mark it offered
        if offered_ip is None:
            offered_ip = get_next_ip(pool, offered_pool)

        if offered_ip is None:
            print(f"DHCP pool exhausted — cannot offer to {client_mac}")
            return

        # Reserve at Offer time to avoid race condition
        offered_pool[client_mac] = {"ip": offered_ip, "timestamp": time.time()}

        print(f"DHCP Offer: {offered_ip} -> {client_mac}")

        reply = (
            Ether(dst="ff:ff:ff:ff:ff:ff")
            / IP(src=server_ip, dst="255.255.255.255")
            / UDP(sport=67, dport=68)
            / BOOTP(
                op=2,
                xid=xid,
                yiaddr=offered_ip,
                siaddr=server_ip,
                chaddr=packet[BOOTP].chaddr,
            )
            / DHCP(options=[
                ("message-type", "offer"),
                ("server_id",    server_ip),
                ("lease_time",   lease_time),
                ("subnet_mask",  config["subnet_mask"]),
                ("router",       gateway),
                ("name_server",  dns),
                "end",
            ])
        )
        sendp(reply, iface=interface, verbose=False)

    # ── DHCP Request ──────────────────────────────────────────────────────────
    elif msg_type == 3:
        requested_ip = dhcp_options.get("requested_addr") or packet[BOOTP].ciaddr

        # INIT-REBOOT: client skipped Discover and requests a previously known IP
        if client_mac not in offered_pool:
            # Accept if IP is free or belongs to this client
            entry = pool.get(requested_ip)
            if entry and (entry["mac"] is None or entry["mac"] == client_mac) and not entry["reserved"]:
                offered_pool[client_mac] = {"ip": requested_ip, "timestamp": time.time()}
            else:
                # NAK — IP not available
                print(f"DHCP NAK (INIT-REBOOT): {requested_ip} not available for {client_mac}")
                nak = (
                    Ether(dst="ff:ff:ff:ff:ff:ff")
                    / IP(src=server_ip, dst="255.255.255.255")
                    / UDP(sport=67, dport=68)
                    / BOOTP(op=2, xid=xid, chaddr=packet[BOOTP].chaddr)
                    / DHCP(options=[
                        ("message-type", "nak"),
                        ("server_id",    server_ip),
                        "end",
                    ])
                )
                sendp(nak, iface=interface, verbose=False)
                return

        offered = offered_pool.get(client_mac)

        # Validate that the requested IP matches our offer
        if offered and str(requested_ip) != str(offered["ip"]):
            print(f"DHCP NAK: {client_mac} requested {requested_ip} but we offered {offered['ip']}")
            nak = (
                Ether(dst="ff:ff:ff:ff:ff:ff")
                / IP(src=server_ip, dst="255.255.255.255")
                / UDP(sport=67, dport=68)
                / BOOTP(op=2, xid=xid, chaddr=packet[BOOTP].chaddr)
                / DHCP(options=[
                    ("message-type", "nak"),
                    ("server_id",    server_ip),
                    "end",
                ])
            )
            sendp(nak, iface=interface, verbose=False)
            return

        # Commit the lease
        assigned_ip = offered["ip"]
        pool[assigned_ip]["mac"]      = client_mac
        pool[assigned_ip]["reserved"] = False  # now a dynamic lease, not a pending offer
        del offered_pool[client_mac]

        print(f"DHCP Ack: {assigned_ip} -> {client_mac}")

        ack = (
            Ether(dst="ff:ff:ff:ff:ff:ff")
            / IP(src=server_ip, dst="255.255.255.255")
            / UDP(sport=67, dport=68)
            / BOOTP(
                op=2,
                xid=xid,
                yiaddr=assigned_ip,
                siaddr=server_ip,
                chaddr=packet[BOOTP].chaddr,
            )
            / DHCP(options=[
                ("message-type", "ack"),
                ("server_id",    server_ip),
                ("lease_time",   lease_time),
                ("subnet_mask",  config["subnet_mask"]),
                ("router",       gateway),
                ("name_server",  dns),
                "end",
            ])
        )
        sendp(ack, iface=interface, verbose=False)


def main():
    config       = load_config("dhcp_server.yaml")
    interface    = config["interface"]
    pool         = build_pool(config)
    offered_pool = {}  # {mac -> {ip, timestamp}} — pending offers not yet Acked

    print(f"DHCP server listening on {interface}")

    sniff(
        iface=interface,
        filter="udp and (port 67 or port 68)",
        prn=lambda pkt: handle_dhcp(pkt, interface, config, pool, offered_pool),
        store=False,
    )


if __name__ == "__main__":
    main()