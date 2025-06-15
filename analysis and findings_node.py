# -*- coding: utf-8 -*-
"""
Created on Fri Jun 13 16:52:47 2025

@author: baroc
"""

# === NODE-LEVEL ANALYSIS ===
import os
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Ensure path setup
script_dir = os.path.dirname(os.path.abspath(__file__))

# Load and clean
df = pd.read_csv("C:/Users/baroc/Downloads/final_workload_node_dataset_2.csv")
print(len(df))

# Feature configuration
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

# Drop rows with missing data
df = df.dropna(subset=features)

# Create log-transformed features
for feat in log_features:
    if feat in df.columns and f"{feat}_log" not in df.columns:
        df[f"{feat}_log"] = np.log10(df[feat].clip(lower=1e-3))

# Sample for plotting
df_sample = df.sample(n=min(5000, len(df)), random_state=42)

# === 1) Distributions ===
for feat in features:
    plot_feat = f"{feat}_log" if f"{feat}_log" in df.columns else feat
    plt.figure(figsize=(6, 4))
    sns.histplot(df_sample[plot_feat], kde=True, bins=50)
    plt.title(f"Distribution of {feature_titles[feat]}{' (log₁₀)' if '_log' in plot_feat else ''}")
    plt.xlabel(feature_titles[feat])
    plt.ylabel("Density")
    plt.tight_layout()
    plt.savefig(os.path.join(script_dir, f"{plot_feat}_Distribution.png"), dpi=300)
    plt.close()

# === 2) Correlation Heatmaps ===
# Raw
corr_raw = df[features].corr().round(2)
plt.figure(figsize=(7, 6))
sns.heatmap(corr_raw, annot=True, fmt=".2f", cmap="coolwarm", square=True, cbar_kws={"shrink": .8})
plt.title("Feature Correlation Heatmap (raw)")
plt.tight_layout()
plt.savefig(os.path.join(script_dir, "Feature_Correlation_Heatmap_raw.png"), dpi=300)
plt.close()

# Log (if applicable)
log_cols = [f"{feat}_log" for feat in log_features if f"{feat}_log" in df.columns]
if log_cols:
    corr_log = df[log_cols].corr().round(2)
    plt.figure(figsize=(5, 4))
    sns.heatmap(corr_log, annot=True, fmt=".2f", cmap="coolwarm", square=True, cbar_kws={"shrink": .8})
    plt.title("Feature Correlation Heatmap (log₁₀)")
    plt.tight_layout()
    plt.savefig(os.path.join(script_dir, "Feature_Correlation_Heatmap_log.png"), dpi=300)
    plt.close()

# === 3) Descriptive Statistics ===
desc_raw = df[features].agg(["mean", "std", "min", "max", "skew", "kurt"]).T.round(2)
print("\n=== Node-Level Descriptive Statistics (raw) ===")
print(desc_raw.to_markdown())

if log_cols:
    desc_log = df[log_cols].agg(["mean", "std", "min", "max", "skew", "kurt"]).T.round(2)
    print("\n=== Node-Level Descriptive Statistics (log₁₀) ===")
    print(desc_log.to_markdown())