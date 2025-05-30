# Deployment Artifact Scoring Formula

I use a **linear scoring model** to assign deployment artifact recommendations to nodes and cloud workloads. This model combines graph-derived features with theory-driven, empirically adjusted weights.

---

### General Formula (Unified)

For both node-level and cloud workload-level:

$$
S_{artifact}(x) = \sum_{i=1}^{k} w_i \cdot f_i(x)
$$

Where:
- **S_{artifact}(x)** = Linear score for a specific artifact type, computed for node *n* or cloud workload *W*
- **wᵢ** = Weight for feature *i* 
- **fᵢ(x)** = Graph-derived feature *i* for node or workload

---

### Node-Level Scoring (Per Workload Node)

For each node *n*, features are **Z-score normalized**:

$$
z_i(n) = \frac{f_i(n) - \mu_i}{\sigma_i}
$$

The node-level artifact scoring formula is:

$$
S(n) = 3 \cdot z_{component\_type\_score}(n) + 2 \cdot z_{bytes}(n) + 2.5 \cdot z_{external\_ratio}(n) + 2 \cdot z_{degree}(n) + 2 \cdot z_{avg\_flow\_duration}(n) + 2.5 \cdot z_{role\_score}(n) + 2.0 \cdot z_{community\_size}(n) + 2.0 \cdot z_{flows}(n) - 2.0 \cdot z_{session\_volatility}(n) - 1.5 \cdot z_{ttl\_variability}(n)
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

### Cloud Workload-Level Scoring (Per Group of Nodes)

For each cloud workload *W* (Louvain community), features are **raw aggregated metrics** (no normalization):

$$
S(W) = 3.0 \cdot max\_degree(W) + 2.0 \cdot mean\_bytes(W) + 2.5 \cdot max\_external\_ratio(W) + 2.0 \cdot total\_flows(W) + 2.0 \cdot mean\_avg\_flow\_duration(W) + 2.5 \cdot mean\_role\_score(W) - 1.5 \cdot mean\_session\_volatility(W) - 1.0 \cdot mean\_ttl\_variability(W)
$$

Where:
- **max_degree(W)** = Maximum degree of nodes in *W*
- **mean_bytes(W)** = Mean bytes across nodes in *W*
- **max_external_ratio(W)** = Maximum external ratio across nodes in *W*
- **total_flows(W)** = Total flows across all nodes in *W*
- **mean_avg_flow_duration(W)** = Mean average flow duration across nodes in *W*
- **mean_role_score(W)** = Mean role score across nodes in *W*
- **mean_session_volatility(W)** = Mean session volatility across nodes in *W*
- **mean_ttl_variability(W)** = Mean TTL variability across nodes in *W*



## References

MOST IMPORTANT PAPERS FOR THESIS:
https://arxiv.org/abs/1211.3951 

While the composite scoring framework in this work draws inspiration from the composite centrality concept by Joseph and Chen (2014), this thesis presents a simplified adaptation tailored to the domain of deployment artifact inference. The system utilizes a linear weighted sum of standardized graph metrics—including degree, flows, session volatility, and flow duration—aligned with theoretical expectations of deployment artifact characteristics. Unlike the original formulation, which employs complex inheritance schemes for general network centrality analysis, this work streamlines the process by focusing on workloads and operationally relevant signals.

https://www.catalyzex.com/paper/movie-recommendation-system-using-composite

Similar to the use of composite ranking systems in movie recommendation systems, where heterogeneous signals like metadata, visual similarity, and sentiment analysis are integrated into a unified score (Mehta, Kamdar, 2022), this work applies a composite scoring framework to graph-based workload graphs. The resulting scores reflect theoretical characteristics of deployment artifacts, guiding the inference of suitable deployment types for each workload.
