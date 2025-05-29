  ## Linear Scoring Formula for Deployment Artifact Inference

We create a general formula where each artifact type is assigned a score profile across graph-derived features (find score distribution across all nodes -> empirical it is defined by my dataset):

**General formula**:

S(n) = ∑(i=1 to k) wᵢ ⋅ fᵢ(n)

Where:

- **S(n)** = Artifact score for node *n*
- **fᵢ(n)** = Graph-derived feature *i* for node *n*
- **wᵢ** = Feature weight, theory-driven and empirically adjusted

---

### Feature Mapping (Based on Cloud Deployment Artifact Document)

| **Feature**             | **Graph Signal**                    | **Why It Matters**                                               | **Weight (wᵢ)**                                        |
|--------------------------|------------------------------------|------------------------------------------------------------------|------------------------------------------------------------|
| **Degree**              | deg(n)                              | High degree → stable, connected workload → VM/Baremetal          | +1.5 VM/Baremetal; -1.5 Serverless                         |
| **Community Size**      | size of community C(n)              | Large clusters → Orchestrated; Singleton → Serverless             | +2.0 Orchestrated; -2.0 Serverless                         |
| **Flows per Node**      | total flows for node n              | High flows → Dedicated resources                                  | +1.5 Baremetal; +1.0 VM                                    |
| **Session Volatility**  | session volatility for node n       | High volatility → Ephemeral, stateless (Serverless)               | -2.0 Baremetal/VM; +2.0 Serverless                         |
| **TTL Variability**     | TTL variability for node n          | High TTL variance → Cloud, bursty, external systems               | -1.5 Baremetal/VM; +1.5 Serverless                         |
| **Component Type Score**| topological score (e.g., Singleton=1, Chain=2, Cluster=3) | Graph topology pattern → Artifact hint                            | +2.0 Orchestrated/Containers; 0 Baremetal                   |
| **Data Volume**         | total bytes sent/received by node n | High data → Baremetal/VM                                          | +1.5 Baremetal/VM                                          |
| **External Flow Ratio** | external flows / total flows        | High → Cloud; Low → On-Prem                                       | +2.0 Cloud; -2.0 Baremetal/VM                              |
| **Role Score**          | NMF latent role score for node n    | Latent embedding (NMF roles)                                      | w_role (tunable, e.g., +1.5)                               |
| **Avg Flow Duration**   | average flow duration per node n    | Long → Persistent (Baremetal/VM); Short → Ephemeral (Serverless)  | +2.0 Baremetal; +1.5 VM; -2.0 Serverless; -1.5 Containers  |
---

### Final Scoring Formula

For each node *n*:

S(n) = 1.5 * deg(n) + 2.0 * |C(n)| + 1.5 * flows(n) - 2.0 * sv(n) - 1.5 * ttl(n) + 2.0 * comp(n) + 1.5 * bytes(n) + 2.0 * external_ratio(n) + wrole * role_score(n)+ d * avg_flow_duration(n)
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
- **role_score(n)** = Role membership from NMF (continuous or categorical)
- **wrole** = Is the weight assigned to this role feature (chosen according to its importance)
- **avg_flow_duration(n)** = Average flow duration per node

Where:
- \( d \) = Time weight for `avg_flow_duration(n)`:
  - **+2.0** for Baremetal
  - **+1.5** for VM
  - **0** for Orchestrated / Mini VM (neutral)
  - **-1.5** for Containers
  - **-2.0** for Serverless

---

### Threshold Heuristics for Artifact Classification

| Artifact      | Score Range (Example)         | Dominant Traits                                         |
|---------------|-------------------------------|----------------------------------------------------------|
| Baremetal     | Highest (>90th percentile)    | High degree, stable flows, low volatility                |
| VM            | High (70th–90th percentile)   | Moderate degree, stable flows, mid-size communities      |
| Orchestrated  | Mid-High (50th–70th percentile) | Clustered, variable degree, external flows               |
| Container     | Mid (30th–50th percentile)    | Dense clusters, moderate volatility                       |
| Mini-VM       | Mid-Low (10th–30th percentile) | Chain-like, small communities                             |
| Serverless    | Low (<10th percentile)        | Singleton, low degree, high volatility, bursty flows      |




## References
Barabási, A.-L. (2016). Network Science. 
(For network metrics: degree, community size, topology patterns)

Newman, M. E. J. (2010). Networks: An Introduction. Oxford University Press. https://doi.org/10.1093/acprof:oso/9780199206650.001.0001
(For foundational graph metrics and models)

Li, D., Zhuang, Y., & Li, J. (2018). A comparative study of containers and virtual machines in big data environment. arXiv preprint arXiv:1807.01842. https://arxiv.org/abs/1807.01842
(For empirical differences in performance between containers and VMs)

Zhang, Y., & Zhang, Y. (2018). Container-based cluster orchestration systems: A taxonomy and future directions. arXiv preprint arXiv:1807.06193. https://arxiv.org/abs/1807.06193
(For understanding orchestrated containers and dynamic scaling)

Gao, M., & Agrawal, D. (2024). Cost modelling and optimisation for cloud: A graph-based approach. Journal of Cloud Computing, 13(1), Article 7. https://doi.org/10.1186/s13677-024-00709-6
(For graph-based modeling of resource allocation and cost in cloud systems)

Sharma, S., & Kumari, R. (2023). Graph-based models for multi-tenant security in cloud computing. International Journal of Cloud Applications and Computing, 13(1), 45–61. https://www.researchgate.net/publication/388394135
(For graph models in cloud multi-tenant environments and isolation)

Khan, R. A., & Abbas, A. (2022). A survey on graph neural networks for microservice-based cloud applications. Sensors, 22(23), 9492. https://doi.org/10.3390/s22239492
(For graph models applied to microservices in cloud systems)

Cloud Deployment Artifacts and Workload Optimization. (2024). Internal Industry Knowledge Document.
(For transdisciplinary heuristic mappings of deployment artifacts based on operational patterns)
