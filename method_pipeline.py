# -*- coding: utf-8 -*-
"""
Created on Fri May 16 16:46:16 2025

@author: baroc
"""

# === PCAP Artifact Inference Pipeline ===

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from collections import defaultdict
import community.community_louvain as community_louvain   
import torch
from torch_geometric.data import Data
from torch_geometric.nn import SAGEConv
import torch.nn.functional as F
import torch.nn as nn

# === Config ===
random_seed = 42
np.random.seed(random_seed)

ARTIFACT_TYPES = ['baremetal', 'vm', 'container', 'serverless', 'orchestrated_container', 'mini_vm']
ARTIFACT_MAP = {name: idx for idx, name in enumerate(ARTIFACT_TYPES)}

# === Load Data ===
df = pd.read_parquet("C:/Users/baroc/Downloads/all_workloads.parquet")
print("Loaded DataFrame shape:", df.shape)

# Downcast numeric columns for memory efficiency
for col in ['bytes_sent', 'bytes_received', 'response_delay_src', 'response_delay_dst',
            'session_length_src', 'session_length_dst', 'connection_count_src', 'connection_count_dst',
            'ttl_variability']:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], downcast='float')

def infer_device_role(row):
    if row['dst_role'] in ['internal_router', 'external_router']:
        return row['dst_role']
    elif row['is_possible_switch']:
        return 'switch'
    elif row['is_broadcast'] or row['is_forward_only_mac']:
        return 'network_core'
    else:
        return 'client'

df['device_role'] = df.apply(infer_device_role, axis=1)

# === Initialize Graph ===
G_attr = nx.Graph()

# === Add Workload Nodes (artifact info only) ===
workload_attrs = df.groupby('workload_id_src').agg({
    'artifact_type_top': 'first',
    'artifact_type_top_score': 'first'
}).reset_index()

for _, row in workload_attrs.iterrows():
    G_attr.add_node(row['workload_id_src'],
                    type='workload',
                    artifact_type_top=row['artifact_type_top'],
                    artifact_type_top_score=row['artifact_type_top_score'])

# Add missing workloads (dst not in src)
all_workloads = pd.concat([df['workload_id_src'], df['workload_id_dst']]).unique()
for wid in all_workloads:
    if not G_attr.has_node(wid):
        G_attr.add_node(wid, type='workload', artifact_type_top=None, artifact_type_top_score=None)

# === Add Device Nodes (infra heuristics) and Edges ===
for _, row in df.iterrows():
    src, dst, device = row['workload_id_src'], row['workload_id_dst'], row['device_role']
    device = device if pd.notna(device) else f"unknown_{src}_{dst}"

    location, dev_type = ('unknown', device) if '_' not in device else device.split('_', 1)

    if not G_attr.has_node(device):
        G_attr.add_node(device, type='device_role',
                        device_type=dev_type,
                        location=location,
                        device_role=row['device_role'],
                        is_possible_switch=row.get('is_possible_switch', False),
                        is_broadcast=row.get('is_broadcast', False),
                        is_forward_only_mac=row.get('is_forward_only_mac', False))

    edge_attrs = {k: (np.float32(row[k]) if pd.notna(row[k]) else None) for k in [
        'bytes_sent', 'bytes_received', 'response_delay_src', 'response_delay_dst',
        'session_length_src', 'session_length_dst', 'connection_count_src',
        'connection_count_dst', 'is_bursty_src', 'is_bursty_dst', 'ttl_variability'
    ]}

    G_attr.add_edge(src, device, **edge_attrs)
    G_attr.add_edge(device, dst, **edge_attrs)

# === Summary ===
print(f"Graph built: {G_attr.number_of_nodes()} nodes, {G_attr.number_of_edges()} edges")
print("Sample nodes:", list(G_attr.nodes(data=True))[:3])
print("Sample edges:", list(G_attr.edges(data=True))[:3])


# === Community Detection ===
partition = community_louvain.best_partition(G_attr)  # {node_id: community_id}

# Assign community to nodes
nx.set_node_attributes(G_attr, partition, 'community')
community_dict = defaultdict(list)
for node, comm in partition.items():
    community_dict[comm].append(node)

# Summary
print(f"Detected {len(community_dict)} communities.")

# Inspect top 5 communities (safe version)
for comm_id, nodes in list(community_dict.items())[:5]:
    workloads = [n for n in nodes if G_attr.nodes[n].get('type') == 'workload']
    print(f"Community {comm_id}: {len(nodes)} nodes, {len(workloads)} workloads")

