---
displayed_sidebar: docs
---

# 从 HDFS 或云存储加载数据

import InsertPrivNote from '../_assets/commonMarkdown/insertPrivNote.mdx'

StarRocks 提供了基于 MySQL 的 Broker Load 导入方法，可帮助您将大量数据从 HDFS 或云存储导入到 StarRocks 中。

Broker Load 在异步导入模式下运行。提交导入作业后，StarRocks 会异步运行该作业。您需要使用 [SHOW LOAD](../sql-reference/sql-statements/loading_unloading/SHOW_LOAD.md) 语句或 `curl` 命令来检查作业结果。

Broker Load 支持单表导入和多表导入。您可以通过运行一个 Broker Load 作业将一个或多个数据文件导入到一个或多个目标表中。Broker Load 确保每个运行的导入作业在导入多个数据文件时的事务原子性。原子性意味着一个导入作业中多个数据文件的导入必须全部成功或全部失败。不会发生某些数据文件导入成功而其他文件导入失败的情况。

Broker Load 支持在数据导入时进行数据转换，并支持在数据导入期间通过 UPSERT 和 DELETE 操作进行数据更改。有关详细信息，请参见 [在导入时转换数据](../loading/Etl_in_loading.md) 和 [通过导入更改数据](../loading/Load_to_Primary_Key_tables.md)。

<InsertPrivNote />

## 背景信息

在 v2.4 及更早版本中，StarRocks 依赖 Broker 在 StarRocks 集群和外部存储系统之间建立连接，以运行 Broker Load 作业。因此，您需要在导入语句中输入 `WITH BROKER "<broker_name>"` 来指定要使用的 Broker。这被称为“基于 Broker 的导入”。Broker 是一种独立的无状态服务，与文件系统接口集成。借助 Broker，StarRocks 可以访问和读取存储在外部存储系统中的数据文件，并可以使用自己的计算资源来预处理和导入这些数据文件的数据。

从 v2.5 开始，StarRocks 在运行 Broker Load 作业时，不再依赖 Broker 在 StarRocks 集群和外部存储系统之间建立连接。因此，您不再需要在导入语句中指定 Broker，但仍需要保留 `WITH BROKER` 关键字。这被称为“无 Broker 导入”。

