---
displayed_sidebar: docs
keywords: ['Routine Load']
---

# 使用 Routine Load 导入数据

import InsertPrivNote from '../_assets/commonMarkdown/insertPrivNote.mdx'
import QSTip from '../_assets/commonMarkdown/quickstart-routine-load-tip.mdx'

<QSTip />

本文介绍如何创建 Routine Load 作业，将 Kafka 消息（事件）流式传输到 StarRocks 中，并帮助您熟悉 Routine Load 的一些基本概念。

要将消息流持续不断地导入到 StarRocks 中，您可以将消息流存储在 Kafka topic 中，并创建一个 Routine Load 作业来消费这些消息。Routine Load 作业在 StarRocks 中持久存在，生成一系列导入任务，以消费 topic 中全部或部分分区中的消息，并将消息导入到 StarRocks 中。

Routine Load 作业支持精确一次 (exactly-once) 的交付语义，以保证导入到 StarRocks 中的数据既不会丢失也不会重复。

Routine Load 支持在数据导入时进行数据转换，并支持在数据导入期间通过 UPSERT 和 DELETE 操作进行数据更改。更多信息，请参见 [在导入时转换数据](../loading/Etl_in_loading.md) 和 [通过导入更改数据](../loading/Load_to_Primary_Key_tables.md)。

<InsertPrivNote />

## 支持的数据格式

Routine Load 现在支持从 Kafka 集群消费 CSV、JSON 和 Avro (v3.0.1 起支持) 格式的数据。

> **NOTE**
>
> 对于 CSV 数据，请注意以下几点：
>
> - 您可以使用 UTF-8 字符串，例如逗号 (,)、制表符或管道 (|)，其长度不超过 50 字节作为文本分隔符。
> - 空值用 `\N` 表示。例如，一个数据文件包含三列，该数据文件中的一条记录在第一列和第三列中包含数据，但在第二列中没有数据。在这种情况下，您需要在第二列中使用 `\N` 来表示空值。这意味着该记录必须编译为 `a,\N,b` 而不是 `a,,b`。`a,,b` 表示该记录的第二列包含一个空字符串。

## 基本概念

![routine load](../_assets/4.5.2-1.png)

### 术语

- **导入作业**

   Routine Load 作业是一个长时间运行的作业。只要其状态为 RUNNING，导入作业就会持续生成一个或多个并发导入任务，这些任务消费 Kafka 集群 topic 中的消息并将数据导入到 StarRocks 中。

- **导入任务**

  一个导入作业通过一定的规则被拆分为多个导入任务。导入任务是数据导入的基本单元。作为一个独立的事件，一个导入任务基于 [Stream Load](../loading/StreamLoad.md) 实现导入机制。多个导入任务并发地消费来自 topic 不同分区的消息，并将数据导入到 StarRocks 中。

### 工作流程

1. **创建一个 Routine Load 作业。**
   要从 Kafka 导入数据，您需要通过运行 [CREATE ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/CREATE_ROUTINE_LOAD.md) 语句来创建一个 Routine Load 作业。FE 解析该语句，并根据您指定的属性创建该作业。

2. **FE 将作业拆分为多个导入任务。**

    FE 基于一定的规则将作业拆分为多个导入任务。每个导入任务都是一个独立的事务。
    拆分规则如下：
    - FE 根据所需的并发数 `desired_concurrent_number`、Kafka topic 中的分区数以及处于活动状态的 BE 节点数来计算导入任务的实际并发数。
    - FE 基于计算出的实际并发数将作业拆分为导入任务，并将这些任务排列在任务队列中。

    每个 Kafka topic 由多个分区组成。Topic 分区和导入任务之间的关系如下：
    - 一个分区唯一地分配给一个导入任务，并且来自该分区的所有消息都由该导入任务消费。
    - 一个导入任务可以消费来自一个或多个分区的消息。
    - 所有分区均匀地分配给导入任务。

