
### BACKBONE OF INDUSTRIAL KNOWLEDGE OF TRANSDICAPLINARY RESEARCH -> BRIDGE INTO ACADEMIA VIA METHODOLOGY -> NETWORK SCIENCE METHODS -> FIND A WAY TO CREATE SCORING SYSTEM: QUANTIFY QUALITATIVE CHARACTERISTICS

# **Cloud Deployment Artifacts and Workload Optimization**

We distinguish technologies that provide environments where applications can execute and serve the purpose of running code as deployment options. All options involve the allocation and management of computing resources (CPU, memory, storage) and require network connectivity to interact with other systems and the internet. Different deployment options offer varying levels of abstraction, resource allocation, and management complexity. Understanding their characteristics helps in choosing the right approach for specific use cases. We distinguish the following models, derived from *industry knowledge*, *operational patterns*, and *practitioner experience* in managing complex systems:

**Serverless functions** are event-driven, stateless, and scale automatically but are ephemeral.

**Containers** provide lightweight process isolation and share the OS kernel.

**Orchestrated containers** use tools like Kubernetes to manage clusters of containers dynamically.

**VMs** offer full OS virtualization, leading to stronger isolation but higher overhead.

**Mini-VMs** (e.g., Firecracker, Kata Containers) balance security with performance, having lower overhead than full VMs.

**Bare Metal servers** provide maximum control and performance but lack the flexibility of virtualization. 

## Industry-Grounded Heuristic Mapping
These models are not purely theoretical: their traits reflect years of operational experience in cloud, hybrid, and datacenter environments. The mappings are derived from practical observations of system behavior, such as:
- Stability of flows
- Density of communication patterns
- Burstiness and volatility

Theoretical Foundation for Deployment Artifact Inference
Table 1 outlines the theoretical characteristics of common deployment artifacts, including serverless functions, containers, virtual machines, and baremetal servers. Each artifact type exhibits distinct properties across dimensions such as abstraction level, resource allocation, startup time, isolation, and state management (e.g., AWS, 2023; CNCF, 2023). These properties serve as a conceptual reference for inferring deployment artifacts from workload graphs.

**TABLE 1**:

| Aspect | Serverless Functions | Containers | Orchestrated Containers | Virtual Machines (VMs) | Mini-VMs (e.g., Firecracker) | Baremetal Server |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| **Abstraction**  **Level** | Function-level (high) | Process-level | Multi-container application | OS-level | Lightweight VM | Hardware-level |
| **Resource Allocation** | Fully managed, ephemeral | Shared kernel | Dynamic allocation via orchestrator | Dedicated resources per VM | Lower overhead per VM | Full machine control |
| **Startup Time** | Milliseconds | Seconds | Seconds | Minutes | Milliseconds | Instant (if running) |
| **Performance** | High but cold start penalty | High | High | Moderate to high | High | Highest |
| **Isolation** | Low (multi-tenant) | Moderate (namespaces) | Moderate to high (policy-based) | Strong (hardware-based) | Strong (lightweight VM isolation) | None (full access) |
| **State Management** | Stateless | Usually stateless | Managed via volumes, services | Managed with storage | Managed with storage | Full control |
| **Scaling** | Automatic | Manual or scripted | Automatic via orchestrator | Manual | Fast auto-scaling possible | Manual |
| **Management Overhead** | Lowest (fully managed) | Moderate (manual setup) | High (orchestrator complexity) | High (OS updates, networking) | Moderate (simpler than full VMs) | Highest (full admin) |
| **Cost Model** | Pay-per-use | Resource-based pricing | Resource-based pricing | Pay for VM uptime | Pay per lightweight VM | Fixed cost (hardware) |

**Mapping Deployment Artifact Traits to Graph-Derived Signals**

To operationalize these characteristics, we design a linear scoring system that maps graph-derived features to artifact-specific signals:

