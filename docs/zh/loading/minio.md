---
displayed_sidebar: docs
toc_max_heading_level: 4
---

# 从 MinIO 导入数据

import InsertPrivNote from '../_assets/commonMarkdown/insertPrivNote.mdx'

StarRocks 提供了以下从 MinIO 导入数据的选项：

- 使用 [INSERT](../sql-reference/sql-statements/loading_unloading/INSERT.md) + [`FILES()`](../sql-reference/sql-functions/table-functions/files.md) 进行同步导入
- 使用 [Broker Load](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md) 进行异步导入

这些选项各有优势，以下各节将详细介绍。

在大多数情况下，我们建议您使用 INSERT+`FILES()` 方法，因为它更易于使用。

但是，INSERT+`FILES()` 方法目前仅支持 Parquet、ORC 和 CSV 文件格式。因此，如果您需要导入其他文件格式（如 JSON）的数据，或者[在数据导入期间执行数据更改（如 DELETE）](../loading/Load_to_Primary_Key_tables.md)，您可以选择使用 Broker Load。

## 前提条件

### 准备源数据

确保要导入到 StarRocks 中的源数据已正确存储在 MinIO bucket 中。您还可以考虑数据和数据库的位置，因为当您的 bucket 和 StarRocks 集群位于同一区域时，数据传输成本会低得多。

在本主题中，我们为您提供了一个示例数据集。您可以使用 `curl` 下载它：

```bash
curl -O https://starrocks-examples.s3.amazonaws.com/user_behavior_ten_million_rows.parquet
```

将 Parquet 文件导入到您的 MinIO 系统中，并记下 bucket 名称。本指南中的示例使用 `/starrocks` 作为 bucket 名称。

### 检查权限

<InsertPrivNote />

### 收集连接详细信息

简而言之，要使用 MinIO Access Key 身份验证，您需要收集以下信息：

- 存储数据的 bucket
- 对象 key（对象名称）（如果访问 bucket 中的特定对象）
- MinIO endpoint
- 用作访问凭据的 access key 和 secret key。

![MinIO access key](../_assets/quick-start/MinIO-create.png)

## 使用 INSERT+FILES()

此方法从 v3.1 版本开始可用，目前仅支持 Parquet、ORC 和 CSV（从 v3.3.0 版本开始）文件格式。

### INSERT+FILES() 的优势

[`FILES()`](../sql-reference/sql-functions/table-functions/files.md) 可以读取存储在云存储中的文件，基于您指定的路径相关属性，推断文件中数据的表结构，然后将文件中的数据作为数据行返回。

使用 `FILES()`，您可以：

- 使用 [SELECT](../sql-reference/sql-statements/table_bucket_part_index/SELECT.md) 直接从 MinIO 查询数据。
- 使用 [CREATE TABLE AS SELECT](../sql-reference/sql-statements/table_bucket_part_index/CREATE_TABLE_AS_SELECT.md) (CTAS) 创建和导入表。
- 使用 [INSERT](../sql-reference/sql-statements/loading_unloading/INSERT.md) 将数据导入到现有表中。

### 典型示例

#### 使用 SELECT 直接从 MinIO 查询

使用 SELECT+`FILES()` 直接从 MinIO 查询可以在创建表之前很好地预览数据集的内容。例如：

- 在不存储数据的情况下获取数据集的预览。
- 查询最小值和最大值，并确定要使用的数据类型。
- 检查 `NULL` 值。

以下示例查询先前添加到您的 MinIO 系统的示例数据集。

:::tip

命令中突出显示的部分包含您可能需要更改的设置：

- 设置 `endpoint` 和 `path` 以匹配您的 MinIO 系统。
- 如果您的 MinIO 系统使用 SSL，请将 `enable_ssl` 设置为 `true`。
- 将您的 MinIO access key 和 secret key 替换为 `AAA` 和 `BBB`。

:::

```sql
SELECT * FROM FILES
(
    -- highlight-start
    "aws.s3.endpoint" = "http://minio:9000",
    "path" = "s3://starrocks/user_behavior_ten_million_rows.parquet",
    "aws.s3.enable_ssl" = "false",
    "aws.s3.access_key" = "AAAAAAAAAAAAAAAAAAAA",
    "aws.s3.secret_key" = "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
    -- highlight-end
    "format" = "parquet",
    "aws.s3.use_aws_sdk_default_behavior" = "false",
    "aws.s3.use_instance_profile" = "false",
    "aws.s3.enable_path_style_access" = "true"
)
LIMIT 3;
```