# Plot
colors = [partition[n] for n in G_attr.nodes()]
plt.figure(figsize=(10, 8))
pos = nx.spring_layout(G_attr, seed=random_seed)
nx.draw_networkx_nodes(G_attr, pos, node_color=colors, cmap=plt.cm.tab20, node_size=50)
nx.draw_networkx_edges(G_attr, pos, alpha=0.2, width=0.5)
plt.title("Louvain Communities")
plt.axis("off")
plt.show()

# === Community Profiles ===
def get_edge_features(node):
    """Collect edge features for a node, replacing None with np.nan for safe aggregation."""
    metrics = defaultdict(list)
    for _, _, data in G_attr.edges(node, data=True):
        def safe_get(key):
            val = data.get(key, np.nan)
            return val if val is not None else np.nan

        metrics['session_length'].append(safe_get('session_length_src'))
        metrics['connection_count'].append(safe_get('connection_count_src'))
        metrics['is_bursty'].append(safe_get('is_bursty_src'))
        metrics['bytes_sent'].append(safe_get('bytes_sent'))
        metrics['bytes_received'].append(safe_get('bytes_received'))
        metrics['ttl_variability'].append(safe_get('ttl_variability'))

    return metrics

community_profiles = {}

for comm_id, nodes in community_dict.items():
    agg = defaultdict(list)
    for node in nodes:
        metrics = get_edge_features(node)
        for k, v in metrics.items():
            agg[k].extend(v)

    # Aggregate metrics per community (use np.nanmean for safety)
    profile = {
        'avg_session_length': np.nanmean(agg['session_length']) if agg['session_length'] else np.nan,
        'avg_connection_count': np.nanmean(agg['connection_count']) if agg['connection_count'] else np.nan,
        'bursty_ratio': np.nanmean(agg['is_bursty']) if agg['is_bursty'] else np.nan,
        'avg_bytes_sent': np.nanmean(agg['bytes_sent']) if agg['bytes_sent'] else np.nan,
        'avg_bytes_received': np.nanmean(agg['bytes_received']) if agg['bytes_received'] else np.nan,
        'avg_ttl_variability': np.nanmean(agg['ttl_variability']) if agg['ttl_variability'] else np.nan,
    }

    community_profiles[comm_id] = profile

# Assign profiles to all nodes
for node in G_attr.nodes():
    comm_id = G_attr.nodes[node]['community']
    G_attr.nodes[node]['community_profile'] = community_profiles[comm_id]

# Inspect a few profiles
for comm_id, profile in list(community_profiles.items())[:5]:
    print(f"Community {comm_id} Profile:", profile)


# === Compute global medians for community profile metrics ===
metrics = ['bursty_ratio', 'avg_session_length', 'avg_bytes_sent', 'avg_bytes_received', 'avg_ttl_variability']
global_medians = {}

for metric in metrics:
    values = [v for cp in community_profiles.values() if (v := cp.get(metric)) is not None and not np.isnan(v)]
    global_medians[metric] = np.median(values) if values else 0.0

print("Global medians computed:", global_medians)

# === Clean NaNs in graph nodes ===
for node, data in G_attr.nodes(data=True):
    cp = data.get('community_profile', {})
    if cp:
        for k in metrics:
            val = cp.get(k, global_medians[k])
            cp[k] = global_medians[k] if val is None or np.isnan(val) else val

    if 'entropy' in data:
        val = data['entropy']
        data['entropy'] = 0.0 if (val is None or np.isnan(val)) else val


# === Compute Graph Metrics ===
# Compute metrics
degree = dict(G_attr.degree())
betweenness = nx.betweenness_centrality(G_attr, normalized=True)
closeness = nx.closeness_centrality(G_attr)
pagerank = nx.pagerank(G_attr)

# Assign metrics to nodes
for node in G_attr.nodes():
    G_attr.nodes[node]['degree'] = degree[node]
    G_attr.nodes[node]['betweenness'] = betweenness[node]
    G_attr.nodes[node]['closeness'] = closeness[node]
    G_attr.nodes[node]['pagerank'] = pagerank[node]

# Preview
print("\nSample node metrics:")
for node, data in list(G_attr.nodes(data=True))[:5]:
    print(f"{node}: degree={data['degree']}, betweenness={data['betweenness']:.4f}, pagerank={data['pagerank']:.4f}")
    
