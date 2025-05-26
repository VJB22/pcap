# Libraries to add to github

## Get data

* subprocess
* json
* os
* glob from tqdm.auto import tqdm

## Preprocessing

* hashlib
* ipaddress
* pyarrow as pa
* pyarrow.parquet as pq
* os
* pandas as pd
* duckdb
* numpy as np

## NS graph

* pandas as pd
* networkx as nx


## What is missing

1. **Edge cases or hybrid types** Some real workloads might have mixed signals or uncommon patterns that need nuanced handling beyond these categories.
2. **Additional signals** one could refine with more features like latency patterns, TLS version specifics, or protocol combinations if data supports them.
CODE:

## Bidirectional workloads (src, dst)
### 1. Network Layer (Infrastructure & Traffic Patterns)
* **Switch Detection** Identifies switches by MAC address reuse across multiple IPs (ip_mac_df count > 3). Detects broadcast nodes (ff:ff:ff:ff:ff:ff) and forward-only MAC addresses (MACs appearing only as source, never destination).


* **Router Classification** Uses flow directionality (internal/external) to classify routers as either internal_router or external_router.


* **TTL Variability** High TTL standard deviation flags unstable/ephemeral hosts, often virtual or containerized workloads.


* **Communication Metrics** Fan-in/out counts from unique peer IPs to identify ‘talkative’ workloads or gateways.
Response delays and burstiness to characterize traffic rhythmicity and workload behavior.


### 2. Storage Layer (Heavy Data & Session Characteristics)

* **Data Volume** Aggregates total data transferred per MAC-IP combination, flagging workloads with high data volumes as is_data_intensive.

* **Session Length & Stability** Measures session duration (session_length_src/dst) and session volatility to differentiate stable vs volatile workloads.


* **Compliance Sensitivity** Flags internal-only workloads with long sessions as potentially compliance-sensitive storage or backend systems.

* **Financial Protocol Activity**
