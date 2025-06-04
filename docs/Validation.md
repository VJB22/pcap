# Cloud Engineer Validation Guide: Final Dataset Columns

## What This Dataset Is

This dataset models workload-to-workload communication from PCAP network data.  
Each row represents a **workload node** (application, service, or machine, based on MAC, IP, port).  
The model assigns **deployment artifact guesses** (bare metal, VM, container, etc.) to help with workload optimization.

---

## Column Explanations (Final Dataset)

| **Column**            | **Meaning**                                         | **Why It Matters**                                                                 | **Example**                           |
|-----------------------|-------------------------------------------------------------------|------------------------------------------------------------------------------------|---------------------------------------|
| `workload_id_node`    | Unique workload ID (hash of MAC, IP, port)                         | Identifies each workload so you can track it across the dataset.                   | abc123...                              |
| `degree`              | Number of other workloads this node talks to                      | High = core service; low = edge client. Shows how connected a workload is.         | 12 = core API; 2 = edge client        |
| `flows`               | Total number of communication flows                               | High = active service; low = idle/light. Helps estimate workload intensity.        | 100 = active; 5 = light               |
| `session_volatility`  | Stability of session lengths (higher = more volatile)              | High = bursty (often serverless); low = stable (likely VMs, bare metal).           | 0.3 = stable; 1.2 = bursty            |
| `ttl_variability`     | Variability in TTL (suggests dynamic infra)                        | High = possibly containerized/virtualized; low = stable routing.                   | 1.5 = unstable; 0.2 = stable          |
| `component_type`      | Detected topology pattern (Hub/Star, Chain, Isolated)              | Central hub? Linear chain? Isolated? Helps understand workload’s network role.     | Hub/Star = central node, many peers   |
| `external_ratio`      | % of traffic going outside the network                            | High = external-facing workloads (APIs, gateways); low = internal services.        | 0.9 = mostly external; 0.1 = internal |
| `role_score`          | Graph-based role strength (from NMF)                               | Higher = core system component; lower = peripheral or supporting node.             | 0.8 = core service; 0.2 = peripheral  |
| `avg_flow_duration`   | Average session duration (in seconds)                              | Longer = stateful workloads (like VMs); shorter = stateless (like serverless).     | 300 = long; 10 = short                |
| `community`           | Louvain community ID (cluster)                                     | Shows which workloads form a logical group; useful for identifying multi-tier apps.| 5 = grouped with 5 other nodes        |
| `top_artifact`        | Best guess for deployment type                                     | Suggested artifact for this workload.                                              | vm, container, baremetal              |
| `artifact_confidence` | Confidence level (higher = better)                                  | Measures how certain the model is. Higher = more certain; lower = more uncertain. For example, 0.8 = high certainty, 0.2 = low certainty.
| `top_artifact_score`  | Score for the top-ranked guess (0–1)                               | Strength of the guess; closer to 1 = better fit.                                   | 0.85 = strong match                   |
| `artifact_ranking`    | Ordered list of artifact guesses                                   | Backup guesses ranked by fit. Helps you check alternatives.                        | ["container", "vm", "baremetal"]      |

---

## Source/Destination Identifiers (for cross-checking)

| **Column**         | **Meaning**                     | **Example**            |
|--------------------|--------------------------------|------------------------|
| `workload_id_src`  | Source workload ID (hash)       | abc123...              |
| `mac_src`          | Source MAC address             | 00:1A:2B:3C:4D:5E      |
| `ip_src`           | Source IP address              | 192.168.1.5            |
| `src_port`         | Source port                    | 443                    |
| `workload_id_dst`  | Destination workload ID (hash) | def456...              |
| `mac_dst`          | Destination MAC address        | 00:1A:2B:3C:4D:5F      |
| `ip_dst`           | Destination IP address         | 10.0.0.1               |
| `dst_port`         | Destination port               | 8080                   |

---