# === Role Mining: Assign functional roles to nodes ===
def assign_role(node, data):
    node_type = data.get('type', 'unknown')

    if node_type == 'device_role':
        return data.get('device_type', 'unknown')
    elif node_type == 'workload':
        deg = data.get('degree', 0)
        betw = data.get('betweenness', 0)
        close = data.get('closeness', 0)
        pagerank = data.get('pagerank', 0)
        entropy = data.get('entropy', 0)
        bursty = data.get('community_profile', {}).get('bursty_ratio', 0.0)
        session_len = data.get('community_profile', {}).get('avg_session_length', 0.0)

        # === Role assignment rules ===
        if deg > 10 and betw > 0.05 and pagerank > 0.01:
            return 'orchestrator'
        elif betw > 0.02 and pagerank > 0.01 and any('router' in G_attr.nodes[n].get('device_type', '') for n in G_attr.neighbors(node)):
            return 'api_gateway'
        elif close > 0.3 and (bursty > 0.5 or entropy > 0.5):
            return 'frontend'
        elif session_len > 1000 and bursty < 0.5 and entropy < 0.3 and pagerank < 0.01:
            return 'backend'
        elif deg <= 1:
            return 'singleton'
        else:
            return 'backend'  # Fallback
    else:
        return 'unknown'  # Handle missing or invalid type

# Apply role assignment
for node, data in G_attr.nodes(data=True):
    G_attr.nodes[node]['role'] = assign_role(node, data)

# Preview
print("\nSample node roles:")
for node, data in list(G_attr.nodes(data=True))[:5]:
    print(f"{node}: role={data['role']}")
    
    

# # === GNN Setup: Build per-community Data objects ===
# # Artifact mapping (consistent across pipeline)
# artifact_map = {'baremetal': 0, 'vm': 1, 'container': 2, 'serverless': 3, 'orchestrated_container': 4, 'mini_vm': 5}
# artifact_types = list(artifact_map.keys())

# gnn_batches = []

# for comm_id, nodes in community_dict.items():
#     node_to_idx = {node: idx for idx, node in enumerate(nodes)}
    
#     edges = []
#     for node in nodes:
#         for neighbor in G_attr.neighbors(node):
#             if neighbor in node_to_idx:
#                 edges.append([node_to_idx[node], node_to_idx[neighbor]])
#     if not edges:
#         continue
    
#     edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
    
#     # Build node features and labels
#     node_features = []
#     labels = []
#     for node in nodes:
#         d = G_attr.nodes[node]
#         f = [
#             d.get('degree', 0),
#             d.get('betweenness', 0),
#             d.get('closeness', 0),
#             d.get('pagerank', 0),
#             d.get('community', 0),
#             d.get('entropy', 0),
#             int(d.get('is_physical_machine', False)),
#             int(d.get('is_possible_vm_by_ip_reuse', False)),
#             int(d.get('is_possible_container_src', False)),
#             int(d.get('is_possible_container_dst', False)),
#             int(d.get('role') == 'backend'),
#             int(d.get('role') == 'frontend'),
#             int(d.get('role') == 'orchestrator'),
#             int(d.get('role') == 'api_gateway'),
#         ]
#         node_features.append(f)
#         labels.append(artifact_map.get(d.get('artifact_type_top'), -1))

#     x = torch.tensor(node_features, dtype=torch.float)
#     y = torch.tensor(labels, dtype=torch.long)

#     # Store batch with node IDs for mapping back
#     gnn_batches.append(Data(x=x, edge_index=edge_index, y=y, node_ids=list(nodes)))

# print(f"Built {len(gnn_batches)} batches.")


# # === GNN Model Definition ===
# class ArtifactGNN(nn.Module):
#     def __init__(self, in_channels, hidden_channels, out_channels):
#         super().__init__()
#         self.conv1 = SAGEConv(in_channels, hidden_channels)
#         self.conv2 = SAGEConv(hidden_channels, hidden_channels)
#         self.lin = nn.Linear(hidden_channels, out_channels)

#     def forward(self, x, edge_index):
#         x = self.conv1(x, edge_index)
#         x = F.relu(x)
#         x = self.conv2(x, edge_index)
#         x = F.relu(x)
#         return self.lin(x)

# # === Initialize Model ===
# in_dim = gnn_batches[0].x.shape[1]
# out_dim = len(artifact_map)
# model = ArtifactGNN(in_channels=in_dim, hidden_channels=32, out_channels=out_dim)

# optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

# # === Train on Batches ===
# print("\nTraining GNN on community batches...")

# for epoch in range(1, 201):
#     model.train()
#     total_loss = 0
#     valid_batches = 0
#     for batch in gnn_batches:
#         optimizer.zero_grad()
#         out = model(batch.x, batch.edge_index)
#         mask = batch.y != -1
#         if mask.sum() == 0:
#             continue
#         loss = F.cross_entropy(out[mask], batch.y[mask])
#         loss.backward()
#         optimizer.step()
#         total_loss += loss.item()
#         valid_batches += 1

