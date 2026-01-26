---
displayed_sidebar: docs
---

# 使用 INSERT 导入数据

import InsertPrivNote from '../_assets/commonMarkdown/insertPrivNote.mdx'

本主题介绍如何使用 SQL 语句 INSERT 将数据导入到 StarRocks 中。

与 MySQL 和许多其他数据库管理系统类似，StarRocks 支持使用 INSERT 将数据导入到内表。您可以使用 VALUES 子句直接插入一行或多行，以测试函数或 DEMO。您还可以通过查询将数据从 [外部表](../data_source/External_table.md) 导入到内表。从 StarRocks v3.1 开始，您可以使用 INSERT 命令和表函数 [FILES()](../sql-reference/sql-functions/table-functions/files.md) 直接从云存储上的文件导入数据。

StarRocks v2.4 进一步支持使用 INSERT OVERWRITE 将数据覆盖到表中。INSERT OVERWRITE 语句集成了以下操作来实现覆盖功能：

1. 根据存储原始数据的分区创建临时分区。
2. 将数据插入到临时分区中。
3. 将原始分区与临时分区交换。

> **NOTE**
>
> 如果您需要在覆盖数据之前验证数据，可以使用上述步骤覆盖数据，并在交换分区之前对其进行验证，而不是使用 INSERT OVERWRITE。