系统返回以下查询结果：

```plaintext
+--------+---------+------------+--------------+---------------------+
| UserID | ItemID  | CategoryID | BehaviorType | Timestamp           |
+--------+---------+------------+--------------+---------------------+
| 543711 |  829192 |    2355072 | pv           | 2017-11-27 08:22:37 |
| 543711 | 2056618 |    3645362 | pv           | 2017-11-27 10:16:46 |
| 543711 | 1165492 |    3645362 | pv           | 2017-11-27 10:17:00 |
+--------+---------+------------+--------------+---------------------+
3 rows in set (0.41 sec)
```

:::info

请注意，上面返回的列名由 Parquet 文件提供。

:::

#### 使用 CTAS 创建和导入表

这是前一个示例的延续。先前的查询包装在 CREATE TABLE AS SELECT (CTAS) 中，以使用模式推断自动执行表创建。这意味着 StarRocks 将推断表结构，创建您想要的表，然后将数据加载到表中。使用 `FILES()` 表函数和 Parquet 文件时，不需要列名和类型来创建表，因为 Parquet 格式包含列名。

:::note

使用模式推断时，CREATE TABLE 的语法不允许设置副本数，因此请在创建表之前设置它。以下示例适用于具有单个副本的系统：

```SQL
ADMIN SET FRONTEND CONFIG ('default_replication_num' = '1');
```

:::

创建一个数据库并切换到它：

```SQL
CREATE DATABASE IF NOT EXISTS mydatabase;
USE mydatabase;
```

使用 CTAS 创建一个表，并加载先前添加到您的 MinIO 系统的示例数据集的数据。

:::tip

命令中突出显示的部分包含您可能需要更改的设置：

- 设置 `endpoint` 和 `path` 以匹配您的 MinIO 系统。
- 如果您的 MinIO 系统使用 SSL，请将 `enable_ssl` 设置为 `true`。
- 将您的 MinIO access key 和 secret key 替换为 `AAA` 和 `BBB`。

:::

```sql
CREATE TABLE user_behavior_inferred AS
SELECT * FROM FILES
(
    -- highlight-start
    "aws.s3.endpoint" = "http://minio:9000",
    "path" = "s3://starrocks/user_behavior_ten_million_rows.parquet",
    "aws.s3.enable_ssl" = "false",
    "aws.s3.access_key" = "AAAAAAAAAAAAAAAAAAAA",
    "aws.s3.secret_key" = "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
    -- highlight-end
    "format" = "parquet",
    "aws.s3.use_aws_sdk_default_behavior" = "false",
    "aws.s3.use_instance_profile" = "false",
    "aws.s3.enable_path_style_access" = "true"
);
```

```plaintext
Query OK, 10000000 rows affected (3.17 sec)
{'label':'insert_a5da3ff5-9ee4-11ee-90b0-02420a060004', 'status':'VISIBLE', 'txnId':'17'}
```

创建表后，您可以使用 [DESCRIBE](../sql-reference/sql-statements/table_bucket_part_index/DESCRIBE.md) 查看其结构：

```SQL
DESCRIBE user_behavior_inferred;
```

系统返回以下查询结果：

```Plaintext
+--------------+------------------+------+-------+---------+-------+
| Field        | Type             | Null | Key   | Default | Extra |
+--------------+------------------+------+-------+---------+-------+
| UserID       | bigint           | YES  | true  | NULL    |       |
| ItemID       | bigint           | YES  | true  | NULL    |       |
| CategoryID   | bigint           | YES  | true  | NULL    |       |
| BehaviorType | varchar(1048576) | YES  | false | NULL    |       |
| Timestamp    | varchar(1048576) | YES  | false | NULL    |       |
+--------------+------------------+------+-------+---------+-------+
```

查询表以验证数据是否已加载到其中。示例：

```SQL
SELECT * from user_behavior_inferred LIMIT 3;
```

返回以下查询结果，表明数据已成功加载：

