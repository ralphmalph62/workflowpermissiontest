---
displayed_sidebar: docs
toc_max_heading_level: 4
keywords: ['Broker Load']
---

# 从 GCS 导入数据

import InsertPrivNote from '../_assets/commonMarkdown/insertPrivNote.mdx'

StarRocks 提供了以下从 GCS 导入数据的选项：

- 使用 [INSERT](../sql-reference/sql-statements/loading_unloading/INSERT.md) + [`FILES()`](../sql-reference/sql-functions/table-functions/files.md) 进行同步导入
- 使用 [Broker Load](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md) 进行异步导入

每个选项都有其自身的优势，以下各节将详细介绍。

在大多数情况下，我们建议您使用 INSERT+`FILES()` 方法，该方法更易于使用。

但是，INSERT+`FILES()` 方法目前仅支持 Parquet、ORC 和 CSV 文件格式。因此，如果您需要导入其他文件格式的数据（如 JSON），或者[在数据导入期间执行数据更改（如 DELETE）](../loading/Load_to_Primary_Key_tables.md)，则可以采用 Broker Load。

## 前提条件

### 准备源数据

确保要加载到 StarRocks 中的源数据已正确存储在 GCS bucket 中。您还可以考虑数据和数据库的位置，因为当您的 bucket 和 StarRocks 集群位于同一区域时，数据传输成本会低得多。

在本主题中，我们为您提供了一个 GCS bucket 中的示例数据集 `gs://starrocks-samples/user_behavior_ten_million_rows.parquet`。您可以使用任何有效的凭据访问该数据集，因为任何 GCP 用户都可以读取该对象。

### 检查权限

<InsertPrivNote />

### 收集身份验证详细信息

本主题中的示例使用基于服务帐户的身份验证。要实践基于 IAM 用户的身份验证，您需要收集有关以下 GCS 资源的信息：

- 存储数据的 GCS bucket。
- GCS 对象键（对象名称），如果访问 bucket 中的特定对象。请注意，如果您的 GCS 对象存储在子文件夹中，则对象键可以包含前缀。
- GCS bucket 所属的 GCS 区域。
- 您的 Google Cloud 服务帐户的 `private_ key_id`、`private_key` 和 `client_email`。

有关所有可用身份验证方法的信息，请参阅 [验证到 Google Cloud Storage 的身份](../integrations/authenticate_to_gcs.md)。

## 使用 INSERT+FILES()

此方法从 v3.2 开始可用，目前仅支持 Parquet、ORC 和 CSV（从 v3.3.0 开始）文件格式。

### INSERT+FILES() 的优势

`FILES()` 可以读取存储在云存储中的文件，基于您指定的路径相关属性，推断文件中数据的表结构，然后将文件中的数据作为数据行返回。

使用 `FILES()`，您可以：

- 使用 [SELECT](../sql-reference/sql-statements/table_bucket_part_index/SELECT.md) 直接从 GCS 查询数据。
- 使用 [CREATE TABLE AS SELECT](../sql-reference/sql-statements/table_bucket_part_index/CREATE_TABLE_AS_SELECT.md) (CTAS) 创建和加载表。
- 使用 [INSERT](../sql-reference/sql-statements/loading_unloading/INSERT.md) 将数据加载到现有表中。

### 典型示例

#### 使用 SELECT 直接从 GCS 查询

使用 SELECT+`FILES()` 直接从 GCS 查询可以在创建表之前很好地预览数据集的内容。例如：

- 在不存储数据的情况下获取数据集的预览。
- 查询最小值和最大值，并确定要使用的数据类型。
- 检查 `NULL` 值。

以下示例查询示例数据集 `gs://starrocks-samples/user_behavior_ten_million_rows.parquet`：

```SQL
SELECT * FROM FILES
(
    "path" = "gs://starrocks-samples/user_behavior_ten_million_rows.parquet",
    "format" = "parquet",
    "gcp.gcs.service_account_email" = "sampledatareader@xxxxx-xxxxxx-000000.iam.gserviceaccount.com",
    "gcp.gcs.service_account_private_key_id" = "baaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "gcp.gcs.service_account_private_key" = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
)
LIMIT 3;
```

> **NOTE**
>
> 将上述命令中的凭据替换为您自己的凭据。可以使用任何有效的服务帐户电子邮件、密钥和密码，因为任何经过 GCP 身份验证的用户都可以读取该对象。

