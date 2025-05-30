## Deployment Artifact Scoring Formula

I use a **linear scoring model** to assign **deployment artifact recommendations at the node level**, based on **graph-derived features** and empirically adjusted weights.  
For **cloud workloads (Louvain communities)**, I aggregate node-level artifacts using **majority voting** and measure diversity via **entropy** and **artifact count**.

---

# General Linear Scoring Formula (Base Model)

The deployment artifact score is computed as a **linear combination** of graph-derived features:

$$
S_{\text{artifact}}(x) = \sum_{i=1}^{k} w_i \cdot f_i(x)
$$

Where:
- **S<sub>artifact</sub>(x)** = Linear score for a specific artifact type, computed for node *n* or cloud workload *W*.
- **wᵢ** = Empirical weight for feature *i*.
- **fᵢ(x)** = Graph-derived feature *i* for node or workload *x*.

----

### Node-Level Linear Scoring Formula

For each node *n*:

$$
S_{\text{artifact}}(n) = \sum_{i=1}^{k} w_i \cdot z_i(n)
$$

Where:
- **S<sub>artifact</sub>(n)** = Score for a specific artifact type.
- **zᵢ(n)** = Z-score normalized value of feature *i* for node *n*.
- **wᵢ** = Empirical weight for feature *i*.

---

### Features (Z-score Normalized)

**S<sub>artifact</sub>(n)** =  
&ensp;&ensp;3.0 · *z<sub>component type</sub>(n)*  
&ensp;+ 2.0 · *z<sub>total bytes</sub>(n)*  
&ensp;+ 2.5 · *z<sub>external ratio</sub>(n)*  
&ensp;+ 2.0 · *z<sub>degree</sub>(n)*  
&ensp;+ 2.0 · *z<sub>avg flow duration</sub>(n)*  
&ensp;+ 2.5 · *z<sub>role score</sub>(n)*  
&ensp;+ 2.0 · *z<sub>community size</sub>(n)*  
&ensp;+ 2.0 · *z<sub>flows</sub>(n)*  
&ensp;− 2.0 · *z<sub>session volatility</sub>(n)*  
&ensp;− 1.5 · *z<sub>ttl variability</sub>(n)*

With artifact-specific adjustments for **avg_flow_duration(n)**:

| Artifact Type            | Adjustment |
| ------------------------ | ---------- |
| Baremetal                | +2.0       |
| VM                       | +1.5       |
| Orchestrated / Mini VM   | 0          |
| Container                | −1.5       |
| Serverless               | −2.0       |

---

### Cloud Workload-Level Artifact Recommendation (Louvain Community)

For each cloud workload *W* (Louvain community), I infer artifacts by:
- Taking the **majority vote** of the node-level top artifacts within *W*.
- Computing **artifact diversity metrics**:
  - **Entropy**:  

$$
H(W) = - \sum_{a} p(a) \cdot \log p(a)
$$

  Where p(a) = proportion of nodes in *W* with artifact *a*.
  - **Unique Artifact Count** = Number of distinct artifacts in *W*.


- This provides a **single recommended artifact** for *W* (via majority vote) and a **diversity signal** to detect mixed workloads.
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
