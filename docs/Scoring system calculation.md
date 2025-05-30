## Deployment Artifact Scoring Formula

I use a **linear scoring model** to assign deployment artifact recommendations to nodes and cloud workloads. This model combines graph-derived features with theory-driven, empirically adjusted weights.

---

## General Formula (Unified)

For both node-level and cloud workload-level:

$$
S_{artifact}(x) = \sum_{i=1}^{k} w_i \cdot f_i(x)
$$

Where:  
- **S_{artifact}(x)** = Linear score for a specific artifact type, computed for node *n* or cloud workload *W*  
- **wᵢ** = Weight for feature *i*  
- **fᵢ(x)** = Graph-derived feature *i* for node or workload  

---

## Node-Level Scoring (Per Workload Node)

For each node *n*, features are **Z-score normalized**:

$$
z_i(n) = \frac{f_i(n) - \mu_i}{\sigma_i}
$$

The node-level artifact scoring formula is:

$$
S_{artifact}(n) =
\begin{aligned}
&3 \cdot z_{component\_type\_score}(n) + 2 \cdot z_{bytes}(n) + 2.5 \cdot z_{external\_ratio}(n) + 2 \cdot z_{degree}(n) \\
&+ 2 \cdot z_{avg\_flow\_duration}(n) + 2.5 \cdot z_{role\_score}(n) + 2.0 \cdot z_{community\_size}(n) + 2.0 \cdot z_{flows}(n) \\
&- 2.0 \cdot z_{session\_volatility}(n) - 1.5 \cdot z_{ttl\_variability}(n)
\end{aligned}
$$

With an artifact-specific adjustment for **avg_flow_duration(n)**:

$$
d =
\begin{cases}
+2.0 & \text{Baremetal} \\
+1.5 & \text{VM} \\
0 & \text{Orchestrated / Mini VM} \\
-1.5 & \text{Container} \\
-2.0 & \text{Serverless}
\end{cases}
$$

---

## Cloud Workload-Level Artifact Inference (Voting-Based Aggregation)

For each cloud workload *W* (Louvain community), **I use a weighted voting system** to infer artifacts. This preserves the diversity of node-level artifact predictions and ranks artifacts by consensus:

1. **Each node votes for its ranked artifacts** (e.g., top-ranked gets the highest vote, second-ranked slightly lower, etc.).
2. **Votes are aggregated across all nodes in *W*.**
3. **Artifacts are ranked based on total votes.**

This produces a **ranked artifact list per cloud workload**, such as:

$$
\text{Cloud } W: [\text{Baremetal}, \text{VM}, \text{Container}, \dots]
$$

### Example:

For Cloud *W*:
- Node 1 votes: *Baremetal > VM > Container*  
- Node 2 votes: *VM > Container > Serverless*  
- Node 3 votes: *Container > Baremetal > VM*

Aggregated votes give a final ranking for *W*:  
$$
[\text{Baremetal}, \text{VM}, \text{Container}]
$$

This approach preserves **artifact heterogeneity** within cloud workloads, enabling multi-artifact recommendations.

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
