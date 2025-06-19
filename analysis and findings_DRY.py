# -*- coding: utf-8 -*-
"""
Created on Fri May 30 14:04:48 2025

@author: baroc
"""
import os
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score
import umap.umap_ as umap
import hdbscan
import optuna
from scipy.stats import entropy

# ----------------------------- data ------------------------------
df = pd.read_csv("final_workload_node_dataset_2.csv")
features = [
    "degree", "flows", "session_volatility", "ttl_variability",
    "external_ratio", "role_score", "avg_flow_duration"
]
feature_titles = {
    "degree": "Node Degree",
    "flows": "Flow Count",
    "session_volatility": "Session Volatility",
    "ttl_variability": "TTL Variability",
    "external_ratio": "External Communication Ratio",
    "role_score": "Inferred Role Score",
    "avg_flow_duration": "Average Flow Duration"
}
log_features = ["flows", "session_volatility", "avg_flow_duration"]
df = df.dropna(subset=features)
X_scaled = StandardScaler().fit_transform(df[features].values)

# ----------------------- optuna search --------------------------

study = optuna.create_study(direction="maximize")

def objective(trial):
    min_cluster_size = trial.suggest_int("min_cluster_size", 50, 600)
    min_samples = trial.suggest_int("min_samples", 5, 100)

    hdb = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        cluster_selection_method="eom"
    )
    labels = hdb.fit_predict(X_scaled)
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)

    if n_clusters < 20 or n_clusters > 40:
        return float("-inf")

    dbcv = hdbscan.validity.validity_index(X_scaled, labels)
    return dbcv

study.optimize(objective, n_trials=60, show_progress_bar=False)
best_params = study.best_params

# ------------------- final hdbscan model ------------------------
hdb = hdbscan.HDBSCAN(**best_params, cluster_selection_method="eom")
df["cluster_hdbscan"] = hdb.fit_predict(X_scaled)
agg = AgglomerativeClustering(n_clusters=3)
df["cluster_agg"] = agg.fit_predict(X_scaled)

# ------------------ cluster groups & logs ----------------------
cluster_counts = df["cluster_hdbscan"].value_counts()
valid_clusters = cluster_counts[cluster_counts.index != -1]
top_10 = valid_clusters.head(10).index.tolist()
bottom_10 = valid_clusters.tail(10).index.tolist()
top_10_set, bottom_10_set = set(top_10), set(bottom_10)

for f in log_features:
    df[f"{f}_log"] = np.log10(df[f].clip(lower=1e-3))

script_dir = os.path.dirname(os.path.abspath(__file__))

def save_boxplot(data, feat, clust, ttl, fname):
    plt.figure(figsize=(10, 4))
    sns.boxplot(data=data, x="cluster_hdbscan", y=feat, order=clust, showfliers=True, palette="tab10")
    plt.title(ttl)
    plt.xlabel("Cluster"); plt.ylabel(feat); plt.xticks(rotation=45)
    plt.tight_layout(); plt.savefig(os.path.join(script_dir, fname), dpi=300); plt.close()

def save_scatter(sub, x, y, ttl, fname):
    plt.figure(figsize=(8, 6))
    sns.scatterplot(data=sub, x=x, y=y, hue="cluster_hdbscan", palette="tab20", s=15, legend="brief")
    plt.title(ttl); plt.legend(loc="best", fontsize="x-small", ncol=2)
    plt.tight_layout(); plt.savefig(os.path.join(script_dir, fname), dpi=300); plt.close()

for feat in features:
    pf = f"{feat}_log" if f"{feat}_log" in df.columns else feat
    save_boxplot(df[df["cluster_hdbscan"].isin(top_10_set)], pf, top_10,
                 f"{feature_titles[feat]} (Top 10 Clusters)", f"{pf}_Top10.png")
    save_boxplot(df[df["cluster_hdbscan"].isin(bottom_10_set)], pf, bottom_10,
                 f"{feature_titles[feat]} (Bottom 10 Clusters)", f"{pf}_Bottom10.png")

