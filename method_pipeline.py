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
    'egonet_edges': [
        sum(1 for u in neighbors[n] for v in neighbors[u] if v in neighbors[n])
        for n in nodes
    ],
    'egonet_out_edges': [
        sum(1 for v in neighbors[n]
            if any(nb not in neighbors[n] for nb in G.neighbors(v)))
        for n in nodes
    ]
}, index=nodes)

for _ in range(3):
    refex = pd.DataFrame({
        n: {
            f'mean_{k}': refex.loc[list(neighbors[n])][k].mean() if neighbors[n] else 0
            for k in refex.columns
        } | {
            f'max_{k}': refex.loc[list(neighbors[n])][k].max() if neighbors[n] else 0
            for k in refex.columns
        }
        for n in nodes
    }).T.fillna(0)

X = refex.values

# === NMF: fit once per k and select best ===
errors = []
models = []
for k in range(2, 10):
    model = NMF(k, init='random', random_state=42)
    W_tmp = model.fit_transform(X)
    H_tmp = model.components_
    errors.append(np.linalg.norm(X - W_tmp @ H_tmp, ord='fro'))
    models.append(model)

best_idx = int(np.argmin(errors))
best_model = models[best_idx]
best_n = list(range(2, 10))[best_idx]

# Final role matrices
W = best_model.transform(X)
H = best_model.components_

# === Store scalar node role score ===
nx.set_node_attributes(G, dict(zip(nodes, np.mean(W, axis=1))), 'role_score')

# === Store full H matrix for role interpretation ===
G.graph['role_definitions'] = H  # shape: (k × features)


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

# === Add primary role and role description from NMF ===
primary_role = W.argmax(axis=1)
H_df = pd.DataFrame(H, columns=refex.columns)
top_features = {
    i: ", ".join(H_df.loc[i].nlargest(3).index)
    for i in range(H.shape[0])
}
df_node_final['primary_role'] = primary_role
df_node_final['role_description'] = df_node_final['primary_role'].map(top_features)

df_node_final.to_csv("final_workload_node_dataset_3.csv", index=False)
print(df_node_final.head())

# save model
with open("graph_model_CICIDS_cd_H.pkl", "wb") as f:
     pickle.dump(G, f)


# ------ visualize and interpret H matrix ------
import matplotlib.pyplot as plt
import seaborn as sns

rename_map = {
    # Degree
    'μ_max_max_degree': 'Max Degree (3-hop)',
    'μ_μ_max_degree': 'Mean–Max Degree (2-hop)',
    'μ_max_μ_degree': 'Max–Mean Degree (2-hop)',
    'μ_μ_μ_degree': 'Mean–Mean–Mean Degree',
    'μ_max_μ_ego_size': 'Max–Mean Ego Size',
    
    # Ego Size
    'μ_max_max_ego_size': 'Max Ego Size (3-hop)',
    'μ_μ_max_ego_size': 'Mean–Max Ego Size (2-hop)',
    'μ_μ_μ_ego_size': 'Mean–Mean–Mean Ego Size',
    'μ_max_μ_ego_size': 'Max–Mean Ego Size (2-hop)',
    
    # Ego Out Edges
    'μ_max_max_ego_out_edges': 'Max Ego Out Edges (3-hop)',
    'μ_μ_max_ego_out_edges': 'Mean–Max Ego Out Edges',
    'μ_max_μ_ego_out_edges': 'Max–Mean Ego Out Edges',
    'μ_μ_μ_ego_out_edges': 'Mean–Mean–Mean Ego Out Edges',
    
    # Egonet Edges
    'μ_max_max_egonet_edges': 'Max Egonet Edges (3-hop)',
    'μ_μ_max_egonet_edges': 'Mean–Max Egonet Edges',
    'μ_μ_μ_egonet_edges': 'Mean–Mean–Mean Egonet Edges',
    
    # Egonet Size
    'μ_max_max_egonet_size': 'Max Egonet Size (3-hop)',
    'μ_μ_max_egonet_size': 'Mean–Max Egonet Size',
    'μ_μ_μ_egonet_size': 'Mean–Mean–Mean Egonet Size',
    
    # Egonet Out Edges
    'μ_max_max_ego_out_edges': 'Max Ego Out Edges',
    'μ_μ_max_ego_out_edges': 'Mean–Max Ego Out Edges',
    'μ_μ_μ_ego_out_edges': 'Mean–Mean–Mean Ego Out Edges',
}

