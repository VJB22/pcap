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


## Threshold Mapping for Metric Interpretation
Each metric was subjected to a set of heuristic thresholds in order to facilitate the interpretation of raw graph-derived features in the context of deployment artifact exploration. According to these thresholds, a variety of structural and behavioral indicators seen in the workload graph can be classified as low, medium, high, or very high. 

# Preliminary Heuristic Thresholds for Metric Interpretation

| Metric                   | Low      | Medium     | High       | Very High |
|--------------------------|----------|------------|------------|------------|
| Degree             | < 5      | 5–30       | 30–100     | > 100     |
| Flows         | < 10     | 10–500     | 500–5000   | > 5000    |
| Session Volatility   | < 0.3    | 0.3–0.8    | 0.8–1.2    | > 1.2     |
| TTL Variability   | < 5      | 5–15       | 15–30      | > 30      |
| External Ratio     | < 0.3    | 0.3–0.7    | 0.7–0.9    | > 0.9     |
| Flow Duration     | < 1 s    | 1–10 s     | 10–100 s   | > 100 s   |
| Role Score                | < 5      | 5–30       | 30–60      | > 60      |
| Community Size     | < 10     | 10–100     | 100–1000   | > 1000    |

These qualitative mappings enable interpretability in the linear scoring model and support transparent justification of classification logic. While initially heuristic, they form a critical layer in bridging abstract graph roles and practical deployment behavior. Their refinement is left as future work.


### Deployment Artifact + Workload Optimization with Graph Indicators

| Aspect                         | Serverless                                       | Containers                                     | Orchestrated Containers                        | VMs                                              | Mini-VMs                                          | Baremetal                                           |
|--------------------------------|--------------------------------------------------|------------------------------------------------|--------------------------------------------------|--------------------------------------------------|---------------------------------------------------|-----------------------------------------------------|
| Abstraction Level             | Function-level (high)                            | Process-level                                  | Multi-container app                             | OS-level virtualization                          | Lightweight OS virtualization                      | Hardware-level (no abstraction)                     |
| Resource Allocation           | Fully managed, ephemeral                         | Shared kernel                                  | Dynamic via orchestrator                        | Dedicated resources                              | Lower overhead per VM                              | Full machine control                                 |
| Startup Time                  | Milliseconds                                     | Seconds                                        | Seconds                                         | Minutes                                          | Milliseconds                                       | Instant (if running)                                 |
| Performance                   | High (cold start penalty)                        | High                                           | High                                            | Moderate to high                                 | High                                               | Highest                                               |
| Isolation                     | Low (multi-tenant)                               | Moderate (namespaces)                          | Moderate to high (policies)                     | Strong (hardware-based)                          | Strong (lightweight isolation)                     | None (full access)                                    |
| State Management              | Stateless                                        | Usually stateless                              | Managed via volumes                             | Managed with storage                             | Managed with storage                               | Full control                                          |
| Scaling                       | Automatic                                        | Manual/scripted                                | Auto via orchestrator                           | Manual                                           | Fast auto-scaling                                  | Manual                                                |
| Management Overhead           | Lowest (fully managed)                           | Moderate (manual setup)                        | High (orchestration complexity)                 | High (OS, networking)                            | Moderate                                           | Highest (full admin lifecycle)                        |
| Cost Model                    | Pay-per-use                                      | Resource-based pricing                         | Resource-based pricing                          | Pay per VM uptime                                | Pay per lightweight VM                             | Fixed cost (CapEx hardware)                           |
| Workload Optimization Signals | Bursty, volatile, external-facing, short-lived   | Mid-stable, flexible, reused connections       | Structured, stable, high-throughput             | Compliance-heavy, stable, long-lived            | Hybrid, burst-handling, scalable                  | Throughput-intensive, compliance-bound, internal-only |
| Expected Graph Behavior       | Low degree, high session volatility, short flows, high external ratio | Medium degree, reused flows, medium session volatility, mixed internal/external | High degree max, large flows, dense internal, structured clusters | Stable degree, long flows, low volatility, internal-only | Short-medium flows, mixed volatility, moderate community structure | Central nodes, high flow volume, low external ratio, stable graph roles |
| What to Look At (final dataset) | Degree low, Session vol. high, Ext. ratio  high, Flow dur. low | Degree medium, Flows medium, Ext. ratio medium, Session vol. medium | Degree  high, TTL var. high, Flows very high, Ext. ratio medium | Degree very low, Flow dur. high, Ext. ratio  low, TTL var.  low | Flow dur.  medium-high, Session vol.  high, Ext. ratio  medium | Degree very high, Flows very high, Ext. ratio very low, TTL var. low 
| **Community Type**            | Star                                             | Hub                                             | Star                                            | Hub                                              | Star                                               | Hub                                                   |
| **Community Size Behavior**   | Small to Medium                                  | Small                                           | Medium to Large                                 | Very Large                                       | Medium                                             | Very Large                                             |