| Aspect | What to Look for in Graph | Why It Matters | Example Patterns |
| :---- | :---- | :---- | :---- |
| Abstraction Level | Graph topology: singleton, hub, dense cluster; node degree distribution | Serverless = singleton, bursty; Containers = dense clusters; VMs = mid-size communities | Serverless: singleton nodes with few edges; Containers: densely connected clusters; VMs: flatter, tiered graph structures |
| Resource Allocation | Node degree; community size; flow count per node | High degree & flows = dedicated (baremetal/VM); low = shared resources (containers, serverless) | Baremetal: high degree, stable flows; Serverless: low degree, low flows; Containers: moderate degree, variable flows |
| Startup Time | Flow initiation patterns; delays after idle; graph burstiness | Serverless shows cold starts: bursty, delayed flows; VMs and containers show consistent flows | Serverless: isolated edges appearing after idle period; VMs: stable edges; Containers: small, frequent bursts |
| Performance | Degree variance; betweenness centrality; clustering coefficient | High variance → orchestration/shared infra; stable metrics → baremetal/VMs | Orchestrated containers: variable degrees, moderate clustering; Baremetal: stable, high degree nodes |
| Isolation | Node uniqueness (MAC/IP mappings inferred via graph roles); community separation | Unique nodes = higher isolation (baremetal/VMs); shared = containers/serverless | Containers: dense, shared clusters; Baremetal: isolated, non-overlapping nodes |
| State Management | Flow persistence; burst vs. sustained edges | Serverless = short, bursty flows; Containers/VMs = persistent flows with stateful services | Serverless: short-lived edges, no re-use; VMs: edges persisting across time intervals |
| Scaling | Graph growth patterns; community size change over time | Rapid graph expansion/contraction → dynamic scaling (serverless/containers); static → baremetal/VM | Orchestrated: community size fluctuates; Serverless: singleton nodes appearing/disappearing; Baremetal: stable node count |
| Management Overhead | Presence of control-plane nodes (identified via roles); central hubs | Baremetal/VMs → admin/control plane traffic; Containers → orchestration control nodes (K8s) | VMs: admin nodes with stable connections; K8s: etcd/CoreDNS; Serverless: minimal control-plane structure |
| Cost Model | Session duration; flow frequency; burstiness | Short-lived, bursty flows → usage-based (serverless); stable, long flows → reserved (VMs, baremetal) | Serverless: high churn, idle periods; VMs: sustained flows over time; Containers: moderate churn |

# This mapping enables the system to infer artifact types by computing a composite score for each workload node in the graph:

S(n) = ∑(i=1 to k) wᵢ ⋅ fᵢ(n)

where fᵢ(n) are graph-derived features for node n and wᵢ are weights aligned with the theoretical characteristics.
----
**Bare Metal Servers** provide direct access to physical hardware and full control over server infrastructure. From an application perspective bare metal servers offer the highest performance, the lowest overhead and the highest level of security isolation, but require the most manual management. Bare metal servers are used for high-performance computing, applications with specific hardware requirements and workloads needing consistent, predictable performance.

**Virtual Machines (VMs)** provide a complete virtualized operating system using a hypervisor for isolated environments with dedicated resources. Operators can run multiple different OS types on the same physical hardware with full OS-level control, moderate overhead and resource consumption. Virtual server are used to run multiple different application environments, for legacy application hosting and scenarios that require full OS customization

**Mini-VMs (Lightweight VMs)** have a smaller footprint compared to traditional VMs and faster startup times with less resource overhead. Employing hardware (chip-based) virtualization, they only require a hypervisor for partial OS virtualization and are more efficient than full VMs, but less efficient than containers. Lightweight VMs are used for microservices with moderate isolation requirements, for development and testing environments and applications needing more isolation than containers

**Containers are** lightweight user space representations that share a single host OS kernel and enable rapid deployment and scaling with a consistent environment across development and production. Containers require minimal resource overhead and can rely on standardized packaging of applications. Containers are used in distributed or ‘cloud-native’ environments and allow for continuous integration/continuous deployment (CI/CD).

**Orchestrated Containers** rely on a central intelligence in a multi-server cluster environment for automated container management, dynamic scaling and load balancing and self-healing capabilities. The orchestrator abstracts complex networking and and provides service discovery capabilities to enable centralized container deployment and management. Orchestrated containers are ised for large, distributed microservices architectures that empower highly scalable applications in complex, dynamic computing environments.

**Serverless Functions** enable ephemeral, event-driven execution of containers with limited execution time and resources. Functions are extremely lightweight and fast and run with zero server management, scale automatically and are usually offered with a pay-per-execution pricing model. Functions are used for event-driven processing, intermittent or unpredictable workloads and microservices with specific, short-running tasks

From a provider perspective bare metal servers require physical servers dedicated to a single tenant. Virtual machines (VMs) a delivery environment for software-based emulation of physical hardware. Containers lightweight, portable execution environments that share the host OS kernel, orchestrated containers and orchestration platforms like Kubernetes and serverless functions and event-framework that enables stateless execution. The choice between these technologies depends on factors such as communication patterns, performance needs, and management overhead.


## **Workload Optimization**

We look at the different artifact types to distinguish workloads that we run on dedicated, private infrastructure versus distributed, shared (cloud) environments. To determine the right target we classify artifacts that carry workloads in two dimensions, the consumption profile and the need for data sovereignty.

### Consumption Profile 