```Plaintext
+--------+--------+------------+--------------+---------------------+
| UserID | ItemID | CategoryID | BehaviorType | Timestamp           |
+--------+--------+------------+--------------+---------------------+
|     58 | 158350 |    2355072 | pv           | 2017-11-27 13:06:51 |
|     58 | 158590 |    3194735 | pv           | 2017-11-27 02:21:04 |
|     58 | 215073 |    3002561 | pv           | 2017-11-30 10:55:42 |
+--------+--------+------------+--------------+---------------------+
```

#### 使用 INSERT 导入到现有表

您可能想要自定义要导入的表，例如：

- 列数据类型、nullable 设置或默认值
- key 类型和列
- 数据分区和分桶

:::tip

创建最有效的表结构需要了解如何使用数据以及列的内容。本主题不包括表设计。有关表设计的信息，请参见 [表类型](../table_design/StarRocks_table_design.md)。

:::

在此示例中，我们基于对如何查询表以及 Parquet 文件中的数据的了解来创建表。对 Parquet 文件中数据的了解可以通过直接在 MinIO 中查询文件来获得。

- 由于在 MinIO 中查询数据集表明 `Timestamp` 列包含与 `datetime` 数据类型匹配的数据，因此在以下 DDL 中指定了列类型。
- 通过查询 MinIO 中的数据，您可以发现数据集中没有 `NULL` 值，因此 DDL 不会将任何列设置为 nullable。
- 根据对预期查询类型的了解，排序键和分桶列设置为列 `UserID`。您的用例可能与此数据不同，因此您可能会决定除了 `UserID` 之外或代替 `UserID` 使用 `ItemID` 作为排序键。

创建一个数据库并切换到它：

```SQL
CREATE DATABASE IF NOT EXISTS mydatabase;
USE mydatabase;
```

手动创建一个表（我们建议该表具有与要从 MinIO 导入的 Parquet 文件相同的结构）：

```SQL
CREATE TABLE user_behavior_declared
(
    UserID int(11) NOT NULL,
    ItemID int(11) NOT NULL,
    CategoryID int(11) NOT NULL,
    BehaviorType varchar(65533) NOT NULL,
    Timestamp datetime NOT NULL
)
ENGINE = OLAP 
DUPLICATE KEY(UserID)
DISTRIBUTED BY HASH(UserID)
PROPERTIES
(
    'replication_num' = '1'
);
```

显示结构，以便您可以将其与 `FILES()` 表函数生成的推断结构进行比较：

```sql
DESCRIBE user_behavior_declared;
```

```plaintext
+--------------+----------------+------+-------+---------+-------+
| Field        | Type           | Null | Key   | Default | Extra |
+--------------+----------------+------+-------+---------+-------+
| UserID       | int            | NO   | true  | NULL    |       |
| ItemID       | int            | NO   | false | NULL    |       |
| CategoryID   | int            | NO   | false | NULL    |       |
| BehaviorType | varchar(65533) | NO   | false | NULL    |       |
| Timestamp    | datetime       | NO   | false | NULL    |       |
+--------------+----------------+------+-------+---------+-------+
5 rows in set (0.00 sec)
```

:::tip

将您刚刚创建的结构与之前使用 `FILES()` 表函数推断的结构进行比较。查看：

- 数据类型
- nullable
- key 字段

为了更好地控制目标表的结构并获得更好的查询性能，我们建议您在生产环境中手动指定表结构。对于时间戳字段，使用 `datetime` 数据类型比使用 `varchar` 更有效。

:::

创建表后，您可以使用 INSERT INTO SELECT FROM FILES() 加载它：

:::tip

命令中突出显示的部分包含您可能需要更改的设置：

- 设置 `endpoint` 和 `path` 以匹配您的 MinIO 系统。
- 如果您的 MinIO 系统使用 SSL，请将 `enable_ssl` 设置为 `true`。
- 将您的 MinIO access key 和 secret key 替换为 `AAA` 和 `BBB`。

:::

```SQL
INSERT INTO user_behavior_declared
SELECT * FROM FILES
(
    -- highlight-start
    "aws.s3.endpoint" = "http://minio:9000",
    "path" = "s3://starrocks/user_behavior_ten_million_rows.parquet",
    "aws.s3.enable_ssl" = "false",
    "aws.s3.access_key" = "AAAAAAAAAAAAAAAAAAAA",
    "aws.s3.secret_key" = "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
    -- highlight-end
    "format" = "parquet",
    "aws.s3.use_aws_sdk_default_behavior" = "false",
    "aws.s3.use_instance_profile" = "false",
    "aws.s3.enable_path_style_access" = "true"
);
```