## What to Check
✅ Does it follow the expected graph patterns (as explained below)?
✅ Do high-degree, stable workloads align with bare metal or VM in your experience?  
✅ Are bursty, short-session workloads realistically serverless?  
✅ Do high-peer workloads look like APIs/gateways in practice?  
✅ Spot mismatches: Any containers that feel like VMs, or vice versa?  
✅ Any patterns you’d expect but don’t see?


### Deployment Artifact Mapping with Descriptive Stats (using SD)

| **Artifact Type**         | **Cloud Characteristics**                                                                                     | **Graph Behavior**                                                                                                 | **Workload Optimization Signals**                                                                 | **What to Look At (Metric-wise)**                                                                 |
|---------------------------|----------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| **Serverless**            | - Function-level  <br> - Ephemeral, auto-scaled  <br> - Cold start penalty  <br> - Stateless  <br> - Fully managed | - Low degree  <br> - High session volatility  <br> - High external ratio  <br> - Short flow duration  <br> - Unstable ports/IPs | - Bursty workloads  <br> - High volatility  <br> - Short lifespan  <br> - External flows  <br> - Port/IP churn | - `degree_mean` (low)  <br> - `session_volatility_SD` (high)  <br> - `external_ratio_mean` (high)  <br> - `flow_duration_max` (low)  <br> - `port_entropy` (high) |
| **Containers**            | - Process-level  <br> - Shared kernel  <br> - Manual scaling  <br> - Moderate isolation  <br> - Moderate overhead | - Moderate degree  <br> - Reused edges  <br> - Medium session volatility  <br> - Mixed internal/external flows  <br> - Medium clustering | - Mid-stable workloads  <br> - Some volatility  <br> - Mixed data intensity and flexibility       | - `degree_mean` (medium)  <br> - `flow_reuse_ratio` (high)  <br> - `session_volatility_SD` (medium)  <br> - `external_ratio_SD` (medium) |
| **Orchestrated Containers** | - Multi-container  <br> - Auto-scaled  <br> - Moderate-to-high isolation  <br> - High orchestration complexity | - High degree  <br> - Dense internal connectivity  <br> - High clustering coefficient  <br> - Low volatility  <br> - Structured community patterns | - Structured workloads  <br> - Stable internal flows  <br> - Low port reuse  <br> - High data throughput | - `degree_max` (high)  <br> - `clustering_coef_mean` (high)  <br> - `session_volatility_SD` (low)  <br> - `community_size` (large) |
| **VMs**                   | - OS-level abstraction  <br> - Dedicated resources  <br> - Manual scaling  <br> - Strong isolation  <br> - High startup overhead | - Stable degree  <br> - Long-duration edges  <br> - Low session volatility  <br> - Mostly internal flows  <br> - Consistent TTL | - Stable workloads  <br> - Compliance-sensitive workloads  <br> - Long-lived sessions  <br> - Low churn | - `degree_SD` (low)  <br> - `flow_duration_mean` (high)  <br> - `TTL_SD` (low)  <br> - `external_ratio_mean` (low) |
| **Mini-VMs**              | - Lightweight VMs  <br> - Fast boot  <br> - Good isolation  <br> - Fast auto-scaling  <br> - Lower overhead than full VMs | - Moderate degree  <br> - Short-medium flows  <br> - Mixed volatility  <br> - Some external connectivity  <br> - Fast change in component size | - Hybrid workloads  <br> - Short-lived services with burst handling  <br> - Scalable but not ephemeral | - `flow_duration_SD` (medium)  <br> - `external_ratio_SD` (medium-high)  <br> - `session_volatility_SD` (medium-high) |
| **Baremetal**             | - Full hardware control  <br> - No abstraction  <br> - Highest performance  <br> - Manual scaling  <br> - Full isolation and admin rights | - Low volatility  <br> - Long-lived, heavy flows  <br> - Low external ratio  <br> - Central nodes  <br> - Very stable degree and flow patterns | - Data-intensive workloads  <br> - Compliance-bound workloads  <br> - High throughput  <br> - Internal-only communication | - `degree_SD` (very low)  <br> - `flow_duration_mean` (very high)  <br> - `external_ratio_mean` (very low)  <br> - `total_bytes` (high) |


