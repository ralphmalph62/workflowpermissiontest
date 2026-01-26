---
displayed_sidebar: docs
---

# 使用 Kafka connector 导入数据

StarRocks 提供了一个自研的 connector，名为 Apache Kafka® connector (StarRocks Connector for Apache Kafka®，简称 Kafka connector)。作为一个 sink connector，它可以持续地从 Kafka 消费消息，并将消息导入到 StarRocks 中。 Kafka connector 保证至少一次 (at-least-once) 的语义。

Kafka connector 可以无缝集成到 Kafka Connect 中，这使得 StarRocks 能够更好地与 Kafka 生态系统集成。如果您想将实时数据导入到 StarRocks 中，这是一个明智的选择。与 Routine Load 相比，建议在以下场景中使用 Kafka connector：

- Routine Load 仅支持导入 CSV、JSON 和 Avro 格式的数据，而 Kafka connector 可以导入更多格式的数据，例如 Protobuf。只要可以使用 Kafka Connect 的转换器将数据转换为 JSON 和 CSV 格式，就可以通过 Kafka connector 将数据导入到 StarRocks 中。
- 自定义数据转换，例如 Debezium 格式的 CDC 数据。
- 从多个 Kafka topic 导入数据。
- 从 Confluent Cloud 导入数据。
- 需要更精细地控制导入的批次大小、并行度和其他参数，以在导入速度和资源利用率之间取得平衡。

## 准备工作

### 版本要求

| Connector | Kafka     | StarRocks     | Java |
| --------- | --------- | ------------- | ---- |
| 1.0.6     | 3.4+/4.0+ | 2.5 及更高版本 | 8    |
| 1.0.5     | 3.4       | 2.5 及更高版本 | 8    |
| 1.0.4     | 3.4       | 2.5 及更高版本 | 8    |
| 1.0.3     | 3.4       | 2.5 及更高版本 | 8    |

### 搭建 Kafka 环境

支持自管理的 Apache Kafka 集群和 Confluent Cloud。

