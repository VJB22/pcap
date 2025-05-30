## Deployment Artifact Scoring Model

I use a **linear scoring model** to assign **deployment artifact recommendations per workload**, where each **workload_id (MAC + IP + Port)** is treated as a **proxy for a cloud workload unit**.
Each workload_id (MAC+IP+Port) is treated as a proxy for a cloud workload unit. I explore deployment artifact suitability per workload using a linear scoring model built on graph-derived features (flows, component type, role score, community size, etc.). Louvain communities and graph topology provide contextual features but do not redefine the workload unit itself.

### Theoretical Justification

- **Workload_id** represents the smallest observable, network-resolvable unit of execution (a proxy for cloud tasks such as processes, containers, or VMs).
- **Graph methods** (Louvain, ReFeX, component type) provide **contextual features** that describe each workload's behavior and topology within the system.
- The **linear scoring system** combines these features to infer the **most suitable deployment artifact** for each workload.

---

## Linear Scoring Formula (Per Workload Node)

For each node *n* (workload):

\[
S_{\text{artifact}}(n) = \sum_{i=1}^{k} w_i \cdot z_i(n)
\]

Where:
- \( S_{\text{artifact}}(n) \) = Score for a specific deployment artifact.
- \( w_i \) = Empirical weight for feature *i*.
- \( z_i(n) \) = Z-score normalized value of feature *i* for node *n*.

---

## Features Used in the Scoring Model

| Feature                    | Description                                  |
|---------------------------|----------------------------------------------|
| Degree                    | Number of connections.                       |
| Flows                     | Total flow count.                            |
| Bytes                     | Total bytes (sum of sent/received).          |
| Session Volatility        | Variability of session behavior.             |
| TTL Variability           | Variability in packet TTLs.                  |
| Component Type (mapped)   | Structural position (e.g., Singleton, Chain). |
| External Ratio            | Proportion of flows to external nodes.       |
| Role Score (NMF/ReFeX)    | Latent graph-based feature.                   |
| Avg Flow Duration         | Mean duration of flows.                      |
| Community Size            | Size of Louvain community.                   |

---

## Linear Scoring Model (Z-Score Normalized)

\[
S_{\text{artifact}}(n) =
3.0 \cdot z_{\text{component type}}(n) +
2.0 \cdot z_{\text{total bytes}}(n) +
2.5 \cdot z_{\text{external ratio}}(n) +
2.0 \cdot z_{\text{degree}}(n) +
2.0 \cdot z_{\text{avg flow duration}}(n) +
2.5 \cdot z_{\text{role score}}(n) +
2.0 \cdot z_{\text{community size}}(n) +
2.0 \cdot z_{\text{flows}}(n) -
2.0 \cdot z_{\text{session volatility}}(n) -
1.5 \cdot z_{\text{ttl variability}}(n)
\]

With artifact-specific adjustments for **avg_flow_duration(n)**:

| Artifact Type            | Adjustment |
|--------------------------|------------|
| Baremetal                | +2.0       |
| VM                       | +1.5       |
| Orchestrated / Mini VM   | 0          |
| Container                | −1.5       |
| Serverless               | −2.0       |

---

## Final Output

- For each **workload_id**, I recommend the **most suitable deployment artifact** (e.g., baremetal, VM, container, serverless) based on this scoring system.
- **Louvain community** and **component type** are used as **features**, not as alternative workload units.
- The result is a **per-workload deployment artifact recommendation** that captures both **network behavior** and **graph topology**.

---

This approach reflects the **most granular unit of workload analysis possible in network data**. It enables **data-driven deployment artifact recommendations** aligned with **cloud workload definition**.

---

FOR LINEAR SCORING SYSTEM

```python
score_fn = lambda f: {
    'baremetal': 3*f[4]+2*f[5]+2.5*f[6]+2*f[0]+2*f[8],
    'VM': 2.5*f[9]+2*f[1]+2.5*f[7]-1.5*f[2]+1.5*f[8],
    'orchestrated': 2*f[9]+1.5*f[0]+2*f[1]-1.5*f[2],
    'container': 1.5*f[1]+1.5*f[0]-1.5*f[2]-1.0*f[3]-1.5*f[8],
    'mini_vm': 1.5*f[0]+1.5*f[7]-2*f[2]-1.5*f[3],
    'serverless': 1.5*f[6]-2.5*f[2]-2*f[3]-1.5*f[1]-2*f[8]
}
```


Here’s the mapping of the feature array `f` by position:

| Index  | Feature in `f`            | Meaning                                           |
|:------|:--------------------------|:--------------------------------------------------|
| `f[0]` | degree                    | Node degree                                      |
| `f[1]` | flows                     | Total flows                                      |
| `f[2]` | session_volatility        | Session volatility per node                      |
| `f[3]` | ttl_variability           | TTL variability                                  |
| `f[4]` | component_type_score      | Encodes component type (e.g., singleton = 1, chain = 2, etc.) |
| `f[5]` | bytes                     | Total bytes over edges                           |
| `f[6]` | external_ratio            | Ratio of flows to external nodes (routers)       |
| `f[7]` | role_score                | NMF/Refex-based role score                       |
| `f[8]` | avg_flow_duration         | Average flow duration per node                   |
| `f[9]` | community_size            | Number of nodes in the community                 |



## References

MOST IMPORTANT PAPERS FOR THESIS:
https://arxiv.org/abs/1211.3951 

While the composite scoring framework in this work draws inspiration from the composite centrality concept by Joseph and Chen (2014), this thesis presents a simplified adaptation tailored to the domain of deployment artifact inference. The system utilizes a linear weighted sum of standardized graph metrics—including degree, flows, session volatility, and flow duration—aligned with theoretical expectations of deployment artifact characteristics. Unlike the original formulation, which employs complex inheritance schemes for general network centrality analysis, this work streamlines the process by focusing on workloads and operationally relevant signals.

https://www.catalyzex.com/paper/movie-recommendation-system-using-composite

Similar to the use of composite ranking systems in movie recommendation systems, where heterogeneous signals like metadata, visual similarity, and sentiment analysis are integrated into a unified score (Mehta, Kamdar, 2022), this work applies a composite scoring framework to graph-based workload graphs. The resulting scores reflect theoretical characteristics of deployment artifacts, guiding the inference of suitable deployment types for each workload.