# Loop over roles and plot
for i in range(H_df.shape[0]):
    top_feats = H_df.iloc[i].sort_values(ascending=False).head(5)
    
    # Convert to Series, apply mapping, and fall back to original if no match
    display_names = pd.Series(top_feats.index).map(rename_map).fillna(pd.Series(top_feats.index)).tolist()

    plt.figure(figsize=(6, 3))
    sns.barplot(x=top_feats.values, y=display_names, palette="viridis")
    plt.title(f"Top Structural Features: Role {i}")
    plt.xlabel("Weight")
    plt.ylabel("")
    plt.tight_layout()
    plt.show()

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# === Create H_df from your actual H matrix ===
roles = [f"Role {i}" for i in range(H.shape[0])]
H_df = pd.DataFrame(H, index=roles, columns=refex.columns)

# === Apply renaming ===
rename_map = {
    'mean_mean_mean_degree': 'Mean–Mean–Mean Degree',
    'mean_mean_mean_egonet_size': 'Mean–Mean–Mean Egonet Size',
    'mean_mean_mean_egonet_edges': 'Mean–Mean–Mean Egonet Edges',
    'mean_mean_mean_egonet_out_edges': 'Mean–Mean–Mean Out Edges',
    'mean_mean_max_degree': 'Mean–Mean–Max Degree',
    'mean_mean_max_egonet_size': 'Mean–Mean–Max Egonet Size',
    'mean_mean_max_egonet_edges': 'Mean–Mean–Max Egonet Edges',
    'mean_mean_max_egonet_out_edges': 'Mean–Mean–Max Out Edges',
    'mean_max_mean_degree': 'Mean–Max–Mean Degree',
    'mean_max_mean_egonet_size': 'Mean–Max–Mean Egonet Size',
    'mean_max_mean_egonet_edges': 'Mean–Max–Mean Egonet Edges',
    'mean_max_mean_egonet_out_edges': 'Mean–Max–Mean Out Edges',
    'mean_max_max_degree': 'Mean–Max–Max Degree',
    'mean_max_max_egonet_size': 'Mean–Max–Max Egonet Size',
    'mean_max_max_egonet_edges': 'Mean–Max–Max Egonet Edges',
    'mean_max_max_egonet_out_edges': 'Mean–Max–Max Out Edges',
    'max_mean_mean_degree': 'Max–Mean–Mean Degree',
    'max_mean_mean_egonet_size': 'Max–Mean–Mean Egonet Size',
    'max_mean_mean_egonet_edges': 'Max–Mean–Mean Egonet Edges',
    'max_mean_mean_egonet_out_edges': 'Max–Mean–Mean Out Edges',
    'max_mean_max_degree': 'Max–Mean–Max Degree',
    'max_mean_max_egonet_size': 'Max–Mean–Max Egonet Size',
    'max_mean_max_egonet_edges': 'Max–Mean–Max Egonet Edges',
    'max_mean_max_egonet_out_edges': 'Max–Mean–Max Out Edges',
    'max_max_mean_degree': 'Max–Max–Mean Degree',
    'max_max_mean_egonet_size': 'Max–Max–Mean Egonet Size',
    'max_max_mean_egonet_edges': 'Max–Max–Mean Egonet Edges',
    'max_max_mean_egonet_out_edges': 'Max–Max–Mean Out Edges',
    'max_max_max_degree': 'Max–Max–Max Degree',
    'max_max_max_egonet_size': 'Max–Max–Max Egonet Size',
    'max_max_max_egonet_edges': 'Max–Max–Max Egonet Edges',
    'max_max_max_egonet_out_edges': 'Max–Max–Max Out Edges',
}
H_df.rename(columns=rename_map, inplace=True)

# === Get Top 5 Features per Role ===
top_features_per_role = {
    role: H_df.loc[role].sort_values(ascending=False).head(5)
    for role in H_df.index
}

# === Build stacked DataFrame ===
plot_df = pd.DataFrame(index=H_df.index)
for role, series in top_features_per_role.items():
    plot_df.loc[role, series.index] = series.values
plot_df = plot_df.fillna(0)

# === Normalize weights per role ===
plot_df_norm = plot_df.div(plot_df.sum(axis=1), axis=0)

# === Identify most frequent features among top 5 ===
top_feature_names = plot_df.apply(lambda row: row.nlargest(5).index.tolist(), axis=1).explode()
top_10_features = top_feature_names.value_counts().head(10).index

# === Keep only top 10 in plot ===
plot_df_norm = plot_df_norm[top_10_features]

# === Plot ===
fig, ax = plt.subplots(figsize=(12, 6))
plot_df_norm.plot(kind='bar', stacked=True, ax=ax, colormap='tab20')

ax.set_ylabel("Relative Feature Contribution (per Role)")
ax.set_xlabel("Latent Role")
ax.set_title("Top Contributing Features per Role (Top 10 Only)")
ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', title="Feature")
plt.tight_layout()
plt.savefig("stacked_bar_roles_cleaned.png", dpi=300)
plt.show()
