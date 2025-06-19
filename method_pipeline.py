# -*- coding: utf-8 -*-
"""
Created on Fri May 16 16:46:16 2025

@author: baroc
"""
import pandas as pd
import numpy as np
import networkx as nx
from sklearn.decomposition import NMF
from networkx.algorithms.community import louvain_communities
import pickle

np.random.seed(42)

# === Load Data ===
df = pd.read_parquet("C:/Users/baroc/Downloads/all_workloads_CICIDS.parquet")
df = df.dropna(subset=['mac_src', 'ip_src', 'src_port', 'mac_dst', 'ip_dst', 'dst_port'])

for col in ['bytes_sent', 'bytes_received', 'response_delay_src', 'response_delay_dst', 'session_length_src',
            'session_length_dst', 'ttl_variability', 'frame_time_epoch']:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], downcast='float', errors='coerce')
df['flows'] = 1

# === Graph Building ===
df['device_role'] = np.where(df['dst_role'].isin(['internal_router', 'external_router']),
                             df['dst_role'],
                             np.where(df['is_possible_switch'], 'switch',
                                      np.where(df['is_broadcast'] | df['is_forward_only_mac'], 'network_core', 'client')))
device_roles = dict(zip(df['workload_id_src'], df['device_role']))

pairs = df[['workload_id_src', 'workload_id_dst']].apply(tuple, axis=1).values
pairs_unique, idx = np.unique(pairs, return_inverse=True)
flows = np.bincount(idx, weights=df['flows'].values)
bytes_sent = np.bincount(idx, weights=df['bytes_sent'].values)
bytes_received = np.bincount(idx, weights=df['bytes_received'].values)

start_time = np.full(len(pairs_unique), np.inf)
end_time = np.full(len(pairs_unique), -np.inf)
np.minimum.at(start_time, idx, df['frame_time_epoch'].values)
np.maximum.at(end_time, idx, df['frame_time_epoch'].values)

G = nx.Graph()
for (src, dst), f, bs, br, st, et in zip(pairs_unique, flows, bytes_sent, bytes_received, start_time, end_time):
    G.add_edge(src, dst, flows=f, weight=bs + br, start_time=st, end_time=et, duration=et - st)
nx.set_node_attributes(G, device_roles, 'device_role')

# === Node Attributes ===
nodes = np.array(list(G.nodes()))
node_idx = {n: i for i, n in enumerate(nodes)}

def aggregate_attr(attr):
    vals = df[attr].values
    agg = np.zeros(len(nodes))
    counts = np.zeros(len(nodes))
    for col in ['workload_id_src', 'workload_id_dst']:
        idxs = np.vectorize(node_idx.get)(df[col].values, -1)
        mask = idxs >= 0
        np.add.at(agg, idxs[mask], vals[mask])
        np.add.at(counts, idxs[mask], 1)
    return agg / np.maximum(counts, 1)

for attr in ['session_volatility_src', 'ttl_variability']:
    nx.set_node_attributes(G, dict(zip(nodes, aggregate_attr(attr))), attr.replace('_src', ''))

for n in nodes:
    durs = [G[n][nbr]['duration'] for nbr in G.neighbors(n)]
    G.nodes[n]['avg_flow_duration'] = np.mean(durs) if durs else 0

# === ReFeX + NMF ===
neighbors = {n: set(G.neighbors(n)) for n in nodes}
refex = pd.DataFrame({
    'degree': [G.degree(n) for n in nodes],
    'egonet_size': [G.degree(n) + 1 for n in nodes],
    'egonet_edges': [sum(1 for u in neighbors[n] for v in neighbors[u] if v in neighbors[n]) for n in nodes],
    'egonet_out_edges': [sum(1 for v in neighbors[n] if any(nb not in neighbors[n] for nb in G.neighbors(v))) for n in nodes]
}, index=nodes)

for _ in range(3):
    refex = pd.DataFrame({
        n: {f'mean_{k}': refex.loc[list(neighbors[n])][k].mean() if neighbors[n] else 0 for k in refex.columns} |
           {f'max_{k}': refex.loc[list(neighbors[n])][k].max() if neighbors[n] else 0 for k in refex.columns}
        for n in nodes
    }).T.fillna(0)

X = refex.values
best_n = range(2, 10)[np.argmin([
    np.linalg.norm(X - NMF(n, init='random', random_state=42).fit_transform(X)
                    .dot(NMF(n, init='random', random_state=42).fit(X).components_), ord='fro') for n in range(2, 10)])]
W = NMF(best_n, init='random', random_state=42).fit_transform(X)
nx.set_node_attributes(G, dict(zip(nodes, np.mean(W, axis=1))), 'role_score')

# === Louvain + Component Type ===
communities = louvain_communities(G, weight='weight', seed=42)
for idx, comm in enumerate(communities):
    for n in comm:
        G.nodes[n]['community'] = idx
    subG = G.subgraph(comm)
    degs = np.array([subG.degree(n) for n in comm])
    c = nx.average_clustering(subG) if len(subG) > 1 else 0
    t = "Singleton" if len(subG) == 1 else "Hub/Star" if degs.max() > 3 and degs[degs > 1].mean() > 2 else "Dense Cluster" if c > 0.5 else "Chain" if np.all(degs <= 2) else "Mixed/Other"
    for n in comm:
        G.nodes[n]['component_type'] = t

for n in nodes:
    flows = [G[n][nbr].get('flows', 0) for nbr in G.neighbors(n)]
    ext = [f for nbr, f in zip(G.neighbors(n), flows) if G.nodes[nbr].get('device_role') == 'external_router']
    G.nodes[n]['external_ratio'] = sum(ext) / sum(flows) if sum(flows) else 0

# === Node Metadata ===
node_meta = pd.concat([
    df[['workload_id_src', 'mac_src', 'ip_src', 'src_port']].rename(
        columns={'workload_id_src': 'workload_id', 'mac_src': 'mac', 'ip_src': 'ip', 'src_port': 'port'}),
    df[['workload_id_dst', 'mac_dst', 'ip_dst', 'dst_port']].rename(
        columns={'workload_id_dst': 'workload_id', 'mac_dst': 'mac', 'ip_dst': 'ip', 'dst_port': 'port'})
]).drop_duplicates()

# === Extract Node Features ===
def extract_node_features(G):
    return pd.DataFrame({
        'workload_id': list(G.nodes()),
        'degree': [G.degree(n) for n in G.nodes()],
        'flows': [sum(G[n][nbr]['flows'] for nbr in G.neighbors(n)) for n in G.nodes()],
        'session_volatility': [G.nodes[n].get('session_volatility', 0) for n in G.nodes()],
        'ttl_variability': [G.nodes[n].get('ttl_variability', 0) for n in G.nodes()],
        'component_type': [G.nodes[n].get('component_type', '') for n in G.nodes()],
        'external_ratio': [G.nodes[n].get('external_ratio', 0) for n in G.nodes()],
        'role_score': [G.nodes[n].get('role_score', 0) for n in G.nodes()],
        'avg_flow_duration': [G.nodes[n].get('avg_flow_duration', 0) for n in G.nodes()],
        'community': [G.nodes[n].get('community', -1) for n in G.nodes()]
    })

node_features = extract_node_features(G)
node_meta_filtered = node_meta[node_meta['workload_id'].isin(G.nodes())]
df_node_final = node_meta_filtered.merge(node_features, on='workload_id', how='left')
df_node_final.to_csv("final_workload_node_dataset_2.csv", index=False)
print(df_node_final.head())

# save model
with open("graph_model_CICIDS_cd.pkl", "wb") as f:
     pickle.dump(G, f)
