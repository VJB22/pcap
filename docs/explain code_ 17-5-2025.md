**What is missing:**

1. **Edge cases or hybrid types**: Some real workloads might have mixed signals or uncommon patterns that need nuanced handling beyond these categories.  
2. **Additional signals**: one could refine with more features like latency patterns, TLS version specifics, or protocol combinations if data supports them.

# CODE:

- **bidirectional workloads (src, dst)**

### **1\. Network Layer (Infrastructure & Traffic Patterns)**

* **Switch Detection:**

  * Identifies switches by MAC address reuse across multiple IPs (`ip_mac_df` count \> 3).  
  * Detects broadcast nodes (`ff:ff:ff:ff:ff:ff`) and forward-only MAC addresses (MACs appearing only as source, never destination).

* **Router Classification:**

  * Uses flow directionality (internal/external) to classify routers as either **internal\_router** or **external\_router**.

* **TTL Variability:**

  * High TTL standard deviation flags unstable/ephemeral hosts, often virtual or containerized workloads.

* **Communication Metrics:**

  * Fan-in/out counts from unique peer IPs to identify ‘talkative’ workloads or gateways.  
  * Response delays and burstiness to characterize traffic rhythmicity and workload behavior.

### **2\. Storage Layer (Heavy Data & Session Characteristics)**

* **Data Volume:**

  * Aggregates total data transferred per MAC-IP combination, flagging workloads with high data volumes as `is_data_intensive`.

* **Session Length & Stability:**

  * Measures session duration (`session_length_src/dst`) and session volatility to differentiate stable vs volatile workloads.

* **Compliance Sensitivity:**

  * Flags internal-only workloads with long sessions as potentially compliance-sensitive storage or backend systems.

* **Financial Protocol Activity:**

  * Detects financial traffic patterns (TLS without HTTP, FIX, ISO8583, SWIFT protocols) indicating storage or backend transactional roles.


### **3\. Compute Layer (Workload Artifact Inference)**

* **Workload Identification:**

  * Generates unique workload IDs by hashing MAC \+ IP \+ Port tuples for source and destination workloads.

* **Artifact Type Classification:**

  * Uses combined behavioral and infrastructure flags to classify workloads into compute artifacts:

    * **Serverless:** Stable, bursty workloads (financial API patterns).  
    * **Container:** Volatile workloads with moderate data and session patterns.  
    * **Orchestrated Container:** Containers with high peer counts and bursty communication (microservice orchestration).  
    * **Mini-VM:** Virtual MACs with stable, low data sessions (lightweight VMs).  
    * **VM:** Virtual MACs with heavy or unstable sessions (full VMs).  
    * **Baremetal:** Physical hosts with heavy data, long sessions, and compliance needs (dedicated servers).

* **Fallback Logic:**

  * Assigns ambiguous workloads based on virtual flags, container volatility, router roles, or switch detection.

* **Scoring & Ranking:**

  * Scores each workload for likelihood of artifact types using weighted behavioral flags.  
  * Calculates entropy to quantify classification uncertainty.  
  * Ranks artifact types per workload for probabilistic inference.

## **Boolean Flags (True/False) Explained:**

These flags represent diagnostic conditions that assist in classifying network behaviors and roles:

| Flag | Explanation (when True) |
| ----- | ----- |
| **is\_virtual\_machine** | MAC address matches known VM-specific prefixes. |
| **is\_tls\_without\_http** | TLS handshake detected but not using standard HTTP port (80). |
| **is\_probably\_tls\_handshake** | TLS handshake likely occurring without visible TLS metadata (heuristic, encrypted traffic). |
| **is\_large\_frame** | Frame payload size exceeds 1400 bytes (large payloads). |
| **is\_quic** | Traffic on UDP port 443 without explicit TLS data (likely QUIC protocol). |
| **is\_dns\_query / response** | DNS query or response explicitly identified. |
| **has\_tcp / udp / tls / fix / iso8583 / swift / rtsp / rtp / rtcp / icmp / igmp / arp** | Presence of respective protocols in the analyzed packet. |
| **is\_possible\_switch** | Device shows IP associated with multiple MACs, forward-only MAC addresses, or broadcasts, indicating a potential network switch. |
| **is\_router (external/internal)** | Traffic pattern indicates router activity: external routers handle cross-network traffic, internal routers handle internal traffic only. |
| **is\_possible\_vm\_by\_ip\_reuse** | IP address frequently reused by different MAC addresses, indicating VM activity. |
| **is\_possible\_container** | High volatility in session creation and destruction (typical container behavior). |
| **is\_ttl\_unstable** | TTL values highly variable, typical of virtualized/container workloads. |
| **is\_physical\_machine** | Not flagged as VM/container, thus a physical (non-virtualized) host. |
| **is\_data\_heavy / intensive** | Transferring large payloads or large volumes of data frequently. |
| **is\_fin\_api\_pattern** | Exhibits financial API communication patterns (TLS without HTTP plus heavy payload). |
| **is\_stable\_workload** | Consistently low volatility, stable communication sessions. |
| **is\_compliance\_sensitive** | Long-lived, internal-only sessions potentially significant for compliance/security. |
| **is\_api\_backend / gateway\_pattern** | Identifies services as backend API servers or gateway/load balancer patterns. |