- 对于自管理的 Apache Kafka 集群，您可以参考 [Apache Kafka quickstart](https://kafka.apache.org/quickstart) 快速部署 Kafka 集群。 Kafka Connect 已经集成到 Kafka 中。
- 对于 Confluent Cloud，请确保您拥有 Confluent 帐户并已创建集群。

### 下载 Kafka connector

将 Kafka connector 提交到 Kafka Connect：

- 自管理的 Kafka 集群：

  下载 [starrocks-connector-for-kafka-x.y.z-with-dependencies.jar](https://github.com/StarRocks/starrocks-connector-for-kafka/releases)。

- Confluent Cloud：

  目前， Kafka connector 尚未上传到 Confluent Hub。您需要下载 [starrocks-connector-for-kafka-x.y.z-with-dependencies.jar](https://github.com/StarRocks/starrocks-connector-for-kafka/releases)，将其打包成 ZIP 文件，然后将 ZIP 文件上传到 Confluent Cloud。

### 网络配置

确保 Kafka 所在的机器可以通过 [`http_port`](../administration/management/FE_configuration.md#http_port) (默认值：`8030`) 和 [`query_port`](../administration/management/FE_configuration.md#query_port) (默认值：`9030`) 访问 StarRocks 集群的 FE 节点，并通过 [`be_http_port`](../administration/management/BE_configuration.md#be_http_port) (默认值：`8040`) 访问 BE 节点。

## 使用方法

本节以自管理的 Kafka 集群为例，介绍如何配置 Kafka connector 和 Kafka Connect，然后运行 Kafka Connect 将数据导入到 StarRocks 中。

### 准备数据集

假设 Kafka 集群的 topic `test` 中存在 JSON 格式的数据。

```JSON
{"id":1,"city":"New York"}
{"id":2,"city":"Los Angeles"}
{"id":3,"city":"Chicago"}
```

### 创建表

根据 JSON 格式数据的键，在 StarRocks 集群的数据库 `example_db` 中创建表 `test_tbl`。

```SQL
CREATE DATABASE example_db;
USE example_db;
CREATE TABLE test_tbl (id INT, city STRING);
```

### 配置 Kafka connector 和 Kafka Connect，然后运行 Kafka Connect 导入数据

#### 在独立模式下运行 Kafka Connect

1. 配置 Kafka connector。在 Kafka 安装目录下的 **config** 目录中，为 Kafka connector 创建配置文件 **connect-StarRocks-sink.properties**，并配置以下参数。有关更多参数和说明，请参见 [参数](#参数)。

    :::info

    - 在本示例中，StarRocks 提供的 Kafka connector 是一个 sink connector，可以持续地从 Kafka 消费数据，并将数据导入到 StarRocks 中。
    - 如果源数据是 CDC 数据，例如 Debezium 格式的数据，并且 StarRocks 表是 Primary Key 表，则还需要在 StarRocks 提供的 Kafka connector 的配置文件 **connect-StarRocks-sink.properties** 中[配置 `transform`](#load-debezium-formatted-cdc-data)，以将源数据的更改同步到 Primary Key 表。

    :::

    ```yaml
    name=starrocks-kafka-connector
    connector.class=com.starrocks.connector.kafka.StarRocksSinkConnector
    topics=test
    key.converter=org.apache.kafka.connect.json.JsonConverter
    value.converter=org.apache.kafka.connect.json.JsonConverter
    key.converter.schemas.enable=true
    value.converter.schemas.enable=false
    # StarRocks 集群中 FE 的 HTTP URL。默认端口为 8030。
    starrocks.http.url=192.168.xxx.xxx:8030
    # 如果 Kafka topic 名称与 StarRocks 表名不同，则需要配置它们之间的映射关系。
    starrocks.topic2table.map=test:test_tbl
    # 输入 StarRocks 用户名。
    starrocks.username=user1
    # 输入 StarRocks 密码。
    starrocks.password=123456
    starrocks.database.name=example_db
    sink.properties.strip_outer_array=true
    ```

2. 配置并运行 Kafka Connect。

   1. 配置 Kafka Connect。在 **config** 目录下的配置文件 **config/connect-standalone.properties** 中，配置以下参数。有关更多参数和说明，请参见 [Running Kafka Connect](https://kafka.apache.org/documentation.html#connect_running)。

        ```yaml
        # Kafka brokers 的地址。多个 Kafka brokers 的地址需要用逗号 (,) 分隔。
        # 请注意，本示例使用 PLAINTEXT 作为访问 Kafka 集群的安全协议。如果您使用其他安全协议访问 Kafka 集群，则需要在本文件中配置相关信息。
        bootstrap.servers=<kafka_broker_ip>:9092
        offset.storage.file.filename=/tmp/connect.offsets
        offset.flush.interval.ms=10000
        key.converter=org.apache.kafka.connect.json.JsonConverter
        value.converter=org.apache.kafka.connect.json.JsonConverter
        key.converter.schemas.enable=true
        value.converter.schemas.enable=false
        # starrocks-connector-for-kafka-x.y.z-with-dependencies.jar 的绝对路径。
        plugin.path=/home/kafka-connect/starrocks-kafka-connector
        ```

   2. 运行 Kafka Connect。

        ```Bash
        CLASSPATH=/home/kafka-connect/starrocks-kafka-connector/* bin/connect-standalone.sh config/connect-standalone.properties config/connect-starrocks-sink.properties
        ```

#### 在分布式模式下运行 Kafka Connect

1. 配置并运行 Kafka Connect。

    1. 配置 Kafka Connect。在 **config** 目录下的配置文件 `config/connect-distributed.properties` 中，配置以下参数。有关更多参数和说明，请参考 [Running Kafka Connect](https://kafka.apache.org/documentation.html#connect_running)。

        ```yaml
        # Kafka brokers 的地址。多个 Kafka brokers 的地址需要用逗号 (,) 分隔。
        # 请注意，本示例使用 PLAINTEXT 作为访问 Kafka 集群的安全协议。
        # 如果您使用其他安全协议访问 Kafka 集群，请在本文件中配置相关信息。
        bootstrap.servers=<kafka_broker_ip>:9092
        offset.storage.file.filename=/tmp/connect.offsets
        offset.flush.interval.ms=10000
        key.converter=org.apache.kafka.connect.json.JsonConverter
        value.converter=org.apache.kafka.connect.json.JsonConverter
        key.converter.schemas.enable=true
        value.converter.schemas.enable=false
        # starrocks-connector-for-kafka-x.y.z-with-dependencies.jar 的绝对路径。
        plugin.path=/home/kafka-connect/starrocks-kafka-connector
        ```

    2. 运行 Kafka Connect。

        ```BASH
        CLASSPATH=/home/kafka-connect/starrocks-kafka-connector/* bin/connect-distributed.sh config/connect-distributed.properties
        ```

2. 配置并创建 Kafka connector。请注意，在分布式模式下，您需要通过 REST API 配置和创建 Kafka connector。有关参数和说明，请参见 [参数](#参数)。

    :::info

    - 在本示例中，StarRocks 提供的 Kafka connector 是一个 sink connector，可以持续地从 Kafka 消费数据，并将数据导入到 StarRocks 中。
    - 如果源数据是 CDC 数据，例如 Debezium 格式的数据，并且 StarRocks 表是 Primary Key 表，则还需要在 StarRocks 提供的 Kafka connector 的配置文件 **connect-StarRocks-sink.properties** 中[配置 `transform`](#load-debezium-formatted-cdc-data)，以将源数据的更改同步到 Primary Key 表。

    :::

      ```Shell
      curl -i http://127.0.0.1:8083/connectors -H "Content-Type: application/json" -X POST -d '{
        "name":"starrocks-kafka-connector",
        "config":{
          "connector.class":"com.starrocks.connector.kafka.StarRocksSinkConnector",
          "topics":"test",
          "key.converter":"org.apache.kafka.connect.json.JsonConverter",
          "value.converter":"org.apache.kafka.connect.json.JsonConverter",
          "key.converter.schemas.enable":"true",
          "value.converter.schemas.enable":"false",
          "starrocks.http.url":"192.168.xxx.xxx:8030",
          "starrocks.topic2table.map":"test:test_tbl",
          "starrocks.username":"user1",
          "starrocks.password":"123456",
          "starrocks.database.name":"example_db",
          "sink.properties.strip_outer_array":"true"
        }
      }'
      ```

#### 查询 StarRocks 表

查询目标 StarRocks 表 `test_tbl`。

```mysql
MySQL [example_db]> select * from test_tbl;

+------+-------------+
| id   | city        |
+------+-------------+
|    1 | New York    |
|    2 | Los Angeles |
|    3 | Chicago     |
+------+-------------+
3 rows in set (0.01 sec)
```

如果返回以上结果，则表示数据已成功导入。

## 参数

### name

**是否必须**：是<br/>
**默认值**：<br/>
**描述**：此 Kafka connector 的名称。在 Kafka Connect 集群中的所有 Kafka connector 中，它必须是全局唯一的。例如，starrocks-kafka-connector。

### connector.class

**是否必须**：是<br/>
**默认值**：<br/>
**描述**：此 Kafka connector 的 sink 使用的类。将值设置为 `com.starrocks.connector.kafka.StarRocksSinkConnector`。

### topics

**是否必须**：<br/>
**默认值**：<br/>
**描述**：要订阅的一个或多个 topic，其中每个 topic 对应一个 StarRocks 表。默认情况下，StarRocks 假定 topic 名称与 StarRocks 表的名称匹配。因此，StarRocks 通过使用 topic 名称来确定目标 StarRocks 表。请选择填写 `topics` 或 `topics.regex` (如下)，但不能同时填写。但是，如果 StarRocks 表名与 topic 名称不同，则可以使用可选的 `starrocks.topic2table.map` 参数 (如下) 来指定从 topic 名称到表名称的映射。

### topics.regex

**是否必须**：<br/>
**默认值**：
**描述**：用于匹配要订阅的一个或多个 topic 的正则表达式。有关更多描述，请参见 `topics`。请选择填写 `topics.regex` 或 `topics` (如上)，但不能同时填写。<br/>

### starrocks.topic2table.map

**是否必须**：否<br/>
**默认值**：<br/>
**描述**：当 topic 名称与 StarRocks 表名不同时，StarRocks 表名与 topic 名称的映射。格式为 `<topic-1>:<table-1>,<topic-2>:<table-2>,...`。

### starrocks.http.url

**是否必须**：是<br/>
**默认值**：<br/>
**描述**：StarRocks 集群中 FE 的 HTTP URL。格式为 `<fe_host1>:<fe_http_port1>,<fe_host2>:<fe_http_port2>,...`。多个地址用逗号 (,) 分隔。例如，`192.168.xxx.xxx:8030,192.168.xxx.xxx:8030`。

### starrocks.database.name

**是否必须**：是<br/>
**默认值**：<br/>
**描述**：StarRocks 数据库的名称。

### starrocks.username

**是否必须**：是<br/>
**默认值**：<br/>
**描述**：您的 StarRocks 集群帐户的用户名。该用户需要对 StarRocks 表具有 [INSERT](../sql-reference/sql-statements/account-management/GRANT.md) 权限。

### starrocks.password

**是否必须**：是<br/>
**默认值**：<br/>
**描述**：您的 StarRocks 集群帐户的密码。

### key.converter

**是否必须**：否<br/>
**默认值**：Kafka Connect 集群使用的 Key converter<br/>
**描述**：此参数指定 sink connector (Kafka-connector-starrocks) 的 key converter，用于反序列化 Kafka 数据的键。默认的 key converter 是 Kafka Connect 集群使用的 key converter。

### value.converter

**是否必须**：否<br/>
**默认值**：Kafka Connect 集群使用的 Value converter<br/>
**描述**：此参数指定 sink connector (Kafka-connector-starrocks) 的 value converter，用于反序列化 Kafka 数据的值。默认的 value converter 是 Kafka Connect 集群使用的 value converter。

### key.converter.schema.registry.url

**是否必须**：否<br/>
**默认值**：<br/>
**描述**：Key converter 的 Schema registry URL。

### value.converter.schema.registry.url

**是否必须**：否<br/>
**默认值**：<br/>
**描述**：Value converter 的 Schema registry URL。

### tasks.max

**是否必须**：否<br/>
**默认值**：1<br/>
**描述**：Kafka connector 可以创建的任务线程数的上限，通常与 Kafka Connect 集群中 worker 节点上的 CPU 核心数相同。您可以调整此参数以控制导入性能。

### bufferflush.maxbytes

**是否必须**：否<br/>
**默认值**：94371840(90M)<br/>
**描述**：在一次发送到 StarRocks 之前，可以在内存中累积的最大数据量。最大值范围为 64 MB 到 10 GB。请记住，Stream Load SDK 缓冲区可能会创建多个 Stream Load 作业来缓冲数据。因此，此处提到的阈值是指总数据大小。

### bufferflush.intervalms

**是否必须**：否<br/>
**默认值**：1000<br/>
**描述**：发送一批数据的间隔，用于控制导入延迟。范围：[1000, 3600000]。

### connect.timeoutms

**是否必须**：否<br/>
**默认值**：1000<br/>
**描述**：连接到 HTTP URL 的超时时间。范围：[100, 60000]。

### sink.properties.*

**是否必须**：<br/>
**默认值**：<br/>
**描述**：用于控制导入行为的 Stream Load 参数。例如，参数 `sink.properties.format` 指定用于 Stream Load 的格式，例如 CSV 或 JSON。有关支持的参数及其描述的列表，请参见 [STREAM LOAD](../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md)。

### sink.properties.format

**是否必须**：否<br/>
**默认值**：json<br/>
**描述**：用于 Stream Load 的格式。Kafka connector 会在将每批数据发送到 StarRocks 之前将其转换为该格式。有效值：`csv` 和 `json`。有关更多信息，请参见 [CSV 参数](../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md#csv-parameters) 和 [JSON 参数](../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md#json-parameters)。

### sink.properties.partial_update

**是否必须**：否<br/>
**默认值**：`FALSE`<br/>
**描述**：是否使用部分更新。有效值：`TRUE` 和 `FALSE`。默认值：`FALSE`，表示禁用此功能。

### sink.properties.partial_update_mode

**是否必须**：否<br/>
**默认值**：`row`<br/>
**描述**：指定部分更新的模式。有效值：`row` 和 `column`。<ul><li>值 `row` (默认) 表示行模式下的部分更新，更适合于具有许多列和小批量的实时更新。</li><li>值 `column` 表示列模式下的部分更新，更适合于具有少量列和许多行的批量更新。在这种情况下，启用列模式可以提供更快的更新速度。例如，在一个具有 100 列的表中，如果仅更新所有行的 10 列 (占总数的 10%)，则列模式的更新速度将快 10 倍。</li></ul>

## 使用注意事项

### Flush 策略

Kafka connector 会将数据缓存在内存中，并通过 Stream Load 将它们批量刷新到 StarRocks。当满足以下任何条件时，将触发刷新：

- 缓冲行的字节数达到限制 `bufferflush.maxbytes`。
- 自上次刷新以来经过的时间达到限制 `bufferflush.intervalms`。
- 达到 connector 尝试提交任务偏移量的间隔。该间隔由 Kafka Connect 配置 [`offset.flush.interval.ms`](https://docs.confluent.io/platform/current/connect/references/allconfigs.html) 控制，默认值为 `60000`。

为了降低数据延迟，请调整 Kafka connector 设置中的这些配置。但是，更频繁的刷新会增加 CPU 和 I/O 使用率。

### 限制

- 不支持将来自 Kafka topic 的单个消息展平为多个数据行并加载到 StarRocks 中。
- StarRocks 提供的 Kafka connector 的 sink 保证至少一次 (at-least-once) 的语义。

## 最佳实践

### 导入 Debezium 格式的 CDC 数据

Debezium 是一种流行的变更数据捕获 (Change Data Capture, CDC) 工具，支持监视各种数据库系统中的数据更改，并将这些更改流式传输到 Kafka。以下示例演示了如何配置和使用 Kafka connector 将 PostgreSQL 更改写入 StarRocks 中的 **Primary Key 表**。

#### 步骤 1：安装并启动 Kafka

> **注意**
>
> 如果您有自己的 Kafka 环境，则可以跳过此步骤。

1. 从官方网站 [下载](https://dlcdn.apache.org/kafka/) 最新的 Kafka 版本并解压该软件包。

   ```Bash
   tar -xzf kafka_2.13-3.7.0.tgz
   cd kafka_2.13-3.7.0
   ```

2. 启动 Kafka 环境。

   生成 Kafka 集群 UUID。

   ```Bash
   KAFKA_CLUSTER_ID="$(bin/kafka-storage.sh random-uuid)"
   ```

   格式化日志目录。

   ```Bash
   bin/kafka-storage.sh format -t $KAFKA_CLUSTER_ID -c config/kraft/server.properties
   ```

   启动 Kafka 服务器。

   ```Bash
   bin/kafka-server-start.sh config/kraft/server.properties
   ```

#### 步骤 2：配置 PostgreSQL

1. 确保 PostgreSQL 用户被授予 `REPLICATION` 权限。

2. 调整 PostgreSQL 配置。

   在 **postgresql.conf** 中将 `wal_level` 设置为 `logical`。

   ```Properties
   wal_level = logical
   ```

   重新启动 PostgreSQL 服务器以应用更改。

   ```Bash
   pg_ctl restart
   ```

3. 准备数据集。

   创建一个表并插入测试数据。

   ```SQL
   CREATE TABLE customers (
     id int primary key ,
     first_name varchar(65533) NULL,
     last_name varchar(65533) NULL ,
     email varchar(65533) NULL 
   );

   INSERT INTO customers VALUES (1,'a','a','a@a.com');
   ```

4. 验证 Kafka 中的 CDC 日志消息。

    ```Json
    {
        "schema": {
            "type": "struct",
            "fields": [
                {
                    "type": "struct",
                    "fields": [
                        {
                            "type": "int32",
                            "optional": false,
                            "field": "id"
                        },
                        {
                            "type": "string",
                            "optional": true,
                            "field": "first_name"
                        },
                        {
                            "type": "string",
                            "optional": true,
                            "field": "last_name"
                        },
                        {
                            "type": "string",
                            "optional": true,
                            "field": "email"
                        }
                    ],
                    "optional": true,
                    "name": "test.public.customers.Value",
                    "field": "before"
                },
                {
                    "type": "struct",
                    "fields": [
                        {
                            "type": "int32",
                            "optional": false,
                            "field": "id"
                        },
                        {
                            "type": "string",
                            "optional": true,
                            "field": "first_name"
                        },
                        {
                            "type": "string",
                            "optional": true,
                            "field": "last_name"
                        },
                        {
                            "type": "string",
                            "optional": true,
                            "field": "email"
                        }
                    ],
                    "optional": true,
                    "name": "test.public.customers.Value",
                    "field": "after"
                },
                {
                    "type": "struct",
                    "fields": [
                        {
                            "type": "string",
                            "optional": false,
                            "field": "version"
                        },
                        {
                            "type": "string",
                            "optional": false,
                            "field": "connector"
                        },
                        {
                            "type": "string",
                            "optional": false,
                            "field": "name"
                        },
                        {
                            "type": "int64",
                            "optional": false,
                            "field": "ts_ms"
                        },
                        {
                            "type": "string",
                            "optional": true,
                            "name": "io.debezium.data.Enum",
                            "version": 1,
                            "parameters": {
                                "allowed": "true,last,false,incremental"
                            },
                            "default": "false",
                            "field": "snapshot"
                        },
                        {
                            "type": "string",
                            "optional": false,
                            "field": "db"
                        },
                        {
                            "type": "string",
                            "optional": true,
                            "field": "sequence"
                        },
                        {
                            "type": "string",
                            "optional": false,
                            "field": "schema"
                        },
                        {
                            "type": "string",
                            "optional": false,
                            "field": "table"
                        },
                        {
                            "type": "int64",
                            "optional": true,
                            "field": "txId"
                        },
                        {
                            "type": "int64",
                            "optional": true,
                            "field": "lsn"
                        },
                        {
                            "type": "int64",
                            "optional": true,
                            "field": "xmin"
                        }
                    ],
                    "optional": false,
                    "name": "io.debezium.connector.postgresql.Source",
                    "field": "source"
                },
                {
                    "type": "string",
                    "optional": false,
                    "field": "op"
                },
                {
                    "type": "int64",
                    "optional": true,
                    "field": "ts_ms"
                },
                {
                    "type": "struct",
                    "fields": [
                        {
                            "type": "string",
                            "optional": false,
                            "field": "id"
                        },
                        {
                            "type": "int64",
                            "optional": false,
                            "field": "total_order"
                        },
                        {
                            "type": "int64",
                            "optional": false,
                            "field": "data_collection_order"
                        }
                    ],
                    "optional": true,
                    "name": "event.block",
                    "version": 1,
                    "field": "transaction"
                }
            ],
            "optional": false,
            "name": "test.public.customers.Envelope",
            "version": 1
        },
        "payload": {
            "before": null,
            "after": {
                "id": 1,
                "first_name": "a",
                "last_name": "a",
                "email": "a@a.com"
            },
            "source": {
                "version": "2.5.3.Final",
                "connector": "postgresql",
                "name": "test",
                "ts_ms": 1714283798721,
                "snapshot": "false",
                "db": "postgres",
                "sequence": "[\"22910216\",\"22910504\"]",
                "schema": "public",
                "table": "customers",
                "txId": 756,
                "lsn": 22910504,
                "xmin": null
            },
            "op": "c",
            "ts_ms": 1714283798790,
            "transaction": null
        }
    }
    ```

#### 步骤 3：配置 StarRocks

在 StarRocks 中创建一个 Primary Key 表，其 schema 与 PostgreSQL 中的源表相同。

```SQL
CREATE TABLE `customers` (
  `id` int(11) COMMENT "",
  `first_name` varchar(65533) NULL COMMENT "",
  `last_name` varchar(65533) NULL COMMENT "",
  `email` varchar(65533) NULL COMMENT ""
) ENGINE=OLAP 
PRIMARY KEY(`id`) 
DISTRIBUTED BY hash(id) buckets 1
PROPERTIES (
"bucket_size" = "4294967296",
"in_memory" = "false",
"enable_persistent_index" = "true",
"replicated_storage" = "true",
"fast_schema_evolution" = "true"
);
```

#### 步骤 4：安装 connector

1. 下载 connectors 并在 **plugins** 目录中解压软件包。

   ```Bash
   mkdir plugins
   tar -zxvf debezium-debezium-connector-postgresql-2.5.3.zip -C plugins
   mv starrocks-connector-for-kafka-x.y.z-with-dependencies.jar plugins
   ```

   此目录是 **config/connect-standalone.properties** 中配置项 `plugin.path` 的值。

   ```Properties
   plugin.path=/path/to/kafka_2.13-3.7.0/plugins
   ```

2. 在 **pg-source.properties** 中配置 PostgreSQL 源 connector。

   ```Json
   {
     "name": "inventory-connector",
     "config": {
       "connector.class": "io.debezium.connector.postgresql.PostgresConnector", 
       "plugin.name": "pgoutput",
       "database.hostname": "localhost", 
       "database.port": "5432", 
       "database.user": "postgres", 
       "database.password": "", 
       "database.dbname" : "postgres", 
       "topic.prefix": "test"
     }
   }
   ```

3. 在 **sr-sink.properties** 中配置 StarRocks sink connector。

   ```Json
   {
       "name": "starrocks-kafka-connector",
       "config": {
           "connector.class": "com.starrocks.connector.kafka.StarRocksSinkConnector",
           "tasks.max": "1",
           "topics": "test.public.customers",
           "starrocks.http.url": "172.26.195.69:28030",
           "starrocks.database.name": "test",
           "starrocks.username": "root",
           "starrocks.password": "StarRocks@123",
           "sink.properties.strip_outer_array": "true",
           "connect.timeoutms": "3000",
           "starrocks.topic2table.map": "test.public.customers:customers",
           "transforms": "addfield,unwrap",
           "transforms.addfield.type": "com.starrocks.connector.kafka.transforms.AddOpFieldForDebeziumRecord",
           "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
           "transforms.unwrap.drop.tombstones": "true",
           "transforms.unwrap.delete.handling.mode": "rewrite"
       }
   }
   ```

   > **注意**
   >
   > - 如果 StarRocks 表不是 Primary Key 表，则无需指定 `addfield` 转换。
   > - unwrap 转换由 Debezium 提供，用于根据操作类型解包 Debezium 的复杂数据结构。有关更多信息，请参见 [New Record State Extraction](https://debezium.io/documentation/reference/stable/transformations/event-flattening.html)。

4. 配置 Kafka Connect。

   在 Kafka Connect 配置文件 **config/connect-standalone.properties** 中配置以下配置项。

   ```Properties
   # Kafka brokers 的地址。多个 Kafka brokers 的地址需要用逗号 (,) 分隔。
   # 请注意，本示例使用 PLAINTEXT 作为访问 Kafka 集群的安全协议。
   # 如果您使用其他安全协议访问 Kafka 集群，请在此部分配置相关信息。

   bootstrap.servers=<kafka_broker_ip>:9092
   offset.storage.file.filename=/tmp/connect.offsets
   key.converter=org.apache.kafka.connect.json.JsonConverter
   value.converter=org.apache.kafka.connect.json.JsonConverter
   key.converter.schemas.enable=true
   value.converter.schemas.enable=false

   # starrocks-connector-for-kafka-x.y.z-with-dependencies.jar 的绝对路径。
   plugin.path=/home/kafka-connect/starrocks-kafka-connector

   # 控制刷新策略的参数。有关更多信息，请参见“使用注意事项”部分。
   offset.flush.interval.ms=10000
   bufferflush.maxbytes = xxx
   bufferflush.intervalms = xxx
   ```

   有关更多参数的描述，请参见 [Running Kafka Connect](https://kafka.apache.org/documentation.html#connect_running)。

#### 步骤 5：在独立模式下启动 Kafka Connect

在独立模式下运行 Kafka Connect 以启动 connectors。

```Bash
bin/connect-standalone.sh config/connect-standalone.properties config/pg-source.properties config/sr-sink.properties 
```

#### 步骤 6：验证数据摄取

测试以下操作，并确保数据已正确摄取到 StarRocks 中。

##### INSERT

- 在 PostgreSQL 中：

```Plain
postgres=# insert into customers values (2,'b','b','b@b.com');
INSERT 0 1
postgres=# select * from customers;
 id | first_name | last_name |  email  
----+------------+-----------+---------
  1 | a          | a         | a@a.com
  2 | b          | b          | b@b.com
(2 rows)
```

- 在 StarRocks 中：

```Plain
MySQL [test]> select * from customers;
+------+------------+-----------+---------+
| id   | first_name | last_name | email   |
+------+------------+-----------+---------+
|    1 | a          | a         | a@a.com |
|    2 | b          | b         | b@b.com |
+------+------------+-----------+---------+
2 rows in set (0.01 sec)
```

##### UPDATE

- 在 PostgreSQL 中：

```Plain
postgres=# update customers set email='c@c.com';
UPDATE 2
postgres=# select * from customers;
 id | first_name | last_name |  email  
----+------------+-----------+---------
  1 | a          | a         | c@c.com
  2 | b          | b         | c@c.com
(2 rows)
```

- 在 StarRocks 中：

```Plain
MySQL [test]> select * from customers;
+------+------------+-----------+---------+
| id   | first_name | last_name | email   |
+------+------------+-----------+---------+
|    1 | a          | a         | c@c.com |
|    2 | b          | b         | c@c.com |
+------+------------+-----------+---------+
2 rows in set (0.00 sec)
```

##### DELETE

- 在 PostgreSQL 中：

```Plain
postgres=# delete from customers where id=1;
DELETE 1
postgres=# select * from customers;
 id | first_name | last_name |  email  
----+------------+-----------+---------
  2 | b          | b         | c@c.com
(1 row)
```

- 在 StarRocks 中：

```Plain
MySQL [test]> select * from customers;
+------+------------+-----------+---------+
| id   | first_name | last_