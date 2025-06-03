# Cloud Engineer Validation Guide: Final Dataset Columns

## What This Dataset Is

This dataset models workload-to-workload communication from PCAP network data.  
Each row represents a **workload node** (application, service, or machine, based on MAC, IP, port).  
The model assigns **deployment artifact guesses** (bare metal, VM, container, etc.) to help with workload optimization.

---

## Column Explanations (Final Dataset)

| **Column**            | **Plain Language Meaning**                                         | **Why It Matters**                                                                 | **Example**                           |
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

✅ Do high-degree, stable workloads align with bare metal or VM in your experience?  
✅ Are bursty, short-session workloads realistically serverless?  
✅ Do high-peer workloads look like APIs/gateways in practice?  
✅ Spot mismatches: Any containers that feel like VMs, or vice versa?  
✅ Any patterns you’d expect but don’t see?