## **Categorical Labels (inferred\_artifact\_type):**

Traffic is categorized into deployment artifacts based on heuristics and flags:

* 'serverless': Stable financial API pattern workloads.  
* 'vm': Backend APIs with unstable workloads.  
  'load\_balancer': Financial API pattern without heavy data payload.  
* 'container': Stable, data-intensive workloads.  
* 'baremetal': Internal-only compliance-sensitive workloads.  
* 'unknown': Doesn't match above criteria.

## **Financial Risk Heuristics (not applicable for our dataset)**

The script calculates a financial\_suspect\_score based on risky indicators such as:

* Non-standard TLS usage (without HTTP)  
* Large frames  
* QUIC protocol  
* DNS activity  
* Specific TCP/UDP ports known for financial transactions (443, 8443, etc.)  
* Financial protocols (FIX, SWIFT, ISO8583)

Flagged as **is\_likely\_financial** if the score is ≥ 4\.

## **Communication Pattern Analysis:**

Analyzes behavioral metrics for each workload:

* **Persistence:** Active time and connection count.  
* **Symmetry/Delay:** Bytes sent/received and response times.  
  **Fan-out/Fan-in:** Unique peers communicated with.  
  **Rhythmicity:** Burst-like or consistent (rhythmic) communication patterns (is\_bursty).

## **Infrastructure Heuristics:**

* Identifies **switches**, **routers**, **VMs**, **containers**, and **physical hosts** through IP/MAC reuse, TTL instability, and flow patterns.

### **How Thresholds Were Defined**

| Feature | Threshold | Reason |
| ----- | ----- | ----- |
| `payload_size > 800` | Static | Typical MTU/payload size beyond headers |
| `payload_rate_dst > 0.75 quantile` | Empirical | Captures top 25% throughput consumers |
| `data_volume > 0.60 quantile` | Empirical | Used to mark intensive talkers |
| `session_volatility > 0.65 quantile` | Empirical | Marks unstable/bursty sessions |
| `ttl_variability > median + std` | Statistical | Indicates routing instability or virtualized networks |
| `active_minute_count < 0.5 * active_seconds / 60` | Derived | Heuristic for burstiness over time |
| `mac_src count per ip_src > 3` | Empirical | IP reuse heuristic for switches or DHCP pools |
| `peer_count_dst >= 5` | Static | Orchestration implies high fanout |
| `score sum == 0` → entropy fallback | Logic | Avoids division by 0 for sparse rows |

## For this thesis, thresholds were applied as part of an experimental approach to feature extraction from PCAP data. These thresholds serve as a starting point, but they are not universal. The optimal thresholds depend on the specific characteristics of the dataset under analysis—particularly the context of the PCAP capture (e.g., network topology, traffic patterns, and typical workloads).
## Experts should iteratively test and refine these thresholds based on their own data, following a test-and-adjust process or deriving thresholds empirically through exploratory analysis and statistical profiling of their datasets over time.

