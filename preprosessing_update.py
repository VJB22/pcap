# -*- coding: utf-8 -*-
"""
Created on Sat May 10 14:50:49 2025

@author: baroc
"""

import hashlib
import ipaddress
import pyarrow as pa
import pyarrow.parquet as pq
import os
import pandas as pd
import duckdb
import numpy as np


def extract_fields(row):
    try:
        epoch = float(row.get('frame.frame.time_epoch'))
        epoch_minute = int(epoch // 60)
        epoch_second = int(epoch)
    except:
        epoch_minute = None
        epoch_second = None

    # === Handle mdns.Queries ===
    mdns_query_name = None
    mdns_query_type = None
    mdns_query_name_raw = None

    try:
        if 'mdns.Queries' in row:
            import ast
            queries = ast.literal_eval(row['mdns.Queries']) if isinstance(row['mdns.Queries'], str) else row['mdns.Queries']
            for q in queries.values():
                if isinstance(q, dict):
                    mdns_query_name = q.get('dns.qry.name')
                    mdns_query_type = q.get('dns.qry.type')
                    mdns_query_name_raw = q.get('dns.qry.name_raw')
                    break
    except Exception:
        pass

    dns_query = (
        row.get('dns.qry.name') or
        row.get('dns.query.name') or
        row.get('dns.questions.name') or
        mdns_query_name
    )

    dns_response = (
        row.get('dns.resp.name') or
        row.get('dns.answers.name') or
        row.get('dns.a') or
        row.get('dns.ns') or
        row.get('mdns.dns.resp.name')
    )

    dns_query_type = row.get('dns.qry.type') or mdns_query_type
    dns_query_name_raw = row.get('dns.qry.name_raw') or mdns_query_name_raw

    return {
        'mac_src': row.get('eth.eth.src'),
        'mac_dst': row.get('eth.eth.dst'),
        'frame_len': row.get('frame.frame.len'),
        'frame_time_epoch': row.get('frame.frame.time_epoch'),
        'epoch_minute': epoch_minute,
        'epoch_second': epoch_second,
        'ip_proto': row.get('ip.ip.proto'),
        'ip_flags': row.get('ip.ip.flags'),
        'ip_src': row.get('ip.ip.src'),
        'ip_dst': row.get('ip.ip.dst'),
        'udp_srcport': row.get('udp.udp.srcport'),
        'udp_dstport': row.get('udp.udp.dstport'),
        'tcp_srcport': row.get('tcp.tcp.srcport'),
        'tcp_dstport': row.get('tcp.tcp.dstport'),
        'tls_is_handshake': (
            any(str(ct).startswith('22') for ct in row.get('tls.record.content_type_raw', []))
            if isinstance(row.get('tls.record.content_type_raw'), list)
            else str(row.get('tls.record.content_type', '')).startswith('22')),
        'tls_record_version': row.get('tls.record.version') or row.get('tls.tls.record.version'),
        'fix_msg_type': row.get('fix.fix.msg_type'),
        'swift_field': row.get('swift.swift.field'),
        'iso8583_field': row.get('iso8583.iso8583.field'),
        'dns_query': dns_query,
        'dns_response': dns_response,
        'dns_query_type': dns_query_type,
        'dns_query_name_raw': str(dns_query_name_raw) if dns_query_name_raw is not None else None,
        'rtsp_method': row.get('rtsp.rtsp.method'),
        'rtp_seq': row.get('rtp.rtp.seq'),
        'rtcp_sr': row.get('rtcp.rtcp.ssrc'),
        'icmp_type': row.get('icmp.icmp.type'),
        'igmp_type': row.get('igmp.igmp.type'),
        'arp_src_hw_mac': row.get('arp.arp.src.hw_mac'),
    }

def ip_is_internal(ip):
    try:
        return ipaddress.ip_address(ip).is_private
    except:
        return None

def classify_flow(src, dst):
    if src and not dst:
        return 'internal_to_external'
    elif not src and dst:
        return 'external_to_internal'
    elif src and dst:
        return 'internal_only'
    elif src is False and dst is False:
        return 'external_only'
    return 'unknown'

def build_workload_id_src(e):
    parts = [
        str(e.get("mac_src", "")),
        str(e.get("ip_src", "")),
        str(e.get("src_port", ""))
    ]
    return hashlib.sha1("|".join(parts).encode()).hexdigest()

def build_workload_id_dst(e):
    parts = [
        str(e.get("mac_dst", "")),
        str(e.get("ip_dst", "")),
        str(e.get("dst_port", ""))
    ]
    return hashlib.sha1("|".join(parts).encode()).hexdigest()

def is_virtual_mac(mac):
    if not isinstance(mac, str): return False
    return mac.upper()[:8] in {
        '00:05:69', '00:0C:29', '00:1C:14', '00:50:56',
        '08:00:27', '00:03:FF', '52:54:00', '00:15:5D'
    }

def stream_process_json(json_path, out_parquet):
    import ijson

    buffer = []

    with open(json_path, 'rb') as f:
        parser = ijson.items(f, 'item')
        for row in parser:
            entry = extract_fields(row)
            entry['src_port'] = entry['tcp_srcport'] or entry['udp_srcport']
            entry['dst_port'] = entry['tcp_dstport'] or entry['udp_dstport']
            entry['ip_ttl'] = row.get('ip.ip.ttl')
            entry['src_is_internal'] = ip_is_internal(entry['ip_src'])
            entry['dst_is_internal'] = ip_is_internal(entry['ip_dst'])
            entry['flow_relation'] = classify_flow(entry['src_is_internal'], entry['dst_is_internal'])
            entry['mac_ip_combo'] = f"{entry['mac_src']}|{entry['ip_src']}"
            entry['workload_id_src'] = build_workload_id_src(entry)
            entry['workload_id_dst'] = build_workload_id_dst(entry)
            entry['is_virtual_machine'] = is_virtual_mac(entry['mac_src'])
            entry['is_tls_without_http'] = entry['tls_is_handshake'] and entry['tcp_dstport'] != 80
            # Heuristic fallback for encrypted handshakes (e.g., TLS 1.3 with ECH)
            entry['is_probably_tls_handshake'] = (
                entry['tcp_dstport'] in [443, 8443, 9443] and
                60 <= int(entry.get('frame_len') or 0) <= 250 and
                not entry.get('tls_record_version')  # no parsed TLS metadata (likely encrypted)
            )
            entry['is_large_frame'] = int(entry.get('frame_len') or 0) > 1400
            entry['is_quic'] = (entry['udp_dstport'] == 443) and not entry.get('tls_record_version')
            entry['is_dns_query'] = bool(entry.get('dns_query'))
            entry['is_dns_response'] = bool(entry.get('dns_response'))

            # Flat protocol flags (booleans)
            entry['has_tcp'] = entry['tcp_srcport'] is not None or entry['tcp_dstport'] is not None
            entry['has_udp'] = entry['udp_srcport'] is not None or entry['udp_dstport'] is not None
            entry['has_tls'] = entry['tls_record_version'] is not None
            entry['has_fix'] = entry['fix_msg_type'] is not None
            entry['has_iso8583'] = entry['iso8583_field'] is not None
            entry['has_swift'] = entry['swift_field'] is not None
            entry['has_rtsp'] = entry['rtsp_method'] is not None
            entry['has_rtp'] = entry['rtp_seq'] is not None
            entry['has_rtcp'] = entry['rtcp_sr'] is not None
            entry['has_icmp'] = entry['icmp_type'] is not None
            entry['has_igmp'] = entry['igmp_type'] is not None
            entry['has_arp'] = entry['arp_src_hw_mac'] is not None

            buffer.append(entry)

    df = pd.DataFrame(buffer)
    
    df['epoch_minute'] = pd.to_numeric(df['epoch_minute'], errors='coerce')

    df['financial_suspect_score'] = (
        df['is_tls_without_http'].astype(int) * 3 +
        df['is_large_frame'].astype(int) +
        df['is_dns_query'].astype(int) +
        df['is_quic'].astype(int) +
        df['tcp_dstport'].apply(lambda p: int(p in [443, 8443, 8080, 5000, 9000]) if pd.notnull(p) else 0) +
        df['udp_dstport'].apply(lambda p: int(p in [161, 162, 830]) if pd.notnull(p) else 0) +
        df['fix_msg_type'].notnull().astype(int) * 4 +
        df['swift_field'].notnull().astype(int) * 4 +
        df['iso8583_field'].notnull().astype(int) * 4
    )
    df['is_likely_financial'] = df['financial_suspect_score'] >= 4


    # Ensure numeric conversion
    df['frame_time_epoch'] = pd.to_numeric(df['frame_time_epoch'], errors='coerce')
    df['frame_len'] = pd.to_numeric(df['frame_len'], errors='coerce')
    df['tcp_dstport'] = pd.to_numeric(df['tcp_dstport'], errors='coerce')
    df['udp_dstport'] = pd.to_numeric(df['udp_dstport'], errors='coerce')

    # === Source workload logic ===
    session_len_src = df['frame_time_epoch'].groupby(df['workload_id_src']).agg(lambda x: x.max() - x.min())
    df['session_length_src'] = df['workload_id_src'].map(session_len_src)
    df['session_length_src'] = df.groupby('workload_id_src')['frame_time_epoch'].transform(lambda x: x.max() - x.min())
    avg_payload_src = df['frame_len'].groupby(df['workload_id_src']).mean()
    df['avg_payload_size_src'] = df['workload_id_src'].map(avg_payload_src)
    df['is_data_heavy_src'] = df['avg_payload_size_src'] > 800
    df['is_fin_api_pattern_src'] = df['is_tls_without_http'] & df['is_data_heavy_src']

    # === Destination workload logic ===
    session_len_dst = df['frame_time_epoch'].groupby(df['workload_id_dst']).agg(lambda x: x.max() - x.min())
    df['session_length_dst'] = df['workload_id_dst'].map(session_len_dst)
    df['session_length_dst'] = df.groupby('workload_id_dst')['frame_time_epoch'].transform(lambda x: x.max() - x.min())
    avg_payload_dst = df['frame_len'].groupby(df['workload_id_dst']).mean()
    df['avg_payload_size_dst'] = df['workload_id_dst'].map(avg_payload_dst)

    # === Traffic patterns ===
    df['is_data_heavy_dst'] = df['avg_payload_size_dst'] > 800
    df['is_fin_api_pattern_dst'] = df['is_tls_without_http'] & df['is_data_heavy_dst']

    data_vol = df.groupby('mac_ip_combo')['frame_len'].sum()
    df['data_volume'] = df['mac_ip_combo'].map(data_vol)
    df['is_data_intensive'] = df['data_volume'] > df['data_volume'].quantile(0.60)  # lower quantile

    # Updated session volatility using session_length_src
    session_volatility_src = df.groupby('mac_ip_combo')['session_length_src'].std()
    df['session_volatility'] = df['mac_ip_combo'].map(session_volatility_src)
    df['is_stable_workload'] = df['session_volatility'] < df['session_volatility'].median()

    # Compliance check using session_length_src
    df['is_compliance_sensitive'] = (df['flow_relation'] == 'internal_only') & (
        df['session_length_src'] > df['session_length_src'].median())

    # Classify backend/gateway logic using dst-side API patterns
    df['is_api_backend'] = df['is_fin_api_pattern_dst'] & df['is_data_heavy_dst']
    df['is_gateway_pattern'] = df['is_fin_api_pattern_dst'] & ~df['is_data_heavy_dst']
    
    
    def infer_artifact(row):
        # Serverless: stable session, low overhead, TLS, bursty, often stateless
        if row['is_fin_api_pattern_dst'] and row['is_stable_workload'] and row['is_bursty_dst']:
            return 'serverless'
    
        # Orchestrated Container: container-like, but fan-out/fan-in + orchestration signs
        elif row['is_possible_container_dst'] and row['peer_count_dst'] >= 5 and row['is_bursty_dst']:
            return 'orchestrated_container'
    
        # Mini-VM: signs of virtualization, stable and lower overhead than full VM
        elif row['is_virtual_machine'] and row['is_stable_workload'] and not row['is_data_intensive']:
            return 'mini_vm'
    
        # Full VM: virtualized, longer sessions, heavier load
        elif row['is_virtual_machine'] and (row['is_data_intensive'] or not row['is_stable_workload']):
            return 'vm'
    
        # Container: stateless-ish, volatile, frequent port reuse
        elif row['is_possible_container_dst']:
            return 'container'
    
        # Baremetal: stable, high data volume, physical, often long sessions
        elif row['is_physical_machine'] and row['is_data_intensive'] and row['is_compliance_sensitive']:
            return 'baremetal'
    
        return 'unknown'
    
    df.loc[df['is_fin_api_pattern_dst'] & df['is_stable_workload'], 'inferred_artifact_type'] = 'serverless'
    df.loc[df['is_api_backend'] & ~df['is_stable_workload'], 'inferred_artifact_type'] = 'vm'
    df.loc[df['is_gateway_pattern'], 'inferred_artifact_type'] = 'load_balancer'
    df.loc[df['is_stable_workload'] & df['is_data_intensive'], 'inferred_artifact_type'] = 'container'
    df.loc[df['is_compliance_sensitive'], 'inferred_artifact_type'] = 'baremetal'
    
    # === INFRASTRUCTURE HEURISTICS ===
    ip_mac_df = df.groupby('ip_src')['mac_src'].nunique()
    switch_ips = set(ip_mac_df[ip_mac_df > 3].index)
    df['is_possible_switch'] = df['ip_src'].isin(switch_ips)

    macs_as_src = set(df['mac_src'])
    macs_as_dst = set(df['mac_dst'])
    df['is_forward_only_mac'] = df['mac_src'].isin(macs_as_src - macs_as_dst)
    df['is_broadcast'] = df['mac_dst'] == 'ff:ff:ff:ff:ff:ff'
    df['is_possible_switch'] |= df['is_forward_only_mac'] | df['is_broadcast']

    def classify_router(row):
        if row['flow_relation'] in ['external_to_internal', 'internal_to_external', 'external_only']:
            return 'external_router'
        elif row['flow_relation'] == 'internal_only' and row['src_is_internal'] and row['dst_is_internal']:
            return 'internal_router'
        return 'client'

    df['dst_role'] = 'client'
    df.loc[df['flow_relation'].isin(['external_to_internal', 'internal_to_external', 'external_only']),'dst_role'] = 'external_router'
    df.loc[(df['flow_relation'] == 'internal_only') & df['src_is_internal'] & df['dst_is_internal'],'dst_role'] = 'internal_router'

    ip_mac_count = df.groupby('ip_src')['mac_src'].nunique()
    ip_reuse_threshold = ip_mac_count.median()
    df['is_possible_vm_by_ip_reuse'] = df['ip_src'].map(ip_mac_count) > ip_reuse_threshold

    # Session volatility (container heuristic) per workload_id_src and dst
    session_counts_src = df.groupby('mac_ip_combo')['workload_id_src'].nunique()
    df['session_volatility_src'] = df['mac_ip_combo'].map(session_counts_src)
    df['is_possible_container_src'] = df['session_volatility_src'] > df['session_volatility_src'].quantile(0.65)

    session_counts_dst = df.groupby('mac_ip_combo')['workload_id_dst'].nunique()
    df['session_volatility_dst'] = df['mac_ip_combo'].map(session_counts_dst)
    df['is_possible_container_dst'] = df['session_volatility_dst'] > df['session_volatility_dst'].quantile(0.65)

    ttl_std = df.groupby('mac_ip_combo')['ip_ttl'].std()
    df['ttl_variability'] = df['mac_ip_combo'].map(ttl_std)
    df['is_ttl_unstable'] = df['ttl_variability'] > (ttl_std.median() + ttl_std.std())

    virtual_flags = (
        df['is_virtual_machine'] |
        df['is_possible_vm_by_ip_reuse'] |
        df['is_possible_container_src'] |
        df['is_possible_container_dst'] |
        df['is_ttl_unstable']
    )
    df['is_physical_machine'] = ~virtual_flags
    
    
    def score_serverless(row):
        return 1.0 * row['is_fin_api_pattern_dst'] + \
               1.0 * row['is_stable_workload'] + \
               1.0 * row['is_bursty_dst']

    def score_container(row):
        return 1.0 * row['is_possible_container_dst'] + \
               1.0 * row['is_data_heavy_dst']
    
    def score_orch_container(row):
        return 1.0 * row['is_possible_container_dst'] + \
               (row['peer_count_dst'] / 10 if pd.notnull(row['peer_count_dst']) else 0)
    
    def score_vm(row):
        return 1.0 * row['is_virtual_machine'] + \
               1.0 * row['is_data_intensive']
    
    def score_minivm(row):
        return 1.0 * row['is_virtual_machine'] + \
               1.0 * row['is_stable_workload'] * (1.0 - row['is_data_intensive'])
    
    def score_baremetal(row):
        return 1.0 * row['is_physical_machine'] + \
               1.0 * row['is_data_intensive'] + \
               1.0 * row['is_compliance_sensitive']
    
    # Apply score and ranking
    def rank_artifact_types(row):
        scores = {
            'serverless': score_serverless(row),
            'container': score_container(row),
            'orchestrated_container': score_orch_container(row),
            'vm': score_vm(row),
            'mini_vm': score_minivm(row),
            'baremetal': score_baremetal(row)
        }
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        row['artifact_type_ranked'] = [t[0] for t in ranked]
        row['artifact_type_top'] = ranked[0][0]
        row['artifact_type_top_score'] = ranked[0][1]
        return row
  

    # --- Additional fallback: assign VM if virtual indicators ---
    df.loc[(df['inferred_artifact_type'] == 'unknown') &
           (df['is_virtual_machine'] | df['is_possible_vm_by_ip_reuse']),
           'inferred_artifact_type'] = 'vm'
    
    # --- Fallback: assign Container if container-like volatility ---
    df.loc[(df['inferred_artifact_type'] == 'unknown') &
           (df['is_possible_container_dst'] | df['is_possible_container_src']),
           'inferred_artifact_type'] = 'container'
    
    # --- Fallback: assign based on router/switch roles ---
    df.loc[(df['inferred_artifact_type'] == 'unknown') &
           (df['dst_role'].str.contains('router')), 'inferred_artifact_type'] = 'vm'
    
    df.loc[(df['inferred_artifact_type'] == 'unknown') &
           (df['is_possible_switch']), 'inferred_artifact_type'] = 'baremetal'
    
    # --- Fallback: assign container if stable + heavy ---
    df.loc[(df['inferred_artifact_type'] == 'unknown') &
           (df['is_data_heavy_dst'] & df['is_stable_workload']),
           'inferred_artifact_type'] = 'container'
    
# === COMMUNICATION PATTERNS ===

    # Persistence per src and dst workload
    active_sec_src = df.groupby('workload_id_src')['frame_time_epoch'].agg(lambda x: x.max() - x.min())
    df['active_seconds_src'] = df['workload_id_src'].map(active_sec_src)
    active_sec_dst = df.groupby('workload_id_dst')['frame_time_epoch'].agg(lambda x: x.max() - x.min())
    df['active_seconds_dst'] = df['workload_id_dst'].map(active_sec_dst)
    conn_count_src = df.groupby('workload_id_src')['frame_time_epoch'].count()
    df['connection_count_src'] = df['workload_id_src'].map(conn_count_src)
    conn_count_dst = df.groupby('workload_id_dst')['frame_time_epoch'].count()
    df['connection_count_dst'] = df['workload_id_dst'].map(conn_count_dst)

    # Symmetry / Delay
    df['bytes_sent'] = df.groupby(['mac_src', 'ip_src'])['frame_len'].transform('sum')
    df['bytes_received'] = df.groupby(['mac_dst', 'ip_dst'])['frame_len'].transform('sum')

    df['response_delay_src'] = df.groupby('workload_id_src')['frame_time_epoch'].transform(
    lambda x: np.median(np.diff(np.sort(x))) if len(x) > 1 else 0)
    df['response_delay_dst'] = df.groupby('workload_id_dst')['frame_time_epoch'].transform(
    lambda x: np.median(np.diff(np.sort(x))) if len(x) > 1 else 0)

    # Fanout / Fanin
    peer_src = df.groupby(['mac_src', 'ip_src'])['ip_dst'].nunique()
    peer_dst = df.groupby(['mac_dst', 'ip_dst'])['ip_src'].nunique()
    df['peer_count_src'] = df.set_index(['mac_src', 'ip_src']).index.map(peer_src)
    df['peer_count_dst'] = df.set_index(['mac_dst', 'ip_dst']).index.map(peer_dst)

    # Rhythmic behavior
    minute_count_src = df.groupby('workload_id_src')['epoch_minute'].nunique()
    df['active_minute_count_src'] = df['workload_id_src'].map(minute_count_src)
    burstiness_ratio = df['active_minute_count_src'] / (df['active_seconds_src'] / 60).clip(lower=1)
    df['is_bursty_src'] = burstiness_ratio < burstiness_ratio.median()

    minute_count_dst = df.groupby('workload_id_dst')['epoch_minute'].nunique()
    df['active_minute_count_dst'] = df['workload_id_dst'].map(minute_count_dst)
    burstiness_ratio = df['active_minute_count_dst'] / (df['active_seconds_dst'] / 60).clip(lower=1)
    df['is_bursty_dst'] = burstiness_ratio < burstiness_ratio.median()
    
    
    scores = pd.DataFrame({
        'serverless': df['is_fin_api_pattern_dst'].astype(int)
                     + df['is_stable_workload'].astype(int)
                     + df['is_bursty_dst'].astype(int),
        
        'container': df['is_possible_container_dst'].astype(int)
                     + df['is_data_heavy_dst'].astype(int),
        
        'orchestrated_container': df['is_possible_container_dst'].astype(int)
                     + (df['peer_count_dst'] / 10.0).fillna(0),
        
        'vm': df['is_virtual_machine'].astype(int)
              + df['is_data_intensive'].astype(int)
              + (df['response_delay_dst'].fillna(0) / 10),  # Add delay signal for VM
        
        'mini_vm': df['is_virtual_machine'].astype(int)
                   + df['is_stable_workload'].astype(int) * (1 - df['is_data_intensive'].astype(int)),
        
        'baremetal': df['is_physical_machine'].astype(int)
               + df['is_data_intensive'].astype(int)
               + df['is_compliance_sensitive'].astype(int)
               + (df['response_delay_dst'].fillna(0) / 10),  # Add delay signal for baremetal
    })
    
    # Normalize scores safely
    score_values = scores.values
    row_sums = score_values.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1  # prevent division by 0
    
    normalized_scores = score_values / row_sums
    
    # Avoid log(0) by using a safe clipped version
    safe_scores = np.clip(normalized_scores, 1e-12, 1.0)
    
    df['artifact_type_entropy'] = -np.sum(safe_scores * np.log(safe_scores), axis=1)
            
    df['artifact_type_top'] = scores.idxmax(axis=1)
    df['artifact_type_top_score'] = scores.max(axis=1)
    df['artifact_type_ranked'] = scores.apply(lambda row: list(row.sort_values(ascending=False).index), axis=1)
    
    # Fallback: assign top artifact when entropy is low and no label exists
    low_entropy_thresh = 0.75
    df.loc[df['inferred_artifact_type'].isnull() & (df['artifact_type_entropy'] < low_entropy_thresh),
       'inferred_artifact_type'] = df['artifact_type_top']

    # Absolute fallback: if any labels are still missing, use the top-ranked one
    df.loc[df['inferred_artifact_type'].isnull() & df['artifact_type_top'].notnull(),
       'inferred_artifact_type'] = df['artifact_type_top']
    
    # Fallback: assign top artifact when entropy is low and no label exists
    low_entropy_thresh = 0.75  # Tunable
    df.loc[df['inferred_artifact_type'].isnull() & (df['artifact_type_entropy'] < low_entropy_thresh),
       'inferred_artifact_type'] = df['artifact_type_top']
    
    # Save to Parquet
    table = pa.Table.from_pandas(df)
    pq.write_table(table, out_parquet)


# ---------------- Entry Point ----------------
json_file = "C:/Users/baroc/Downloads/full_capture/full_capture.json"
parquet_file = "C:/Users/baroc/Downloads/all_workloads.parquet"

if os.path.exists(parquet_file):
    os.remove(parquet_file)

stream_process_json(json_file, parquet_file)


# ---------------DUCKDB: VIEW DATA & SAVE --------
# Load the Parquet file
parquet_file = "C:/Users/baroc/Downloads/all_workloads.parquet"
con = duckdb.connect()

# Helper function for labeled output
def show(title, query):
    print(f"\n==== {title} ====")
    print(con.execute(query).df())

# Preview
show("Sample Preview (20 rows)", f"""
    SELECT * FROM parquet_scan('{parquet_file}') LIMIT 20
""")


# workloads (initiators vs responders)
show("WORKLOADS: Count of Source and Destination Workloads", f"""
    SELECT
        COUNT(workload_id_src) AS src_workloads,
        COUNT(workload_id_dst) AS dst_workloads
    FROM parquet_scan('{parquet_file}')
""")


# Unique workloads (initiators vs responders)
show("WORKLOADS: Count of Unique Source and Destination Workloads", f"""
    SELECT
        COUNT(DISTINCT workload_id_src) AS unique_src_workloads,
        COUNT(DISTINCT workload_id_dst) AS unique_dst_workloads
    FROM parquet_scan('{parquet_file}')
""")

# --------- TRAFFIC PATTERN ANALYSIS ----------------

''' packet characteristics, volume, protocols, and infrastructure '''

# Frame and TTL stats
show("TRAFFIC: Frame Size and TTL Distribution", f"""
    SELECT
        AVG(CAST(frame_len AS DOUBLE)) AS avg_frame_len,
        MAX(CAST(frame_len AS DOUBLE)) AS max_frame_len,
        MIN(CAST(frame_len AS DOUBLE)) AS min_frame_len,
        AVG(CAST(ip_ttl AS DOUBLE)) AS avg_ttl,
        MAX(CAST(ip_ttl AS DOUBLE)) AS max_ttl,
        MIN(CAST(ip_ttl AS DOUBLE)) AS min_ttl
    FROM parquet_scan('{parquet_file}')
""")

# Add Workload Counts by Protocol Involvement
show("WORKLOADS: Count of Protocol Usage by Unique Workloads", f"""
    SELECT
        COUNT(DISTINCT workload_id_src) FILTER (WHERE has_tls) AS tls_src,
        COUNT(DISTINCT workload_id_dst) FILTER (WHERE has_tls) AS tls_dst,
        COUNT(DISTINCT workload_id_src) FILTER (WHERE has_fix) AS fix_src,
        COUNT(DISTINCT workload_id_dst) FILTER (WHERE has_fix) AS fix_dst,
        COUNT(DISTINCT workload_id_src) FILTER (WHERE has_iso8583) AS iso8583_src,
        COUNT(DISTINCT workload_id_dst) FILTER (WHERE has_iso8583) AS iso8583_dst
    FROM parquet_scan('{parquet_file}')
""")

# Protocol usage summary
show("TRAFFIC: Protocol Presence", f"""
    SELECT
        SUM(has_tcp::INT) AS tcp,
        SUM(has_udp::INT) AS udp,
        SUM(has_tls::INT) AS tls,
        SUM(has_fix::INT) AS fix,
        SUM(has_iso8583::INT) AS iso8583,
        SUM(has_swift::INT) AS swift,
        SUM(has_rtsp::INT) AS rtsp,
        SUM(has_rtp::INT) AS rtp,
        SUM(has_rtcp::INT) AS rtcp,
        SUM(has_icmp::INT) AS icmp,
        SUM(has_arp::INT) AS arp,
        SUM(has_igmp::INT) AS igmp
    FROM parquet_scan('{parquet_file}')
""")

# TLS/QUIC/DNS
show("TRAFFIC: DNS & QUIC/TLS Detection", f"""
    SELECT
        SUM(is_dns_query::INT) AS dns_queries,
        SUM(is_dns_response::INT) AS dns_responses,
        SUM(is_quic::INT) AS quic_suspected,
        SUM(is_tls_without_http::INT) AS tls_wo_http
    FROM parquet_scan('{parquet_file}')
""")



# Financial flags
show("TRAFFIC: Financial Protocol Activity", f"""
    SELECT
        SUM(is_likely_financial::INT) AS likely_financial_flows,
        AVG(financial_suspect_score) AS avg_score,
        MAX(financial_suspect_score) AS max_score
    FROM parquet_scan('{parquet_file}')
""")

# Switches, Routers, Machines
show("TRAFFIC: Switch Detection", f"""
    SELECT COUNT(*) AS possible_switches
    FROM parquet_scan('{parquet_file}')
    WHERE is_possible_switch
""")

show("TRAFFIC: Router Roles", f"""
    SELECT dst_role, COUNT(*) AS count
    FROM parquet_scan('{parquet_file}')
    GROUP BY dst_role
""")

show("TRAFFIC: Virtual/Physical Host Summary", f"""
    SELECT
        SUM(is_virtual_machine::INT) AS vm_oui,
        SUM(is_possible_vm_by_ip_reuse::INT) AS vm_by_ip_reuse,
        SUM(is_possible_container_src::INT + is_possible_container_dst::INT) AS containers,
        SUM(is_ttl_unstable::INT) AS ttl_unstable,
        SUM(is_physical_machine::INT) AS physical_hosts
    FROM parquet_scan('{parquet_file}')
""")


# -------- COMMUNICATION PATTERN ANALYSIS ---------

'''behavior over time, interaction, and flow characteristics'''

# Communication Persistence (source & destination)
show("COMM: Persistence by Workload Source", f"""
    SELECT
        ROUND(AVG(active_seconds_src), 2) AS avg_active_seconds_src,
        ROUND(MAX(active_seconds_src), 2) AS max_active_seconds_src,
        ROUND(AVG(connection_count_src), 2) AS avg_connection_count_src,
        COUNT(*) FILTER (WHERE active_seconds_src > 60) AS sessions_over_1_minute_src
    FROM parquet_scan('{parquet_file}')
""")

show("COMM: Persistence by Workload Destination", f"""
    SELECT
        ROUND(AVG(active_seconds_dst), 2) AS avg_active_seconds_dst,
        ROUND(MAX(active_seconds_dst), 2) AS max_active_seconds_dst,
        ROUND(AVG(connection_count_dst), 2) AS avg_connection_count_dst,
        COUNT(*) FILTER (WHERE active_seconds_dst > 60) AS sessions_over_1_minute_dst
    FROM parquet_scan('{parquet_file}')
""")

# Symmetry & Delay
show("COMM: Traffic Symmetry & Delay", f"""
    SELECT
        ROUND(AVG(bytes_sent), 2) AS avg_bytes_sent,
        ROUND(AVG(bytes_received), 2) AS avg_bytes_received,
        ROUND(AVG(response_delay_src), 2) AS avg_response_delay_src,
        ROUND(AVG(response_delay_dst), 2) AS avg_response_delay_dst,
        MAX(response_delay_src) AS max_response_delay_src,
        MAX(response_delay_dst) AS max_response_delay_dst
    FROM parquet_scan('{parquet_file}')
""")

# Fan-in / Fan-out
show("COMM: Fan-in and Fan-out", f"""
    SELECT
        ROUND(AVG(peer_count_src), 2) AS avg_fanout,
        ROUND(MAX(peer_count_src), 2) AS max_fanout,
        ROUND(AVG(peer_count_dst), 2) AS avg_fanin,
        ROUND(MAX(peer_count_dst), 2) AS max_fanin
    FROM parquet_scan('{parquet_file}')
""")

# Rhythmicity
show("COMM: Bursty vs Rhythmic Behavior", f"""
    SELECT
        COUNT(*) FILTER (WHERE is_bursty_src) AS bursty_src,
        COUNT(*) FILTER (WHERE NOT is_bursty_src) AS rhythmic_src,
        COUNT(*) FILTER (WHERE is_bursty_dst) AS bursty_dst,
        COUNT(*) FILTER (WHERE NOT is_bursty_dst) AS rhythmic_dst
    FROM parquet_scan('{parquet_file}')
""")

# Suitable deployment artifact
show("Suitable Deployment Artifact Types", f"""
    SELECT
        inferred_artifact_type,
        COUNT(*) AS count
    FROM parquet_scan('{parquet_file}')
    GROUP BY inferred_artifact_type
    ORDER BY count DESC
""")

show("Fallback Probabilities for None-Labeled Artifacts", f"""
    SELECT
        artifact_type_top,
        COUNT(*) AS count
    FROM parquet_scan('{parquet_file}')
    WHERE inferred_artifact_type IS NULL
    GROUP BY artifact_type_top
    ORDER BY count DESC
""")

example_path = "C:/Users/baroc/Downloads/example_head20.csv"
df_head = con.execute(f"SELECT * FROM parquet_scan('{parquet_file}') LIMIT 20").df()
df_head.to_csv(example_path, index=False)
print(f"Saved: {example_path}")