加载完成后，您可以查询表以验证数据是否已加载到其中。示例：

```SQL
SELECT * from user_behavior_declared LIMIT 3;
```

返回以下查询结果，表明数据已成功加载：

```Plaintext
+--------+---------+------------+--------------+---------------------+
| UserID | ItemID  | CategoryID | BehaviorType | Timestamp           |
+--------+---------+------------+--------------+---------------------+
|     58 | 4309692 |    1165503 | pv           | 2017-11-25 14:06:52 |
|     58 |  181489 |    1165503 | pv           | 2017-11-25 14:07:22 |
|     58 | 3722956 |    1165503 | pv           | 2017-11-25 14:09:28 |
+--------+---------+------------+--------------+---------------------+
```

#### 检查导入进度

您可以从 StarRocks Information Schema 中的 [`loads`](../sql-reference/information_schema/loads.md) 视图查询 INSERT 作业的进度。此功能从 v3.1 版本开始支持。示例：

```SQL
SELECT * FROM information_schema.loads ORDER BY JOB_ID DESC;
```

有关 `loads` 视图中提供的字段的信息，请参见 [`loads`](../sql-reference/information_schema/loads.md)。

如果您提交了多个导入作业，则可以按与作业关联的 `LABEL` 进行过滤。示例：

```SQL
SELECT * FROM information_schema.loads WHERE LABEL = 'insert_e3b882f5-7eb3-11ee-ae77-00163e267b60' \G
*************************** 1. row ***************************
              JOB_ID: 10243
               LABEL: insert_e3b882f5-7eb3-11ee-ae77-00163e267b60
       DATABASE_NAME: mydatabase
               STATE: FINISHED
            PROGRESS: ETL:100%; LOAD:100%
                TYPE: INSERT
            PRIORITY: NORMAL
           SCAN_ROWS: 10000000
       FILTERED_ROWS: 0
     UNSELECTED_ROWS: 0
           SINK_ROWS: 10000000
            ETL_INFO:
           TASK_INFO: resource:N/A; timeout(s):300; max_filter_ratio:0.0
         CREATE_TIME: 2023-11-09 11:56:01
      ETL_START_TIME: 2023-11-09 11:56:01
     ETL_FINISH_TIME: 2023-11-09 11:56:01
     LOAD_START_TIME: 2023-11-09 11:56:01
    LOAD_FINISH_TIME: 2023-11-09 11:56:44
         JOB_DETAILS: {"All backends":{"e3b882f5-7eb3-11ee-ae77-00163e267b60":[10142]},"FileNumber":0,"FileSize":0,"InternalTableLoadBytes":311710786,"InternalTableLoadRows":10000000,"ScanBytes":581574034,"ScanRows":10000000,"TaskNumber":1,"Unfinished backends":{"e3b882f5-7eb3-11ee-ae77-00163e267b60":[]}}
           ERROR_MSG: NULL
        TRACKING_URL: NULL
        TRACKING_SQL: NULL
REJECTED_RECORD_PATH: NULL
```

:::tip

INSERT 是一个同步命令。如果 INSERT 作业仍在运行，您需要打开另一个会话来检查其执行状态。

:::

### 比较磁盘上的表大小

此查询比较具有推断结构的表和声明了结构的表。由于推断的结构具有 nullable 列和时间戳的 varchar，因此数据长度更大：

```sql
SELECT TABLE_NAME,
       TABLE_ROWS,
       AVG_ROW_LENGTH,
       DATA_LENGTH
FROM information_schema.tables
WHERE TABLE_NAME like 'user_behavior%'\G
```

```plaintext
*************************** 1. row ***************************
    TABLE_NAME: user_behavior_declared
    TABLE_ROWS: 10000000
AVG_ROW_LENGTH: 10
   DATA_LENGTH: 102562516
*************************** 2. row ***************************
    TABLE_NAME: user_behavior_inferred
    TABLE_ROWS: 10000000
AVG_ROW_LENGTH: 17
   DATA_LENGTH: 176803880
2 rows in set (0.04 sec)
```

## 使用 Broker Load

异步 Broker Load 进程处理与 MinIO 的连接、提取数据以及将数据存储在 StarRocks 中。