**Variable Workloads \-** Distributed systems, hence public clouds excel at handling fluctuating workloads due to their scalability. Organizations can use public cloud resources for peak demands and scale down during lulls, avoiding the cost of maintaining excess on-premises capacity.  This "pay-as-you-go" model is ideal for applications with unpredictable traffic patterns.  

**Stable Workloads \-** Dedicated hardware runs predictable and consistent workloads more cost-effective in a private cloud or on-premises environment, because it requires less operational overhead. By keeping these workloads in-house, organizations avoid the ongoing costs of public cloud usage.  

| Trait | What to Look For in Data | Heuristic Have |
| :---- | :---- | :---- |
| **Variable Workloads** (Cloud-friendly, bursty usage) | 🔸 High session volatility 🔸 Short lifespan (frame\_time\_epoch) 🔸 High TTL variability 🔸 Many external flows (flow\_relation) 🔸 Frequent port variation (many src\_port/dst\_port combinations) 🔸 MAC/IP reuse (many MACs per IP or vice versa) | ✔ session\_volatility ✔ ttl\_variability ✔ flow\_relation ✔ IP-to-MAC mapping (ip\_reuse) |
| **Stable Workloads** (On-prem/dedicated-friendly) | 🔸 Low session volatility 🔸 Consistent TTL 🔸 Mostly internal\_only flows 🔸 Long active duration per MAC+IP 🔸 Low MAC/IP reuse | ✔ is\_stable\_workload (you can derive) ✔ flow\_relation analysis |

### Data Sovereignty 

**Data-Intensive Workloads \-** Storing and processing large volumes of data in the public cloud can be expensive.  A hybrid approach allows organizations to keep data-intensive workloads in a private cloud, potentially reducing data transfer and storage costs.

**Compliance-Sensitive Workloads \-** Maintaining sensitive data within a private cloud or on-premises environment can minimize compliance risks and associated costs.  This approach allows organizations to leverage the public cloud for less sensitive data and applications.

| Trait | What to Look For | Heuristic Add |
| :---- | :---- | :---- |
| **Data-Intensive Workloads** | 🔸 High volume per MAC+IP 🔸 High byte count (requires frame\_len aggregation) 🔸 Repeated large flows between internal nodes | Add: data\_volume \= df.groupby('mac\_ip\_combo')\['frame\_len'\].sum() |
| **Compliance-Sensitive Workloads** | 🔸 Internal flows only 🔸 MACs/IPs that never communicate with external endpoints 🔸 Long-lived services (low churn) | ✔ flow\_relation \= 'internal\_only' ✔ Long active durations |


## 📚 Related Research Articles

### 📘 1. DevOps Workflow Optimization: Enhancing Deployment and Efficiency for Cloud Applications  
**Authors**: Devik Pareek & Prashanth K  
**Published**: 2024  
**Summary**:  
This paper explores DevOps workflow optimization techniques, including automation, CI/CD processes, Infrastructure as Code (IaC), and monitoring. It provides guidance on increasing deployment velocity and operational efficiency for cloud-hosted applications.  
**Access**: [ResearchGate](https://www.researchgate.net/publication/384460916_DevOps_workflow_optimization_Enhancing_deployment_and_efficiency_for_cloud_application)

---

### 📘 2. Towards Workload-aware Cloud Efficiency: A Large-scale Empirical Study of Cloud Workload Characteristics  
**Authors**: Mateo Clement  
**Published**: 2024  
**Summary**:  
This study analyzes various virtualization solutions, such as hypervisors and container-based approaches, providing insights into how virtualization influences performance and cost-effectiveness in cloud computing environments. It offers recommendations for optimizing cloud efficiency through appropriate virtualization technologies.  
**Access**: [ResearchGate](https://www.researchgate.net/publication/391454975_Towards_Workload-aware_Cloud_Efficiency_A_Large-scale_Empirical_Study_of_Cloud_Workload_Characteristics)

---

### 📘 3. Containerization in Multi-Cloud Environment: Roles, Strategies, Challenges, and Solutions for Effective Implementation  
**Authors**: Muhammad Waseem et al.  
**Published**: 2024  
**Summary**:  
This research systematically investigates containerization in multi-cloud environments, identifying themes like scalability, performance optimization, security, and monitoring. It categorizes strategies and challenges, providing a comprehensive overview for effective containerization implementation.  
**Access**: [arXiv](https://arxiv.org/abs/2403.12980)

---

### 📘 4. Recent Improvements in Cloud Resource Optimization with Dynamic Workloads  
**Authors**: Not specified  
**Published**: 2024  
**Summary**:  
This article examines advancements in optimizing cloud resources for dynamic workloads using machine learning. It reviews approaches and frameworks aimed at improving resource allocation, performance, and cost-effectiveness in cloud systems.  
**Access**: [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4803863)

---