从 v3.4.0 开始，StarRocks 支持一种新的语义 - 用于分区表的 INSERT OVERWRITE 的动态覆盖。有关更多信息，请参见 [动态覆盖](#dynamic-overwrite)。

## 注意事项

- 您只能通过在 MySQL 客户端中按 **Ctrl** 和 **C** 键来取消同步 INSERT 事务。
- 您可以使用 [SUBMIT TASK](../sql-reference/sql-statements/loading_unloading/ETL/SUBMIT_TASK.md) 提交异步 INSERT 任务。
- 对于当前版本的 StarRocks，如果任何行的数据不符合表的 schema，则默认情况下 INSERT 事务将失败。例如，如果任何行中的字段长度超过表中映射字段的长度限制，则 INSERT 事务将失败。您可以将会话变量 `enable_insert_strict` 设置为 `false`，以允许事务通过过滤掉与表不匹配的行来继续执行。
- 如果您频繁执行 INSERT 语句以将小批量数据导入到 StarRocks 中，则会生成过多的数据版本，严重影响查询性能。我们建议您在生产环境中不要过于频繁地使用 INSERT 命令导入数据，也不要将其用作日常数据导入的例程。如果您的应用程序或分析场景需要单独加载流式数据或小批量数据的解决方案，我们建议您使用 Apache Kafka® 作为数据源，并通过 Routine Load 导入数据。
- 如果您执行 INSERT OVERWRITE 语句，StarRocks 会为存储原始数据的分区创建临时分区，将新数据插入到临时分区中，并将 [原始分区与临时分区交换](../sql-reference/sql-statements/table_bucket_part_index/ALTER_TABLE.md#use-a-temporary-partition-to-replace-the-current-partition)。所有这些操作都在 FE Leader 节点中执行。因此，如果在执行 INSERT OVERWRITE 命令时 FE Leader 节点崩溃，则整个导入事务将失败，并且临时分区将被截断。

## 准备工作

### 检查权限

<InsertPrivNote />

### 创建对象

创建一个名为 `load_test` 的数据库，并创建一个表 `insert_wiki_edit` 作为目标表，并创建一个表 `source_wiki_edit` 作为源表。

> **NOTE**
>
> 本主题中演示的示例基于表 `insert_wiki_edit` 和表 `source_wiki_edit`。如果您喜欢使用自己的表和数据，则可以跳过准备工作并继续执行下一步。

```SQL
CREATE DATABASE IF NOT EXISTS load_test;
USE load_test;
CREATE TABLE insert_wiki_edit
(
    event_time      DATETIME,
    channel         VARCHAR(32)      DEFAULT '',
    user            VARCHAR(128)     DEFAULT '',
    is_anonymous    TINYINT          DEFAULT '0',
    is_minor        TINYINT          DEFAULT '0',
    is_new          TINYINT          DEFAULT '0',
    is_robot        TINYINT          DEFAULT '0',
    is_unpatrolled  TINYINT          DEFAULT '0',
    delta           INT              DEFAULT '0',
    added           INT              DEFAULT '0',
    deleted         INT              DEFAULT '0'
)
DUPLICATE KEY(
    event_time,
    channel,
    user,
    is_anonymous,
    is_minor,
    is_new,
    is_robot,
    is_unpatrolled
)
PARTITION BY RANGE(event_time)(
    PARTITION p06 VALUES LESS THAN ('2015-09-12 06:00:00'),
    PARTITION p12 VALUES LESS THAN ('2015-09-12 12:00:00'),
    PARTITION p18 VALUES LESS THAN ('2015-09-12 18:00:00'),
    PARTITION p24 VALUES LESS THAN ('2015-09-13 00:00:00')
)
DISTRIBUTED BY HASH(user);

CREATE TABLE source_wiki_edit
(
    event_time      DATETIME,
    channel         VARCHAR(32)      DEFAULT '',
    user            VARCHAR(128)     DEFAULT '',
    is_anonymous    TINYINT          DEFAULT '0',
    is_minor        TINYINT          DEFAULT '0',
    is_new          TINYINT          DEFAULT '0',
    is_robot        TINYINT          DEFAULT '0',
    is_unpatrolled  TINYINT          DEFAULT '0',
    delta           INT              DEFAULT '0',
    added           INT              DEFAULT '0',
    deleted         INT              DEFAULT '0'
)
DUPLICATE KEY(
    event_time,
    channel,user,
    is_anonymous,
    is_minor,
    is_new,
    is_robot,
    is_unpatrolled
)
PARTITION BY RANGE(event_time)(
    PARTITION p06 VALUES LESS THAN ('2015-09-12 06:00:00'),
    PARTITION p12 VALUES LESS THAN ('2015-09-12 12:00:00'),
    PARTITION p18 VALUES LESS THAN ('2015-09-12 18:00:00'),
    PARTITION p24 VALUES LESS THAN ('2015-09-13 00:00:00')
)
DISTRIBUTED BY HASH(user);
```

> **NOTICE**
>
> 从 v2.5.7 开始，当您创建表或添加分区时，StarRocks 可以自动设置 bucket 数量 (BUCKETS)。您不再需要手动设置 bucket 数量。有关详细信息，请参见 [设置 bucket 数量](../table_design/data_distribution/Data_distribution.md#set-the-number-of-buckets)。

## 通过 INSERT INTO VALUES 导入数据

您可以使用 INSERT INTO VALUES 命令将一行或多行追加到特定表中。多行用逗号 (,) 分隔。有关详细说明和参数参考，请参见 [SQL Reference - INSERT](../sql-reference/sql-statements/loading_unloading/INSERT.md)。

> **CAUTION**
>
> 通过 INSERT INTO VALUES 导入数据仅适用于需要使用小型数据集验证 DEMO 的情况。不建议用于大规模测试或生产环境。要将海量数据导入到 StarRocks 中，请参见 [导入选项](Loading_intro.md)，以获取适合您场景的其他选项。

以下示例使用标签 `insert_load_wikipedia` 将两行数据插入到数据源表 `source_wiki_edit` 中。标签是数据库中每个数据导入事务的唯一标识标签。

```SQL
INSERT INTO source_wiki_edit
WITH LABEL insert_load_wikipedia
VALUES
    ("2015-09-12 00:00:00","#en.wikipedia","AustinFF",0,0,0,0,0,21,5,0),
    ("2015-09-12 00:00:00","#ca.wikipedia","helloSR",0,1,0,1,0,3,23,0);
```

## 通过 INSERT INTO SELECT 导入数据

您可以通过 INSERT INTO SELECT 命令将对数据源表执行查询的结果加载到目标表中。INSERT INTO SELECT 命令对来自数据源表的数据执行 ETL 操作，并将数据加载到 StarRocks 的内表中。数据源可以是一个或多个内部或外部表，甚至是云存储上的数据文件。目标表必须是 StarRocks 中的内表。有关详细说明和参数参考，请参见 [SQL Reference - INSERT](../sql-reference/sql-statements/loading_unloading/INSERT.md)。

### 将数据从内部表或外部表导入到内部表

> **NOTE**
>
> 从外部表导入数据与从内部表导入数据相同。为简单起见，我们仅在以下示例中演示如何从内部表导入数据。

- 以下示例将数据从源表导入到目标表 `insert_wiki_edit`。

```SQL
INSERT INTO insert_wiki_edit
WITH LABEL insert_load_wikipedia_1
SELECT * FROM source_wiki_edit;
```

- 以下示例将数据从源表导入到目标表 `insert_wiki_edit` 的 `p06` 和 `p12` 分区。如果未指定分区，则数据将导入到所有分区。否则，数据将仅导入到指定的分区中。

```SQL
INSERT INTO insert_wiki_edit PARTITION(p06, p12)
WITH LABEL insert_load_wikipedia_2
SELECT * FROM source_wiki_edit;
```

查询目标表以确保其中有数据。

```Plain text
MySQL > select * from insert_wiki_edit;
+---------------------+---------------+----------+--------------+----------+--------+----------+----------------+-------+-------+---------+
| event_time          | channel       | user     | is_anonymous | is_minor | is_new | is_robot | is_unpatrolled | delta | added | deleted |
+---------------------+---------------+----------+--------------+----------+--------+----------+----------------+-------+-------+---------+
| 2015-09-12 00:00:00 | #en.wikipedia | AustinFF |            0 |        0 |      0 |        0 |              0 |    21 |     5 |       0 |
| 2015-09-12 00:00:00 | #ca.wikipedia | helloSR  |            0 |        1 |      0 |        1 |              0 |     3 |    23 |       0 |
+---------------------+---------------+----------+--------------+----------+--------+----------+----------------+-------+-------+---------+
2 rows in set (0.00 sec)
```

如果截断 `p06` 和 `p12` 分区，则查询中不会返回数据。

```Plain
MySQL > TRUNCATE TABLE insert_wiki_edit PARTITION(p06, p12);
Query OK, 0 rows affected (0.01 sec)

MySQL > select * from insert_wiki_edit;
Empty set (0.00 sec)
```

- 以下示例将源表中的 `event_time` 和 `channel` 列导入到目标表 `insert_wiki_edit`。默认值用于此处未指定的列。

```SQL
INSERT INTO insert_wiki_edit
WITH LABEL insert_load_wikipedia_3 
(
    event_time, 
    channel
)
SELECT event_time, channel FROM source_wiki_edit;
```

:::note
从 v3.3.1 开始，在主键表上使用 INSERT INTO 语句指定列列表将执行部分更新（而不是早期版本中的完全 Upsert）。如果未指定列列表，系统将执行完全 Upsert。
:::

### 使用 FILES() 直接从外部源的文件导入数据

从 v3.1 开始，StarRocks 支持使用 INSERT 命令和 [FILES()](../sql-reference/sql-functions/table-functions/files.md) 函数直接从云存储上的文件导入数据，因此您无需先创建 external catalog 或文件外部表。此外，FILES() 可以自动推断文件的表 schema，从而大大简化了数据导入过程。

以下示例将 AWS S3 bucket `inserttest` 中的 Parquet 文件 **parquet/insert_wiki_edit_append.parquet** 中的数据行插入到表 `insert_wiki_edit` 中：

```Plain
INSERT INTO insert_wiki_edit
    SELECT * FROM FILES(
        "path" = "s3://inserttest/parquet/insert_wiki_edit_append.parquet",
        "format" = "parquet",
        "aws.s3.access_key" = "XXXXXXXXXX",
        "aws.s3.secret_key" = "YYYYYYYYYY",
        "aws.s3.region" = "us-west-2"
);
```

## 通过 INSERT OVERWRITE VALUES 覆盖数据

您可以使用 INSERT OVERWRITE VALUES 命令使用一行或多行覆盖特定表。多行用逗号 (,) 分隔。有关详细说明和参数参考，请参见 [SQL Reference - INSERT](../sql-reference/sql-statements/loading_unloading/INSERT.md)。

> **CAUTION**
>
> 通过 INSERT OVERWRITE VALUES 覆盖数据仅适用于需要使用小型数据集验证 DEMO 的情况。不建议用于大规模测试或生产环境。要将海量数据导入到 StarRocks 中，请参见 [导入选项](Loading_intro.md)，以获取适合您场景的其他选项。

查询源表和目标表以确保其中有数据。

```Plain
MySQL > SELECT * FROM source_wiki_edit;
+---------------------+---------------+----------+--------------+----------+--------+----------+----------------+-------+-------+---------+
| event_time          | channel       | user     | is_anonymous | is_minor | is_new | is_robot | is_unpatrolled | delta | added | deleted |
+---------------------+---------------+----------+--------------+----------+--------+----------+----------------+-------+-------+---------+
| 2015-09-12 00:00:00 | #ca.wikipedia | helloSR  |            0 |        1 |      0 |        1 |              0 |     3 |    23 |       0 |
| 2015-09-12 00:00:00 | #en.wikipedia | AustinFF |            0 |        0 |      0 |        0 |              0 |    21 |     5 |       0 |
+---------------------+---------------+----------+--------------+----------+--------+----------+----------------+-------+-------+---------+
2 rows in set (0.02 sec)
 
MySQL > SELECT * FROM insert_wiki_edit;
+---------------------+---------------+----------+--------------+----------+--------+----------+----------------+-------+-------+---------+
| event_time          | channel       | user     | is_anonymous | is_minor | is_new | is_robot | is_unpatrolled | delta | added | deleted |
+---------------------+---------------+----------+--------------+----------+--------+----------+----------------+-------+-------+---------+
| 2015-09-12 00:00:00 | #ca.wikipedia | helloSR  |            0 |        1 |      0 |        1 |              0 |     3 |    23 |       0 |
| 2015-09-12 00:00:00 | #en.wikipedia | AustinFF |            0 |        0 |      0 |        0 |              0 |    21 |     5 |       0 |
+---------------------+---------------+----------+--------------+----------+--------+----------+----------------+-------+-------+---------+
2 rows in set (0.01 sec)
```

以下示例使用两个新行覆盖源表 `source_wiki_edit`。

```SQL
INSERT OVERWRITE source_wiki_edit
WITH LABEL insert_load_wikipedia_ow
VALUES
    ("2015-09-12 00:00:00","#cn.wikipedia","GELongstreet",0,0,0,0,0,36,36,0),
    ("2015-09-12 00:00:00","#fr.wikipedia","PereBot",0,1,0,1,0,17,17,0);
```

## 通过 INSERT OVERWRITE SELECT 覆盖数据

您可以使用 INSERT OVERWRITE SELECT 命令使用对数据源表执行查询的结果覆盖表。INSERT OVERWRITE SELECT 语句对来自一个或多个内部或外部表的数据执行 ETL 操作，并使用该数据覆盖内部表。有关详细说明和参数参考，请参见 [SQL Reference - INSERT](../sql-reference/sql-statements/loading_unloading/INSERT.md)。

> **NOTE**
>
> 从外部表导入数据与从内部表导入数据相同。为简单起见，我们仅在以下示例中演示如何使用来自内部表的数据覆盖目标表。

查询源表和目标表以确保它们包含不同的数据行。

```Plain
MySQL > SELECT * FROM source_wiki_edit;
+---------------------+---------------+--------------+--------------+----------+--------+----------+----------------+-------+-------+---------+
| event_time          | channel       | user         | is_anonymous | is_minor | is_new | is_robot | is_unpatrolled | delta | added | deleted |
+---------------------+---------------+--------------+--------------+----------+--------+----------+----------------+-------+-------+---------+
| 2015-09-12 00:00:00 | #cn.wikipedia | GELongstreet |            0 |        0 |      0 |        0 |              0 |    36 |    36 |       0 |
| 2015-09-12 00:00:00 | #fr.wikipedia | PereBot      |            0 |        1 |      0 |        1 |              0 |    17 |    17 |       0 |
+---------------------+---------------+--------------+--------------+----------+--------+----------+----------------+-------+-------+---------+
2 rows in set (0.02 sec)
 
MySQL > SELECT * FROM insert_wiki_edit;
+---------------------+---------------+----------+--------------+----------+--------+----------+----------------+-------+-------+---------+
| event_time          | channel       | user     | is_anonymous | is_minor | is_new | is_robot | is_unpatrolled | delta | added | deleted |
+---------------------+---------------+----------+--------------+----------+--------+----------+----------------+-------+-------+---------+
| 2015-09-12 00:00:00 | #en.wikipedia | AustinFF |            0 |        0 |      0 |        0 |              0 |    21 |     5 |       0 |
| 2015-09-12 00:00:00 | #ca.wikipedia | helloSR  |            0 |        1 |      0 |        1 |              0 |     3 |    23 |       0 |
+---------------------+---------------+----------+--------------+----------+--------+----------+----------------+-------+-------+---------+
2 rows in set (0.01 sec)
```

- 以下示例使用来自源表的数据覆盖表 `insert_wiki_edit`。

```SQL
INSERT OVERWRITE insert_wiki_edit
WITH LABEL insert_load_wikipedia_ow_1
SELECT * FROM source_wiki_edit;
```

- 以下示例使用来自源表的数据覆盖表 `insert_wiki_edit` 的 `p06` 和 `p12` 分区。

```SQL
INSERT OVERWRITE insert_wiki_edit PARTITION(p06, p12)
WITH LABEL insert_load_wikipedia_ow_2
SELECT * FROM source_wiki_edit;
```

查询目标表以确保其中有数据。

```plain text
MySQL > select * from insert_wiki_edit;
+---------------------+---------------+--------------+--------------+----------+--------+----------+----------------+-------+-------+---------+
| event_time          | channel       | user         | is_anonymous | is_minor | is_new | is_robot | is_unpatrolled | delta | added | deleted |
+---------------------+---------------+--------------+--------------+----------+--------+----------+----------------+-------+-------+---------+
| 2015-09-12 00:00:00 | #fr.wikipedia | PereBot      |            0 |        1 |      0 |        1 |              0 |    17 |    17 |       0 |
| 2015-09-12 00:00:00 | #cn.wikipedia | GELongstreet |            0 |        0 |      0 |        0 |              0 |    36 |    36 |       0 |
+---------------------+---------------+--------------+--------------+----------+--------+----------+----------------+-------+-------+---------+
2 rows in set (0.01 sec)
```

如果截断 `p06` 和 `p12` 分区，则查询中不会返回数据。

```Plain
MySQL > TRUNCATE TABLE insert_wiki_edit PARTITION(p06, p12);
Query OK, 0 rows affected (0.01 sec)

MySQL > select * from insert_wiki_edit;
Empty set (0.00 sec)
```

:::note
对于使用 `PARTITION BY column` 策略的表，INSERT OVERWRITE 支持通过指定分区键的值在目标表中创建新分区。现有分区照常覆盖。

以下示例创建分区表 `activity`，并在表中创建新分区，同时将数据插入到该分区中：

```SQL
CREATE TABLE activity (
id INT          NOT NULL,
dt VARCHAR(10)  NOT NULL
) ENGINE=OLAP 
DUPLICATE KEY(`id`)
PARTITION BY (`id`, `dt`)
DISTRIBUTED BY HASH(`id`);

INSERT OVERWRITE activity
PARTITION(id='4', dt='2022-01-01')
WITH LABEL insert_activity_auto_partition
VALUES ('4', '2022-01-01');
```

:::

- 以下示例使用来自源表的 `event_time` 和 `channel` 列覆盖目标表 `insert_wiki_edit`。默认值分配给未覆盖数据的列。

```SQL
INSERT OVERWRITE insert_wiki_edit
WITH LABEL insert_load_wikipedia_ow_3 
(
    event_time, 
    channel
)
SELECT event_time, channel FROM source_wiki_edit;
```

### 动态覆盖

从 v3.4.0 开始，StarRocks 支持一种新的语义 - 用于分区表的 INSERT OVERWRITE 的动态覆盖。

目前，INSERT OVERWRITE 的默认行为如下：

- 当覆盖整个分区表时（即，不指定 PARTITION 子句），新的数据记录将替换其相应分区中的数据。如果存在未涉及的分区，则这些分区将被截断，而其他分区将被覆盖。
- 当覆盖空分区表（即，其中没有分区）并指定 PARTITION 子句时，系统会返回错误 `ERROR 1064 (HY000): Getting analyzing error. Detail message: Unknown partition 'xxx' in table 'yyy'`。
- 当覆盖分区表并在 PARTITION 子句中指定不存在的分区时，系统会返回错误 `ERROR 1064 (HY000): Getting analyzing error. Detail message: Unknown partition 'xxx' in table 'yyy'`。
- 当使用与 PARTITION 子句中指定的任何分区都不匹配的数据记录覆盖分区表时，系统要么返回错误 `ERROR 1064 (HY000): Insert has filtered data in strict mode`（如果启用了严格模式），要么过滤掉不合格的数据记录（如果禁用了严格模式）。

新的动态覆盖语义的行为大不相同：

当覆盖整个分区表时，新的数据记录将替换其相应分区中的数据。如果存在未涉及的分区，则这些分区将被保留，而不是被截断或删除。并且如果存在与不存在的分区对应的新数据记录，系统将创建该分区。

默认情况下禁用动态覆盖语义。要启用它，您需要将系统变量 `dynamic_overwrite` 设置为 `true`。

在当前会话中启用动态覆盖：

```SQL
SET dynamic_overwrite = true;
```

您也可以在 INSERT OVERWRITE 语句的 hint 中设置它，以使其仅对该语句生效：

示例：

```SQL
INSERT /*+set_var(dynamic_overwrite = true)*/ OVERWRITE insert_wiki_edit
SELECT * FROM source_wiki_edit;
```

## 将数据导入到具有生成列的表中

生成列是一种特殊的列，其值源自基于其他列的预定义表达式或评估。当您的查询请求涉及对昂贵表达式的评估时，生成列特别有用，例如，从 JSON 值查询某个字段或计算 ARRAY 数据。StarRocks 在将数据加载到表中的同时评估表达式并将结果存储在生成列中，从而避免了查询期间的表达式评估并提高了查询性能。

您可以使用 INSERT 将数据导入到具有生成列的表中。

以下示例创建一个表 `insert_generated_columns` 并向其中插入一行。该表包含两个生成列：`avg_array` 和 `get_string`。`avg_array` 计算 `data_array` 中 ARRAY 数据的平均值，`get_string` 从 `data_json` 中的 JSON 路径 `a` 提取字符串。

```SQL
CREATE TABLE insert_generated_columns (
  id           INT(11)           NOT NULL    COMMENT "ID",
  data_array   ARRAY<INT(11)>    NOT NULL    COMMENT "ARRAY",
  data_json    JSON              NOT NULL    COMMENT "JSON",
  avg_array    DOUBLE            NULL 
      AS array_avg(data_array)               COMMENT "Get the average of ARRAY",
  get_string   VARCHAR(65533)    NULL 
      AS get_json_string(json_string(data_json), '$.a') COMMENT "Extract JSON string"
) ENGINE=OLAP 
PRIMARY KEY(id)
DISTRIBUTED BY HASH(id);

INSERT INTO insert_generated_columns 
VALUES (1, [1,2], parse_json('{"a" : 1, "b" : 2}'));
```

> **NOTE**
>
> 不支持直接将数据加载到生成列中。

您可以查询该表以检查其中的数据。

```Plain
mysql> SELECT * FROM insert_generated_columns;
+------+------------+------------------+-----------+------------+
| id   | data_array | data_json        | avg_array | get_string |
+------+------------+------------------+-----------+------------+
|    1 | [1,2]      | {"a": 1, "b": 2} |       1.5 | 1          |
+------+------------+------------------+-----------+------------+
1 row in set (0.02 sec)
```

## 使用 PROPERTIES 的 INSERT 数据

从 v3.4.0 开始，INSERT 语句支持配置 PROPERTIES，它可以用于各种目的。PROPERTIES 会覆盖其相应的变量。

### 启用严格模式

从 v3.4.0 开始，您可以启用严格模式并为来自 FILES() 的 INSERT 设置 `max_filter_ratio`。来自 FILES() 的 INSERT 的严格模式与其他导入方法的行为相同。

如果要加载包含一些不合格行的数据集，您可以过滤掉这些不合格行，也可以加载它们并将 NULL 值分配给不合格的列。您可以使用属性 `strict_mode` 和 `max_filter_ratio` 来实现这些目的。

- 要过滤掉不合格的行：将 `strict_mode` 设置为 `true`，并将 `max_filter_ratio` 设置为所需的值。
- 要加载所有具有 NULL 值的不合格行：将 `strict_mode` 设置为 `false`。

以下示例将 AWS S3 bucket `inserttest` 中的 Parquet 文件 **parquet/insert_wiki_edit_append.parquet** 中的数据行插入到表 `insert_wiki_edit` 中，启用严格模式以过滤掉不合格的数据记录，并容忍最多 10% 的错误数据：

```SQL
INSERT INTO insert_wiki_edit
PROPERTIES(
    "strict_mode" = "true",
    "max_filter_ratio" = "0.1"
)
SELECT * FROM FILES(
    "path" = "s3://inserttest/parquet/insert_wiki_edit_append.parquet",
    "format" = "parquet",
    "aws.s3.access_key" = "XXXXXXXXXX",
    "aws.s3.secret_key" = "YYYYYYYYYY",
    "aws.s3.region" = "us-west-2"
);
```

:::note

`strict_mode` 和 `max_filter_ratio` 仅支持来自 FILES() 的 INSERT。来自表的 INSERT 不支持这些属性。

:::

### 设置超时时长

从 v3.4.0 开始，您可以使用属性设置 INSERT 语句的超时时长。

以下示例将源表 `source_wiki_edit` 中的数据插入到目标表 `insert_wiki_edit` 中，并将超时时长设置为 `2` 秒。

```SQL
INSERT INTO insert_wiki_edit
PROPERTIES(
    "timeout" = "2"
)
SELECT * FROM source_wiki_edit;
```

:::note

从 v3.4.0 开始，您还可以使用系统变量 `insert_timeout` 设置 INSERT 超时时长，该变量适用于涉及 INSERT 的操作（例如，UPDATE、DELETE、CTAS、物化视图刷新、统计信息收集和 PIPE）。在早于 v3.4.0 的版本中，相应的变量是 `query_timeout`。

:::

### 按名称匹配列

默认情况下，INSERT 按位置匹配源表和目标表中的列，即语句中列的映射。

以下示例通过位置显式匹配源表和目标表中的每个列：

```SQL
INSERT INTO insert_wiki_edit (
    event_time,
    channel,
    user
)
SELECT event_time, channel, user FROM source_wiki_edit;
```

如果您更改列列表或 SELECT 语句中 `channel` 和 `user` 的顺序，则列映射将更改。

```SQL
INSERT INTO insert_wiki_edit (
    event_time,
    channel,
    user
)
SELECT event_time, user, channel FROM source_wiki_edit;
```

在这里，提取的数据可能不是您想要的，因为目标表 `insert_wiki_edit` 中的 `channel` 将填充来自源表 `source_wiki_edit` 中的 `user` 的数据。

通过在 INSERT 语句中添加 `BY NAME` 子句，系统将检测源表和目标表中的列名，并匹配具有相同名称的列。

:::note

- 如果指定了 `BY NAME`，则不能指定列列表。
- 如果未指定 `BY NAME`，则系统会按列列表和 SELECT 语句中列的位置匹配列。

:::

以下示例按名称匹配源表和目标表中的每个列：

```SQL
INSERT INTO insert_wiki_edit BY NAME
SELECT event_time, user, channel FROM source_wiki_edit;
```

在这种情况下，更改 `channel` 和 `user` 的顺序不会更改列映射。

## 使用 INSERT 异步导入数据

使用 INSERT 导入数据会提交一个同步事务，该事务可能会因会话中断或超时而失败。您可以使用 [SUBMIT TASK](../sql-reference/sql-statements/loading_unloading/ETL/SUBMIT_TASK.md) 提交异步 INSERT 事务。此功能自 StarRocks v2.5 起受支持。

- 以下示例异步地将数据从源表插入到目标表 `insert_wiki_edit`。

```SQL
SUBMIT TASK AS INSERT INTO insert_wiki_edit
SELECT * FROM source_wiki_edit;
```

- 以下示例使用源表中的数据异步覆盖表 `insert_wiki_edit`。

```SQL
SUBMIT TASK AS INSERT OVERWRITE insert_wiki_edit
SELECT * FROM source_wiki_edit;
```

- 以下示例使用源表中的数据异步覆盖表 `insert_wiki_edit`，并使用 hint 将查询超时延长至 `100000` 秒。

```SQL
SUBMIT /*+set_var(insert_timeout=100000)*/ TASK AS
INSERT OVERWRITE insert_wiki_edit
SELECT * FROM source_wiki_edit;
```

- 以下示例使用源表中的数据异步覆盖表 `insert_wiki_edit`，并将任务名称指定为 `async`。

```SQL
SUBMIT TASK async
AS INSERT OVERWRITE insert_wiki_edit
SELECT * FROM source_wiki_edit;
```

您可以通过查询 Information Schema 中的元数据视图 `task_runs` 来检查异步 INSERT 任务的状态。

以下示例检查 INSERT 任务 `async` 的状态。

```SQL
SELECT * FROM information_schema.task_runs WHERE task_name = 'async';
```

## 检查 INSERT 作业状态

### 通过结果检查

同步 INSERT 事务根据事务的结果返回不同的状态。

- **事务成功**

如果事务成功，StarRocks 将返回以下内容：

```Plain
Query OK, 2 rows affected (0.05 sec)
{'label':'insert_load_wikipedia', 'status':'VISIBLE', 'txnId':'1006'}
```

- **事务失败**

如果所有数据行都无法加载到目标表中，则 INSERT 事务将失败。如果事务失败，StarRocks 将返回以下内容：

```Plain
ERROR 1064 (HY000): Insert has filtered data in strict mode, tracking_url=http://x.x.x.x:yyyy/api/_load_error_log?file=error_log_9f0a4fd0b64e11ec_906bbede076e9d08
```

您可以通过使用 `tracking_url` 检查日志来找到问题。

### 通过 Information Schema 检查

您可以使用 [SELECT](../sql-reference/sql-statements/table_bucket_part_index/SELECT.md) 语句从 `information_schema` 数据库中的 `loads` 表中查询一个或多个导入作业的结果。此功能自 v3.1 起受支持。

示例 1：查询在 `load_test` 数据库上执行的导入作业的结果，按创建时间 (`CREATE_TIME`) 降序对结果进行排序，并且仅返回最上面的结果。

```SQL
SELECT * FROM information_schema.loads
WHERE database_name = 'load_test'
ORDER BY create_time DESC
LIMIT 1\G
```

示例 2：查询在 `load_test` 数据库上执行的导入作业（其标签为 `insert_load_wikipedia`）的结果：

```SQL
SELECT * FROM information_schema.loads
WHERE database_name = 'load_test' and label = 'insert_load_wikipedia'\G
```

返回结果如下：

```Plain
*************************** 1. row ***************************
              JOB_ID: 21319
               LABEL: insert_load_wikipedia
       DATABASE_NAME: load_test
               STATE: FINISHED
            PROGRESS: ETL:100%; LOAD:100%
                TYPE: INSERT
            PRIORITY: NORMAL
           SCAN_ROWS: 0
       FILTERED_ROWS: 0
     UNSELECTED_ROWS: 0
           SINK_ROWS: 2
            ETL_INFO: 
           TASK_INFO: resource:N/A; timeout(s):300; max_filter_ratio:0.0
         CREATE_TIME: 2023-08-09 10:42:23
      ETL_START_TIME: 2023-08-09 10:42:23
     ETL_FINISH_TIME: 2023-08-09