系统返回类似于以下的查询结果：

```Plain
+--------+---------+------------+--------------+---------------------+
| UserID | ItemID  | CategoryID | BehaviorType | Timestamp           |
+--------+---------+------------+--------------+---------------------+
| 543711 |  829192 |    2355072 | pv           | 2017-11-27 08:22:37 |
| 543711 | 2056618 |    3645362 | pv           | 2017-11-27 10:16:46 |
| 543711 | 1165492 |    3645362 | pv           | 2017-11-27 10:17:00 |
+--------+---------+------------+--------------+---------------------+
```

> **NOTE**
>
> 请注意，上面返回的列名由 Parquet 文件提供。

#### 使用 CTAS 创建和加载表

这是前一个示例的延续。先前的查询包装在 CREATE TABLE AS SELECT (CTAS) 中，以使用模式推断自动执行表创建。这意味着 StarRocks 将推断表模式，创建您想要的表，然后将数据加载到表中。当使用带有 Parquet 文件的 `FILES()` 表函数时，由于 Parquet 格式包含列名，因此不需要列名和类型来创建表。

> **NOTE**
>
> 使用模式推断时，CREATE TABLE 的语法不允许设置副本数。如果您使用的是 StarRocks 存算一体集群，请在创建表之前设置副本数。以下示例适用于具有三个副本的系统：
>
> ```SQL
> ADMIN SET FRONTEND CONFIG ('default_replication_num' = "3");
> ```

创建一个数据库并切换到它：

```SQL
CREATE DATABASE IF NOT EXISTS mydatabase;
USE mydatabase;
```

使用 CTAS 创建一个表，并将示例数据集 `gs://starrocks-samples/user_behavior_ten_million_rows.parquet` 的数据加载到该表中：

```SQL
CREATE TABLE user_behavior_inferred AS
SELECT * FROM FILES
(
    "path" = "gs://starrocks-samples/user_behavior_ten_million_rows.parquet",
    "format" = "parquet",
    "gcp.gcs.service_account_email" = "sampledatareader@xxxxx-xxxxxx-000000.iam.gserviceaccount.com",
    "gcp.gcs.service_account_private_key_id" = "baaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "gcp.gcs.service_account_private_key" = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
);
```

> **NOTE**
>
> 将上述命令中的凭据替换为您自己的凭据。可以使用任何有效的服务帐户电子邮件、密钥和密码，因为任何经过 GCP 身份验证的用户都可以读取该对象。

创建表后，您可以使用 [DESCRIBE](../sql-reference/sql-statements/table_bucket_part_index/DESCRIBE.md) 查看其模式：

```SQL
DESCRIBE user_behavior_inferred;
```

系统返回类似于以下的查询结果：

```Plain
+--------------+-----------+------+-------+---------+-------+
| Field        | Type      | Null | Key   | Default | Extra |
+--------------+-----------+------+-------+---------+-------+
| UserID       | bigint    | YES  | true  | NULL    |       |
| ItemID       | bigint    | YES  | true  | NULL    |       |
| CategoryID   | bigint    | YES  | true  | NULL    |       |
| BehaviorType | varbinary | YES  | false | NULL    |       |
| Timestamp    | varbinary | YES  | false | NULL    |       |
+--------------+-----------+------+-------+---------+-------+
```

查询表以验证数据是否已加载到其中。示例：

```SQL
SELECT * from user_behavior_inferred LIMIT 3;
```

返回以下查询结果，表明数据已成功加载：

```Plain
+--------+--------+------------+--------------+---------------------+
| UserID | ItemID | CategoryID | BehaviorType | Timestamp           |
+--------+--------+------------+--------------+---------------------+
|     84 | 162325 |    2939262 | pv           | 2017-12-02 05:41:41 |
|     84 | 232622 |    4148053 | pv           | 2017-11-27 04:36:10 |
|     84 | 595303 |     903809 | pv           | 2017-11-26 08:03:59 |
+--------+--------+------------+--------------+---------------------+
```

#### 使用 INSERT 加载到现有表中

您可能想要自定义要插入的表，例如：

- 列数据类型、可为空设置或默认值
- 键类型和列
- 数据分区和分桶

