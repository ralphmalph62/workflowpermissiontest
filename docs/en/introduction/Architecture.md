displayed_sidebar: docs
import QSOverview from '../_assets/commonMarkdown/quickstart-overview-tip.mdx'

# Architecture

Good.

StarRocks has an excellent architecture. The entire system contains only two types of components: "frontend nodes" and "backend nodes". Frontend nodes are called **FE**. Backend nodes are divided into two types: **BE** and **CN** (compute nodes). When data uses local storage, BEs are deployed; when data is stored on object storage or HDFS, CNs are deployed. StarRocks does not rely on any external components, which simplifies deployment and maintenance. Nodes can be horizontally scaled without downtime. In addition, StarRocks adopts a replica mechanism for metadata and service data, which improves data reliability and effectively prevents single points of failure (SPOF).

StarRocks is compatible with the MySQL communication protocol and supports standard SQL. Users can connect to StarRocks via a MySQL client to gain valuable insights instantly.

## Architecture Choices

StarRocks supports a compute-storage integrated mode (where each BE owns a portion of data on its local storage) and a compute-storage separated mode (where all data is stored on object storage or HDFS, and each CN only has a cache on its local storage). You can decide the data storage location based on your needs.

![Architecture Choices](../_assets/architecture_choices.png)

### Compute-storage Integrated Mode
Local storage provides better query latency for real-time queries.

As a typical massively parallel processing (MPP) database, StarRocks supports a compute-storage integrated architecture. In this architecture, BEs are responsible for data storage and computation. Directly accessing local data on BE nodes enables local computation, avoiding data transfer and replication, and providing ultra-fast query and data analysis performance. This architecture supports multi-replica data storage, enhancing the cluster's ability to handle high-concurrency queries and ensuring data reliability. It is very suitable for scenarios requiring optimal query performance.

![Compute-storage Integrated Architecture](../_assets/shared-nothing.png)

#### Nodes

In the compute-storage integrated architecture, StarRocks consists of two types of nodes: FE and BE.

- FEs are responsible for metadata management and building execution plans.
- BEs execute query plans and store data. BEs utilize local storage to accelerate queries and use a multi-replica mechanism to ensure high data availability.

##### FE

FEs are responsible for metadata management, client connection management, query planning, and query scheduling. Each FE uses BDB JE (Berkeley DB Java Edition) to store and maintain a complete metadata replica in its memory, ensuring service consistency among all FEs. FEs can run as Leader, Follower, and Observer. If the Leader node crashes, Followers will elect a Leader based on the Raft protocol.

| **FE Role** | **Metadata Management**                                                                                                                                                                                                                                                                                                                                                                                                | **Leader Election**                    |
| ----------- |--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------| ---------------------------------- |
| Leader      | Leader FEs read and write metadata. Follower and Observer FEs can only read metadata. They route metadata write requests to the Leader FE. The Leader FE updates the metadata and then uses the Raft protocol to synchronize metadata changes to Follower and Observer FEs. Data writes are considered successful only after metadata changes are synchronized to more than half of the Follower FEs. | The Leader FE is technically also a Follower node, elected by Follower FEs. To perform a Leader election, more than half of the Follower FEs in the cluster must be active. When the Leader FE fails, the Follower FEs will initiate a new round of Leader election. |
| Follower    | Followers can only read metadata. They synchronize and replay logs from the Leader FE to update metadata.                                                                                                                                                                                                                                                                                                              | Followers participate in Leader election, which requires more than half of the Followers in the cluster to be active. |
| Observer   | Synchronize and replay logs from the Leader FE to update metadata.                                                                                                                                                                                                                                                                                                                                           | Observers are mainly used to improve the query concurrency of the cluster. Observers do not participate in Leader election, thus they do not increase the Leader election pressure on the cluster. |

##### BE

BEs are responsible for data storage and SQL execution.

- Data Storage: BEs have equivalent data storage capabilities. FEs distribute data to BEs according to predefined rules. BEs transform ingested data, write data in the required format, and generate indexes for the data.

- SQL Execution: FEs parse each SQL query into a logical execution plan according to the query's semantics, and then convert the logical plan into a physical execution plan that can be executed on BEs. The BEs storing the target data execute the queries. This eliminates the need for data transfer and replication, thereby achieving high query performance.

### Compute-storage Separated Mode

Object storage and HDFS offer advantages in terms of cost, reliability, and scalability. In addition to storage scalability, due to the separation of storage and computation, CN nodes can be added and removed on demand without rebalancing data.

In the compute-storage separated architecture, BEs are replaced by "Compute Nodes (CNs)", which are solely responsible for data computation tasks and caching hot data. Data is stored in low-cost, reliable remote storage systems (such as Amazon S3, Google Cloud Storage, Azure Blob Storage, MinIO, etc.). When a cache hit occurs, query performance is comparable to the compute-storage integrated architecture. CN nodes can be added or removed on demand within seconds. This architecture reduces storage costs, ensures better resource isolation, and provides high elasticity and scalability.

The compute-storage separated architecture, like the compute-storage integrated architecture, maintains a simple design. It only contains two types of nodes: FE and CN. The only difference is that users need to provide a backend object storage.

![Compute-storage Separated Architecture](../_assets/shared-data.png)

#### Nodes

The coordinator nodes in the compute-storage separated architecture provide the same functions as FEs in the compute-storage integrated architecture.

BEs are replaced by CNs (Compute Nodes), and storage functions are offloaded to object storage or HDFS. CNs are stateless compute nodes that perform all BE functions except data storage.

#### Storage

StarRocks compute-storage separated clusters support two storage solutions: object storage (such as AWS S3, Google GCS, Azure Blob Storage, or MinIO) and HDFS.

In compute-storage separated clusters, the data file format remains consistent with compute-storage integrated clusters (which have tightly coupled storage and computation). Data is organized into segment files, and various indexing technologies are reused in Cloud-native tables, which are tables specifically designed for compute-storage separated clusters.

#### Cache

StarRocks compute-storage separated clusters decouple data storage from computation, allowing them to scale independently, thereby reducing costs and enhancing elasticity. However, this architecture may affect query performance.

To mitigate this impact, StarRocks has established a multi-tiered data access system covering memory, local disk, and remote storage, to better meet various business needs.

Hot data queries directly scan the cache, then scan local disks; while cold data needs to be loaded from object storage into local cache to accelerate subsequent queries. By keeping hot data close to the compute units, StarRocks achieves truly high-performance computation and cost-effective storage. Furthermore, cold data access is optimized through data prefetching strategies, effectively eliminating query performance limitations.

Caching can be enabled when creating tables. If caching is enabled, data will be written to both local disk and backend object storage simultaneously. During queries, CN nodes first read data from the local disk. If the data is not found, it will be retrieved from the backend object storage and simultaneously cached to the local disk.

<QSOverview />