## Why Use Percentiles Instead of Averages?
As Dynatrace points out in this article (https://www.dynatrace.com/news/blog/why-averages-suck-and-percentiles-are-great), averages are ineffective because they oversimplify complex distributions. Percentiles provide a more accurate, multi-dimensional view of system behavior, allowing for:
Precise detection of anomalies,
Effective baselining and behavioral learning,
Informed optimization of thresholds for performance and security monitoring.

Percentiles are widely used in network analysis. For instance, the 95th percentile is a common standard in bandwidth metering, as discussed in:
[NetCraftsmen,](https://netcraftsmen.com/networking-by-the-95th-percentile)
[Auvik.](https://www.auvik.com/franklyit/blog/95th-percentile-bandwidth-metering)

## 1. Payload Size > 800 Bytes
Rationale: The Ethernet MTU is 1500 bytes. Subtracting headers (~40 bytes) leaves ~1460 bytes for payloads. Setting a threshold at 800 bytes flags unusually large payloads that may signal data exfiltration or tunneling.
Adjustment Considerations:
In environments with large payloads (e.g., file transfers), this threshold may trigger false positives.
In environments with predominantly small payloads, a lower threshold may be better.
Supporting Research:
[ ResearchGate - NSF Study](https://par.nsf.gov/servlets/purl/10205654)

## 2. Payload Rate per Destination > 0.75 Quantile
Rationale: The 75th percentile identifies the top 25% of throughput consumers, highlighting destinations with high data rates potentially linked to exfiltration or DDoS activity.
Adjustment Considerations:
Use a higher percentile (e.g., 90th) in high-throughput environments to avoid false positives.
Use a lower percentile (e.g., 60th) in low-throughput environments for sensitivity.
Supporting Research:
[CEUR Workshop Paper](https://ceur-ws.org/Vol-3746/Paper_7.pdf)

## 3. Data Volume > 0.60 Quantile
Rationale: The 60th percentile flags sources/destinations contributing a significant share of data volume, identifying "intensive talkers."
Adjustment Considerations:
In environments with high variance in data volume, consider a higher percentile.
In uniform environments, a lower percentile might suffice.
Supporting Research:
[ Dynatrace](https://www.dynatrace.com/news/blog/why-averages-suck-and-percentiles-are-great)

## 4. Session Volatility > 0.65 Quantile
Rationale: Captures bursty or unstable sessions, possibly indicating scanning or probing behavior.
Adjustment Considerations:
Raise the threshold in noisy environments.
Lower it in stable environments.
Supporting Research:
[ arXiv Preprint](https://arxiv.org/abs/0905.1983)

## 5. TTL Variability > Median + Standard Deviation
Rationale: High TTL variability may point to routing instability or virtualized networks.
Adjustment Considerations:
Lower the threshold in stable routing networks.
Raise it in dynamic routing environments.
Supporting Research:
[ UCLA Globcom](https://web.cs.ucla.edu/~lixia/papers/98Globcom.pdf)

## 6. Active Minute Count < 0.5 × Active Seconds / 60
Rationale: Derived heuristic to detect bursty, sporadic sessions by comparing active minutes and total active seconds.
Adjustment Considerations:
Adjust in environments with frequent short bursts to reduce false positives.
Supporting Research:
 [TUM Report](https://www.net.in.tum.de/fileadmin/TUM/NET/NET-2010-06-1.pdf)

## 7. MAC Source Count per IP Source > 3
Rationale: Indicates potential IP reuse (e.g., via switches or DHCP pools).
Adjustment Considerations:
Use a higher threshold for dynamic IP networks.
Lower the threshold for static environments.
Supporting Research:
[ Cisco Documentation](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst2960/software/release/12-2_58_se/configuration/guide/2960scg/swdhcp82.html)
 
## 8. Peer Count per Destination ≥ 5
Rationale: Suggests high fan-out, common in orchestrated environments or scanning behavior.
Adjustment Considerations:
Increase for microservices architectures.
Decrease for traditional client-server models.
Supporting Research:
[ Cloudera Docs](https://www.cisco.com/c/en/us/td/docs/switches/lan/catalyst2960/software/release/12-2_58_se/configuration/guide/2960scg/swdhcp82.html)


## WHAT WAS FOUND:

| My Finding | How It Connects to Finding the Best Deployment Artifact |
| ----- | ----- |
| **I found 124 unique source workloads and 55 unique destination workloads** | This shows me the distinct network entities, helping me isolate separate deployment units for accurate artifact assignment. |
| **I observed an average frame size of about 1264 bytes and max frame size of 1514 bytes** | Larger frames usually mean physical or VM deployments with heavy data transfer, guiding me to classify these as "baremetal" or "vm". |
| **I detected no TLS, FIX, or ISO8583 protocol usage** | The absence of these financial protocols suggests that many workloads may be generic containers or serverless functions, not specialized secure servers. |
| **I saw high UDP (2,124,069) and TCP (376,842) packet counts** | A high UDP volume can indicate microservices or containerized workloads, while TCP dominance hints at traditional VM or baremetal. |
| **I noticed only 20 DNS queries, no DNS responses, and no QUIC traffic** | This limited DNS activity suggests static workloads or internal-only services, steering me away from serverless classifications. |
| **I found zero flows flagged as likely financial** | This tells me the workloads are less compliance-sensitive, making containerized or serverless options more likely than baremetal or VMs requiring strict compliance. |
| **I detected 1,828 possible switches by MAC reuse \> 3** | This helps me exclude infrastructure devices from workload artifact classification, improving accuracy. |
| **I found internal routers (2,501,866) far outnumber external routers (217)** | This means most traffic is internal, so artifacts are probably within private cloud or data center, which guides me towards VM, container, or baremetal types. |
| **I counted 22,479 VM OUIs, 1,649,616 VM by IP reuse, and 346 containers** | These high virtual counts with IP reuse show widespread virtualization, pushing me to classify workloads as VMs or orchestrated containers. |
| **I observed TTL instability in 150 hosts** | TTL variability signals ephemeral or containerized workloads, guiding me to assign "container" or "serverless" artifacts. |
| **I counted 853,889 physical hosts** | This large number tells me there’s a significant baremetal presence, so I classify those workloads accordingly. |
| **I measured average session lengths greater than 1200 seconds** | Long sessions indicate stable VMs or baremetal servers rather than short-lived serverless functions. |
| **I found average fan-in/out around 2-3 with maximums up to 7** | Moderate fan-out suggests orchestrated containers or load balancers, so I classify some workloads as "orchestrated\_container". |
| **I saw very few bursty sources (39 sessions) but mostly rhythmic communication (\~2.5 million)** | This rhythmic pattern means workloads are stable and long-lived, like VMs or baremetal, not serverless. |
| **I inferred most artifacts as 'baremetal' (1,077,589) or 'None' (1,426,678)** | Baremetal dominates, indicating many stable physical machines; the large None count makes me apply fallback logic to assign containers or VMs. |
| **I applied fallback logic that mostly assigns 'container' to unknown workloads (1,419,431)** | Many ambiguous workloads fit container patterns, so I classify them accordingly to fill the gap between baremetal and VMs. |

**How My Findings Help Me Identify the Best Deployment Artifact:**

* **Physical hosts \+ long sessions \+ large frames** → I classify these as **baremetal** workloads because they indicate stable, heavy data transfers on physical servers.

* **High virtual MAC counts \+ IP reuse \+ moderate session lengths** → I interpret this as many workloads running on **virtual machines (VMs)** — stable but virtualized.

* **TTL instability \+ bursty communication \+ fallback assignments** → These point me towards **containers** or **orchestrated containers**, which are more ephemeral and volatile.

* **Low presence of serverless indicators \+ rhythmic patterns \+ limited DNS/QUIC** → I conclude **serverless** is rare or minimal in this dataset.

* **Infrastructure heuristics for switches and routers** → I use these to avoid misclassifying network devices as compute workloads, improving artifact assignment accuracy.

Readings:

### **1\. "Using Network Traffic to Infer Hardware State: A Kernel-Level Investigation"**

**Authors**: Lanier Watkins, William H. Robinson, Raheem Beyah  
 **Published in**: ACM Transactions on Embedded Computing Systems, 2015  
 **DOI**: [10.1145/2700094](https://doi.org/10.1145/2700094)[ResearchGate](https://www.researchgate.net/publication/276550505_Using_Network_Traffic_to_Infer_Hardware_State_A_Kernel-Level_Investigation?utm_source=chatgpt.com)

**Summary**:  
 This study demonstrates that it's possible to infer the internal hardware state of a general-purpose computing node by analyzing its network traffic. By identifying delay signatures in packet timing—caused by factors like CPU load and memory access delays—the researchers correlate these patterns with hardware utilization levels. This approach enables remote assessment of a system's hardware performance without direct access to the device.

**2\. "Understanding the Micro-Behaviors of Hardware Offloaded Network Stacks with Lumina"**

**Authors**: Zhuolong Yu, Bowen Su, Wei Bai, Shachar Raindel, Vladimir Braverman, Xin Jin  
 **Presented at**: ACM SIGCOMM 2023  
 **Link**: [Lumina Paper](https://www.cs.jhu.edu/~zhuolong/papers/sigcomm23lumina.pdf)[Department of Computer Science](https://www.cs.jhu.edu/~zhuolong/papers/sigcomm23lumina.pdf?utm_source=chatgpt.com)

**Summary**:  
 The paper introduces Lumina, a tool designed to test and analyze the performance of hardware offloaded network stacks, such as RDMA NICs. By capturing and examining packet behaviors, Lumina identifies micro-behaviors and potential bugs in hardware network stacks. This analysis provides insights into the hardware's operational characteristics through network traffic patterns.[Department of Computer Science](https://www.cs.jhu.edu/~zhuolong/papers/sigcomm23lumina.pdf?utm_source=chatgpt.com)

### **3\. "Methodology for Characterizing Network Behavior of Internet of Things Devices"**

**Authors**: Paul Watrobski, Joshua Klosterman, William Barker, Murugiah Souppaya  
 **Published by**: National Institute of Standards and Technology (NIST), 2020  
 **Link**: [NIST Draft White Paper](https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.04012020-draft.pdf)[NIST Publications](https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.04012020-draft.pdf?utm_source=chatgpt.com)

**Summary**:  
This draft white paper outlines a methodology for characterizing the network behavior of IoT devices. By analyzing PCAPNG files, the approach identifies communication patterns and device types, aiding in the creation of Manufacturer Usage Description (MUD) files. This characterization helps in understanding the hardware and software profiles of IoT devices based on their network traffic.



