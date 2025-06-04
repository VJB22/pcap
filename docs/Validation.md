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


### Deployment Artifact + workload opt. with Graph Indicators and the Descriptive Stats Table

| **Aspect**                      | **Serverless**                                                                 | **Containers**                                                           | **Orchestrated Containers**                                                   | **VMs**                                                                       | **Mini-VMs**                                                                  | **Baremetal**                                                                 |
|----------------------------------|--------------------------------------------------------------------------------|--------------------------------------------------------------------------|--------------------------------------------------------------------------------|--------------------------------------------------------------------------------|--------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| **Abstraction Level**           | Function-level (high)                                                         | Process-level                                                            | Multi-container app                                                           | OS-level virtualization                                                       | Lightweight OS virtualization                                                 | Hardware-level (no abstraction)                                               |
| **Resource Allocation**         | Fully managed, ephemeral                                                      | Shared kernel                                                            | Dynamic via orchestrator                                                      | Dedicated resources                                                            | Lower overhead per VM                                                         | Full machine control                                                          |
| **Startup Time**                | Milliseconds                                                                  | Seconds                                                                  | Seconds                                                                       | Minutes                                                                        | Milliseconds                                                                  | Instant (if running)                                                          |
| **Performance**                 | High (cold start penalty)                                                     | High                                                                     | High                                                                          | Moderate to high                                                               | High                                                                          | Highest                                                                       |
| **Isolation**                   | Low (multi-tenant)                                                            | Moderate (namespaces)                                                    | Moderate to high (policies)                                                   | Strong (hardware-based)                                                       | Strong (lightweight isolation)                                                | None (full access)                                                            |
| **State Management**            | Stateless                                                                     | Usually stateless                                                        | Managed via volumes                                                           | Managed with storage                                                           | Managed with storage                                                          | Full control                                                                  |
| **Scaling**                     | Automatic                                                                     | Manual/scripted                                                          | Auto via orchestrator                                                         | Manual                                                                         | Fast auto-scaling                                                             | Manual                                                                        |
| **Management Overhead**         | Lowest (fully managed)                                                        | Moderate (manual setup)                                                  | High (orchestration complexity)                                               | High (OS, networking)                                                          | Moderate                                                                       | Highest (full admin lifecycle)                                                |
| **Cost Model**                  | Pay-per-use                                                                   | Resource-based pricing                                                   | Resource-based pricing                                                        | Pay per VM uptime                                                              | Pay per lightweight VM                                                       | Fixed cost (CapEx hardware)                                                   |
| **Workload Optimization Signals** | Bursty, volatile, external-facing, short-lived                                | Mid-stable, flexible, reused connections                                 | Structured, stable, high-throughput                                           | Compliance-heavy, stable, long-lived                                           | Hybrid, burst-handling, scalable                                             | Throughput-intensive, compliance-bound, internal-only                         |
| **Expected Graph Behavior**     | Low degree, high volatility, short flows, unstable ports, high external ratio | Medium degree, reused flows, mixed I/O, medium clustering                | High degree, dense internal flows, high clustering, large communities         | Stable degree, long durations, low volatility, mostly internal                 | Medium degree, short-medium flows, mixed volatility, fast component shifts    | Central nodes, stable long-lived flows, very low external ratio               |
| **What to Look At (Descriptive Stats)** | `degree_mean` (low), `session_volatility_SD` (high), `external_ratio_mean` (high), `flow_duration_max` (low), `port_entropy` (high) | `degree_mean` (medium), `flow_reuse_ratio` (high), `session_volatility_SD` (medium), `external_ratio_SD` (medium) | `degree_max` (high), `clustering_coef_mean` (high), `session_volatility_SD` (low), `community_size` (large) | `degree_SD` (low), `flow_duration_mean` (high), `TTL_SD` (low), `external_ratio_mean` (low) | `flow_duration_SD` (medium), `external_ratio_SD` (medium-high), `session_volatility_SD` (medium-high) | `degree_SD` (very low), `flow_duration_mean` (very high), `external_ratio_mean` (very low), `total_bytes` (high) |





### Descriptive statistics of graph-based features per artifact type

| Artifact      | Degree (M) | Degree (SD) | Degree (Min) | Degree (Max) | Flows (M) | Flows (SD) | Flows (Min) | Flows (Max) | Session vol. (M) | Session vol. (SD) | TTL var. (M) | TTL var. (SD) | Ext. ratio (M) | Ext. ratio (SD) | Role score (M) | Flow dur. (M) |
|---------------|-------------|--------------|----------------|----------------|-------------|--------------|----------------|----------------|---------------------|----------------------|----------------|------------------|--------------------|----------------------|------------------|----------------|
| VM            | 1.05        | 0.23         | 1              | 3              | 2.99        | 5.47         | 2              | 340            | 3171.18              | 878.90               | 14.36          | 8.28             | 0.038              | 0.169                | 64.25            | 51.72          |
| Baremetal     | 10911.30    | 8856.94      | 1              | 18459          | 25911.60    | 20020.20     | 1              | 147506         | 2765.00              | 801.10               | 12.38          | 5.82             | 0.278              | 0.408                | 3.20             | 287.40         |
| Container     | 30.63       | 59.66        | 1              | 164            | 1705.70     | 5004.93      | 1              | 24288          | 2246.60              | 899.64               | 22.88          | 10.58            | 0.085              | 0.263                | 9.12             | 26.03          |
| Mini_vm       | 1.20        | 0.40         | 1              | 2              | 11.82       | 118.17       | 2              | 2043           | 1684.83              | 953.38               | 6.92           | 2.92             | 0.026              | 0.124                | 19.16            | 567.27         |
| Orchestrated  | 7.66        | 14.62        | 1              | 45             | 92889.50    | 410057.00    | 1              | 2000000        | 1591.84              | 804.20               | 33.20          | 19.08            | 0.320              | 0.432                | 6.21             | 28.30          |
| Serverless    | 4.73        | 8.96         | 1              | 74             | 149.53      | 467.79       | 1              | 8563           | 1935.58              | 798.06               | 7.76           | 6.13             | 0.948              | 0.168                | 9.25             | 45.31          |

**Note:** M = mean; SD = standard deviation; Min = minimum; Max = maximum.