> **NOTE**
>
> 创建最有效的表结构需要了解数据的使用方式和列的内容。本主题不涵盖表设计。有关表设计的信息，请参阅 [表类型](../table_design/StarRocks_table_design.md)。

在此示例中，我们基于对表的查询方式和 Parquet 文件中的数据的了解来创建表。对 Parquet 文件中的数据的了解可以通过直接在 GCS 中查询文件来获得。

- 由于 GCS 中数据集的查询表明 `Timestamp` 列包含与 VARBINARY 数据类型匹配的数据，因此在以下 DDL 中指定了列类型。
- 通过查询 GCS 中的数据，您可以发现数据集中没有 `NULL` 值，因此 DDL 不会将任何列设置为可为空。
- 根据对预期查询类型的了解，排序键和分桶列设置为列 `UserID`。您的用例可能与此数据不同，因此您可能会决定除了 `UserID` 之外或代替 `UserID` 使用 `ItemID` 作为排序键。

创建一个数据库并切换到它：

```SQL
CREATE DATABASE IF NOT EXISTS mydatabase;
USE mydatabase;
```

手动创建一个表（我们建议该表具有与要从 GCS 加载的 Parquet 文件相同的模式）：

```SQL
CREATE TABLE user_behavior_declared
(
    UserID int(11),
    ItemID int(11),
    CategoryID int(11),
    BehaviorType varchar(65533),
    Timestamp varbinary
)
ENGINE = OLAP 
DUPLICATE KEY(UserID)
DISTRIBUTED BY HASH(UserID);
```

显示模式，以便您可以将其与 `FILES()` 表函数生成的推断模式进行比较：

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
| Timestamp    | varbinary      | NO   | false | NULL    |       |
+--------------+----------------+------+-------+---------+-------+
5 rows in set (0.00 sec)
```

:::tip

将您刚刚创建的模式与之前使用 `FILES()` 表函数推断的模式进行比较。查看：

- 数据类型
- 可为空性
- 键字段

为了更好地控制目标表的模式并获得更好的查询性能，我们建议您在生产环境中手动指定表模式。

:::

创建表后，您可以使用 INSERT INTO SELECT FROM FILES() 加载它：

```SQL
INSERT INTO user_behavior_declared
  SELECT * FROM FILES
  (
    "path" = "gs://starrocks-samples/user_behavior_ten_million_rows.parquet",
    "format" = "parquet",
    "gcp.gcs.service_account_email" = "sampledatareader@xxxxx-xxxxxx-000000.iam.gserviceaccount.com",
    "gcp.gcs.service_account_private_key_id" = "baaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "gcp.gcs.service_account_private_key" = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
);
```

> **NOTE**
>
> 将上述命令中的凭据替换为您自己的凭据。可以使用任何有效的服务帐户电子邮件、密钥和密码，因为任何经过 GCP 身份验证的用户都可以读取该对象。

加载完成后，您可以查询表以验证数据是否已加载到其中。示例：

```SQL
SELECT * from user_behavior_declared LIMIT 3;
```

系统返回类似于以下的查询结果，表明数据已成功加载：

```Plain
+--------+---------+------------+--------------+---------------------+
| UserID | ItemID  | CategoryID | BehaviorType | Timestamp           |
+--------+---------+------------+--------------+---------------------+
|    142 | 2869980 |    2939262 | pv           | 2017-11-25 03:43:22 |
|    142 | 2522236 |    1669167 | pv           | 2017-11-25 15:14:12 |
|    142 | 3031639 |    3607361 | pv           | 2017-11-25 15:19:25 |
+--------+---------+------------+--------------+---------------------+
```

#### 检查导入进度

您可以从 StarRocks Information Schema 中的 [`loads`](../sql-reference/information_schema/loads.md) 视图查询 INSERT 作业的进度。此功能从 v3.1 开始受支持。示例：

```SQL
SELECT * FROM information_schema.loads ORDER BY JOB_ID DESC;
```

有关 `loads` 视图中提供的字段的信息，请参阅 [`loads`](../sql-reference/information_schema/loads.md)。

如果您提交了多个导入作业，则可以按与该作业关联的 `LABEL` 进行筛选。示例：

```SQL
SELECT * FROM information_schema.loads WHERE LABEL = 'insert_f3fc2298-a553-11ee-92f4-00163e0842bd' \G
*************************** 1. row ***************************
              JOB_ID: 10193
               LABEL: insert_f3fc2298-a553-11ee-92f4-00163e0842bd
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
         CREATE_TIME: 2023-12-28 15:37:38
      ETL_START_TIME: 2023-12-28 15:37:38
     ETL_FINISH_TIME: 2023-12-28 15:37:38
     LOAD_START_TIME: 2023-12-28 15:37:38
    LOAD_FINISH_TIME: 2023-12-28 15:39:35
         JOB_DETAILS: {"All backends":{"f3fc2298-a553-11ee-92f4-00163e0842bd":[10120]},"FileNumber":0,"FileSize":0,"InternalTableLoadBytes":581730322,"InternalTableLoadRows":10000000,"ScanBytes":581574034,"ScanRows":10000000,"TaskNumber":1,"Unfinished backends":{"f3fc2298-a553-11ee-92f4-00163e0842bd":[]}}
           ERROR_MSG: NULL
        TRACKING_URL: NULL
        TRACKING_SQL: NULL
