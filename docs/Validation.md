# Cloud Engineer Validation Guide: Understanding the Dataset Columns


## What This Dataset Is

This dataset contains **workload-level insights**, built from PCAP traffic.  
Each row is a **workload (node)**—a unique application, service, or machine, identified by MAC, IP, and port.  
The model combines network signals into **artifact type guesses** (e.g., bare metal, VM, container) for **workload optimization**.  

---

## Column Explanations (Final Dataset)

| **Column** | **Plain Language Meaning** | **Example** |
|------------|----------------------------|-------------|
| `workload_id_node` | Unique workload ID (hash of MAC, IP, port) | `abc123...` |
| `degree` | Number of other workloads this node talks to | 12 = core API; 2 = edge client |
| `flows` | Total number of communication flows | 100 = active; 5 = light |
| `session_volatility` | Stability of session lengths (higher = more volatile) | 0.3 = stable; 1.2 = bursty |
| `ttl_variability` | Variability in TTL (suggests dynamic infra) | 1.5 = unstable; 0.2 = stable |
| `component_type` | Detected system role (e.g., router, switch, client) | `external_router`, `internal_router`, `client` |
| `external_ratio` | % of traffic going outside the network | 0.9 = mostly external; 0.1 = mostly internal |
| `role_score` | Graph-based role strength (from NMF) | 0.8 = core service; 0.2 = peripheral |
| `avg_flow_duration` | Average session duration (in seconds) | 300 = long; 10 = short |
| `community` | Louvain community ID (cluster) | 5 = grouped with 5 other nodes |
| `top_artifact` | Best guess for deployment type | `vm`, `container`, `baremetal` |
| `artifact_confidence` | Confidence level (lower = better) | 0.2 = high certainty; 0.8 = uncertain |
| `top_artifact_score` | Score for the top-ranked guess (0-1) | 0.85 = strong match |
| `artifact_ranking` | Ordered list of artifact guesses | `["container", "vm", "baremetal"]` |

### Source/Destination Identifiers (for cross-checking)
| **Column** | **Meaning** | Example |
|------------|-------------|---------|
| `workload_id_src` | Source workload ID | Hash of MAC, IP, port |
| `mac_src` | Source MAC address | `00:1A:2B:3C:4D:5E` |
| `ip_src` | Source IP address | `192.168.1.5` |
| `src_port` | Source port | 443 |
| `workload_id_dst` | Destination workload ID | Hash of MAC, IP, port |
| `mac_dst` | Destination MAC address | `00:1A:2B:3C:4D:5F` |
| `ip_dst` | Destination IP address | `10.0.0.1` |
| `dst_port` | Destination port | 8080 |

---

## What to Check

✅ Do **high-degree, stable workloads** align with **bare metal or VM** in your experience?  
✅ Are **bursty, short-session workloads** realistically **serverless**?  
✅ Do **high-peer workloads** look like **APIs/gateways** in practice?  
✅ Spot **mismatches**: Any containers that feel like VMs, or vice versa?  
✅ Any patterns you’d expect but don’t see?  