#     if epoch % 20 == 0 and valid_batches > 0:
#         avg_loss = total_loss / valid_batches
#         print(f"Epoch {epoch:03d} - Avg Loss: {avg_loss:.4f}")
        
# # === Map Predictions Back to Graph ===
# print("\nMapping GNN predictions back to graph nodes...")

# model.eval()
# with torch.no_grad():
#     for batch in gnn_batches:
#         out = model(batch.x, batch.edge_index).softmax(dim=1)
#         for idx, node in enumerate(batch.node_ids):
#             G_attr.nodes[node]['artifact_gnn_probs'] = out[idx].tolist()
#             G_attr.nodes[node]['artifact_gnn_top1'] = int(out[idx].argmax())
            
            
# # === Final Artifact Ranking ===
# artifact_map_rev = {v: k for k, v in artifact_map.items()}

# # --- Scoring functions ---
# def bias_vector(node):
#     role = G_attr.nodes[node].get('role', '')
#     entropy = G_attr.nodes[node].get('entropy', 0)
#     deg = G_attr.nodes[node].get('degree', 0)
#     betw = G_attr.nodes[node].get('betweenness', 0)

#     bias = np.zeros(len(artifact_map))
#     if role == 'backend':
#         bias[artifact_map['vm']] += 0.5
#         bias[artifact_map['mini_vm']] += 0.3
#     elif role == 'frontend':
#         bias[artifact_map['container']] += 0.5
#     elif role == 'orchestrator':
#         bias[artifact_map['orchestrated_container']] += 0.7
#     elif role == 'api_gateway':
#         bias[artifact_map['serverless']] += 0.7
#     elif role == 'singleton':
#         bias[artifact_map['serverless']] += 0.3

#     if entropy > 0.5:
#         bias[artifact_map['container']] += 0.3
#         bias[artifact_map['serverless']] += 0.3
#     else:
#         bias[artifact_map['vm']] += 0.3

#     if deg > 10:
#         bias[artifact_map['container']] += 0.2
#     if betw > 0.05:
#         bias[artifact_map['serverless']] += 0.2

#     return bias

# def final_scores(node):
#     gnn_probs = np.array(G_attr.nodes[node].get('artifact_gnn_probs', [0] * len(artifact_map)))
#     biases = bias_vector(node)

#     # Add an edge-based bias term (e.g., avg bytes_sent over edges)
#     edges = list(G_attr.edges(node, data=True))
#     avg_bytes = np.mean([e[2].get('bytes_sent', 0) or 0 for e in edges]) if edges else 0
#     edge_boost = np.zeros(len(artifact_map))
#     if avg_bytes > 1e6:  # Example threshold
#         edge_boost[artifact_map['vm']] += 0.1

#     combined = gnn_probs + biases + edge_boost
#     combined /= combined.sum() if combined.sum() > 0 else 1

#     sorted_artifacts = sorted(
#         ((artifact_map_rev[i], float(combined[i])) for i in range(len(artifact_map))),
#         key=lambda x: -x[1]
#     )
#     return dict(sorted_artifacts)

# # === Compute final scores ONCE per node ===
# final_scores_cache = {node: final_scores(node) for node in G_attr.nodes()}

# # === Build chain recommendations ===
# chain_recommendations = []

# for device in [n for n in G_attr.nodes() if G_attr.nodes[n]['type'] == 'device_role']:
#     neighbors = list(G_attr.neighbors(device))
#     if len(neighbors) < 2:
#         continue

#     for i in range(len(neighbors)):
#         for j in range(i + 1, len(neighbors)):
#             w1, w2 = neighbors[i], neighbors[j]
#             if G_attr.nodes[w1]['type'] != 'workload' or G_attr.nodes[w2]['type'] != 'workload':
#                 continue

#             chain_recommendations.append({
#                 'workload_1': w1,
#                 'workload_1_artifacts': final_scores_cache[w1],
#                 'device': device,
#                 'device_role': G_attr.nodes[device].get('device_type', 'unknown'),
#                 'workload_2': w2,
#                 'workload_2_artifacts': final_scores_cache[w2],
#             })

# # === Convert to DataFrame ===
# chain_df = pd.DataFrame(chain_recommendations)
# print(chain_df.head())

# VALIDATE? -> Human-labeled ground truth: Ask domain experts to review and confirm artifact types for a representative sample of nodes.