---
displayed_sidebar: docs
---

# 从 Apache Flink® 持续导入数据

StarRocks 提供了一个自主开发的连接器，名为 StarRocks Connector for Apache Flink® (简称为 Flink connector)，以帮助您使用 Flink 将数据导入到 StarRocks 表中。其基本原理是先积累数据，然后通过 [STREAM LOAD](../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md) 将数据一次性导入到 StarRocks 中。

Flink connector 支持 DataStream API、Table API & SQL 和 Python API。与 Apache Flink® 提供的 [flink-connector-jdbc](https://nightlies.apache.org/flink/flink-docs-master/docs/connectors/table/jdbc/) 相比，它具有更高且更稳定的性能。

> **注意**
>
> 使用 Flink connector 将数据导入到 StarRocks 表中，需要对目标 StarRocks 表具有 SELECT 和 INSERT 权限。如果您没有这些权限，请按照 [GRANT](../sql-reference/sql-statements/account-management/GRANT.md) 中提供的说明，将这些权限授予用于连接 StarRocks 集群的用户。

## 版本要求

| Connector | Flink                         | StarRocks     | Java | Scala     |
|-----------|-------------------------------|---------------| ---- |-----------|
| 1.2.11    | 1.15,1.16,1.17,1.18,1.19,1.20 | 2.1 and later | 8    | 2.11,2.12 |
| 1.2.10    | 1.15,1.16,1.17,1.18,1.19      | 2.1 and later | 8    | 2.11,2.12 |
| 1.2.9     | 1.15,1.16,1.17,1.18           | 2.1 and later | 8    | 2.11,2.12 |
| 1.2.8     | 1.13,1.14,1.15,1.16,1.17      | 2.1 and later | 8    | 2.11,2.12 |
| 1.2.7     | 1.11,1.12,1.13,1.14,1.15      | 2.1 and later | 8    | 2.11,2.12 |

## 获取 Flink connector

您可以通过以下方式获取 Flink connector JAR 文件：

- 直接下载已编译的 Flink connector JAR 文件。
- 在您的 Maven 项目中添加 Flink connector 作为依赖项，然后下载 JAR 文件。
- 自己将 Flink connector 的源代码编译为 JAR 文件。

Flink connector JAR 文件的命名格式如下：

- 从 Flink 1.15 开始，命名格式为 `flink-connector-starrocks-${connector_version}_flink-${flink_version}.jar`。例如，如果您安装了 Flink 1.15 并且想要使用 Flink connector 1.2.7，则可以使用 `flink-connector-starrocks-1.2.7_flink-1.15.jar`。

- 在 Flink 1.15 之前，命名格式为 `flink-connector-starrocks-${connector_version}_flink-${flink_version}_${scala_version}.jar`。例如，如果您的环境中安装了 Flink 1.14 和 Scala 2.12，并且想要使用 Flink connector 1.2.7，则可以使用 `flink-connector-starrocks-1.2.7_flink-1.14_2.12.jar`。

> **注意**
>
> 通常，最新版本的 Flink connector 仅保持与 Flink 的三个最新版本的兼容性。

### 下载已编译的 Jar 文件

从 [Maven Central Repository](https://repo1.maven.org/maven2/com/starrocks) 直接下载相应版本的 Flink connector Jar 文件。

### Maven 依赖

在您的 Maven 项目的 `pom.xml` 文件中，按照以下格式添加 Flink connector 作为依赖项。将 `flink_version`、`scala_version` 和 `connector_version` 替换为相应的版本。

- 在 Flink 1.15 及更高版本中

    ```xml
    <dependency>
        <groupId>com.starrocks</groupId>
        <artifactId>flink-connector-starrocks</artifactId>
        <version>${connector_version}_flink-${flink_version}</version>
    </dependency>
    ```

- 在低于 Flink 1.15 的版本中

    ```xml
    <dependency>
        <groupId>com.starrocks</groupId>
        <artifactId>flink-connector-starrocks</artifactId>
        <version>${connector_version}_flink-${flink_version}_${scala_version}</version>
    </dependency>
    ```

### 自行编译

1. 下载 [Flink connector 源代码](https://github.com/StarRocks/starrocks-connector-for-apache-flink)。
2. 执行以下命令，将 Flink connector 的源代码编译为 JAR 文件。请注意，`flink_version` 替换为相应的 Flink 版本。

      ```bash
      sh build.sh <flink_version>
      ```

   例如，如果您的环境中的 Flink 版本为 1.15，则需要执行以下命令：

      ```bash
      sh build.sh 1.15
      ```

3. 进入 `target/` 目录以查找 Flink connector JAR 文件，例如编译后生成的 `flink-connector-starrocks-1.2.7_flink-1.15-SNAPSHOT.jar`。

> **注意**
>
> 非正式发布的 Flink connector 的名称包含 `SNAPSHOT` 后缀。

## Options

### connector

**是否必须**: 是<br/>
**默认值**: NONE<br/>
**描述**: 您要使用的连接器。该值必须为 "starrocks"。

### jdbc-url

**是否必须**: 是<br/>
**默认值**: NONE<br/>
**描述**: 用于连接 FE 的 MySQL 服务器的地址。您可以指定多个地址，这些地址必须用逗号 (,) 分隔。格式：`jdbc:mysql://<fe_host1>:<fe_query_port1>,<fe_host2>:<fe_query_port2>,<fe_host3>:<fe_query_port3>`。

### load-url

**是否必须**: 是<br/>
**默认值**: NONE<br/>
**描述**: 用于连接 FE 的 HTTP 服务器的地址。您可以指定多个地址，这些地址必须用分号 (;) 分隔。格式：`<fe_host1>:<fe_http_port1>;<fe_host2>:<fe_http_port2>`。

### database-name

**是否必须**: 是<br/>
**默认值**: NONE<br/>
**描述**: 您要将数据加载到的 StarRocks 数据库的名称。

### table-name

**是否必须**: 是<br/>
**默认值**: NONE<br/>
**描述**: 您要用于将数据加载到 StarRocks 中的表的名称。

### username

**是否必须**: 是<br/>
**默认值**: NONE<br/>
**描述**: 您要用于将数据加载到 StarRocks 中的帐户的用户名。该帐户需要对目标 StarRocks 表具有 [SELECT 和 INSERT 权限](../sql-reference/sql-statements/account-management/GRANT.md)。

### password

**是否必须**: 是<br/>
**默认值**: NONE<br/>
**描述**: 上述帐户的密码。

### sink.version

**是否必须**: 否<br/>
**默认值**: AUTO<br/>
**描述**: 用于加载数据的接口。从 Flink connector 1.2.4 版本开始支持此参数。<ul><li>`V1`: 使用 [Stream Load](../loading/StreamLoad.md) 接口加载数据。1.2.4 之前的连接器仅支持此模式。</li> <li>`V2`: 使用 [Stream Load 事务](./Stream_Load_transaction_interface.md) 接口加载数据。它要求 StarRocks 至少为 2.4 版本。推荐使用 `V2`，因为它优化了内存使用并提供了更稳定的 exactly-once 实现。</li> <li>`AUTO`: 如果 StarRocks 的版本支持事务 Stream Load，将自动选择 `V2`，否则选择 `V1`。</li></ul>

### sink.label-prefix

**是否必须**: 否<br/>
**默认值**: NONE<br/>
**描述**: Stream Load 使用的标签前缀。如果您正在使用 1.2.8 及更高版本的连接器进行 exactly-once，建议配置此参数。请参阅 [exactly-once 使用说明](#exactly-once)。

### sink.semantic

**是否必须**: 否<br/>
**默认值**: at-least-once<br/>
**描述**: sink 保证的语义。有效值：**at-least-once** 和 **exactly-once**。

### sink.buffer-flush.max-bytes

**是否必须**: 否<br/>
**默认值**: 94371840(90M)<br/>
**描述**: 在一次发送到 StarRocks 之前，可以在内存中累积的最大数据量。最大值范围为 64 MB 到 10 GB。将此参数设置为较大的值可以提高导入性能，但可能会增加导入延迟。此参数仅在 `sink.semantic` 设置为 `at-least-once` 时生效。如果 `sink.semantic` 设置为 `exactly-once`，则在触发 Flink checkpoint 时刷新内存中的数据。在这种情况下，此参数不生效。

### sink.buffer-flush.max-rows

**是否必须**: 否<br/>
**默认值**: 500000<br/>
**描述**: 在一次发送到 StarRocks 之前，可以在内存中累积的最大行数。此参数仅在 `sink.version` 为 `V1` 且 `sink.semantic` 为 `at-least-once` 时可用。有效值：64000 到 5000000。

### sink.buffer-flush.interval-ms

**是否必须**: 否<br/>
**默认值**: 300000<br/>
**描述**: 刷新数据的间隔。此参数仅在 `sink.semantic` 为 `at-least-once` 时可用。有效值：1000 到 3600000。单位：毫秒。

### sink.max-retries

**是否必须**: 否<br/>
**默认值**: 3<br/>
**描述**: 系统重试执行 Stream Load 作业的次数。仅当您将 `sink.version` 设置为 `V1` 时，此参数才可用。有效值：0 到 10。

### sink.connect.timeout-ms

**是否必须**: 否<br/>
**默认值**: 30000<br/>
**描述**: 建立 HTTP 连接的超时时间。有效值：100 到 60000。单位：毫秒。在 Flink connector v1.2.9 之前，默认值为 `1000`。

### sink.socket.timeout-ms

**是否必须**: 否<br/>
**默认值**: -1<br/>
**描述**: 自 1.2.10 起支持。HTTP 客户端等待数据的时间。单位：毫秒。默认值 `-1` 表示没有超时。

### sink.sanitize-error-log

**是否必须**: 否<br/>
**默认值**: false<br/>
**描述**: 自 1.2.12 起支持。是否对生产安全错误日志中的敏感数据进行清理。当此项设置为 `true` 时，连接器和 SDK 日志中的 Stream Load 错误日志中的敏感行数据和列值将被编辑。为了向后兼容，该值默认为 `false`。

### sink.wait-for-continue.timeout-ms

**是否必须**: 否<br/>
**默认值**: 10000<br/>
**描述**: 自 1.2.7 起支持。等待来自 FE 的 HTTP 100-continue 响应的超时时间。有效值：`3000` 到 `60000`。单位：毫秒。

### sink.ignore.update-before

**是否必须**: 否<br/>
**默认值**: true<br/>
**描述**: 自 1.2.8 版本起支持。将数据加载到主键表时，是否忽略来自 Flink 的 `UPDATE_BEFORE` 记录。如果此参数设置为 false，则该记录将被视为对 StarRocks 表的删除操作。

### sink.parallelism

**是否必须**: 否<br/>
**默认值**: NONE<br/>
**描述**: 导入的并行度。仅适用于 Flink SQL。如果未指定此参数，则 Flink planner 决定并行度。**在多并行度的情况下，用户需要保证数据以正确的顺序写入。**

### sink.properties.*

**是否必须**: 否<br/>
**默认值**: NONE<br/>
**描述**: 用于控制 Stream Load 行为的参数。例如，参数 `sink.properties.format` 指定用于 Stream Load 的格式，例如 CSV 或 JSON。有关支持的参数及其描述的列表，请参阅 [STREAM LOAD](../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md)。

### sink.properties.format

**是否必须**: 否<br/>
**默认值**: csv<br/>
**描述**: 用于 Stream Load 的格式。Flink connector 将在将每批数据发送到 StarRocks 之前将其转换为该格式。有效值：`csv` 和 `json`。

### sink.properties.column_separator

**是否必须**: 否<br/>
**默认值**: \t<br/>
**描述**: CSV 格式数据的列分隔符。

### sink.properties.row_delimiter

**是否必须**: 否<br/>
**默认值**: \n<br/>
**描述**: CSV 格式数据的行分隔符。

### sink.properties.max_filter_ratio

**是否必须**: 否<br/>
**默认值**: 0<br/>
**描述**: Stream Load 的最大错误容忍度。它是由于数据质量不足而被过滤掉的数据记录的最大百分比。有效值：`0` 到 `1`。默认值：`0`。有关详细信息，请参阅 [Stream Load](../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md)。

### sink.properties.partial_update

**是否必须**: 否<br/>
**默认值**: `FALSE`<br/>
**描述**: 是否使用部分更新。有效值：`TRUE` 和 `FALSE`。默认值为 `FALSE`，表示禁用此功能。

### sink.properties.partial_update_mode

**是否必须**: 否<br/>
**默认值**: `row`<br/>
**描述**: 指定部分更新的模式。有效值：`row` 和 `column`。<ul><li>值 `row` (默认) 表示行模式下的部分更新，更适合于具有许多列和小批量的实时更新。</li><li>值 `column` 表示列模式下的部分更新，更适合于具有少量列和许多行的批量更新。在这种情况下，启用列模式可以提供更快的更新速度。例如，在一个具有 100 列的表中，如果仅更新所有行的 10 列（总数的 10%），则列模式的更新速度比行模式快 10 倍。</li></ul>

### sink.properties.strict_mode

**是否必须**: 否<br/>
**默认值**: false<br/>
**描述**: 指定是否为 Stream Load 启用严格模式。它会影响存在不合格行（例如，列值不一致）时的加载行为。有效值：`true` 和 `false`。默认值：`false`。有关详细信息，请参阅 [Stream Load](../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md)。

### sink.properties.compression

**是否必须**: 否<br/>
**默认值**: NONE<br/>
**描述**: 用于 Stream Load 的压缩算法。有效值：`lz4_frame`。JSON 格式的压缩需要 Flink connector 1.2.10+ 和 StarRocks v3.2.7+。CSV 格式的压缩仅需要 Flink connector 1.2.11+。

### sink.properties.prepared_timeout

**是否必须**: 否<br/>
**默认值**: NONE<br/>
**描述**: 自 1.2.12 起支持，并且仅在 `sink.version` 设置为 `V2` 时有效。需要 StarRocks 3.5.4 或更高版本。设置从 `PREPARED` 到 `COMMITTED` 的事务 Stream Load 阶段的超时时间（以秒为单位）。通常，仅 exactly-once 需要此设置；at-least-once 通常不需要设置此项（连接器默认为 300 秒）。如果未在 exactly-once 中设置，则应用 StarRocks FE 配置 `prepared_transaction_default_timeout_second`（默认为 86400 秒）。请参阅 [StarRocks 事务超时管理](./Stream_Load_transaction_interface.md#transaction-timeout-management)。

## Flink 和 StarRocks 之间的数据类型映射

| Flink 数据类型                   | StarRocks 数据类型   |
|-----------------------------------|-----------------------|
| BOOLEAN                           | BOOLEAN               |
| TINYINT                           | TINYINT               |
| SMALLINT                          | SMALLINT              |
| INTEGER                           | INTEGER               |
| BIGINT                            | BIGINT                |
| FLOAT                             | FLOAT                 |
| DOUBLE                            | DOUBLE                |
| DECIMAL                           | DECIMAL               |
| BINARY                            | INT                   |
| CHAR                              | STRING                |
| VARCHAR                           | STRING                |
| STRING                            | STRING                |
| DATE                              | DATE                  |
| TIMESTAMP_WITHOUT_TIME_ZONE(N)    | DATETIME              |
| TIMESTAMP_WITH_LOCAL_TIME_ZONE(N) | DATETIME              |
| ARRAY&lt;T&gt;                        | ARRAY&lt;T&gt;              |
| MAP&lt;KT,VT&gt;                        | JSON STRING           |
| ROW&lt;arg T...&gt;                     | JSON STRING           |

## 使用说明

### Exactly Once

- 如果您希望 sink 保证 exactly-once 语义，我们建议您将 StarRocks 升级到 2.5 或更高版本，并将 Flink connector 升级到 1.2.4 或更高版本。
  - 自 Flink connector 1.2.4 起，exactly-once 基于 StarRocks 自 2.4 起提供的 [Stream Load 事务接口](./Stream_Load_transaction_interface.md) 重新设计。与之前基于非事务 Stream Load 接口的实现相比，新实现减少了内存使用和 checkpoint 开销，从而提高了实时性能和加载稳定性。

  - 如果 StarRocks 的版本早于 2.4 或 Flink connector 的版本早于 1.2.4，则 sink 将自动选择基于 Stream Load 非事务接口的实现。

- 保证 exactly-once 的配置

  - `sink.semantic` 的值需要为 `exactly-once`。

  - 如果 Flink connector 的版本为 1.2.8 及更高版本，建议指定 `sink.label-prefix` 的值。请注意，标签前缀在 StarRocks 中的所有类型的加载（例如 Flink 作业、Routine Load 和 Broker Load）中必须是唯一的。

    - 如果指定了标签前缀，Flink connector 将使用该标签前缀来清理在某些 Flink 故障场景中可能生成的长期存在的事务，例如当 checkpoint 仍在进行中时 Flink 作业失败。如果您使用 `SHOW PROC '/transactions/<db_id>/running';` 在 StarRocks 中查看这些长期存在的事务，它们通常处于 `PREPARED` 状态。当 Flink 作业从 checkpoint 恢复时，Flink connector 将根据标签前缀和 checkpoint 中的一些信息找到这些长期存在的事务，并中止它们。由于用于实现 exactly-once 的两阶段提交机制，Flink connector 无法在 Flink 作业退出时中止它们。当 Flink 作业退出时，Flink connector 尚未收到来自 Flink checkpoint 协调器的通知，说明是否应将事务包含在成功的 checkpoint 中，如果无论如何都中止这些事务，可能会导致数据丢失。您可以在此 [博客文章](https://flink.apache.org/2018/02/28/an-overview-of-end-to-end-exactly-once-processing-in-apache-flink-with-apache-kafka-too/) 中大致了解如何在 Flink 中实现端到端 exactly-once。

    - 如果未指定标签前缀，则仅在长期存在的事务超时后，StarRocks 才会清理它们。但是，如果在事务超时之前 Flink 作业频繁失败，则正在运行的事务数可能会达到 StarRocks `max_running_txn_num_per_db` 的限制。您可以为 `PREPARED` 事务设置较小的超时时间，以便在未指定标签前缀时更快地过期。请参阅以下有关如何设置 prepared 超时的信息。

- 如果您确定 Flink 作业在因停止或持续故障转移而长时间停机后最终将从 checkpoint 或 savepoint 恢复，请相应地调整以下 StarRocks 配置，以避免数据丢失。

  - 调整 `PREPARED` 事务超时。请参阅以下有关如何设置超时的信息。

    超时时间需要大于 Flink 作业的停机时间。否则，包含在成功的 checkpoint 中的长期存在的事务可能会因超时而在您重新启动 Flink 作业之前中止，从而导致数据丢失。

    请注意，当您为此配置设置较大的值时，最好指定 `sink.label-prefix` 的值，以便可以根据标签前缀和 checkpoint 中的一些信息清理长期存在的事务，而不是由于超时（这可能会导致数据丢失）。

  - `label_keep_max_second` 和 `label_keep_max_num`：StarRocks FE 配置，默认值分别为 `259200` 和 `1000`。有关详细信息，请参阅 [FE 配置](./loading_introduction/loading_considerations.md#fe-configurations)。`label_keep_max_second` 的值需要大于 Flink 作业的停机时间。否则，Flink connector 无法通过使用保存在 Flink 的 savepoint 或 checkpoint 中的事务标签来检查 StarRocks 中事务的状态，并确定这些事务是否已提交，这最终可能会导致数据丢失。

- 如何设置 PREPARED 事务的超时时间

  - 对于 Connector 1.2.12+ 和 StarRocks 3.5.4+，您可以通过配置连接器参数 `sink.properties.prepared_timeout` 来设置超时时间。默认情况下，该值未设置，并且会回退到 StarRocks FE 的全局配置 `prepared_transaction_default_timeout_second`（默认值为 `86400`）。

  - 对于其他版本的 Connector 或 StarRocks，您可以通过配置 StarRocks FE 的全局配置 `prepared_transaction_default_timeout_second`（默认值为 `86400`）来设置超时时间。

### Flush 策略

Flink connector 将在内存中缓冲数据，并通过 Stream Load 将它们批量刷新到 StarRocks。在 at-least-once 和 exactly-once 之间，触发刷新的方式有所不同。

对于 at-least-once，当满足以下任何条件时，将触发刷新：

- 缓冲行的字节数达到限制 `sink.buffer-flush.max-bytes`
- 缓冲行的数量达到限制 `sink.buffer-flush.max-rows`。（仅对 sink 版本 V1 有效）
- 自上次刷新以来经过的时间达到限制 `sink.buffer-flush.interval-ms`
- 触发 checkpoint

对于 exactly-once，仅当触发 checkpoint 时才会发生刷新。

### 监控导入指标

Flink connector 提供了以下指标来监控导入。

| 指标                     | 类型    | 描述                                                         |
|--------------------------|---------|------------------------------------------------------------|
| totalFlushBytes          | counter | 成功刷新的字节数。                                               |
| totalFlushRows           | counter | 成功刷新的行数。                                                   |
| totalFlushSucceededTimes | counter | 成功刷新数据的次数。                                     |
| totalFlushFailedTimes    | counter | 数据刷新失败的次数。                                         |
| totalFilteredRows        | counter | 过滤的行数，也包含在 totalFlushRows 中。                        |

## 示例

以下示例展示了如何使用 Flink connector 通过 Flink SQL 或 Flink DataStream 将数据加载到 StarRocks 表中。

### 准备工作

#### 创建 StarRocks 表

创建一个数据库 `test` 并创建一个主键表 `score_board`。

```sql
CREATE DATABASE `test`;

CREATE TABLE `test`.`score_board`
(
    `id` int(11) NOT NULL COMMENT "",
    `name` varchar(65533) NULL DEFAULT "" COMMENT "",
    `score` int(11) NOT NULL DEFAULT "0" COMMENT ""
)
ENGINE=OLAP
PRIMARY KEY(`id`)
COMMENT "OLAP"
DISTRIBUTED BY HASH(`id`);
```

#### 设置 Flink 环境

- 下载 Flink 二进制文件 [Flink 1.15.2](https://archive.apache.org/dist/flink/flink-1.15.2/flink-1.15.2-bin-scala_2.12.tgz)，并将其解压缩到目录 `flink-1.15.2`。
- 下载 [Flink connector 1.2.7](https://repo1.maven.org/maven2/com/starrocks/flink-connector-starrocks/1.2.7_flink-1.15/flink-connector-starrocks-1.2.7_flink-1.15.jar)，并将其放入目录 `flink-1.15.2/lib`。
- 运行以下命令以启动 Flink 集群：

    ```shell
    cd flink-1.15.2
    ./bin/start-cluster.sh
    ```

#### 网络配置

确保 Flink 所在的机器可以通过 [`http_port`](../administration/management/FE_configuration.md#http_port)（默认：`8030`）和 [`query_port`](../administration/management/FE_configuration.md#query_port)（默认：`9030`）访问 StarRocks 集群的 FE 节点，并通过 [`be_http_port`](../administration/management/BE_configuration.md#be_http_port)（默认：`8040`）访问 BE 节点。

### 使用 Flink SQL 运行

- 运行以下命令以启动 Flink SQL 客户端。

    ```shell
    ./bin/sql-client.sh
    ```

- 创建一个 Flink 表 `score_board`，并通过 Flink SQL 客户端将值插入到该表中。请注意，如果要将数据加载到 StarRocks 的主键表中，则必须在 Flink DDL 中定义主键。对于其他类型的 StarRocks 表，这是可选的。

    ```SQL
    CREATE TABLE `score_board` (
        `id` INT,
        `name` STRING,
        `score` INT,
        PRIMARY KEY (id) NOT ENFORCED
    ) WITH (
        'connector' = 'starrocks',
        'jdbc-url' = 'jdbc:mysql://127.0.0.1:9030',
        'load-url' = '127.0.0.1:8030',
        'database-name' = 'test',
        
        'table-name' = 'score_board',
        'username' = 'root',
        'password' = ''
    );

    INSERT INTO `score_board` VALUES (1, 'starrocks', 100), (2, 'flink', 100);
    ```

### 使用 Flink DataStream 运行

根据输入记录的类型（例如 CSV Java `String`、JSON Java `String` 或自定义 Java 对象），有几种方法可以实现 Flink DataStream 作业。

- 输入记录是 CSV 格式的 `String`。有关完整示例，请参阅 [LoadCsvRecords](https://github.com/StarRocks/starrocks-connector-for-apache-flink/tree/cd8086cfedc64d5181785bdf5e89a847dc294c1d/examples/src/main/java/com/starrocks/connector/flink/examples/datastream)。

    ```java
    /**
     * Generate CSV-format records. Each record has three values separated by "\t". 
     * These values will be loaded to the columns `id`, `name`, and `score` in the StarRocks table.
     */
    String[] records = new String[]{
            "1\tstarrocks-csv\t100",
            "2\tflink-csv\t100"
    };
    DataStream<String> source = env.fromElements(records);

    /**
     * Configure the connector with the required properties.
     * You also need to add properties "sink.properties.format" and "sink.properties.column_separator"
     * to tell the connector the input records are CSV-format, and the column separator is "\t".
     * You can also use other column separators in the CSV-format records,
     * but remember to modify the "sink.properties.column_separator" correspondingly.
     */
    StarRocksSinkOptions options = StarRocksSinkOptions.builder()
            .withProperty("jdbc-url", jdbcUrl)
            .withProperty("load-url", loadUrl)
            .withProperty("database-name", "test")
            .withProperty("table-name", "score_board")
            .withProperty("username", "root")
            .withProperty("password", "")
            .withProperty("sink.properties.format", "csv")
            .withProperty("sink.properties.column_separator", "\t")
            .build();
    // Create the sink with the options.
    SinkFunction<String> starRockSink = StarRocksSink.sink(options);
    source.addSink(starRockSink);
    ```

- 输入记录是 JSON 格式的 `String`。有关完整示例，请参阅 [LoadJsonRecords](https://github.com/StarRocks/starrocks-connector-for-apache-flink/tree/cd8086cfedc64d5181785bdf5e89a847dc294c1d/examples/src/main/java/com/starrocks/connector/flink/examples/datastream)。

    ```java
    /**
     * Generate JSON-format records. 
     * Each record has three key-value pairs corresponding to the columns `id`, `name`, and `score` in the StarRocks table.
     */
    String[] records = new String[]{
            "{\"id\":1, \"name\":\"starrocks-json\", \"score\":100}",
            "{\"id\":2, \"name\":\"flink-json\", \"score\":100}",
    };
    DataStream<String> source = env.fromElements(records);

    /** 
     * Configure the connector with the required properties.
     * You also need to add properties "sink.properties.format" and "sink.properties.strip_outer_array"
     * to tell the connector the input records are JSON-format and to strip the outermost array structure. 
     */
    StarRocksSinkOptions options = StarRocksSinkOptions.builder()
            .withProperty("jdbc-url", jdbcUrl)
            .withProperty("load-url", loadUrl)
            .withProperty("database-name", "test")
            .withProperty("table-name", "score_board")
            .withProperty("username", "root")
            .withProperty("password", "")
            .withProperty("sink.properties.format", "json")
            .withProperty("sink.properties.strip_outer_array", "true")
            .build();
    // Create the sink with the options.
    SinkFunction<String> starRockSink = StarRocksSink.sink(options);
    source.addSink(starRockSink);
    ```

- 输入记录是自定义 Java 对象。有关完整示例，请参阅 [LoadCustomJavaRecords](https://github.com/StarRocks/starrocks-connector-for-apache-flink/tree/cd8086cfedc64d5181785bdf5e89a847dc294c1d/examples/src/main/java/com/starrocks/connector/flink/examples/datastream)。

  - 在此示例中，输入记录是一个简单的 POJO `RowData`。

      ```java
      public static class RowData {
              public int id;
              public String name;
              public int score;
    
              public RowData() {}
    
              public RowData(int id, String name, int score) {
                  this.id = id;
                  this.name = name;
                  this.score = score;
              }
        }
      ```

  - 主程序如下：

    ```java
    // Generate records which use RowData as the container.
    RowData[] records = new RowData[]{
            new RowData(1, "starrocks-rowdata", 100),
            new RowData(2, "flink-rowdata", 100),
        };
    DataStream<RowData> source = env.fromElements(records);

    // Configure the connector with the required properties.
    StarRocksSinkOptions options = StarRocksSinkOptions.builder()
            .withProperty("jdbc-url", jdbcUrl)
            .withProperty("load-url", loadUrl)
            .withProperty("database-name", "test")
            .withProperty("table-name", "score_board")
            .withProperty("username", "root")
            .withProperty("password", "")
            .build();

    /**
     * The Flink connector will use a Java object array (Object[]) to represent a row to be loaded into the StarRocks table,
     * and each element is the value for a column.
     * You need to define the schema of the Object[] which matches that of the StarRocks table.
     */
    TableSchema schema = TableSchema.builder()
            .field("id", DataTypes.INT().notNull())
            .field("name", DataTypes.STRING())
            .field("score", DataTypes.INT())
            // When the StarRocks table is a Primary Key table, you must specify notNull(), for example, DataTypes.INT().notNull(), for the primary key `id`.
            .primaryKey("id")
            .build();
    // Transform the RowData to the Object[] according to the schema.
    RowDataTransformer transformer = new RowDataTransformer();
    // Create the sink with the schema, options, and transformer.
    SinkFunction<RowData> starRockSink = StarRocksSink.sink(schema, options, transformer);
    source.addSink(starRockSink);
    ```

  - 主程序中的 `RowDataTransformer` 定义如下：

    ```java
    private static class RowDataTransformer implements StarRocksSinkRowBuilder<RowData> {
    
        /**
         * Set each element of the object array according to the input RowData.
         * The schema of the array matches that of the StarRocks table.
         */
        @Override
        public void accept(Object[] internalRow, RowData rowData) {
            internalRow[0] = rowData.id;
            internalRow[1] = rowData.name;
            internalRow[2] = rowData.score;
            // When the StarRocks table is a Primary Key table, you need to set the last element to indicate whether