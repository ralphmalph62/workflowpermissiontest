---
displayed_sidebar: docs
---

# 数据导入时转换数据

import InsertPrivNote from '../_assets/commonMarkdown/insertPrivNote.mdx'

StarRocks 支持在数据导入时转换数据。

该功能支持 [Stream Load](../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md) 、[Broker Load](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md) 和 [Routine Load](../sql-reference/sql-statements/loading_unloading/routine_load/CREATE_ROUTINE_LOAD.md) ，但不支持 [Spark Load](../sql-reference/sql-statements/loading_unloading/SPARK_LOAD.md) 。

<InsertPrivNote />

本文档以 CSV 数据为例，介绍如何在数据导入时提取和转换数据。支持的数据文件格式因您选择的导入方式而异。

> **NOTE**
>
> 对于 CSV 数据，您可以使用 UTF-8 字符串（例如逗号 (,)、制表符或管道 (|)）作为文本分隔符，其长度不超过 50 字节。

## 适用场景

当您将数据文件导入到 StarRocks 表中时，数据文件的数据可能无法完全映射到 StarRocks 表的数据。在这种情况下，您无需在将数据加载到 StarRocks 表之前提取或转换数据。StarRocks 可以帮助您在加载期间提取和转换数据：

- 跳过不需要加载的列。
  
  您可以跳过不需要加载的列。此外，如果数据文件的列与 StarRocks 表的列顺序不同，则可以在数据文件和 StarRocks 表之间创建列映射。

- 过滤掉您不想加载的行。
  
  您可以指定过滤条件，StarRocks 会根据这些条件过滤掉您不想加载的行。

- 从原始列生成新列。
  
  生成的列是从数据文件的原始列计算得出的特殊列。您可以将生成的列映射到 StarRocks 表的列。

- 从文件路径提取分区字段值。
  
  如果数据文件是从 Apache Hive™ 生成的，则可以从文件路径提取分区字段值。

## 数据示例

1. 在本地文件系统中创建数据文件。

   a. 创建一个名为 `file1.csv` 的数据文件。该文件由四列组成，依次表示用户 ID、用户性别、事件日期和事件类型。

      ```Plain
      354,female,2020-05-20,1
      465,male,2020-05-21,2
      576,female,2020-05-22,1
      687,male,2020-05-23,2
      ```

   b. 创建一个名为 `file2.csv` 的数据文件。该文件仅由一列组成，表示日期。

      ```Plain
      2020-05-20
      2020-05-21
      2020-05-22
      2020-05-23
      ```