此方法支持以下文件格式：

- Parquet
- ORC
- CSV
- JSON（从 v3.2.3 版本开始支持）

### Broker Load 的优势

- Broker Load 在后台运行，客户端无需保持连接即可继续作业。
- Broker Load 更适合长时间运行的作业，默认超时时间为 4 小时。
- 除了 Parquet 和 ORC 文件格式外，Broker Load 还支持 CSV 文件格式和 JSON 文件格式（JSON 文件格式从 v3.2.3 版本开始支持）。

### 数据流

![Broker Load 的工作流程](../_assets/broker_load_how-to-work_en.png)

1. 用户创建一个导入作业。
2. 前端 (FE) 创建一个查询计划，并将该计划分发到后端节点 (BE) 或计算节点 (CN)。
3. BE 或 CN 从源提取数据，并将数据加载到 StarRocks 中。

### 典型示例

创建一个表，启动一个导入进程，该进程提取先前加载到您的 MinIO 系统的示例数据集。

#### 创建数据库和表

创建一个数据库并切换到它：

```SQL
CREATE DATABASE IF NOT EXISTS mydatabase;
USE mydatabase;
```

手动创建一个表（我们建议该表具有与要从 MinIO 导入的 Parquet 文件相同的结构）：

```SQL
CREATE TABLE user_behavior
(
    UserID int(11) NOT NULL,
    ItemID int(11) NOT NULL,
    CategoryID int(11) NOT NULL,
    BehaviorType varchar(65533) NOT NULL,
    Timestamp datetime NOT NULL
)
ENGINE = OLAP 
DUPLICATE KEY(UserID)
DISTRIBUTED BY HASH(UserID)
PROPERTIES
(
    'replication_num' = '1'
);
```

#### 启动 Broker Load

运行以下命令以启动一个 Broker Load 作业，该作业将数据从示例数据集 `user_behavior_ten_million_rows.parquet` 加载到 `user_behavior` 表：

:::tip

命令中突出显示的部分包含您可能需要更改的设置：

- 设置 `endpoint` 和 `DATA INFILE` 以匹配您的 MinIO 系统。
- 如果您的 MinIO 系统使用 SSL，请将 `enable_ssl` 设置为 `true`。
- 将您的 MinIO access key 和 secret key 替换为 `AAA` 和 `BBB`。

:::

```sql
LOAD LABEL UserBehavior
(
    -- highlight-start
    DATA INFILE("s3://starrocks/user_behavior_ten_million_rows.parquet")
    -- highlight-end
    INTO TABLE user_behavior
 )
 WITH BROKER
 (
    -- highlight-start
    "aws.s3.endpoint" = "http://minio:9000",
    "aws.s3.enable_ssl" = "false",
    "aws.s3.access_key" = "AAAAAAAAAAAAAAAAAAAA",
    "aws.s3.secret_key" = "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
    -- highlight-end
    "aws.s3.use_aws_sdk_default_behavior" = "false",
    "aws.s3.use_instance_profile" = "false",
    "aws.s3.enable_path_style_access" = "true"
 )
PROPERTIES
(
    "timeout" = "72000"
);
```

此作业有四个主要部分：

- `LABEL`: 用于查询导入作业状态的字符串。
- `LOAD` 声明：源 URI、源数据格式和目标表名称。
- `BROKER`: 源的连接详细信息。
- `PROPERTIES`: 超时值和要应用于导入作业的任何其他属性。

有关详细的语法和参数说明，请参见 [BROKER LOAD](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md)。

#### 检查导入进度

您可以从 StarRocks Information Schema 中的 [`loads`](../sql-reference/information_schema/loads.md) 视图查询 Broker Load 作业的进度。此功能从 v3.1 版本开始支持。

```SQL
SELECT * FROM information_schema.loads;
```

有关 `loads` 视图中提供的字段的信息，请参见 [`loads`](../sql-reference/information_schema/loads.md)。

如果您提交了多个导入作业，则可以按与作业关联的 `LABEL` 进行过滤。示例：

```sql
SELECT * FROM information_schema.loads
WHERE LABEL = 'UserBehavior'\G
```