当您的数据存储在 HDFS 中时，您可能会遇到无 Broker 导入不起作用的情况。当您的数据存储在多个 HDFS 集群中或您配置了多个 Kerberos 用户时，可能会发生这种情况。在这些情况下，您可以改为使用基于 Broker 的导入。要成功执行此操作，请确保至少部署了一个独立的 Broker 组。有关如何在这些情况下指定身份验证配置和 HA 配置的信息，请参见 [HDFS](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md#hdfs)。

## 支持的数据文件格式

Broker Load 支持以下数据文件格式：

- CSV

- Parquet

- ORC

> **NOTE**
>
> 对于 CSV 数据，请注意以下几点：
>
> - 您可以使用 UTF-8 字符串（例如逗号 (,)、制表符或管道 (|)），其长度不超过 50 字节作为文本分隔符。
> - 空值用 `\N` 表示。例如，一个数据文件包含三列，并且该数据文件中的一条记录在第一列和第三列中包含数据，但在第二列中没有数据。在这种情况下，您需要在第二列中使用 `\N` 来表示空值。这意味着该记录必须编译为 `a,\N,b` 而不是 `a,,b`。`a,,b` 表示该记录的第二列包含一个空字符串。

## 支持的存储系统

Broker Load 支持以下存储系统：

- HDFS

- AWS S3

- Google GCS

- 其他 S3 兼容的存储系统，例如 MinIO

- Microsoft Azure Storage

## 工作原理

在您向 FE 提交导入作业后，FE 会生成一个查询计划，根据可用 BE 的数量和要导入的数据文件的大小将查询计划拆分为多个部分，然后将查询计划的每个部分分配给一个可用的 BE。在导入期间，每个涉及的 BE 从您的 HDFS 或云存储系统中提取数据文件的数据，预处理数据，然后将数据导入到您的 StarRocks 集群中。在所有 BE 完成其查询计划部分后，FE 确定导入作业是否成功。

下图显示了 Broker Load 作业的工作流程。

![Broker Load 的工作流程](../_assets/broker_load_how-to-work_en.png)

## 基本操作

### 创建多表导入作业

本主题以 CSV 为例，介绍如何将多个数据文件导入到多个表中。有关如何导入其他文件格式的数据以及 Broker Load 的语法和参数说明，请参见 [BROKER LOAD](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md)。

请注意，在 StarRocks 中，某些字面量被 SQL 语言用作保留关键字。请勿在 SQL 语句中直接使用这些关键字。如果要在 SQL 语句中使用此类关键字，请将其括在一对反引号 (`) 中。请参见 [关键字](../sql-reference/sql-statements/keywords.md)。

#### 数据示例

1. 在本地文件系统中创建 CSV 文件。

   a. 创建一个名为 `file1.csv` 的 CSV 文件。该文件包含三列，依次表示用户 ID、用户名和用户分数。

      ```Plain
      1,Lily,23
      2,Rose,23
      3,Alice,24
      4,Julia,25
      ```

   b. 创建一个名为 `file2.csv` 的 CSV 文件。该文件包含两列，依次表示城市 ID 和城市名称。

      ```Plain
      200,'Beijing'
      ```

2. 在 StarRocks 数据库 `test_db` 中创建 StarRocks 表。

   > **NOTE**
   >
   > 从 v2.5.7 开始，StarRocks 可以在您创建表或添加分区时自动设置 bucket 数量 (BUCKETS)。您不再需要手动设置 bucket 数量。有关详细信息，请参见 [设置 bucket 数量](../table_design/data_distribution/Data_distribution.md#set-the-number-of-buckets)。

   a. 创建一个名为 `table1` 的主键表。该表包含三列：`id`、`name` 和 `score`，其中 `id` 是主键。

      ```SQL
      CREATE TABLE `table1`
      (
          `id` int(11) NOT NULL COMMENT "user ID",
          `name` varchar(65533) NULL DEFAULT "" COMMENT "user name",
          `score` int(11) NOT NULL DEFAULT "0" COMMENT "user score"
      )
      ENGINE=OLAP
      PRIMARY KEY(`id`)
      DISTRIBUTED BY HASH(`id`);
      ```

   b. 创建一个名为 `table2` 的主键表。该表包含两列：`id` 和 `city`，其中 `id` 是主键。

      ```SQL
      CREATE TABLE `table2`
      (
          `id` int(11) NOT NULL COMMENT "city ID",
          `city` varchar(65533) NULL DEFAULT "" COMMENT "city name"
      )
      ENGINE=OLAP
      PRIMARY KEY(`id`)
      DISTRIBUTED BY HASH(`id`);
      ```

3. 将 `file1.csv` 和 `file2.csv` 上传到 HDFS 集群的 `/user/starrocks/` 路径、AWS S3 bucket `bucket_s3` 的 `input` 文件夹、Google GCS bucket `bucket_gcs` 的 `input` 文件夹、MinIO bucket `bucket_minio` 的 `input` 文件夹以及 Azure Storage 的指定路径。

#### 从 HDFS 加载数据

执行以下语句，将 `file1.csv` 和 `file2.csv` 从 HDFS 集群的 `/user/starrocks` 路径分别加载到 `table1` 和 `table2` 中：

```SQL
LOAD LABEL test_db.label1
(
    DATA INFILE("hdfs://<hdfs_host>:<hdfs_port>/user/starrocks/file1.csv")
    INTO TABLE table1
    COLUMNS TERMINATED BY ","
    (id, name, score)
    ,
    DATA INFILE("hdfs://<hdfs_host>:<hdfs_port>/user/starrocks/file2.csv")
    INTO TABLE table2
    COLUMNS TERMINATED BY ","
    (id, city)
)
WITH BROKER
(
    StorageCredentialParams
)
PROPERTIES
(
    "timeout" = "3600"
);
```

在上面的示例中，`StorageCredentialParams` 表示一组身份验证参数，这些参数因您选择的身份验证方法而异。有关详细信息，请参见 [BROKER LOAD](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md#hdfs)。

#### 从 AWS S3 加载数据

执行以下语句，将 `file1.csv` 和 `file2.csv` 从 AWS S3 bucket `bucket_s3` 的 `input` 文件夹分别加载到 `table1` 和 `table2` 中：

```SQL
LOAD LABEL test_db.label2
(
    DATA INFILE("s3a://bucket_s3/input/file1.csv")
    INTO TABLE table1
    COLUMNS TERMINATED BY ","
    (id, name, score)
    ,
    DATA INFILE("s3a://bucket_s3/input/file2.csv")
    INTO TABLE table2
    COLUMNS TERMINATED BY ","
    (id, city)
)
WITH BROKER
(
    StorageCredentialParams
);
```

> **NOTE**
>
> Broker Load 仅支持根据 S3A 协议访问 AWS S3。因此，当您从 AWS S3 加载数据时，必须将您作为文件路径传递的 S3 URI 中的 `s3://` 替换为 `s3a://`。

在上面的示例中，`StorageCredentialParams` 表示一组身份验证参数，这些参数因您选择的身份验证方法而异。有关详细信息，请参见 [BROKER LOAD](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md#aws-s3)。

从 v3.1 开始，StarRocks 支持通过使用 INSERT 命令和 TABLE 关键字直接从 AWS S3 加载 Parquet 格式或 ORC 格式的文件数据，从而省去了首先创建外部表的麻烦。有关详细信息，请参见 [使用 INSERT 加载数据 > 使用 TABLE 关键字直接从外部源的文件中插入数据](../loading/InsertInto.md#insert-data-directly-from-files-in-an-external-source-using-files)。

#### 从 Google GCS 加载数据

执行以下语句，将 `file1.csv` 和 `file2.csv` 从 Google GCS bucket `bucket_gcs` 的 `input` 文件夹分别加载到 `table1` 和 `table2` 中：

```SQL
LOAD LABEL test_db.label3
(
    DATA INFILE("gs://bucket_gcs/input/file1.csv")
    INTO TABLE table1
    COLUMNS TERMINATED BY ","
    (id, name, score)
    ,
    DATA INFILE("gs://bucket_gcs/input/file2.csv")
    INTO TABLE table2
    COLUMNS TERMINATED BY ","
    (id, city)
)
WITH BROKER
(
    StorageCredentialParams
);
```

> **NOTE**
>
> Broker Load 仅支持根据 gs 协议访问 Google GCS。因此，当您从 Google GCS 加载数据时，必须在您作为文件路径传递的 GCS URI 中包含 `gs://` 作为前缀。

在上面的示例中，`StorageCredentialParams` 表示一组身份验证参数，这些参数因您选择的身份验证方法而异。有关详细信息，请参见 [BROKER LOAD](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md#google-gcs)。

#### 从其他 S3 兼容的存储系统加载数据

以 MinIO 为例。您可以执行以下语句，将 `file1.csv` 和 `file2.csv` 从 MinIO bucket `bucket_minio` 的 `input` 文件夹分别加载到 `table1` 和 `table2` 中：

```SQL
LOAD LABEL test_db.label7
(
    DATA INFILE("s3://bucket_minio/input/file1.csv")
    INTO TABLE table1
    COLUMNS TERMINATED BY ","
    (id, name, score)
    ,
    DATA INFILE("s3://bucket_minio/input/file2.csv")
    INTO TABLE table2
    COLUMNS TERMINATED BY ","
    (id, city)
)
WITH BROKER
(
    StorageCredentialParams
);
```

在上面的示例中，`StorageCredentialParams` 表示一组身份验证参数，这些参数因您选择的身份验证方法而异。有关详细信息，请参见 [BROKER LOAD](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md#other-s3-compatible-storage-system)。

#### 从 Microsoft Azure Storage 加载数据

执行以下语句，将 `file1.csv` 和 `file2.csv` 从 Azure Storage 的指定路径加载：

```SQL
LOAD LABEL test_db.label8
(
    DATA INFILE("wasb[s]://<container>@<storage_account>.blob.core.windows.net/<path>/file1.csv")
    INTO TABLE table1
    COLUMNS TERMINATED BY ","
    (id, name, score)
    ,
    DATA INFILE("wasb[s]://<container>@<storage_account>.blob.core.windows.net/<path>/file2.csv")
    INTO TABLE table2
    COLUMNS TERMINATED BY ","
    (id, city)
)
WITH BROKER
(
    StorageCredentialParams
);
```

> **NOTICE**
  >
  > 从 Azure Storage 加载数据时，您需要根据您使用的访问协议和特定存储服务来确定要使用的前缀。以下示例使用 Blob Storage 作为示例。
  >
  > - 当您从 Blob Storage 加载数据时，您必须根据用于访问存储帐户的协议在文件路径中包含 `wasb://` 或 `wasbs://` 作为前缀：
  >   - 如果您的 Blob Storage 仅允许通过 HTTP 进行访问，请使用 `wasb://` 作为前缀，例如 `wasb://<container>@<storage_account>.blob.core.windows.net/<path>/<file_name>/*`。
  >   - 如果您的 Blob Storage 仅允许通过 HTTPS 进行访问，请使用 `wasbs://` 作为前缀，例如 `wasbs://<container>@<storage_account>.blob.core.windows.net/<path>/<file_name>/*`
  > - 当您从 Data Lake Storage Gen1 加载数据时，您必须在文件路径中包含 `adl://` 作为前缀，例如 `adl://<data_lake_storage_gen1_name>.azuredatalakestore.net/<path>/<file_name>`。
  > - 当您从 Data Lake Storage Gen2 加载数据时，您必须根据用于访问存储帐户的协议在文件路径中包含 `abfs://` 或 `abfss://` 作为前缀：
  >   - 如果您的 Data Lake Storage Gen2 仅允许通过 HTTP 进行访问，请使用 `abfs://` 作为前缀，例如 `abfs://<container>@<storage_account>.dfs.core.windows.net/<file_name>`。
  >   - 如果您的 Data Lake Storage Gen2 仅允许通过 HTTPS 进行访问，请使用 `abfss://` 作为前缀，例如 `abfss://<container>@<storage_account>.dfs.core.windows.net/<file_name>`。

在上面的示例中，`StorageCredentialParams` 表示一组身份验证参数，这些参数因您选择的身份验证方法而异。有关详细信息，请参见 [BROKER LOAD](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md#microsoft-azure-storage)。

#### 查询数据

从 HDFS 集群、AWS S3 bucket 或 Google GCS bucket 加载数据完成后，您可以使用 SELECT 语句查询 StarRocks 表的数据，以验证加载是否成功。

1. 执行以下语句以查询 `table1` 的数据：

   ```SQL
   MySQL [test_db]> SELECT * FROM table1;
   +------+-------+-------+
   | id   | name  | score |
   +------+-------+-------+
   |    1 | Lily  |    23 |
   |    2 | Rose  |    23 |
   |    3 | Alice |    24 |
   |    4 | Julia |    25 |
   +------+-------+-------+
   4 rows in set (0.00 sec)
   ```

2. 执行以下语句以查询 `table2` 的数据：

   ```SQL
   MySQL [test_db]> SELECT * FROM table2;
   +------+--------+
   | id   | city   |
   +------+--------+
   | 200  | Beijing|
   +------+--------+
   4 rows in set (0.01 sec)
   ```

### 创建单表导入作业

您还可以将单个数据文件或指定路径中的所有数据文件加载到单个目标表中。假设您的 AWS S3 bucket `bucket_s3` 包含一个名为 `input` 的文件夹。`input` 文件夹包含多个数据文件，其中一个名为 `file1.csv`。这些数据文件包含与 `table1` 相同的列数，并且来自每个数据文件的列可以按顺序一一映射到来自 `table1` 的列。

要将 `file1.csv` 加载到 `table1` 中，请执行以下语句：

```SQL
LOAD LABEL test_db.label_7
(
    DATA INFILE("s3a://bucket_s3/input/file1.csv")
    INTO TABLE table1
    COLUMNS TERMINATED BY ","
    FORMAT AS "CSV"
)
WITH BROKER 
(
    StorageCredentialParams
);
```

要将 `input` 文件夹中的所有数据文件加载到 `table1` 中，请执行以下语句：

```SQL
LOAD LABEL test_db.label_8
(
    DATA INFILE("s3a://bucket_s3/input/*")
    INTO TABLE table1
    COLUMNS TERMINATED BY ","
    FORMAT AS "CSV"
)
WITH BROKER 
(
    StorageCredentialParams
);
```

在上面的示例中，`StorageCredentialParams` 表示一组身份验证参数，这些参数因您选择的身份验证方法而异。有关详细信息，请参见 [BROKER LOAD](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md#aws-s3)。

### 查看导入作业

Broker Load 允许您使用 SHOW LOAD 语句或 `curl` 命令查看 lob 作业。

#### 使用 SHOW LOAD

有关详细信息，请参见 [SHOW LOAD](../sql-reference/sql-statements/loading_unloading/SHOW_LOAD.md)。

#### 使用 curl

语法如下：

```Bash
curl --location-trusted -u <username>:<password> \
    'http://<fe_host>:<fe_http_port>/api/<database_name>/_load_info?label=<label_name>'
```

> **NOTE**
>
> 如果您使用的帐户未设置密码，则只需输入 `<username>:`。

例如，您可以运行以下命令来查看 `test_db` 数据库中标签为 `label1` 的导入作业的信息：

```Bash
curl --location-trusted -u <username>:<password> \
    'http://<fe_host>:<fe_http_port>/api/test_db/_load_info?label=label1'
```

`curl` 命令以 JSON 对象 `jobInfo` 的形式返回有关具有指定标签的最近执行的导入作业的信息：

```JSON
{"jobInfo":{"dbName":"default_cluster:test_db","tblNames":["table1_simple"],"label":"label1","state":"FINISHED","failMsg":"","trackingUrl":""},"status":"OK","msg":"Success"}%
```

下表描述了 `jobInfo` 中的参数。

| **参数**    | **描述**                                                     |
| ------------- | ------------------------------------------------------------ |
| dbName        | 要将数据加载到的数据库的名称。                               |
| tblNames      | 要将数据加载到的表的名称。                                   |
| label         | 导入作业的标签。                                             |
| state         | 导入作业的状态。有效值：<ul><li>`PENDING`：导入作业正在队列中等待调度。</li><li>`QUEUEING`：导入作业正在队列中等待调度。</li><li>`LOADING`：导入作业正在运行。</li><li>`PREPARED`：事务已提交。</li><li>`FINISHED`：导入作业成功。</li><li>`CANCELLED`：导入作业失败。</li></ul>有关详细信息，请参见 [导入概念](./loading_introduction/loading_concepts.md) 中的“异步导入”部分。 |
| failMsg       | 导入作业失败的原因。如果导入作业的 `state` 值为 `PENDING`、`LOADING` 或 `FINISHED`，则为 `failMsg` 参数返回 `NULL`。如果导入作业的 `state` 值为 `CANCELLED`，则为 `failMsg` 参数返回的值由两部分组成：`type` 和 `msg`。<ul><li>`type` 部分可以是以下任何值：</li><ul><li>`USER_CANCEL`：导入作业已手动取消。</li><li>`ETL_SUBMIT_FAIL`：导入作业未能提交。</li><li>`ETL-QUALITY-UNSATISFIED`：导入作业失败，因为不合格数据的百分比超过了 `max-filter-ratio` 参数的值。</li><li>`LOAD-RUN-FAIL`：导入作业在 `LOADING` 阶段失败。</li><li>`TIMEOUT`：导入作业未在指定的超时时间内完成。</li><li>`UNKNOWN`：导入作业因未知错误而失败。</li></ul><li>`msg` 部分提供了导入失败的详细原因。</li></ul> |
| trackingUrl   | 用于访问在导入作业中检测到的不合格数据的 URL。您可以使用 `curl` 或 `wget` 命令访问该 URL 并获取不合格数据。如果未检测到不合格数据，则为 `trackingUrl` 参数返回 `NULL`。 |
| status        | 导入作业的 HTTP 请求的状态。有效值为：`OK` 和 `Fail`。     |
| msg           | 导入作业的 HTTP 请求的错误信息。                             |

### 取消导入作业

当导入作业未处于 **CANCELLED** 或 **FINISHED** 阶段时，您可以使用 [CANCEL LOAD](../sql-reference/sql-statements/loading_unloading/CANCEL_LOAD.md) 语句取消该作业。

例如，您可以执行以下语句以取消数据库 `test_db` 中标签为 `label1` 的导入作业：

```SQL
CANCEL LOAD
FROM test_db
WHERE LABEL = "label";
```

## 作业拆分和并发运行

一个 Broker Load 作业可以拆分为一个或多个并发运行的任务。一个导入作业中的所有任务都在一个事务中运行。它们必须全部成功或全部失败。StarRocks 根据您在 `LOAD` 语句中如何声明 `data_desc` 来拆分每个导入作业：

- 如果您声明了多个 `data_desc` 参数，每个参数指定一个不同的表，则会生成一个任务来加载每个表的数据。

- 如果您声明了多个 `data_desc` 参数，每个参数指定同一表的不同分区，则会生成一个任务来加载每个分区的数据。

此外，每个任务可以进一步拆分为一个或多个实例，这些实例均匀分布到 StarRocks 集群的 BE 上并并发运行。StarRocks 根据以下 [FE 配置](../administration/management/FE_configuration.md) 拆分每个任务：

- `min_bytes_per_broker_scanner`：每个实例处理的最小数据量。默认量为 64 MB。

- `load_parallel_instance_num`：每个 BE 上每个导入作业中允许的并发实例数。默认数量为 1。
  
  您可以使用以下公式计算单个任务中的实例数：

  **单个任务中的实例数 = min(单个任务要加载的数据量/`min_bytes_per_broker_scanner`，`load_parallel_instance_num` x BE 数量)**

在大多数情况下，每个导入作业只声明一个 `data_desc`，每个导入作业只拆分为一个任务，并且该任务拆分的实例数与 BE 的数量相同。

## 相关配置项

[FE 配置项](../administration/management/FE_configuration.md) `max_broker_load_job_concurrency` 指定了 StarRocks 集群中可以并发运行的最大 Broker Load 作业数。

在 StarRocks v2.4 及更早版本中，如果在特定时间段内提交的 Broker Load 作业总数超过最大数量，则会将过多的作业排队并根据其提交时间进行调度。

自 StarRocks v2.5 以来，如果在特定时间段内提交的 Broker Load 作业总数超过最大数量，则会将过多的作业排队并根据其优先级进行调度。您可以在创建作业时使用 `priority` 参数为作业指定优先级。请参见 [BROKER LOAD](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md#opt_properties)。您还可以使用 [ALTER LOAD](../sql-reference/sql-statements/loading_unloading/ALTER_LOAD.md) 修改处于 **QUEUEING** 或 **LOADING** 状态的现有作业的优先级。