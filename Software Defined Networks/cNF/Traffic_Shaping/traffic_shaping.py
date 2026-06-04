#!/usr/bin/env python3

import signal
import subprocess
import sys
import time
import yaml

STATE = {
    "enabled": False,
    "interface": None,
    "config": None,
}

# set up traffic shaping
def run(cmd):
    subprocess.run(cmd, check=True, capture_output=True, text=True)

# best effort version that doesn't error on failure
def run_best_effort(cmd):
    subprocess.run(cmd, check=False, capture_output=True, text=True)

# load shaping config from YAML file
def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# wait for interface to exist (with retry for container startup race)
def wait_interface_ready(interface, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        result = subprocess.run(["ip", "link", "show", interface], capture_output=True, text=True)
        if result.returncode == 0:
            return True
        print(f"[TS] waiting for interface {interface}...")
        time.sleep(0.5)
    raise TimeoutError(f"interface {interface} did not appear within {timeout}s")

# ensure the interface is up before applying tc rules
def ensure_interface_up(interface):
    try:
        wait_interface_ready(interface)
    except TimeoutError as e:
        print(f"[TS] error: {e}")
        sys.exit(1)
    run(["ip", "link", "set", interface, "up"])

# clear existing tc rules to start fresh
def clear_tc(interface):
    run_best_effort(["tc", "qdisc", "del", "dev", interface, "root"])
    run_best_effort(["tc", "qdisc", "del", "dev", interface, "ingress"])

# set up HTB shaping with per-slice classes and filters based on config
def setup_shaping(interface, config):
    qdisc = str(config.get("qdisc", "htb")).lower()
    if qdisc != "htb":
        print(f"[TS] warning: qdisc={qdisc} requested, but runtime uses htb for per-slice buffering")

    default_rate = int(config.get("default_rate_Bps", 1250000))
    default_burst = int(config.get("default_burst_bytes", 50000))
    default_qlimit = int(config.get("default_queue_limit_bytes", 1048576))

    profiles = config.get("profiles", [])
    exceed_cfg = config.get("on_exceed", {})
    overflow_action = exceed_cfg.get("overflow_action", "drop")

    if overflow_action != "drop":
        print("[TS] warning: only overflow_action=drop is supported by tc queue overflow")

    clear_tc(interface)

    default_rate_bit = max(default_rate * 8, 8)

    # Root HTB with high-cap default class. Per-slice classes enforce profile rates.
    run(["tc", "qdisc", "add", "dev", interface, "root", "handle", "1:", "htb", "default", "999"])

    # Default class keeps unmatched traffic flowing.
    run([
        "tc", "class", "add", "dev", interface,
        "parent", "1:", "classid", "1:999", "htb",
        "rate", f"{default_rate_bit}bit",
        "ceil", f"{default_rate_bit}bit",
        "burst", str(max(default_burst, 1024)),
    ])

    # Default queue: buffer first, drop only when queue limit is exceeded.
    run([
        "tc", "qdisc", "add", "dev", interface,
        "parent", "1:999", "handle", "999:", "bfifo",
        "limit", str(max(default_qlimit, 65536)),
    ])

    for profile in profiles:
        slice_id = int(profile["slice_id"])
        src_ip = profile["src_ip"]
        rate = int(profile["rate_Bps"])
        burst = int(profile.get("burst_bytes", default_burst))
        qlimit = int(profile.get("queue_limit_bytes", default_qlimit))
        rate_bit = max(rate * 8, 8)

        class_minor = 100 + slice_id
        classid = f"1:{class_minor}"
        handle = f"{class_minor}:"
        prio = str(10 + slice_id)

        # Per-slice token bucket shaping. Over-limit packets wait in this class queue.
        run([
            "tc", "class", "add", "dev", interface,
            "parent", "1:", "classid", classid, "htb",
            "rate", f"{rate_bit}bit",
            "ceil", f"{rate_bit}bit",
            "burst", str(max(burst, 1024)),
        ])

        # Queue buffers packets and drops only on overflow.
        run([
            "tc", "qdisc", "add", "dev", interface,
            "parent", classid, "handle", handle, "bfifo",
            "limit", str(max(qlimit, 65536)),
        ])

        # Classify by source IP so each slice gets its own queue/rate.
        run([
            "tc", "filter", "add", "dev", interface,
            "protocol", "ip", "parent", "1:", "prio", prio,
            "u32", "match", "ip", "src", src_ip, "flowid", classid,
        ])

        print(
            f"[TS] slice={slice_id} src={src_ip} rate={rate}Bps burst={burst}B queue={qlimit}B"
        )

    # 1. Set the interface to promiscuous mode
    run(["ip", "link", "set", interface, "promisc", "on"])

    # 2. Create the input ‘qdisc’
    run_best_effort(["tc", "qdisc", "add", "dev", interface, "handle", "ffff:", "ingress"])

    # 3. Redirect everything coming in (ingress) directly to the output (egress)
    run([
        "tc", "filter", "add", "dev", interface, "parent", "ffff:",
        "protocol", "all", "u32", "match", "u32", "0", "0",
        "action", "mirred", "egress", "redirect", "dev", interface
    ])
    print("[TS] Boomerang (mirred) successfully configured.")


# enable shaping, called by controller
def enable_shaping():
    interface = STATE["interface"]
    config = STATE["config"]
    if STATE["enabled"]:
        return
    ensure_interface_up(interface)
    setup_shaping(interface, config)
    STATE["enabled"] = True
    print("[TS] shaping ENABLED")

# disable shaping, called by controller
def disable_shaping():
    interface = STATE["interface"]
    if not STATE["enabled"]:
        return
    clear_tc(interface)
    STATE["enabled"] = False
    print("[TS] shaping DISABLED")


def main():
    config = load_config("traffic_shaping.yaml")
    interface = config["interface"]
    STATE["interface"] = interface
    STATE["config"] = config

    def shutdown_handler(signum, frame):
        print("[TS] stopping and cleaning tc rules")
        disable_shaping()
        clear_tc(interface)
        sys.exit(0)

    def enable_handler(signum, frame):
        enable_shaping()

    def disable_handler(signum, frame):
        disable_shaping()

    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGUSR1, enable_handler)
    signal.signal(signal.SIGUSR2, disable_handler)

    print(f"[TS] starting on interface {interface}")
    ensure_interface_up(interface)
    clear_tc(interface)
    print("[TS] shaping is OFF (waiting for controller signal)")

    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()