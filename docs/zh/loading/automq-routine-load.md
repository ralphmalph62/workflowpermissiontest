---
displayed_sidebar: docs
description: Cloud based Kafka from AutoMQ
---

# AutoMQ Kafka

import Replicanum from '../_assets/commonMarkdown/replicanum.mdx'

[AutoMQ for Kafka](https://www.automq.com/docs) 是一个为云环境重新设计的 Kafka 云原生版本。
AutoMQ Kafka 是 [开源](https://github.com/AutoMQ/automq-for-kafka) 的，并且完全兼容 Kafka 协议，充分利用云的优势。
与自管理的 Apache Kafka 相比，AutoMQ Kafka 凭借其云原生架构，提供了诸如容量自动伸缩、网络流量的自我平衡、秒级移动分区等功能。这些功能大大降低了用户的总拥有成本 (TCO)。

本文将指导您使用 StarRocks Routine Load 将数据导入到 AutoMQ Kafka 中。
要了解 Routine Load 的基本原理，请参阅 Routine Load 原理部分。

## 准备环境

### 准备 StarRocks 和测试数据

确保您有一个正在运行的 StarRocks 集群。

创建一个数据库和一个 Primary Key 表用于测试：

```sql
create database automq_db;
create table users (
  id bigint NOT NULL,
  name string NOT NULL,
  timestamp string NULL,
  status string NULL
) PRIMARY KEY (id)
DISTRIBUTED BY HASH(id)
PROPERTIES (
  "enable_persistent_index" = "true"
);
```

<Replicanum />

## 准备 AutoMQ Kafka 和测试数据

要准备您的 AutoMQ Kafka 环境和测试数据，请按照 AutoMQ [Quick Start](https://www.automq.com/docs) 指南部署您的 AutoMQ Kafka 集群。确保 StarRocks 可以直接连接到您的 AutoMQ Kafka 服务器。

要在 AutoMQ Kafka 中快速创建一个名为 `example_topic` 的 topic 并写入测试 JSON 数据，请按照以下步骤操作：

### 创建一个 topic

使用 Kafka 的命令行工具创建一个 topic。确保您可以访问 Kafka 环境并且 Kafka 服务正在运行。
以下是创建 topic 的命令：

```shell
./kafka-topics.sh --create --topic example_topic --bootstrap-server 10.0.96.4:9092 --partitions 1 --replication-factor 1
```

> Note: 将 `topic` 和 `bootstrap-server` 替换为您的 Kafka 服务器地址。

要检查 topic 创建的结果，请使用以下命令：

```shell
./kafka-topics.sh --describe example_topic --bootstrap-server 10.0.96.4:9092
```

### 生成测试数据

生成一个简单的 JSON 格式测试数据

```json
{
  "id": 1,
  "name": "testuser",
  "timestamp": "2023-11-10T12:00:00",
  "status": "active"
}
```

### 写入测试数据

使用 Kafka 的命令行工具或编程方法将测试数据写入 example_topic。以下是使用命令行工具的示例：

```shell
echo '{"id": 1, "name": "testuser", "timestamp": "2023-11-10T12:00:00", "status": "active"}' | sh kafka-console-producer.sh --broker-list 10.0.96.4:9092 --topic example_topic
```

> Note: 将 `topic` 和 `bootstrap-server` 替换为您的 Kafka 服务器地址。

要查看最近写入的 topic 数据，请使用以下命令：

```shell
sh kafka-console-consumer.sh --bootstrap-server 10.0.96.4:9092 --topic example_topic --from-beginning
```

## 创建 Routine Load 任务

在 StarRocks 命令行中，创建一个 Routine Load 任务以持续从 AutoMQ Kafka topic 导入数据：

```sql
CREATE ROUTINE LOAD automq_example_load ON users
COLUMNS(id, name, timestamp, status)
PROPERTIES
(
  "desired_concurrent_number" = "5",
  "format" = "json",
  "jsonpaths" = "[\"$.id\",\"$.name\",\"$.timestamp\",\"$.status\"]"
)
FROM KAFKA
(
  "kafka_broker_list" = "10.0.96.4:9092",
  "kafka_topic" = "example_topic",
  "kafka_partitions" = "0",
  "property.kafka_default_offsets" = "OFFSET_BEGINNING"
);
```

> Note: 将 `kafka_broker_list` 替换为您的 Kafka 服务器地址。

### 参数说明

#### 数据格式

在 PROPERTIES 子句的 "format" = "json" 中将数据格式指定为 JSON。

#### 数据提取和转换

要指定源数据和目标表之间的映射和转换关系，请配置 COLUMNS 和 jsonpaths 参数。COLUMNS 中的列名对应于目标表的列名，它们的顺序对应于源数据中的列顺序。jsonpaths 参数用于从 JSON 数据中提取所需的字段数据，类似于新生成的 CSV 数据。然后，COLUMNS 参数临时命名 jsonpaths 中的字段，以便排序。有关数据转换的更多说明，请参见 [数据导入转换](./Etl_in_loading.md)。
> Note: 如果每行 JSON 对象都具有与目标表的列相对应的键名和数量（不需要顺序），则无需配置 COLUMNS。

## 验证数据导入

首先，我们检查 Routine Load 导入作业，并确认 Routine Load 导入任务状态为 RUNNING 状态。

```sql
show routine load\G
```

然后，查询 StarRocks 数据库中的相应表，我们可以观察到数据已成功导入。

```sql
StarRocks > select * from users;
+------+--------------+---------------------+--------+
| id   | name         | timestamp           | status |
+------+--------------+---------------------+--------+
|    1 | testuser     | 2023-11-10T12:00:00 | active |
|    2 | testuser     | 2023-11-10T12:00:00 | active |
+------+--------------+---------------------+--------+
2 rows in set (0.01 sec)
```