---
displayed_sidebar: docs
---

# 通过导入更改数据

import InsertPrivNote from '../_assets/commonMarkdown/insertPrivNote.mdx'

StarRocks 提供的 [主键表](../table_design/table_types/primary_key_table.md) 允许您通过运行 [Stream Load](../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md) 、[Broker Load](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md) 或 [Routine Load](../sql-reference/sql-statements/loading_unloading/routine_load/CREATE_ROUTINE_LOAD.md) 作业来更改 StarRocks 表中的数据。这些数据更改包括插入、更新和删除。但是，主键表不支持使用 [Spark Load](../sql-reference/sql-statements/loading_unloading/SPARK_LOAD.md) 或 [INSERT](../sql-reference/sql-statements/loading_unloading/INSERT.md) 更改数据。

StarRocks 还支持部分更新和条件更新。

<InsertPrivNote />

本主题以 CSV 数据为例，介绍如何通过导入更改 StarRocks 表中的数据。支持的数据文件格式因您选择的导入方法而异。

> **NOTE**
>
> 对于 CSV 数据，您可以使用 UTF-8 字符串（例如逗号 (,)、制表符或管道 (|)），其长度不超过 50 字节作为文本分隔符。

## 实现

StarRocks 提供的主键表支持 UPSERT 和 DELETE 操作，并且不区分 INSERT 操作和 UPDATE 操作。

创建导入作业时，StarRocks 支持向作业创建语句或命令添加名为 `__op` 的字段。 `__op` 字段用于指定要执行的操作类型。

> **NOTE**
>
> 创建表时，无需向该表添加名为 `__op` 的列。

定义 `__op` 字段的方法因您选择的导入方法而异：

- 如果选择 Stream Load，请使用 `columns` 参数定义 `__op` 字段。

- 如果选择 Broker Load，请使用 SET 子句定义 `__op` 字段。

- 如果选择 Routine Load，请使用 `COLUMNS` 列定义 `__op` 字段。

您可以根据要进行的数据更改来决定是否添加 `__op` 字段。如果未添加 `__op` 字段，则操作类型默认为 UPSERT。主要的数据更改场景如下：

- 如果要导入的数据文件仅涉及 UPSERT 操作，则无需添加 `__op` 字段。

- 如果要导入的数据文件仅涉及 DELETE 操作，则必须添加 `__op` 字段并将操作类型指定为 DELETE。

- 如果要导入的数据文件同时涉及 UPSERT 和 DELETE 操作，则必须添加 `__op` 字段，并确保数据文件包含一个列，其值为 `0` 或 `1`。值 `0` 表示 UPSERT 操作，值 `1` 表示 DELETE 操作。

## 使用说明

- 确保数据文件中的每一行都具有相同数量的列。

- 涉及数据更改的列必须包含主键列。

## 基本操作

本节提供有关如何通过导入更改 StarRocks 表中的数据的示例。有关详细的语法和参数说明，请参见 [STREAM LOAD](../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md) 、[BROKER LOAD](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md) 和 [CREATE ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/CREATE_ROUTINE_LOAD.md)。

### UPSERT

如果要导入的数据文件仅涉及 UPSERT 操作，则无需添加 `__op` 字段。

> **NOTE**
>
> 如果添加 `__op` 字段：
>
> - 可以将操作类型指定为 UPSERT。
>
> - 可以将 `__op` 字段留空，因为操作类型默认为 UPSERT。

#### 数据示例

1. 准备数据文件。

   a. 在本地文件系统中创建一个名为 `example1.csv` 的 CSV 文件。该文件由三列组成，依次表示用户 ID、用户名和用户分数。

      ```Plain
      101,Lily,100
      102,Rose,100
      ```

   b. 将 `example1.csv` 的数据发布到 Kafka 集群的 `topic1`。