3. **多个导入任务并发运行，以消费来自多个 Kafka topic 分区的消息，并将数据导入到 StarRocks 中。**

   1. **FE 调度和提交导入任务**：FE 及时调度队列中的导入任务，并将它们分配给选定的 Coordinator BE 节点。导入任务之间的时间间隔由配置项 `max_batch_interval` 定义。FE 将导入任务均匀地分配给所有 BE 节点。有关 `max_batch_interval` 的更多信息，请参见 [CREATE ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/CREATE_ROUTINE_LOAD.md#examples)。

   2. Coordinator BE 启动导入任务，消费分区中的消息，解析和过滤数据。一个导入任务持续到消费了预定义数量的消息或达到预定义的时间限制为止。消息批处理大小和时间限制在 FE 配置 `max_routine_load_batch_size` 和 `routine_load_task_consume_second` 中定义。有关详细信息，请参见 [FE 配置](../administration/management/FE_configuration.md)。然后，Coordinator BE 将消息分发给 Executor BE。Executor BE 将消息写入磁盘。

         > **NOTE**
         >
         > StarRocks 支持通过包括 SASL_SSL、SAS_PLAINTEXT、SSL 和 PLAINTEXT 在内的安全协议访问 Kafka。本主题以通过 PLAINTEXT 连接到 Kafka 为例。如果您需要通过其他安全协议连接到 Kafka，请参见 [CREATE ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/CREATE_ROUTINE_LOAD.md)。

4. **FE 生成新的导入任务以持续导入数据。**
   在 Executor BE 将数据写入磁盘后，Coordinator BE 将导入任务的结果报告给 FE。基于该结果，FE 然后生成新的导入任务以持续导入数据。或者，FE 重试失败的任务以确保导入到 StarRocks 中的数据既不会丢失也不会重复。

## 创建 Routine Load 作业

以下三个示例描述了如何消费 Kafka 中的 CSV 格式、JSON 格式和 Avro 格式的数据，并通过创建 Routine Load 作业将数据导入到 StarRocks 中。有关详细的语法和参数描述，请参见 [CREATE ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/CREATE_ROUTINE_LOAD.md)。

### 导入 CSV 格式的数据

本节介绍如何创建一个 Routine Load 作业，以消费 Kafka 集群中的 CSV 格式数据，并将数据导入到 StarRocks 中。

#### 准备数据集

假设 Kafka 集群的 topic `ordertest1` 中有一个 CSV 格式的数据集。数据集中的每条消息都包含六个字段：订单 ID、支付日期、客户姓名、国籍、性别和价格。

```Plain
2020050802,2020-05-08,Johann Georg Faust,Deutschland,male,895
2020050802,2020-05-08,Julien Sorel,France,male,893
2020050803,2020-05-08,Dorian Grey,UK,male,1262
2020050901,2020-05-09,Anna Karenina",Russia,female,175
2020051001,2020-05-10,Tess Durbeyfield,US,female,986
2020051101,2020-05-11,Edogawa Conan,japan,male,8924
```

#### 创建表

根据 CSV 格式数据的字段，在数据库 `example_db` 中创建表 `example_tbl1`。以下示例创建一个包含 5 个字段的表，不包括 CSV 格式数据中的客户性别字段。

```SQL
CREATE TABLE example_db.example_tbl1 ( 
    `order_id` bigint NOT NULL COMMENT "Order ID",
    `pay_dt` date NOT NULL COMMENT "Payment date", 
    `customer_name` varchar(26) NULL COMMENT "Customer name", 
    `nationality` varchar(26) NULL COMMENT "Nationality", 
    `price`double NULL COMMENT "Price"
) 
ENGINE=OLAP 
DUPLICATE KEY (order_id,pay_dt) 
DISTRIBUTED BY HASH(`order_id`); 
```

> **NOTICE**
>
> 从 v2.5.7 开始，StarRocks 可以在您创建表或添加分区时自动设置 bucket 数量 (BUCKETS)。您不再需要手动设置 bucket 数量。有关详细信息，请参见 [设置 bucket 数量](../table_design/data_distribution/Data_distribution.md#set-the-number-of-buckets)。

#### 提交 Routine Load 作业

执行以下语句以提交一个名为 `example_tbl1_ordertest1` 的 Routine Load 作业，以消费 topic `ordertest1` 中的消息并将数据导入到表 `example_tbl1` 中。导入任务从 topic 的指定分区中的初始 offset 消费消息。

```SQL
CREATE ROUTINE LOAD example_db.example_tbl1_ordertest1 ON example_tbl1
COLUMNS TERMINATED BY ",",
COLUMNS (order_id, pay_dt, customer_name, nationality, temp_gender, price)
PROPERTIES
(
    "desired_concurrent_number" = "5"
)
FROM KAFKA
(
    "kafka_broker_list" = "<kafka_broker1_ip>:<kafka_broker1_port>,<kafka_broker2_ip>:<kafka_broker2_port>",
    "kafka_topic" = "ordertest1",
    "kafka_partitions" = "0,1,2,3,4",
    "property.kafka_default_offsets" = "OFFSET_BEGINNING"
);
```

提交导入作业后，您可以执行 [SHOW ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/SHOW_ROUTINE_LOAD.md) 语句来检查导入作业的状态。

- **导入作业名称**

  一个表上可能有多个导入作业。因此，我们建议您使用相应的 Kafka topic 和提交导入作业的时间来命名导入作业。这有助于您区分每个表上的导入作业。

- **列分隔符**

  属性 `COLUMN TERMINATED BY` 定义 CSV 格式数据的列分隔符。默认为 `\t`。

- **Kafka topic 分区和 offset**

  您可以指定属性 `kafka_partitions` 和 `kafka_offsets` 来指定要消费消息的分区和 offset。例如，如果您希望导入作业消费 topic `ordertest1` 的 Kafka 分区 `"0,1,2,3,4"` 中的消息，并且所有消息都具有初始 offset，则可以按如下方式指定属性：如果您希望导入作业消费 Kafka 分区 `"0,1,2,3,4"` 中的消息，并且需要为每个分区指定单独的起始 offset，则可以按如下方式配置：

    ```SQL
    "kafka_partitions" ="0,1,2,3,4",
    "kafka_offsets" = "OFFSET_BEGINNING, OFFSET_END, 1000, 2000, 3000"
    ```

  您还可以使用属性 `property.kafka_default_offsets` 设置所有分区的默认 offset。

    ```SQL
    "kafka_partitions" ="0,1,2,3,4",
    "property.kafka_default_offsets" = "OFFSET_BEGINNING"
    ```

  有关详细信息，请参见 [CREATE ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/CREATE_ROUTINE_LOAD.md)。

- **数据映射和转换**

  要指定 CSV 格式数据和 StarRocks 表之间的映射和转换关系，您需要使用 `COLUMNS` 参数。

  **数据映射：**

  - StarRocks 提取 CSV 格式数据中的列，并按照**顺序**将它们映射到 `COLUMNS` 参数中声明的字段。

  - StarRocks 提取 `COLUMNS` 参数中声明的字段，并按照**名称**将它们映射到 StarRocks 表的列。

  **数据转换：**

  并且由于该示例排除了 CSV 格式数据中的客户性别列，因此 `COLUMNS` 参数中的字段 `temp_gender` 用作此字段的占位符。其他字段直接映射到 StarRocks 表 `example_tbl1` 的列。

  有关数据转换的更多信息，请参见 [在导入时转换数据](./Etl_in_loading.md)。

    > **NOTE**
    >
    > 如果 CSV 格式数据中列的名称、数量和顺序与 StarRocks 表中的列完全对应，则无需指定 `COLUMNS` 参数。

- **任务并发**

  当 Kafka topic 分区很多且 BE 节点足够时，您可以通过增加任务并发来加速导入。

  要增加实际的导入任务并发，您可以在创建 Routine Load 作业时增加所需的导入任务并发 `desired_concurrent_number`。您还可以将 FE 的动态配置项 `max_routine_load_task_concurrent_num`（默认的最大导入任务并发数）设置为更大的值。有关 `max_routine_load_task_concurrent_num` 的更多信息，请参见 [FE 配置项](../administration/management/FE_configuration.md)。

  实际的任务并发由处于活动状态的 BE 节点数、预先指定的 Kafka topic 分区数以及 `desired_concurrent_number` 和 `max_routine_load_task_concurrent_num` 的值中的最小值定义。

  在该示例中，处于活动状态的 BE 节点数为 `5`，预先指定的 Kafka topic 分区数为 `5`，并且 `max_routine_load_task_concurrent_num` 的值为 `5`。要增加实际的导入任务并发，您可以将 `desired_concurrent_number` 从默认值 `3` 增加到 `5`。

  有关属性的更多信息，请参见 [CREATE ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/CREATE_ROUTINE_LOAD.md)。

### 导入 JSON 格式的数据

本节介绍如何创建一个 Routine Load 作业，以消费 Kafka 集群中的 JSON 格式数据，并将数据导入到 StarRocks 中。

#### 准备数据集

假设 Kafka 集群的 topic `ordertest2` 中有一个 JSON 格式的数据集。该数据集包括六个键：商品 ID、客户姓名、国籍、支付时间和价格。此外，您希望将支付时间列转换为 DATE 类型，并将其导入到 StarRocks 表中的 `pay_dt` 列。

```JSON
{"commodity_id": "1", "customer_name": "Mark Twain", "country": "US","pay_time": 1589191487,"price": 875}
{"commodity_id": "2", "customer_name": "Oscar Wilde", "country": "UK","pay_time": 1589191487,"price": 895}
{"commodity_id": "3", "customer_name": "Antoine de Saint-Exupéry","country": "France","pay_time": 1589191487,"price": 895}
```

> **CAUTION** 一行中的每个 JSON 对象必须位于一条 Kafka 消息中，否则将返回 JSON 解析错误。

#### 创建表

根据 JSON 格式数据的键，在数据库 `example_db` 中创建表 `example_tbl2`。

```SQL
CREATE TABLE `example_tbl2` ( 
    `commodity_id` varchar(26) NULL COMMENT "Commodity ID", 
    `customer_name` varchar(26) NULL COMMENT "Customer name", 
    `country` varchar(26) NULL COMMENT "Country", 
    `pay_time` bigint(20) NULL COMMENT "Payment time", 
    `pay_dt` date NULL COMMENT "Payment date", 
    `price`double SUM NULL COMMENT "Price"
) 
ENGINE=OLAP
AGGREGATE KEY(`commodity_id`,`customer_name`,`country`,`pay_time`,`pay_dt`) 
DISTRIBUTED BY HASH(`commodity_id`); 
```

> **NOTICE**
>
> 从 v2.5.7 开始，StarRocks 可以在您创建表或添加分区时自动设置 bucket 数量 (BUCKETS)。您不再需要手动设置 bucket 数量。有关详细信息，请参见 [设置 bucket 数量](../table_design/data_distribution/Data_distribution.md#set-the-number-of-buckets)。

#### 提交 Routine Load 作业

执行以下语句以提交一个名为 `example_tbl2_ordertest2` 的 Routine Load 作业，以消费 topic `ordertest2` 中的消息并将数据导入到表 `example_tbl2` 中。导入任务从 topic 的指定分区中的初始 offset 消费消息。

```SQL
CREATE ROUTINE LOAD example_db.example_tbl2_ordertest2 ON example_tbl2
COLUMNS(commodity_id, customer_name, country, pay_time, price, pay_dt=from_unixtime(pay_time, '%Y%m%d'))
PROPERTIES
(
    "desired_concurrent_number" = "5",
    "format" = "json",
    "jsonpaths" = "[\"$.commodity_id\",\"$.customer_name\",\"$.country\",\"$.pay_time\",\"$.price\"]"
 )
FROM KAFKA
(
    "kafka_broker_list" ="<kafka_broker1_ip>:<kafka_broker1_port>,<kafka_broker2_ip>:<kafka_broker2_port>",
    "kafka_topic" = "ordertest2",
    "kafka_partitions" ="0,1,2,3,4",
    "property.kafka_default_offsets" = "OFFSET_BEGINNING"
);
```

提交导入作业后，您可以执行 [SHOW ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/SHOW_ROUTINE_LOAD.md) 语句来检查导入作业的状态。

- **数据格式**

  您需要在 `PROPERTIES` 子句中指定 `"format" = "json"`，以定义数据格式为 JSON。

- **数据映射和转换**

  要指定 JSON 格式数据和 StarRocks 表之间的映射和转换关系，您需要指定参数 `COLUMNS` 和属性 `jsonpaths`。`COLUMNS` 参数中指定的字段顺序必须与 JSON 格式数据的顺序匹配，并且字段名称必须与 StarRocks 表的名称匹配。属性 `jsonpaths` 用于从 JSON 数据中提取所需的字段。然后，这些字段由属性 `COLUMNS` 命名。

  因为该示例需要将支付时间字段转换为 DATE 数据类型，并将数据导入到 StarRocks 表中的 `pay_dt` 列，所以您需要使用 from_unixtime 函数。其他字段直接映射到表 `example_tbl2` 的字段。

  **数据映射：**

  - StarRocks 提取 JSON 格式数据的 `name` 和 `code` 键，并将它们映射到 `jsonpaths` 属性中声明的键。

  - StarRocks 提取 `jsonpaths` 属性中声明的键，并按照**顺序**将它们映射到 `COLUMNS` 参数中声明的字段。

  - StarRocks 提取 `COLUMNS` 参数中声明的字段，并按照**名称**将它们映射到 StarRocks 表的列。

  **数据转换**：

  - 因为该示例需要将键 `pay_time` 转换为 DATE 数据类型，并将数据导入到 StarRocks 表中的 `pay_dt` 列，所以您需要在 `COLUMNS` 参数中使用 from_unixtime 函数。其他字段直接映射到表 `example_tbl2` 的字段。

  - 并且由于该示例排除了 JSON 格式数据中的客户性别列，因此 `COLUMNS` 参数中的字段 `temp_gender` 用作此字段的占位符。其他字段直接映射到 StarRocks 表 `example_tbl1` 的列。

    有关数据转换的更多信息，请参见 [在导入时转换数据](./Etl_in_loading.md)。

    > **NOTE**
    >
    > 如果 JSON 对象中键的名称和数量与 StarRocks 表中字段的名称和数量完全匹配，则无需指定 `COLUMNS` 参数。

### 导入 Avro 格式的数据

从 v3.0.1 开始，StarRocks 支持使用 Routine Load 导入 Avro 数据。

#### 准备数据集

##### Avro schema

1. 创建以下 Avro schema 文件 `avro_schema.avsc`：

      ```JSON
      {
          "type": "record",
          "name": "sensor_log",
          "fields" : [
              {"name": "id", "type": "long"},
              {"name": "name", "type": "string"},
              {"name": "checked", "type" : "boolean"},
              {"name": "data", "type": "double"},
              {"name": "sensor_type", "type": {"type": "enum", "name": "sensor_type_enum", "symbols" : ["TEMPERATURE", "HUMIDITY", "AIR-PRESSURE"]}}  
          ]
      }
      ```

2. 在 [Schema Registry](https://docs.confluent.io/cloud/current/get-started/schema-registry.html#create-a-schema) 中注册 Avro schema。

##### Avro 数据

准备 Avro 数据并将其发送到 Kafka topic `topic_0`。

#### 创建表

根据 Avro 数据的字段，在 StarRocks 集群的目标数据库 `example_db` 中创建一个表 `sensor_log`。表的列名必须与 Avro 数据中的字段名匹配。有关表列和 Avro 数据字段之间的数据类型映射，请参见 [数据类型映射](#Data types mapping)。

```SQL
CREATE TABLE example_db.sensor_log ( 
    `id` bigint NOT NULL COMMENT "sensor id",
    `name` varchar(26) NOT NULL COMMENT "sensor name", 
    `checked` boolean NOT NULL COMMENT "checked", 
    `data` double NULL COMMENT "sensor data", 
    `sensor_type` varchar(26) NOT NULL COMMENT "sensor type"
) 
ENGINE=OLAP 
DUPLICATE KEY (id) 
DISTRIBUTED BY HASH(`id`); 
```

> **NOTICE**
>
> 从 v2.5.7 开始，StarRocks 可以在您创建表或添加分区时自动设置 bucket 数量 (BUCKETS)。您不再需要手动设置 bucket 数量。有关详细信息，请参见 [设置 bucket 数量](../table_design/data_distribution/Data_distribution.md#set-the-number-of-buckets)。

#### 提交 Routine Load 作业

执行以下语句以提交一个名为 `sensor_log_load_job` 的 Routine Load 作业，以消费 Kafka topic `topic_0` 中的 Avro 消息并将数据导入到数据库 `sensor` 中的表 `sensor_log` 中。导入作业从 topic 的指定分区中的初始 offset 消费消息。

```SQL
CREATE ROUTINE LOAD example_db.sensor_log_load_job ON sensor_log  
PROPERTIES  
(  
    "format" = "avro"  
)  
FROM KAFKA  
(  
    "kafka_broker_list" = "<kafka_broker1_ip>:<kafka_broker1_port>,<kafka_broker2_ip>:<kafka_broker2_port>,...",
    "confluent.schema.registry.url" = "http://172.xx.xxx.xxx:8081",  
    "kafka_topic" = "topic_0",  
    "kafka_partitions" = "0,1,2,3,4,5",  
    "property.kafka_default_offsets" = "OFFSET_BEGINNING"  
);
```

- 数据格式

  您需要在 `PROPERTIES` 子句中指定 `"format = "avro"`，以定义数据格式为 Avro。

- Schema Registry

  您需要配置 `confluent.schema.registry.url` 以指定注册 Avro schema 的 Schema Registry 的 URL。StarRocks 使用此 URL 检索 Avro schema。格式如下：

  ```Plaintext
  confluent.schema.registry.url = http[s]://[<schema-registry-api-key>:<schema-registry-api-secret>@]<hostname|ip address>[:<port>]
  ```

- 数据映射和转换

  要指定 Avro 格式数据和 StarRocks 表之间的映射和转换关系，您需要指定参数 `COLUMNS` 和属性 `jsonpaths`。`COLUMNS` 参数中指定的字段顺序必须与属性 `jsonpaths` 中字段的顺序匹配，并且字段名称必须与 StarRocks 表的名称匹配。属性 `jsonpaths` 用于从 Avro 数据中提取所需的字段。然后，这些字段由属性 `COLUMNS` 命名。

  有关数据转换的更多信息，请参见 [在导入时转换数据](./Etl_in_loading.md)。

  > NOTE
  >
  > 如果 Avro 记录中字段的名称和数量与 StarRocks 表中列的名称和数量完全匹配，则无需指定 `COLUMNS` 参数。

提交导入作业后，您可以执行 [SHOW ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/SHOW_ROUTINE_LOAD.md) 语句来检查导入作业的状态。

#### 数据类型映射

您要导入的 Avro 数据字段与 StarRocks 表列之间的数据类型映射如下：

##### 原始类型

| Avro    | StarRocks |
| ------- | --------- |
| nul     | NULL      |
| boolean | BOOLEAN   |
| int     | INT       |
| long    | BIGINT    |
| float   | FLOAT     |
| double  | DOUBLE    |
| bytes   | STRING    |
| string  | STRING    |

##### 复杂类型

| Avro           | StarRocks                                                    |
| -------------- | ------------------------------------------------------------ |
| record         | 将整个 RECORD 或其子字段作为 JSON 导入到 StarRocks 中。 |
| enums          | STRING                                                       |
| arrays         | ARRAY                                                        |
| maps           | JSON                                                         |
| union(T, null) | NULLABLE(T)                                                  |
| fixed          | STRING                                                       |

#### 限制

- 目前，StarRocks 不支持 schema evolution。
- 每条 Kafka 消息必须仅包含一条 Avro 数据记录。

## 检查导入作业和任务

### 检查导入作业

执行 [SHOW ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/SHOW_ROUTINE_LOAD.md) 语句以检查导入作业 `example_tbl2_ordertest2` 的状态。StarRocks 返回执行状态 `State`、统计信息（包括消费的总行数和导入的总行数）`Statistics` 以及导入作业的进度 `progress`。

如果导入作业的状态自动更改为 **PAUSED**，则可能是因为错误行数已超过阈值。有关设置此阈值的详细说明，请参见 [CREATE ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/CREATE_ROUTINE_LOAD.md)。您可以检查文件 `ReasonOfStateChanged` 和 `ErrorLogUrls` 以识别和解决问题。解决问题后，您可以执行 [RESUME ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/RESUME_ROUTINE_LOAD.md) 语句以恢复 **PAUSED** 导入作业。

如果导入作业的状态为 **CANCELLED**，则可能是因为导入作业遇到异常（例如，表已被删除）。您可以检查文件 `ReasonOfStateChanged` 和 `ErrorLogUrls` 以识别和解决问题。但是，您无法恢复 **CANCELLED** 导入作业。

```SQL
MySQL [example_db]> SHOW ROUTINE LOAD FOR example_tbl2_ordertest2 \G
*************************** 1. row ***************************
                  Id: 63013
                Name: example_tbl2_ordertest2
          CreateTime: 2022-08-10 17:09:00
           PauseTime: NULL
             EndTime: NULL
              DbName: default_cluster:example_db
           TableName: example_tbl2
               State: RUNNING
      DataSourceType: KAFKA
      CurrentTaskNum: 3
       JobProperties: {"partitions":"*","partial_update":"false","columnToColumnExpr":"commodity_id,customer_name,country,pay_time,pay_dt=from_unixtime(`pay_time`, '%Y%m%d'),price","maxBatchIntervalS":"20","whereExpr":"*","dataFormat":"json","timezone":"Asia/Shanghai","format":"json","json_root":"","strict_mode":"false","jsonpaths":"[\"$.commodity_id\",\"$.customer_name\",\"$.country\",\"$.pay_time\",\"$.price\"]","desireTaskConcurrentNum":"3","maxErrorNum":"0","strip_outer_array":"false","currentTaskConcurrentNum":"3","maxBatchRows":"200000"}
DataSourceProperties: {"topic":"ordertest2","currentKafkaPartitions":"0,1,2,3,4","brokerList":"<kafka_broker1_ip>:<kafka_broker1_port>,<kafka_broker2_ip>:<kafka_broker2_port>"}
    CustomProperties: {"kafka_default_offsets":"OFFSET_BEGINNING"}
           Statistic: {"receivedBytes":230,"errorRows":0,"committedTaskNum":1,"loadedRows":2,"loadRowsRate":0,"abortedTaskNum":0,"totalRows":2,"unselectedRows":0,"receivedBytesRate":0,"taskExecuteTimeMs":522}
            Progress: {"0":"1","1":"OFFSET_ZERO","2":"OFFSET_ZERO","3":"OFFSET_ZERO","4":"OFFSET_ZERO"}
ReasonOfStateChanged: 
        ErrorLogUrls: 
            OtherMsg: 
```

> **CAUTION**
>
> 您无法检查已停止或尚未启动的导入作业。

### 检查导入任务

执行 [SHOW ROUTINE LOAD TASK](../sql-reference/sql-statements/loading_unloading/routine_load/SHOW_ROUTINE_LOAD_TASK.md) 语句以检查导入作业 `example_tbl2_ordertest2` 的导入任务，例如当前正在运行的任务数、正在消费的 Kafka topic 分区和消费进度 `DataSourceProperties` 以及相应的 Coordinator BE 节点 `BeId`。

```SQL
MySQL [example_db]> SHOW ROUTINE LOAD TASK WHERE JobName = "example_tbl2_ordertest2" \G
*************************** 1. row ***************************
              TaskId: 18c3a823-d73e-4a64-b9cb-b9eced026753
               TxnId: -1
           TxnStatus: UNKNOWN
               JobId: 63013
          CreateTime: 2022-08-10 17:09:05
   LastScheduledTime: 2022-08-10 17:47:27
    ExecuteStartTime: NULL
             Timeout: 60
                BeId: -1
DataSourceProperties: {"1":0,"4":0}
             Message: there is no new data in kafka, wait for 20 seconds to schedule again
*************************** 2. row ***************************
              TaskId: f76c97ac-26aa-4b41-8194-a8ba2063eb00
               TxnId: -1
           TxnStatus: UNKNOWN
               JobId: 63013
          CreateTime: 2022-08-10 17:09:05
   LastScheduledTime: 2022-08-10 17:47:26
    ExecuteStartTime: NULL
             Timeout: 60
                BeId: -1
DataSourceProperties: {"2":0}
             Message: there is no new data in kafka, wait for 20 seconds to schedule again
*************************** 3. row ***************************
              TaskId: 1a327a34-99f4-4f8d-8014-3cd38db99ec6
               TxnId: -1
           TxnStatus: UNKNOWN
               JobId: 63013
          CreateTime: 2022-08-10 17:09:26
   LastScheduledTime: 2022-08-10 17:47:27
    ExecuteStartTime: NULL
             Timeout: 60
                BeId: -1
DataSourceProperties: {"0":2,"3":0}
             Message: there is no new data in kafka, wait for 20 seconds to schedule again
```

## 暂停导入作业

您可以执行 [PAUSE ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/PAUSE_ROUTINE_LOAD.md) 语句以暂停导入作业。执行该语句后，导入作业的状态将为 **PAUSED**。但是，它尚未停止。您可以执行 [RESUME ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/RESUME_ROUTINE_LOAD.md) 语句以恢复它。您还可以使用 [SHOW ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/SHOW_ROUTINE_LOAD.md) 语句检查其状态。

以下示例暂停导入作业 `example_tbl2_ordertest2`：

```SQL
PAUSE ROUTINE LOAD FOR example_tbl2_ordertest2;
```

## 恢复导入作业

您可以执行 [RESUME ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/RESUME_ROUTINE_LOAD.md) 语句以恢复已暂停的导入作业。导入作业的状态将暂时为 **NEED_SCHEDULE**（因为正在重新调度导入作业），然后变为 **RUNNING**。您可以使用 [SHOW ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/SHOW_ROUTINE_LOAD.md) 语句检查其状态。

以下示例恢复已暂停的导入作业 `example_tbl2_ordertest2`：

```SQL
RESUME ROUTINE LOAD FOR example_tbl2_ordertest2;
```

## 更改导入作业

在更改导入作业之前，您必须使用 [PAUSE ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/PAUSE_ROUTINE_LOAD.md) 语句暂停它。然后，您可以执行 [ALTER ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/ALTER_ROUTINE_LOAD.md)。更改后，您可以执行 [RESUME ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/RESUME_ROUTINE_LOAD.md) 语句以恢复它，并使用 [SHOW ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/SHOW_ROUTINE_LOAD.md) 语句检查其状态。

假设处于活动状态的 BE 节点数增加到 `6`，并且要消费的 Kafka topic 分区为 `"0,1,2,3,4,5,6,7"`。如果您想增加实际的导入任务并发，您可以执行以下语句来将所需的任务并发数 `desired_concurrent_number` 增加到 `6`（大于或等于处于活动状态的 BE 节点数），并指定 Kafka topic 分区和初始 offset。

> **NOTE**
>
> 因为实际的任务并发由多个参数的最小值决定，所以您必须确保 FE 动态参数 `max_routine_load_task_concurrent_num` 的值大于或