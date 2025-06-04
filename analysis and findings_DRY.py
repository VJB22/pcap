# -*- coding: utf-8 -*-
"""
Created on Fri May 30 14:04:48 2025

@author: baroc
"""
import pickle
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# === Load Graph ===
with open("graph_model_CICIDS.pkl", "rb") as f:
    G = pickle.load(f)

# === Load Workload-Level Data ===
df = pd.read_parquet("C:/Users/baroc/Downloads/all_workloads_CICIDS.parquet")
df = df.dropna(subset=['mac_src', 'ip_src', 'src_port', 'mac_dst', 'ip_dst', 'dst_port'])

# === Load Artifact Classification Output ===
df_2 = pd.read_csv("C:/Users/baroc/Downloads/artifact_exploration.csv")
print(df_2.columns.tolist())

# === 7.1.1 SCORE VALIDATION: Class Distribution Check ===
plt.figure(figsize=(8, 5))
sns.countplot(data=df_2, x='top_artifact', order=df_2['top_artifact'].value_counts().index)
plt.title("Distribution of Top Artifact Classes")
plt.xlabel("Artifact Type")
plt.ylabel("Count")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Table 1: Artifact Class Distribution

# Artifact class distribution table
class_dist_table = df_2['top_artifact'].value_counts().reset_index()
class_dist_table.columns = ['Artifact Type', 'Node Count']
print(class_dist_table.to_markdown(index=False))


# Table 2: Confidence Margin Summary

# Confidence margin = top score - second best
conf_summary = df_2['artifact_confidence'].describe(percentiles=[.05, .25, .5, .75, .95])
conf_summary = conf_summary.round(4)
print(conf_summary.to_frame(name='Confidence Margin').to_markdown())



# === 7.1.2 FEATURE INTERPRETATION: Boxplots by Artifact Type ===

# Compute how many nodes are in each community
comm_counts = df_2['community'].value_counts().to_dict()
# Map size back to each node
df_2['community_size'] = df_2['community'].map(comm_counts)

features = [
    'degree', 'flows', 'session_volatility', 'ttl_variability',
    'external_ratio', 'role_score', 'avg_flow_duration', 'community_size'
]

# Numeric stats
summary_numeric = df_2.groupby('top_artifact')[features].agg(['mean', 'std', 'min', 'max'])

# Component type mode per artifact
summary_component = df_2.groupby('top_artifact')['component_type'].agg(lambda x: x.mode().iloc[0])

# Combine both
summary_numeric[('component_type', 'mode')] = summary_component
summary_combined = summary_numeric.copy()

# Flatten column names
summary_combined.columns = [
    f"{col[0]}_{col[1]}" if isinstance(col, tuple) else col for col in summary_combined.columns
]

summary_combined = summary_combined.round(2)
print(summary_combined.to_markdown())




# === 7.1.2 CENTRALITY PATTERNS ===
# Compute community size for each node
if 'community_size' not in df.columns:
    comm_counts = df_2['community'].value_counts().to_dict()
    df_2['community_size'] = df_2['community'].map(comm_counts)

# Features to analyze
features = ['degree', 'role_score', 'community_size']

# Boxplots: feature vs top_artifact
for feature in features:
    plt.figure(figsize=(8, 4))
    sns.boxplot(x='top_artifact', y=feature, data=df_2)
    plt.title(f'{feature.replace("_", " ").capitalize()} by Artifact Type')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

# Barplot: component type distribution by artifact
plt.figure(figsize=(8, 4))
sns.countplot(x='top_artifact', hue='component_type', data=df_2)
plt.title("Component Type Distribution by Artifact Type")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Descriptive statistics table
summary = df_2.groupby('top_artifact')[features].agg(
    ['count', 'mean', 'std', 'min', 'median', 'max', lambda x: x.nunique()]
)
summary.columns = ['_'.join(col).replace('<lambda_0>', 'nunique') for col in summary.columns]
summary = summary.round(3)

print("\n=== Centrality Pattern Summary Table ===")
print(summary.to_markdown())


# === 7.1.2 COMMUNITY HOMOGENEITY ===
# Count unique artifact types per community
community_diversity = df_2.groupby('community')['top_artifact'].nunique()
plt.figure(figsize=(8, 4))
sns.histplot(community_diversity, bins=range(1, community_diversity.max() + 2), discrete=True)
plt.title("Artifact Diversity per Community")
plt.xlabel("Unique Artifact Types")
plt.ylabel("Community Count")
plt.tight_layout()
plt.show()

div_table = community_diversity.value_counts().sort_index().reset_index()
div_table.columns = ['# Unique Artifact Types', '# Communities']
print(div_table.to_markdown(index=False))