for feat in features:
    pf = f"{feat}_log" if f"{feat}_log" in df.columns else feat
    means = df.groupby("cluster_hdbscan")[feat].mean()
    ranked_top = means.sort_values(ascending=False).head(10).index.tolist()
    ranked_bottom = means.sort_values().head(10).index.tolist()
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    sns.boxplot(data=df[df["cluster_hdbscan"].isin(ranked_top)], x="cluster_hdbscan", y=pf,
                order=ranked_top, showfliers=True, palette="tab10", ax=axes[0])
    sns.boxplot(data=df[df["cluster_hdbscan"].isin(ranked_bottom)], x="cluster_hdbscan", y=pf,
                order=ranked_bottom, showfliers=True, palette="tab10", ax=axes[1])
    axes[0].set_title(f"Top 10 Clusters by Mean {feature_titles[feat]}")
    axes[1].set_title(f"Bottom 10 Clusters by Mean {feature_titles[feat]}")
    for ax in axes: ax.set_xlabel("Cluster"); ax.set_ylabel(pf); ax.tick_params(axis="x", rotation=45)
    fig.suptitle(f"{feature_titles[feat]}: Cluster Comparison by Mean", fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(os.path.join(script_dir, f"{feat}_TopVsBottom_Comparison.png"), dpi=300)
    plt.close()


# ------------------ Compute UMAP ------------------
umap_emb = umap.UMAP(random_state=42).fit_transform(X_scaled)
df["umap1"], df["umap2"] = umap_emb[:, 0], umap_emb[:, 1]

# ------------------ Save UMAP Plot with Cluster Labels ------------------
def save_umap_all(data, fname, title):
    plt.figure(figsize=(9, 7))
    sns.scatterplot(data=data, x="umap1", y="umap2",
                    hue="cluster_hdbscan", palette="tab20", s=15, legend="brief")

    # Annotate each cluster at its median UMAP coordinates
    for cluster_id in sorted(data["cluster_hdbscan"].unique()):
        subset = data[data["cluster_hdbscan"] == cluster_id]
        x_med = subset["umap1"].median()
        y_med = subset["umap2"].median()
        plt.text(x_med, y_med, str(cluster_id), fontsize=6, ha="center", va="center",
                 bbox=dict(facecolor='white', alpha=0.6, edgecolor='none', boxstyle='round,pad=0.2'))

    plt.title(title)
    plt.legend(loc="upper right", fontsize="xx-small", ncol=3, title="Cluster", title_fontsize="x-small")
    plt.tight_layout()
    plt.savefig(os.path.join(script_dir, fname), dpi=300)
    plt.close()


save_umap_all(df[df["cluster_hdbscan"] != -1], "UMAP_All_Clusters.png", "UMAP Projection of All Clusters")

# ------------------ Clustering Scores ------------------
sil_score = silhouette_score(X_scaled, df["cluster_agg"])
dbcv_score = hdbscan.validity.validity_index(X_scaled, df["cluster_hdbscan"])
print(f"\nSilhouette score (Agglomerative): {sil_score:.4f}")
print(f"DBCV score (HDBSCAN): {dbcv_score:.4f}")

# ------------------ Summary Table ------------------
summary = df.groupby("cluster_hdbscan")[features].agg(["mean", "std", "min", "max"]).round(2)
print("\n=== Summary Table ===\n")
print(summary.to_markdown())

# === Top 10 and Bottom 10 Cluster Descriptive Stats ===
top_df = df[df["cluster_hdbscan"].isin(top_10)]
bottom_df = df[df["cluster_hdbscan"].isin(bottom_10)]

top_summary = top_df.groupby("cluster_hdbscan")[features].agg(["mean", "std", "min", "max"]).round(2)
bottom_summary = bottom_df.groupby("cluster_hdbscan")[features].agg(["mean", "std", "min", "max"]).round(2)
# Loop over features to generate per-feature tables
for feature in features:
    print(f"\n=== Top 10 Clusters: {feature} ===\n")
    top_feat = top_summary[feature]
    print(top_feat.to_markdown())

    print(f"\n=== Bottom 10 Clusters: {feature} ===\n")
    bottom_feat = bottom_summary[feature]
    print(bottom_feat.to_markdown())
    
    
def save_umap_example_cluster(df, cluster_id, fname):
    subset = df[df["cluster_hdbscan"] == cluster_id]
    plt.figure(figsize=(6, 5))
    sns.scatterplot(data=subset, x="umap1", y="umap2", color="red", s=20)
    plt.title(f"UMAP: Cluster {cluster_id}")
    plt.tight_layout()
    plt.savefig(os.path.join(script_dir, fname), dpi=300)
    plt.close()


# save_umap_example_cluster(df, 14, "UMAP_Cluster14.png")
# save_umap_example_cluster(df, 7, "UMAP_Cluster7.png")


save_umap_all(df, "UMAP_All_Clusters_WithNoise.png", "UMAP Projection (Including Noise)")
    
    
    
# ------------------ Structural Interpretation ------------------
df_struct = df.dropna(subset=["community", "component_type"])
community_dist = df_struct.groupby("cluster_hdbscan")["community"].value_counts().unstack(fill_value=0)
component_dist = df_struct.groupby("cluster_hdbscan")["component_type"].value_counts().unstack(fill_value=0)
component_dist_pct = component_dist.div(component_dist.sum(axis=1), axis=0).round(2)

print("\n=== Topological Community Distribution ===\n")
df_all = community_dist.to_markdown()
print(community_dist.head(10).to_markdown())

print("\n=== Component Type Distribution (counts) ===\n")
df_all_1 = component_dist.to_markdown()
print(component_dist.head(10).to_markdown())


# ------------------ Extended Cluster Summary ------------------
summary = df.groupby("cluster_hdbscan")[features].agg(["mean", "std", "min", "max"]).round(2)
summary["n_unique_communities"] = df_struct.groupby("cluster_hdbscan")["community"].nunique()
print("\n=== Extended Cluster Summary ===\n")
print(summary.head(10).to_markdown())

# ------------------ UMAP Colored by Top Communities (Including Noise) ------------------
top_comms = df["community"].value_counts().nlargest(10).index
df_plot = df.copy()
df_plot["community_plot"] = df_plot["community"].where(df_plot["community"].isin(top_comms), "Other")

plt.figure(figsize=(10, 7))
sns.scatterplot(data=df_plot, x="umap1", y="umap2", hue="community_plot", palette="tab10", s=15)
plt.title("UMAP Projection Colored by Community (Top 10 + Other, Including Noise)")
plt.legend(loc="upper center", bbox_to_anchor=(0.5, 1.15), ncol=6, fontsize="x-small", title="Community", title_fontsize="x-small")
plt.tight_layout()
plt.savefig(os.path.join(script_dir, "UMAP_Top10_Communities_WithNoise.png"), dpi=300)
plt.close()


def save_umap_component_type(df, fname, title):
    df_plot = df.dropna(subset=["component_type"])
    plt.figure(figsize=(9, 7))
    sns.scatterplot(data=df_plot, x="umap1", y="umap2", hue="component_type", palette="tab10", s=15)
    plt.title(title)
    plt.legend(loc="best", fontsize="x-small")
    plt.tight_layout()
    plt.savefig(os.path.join(script_dir, fname), dpi=300)
    plt.close()

# ------------------ Community Diversity (Entropy) ------------------
community_stats = (
    df_struct.groupby("cluster_hdbscan")["community"]
    .agg(n_unique="nunique", entropy=lambda x: entropy(x.value_counts(normalize=True)))
    .sort_values("n_unique", ascending=False)
    .round(2)
    .head(10)
)
print(community_stats.to_markdown())


community_stats_all = (
    df_struct.groupby("cluster_hdbscan")["community"]
    .agg(n_unique="nunique", entropy=lambda x: entropy(x.value_counts(normalize=True)))
    .sort_values("n_unique", ascending=False)
    .round(2))