```plaintext
*************************** 1. row ***************************
              JOB_ID: 10176
               LABEL: userbehavior
       DATABASE_NAME: mydatabase
               STATE: FINISHED
            PROGRESS: ETL:100%; LOAD:100%
                TYPE: BROKER
            PRIORITY: NORMAL
           SCAN_ROWS: 10000000
       FILTERED_ROWS: 0
     UNSELECTED_ROWS: 0
           SINK_ROWS: 10000000
            ETL_INFO:
           TASK_INFO: resource:N/A; timeout(s):72000; max_filter_ratio:0.0
         CREATE_TIME: 2023-12-19 23:02:41
      ETL_START_TIME: 2023-12-19 23:02:44
     ETL_FINISH_TIME: 2023-12-19 23:02:44
     LOAD_START_TIME: 2023-12-19 23:02:44
    LOAD_FINISH_TIME: 2023-12-19 23:02:46
         JOB_DETAILS: {"All backends":{"4aeec563-a91e-4c1e-b169-977b660950d1":[10004]},"FileNumber":1,"FileSize":132251298,"InternalTableLoadBytes":311710786,"InternalTableLoadRows":10000000,"ScanBytes":132251298,"ScanRows":10000000,"TaskNumber":1,"Unfinished backends":{"4aeec563-a91e-4c1e-b169-977b660950d1":[]}}
           ERROR_MSG: NULL
        TRACKING_URL: NULL
        TRACKING_SQL: NULL
REJECTED_RECORD_PATH: NULL
1 row in set (0.02 sec)
```

确认导入作业已完成后，您可以检查目标表的一个子集，以查看数据是否已成功加载。示例：

```SQL
SELECT * from user_behavior LIMIT 3;
```

返回以下查询结果，表明数据已成功加载：

```Plaintext
+--------+---------+------------+--------------+---------------------+
| UserID | ItemID  | CategoryID | BehaviorType | Timestamp           |
+--------+---------+------------+--------------+---------------------+
|    142 | 2869980 |    2939262 | pv           | 2017-11-25 03:43:22 |
|    142 | 2522236 |    1669167 | pv           | 2017-11-25 15:14:12 |
|    142 | 3031639 |    3607361 | pv           | 2017-11-25 15:19:25 |
+--------+---------+------------+--------------+---------------------+
```

<!-- ## Use Pipe

Starting from v3.2, StarRocks provides the Pipe loading method, which currently supports only the Parquet and ORC file formats.

### Advantages of Pipe

Pipe is ideal for continuous data loading and large-scale data loading:

- **Large-scale data loading in micro-batches helps reduce the cost of retries caused by data errors.**

  With the help of Pipe, StarRocks enables the efficient loading of a large number of data files with a significant data volume in total. Pipe automatically splits the files based on their number or size, breaking down the load job into smaller, sequential tasks. This approach ensures that errors in one file do not impact the entire load job. The load status of each file is recorded by Pipe, allowing you to easily identify and fix files that contain errors. By minimizing the need for retries due to data errors, this approach helps to reduce costs.

- **Continuous data loading helps reduce manpower.**

  Pipe helps you write new or updated data files to a specific location and continuously load the new data from these files into StarRocks. After you create a Pipe job with `"AUTO_INGEST" = "TRUE"` specified, it will constantly monitor changes to the data files stored in the specified path and automatically load new or updated data from the data files into the destination StarRocks table.

Additionally, Pipe performs file uniqueness checks to help prevent duplicate data loading.During the loading process, Pipe checks the uniqueness of each data file based on the file name and digest. If a file with a specific file name and digest has already been processed by a Pipe job, the Pipe job will skip all subsequent files with the same file name and digest. Note that object storage like MinIO uses `ETag` as file digest.

The load status of each data file is recorded and saved to the `information_schema.pipe_files` view. After a Pipe job associated with the view is deleted, the records about the files loaded in that job will also be deleted.

### Data flow

![Pipe data flow](../_assets/pipe_data_flow.png)

### Differences between Pipe and INSERT+FILES()

A Pipe job is split into one or more transactions based on the size and number of rows in each data file. Users can query the intermediate results during the loading process. In contrast, an INSERT+`FILES()` job is processed as a single transaction, and users are unable to view the data during the loading process.

### File loading sequence

For each Pipe job, StarRocks maintains a file queue, from which it fetches and loads data files as micro-batches. Pipe does not ensure that the data files are loaded in the same order as they are uploaded. Therefore, newer data may be loaded prior to older data.

