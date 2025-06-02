# Cloud Engineer Validation Guide: Understanding the Dataset Columns

## What This Dataset Is

This dataset contains **workload-level information**, extracted from **PCAP network traffic**. Each **row** is a unique workload (an application, service, or machine), identified by MAC, IP, and port.  

The dataset maps **network behavior to deployment artifacts** (like containers, VMs, bare metal) based on observed communication patterns.

---

## Column-by-Column Explanation

| **Column** | **Plain Language Meaning** | **Why It Matters** |
|------------|---------------------------|--------------------|
| `inferred_artifact_type` | Our best guess for what kind of deployment it is | E.g., "baremetal", "vm", "container" |
| `artifact_type_ranked` | Ranked list of likely deployment types | Shows other possibilities, like a top-3 |
| `artifact_type_top_score` | Score for the top-ranked guess (closer to 1 = stronger match) | Confidence in the top guess |
| `artifact_type_entropy` | How certain we are about the guess (lower = better) | 0.2 = high confidence, 1.0 = uncertain |

### Network Behavior Columns

| **Column** | **Plain Language Meaning** | **Example/Interpretation** |
|------------|---------------------------|---------------------------|
| `degree` | How many other workloads this one talks to | High = core service; low = edge workload |
| `flow_count` | Number of communication flows | High = busy API or server; low = passive client |
| `community_size` | Size of the cluster this workload belongs to (via Louvain detection) | Large = microservices group; small = isolated service |
| `burstiness` | Is the workload’s traffic spiky (1) or stable (0)? | Bursty → serverless; stable → VM/baremetal |
| `session_length` | How long sessions last on average | Long = stable VM/backend; short = serverless/microservice |
| `peer_count` | Number of unique peers (destinations) the workload connects to | High = API, load balancer; low = isolated service |
| `data_volume` | Total bytes sent/received | High = data-intensive workload (e.g., DB, analytics) |

### Additional Context Columns

| **Column** | **Plain Language Meaning** | **Example/Interpretation** |
|------------|---------------------------|---------------------------|
| `is_virtual_machine` | Flag: Is this workload likely virtual? | Based on MAC OUI or IP reuse |
| `is_data_intensive` | Flag: Sends/receives a lot of data | High-volume workloads (e.g., DB, file servers) |
| `is_stable_workload` | Flag: Low volatility, long sessions | Backend, VM-like workloads |
| `is_bursty_dst` | Flag: Destination has bursty traffic | Suggests serverless or event-driven pattern |
| `is_compliance_sensitive` | Flag: Internal, stable, long sessions | Compliance-relevant workloads (e.g., databases) |

---

## What You’ll See in the Data

Here’s a **sample row** to help you orient yourself:

| inferred_artifact_type | artifact_type_ranked | artifact_type_entropy | degree | flow_count | community_size | burstiness | session_length | peer_count | data_volume |
|------------------------|----------------------|-----------------------|--------|------------|----------------|------------|----------------|------------|-------------|
| vm                     | ["vm", "baremetal"]  | 0.3                   | 10     | 150        | 8              | 0          | Long (seconds) | 5          | 1 GB        |
| serverless             | ["serverless", "container"] | 0.6             | 2      | 20         | 3              | 1          | Short (seconds) | 1          | 100 MB      |

---

## What I Need From You

✅ Review if these **artifact guesses** make sense:  
- Are high-degree, stable workloads really **bare metal** or **VM** in your world?  
- Are bursty, short-session workloads realistically **serverless**?  
- Do high-peer workloads match **API gateways** in practice?  

✅ Spot any **surprises or mismatches**:  
- Any workloads labeled **container** that seem more like **VMs**?  
- Any missing patterns that you’d expect?  

✅ **Feedback on usability**:  
- Would this help your team with placement, security, optimization, or migration?  

---
