# -*- coding: utf-8 -*-
"""
Created on Tue May  6 19:54:49 2025

@author: baroc
"""

import subprocess
import json
import os
import glob
from tqdm.auto import tqdm


# === CONFIG ===
tshark_path = r"C:\\Program Files\\Wireshark\\tshark.exe"
editcap_path = r"C:\\Program Files\\Wireshark\\editcap.exe"
capinfos_path = r"C:\\Program Files\\Wireshark\\capinfos.exe"

pcap_file = "bigFlows.pcap"
batch_dir = "batches"
output_json = "full_capture_bigFlows.json"
batch_size = 1000

os.makedirs(batch_dir, exist_ok=True)

# === Step 1: Split PCAP ===
split_pattern = os.path.join(batch_dir, "batch_%03d.pcap")
if not glob.glob(os.path.join(batch_dir, "*.pcap")):
    print("Splitting PCAP...")
    subprocess.run([editcap_path, "-c", str(batch_size), pcap_file, split_pattern])
else:
    print("Batches already exist — skipping split.")

# === Step 2: Global metadata (excluding file_name) ===
capinfos_result = subprocess.run(
    [capinfos_path, pcap_file],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)
stdout = capinfos_result.stdout.decode('utf-8', errors='replace')

file_metadata = {
    k.strip().replace(" ", "_").lower(): v.strip()
    for line in stdout.strip().splitlines()
    if ':' in line
    for k, v in [line.split(':', 1)]
}
file_metadata.pop("file_name", None)

# === Helper to flatten packets ===
def flatten_packet(pkt, file_metadata):
    row = {}
    layers = pkt.get("_source", {}).get("layers", {})

    allowed_protocols = {
        # Layer 2 & 3
        "frame", "eth", "ethertype", "dot1q", "llc", "stp", "mpls", "ip", "ipv6", "arp",

        # Layer 4
        "tcp", "udp", "icmp", "icmpv6",

        # Transport/Tunneling/VPN
        "ipsec", "gre", "vxlan", "l2tp", "pptp", "openvpn",

        # Common Application Protocols
        "http", "http2", "tls", "ssl", "quic",
        "dns", "bootp", "dhcp", "ldap", "ntp",
        "ssdp", "nbns", "mdns", "smb", "kerberos",
        "ftp", "telnet", "smtp", "pop", "imap",

        # Real-time Streaming / VoIP
        "rtsp", "rtp", "rtcp", "sip",

        # IoT / Messaging
        "mqtt", "coap", "diameter",

        # Financial Industry Protocols
        "fix", "swift", "iso8583", "cme", "bloomberg", "marketdata",

        # Generic Data Container (unparsed payloads)
        "data"
    }

    for proto, fields in layers.items():
        if proto not in allowed_protocols:
            continue
        if isinstance(fields, list):
            merged = {}
            for item in fields:
                if isinstance(item, dict):
                    merged.update(item)
            fields = merged
        if isinstance(fields, dict):
            for key, value in fields.items():
                col = f"{proto}.{key}"
                row[col] = str(value[0]) if isinstance(value, list) else str(value)

    row.update(file_metadata)
    return row

# === Step 3: Process and stream-write packets ===
batch_files = sorted(glob.glob(os.path.join(batch_dir, "*.pcap")))

print("Processing batches and writing packets to JSON...")

with open(output_json, "w", encoding="utf-8") as out_f:
    out_f.write("[\n")
    first = True

    for batch_num, batch_file in enumerate(batch_files):
        print(f"\nBatch {batch_num + 1}/{len(batch_files)}: {os.path.basename(batch_file)}")

        result = subprocess.run(
            [
                tshark_path,
                "-r", batch_file,
                "-T", "json",
                "-x",
                "-n",
                "-s", "0",
                "-d", "udp.port==53,dns",
                "-d", "udp.port==443,quic",
                "-d", "tcp.port==443,tls",
                "--enable-protocol", "dns",
                "--enable-protocol", "quic",
                "--enable-protocol", "tls"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        stdout = result.stdout.decode('utf-8', errors='replace')

        if not stdout.strip():
            print("Empty batch — skipping.")
            continue

        try:
            packets = json.loads(stdout)
        except json.JSONDecodeError:
            print("JSON error — skipping.")
            continue

        for pkt in tqdm(packets, desc=f"Batch {batch_num + 1}", unit="pkt"):
            row = flatten_packet(pkt, file_metadata)
            if not first:
                out_f.write(",\n")
            else:
                first = False
            json.dump(row, out_f)

    out_f.write("\n]\n")

print(f"\n JSON saved to: {output_json}")
