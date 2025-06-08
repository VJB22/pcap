# -*- coding: utf-8 -*-
"""
Created on Fri May 30 14:04:48 2025

@author: baroc
"""
import pickle
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# === Load Graph ===
with open("graph_model_CICIDS_log.pkl", "rb") as f:
    G = pickle.load(f)

# === Load Workload-Level Data ===
df = pd.read_parquet("C:/Users/baroc/Downloads/all_workloads_CICIDS.parquet")
df = df.dropna(subset=['mac_src', 'ip_src', 'src_port', 'mac_dst', 'ip_dst', 'dst_port'])

# === Load Artifact Classification Output ===
df_2 = pd.read_csv("C:/Users/baroc/Downloads/final_workload_node_dataset.csv")
print(df_2.columns.tolist())


# === 7.1.1 SCORE VALIDATION: Class Distribution Check ===
plt.figure(figsize=(8, 5))
sns.countplot(data=df_2, x='top_artifact', order=df_2['top_artifact'].value_counts().index)
plt.title("Distribution of Top Artifact Classes (Node Level)")
plt.xlabel("Artifact Type")
plt.ylabel("Node Count")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Table 1: Artifact Class Distribution
class_dist_table = df_2['top_artifact'].value_counts().reset_index()
class_dist_table.columns = ['Artifact Type', 'Node Count']
print(class_dist_table.to_markdown(index=False))

# Table 2: Confidence Margin Summary
conf_summary = df_2['artifact_confidence'].describe(percentiles=[.05, .25, .5, .75, .95])
conf_summary = conf_summary.round(4)
print(conf_summary.to_frame(name='Confidence Margin').to_markdown())

# === 7.1.2 FEATURE INTERPRETATION: Boxplots by Artifact Type ===
features = [
    'degree', 'flows', 'session_volatility', 'ttl_variability',
    'external_ratio', 'role_score', 'avg_flow_duration'
]

for feat in features:
    plt.figure(figsize=(8, 6))
    sns.boxplot(x='top_artifact', y=feat, data=df_2)
    plt.xticks(rotation=45)
    plt.title(f'{feat} by Artifact Type (Node Level)')
    plt.tight_layout()
    plt.show()

summary_1 = df_2.groupby('top_artifact')[features].agg(['mean', 'std', 'min', 'max']).round(2)
print(summary_1.to_markdown())

# === BOOTSTRAP 95% CI for Artifact-Wise Feature Means ===
def bootstrap_ci(data, n_bootstraps=1000, ci=95):
    boot_means = np.array([
        data.sample(frac=1, replace=True).mean()
        for _ in range(n_bootstraps)
    ])
    lower = np.percentile(boot_means, (100 - ci) / 2, axis=0)
    upper = np.percentile(boot_means, 100 - (100 - ci) / 2, axis=0)
    return lower, upper

print("\n=== Bootstrap 95% CI for Artifact-wise Feature Means ===")
for artifact in df_2['top_artifact'].unique():
    artifact_data = df_2[df_2['top_artifact'] == artifact][features]
    lower, upper = bootstrap_ci(artifact_data)
    ci_df = pd.DataFrame({'Lower 95% CI': lower, 'Upper 95% CI': upper}, index=features)
    print(f"\nArtifact: {artifact}")
    print(ci_df.round(2).to_markdown())


# === 7.1.2 FEATURE INTERPRETATION: Correlation Analysis ===
plt.figure(figsize=(8, 6))
sns.heatmap(df_2[features].corr(), annot=True, cmap='coolwarm')
plt.title("Feature Correlation Heatmap (Node Level)")
plt.tight_layout()
plt.show()

# === 7.1.2 CENTRALITY PATTERNS ===
if 'community_size' not in df_2.columns:
    comm_counts = df_2['community'].value_counts().to_dict()
    df_2['community_size'] = df_2['community'].map(comm_counts)

centrality_features = ['degree', 'role_score', 'community_size']

for feat in centrality_features:
    plt.figure(figsize=(8, 4))
    sns.boxplot(x='top_artifact', y=feat, data=df_2)
    plt.title(f'{feat.replace("_", " ").capitalize()} by Artifact Type (Node Level)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

# Component type distribution (node-level)
plt.figure(figsize=(8, 4))
sns.countplot(x='top_artifact', hue='component_type', data=df_2)
plt.title("Component Type Distribution by Artifact Type (Node Level)")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Descriptive statistics table
summary_2 = df_2.groupby('top_artifact')[centrality_features].agg(
    ['count', 'mean', 'std', 'min', 'median', 'max', lambda x: x.nunique()]
)
summary_2.columns = ['_'.join(col).replace('<lambda_0>', 'nunique') for col in summary_2.columns]
summary_2 = summary_2.round(3)

print("\n=== Centrality Pattern Summary Table ===")
print(summary_2.to_markdown())

# === 7.1.2 COMMUNITY HOMOGENEITY ===
community_diversity = df_2.groupby('community')['top_artifact'].nunique()
plt.figure(figsize=(8, 4))
sns.histplot(community_diversity, bins=range(1, community_diversity.max() + 2), discrete=True)
plt.title("Artifact Diversity per Community (Node Level)")
plt.xlabel("Unique Artifact Types")
plt.ylabel("Community Count")
plt.tight_layout()
plt.show()

div_table = community_diversity.value_counts().sort_index().reset_index()
div_table.columns = ['# Unique Artifact Types', '# Communities']
print(div_table.to_markdown(index=False))




