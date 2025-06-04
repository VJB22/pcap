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



### Deployment Artifact + Workload Optimization with Graph Indicators and Descriptive Stats

| **Aspect**                      | **Serverless**                                                                 | **Containers**                                                           | **Orchestrated Containers**                                                   | **VMs**                                                                       | **Mini-VMs**                                                                  | **Baremetal**                                                                 |
|----------------------------------|--------------------------------------------------------------------------------|--------------------------------------------------------------------------|--------------------------------------------------------------------------------|--------------------------------------------------------------------------------|--------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| **Abstraction Level**           | Function-level (high)                                                         | Process-level                                                            | Multi-container app                                                           | OS-level virtualization                                                       | Lightweight OS virtualization                                                 | Hardware-level (no abstraction)                                               |
| **Resource Allocation**         | Fully managed, ephemeral                                                      | Shared kernel                                                            | Dynamic via orchestrator                                                      | Dedicated resources                                                            | Lower overhead per VM                                                         | Full machine control                                                          |
| **Startup Time**                | Milliseconds                                                                  | Seconds                                                                  | Seconds                                                                       | Minutes                                                                        | Milliseconds                                                                  | Instant (if running)                                                          |
| **Performance**                 | High (cold start penalty)                                                     | High                                                                     | High                                                                          | Moderate to high                                                               | High                                                                          | Highest                                                                       |
| **Isolation**                   | Low (multi-tenant)                                                            | Moderate (namespaces)                                                    | Moderate to high (policies)                                                   | Strong (hardware-based)                                                       | Strong (lightweight isolation)                                                | None (full access)                                                            |
| **State Management**            | Stateless                                                                     | Usually stateless                                                        | Managed via volumes                                                           | Managed with storage                                                           | Managed with storage                                                          | Full control                                                                  |
| **Scaling**                     | Automatic                                                                     | Manual/scripted                                                          | Auto via orchestrator                                                         | Manual                                                                         | Fast auto-scaling                                                             | Manual                                                                        |
| **Management Overhead**         | Lowest (fully managed)                                                        | Moderate (manual setup)                                                  | High (orchestration complexity)                                               | High (OS, networking)                                                          | Moderate                                                                      | Highest (full admin lifecycle)                                                |
| **Cost Model**                  | Pay-per-use                                                                   | Resource-based pricing                                                   | Resource-based pricing                                                        | Pay per VM uptime                                                              | Pay per lightweight VM                                                       | Fixed cost (CapEx hardware)                                                   |
| **Workload Optimization Signals** | Bursty, volatile, external-facing, short-lived                                | Mid-stable, flexible, reused connections                                 | Structured, stable, high-throughput                                           | Compliance-heavy, stable, long-lived                                           | Hybrid, burst-handling, scalable                                             | Throughput-intensive, compliance-bound, internal-only                         |
| **Expected Graph Behavior**     | Low degree, high session volatility, short flows, high external ratio         | Medium degree, reused flows, medium session volatility, mixed internal/external | High degree max, large flows, dense internal, structured clusters              | Stable degree, long flows, low volatility, internal-only                      | Short-medium flows, mixed volatility, moderate community structure            | Central nodes, high flow volume, low external ratio, stable graph roles       |
| **What to Look At (Descriptive Stats)** | `Degree (M)` (low), `Session vol. (SD)` (high), `Ext. ratio (M)` (high), `Flow dur. (M)` (low) | `Degree (M)` (medium), `Flows (M)` (medium), `Ext. ratio (SD)` (medium), `Session vol. (SD)` (medium) | `Degree (Max)` (high), `TTL var. (M)` (high), `Flows (Max)` (very high), `Ext. ratio (M)` (medium) | `Degree (SD)` (very low), `Flow dur. (M)` (high), `Ext. ratio (M)` (low), `TTL var. (SD)` (low) | `Flow dur. (M)` (medium-high), `Session vol. (SD)` (high), `Ext. ratio (SD)` (medium) | `Degree (M)` (very high), `Flows (M)` (very high), `Ext. ratio (M)` (very low), `TTL var. (M)` (low) |






### Descriptive statistics of graph-based features per artifact type

| **Artifact**     | **Deg. Mean** | **Deg. SD** | **Deg. Min** | **Deg. Max** | **Flows Mean** | **Flows SD** | **Flows Min** | **Flows Max** | **Sess. Vol. Mean** | **Sess. Vol. SD** | **TTL Var. Mean** | **TTL Var. SD** | **Ext. Ratio Mean** | **Ext. Ratio SD** | **Role Mean** | **Role SD** | **Role Min** | **Role Max** | **Flow Dur. Mean** | **Flow Dur. SD** | **Flow Dur. Min** | **Flow Dur. Max** | **Comm. Size Mean** | **Comm. Size SD** | **Comm. Size Min** | **Comm. Size Max** | **Component Type** |
|------------------|---------------|-------------|--------------|--------------|----------------|--------------|---------------|---------------|---------------------|-------------------|-------------------|------------------|----------------------|---------------------|--------------|-------------|-------------|-------------|--------------------|------------------|--------------------|--------------------|---------------------|--------------------|---------------------|---------------------|--------------------|
| Serverless       | 4.73          | 8.96        | 1            | 74           | 149.53         | 467.78       | 1             | 8563          | 1935.58             | 798.06            | 7.76              | 6.13             | 0.95                 | 0.17                | 9.25         | 16.40       | 0           | 62.19        | 45.31              | 63.02             | 0                  | 1121.30            | 6829.40             | 15009.20           | 2                   | 41585               | Hub/Star           |
| Container        | 30.63         | 59.65       | 1            | 164          | 1705.70        | 5004.93      | 1             | 24288         | 2246.60             | 899.64            | 22.88             | 10.58            | 0.09                 | 0.26                | 9.12         | 8.29        | 0           | 58.48        | 26.03              | 40.48             | 0                  | 338.12             | 515.11              | 423.29             | 2                   | 1042                | Hub/Star           |
| Orchestrated     | 7.66          | 14.62       | 1            | 45           | 92889.50       | 410057.00    | 1             | 2001230       | 1591.84             | 804.20            | 33.20             | 19.08            | 0.32                 | 0.43                | 6.21         | 9.63        | 0           | 32.18        | 28.30              | 62.68             | 0                  | 589.32             | 13364.90            | 19346.70           | 2                   | 41585               | Hub/Star           |
| VM               | 1.05          | 0.23        | 1            | 3            | 2.99           | 5.47         | 2             | 340           | 3171.18             | 878.90            | 14.36             | 8.28             | 0.04                 | 0.17                | 64.25        | 1.11        | 41.93        | 64.55        | 51.72              | 266.32            | 0                  | 3105.42            | 41532.50            | 1467.49            | 7                   | 41585               | Hub/Star           |
| Mini-VM          | 1.20          | 0.40        | 1            | 2            | 11.81          | 118.17       | 2             | 2043          | 1684.83             | 953.38            | 6.92              | 2.92             | 0.03                 | 0.13                | 19.16        | 21.11       | 0.01         | 61.89        | 567.27             | 287.31            | 0                  | 1203.22            | 3995.92             | 1769.40            | 5                   | 4886                | Hub/Star           |
| Baremetal        | 10911.30      | 8856.94     | 1            | 18459        | 25911.50       | 20020.20     | 1             | 147506        | 2765.00             | 801.10            | 12.38             | 5.82             | 0.28                 | 0.41                | 3.20         | 10.41       | 0            | 62.19        | 287.40             | 585.68            | 0                  | 3150.82            | 27901.60            | 18766.00           | 1                   | 41585               | Hub/Star           |