2. 准备 StarRocks 表。

   a. 在 StarRocks 数据库 `test_db` 中创建一个名为 `table1` 的主键表。该表由三列组成：`id`、`name` 和 `score`，其中 `id` 是主键。

      ```SQL
      CREATE TABLE `table1`
      (
          `id` int(11) NOT NULL COMMENT "user ID",
          `name` varchar(65533) NOT NULL COMMENT "user name",
          `score` int(11) NOT NULL COMMENT "user score"
      )
      ENGINE=OLAP
      PRIMARY KEY(`id`)
      DISTRIBUTED BY HASH(`id`);
      ```

      > **NOTE**
      >
      > 从 v2.5.7 开始，StarRocks 可以在创建表或添加分区时自动设置 bucket 数量 (BUCKETS)。您不再需要手动设置 bucket 数量。有关详细信息，请参见 [设置 bucket 数量](../table_design/data_distribution/Data_distribution.md#set-the-number-of-buckets)。

   b. 将一条记录插入到 `table1` 中。

      ```SQL
      INSERT INTO table1 VALUES
          (101, 'Lily',80);
      ```

#### 导入数据

运行一个导入作业，以将 `example1.csv` 中 `id` 为 `101` 的记录更新到 `table1`，并将 `example1.csv` 中 `id` 为 `102` 的记录插入到 `table1`。

- 运行 Stream Load 作业。
  
  - 如果不想包含 `__op` 字段，请运行以下命令：

    ```Bash
    curl --location-trusted -u <username>:<password> \
        -H "Expect:100-continue" \
        -H "label:label1" \
        -H "column_separator:," \
        -T example1.csv -XPUT \
        http://<fe_host>:<fe_http_port>/api/test_db/table1/_stream_load
    ```

  - 如果想包含 `__op` 字段，请运行以下命令：

    ```Bash
    curl --location-trusted -u <username>:<password> \
        -H "Expect:100-continue" \
        -H "label:label2" \
        -H "column_separator:," \
        -H "columns:__op ='upsert'" \
        -T example1.csv -XPUT \
        http://<fe_host>:<fe_http_port>/api/test_db/table1/_stream_load
    ```

- 运行 Broker Load 作业。

  - 如果不想包含 `__op` 字段，请运行以下命令：

    ```SQL
    LOAD LABEL test_db.label1
    (
        data infile("hdfs://<hdfs_host>:<hdfs_port>/example1.csv")
        into table table1
        columns terminated by ","
        format as "csv"
    )
    WITH BROKER;
    ```

  - 如果想包含 `__op` 字段，请运行以下命令：

    ```SQL
    LOAD LABEL test_db.label2
    (
        data infile("hdfs://<hdfs_host>:<hdfs_port>/example1.csv")
        into table table1
        columns terminated by ","
        format as "csv"
        set (__op = 'upsert')
    )
    WITH BROKER;
    ```

- 运行 Routine Load 作业。

  - 如果不想包含 `__op` 字段，请运行以下命令：

    ```SQL
    CREATE ROUTINE LOAD test_db.table1 ON table1
    COLUMNS TERMINATED BY ",",
    COLUMNS (id, name, score)
    PROPERTIES
    (
        "desired_concurrent_number" = "3",
        "max_batch_interval" = "20",
        "max_batch_rows"= "250000",
        "max_error_number" = "1000"
    )
    FROM KAFKA
    (
        "kafka_broker_list" ="<kafka_broker_host>:<kafka_broker_port>",
        "kafka_topic" = "test1",
        "property.kafka_default_offsets" ="OFFSET_BEGINNING"
    );
    ```

  - 如果想包含 `__op` 字段，请运行以下命令：

    ```SQL
    CREATE ROUTINE LOAD test_db.table1 ON table1
    COLUMNS TERMINATED BY ",",
    COLUMNS (id, name, score, __op ='upsert')
    PROPERTIES
    (
        "desired_concurrent_number" = "3",
        "max_batch_interval" = "20",
        "max_batch_rows"= "250000",
        "max_error_number" = "1000"
    )
    FROM KAFKA
    (
        "kafka_broker_list" ="<kafka_broker_host>:<kafka_broker_port>",
        "kafka_topic" = "test1",
        "property.kafka_default_offsets" ="OFFSET_BEGINNING"
    );
    ```

#### 查询数据

导入完成后，查询 `table1` 的数据以验证导入是否成功：

```SQL
SELECT * FROM table1;
+------+------+-------+
| id   | name | score |
+------+------+-------+
|  101 | Lily |   100 |
|  102 | Rose |   100 |
+------+------+-------+
2 rows in set (0.02 sec)
```

如上述查询结果所示，`example1.csv` 中 `id` 为 `101` 的记录已更新到 `table1`，并且 `example1.csv` 中 `id` 为 `102` 的记录已插入到 `table1` 中。

### DELETE

如果要导入的数据文件仅涉及 DELETE 操作，则必须添加 `__op` 字段并将操作类型指定为 DELETE。

#### 数据示例

1. 准备数据文件。

   a. 在本地文件系统中创建一个名为 `example2.csv` 的 CSV 文件。该文件由三列组成，依次表示用户 ID、用户名和用户分数。

      ```Plain
      101,Jack,100
      ```

   b. 将 `example2.csv` 的数据发布到 Kafka 集群的 `topic2`。

2. 准备 StarRocks 表。

   a. 在 StarRocks 数据库 `test_db` 中创建一个名为 `table2` 的主键表。该表由三列组成：`id`、`name` 和 `score`，其中 `id` 是主键。

      ```SQL
      CREATE TABLE `table2`
            (
          `id` int(11) NOT NULL COMMENT "user ID",
          `name` varchar(65533) NOT NULL COMMENT "user name",
          `score` int(11) NOT NULL COMMENT "user score"
      )
      ENGINE=OLAP
      PRIMARY KEY(`id`)
      DISTRIBUTED BY HASH(`id`);
      ```

      > **NOTE**
      >
      > 从 v2.5.7 开始，StarRocks 可以在创建表或添加分区时自动设置 bucket 数量 (BUCKETS)。您不再需要手动设置 bucket 数量。有关详细信息，请参见 [设置 bucket 数量](../table_design/data_distribution/Data_distribution.md#set-the-number-of-buckets)。

   b. 将两条记录插入到 `table2` 中。

      ```SQL
      INSERT INTO table2 VALUES
      (101, 'Jack', 100),
      (102, 'Bob', 90);
      ```

#### 导入数据

运行一个导入作业，以从 `table2` 中删除 `example2.csv` 中 `id` 为 `101` 的记录。

- 运行 Stream Load 作业。

  ```Bash
  curl --location-trusted -u <username>:<password> \
      -H "Expect:100-continue" \
      -H "label:label3" \
      -H "column_separator:," \
      -H "columns:__op='delete'" \
      -T example2.csv -XPUT \
      http://<fe_host>:<fe_http_port>/api/test_db/table2/_stream_load
  ```

- 运行 Broker Load 作业。

  ```SQL
  LOAD LABEL test_db.label3
  (
      data infile("hdfs://<hdfs_host>:<hdfs_port>/example2.csv")
      into table table2
      columns terminated by ","
      format as "csv"
      set (__op = 'delete')
  )
  WITH BROKER;  
  ```

- 运行 Routine Load 作业。

  ```SQL
  CREATE ROUTINE LOAD test_db.table2 ON table2
  COLUMNS(id, name, score, __op = 'delete')
  PROPERTIES
  (
      "desired_concurrent_number" = "3",
      "max_batch_interval" = "20",
      "max_batch_rows"= "250000",
      "max_error_number" = "1000"
  )
  FROM KAFKA
  (
      "kafka_broker_list" ="<kafka_broker_host>:<kafka_broker_port>",
      "kafka_topic" = "test2",
      "property.kafka_default_offsets" ="OFFSET_BEGINNING"
  );
  ```

#### 查询数据

导入完成后，查询 `table2` 的数据以验证导入是否成功：

```SQL
SELECT * FROM table2;
+------+------+-------+
| id   | name | score |
+------+------+-------+
|  102 | Bob  |    90 |
+------+------+-------+
1 row in set (0.00 sec)
```

如上述查询结果所示，`example2.csv` 中 `id` 为 `101` 的记录已从 `table2` 中删除。

### UPSERT 和 DELETE

如果要导入的数据文件同时涉及 UPSERT 和 DELETE 操作，则必须添加 `__op` 字段，并确保数据文件包含一个列，其值为 `0` 或 `1`。值 `0` 表示 UPSERT 操作，值 `1` 表示 DELETE 操作。

#### 数据示例

1. 准备数据文件。

   a. 在本地文件系统中创建一个名为 `example3.csv` 的 CSV 文件。该文件由四列组成，依次表示用户 ID、用户名、用户分数和操作类型。

      ```Plain
      101,Tom,100,1
      102,Sam,70,0
      103,Stan,80,0
      ```

   b. 将 `example3.csv` 的数据发布到 Kafka 集群的 `topic3`。

2. 准备 StarRocks 表。

   a. 在 StarRocks 数据库 `test_db` 中创建一个名为 `table3` 的主键表。该表由三列组成：`id`、`name` 和 `score`，其中 `id` 是主键。

      ```SQL
      CREATE TABLE `table3`
      (
          `id` int(11) NOT NULL COMMENT "user ID",
          `name` varchar(65533) NOT NULL COMMENT "user name",
          `score` int(11) NOT NULL COMMENT "user score"
      )
      ENGINE=OLAP
      PRIMARY KEY(`id`)
      DISTRIBUTED BY HASH(`id`);
      ```

      > **NOTE**
      >
      > 从 v2.5.7 开始，StarRocks 可以在创建表或添加分区时自动设置 bucket 数量 (BUCKETS)。您不再需要手动设置 bucket 数量。有关详细信息，请参见 [设置 bucket 数量](../table_design/data_distribution/Data_distribution.md#set-the-number-of-buckets)。

   b. 将两条记录插入到 `table3` 中。

      ```SQL
      INSERT INTO table3 VALUES
          (101, 'Tom', 100),
          (102, 'Sam', 90);
      ```

#### 导入数据

运行一个导入作业，以从 `table3` 中删除 `example3.csv` 中 `id` 为 `101` 的记录，将 `example3.csv` 中 `id` 为 `102` 的记录更新到 `table3`，并将 `example3.csv` 中 `id` 为 `103` 的记录插入到 `table3`。

- 运行 Stream Load 作业：

  ```Bash
  curl --location-trusted -u <username>:<password> \
      -H "Expect:100-continue" \
      -H "label:label4" \
      -H "column_separator:," \
      -H "columns: id, name, score, temp, __op = temp" \
      -T example3.csv -XPUT \
      http://<fe_host>:<fe_http_port>/api/test_db/table3/_stream_load
  ```

  > **NOTE**
  >
  > 在上面的示例中，`example3.csv` 中表示操作类型的第四列暂时命名为 `temp`，并且 `__op` 字段通过 `columns` 参数映射到 `temp` 列。这样，StarRocks 可以根据 `example3.csv` 的第四列中的值是 `0` 还是 `1` 来决定是执行 UPSERT 还是 DELETE 操作。

- 运行 Broker Load 作业：

  ```Bash
  LOAD LABEL test_db.label4
  (
      data infile("hdfs://<hdfs_host>:<hdfs_port>/example1.csv")
      into table table1
      columns terminated by ","
      format as "csv"
      (id, name, score, temp)
      set (__op=temp)
  )
  WITH BROKER;
  ```

- 运行 Routine Load 作业：

  ```SQL
  CREATE ROUTINE LOAD test_db.table3 ON table3
  COLUMNS(id, name, score, temp, __op = temp)
  PROPERTIES
  (
      "desired_concurrent_number" = "3",
      "max_batch_interval" = "20",
      "max_batch_rows"= "250000",
      "max_error_number" = "1000"
  )
  FROM KAFKA
  (
      "kafka_broker_list" = "<kafka_broker_host>:<kafka_broker_port>",
      "kafka_topic" = "test3",
      "property.kafka_default_offsets" = "OFFSET_BEGINNING"
  );
  ```

#### 查询数据

导入完成后，查询 `table3` 的数据以验证导入是否成功：

```SQL
SELECT * FROM table3;
+------+------+-------+
| id   | name | score |
+------+------+-------+
|  102 | Sam  |    70 |
|  103 | Stan |    80 |
+------+------+-------+
2 rows in set (0.01 sec)
```

如上述查询结果所示，`example3.csv` 中 `id` 为 `101` 的记录已从 `table3` 中删除，`example3.csv` 中 `id` 为 `102` 的记录已更新到 `table3`，并且 `example3.csv` 中 `id` 为 `103` 的记录已插入到 `table3` 中。

## 部分更新

主键表还支持部分更新，并为不同的数据更新场景提供两种部分更新模式：行模式和列模式。这两种部分更新模式可以在保证查询性能的同时，尽可能地减少部分更新的开销，从而确保实时更新。行模式更适合涉及许多列和小批量的实时更新场景。列模式适用于涉及少量列和大量行的批量处理更新场景。

> **NOTICE**
>
> 执行部分更新时，如果要更新的行不存在，StarRocks 会插入一个新行，并在由于没有数据更新插入而为空的字段中填充默认值。

本节以 CSV 为例，介绍如何执行部分更新。

### 数据示例

1. 准备数据文件。

   a. 在本地文件系统中创建一个名为 `example4.csv` 的 CSV 文件。该文件由两列组成，依次表示用户 ID 和用户名。

      ```Plain
      101,Lily
      102,Rose
      103,Alice
      ```

   b. 将 `example4.csv` 的数据发布到 Kafka 集群的 `topic4`。

2. 准备 StarRocks 表。

   a. 在 StarRocks 数据库 `test_db` 中创建一个名为 `table4` 的主键表。该表由三列组成：`id`、`name` 和 `score`，其中 `id` 是主键。

      ```SQL
      CREATE TABLE `table4`
      (
          `id` int(11) NOT NULL COMMENT "user ID",
          `name` varchar(65533) NOT NULL COMMENT "user name",
          `score` int(11) NOT NULL COMMENT "user score"
      )
      ENGINE=OLAP
      PRIMARY KEY(`id`)
      DISTRIBUTED BY HASH(`id`);
      ```

      > **NOTE**
      >
      > 从 v2.5.7 开始，StarRocks 可以在创建表或添加分区时自动设置 bucket 数量 (BUCKETS)。您不再需要手动设置 bucket 数量。有关详细信息，请参见 [设置 bucket 数量](../table_design/data_distribution/Data_distribution.md#set-the-number-of-buckets)。

   b. 将一条记录插入到 `table4` 中。

      ```SQL
      INSERT INTO table4 VALUES
          (101, 'Tom',80);
      ```

### 导入数据

运行一个导入作业，以将 `example4.csv` 中两列的数据更新到 `table4` 的 `id` 和 `name` 列。

- 运行 Stream Load 作业：

  ```Bash
  curl --location-trusted -u <username>:<password> \
      -H "Expect:100-continue" \
      -H "label:label7" -H "column_separator:," \
      -H "partial_update:true" \
      -H "columns:id,name" \
      -T example4.csv -XPUT \
      http://<fe_host>:<fe_http_port>/api/test_db/table4/_stream_load
  ```

  > **NOTE**
  >
  > 如果选择 Stream Load，则必须将 `partial_update` 参数设置为 `true` 才能启用部分更新功能。默认情况下，是行模式下的部分更新。如果需要执行列模式下的部分更新，则需要将 `partial_update_mode` 设置为 `column`。此外，必须使用 `columns` 参数指定要更新的列。

- 运行 Broker Load 作业：

  ```SQL
  LOAD LABEL test_db.table4
  (
      data infile("hdfs://<hdfs_host>:<hdfs_port>/example4.csv")
      into table table4
      format as "csv"
      (id, name)
  )
  WITH BROKER
  PROPERTIES
  (
      "partial_update" = "true"
  );
  ```

  > **NOTE**
  >
  > 如果选择 Broker Load，则必须将 `partial_update` 参数设置为 `true` 才能启用部分更新功能。默认情况下，是行模式下的部分更新。如果需要执行列模式下的部分更新，则需要将 `partial_update_mode` 设置为 `column`。此外，必须使用 `column_list` 参数指定要更新的列。

- 运行 Routine Load 作业：

  ```SQL
  CREATE ROUTINE LOAD test_db.table4 on table4
  COLUMNS (id, name),
  COLUMNS TERMINATED BY ','
  PROPERTIES
  (
      "partial_update" = "true"
  )
  FROM KAFKA
  (
      "kafka_broker_list" ="<kafka_broker_host>:<kafka_broker_port>",
      "kafka_topic" = "test4",
      "property.kafka_default_offsets" ="OFFSET_BEGINNING"
  );
  ```

  > **NOTE**
  >
  > - 如果选择 Routine Load，则必须将 `partial_update` 参数设置为 `true` 才能启用部分更新功能。此外，必须使用 `COLUMNS` 参数指定要更新的列。
  > - Routine Load 仅支持行模式下的部分更新，不支持列模式下的部分更新。

### 查询数据

导入完成后，查询 `table4` 的数据以验证导入是否成功：

```SQL
SELECT * FROM table4;
+------+-------+-------+
| id   | name  | score |
+------+-------+-------+
|  102 | Rose  |     0 |
|  101 | Lily  |    80 |
|  103 | Alice |     0 |
+------+-------+-------+
3 rows in set (0.01 sec)
```

如上述查询结果所示，`example4.csv` 中 `id` 为 `101` 的记录已更新到 `table4`，并且 `example4.csv` 中 `id` 为 `102` 和 `103` 的记录已插入到 `table4`。

## 条件更新

从 StarRocks v2.5 开始，主键表支持条件更新。您可以指定一个非主键列作为条件，以确定更新是否可以生效。这样，仅当源数据记录在指定列中具有大于或等于目标数据记录的值时，从源记录到目标记录的更新才会生效。

条件更新功能旨在解决数据无序问题。如果源数据是无序的，则可以使用此功能来确保新数据不会被旧数据覆盖。

> **NOTICE**
>
> - 不能为同一批数据指定不同的列作为更新条件。
> - DELETE 操作不支持条件更新。
> - 在低于 v3.1.3 的版本中，部分更新和条件更新不能同时使用。从 v3.1.3 开始，StarRocks 支持将部分更新与条件更新一起使用。

### 数据示例

1. 准备数据文件。

   a. 在本地文件系统中创建一个名为 `example5.csv` 的 CSV 文件。该文件由三列组成，依次表示用户 ID、版本和用户分数。

      ```Plain
      101,1,100
      102,3,100
      ```

   b. 将 `example5.csv` 的数据发布到 Kafka 集群的 `topic5`。

2. 准备 StarRocks 表。

   a. 在 StarRocks 数据库 `test_db` 中创建一个名为 `table5` 的主键表。该表由三列组成：`id`、`version` 和 `score`，其中 `id` 是主键。

      ```SQL
      CREATE TABLE `table5`
      (
          `id` int(11) NOT NULL COMMENT "user ID", 
          `version` int NOT NULL COMMENT "version",
          `score` int(11) NOT NULL COMMENT "user score"
      )
      ENGINE=OLAP
      PRIMARY KEY(`id`) DISTRIBUTED BY HASH(`id`);
      ```

      > **NOTE**
      >
      > 从 v2.5.7 开始，StarRocks 可以在创建表或添加分区时自动设置 bucket 数量 (BUCKETS)。您不再需要手动设置 bucket 数量。有关详细信息，请参见 [设置 bucket 数量](../table_design/data_distribution/Data_distribution.md#set-the-number-of-buckets)。

   b. 将一条记录插入到 `table5` 中。

      ```SQL
      INSERT INTO table5 VALUES
          (101, 2, 80),
          (102, 2, 90);
      ```

### 导入数据

运行一个导入作业，以将 `example5.csv` 中 `id` 值分别为 `101` 和 `102` 的记录更新到 `table5`，并指定仅当两条记录中的 `version` 值大于或等于其当前的 `version` 值时，更新才会生效。

- 运行 Stream Load 作业：

  ```Bash
  curl --location-trusted -u <username>:<password> \
      -H "Expect:100-continue" \
      -H "label:label10" \
      -H "column_separator:," \
      -H "merge_condition:version" \
      -T example5.csv -XPUT \
      http://<fe_host>:<fe_http_port>/api/test_db/table5/_stream_load
  ```
- 运行 Insert Load 作业:
  ```SQL
  INSERT INTO test_db.table5 properties("merge_condition" = "version")
  VALUES (101, 2, 70), (102, 3, 100);
  ```

- 运行 Routine Load 作业：

  ```SQL
  CREATE ROUTINE LOAD test_db.table5 on table5
  COLUMNS (id, version, score),
  COLUMNS TERMINATED BY ','
  PROPERTIES
  (
      "merge_condition" = "version"
  )
  FROM KAFKA
  (
      "kafka_broker_list" ="<kafka_broker_host>:<kafka_broker_port>",
      "kafka_topic" = "topic5",
      "property.kafka_default_offsets" ="OFFSET_BEGINNING"
  );
  ```

- 运行 Broker Load 作业：

  ```SQL
  LOAD LABEL test_db.table5
  ( DATA INFILE ("s3://xxx.csv")
    INTO TABLE table5 COLUMNS TERMINATED BY "," FORMAT AS "CSV"
  )
  WITH BROKER
  PROPERTIES
  (
      "merge_condition" = "version"
  );
  ```

### 查询数据

导入完成后，查询 `table5` 的数据以验证导入是否成功：

```SQL
SELECT * FROM table5;
+------+------+-------+
| id   | version | score |
+------+------+-------+
|  101 |       2 |   80 |
|  102 |       3 |  100 |
+------+------+-------+
2 rows in set (0.02 sec)
```

如上述查询结果所示，`example5.csv` 中 `id` 为 `101` 的记录未更新到 `table5`，并且 `example5.csv` 中 `id` 为 `102` 的记录已插入到 `table5`。