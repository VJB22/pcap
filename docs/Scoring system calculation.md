  ## Linear Scoring Formula for Deployment Artifact Inference

We create a general formula where each artifact type is assigned a score profile across graph-derived features:

\[
S(n) = \sum_{i=1}^{k} w_i \cdot f_i(n)
\]

Where:

- **S(n)** = Artifact score for node *n*
- **fᵢ(n)** = Graph-derived feature *i* for node *n*
- **wᵢ** = Weight for feature *i*, aligned with artifact theory

### Feature Mapping (Based on Cloud deployment artifact document)

| Feature               | Signal (Graph)                       | Why It Matters                                           | Weight wᵢ                                       |
|-----------------------|--------------------------------------|-----------------------------------------------------------|-------------------------------------------------|
| Degree                | deg(n)                               | High degree → stable flows → VM/Baremetal                 | +1.5 for VM/Baremetal; -1.5 for Serverless      |
| Community Size        | \|C(n)\|                             | Large clusters → Orchestrated; Singleton → Serverless     | +2.0 Orchestrated; -2.0 Serverless              |
| Flows per Node        | Σ flows(n)                            | High flows → Dedicated resources                          | +1.5 Baremetal; +1.0 VM                         |
| Session Volatility    | sv(n)                                 | High volatility → Serverless                              | -2.0 Baremetal/VM; +2.0 Serverless              |
| TTL Variability       | ttl(n)                                | High TTL variance → Cloud/Bursty                          | -1.5 Baremetal/VM; +1.5 Serverless              |
| Component Type Score  | Singleton=0, Chain=1, Cluster=2, Hub=3 | Topology indicator for artifact type                      | +2.0 Orchestrated/Containers; 0 Baremetal       |
| Data Volume           | bytes(n)                              | High data → Baremetal/VM                                  | +1.5 Baremetal/VM                               |
| External Flow Ratio   | external_ratio(n)                      | High → Cloud; Low → On-Prem                               | +2.0 Cloud (Serverless/Container); -2.0 Baremetal/VM |

### Final Scoring Formula

For each node *n*:

\[
S(n) = 1.5 \cdot \deg(n) + 2.0 \cdot |C(n)| + 1.5 \cdot \text{flows}(n) - 2.0 \cdot sv(n) - 1.5 \cdot ttl(n) + 2.0 \cdot comp(n) + 1.5 \cdot bytes(n) + 2.0 \cdot external\_ratio(n)
\]

Where:

- **deg(n)** = Degree of node
- **|C(n)|** = Community size
- **flows(n)** = Sum of flows across edges
- **sv(n)** = Session volatility
- **ttl(n)** = TTL variability
- **comp(n)** = Component type score
- **bytes(n)** = Total bytes sent/received
- **external_ratio(n)** = Ratio of external flows to total flows

### Threshold Heuristics for Artifact Classification

| Artifact      | Score Range (Example)         | Dominant Traits                                         |
|---------------|-------------------------------|----------------------------------------------------------|
| Baremetal     | Highest (>90th percentile)    | High degree, stable flows, low volatility                |
| VM            | High (70th–90th percentile)   | Moderate degree, stable flows, mid-size communities      |
| Orchestrated  | Mid-High (50th–70th percentile) | Clustered, variable degree, external flows               |
| Container     | Mid (30th–50th percentile)    | Dense clusters, moderate volatility                       |
| Mini-VM       | Mid-Low (10th–30th percentile) | Chain-like, small communities                             |
| Serverless    | Low (<10th percentile)        | Singleton, low degree, high volatility, bursty flows      |