2. 在 StarRocks 数据库 `test_db` 中创建表。

   > **NOTE**
   >
   > 从 v2.5.7 开始，StarRocks 可以在您创建表或添加分区时自动设置 bucket 数量 (BUCKETS)。您不再需要手动设置 bucket 数量。有关详细信息，请参见 [设置 bucket 数量](../table_design/data_distribution/Data_distribution.md#set-the-number-of-buckets)。

   a. 创建一个名为 `table1` 的表，该表由三列组成：`event_date`、`event_type` 和 `user_id`。

      ```SQL
      MySQL [test_db]> CREATE TABLE table1
      (
          `event_date` DATE COMMENT "event date",
          `event_type` TINYINT COMMENT "event type",
          `user_id` BIGINT COMMENT "user ID"
      )
      DISTRIBUTED BY HASH(user_id);
      ```

   b. 创建一个名为 `table2` 的表，该表由四列组成：`date`、`year`、`month` 和 `day`。

      ```SQL
      MySQL [test_db]> CREATE TABLE table2
      (
          `date` DATE COMMENT "date",
          `year` INT COMMENT "year",
          `month` TINYINT COMMENT "month",
          `day` TINYINT COMMENT "day"
      )
      DISTRIBUTED BY HASH(date);
      ```

3. 将 `file1.csv` 和 `file2.csv` 上传到 HDFS 集群的 `/user/starrocks/data/input/` 路径，将 `file1.csv` 的数据发布到 Kafka 集群的 `topic1`，并将 `file2.csv` 的数据发布到 Kafka 集群的 `topic2`。

## 跳过不需要加载的列

您要加载到 StarRocks 表中的数据文件可能包含一些无法映射到 StarRocks 表的任何列的列。在这种情况下，StarRocks 支持仅加载可以从数据文件映射到 StarRocks 表的列。

此功能支持从以下数据源加载数据：

- 本地文件系统

- HDFS 和云存储
  
  > **NOTE**
  >
  > 本节以 HDFS 为例。

- Kafka

在大多数情况下，CSV 文件的列未命名。对于某些 CSV 文件，第一行由列名组成，但 StarRocks 将第一行的内容处理为普通数据，而不是列名。因此，当您加载 CSV 文件时，必须在作业创建语句或命令中**按顺序**临时命名 CSV 文件的列。这些临时命名的列**按名称**映射到 StarRocks 表的列。请注意以下关于数据文件列的几点：

- 可以映射到 StarRocks 表的列，并通过使用 StarRocks 表中列的名称临时命名，这些列的数据将被直接加载。

- 无法映射到 StarRocks 表的列将被忽略，这些列的数据不会被加载。

- 如果某些列可以映射到 StarRocks 表的列，但在作业创建语句或命令中未临时命名，则加载作业会报告错误。

本节以 `file1.csv` 和 `table1` 为例。`file1.csv` 的四列依次临时命名为 `user_id`、`user_gender`、`event_date` 和 `event_type`。在 `file1.csv` 的临时命名列中，`user_id`、`event_date` 和 `event_type` 可以映射到 `table1` 的特定列，而 `user_gender` 无法映射到 `table1` 的任何列。因此，`user_id`、`event_date` 和 `event_type` 将被加载到 `table1` 中，但 `user_gender` 不会被加载。

### 导入数据

#### 从本地文件系统加载数据

如果 `file1.csv` 存储在您的本地文件系统中，请运行以下命令来创建 [Stream Load](../loading/StreamLoad.md) 作业：

```Bash
curl --location-trusted -u <username>:<password> \
    -H "Expect:100-continue" \
    -H "column_separator:," \
    -H "columns: user_id, user_gender, event_date, event_type" \
    -T file1.csv -XPUT \
    http://<fe_host>:<fe_http_port>/api/test_db/table1/_stream_load
```

> **NOTE**
>
> 如果您选择 Stream Load，则必须使用 `columns` 参数临时命名数据文件的列，以在数据文件和 StarRocks 表之间创建列映射。

有关详细的语法和参数说明，请参见 [STREAM LOAD](../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md)。

#### 从 HDFS 集群加载数据

如果 `file1.csv` 存储在您的 HDFS 集群中，请执行以下语句来创建 [Broker Load](../loading/hdfs_load.md) 作业：

```SQL
LOAD LABEL test_db.label1
(
    DATA INFILE("hdfs://<hdfs_host>:<hdfs_port>/user/starrocks/data/input/file1.csv")
    INTO TABLE `table1`
    FORMAT AS "csv"
    COLUMNS TERMINATED BY ","
    (user_id, user_gender, event_date, event_type)
)
WITH BROKER;
```

> **NOTE**
>
> 如果您选择 Broker Load，则必须使用 `column_list` 参数临时命名数据文件的列，以在数据文件和 StarRocks 表之间创建列映射。

有关详细的语法和参数说明，请参见 [BROKER LOAD](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md)。

#### 从 Kafka 集群加载数据

如果 `file1.csv` 的数据发布到 Kafka 集群的 `topic1`，请执行以下语句来创建 [Routine Load](../loading/RoutineLoad.md) 作业：

```SQL
CREATE ROUTINE LOAD test_db.table101 ON table1
    COLUMNS TERMINATED BY ",",
    COLUMNS(user_id, user_gender, event_date, event_type)
FROM KAFKA
(
    "kafka_broker_list" = "<kafka_broker_host>:<kafka_broker_port>",
    "kafka_topic" = "topic1",
    "property.kafka_default_offsets" = "OFFSET_BEGINNING"
);
```

> **NOTE**
>
> 如果您选择 Routine Load，则必须使用 `COLUMNS` 参数临时命名数据文件的列，以在数据文件和 StarRocks 表之间创建列映射。

有关详细的语法和参数说明，请参见 [CREATE ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/CREATE_ROUTINE_LOAD.md)。

### 查询数据

从本地文件系统、HDFS 集群或 Kafka 集群加载数据完成后，查询 `table1` 的数据以验证加载是否成功：

```SQL
MySQL [test_db]> SELECT * FROM table1;
+------------+------------+---------+
| event_date | event_type | user_id |
+------------+------------+---------+
| 2020-05-22 |          1 |     576 |
| 2020-05-20 |          1 |     354 |
| 2020-05-21 |          2 |     465 |
| 2020-05-23 |          2 |     687 |
+------------+------------+---------+
4 rows in set (0.01 sec)
```

## 过滤掉您不想加载的行

当您将数据文件加载到 StarRocks 表中时，您可能不想加载数据文件的特定行。在这种情况下，您可以使用 WHERE 子句来指定要加载的行。StarRocks 会过滤掉所有不满足 WHERE 子句中指定的过滤条件的行。

此功能支持从以下数据源加载数据：

- 本地文件系统

- HDFS 和云存储
  > **NOTE**
  >
  > 本节以 HDFS 为例。

- Kafka

本节以 `file1.csv` 和 `table1` 为例。如果您只想将 `file1.csv` 中事件类型为 `1` 的行加载到 `table1` 中，则可以使用 WHERE 子句来指定过滤条件 `event_type = 1`。

### 导入数据

#### 从本地文件系统加载数据

如果 `file1.csv` 存储在您的本地文件系统中，请运行以下命令来创建 [Stream Load](../loading/StreamLoad.md) 作业：

```Bash
curl --location-trusted -u <username>:<password> \
    -H "Expect:100-continue" \
    -H "column_separator:," \
    -H "columns: user_id, user_gender, event_date, event_type" \
    -H "where: event_type=1" \
    -T file1.csv -XPUT \
    http://<fe_host>:<fe_http_port>/api/test_db/table1/_stream_load
```

有关详细的语法和参数说明，请参见 [STREAM LOAD](../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md)。

#### 从 HDFS 集群加载数据

如果 `file1.csv` 存储在您的 HDFS 集群中，请执行以下语句来创建 [Broker Load](../loading/hdfs_load.md) 作业：

```SQL
LOAD LABEL test_db.label2
(
    DATA INFILE("hdfs://<hdfs_host>:<hdfs_port>/user/starrocks/data/input/file1.csv")
    INTO TABLE `table1`
    FORMAT AS "csv"
    COLUMNS TERMINATED BY ","
    (user_id, user_gender, event_date, event_type)
    WHERE event_type = 1
)
WITH BROKER;
```

有关详细的语法和参数说明，请参见 [BROKER LOAD](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md)。

#### 从 Kafka 集群加载数据

如果 `file1.csv` 的数据发布到 Kafka 集群的 `topic1`，请执行以下语句来创建 [Routine Load](../loading/RoutineLoad.md) 作业：

```SQL
CREATE ROUTINE LOAD test_db.table102 ON table1
COLUMNS TERMINATED BY ",",
COLUMNS (user_id, user_gender, event_date, event_type),
WHERE event_type = 1
FROM KAFKA
(
    "kafka_broker_list" = "<kafka_broker_host>:<kafka_broker_port>",
    "kafka_topic" = "topic1",
    "property.kafka_default_offsets" = "OFFSET_BEGINNING"
);
```

有关详细的语法和参数说明，请参见 [CREATE ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/CREATE_ROUTINE_LOAD.md)。

### 查询数据

从本地文件系统、HDFS 集群或 Kafka 集群加载数据完成后，查询 `table1` 的数据以验证加载是否成功：

```SQL
MySQL [test_db]> SELECT * FROM table1;
+------------+------------+---------+
| event_date | event_type | user_id |
+------------+------------+---------+
| 2020-05-20 |          1 |     354 |
| 2020-05-22 |          1 |     576 |
+------------+------------+---------+
2 rows in set (0.01 sec)
```

## 从原始列生成新列

当您将数据文件加载到 StarRocks 表中时，数据文件的某些数据可能需要转换后才能加载到 StarRocks 表中。在这种情况下，您可以使用作业创建命令或语句中的函数或表达式来实现数据转换。

此功能支持从以下数据源加载数据：

- 本地文件系统

- HDFS 和云存储
  > **NOTE**
  >
  > 本节以 HDFS 为例。

- Kafka

本节以 `file2.csv` 和 `table2` 为例。`file2.csv` 仅由一列组成，表示日期。您可以使用 [year](../sql-reference/sql-functions/date-time-functions/year.md) 、[month](../sql-reference/sql-functions/date-time-functions/month.md) 和 [day](../sql-reference/sql-functions/date-time-functions/day.md) 函数从 `file2.csv` 中的每个日期提取年、月和日，并将提取的数据加载到 `table2` 的 `year`、`month` 和 `day` 列中。

### 导入数据

#### 从本地文件系统加载数据

如果 `file2.csv` 存储在您的本地文件系统中，请运行以下命令来创建 [Stream Load](../loading/StreamLoad.md) 作业：

```Bash
curl --location-trusted -u <username>:<password> \
    -H "Expect:100-continue" \
    -H "column_separator:," \
    -H "columns:date,year=year(date),month=month(date),day=day(date)" \
    -T file2.csv -XPUT \
    http://<fe_host>:<fe_http_port>/api/test_db/table2/_stream_load
```

> **NOTE**
>
> - 在 `columns` 参数中，您必须首先临时命名数据文件的**所有列**，然后临时命名要从数据文件的原始列生成的新列。如前面的示例所示，`file2.csv` 的唯一列临时命名为 `date`，然后调用 `year=year(date)`、`month=month(date)` 和 `day=day(date)` 函数来生成三个新列，这些新列临时命名为 `year`、`month` 和 `day`。
>
> - Stream Load 不支持 `column_name = function(column_name)`，但支持 `column_name = function(column_name)`。

有关详细的语法和参数说明，请参见 [STREAM LOAD](../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md)。

#### 从 HDFS 集群加载数据

如果 `file2.csv` 存储在您的 HDFS 集群中，请执行以下语句来创建 [Broker Load](../loading/hdfs_load.md) 作业：

```SQL
LOAD LABEL test_db.label3
(
    DATA INFILE("hdfs://<hdfs_host>:<hdfs_port>/user/starrocks/data/input/file2.csv")
    INTO TABLE `table2`
    FORMAT AS "csv"
    COLUMNS TERMINATED BY ","
    (date)
    SET(year=year(date), month=month(date), day=day(date))
)
WITH BROKER;
```

> **NOTE**
>
> 您必须首先使用 `column_list` 参数临时命名数据文件的**所有列**，然后使用 SET 子句临时命名要从数据文件的原始列生成的新列。如前面的示例所示，`file2.csv` 的唯一列在 `column_list` 参数中临时命名为 `date`，然后在 SET 子句中调用 `year=year(date)`、`month=month(date)` 和 `day=day(date)` 函数来生成三个新列，这些新列临时命名为 `year`、`month` 和 `day`。

有关详细的语法和参数说明，请参见 [BROKER LOAD](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md)。

#### 从 Kafka 集群加载数据

如果 `file2.csv` 的数据发布到 Kafka 集群的 `topic2`，请执行以下语句来创建 [Routine Load](../loading/RoutineLoad.md) 作业：

```SQL
CREATE ROUTINE LOAD test_db.table201 ON table2
    COLUMNS TERMINATED BY ",",
    COLUMNS(date,year=year(date),month=month(date),day=day(date))
FROM KAFKA
(
    "kafka_broker_list" = "<kafka_broker_host>:<kafka_broker_port>",
    "kafka_topic" = "topic2",
    "property.kafka_default_offsets" = "OFFSET_BEGINNING"
);
```

> **NOTE**
>
> 在 `COLUMNS` 参数中，您必须首先临时命名数据文件的**所有列**，然后临时命名要从数据文件的原始列生成的新列。如前面的示例所示，`file2.csv` 的唯一列临时命名为 `date`，然后调用 `year=year(date)`、`month=month(date)` 和 `day=day(date)` 函数来生成三个新列，这些新列临时命名为 `year`、`month` 和 `day`。

有关详细的语法和参数说明，请参见 [CREATE ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/CREATE_ROUTINE_LOAD.md)。

### 查询数据

从本地文件系统、HDFS 集群或 Kafka 集群加载数据完成后，查询 `table2` 的数据以验证加载是否成功：

```SQL
MySQL [test_db]> SELECT * FROM table2;
+------------+------+-------+------+
| date       | year | month | day  |
+------------+------+-------+------+
| 2020-05-20 | 2020 |  5    | 20   |
| 2020-05-21 | 2020 |  5    | 21   |
| 2020-05-22 | 2020 |  5    | 22   |
| 2020-05-23 | 2020 |  5    | 23   |
+------------+------+-------+------+
4 rows in set (0.01 sec)
```

## 从文件路径提取分区字段值

如果您指定的文件路径包含分区字段，则可以使用 `COLUMNS FROM PATH AS` 参数来指定要从文件路径提取的分区字段。文件路径中的分区字段等同于数据文件中的列。仅当您从 HDFS 集群加载数据时，才支持 `COLUMNS FROM PATH AS` 参数。

例如，您要加载以下四个从 Hive 生成的数据文件：

```Plain
/user/starrocks/data/input/date=2020-05-20/data
1,354
/user/starrocks/data/input/date=2020-05-21/data
2,465
/user/starrocks/data/input/date=2020-05-22/data
1,576
/user/starrocks/data/input/date=2020-05-23/data
2,687
```

这四个数据文件存储在 HDFS 集群的 `/user/starrocks/data/input/` 路径中。这些数据文件中的每一个都按分区字段 `date` 分区，并由两列组成，依次表示事件类型和用户 ID。

### 从 HDFS 集群加载数据

执行以下语句以创建 [Broker Load](../loading/hdfs_load.md) 作业，该作业使您可以从 `/user/starrocks/data/input/` 文件路径提取 `date` 分区字段值，并使用通配符 (*) 来指定您要将文件路径中的所有数据文件加载到 `table1`：

```SQL
LOAD LABEL test_db.label4
(
    DATA INFILE("hdfs://<fe_host>:<fe_http_port>/user/starrocks/data/input/date=*/*")
    INTO TABLE `table1`
    FORMAT AS "csv"
    COLUMNS TERMINATED BY ","
    (event_type, user_id)
    COLUMNS FROM PATH AS (date)
    SET(event_date = date)
)
WITH BROKER;
```

> **NOTE**
>
> 在前面的示例中，指定文件路径中的 `date` 分区字段等同于 `table1` 的 `event_date` 列。因此，您需要使用 SET 子句将 `date` 分区字段映射到 `event_date` 列。如果指定文件路径中的分区字段与 StarRocks 表的列同名，则无需使用 SET 子句创建映射。

有关详细的语法和参数说明，请参见 [BROKER LOAD](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md)。

### 查询数据

从 HDFS 集群加载数据完成后，查询 `table1` 的数据以验证加载是否成功：

```SQL
MySQL [test_db]> SELECT * FROM table1;
+------------+------------+---------+
| event_date | event_type | user_id |
+------------+------------+---------+
| 2020-05-22 |          1 |     576 |
| 2020-05-20 |          1 |     354 |
| 2020-05-21 |          2 |     465 |
| 2020-05-23 |          2 |     687 |
+------------+------------+---------+
4 rows in set (0.01 sec)
```