REJECTED_RECORD_PATH: NULL
```

> **NOTE**
>
> INSERT 是一个同步命令。如果 INSERT 作业仍在运行，您需要打开另一个会话来检查其执行状态。

## 使用 Broker Load

异步 Broker Load 进程处理与 GCS 的连接、提取数据以及将数据存储在 StarRocks 中。

此方法支持以下文件格式：

- Parquet
- ORC
- CSV
- JSON（从 v3.2.3 开始支持）

### Broker Load 的优势

- Broker Load 在后台运行，客户端无需保持连接即可继续作业。
- Broker Load 是长时间运行作业的首选，默认超时时间为 4 小时。
- 除了 Parquet 和 ORC 文件格式外，Broker Load 还支持 CSV 文件格式和 JSON 文件格式（从 v3.2.3 开始支持 JSON 文件格式）。

### 数据流

![Broker Load 的工作流程](../_assets/broker_load_how-to-work_en.png)

1. 用户创建一个导入作业。
2. 前端 (FE) 创建一个查询计划，并将该计划分发到后端节点 (BEs) 或计算节点 (CNs)。
3. BE 或 CN 从源中提取数据，并将数据加载到 StarRocks 中。

### 典型示例

创建一个表，启动一个从 GCS 提取示例数据集 `gs://starrocks-samples/user_behavior_ten_million_rows.parquet` 的导入进程，并验证数据加载的进度和成功。

#### 创建数据库和表

创建一个数据库并切换到它：

```SQL
CREATE DATABASE IF NOT EXISTS mydatabase;
USE mydatabase;
```

手动创建一个表（我们建议该表具有与要从 GCS 加载的 Parquet 文件相同的模式）：

```SQL
CREATE TABLE user_behavior
(
    UserID int(11),
    ItemID int(11),
    CategoryID int(11),
    BehaviorType varchar(65533),
    Timestamp varbinary
)
ENGINE = OLAP 
DUPLICATE KEY(UserID)
DISTRIBUTED BY HASH(UserID);
```

#### 启动 Broker Load

运行以下命令以启动一个 Broker Load 作业，该作业将数据从示例数据集 `gs://starrocks-samples/user_behavior_ten_million_rows.parquet` 加载到 `user_behavior` 表：

```SQL
LOAD LABEL user_behavior
(
    DATA INFILE("gs://starrocks-samples/user_behavior_ten_million_rows.parquet")
    INTO TABLE user_behavior
    FORMAT AS "parquet"
 )
 WITH BROKER
 (
 
    "gcp.gcs.service_account_email" = "sampledatareader@xxxxx-xxxxxx-000000.iam.gserviceaccount.com",
    "gcp.gcs.service_account_private_key_id" = "baaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "gcp.gcs.service_account_private_key" = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
 )
PROPERTIES
(
    "timeout" = "72000"
);
```

> **NOTE**
>
> 将上述命令中的凭据替换为您自己的凭据。可以使用任何有效的服务帐户电子邮件、密钥和密码，因为任何经过 GCP 身份验证的用户都可以读取该对象。

此作业有四个主要部分：

