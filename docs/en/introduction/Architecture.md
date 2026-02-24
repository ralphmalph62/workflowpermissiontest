displayed_sidebar: docs
import QSOverview from '../_assets/commonMarkdown/quickstart-overview-tip.mdx'

# Architecture

StarRocks has a wonderful architecture. The entire system consists of only two types of components: "frontends" and "backends". Frontend nodes are called **FE**. Backend nodes are divided into two types: **BE** and **CN** (compute node). When data uses local storage, BEs are deployed; when data is stored on object storage or HDFS, CNs are deployed. StarRocks does not rely on any external components, which simplifies deployment and maintenance. Nodes can be scaled horizontally without downtime. In addition, StarRocks has a replica mechanism for metadata and service data, which improves data reliability and effectively prevents single points of failure (SPOFs).

StarRocks is compatible with the MySQL communication protocol and supports standard SQL. Users can connect to StarRocks via a MySQL client to gain instant and valuable insights.

## Architecture Choices

StarRocks supports the shared-nothing mode (where each BE owns a portion of the data on its local storage) and the shared-data mode (where all data is stored on object storage or HDFS, and each CN only has a cache on its local storage). You can decide where to store your data based on your needs.

![架构选择](../_assets/architecture_choices.png)

### Shared-nothing Mode
Local storage provides better query latency for real-time queries.

As a typical Massively Parallel Processing (MPP) database, StarRocks supports the shared-nothing architecture. In this architecture, BEs are responsible for data storage and compute. Directly accessing local data on BE nodes enables local compute, avoiding data transfer and data copying, and providing ultra-fast query and data analytics performance. This architecture supports multi-replica data storage, enhancing the cluster's ability to handle high-concurrency queries and ensuring data reliability. It is ideal for scenarios that require optimal query performance.

![存算一体架构](../_assets/shared-nothing.png)

#### Nodes


In the shared-nothing architecture, StarRocks consists of two types of nodes: FE and BE.

- FE is responsible for metadata management and building execution plans.
- BE executes query plans and stores data. BEs leverage local storage to accelerate queries and use a multi-replica mechanism to ensure data high availability.

##### FE

FE is responsible for metadata management, client connection management, query planning, and query scheduling. Each FE uses BDB JE (Berkeley DB Java Edition) to store and maintain a complete replica of metadata in its memory, ensuring service consistency among all FEs. FEs can operate as Leader, Follower, and Observer. If the Leader node crashes, Followers will elect a Leader based on the Raft protocol.

| **FE Role** | **Metadata Management**                                                                                                                                                                                                                                                                                                                                                                                                | **Leader Election**                |
| ----------- |--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------| ---------------------------------- |
| Leader      | The Leader FE reads and writes metadata. Follower and Observer FEs can only read metadata. They route metadata write requests to the Leader FE. The Leader FE updates metadata, then uses the Raft protocol to synchronize metadata changes to Follower and Observer FEs. Data writes are considered successful only after metadata changes are synchronized to more than half of the Follower FEs. | The Leader FE is, technically, also a Follower node, elected by Follower FEs. To perform Leader election, more than half of the Follower FEs in the cluster must be active. When the Leader FE fails, Follower FEs will initiate a new round of Leader election. |
| Follower    | Followers can only read metadata. They synchronize and replay logs from the Leader FE to update metadata.                                                                                                                                                                                                                                                                                                              | Followers participate in Leader election, which requires more than half of the Followers in the cluster to be active. |
| Observer   | Synchronizes and replays logs from the Leader FE to update metadata.                                                                                                                                                                                                                                                                                                                                           | Observers are mainly used to improve the query concurrency of the cluster. Observers do not participate in Leader election and therefore do not increase the Leader election pressure on the cluster. |

##### BE

BEs are responsible for data storage and SQL execution.

- Data Storage: BEs have equivalent data storage capabilities. FE distributes data to BEs according to predefined rules. BEs transform ingested data, write data in the required format, and generate indexes for the data.

- SQL Execution: FE parses each SQL query into a logical execution plan based on the query's semantics, and then converts the logical plan into a physical execution plan that can be executed on BEs. The BEs storing the target data execute the query. This eliminates the need for data transfer and copying, thereby achieving high query performance.

### Shared-data Mode

Object storage and HDFS offer advantages in terms of cost, reliability, and scalability. In addition to storage scalability, due to the separation of storage and compute, CN nodes can be added and removed on demand without re-balancing data.

In the shared-data architecture, BEs are replaced by "compute nodes (CNs)", which are only responsible for data compute tasks and caching hot data. Data is stored in low-cost, reliable remote storage systems, such as Amazon S3, Google Cloud Storage, Azure Blob Storage, MinIO, etc. When the cache hits, query performance is comparable to the shared-nothing architecture. CN nodes can be added or removed on demand within seconds. This architecture reduces storage costs, ensures better resource isolation, and offers high elasticity and scalability.

The shared-data architecture, like the shared-nothing architecture, maintains a simple design. It consists of only two types of nodes: FE and CN. The only difference is that users need to provision a backend object storage.

![存算分离架构](../_assets/shared-data.png)

#### Nodes

The coordinator nodes in a shared-data architecture provide the same functionality as the FEs in a shared-nothing architecture.

BEs are replaced by CNs (compute nodes), and storage functionality is offloaded to object storage or HDFS. CNs are stateless compute nodes that perform all BE functions except data storage.

#### Storage

StarRocks shared-data clusters support two storage solutions: object storage (such as AWS S3, Google GCS, Azure Blob Storage, or MinIO) and HDFS.

In shared-data clusters, the data file format remains consistent with shared-nothing clusters (which feature coupled storage and compute). Data is organized into segment files, and various indexing technologies are reused in Cloud-native tables, which are tables specifically used in shared-data clusters.

#### Cache

StarRocks shared-data clusters decouple data storage and compute, allowing them to scale independently, thereby reducing costs and enhancing elasticity. However, this architecture may affect query performance.

To mitigate the impact, StarRocks has established a multi-tiered data access system covering memory, local disk, and remote storage to better meet various business needs.

Hot data queries directly scan the cache, then scan the local disk; while cold data needs to be loaded from object storage into the local cache to accelerate subsequent queries. By keeping hot data close to the compute unit, StarRocks achieves truly high-performance compute and cost-effective storage. In addition, cold data access has been optimized through data prefetching strategies, effectively eliminating query performance limitations.

Caching can be enabled when creating a table. If caching is enabled, data will be written simultaneously to both local disk and the backend object storage. During queries, CN nodes first read data from the local disk. If data is not found, it will be retrieved from the backend object storage and simultaneously cached to the local disk.

<QSOverview />