### Typical example

Note that Pipe is typically used with:

- large datasets
- datasets that are in multiple files
- datasets that grow over time

This example uses only one small file and is only intended to introduce the Pipe functionality. See the [FILES](../sql-reference/sql-functions/table-functions/files.md) and [CREATE PIPE](../sql-reference/sql-statements/loading_unloading/pipe/CREATE_PIPE.md) docs.

#### Create a database and a table

Create a database and switch to it:

```SQL
CREATE DATABASE IF NOT EXISTS mydatabase;
USE mydatabase;
```

Create a table by hand (we recommend that the table have the same schema as the Parquet file you want to load from MinIO):

```SQL
CREATE TABLE user_behavior_replica
(
    UserID int(11) NOT NULL,
    ItemID int(11) NOT NULL,
    CategoryID int(11) NOT NULL,
    BehaviorType varchar(65533) NOT NULL,
    Timestamp datetime NOT NULL
)
ENGINE = OLAP 
DUPLICATE KEY(UserID)
DISTRIBUTED BY HASH(UserID)
PROPERTIES
(
    'replication_num' = '1'
);
```

#### Start a Pipe job

Run the following command to start a Pipe job that loads data from the sample dataset `user_behavior_ten_million_rows.parquet` to the `user_behavior_replica` table:

```sql
CREATE PIPE user_behavior_replica
PROPERTIES
(
    "AUTO_INGEST" = "TRUE"
)
AS
INSERT INTO user_behavior_replica
SELECT * FROM FILES
(
    --highlight-start
    "aws.s3.endpoint" = "http://minio:9000",
    "aws.s3.enable_ssl" = "false",
    "path" = "s3://starrocks/user_behavior_ten_million_rows.parquet",
    "aws.s3.access_key" = "AAAAAAAAAAAAAAAAAAAA",
    "aws.s3.secret_key" = "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
    --highlight-end
    "format" = "parquet",
    "aws.s3.use_aws_sdk_default_behavior" = "false",
    "aws.s3.use_instance_profile" = "false",
    "aws.s3.enable_path_style_access" = "true"
);
```

This job has four main sections:

- `pipe_name`: The name of the pipe. The pipe name must be unique within the database to which the pipe belongs.
- `INSERT_SQL`: The INSERT INTO SELECT FROM FILES statement that is used to load data from the specified source data file to the destination table.
- `PROPERTIES`: A set of optional parameters that specify how to execute the pipe. These include `AUTO_INGEST`, `POLL_INTERVAL`, `BATCH_SIZE`, and `BATCH_FILES`. Specify these properties in the `"key" = "value"` format.

For detailed syntax and parameter descriptions, see [CREATE PIPE](../sql-reference/sql-statements/loading_unloading/pipe/CREATE_PIPE.md).

#### Check load progress

- Query the progress of Pipe jobs by using [SHOW PIPES](../sql-reference/sql-statements/loading_unloading/pipe/SHOW_PIPES.md).

```sql
SHOW PIPES\G
```

```plaintext
*************************** 1. row ***************************
DATABASE_NAME: mydatabase
      PIPE_ID: 10204
    PIPE_NAME: user_behavior_replica
        STATE: RUNNING
   TABLE_NAME: mydatabase.user_behavior_replica
  LOAD_STATUS: {"loadedFiles":1,"loadedBytes":132251298,"loadingFiles":0,"lastLoadedTime":"2023-12-20 03:20:58"}
   LAST_ERROR: NULL
 CREATED_TIME: 2023-12-20 03:20:53
1 row in set (0.00 sec)
```

#### Manage Pipe jobs

You can alter, suspend or resume, drop, or query the pipes you have created and retry to load specific data files. For more information, see [ALTER PIPE](../sql-reference/sql-statements/loading_unloading/pipe/ALTER_PIPE.md), [SUSPEND or RESUME PIPE](../sql-reference/sql-statements/loading_unloading/pipe/SUSPEND_or_RESUME_PIPE.md), [DROP PIPE](../sql-reference/sql-statements/loading_unloading/pipe/DROP_PIPE.md), [SHOW PIPES](../sql-reference/sql-statements/loading_unloading/pipe/SHOW_PIPES.md), and [RETRY FILE](../sql-reference/sql-statements/loading_unloading/pipe/RETRY_FILE.md).
-->