- `LABEL`: 查询导入作业状态时使用的字符串。
- `LOAD` 声明：源 URI、源数据格式和目标表名称。
- `BROKER`: 源的连接详细信息。
- `PROPERTIES`: 超时值和要应用于导入作业的任何其他属性。

有关详细的语法和参数说明，请参阅 [BROKER LOAD](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md)。

#### 检查导入进度

您可以从 StarRocks Information Schema 中的 [`loads`](../sql-reference/information_schema/loads.md) 视图查询 INSERT 作业的进度。此功能从 v3.1 开始受支持。

```SQL
SELECT * FROM information_schema.loads;
```

有关 `loads` 视图中提供的字段的信息，请参阅 [`loads`](../sql-reference/information_schema/loads.md)。

如果您提交了多个导入作业，则可以按与该作业关联的 `LABEL` 进行筛选。示例：

```SQL
SELECT * FROM information_schema.loads WHERE LABEL = 'user_behavior';
```

在下面的输出中，`user_behavior` 导入作业有两个条目：

- 第一个记录显示 `CANCELLED` 状态。滚动到 `ERROR_MSG`，您可以看到该作业由于 `listPath failed` 而失败。
- 第二个记录显示 `FINISHED` 状态，这意味着该作业已成功。

```Plain
JOB_ID|LABEL                                      |DATABASE_NAME|STATE    |PROGRESS           |TYPE  |PRIORITY|SCAN_ROWS|FILTERED_ROWS|UNSELECTED_ROWS|SINK_ROWS|ETL_INFO|TASK_INFO                                           |CREATE_TIME        |ETL_START_TIME     |ETL_FINISH_TIME    |LOAD_START_TIME    |LOAD_FINISH_TIME   |JOB_DETAILS                                                                                                                                                                                                                                                    |ERROR_MSG                             |TRACKING_URL|TRACKING_SQL|REJECTED_RECORD_PATH|
------+-------------------------------------------+-------------+---------+-------------------+------+--------+---------+-------------+---------------+---------+--------+----------------------------------------------------+-------------------+-------------------+-------------------+-------------------+-------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+--------------------------------------+------------+------------+--------------------+
 10121|user_behavior                              |mydatabase   |CANCELLED|ETL:N/A; LOAD:N/A  |BROKER|NORMAL  |        0|            0|              0|        0|        |resource:N/A; timeout(s):72000; max_filter_ratio:0.0|2023-08-10 14:59:30|                   |                   |                   |2023-08-10 14:59:34|{"All backends":{},"FileNumber":0,"FileSize":0,"InternalTableLoadBytes":0,"InternalTableLoadRows":0,"ScanBytes":0,"ScanRows":0,"TaskNumber":0,"Unfinished backends":{}}                                                                                        |type:ETL_RUN_FAIL; msg:listPath failed|            |            |                    |
 10106|user_behavior                              |mydatabase   |FINISHED |ETL:100%; LOAD:100%|BROKER|NORMAL  | 86953525|            0|              0| 86953525|        |resource:N/A; timeout(s):72000; max_filter_ratio:0.0|2023-08-10 14:50:15|2023-08-10 14:50:19|2023-08-10 14:50:19|2023-08-10 14:50:19|2023-08-10 14:55:10|{"All backends":{"a5fe5e1d-d7d0-4826-ba99-c7348f9a5f2f":[10004]},"FileNumber":1,"FileSize":1225637388,"InternalTableLoadBytes":2710603082,"InternalTableLoadRows":86953525,"ScanBytes":1225637388,"ScanRows":86953525,"TaskNumber":1,"Unfinished backends":{"a5|                                      |            |            |                    |
```

确认导入作业已完成后，您可以检查目标表的一个子集，以查看数据是否已成功加载。示例：

```SQL
SELECT * from user_behavior LIMIT 3;
```

系统返回类似于以下的查询结果，表明数据已成功加载：

```Plain
+--------+---------+------------+--------------+---------------------+
| UserID | ItemID  | CategoryID | BehaviorType | Timestamp           |
+--------+---------+------------+--------------+---------------------+
|    142 | 2869980 |    2939262 | pv           | 2017-11-25 03:43:22 |
|    142 | 2522236 |    1669167 | pv           | 2017-11-25 15:14:12 |
|    142 | 3031639 |    3607361 | pv           | 2017-11-25 15:19:25 |
+--------+---------+------------+--------------+---------------------+