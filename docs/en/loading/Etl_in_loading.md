displayed_sidebar: docs
---

# Data Transformation on Import

import InsertPrivNote from '../_assets/commonMarkdown/insertPrivNote.mdx'

StarRocks supports data transformation during data import.
OK

This feature supports [Stream Load](../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md), [Broker Load](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md), and [Routine Load](../sql-reference/sql-statements/loading_unloading/routine_load/CREATE_ROUTINE_LOAD.md), but does not support [Spark Load](../sql-reference/sql-statements/loading_unloading/SPARK_LOAD.md).

<InsertPrivNote />

This document uses CSV data as an example to describe how to extract and transform data during data import. Supported data file formats vary depending on the import method you choose.

:::note

For CSV data, you can use UTF-8 strings (such as commas (,), tabs, or vertical bars (|)) as text delimiters. Their length cannot exceed 50 bytes.

:::

## Scenarios

When you import data files into StarRocks tables, the data in the data files may not be fully mappable to the data in the StarRocks tables. In this case, you do not need to extract or transform the data before importing it into StarRocks tables. StarRocks can help you extract and transform data during data import:

- Skip columns that do not need to be imported.
  
  You can skip columns that do not need to be imported. In addition, if the column order of the data file is different from that of the StarRocks table, you can create column mappings between the data file and the StarRocks table.

- Filter out rows that do not need to be imported.
  
  You can specify filter conditions, and StarRocks will filter out rows that you do not need to import based on these conditions.

- Generate new columns from original columns.
  
  Generated columns are special columns calculated from the original columns of the data file. You can map generated columns to columns in the StarRocks table.

- Extract partition field values from file paths.
  
  If the data file is generated from Apache Hive™, you can extract partition field values from the file path.

## Data Example

1.  Create data files in the local file system.

    a. Create a data file named `file1.csv`. This file contains four columns, which sequentially represent user ID, user gender, event date, and event type.

    ```Plain
    354,female,2020-05-20,1
    465,male,2020-05-21,2
    576,female,2020-05-22,1
    687,male,2020-05-23,2
    ```

    b. Create a data file named `file2.csv`. This file contains only one column, which represents the date.

    ```Plain
    2020-05-20
    2020-05-21
    2020-05-22
    2020-05-23
    ```

2.  Create tables in the StarRocks database `test_db`.

    > **NOTE**
    >
    > Starting from v2.5.7, StarRocks can automatically set the number of buckets (BUCKETS) when you create tables or add partitions. You no longer need to manually set the number of buckets. For more information, see [Set the number of buckets](../table_design/data_distribution/Data_distribution.md#set-the-number-of-buckets).

    a. Create a table named `table1` that contains three columns: `event_date`, `event_type`, and `user_id`.

    ```SQL
    MySQL [test_db]> CREATE TABLE table1
    (
        `event_date` DATE COMMENT "event date",
        `event_type` TINYINT COMMENT "event type",
        `user_id` BIGINT COMMENT "user ID"
    )
    DISTRIBUTED BY HASH(user_id);
    ```

    b. Create a table named `table2` that contains four columns: `date`, `year`, `month`, and `day`.

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

3.  Upload `file1.csv` and `file2.csv` to the `/user/starrocks/data/input/` path of the HDFS cluster, publish the data from `file1.csv` to `topic1` of the Kafka cluster, and publish the data from `file2.csv` to `topic2` of the Kafka cluster.

## Skip columns that do not need to be imported

The data file you want to import into a StarRocks table may contain columns that cannot be mapped to any column in the StarRocks table. In this case, StarRocks supports importing only those columns in the data file that can be mapped to StarRocks table columns.

This feature supports importing data from the following data sources:

- Local file system

- HDFS and cloud storage
  
  > **NOTE**
  >
  > This section takes HDFS as an example.

- Kafka

In most cases, columns in CSV files are unnamed. For some CSV files, the first row consists of column names, but StarRocks treats the content of the first row as ordinary data, not column names. Therefore, when you import CSV files, you must temporarily name the columns of the CSV file **in order** in the job creation statement or command. These temporarily named columns are mapped to StarRocks table columns **by name**. Please note the following about data file columns:

- Data from columns that can be mapped to StarRocks table columns and are temporarily named using the StarRocks table column names will be imported directly.

- Columns that cannot be mapped to StarRocks table columns will be ignored, and their data will not be imported.

- If some columns can be mapped to StarRocks table columns but are not temporarily named in the job creation statement or command, the import job will report an error.

This section uses `file1.csv` and `table1` as an example. The four columns of `file1.csv` are temporarily named `user_id`, `user_gender`, `event_date`, and `event_type` in order. Among the temporarily named columns of `file1.csv`, `user_id`, `event_date`, and `event_type` can be mapped to specific columns of `table1`, while `user_gender` cannot be mapped to any column of `table1`. Therefore, `user_id`, `event_date`, and `event_type` will be imported into `table1`, but `user_gender` will not be imported.

### Import data

#### Import data from the local file system

If `file1.csv` is stored in the local file system, run the following command to create a [Stream Load](../loading/StreamLoad.md) job:

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
> If you choose Stream Load, you must use the `columns` parameter to temporarily name the columns of the data file to create column mappings between the data file and the StarRocks table.

For detailed syntax and parameter descriptions, see [STREAM LOAD](../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md).

#### Import data from HDFS cluster

If `file1.csv` is stored in the HDFS cluster, execute the following statement to create a [Broker Load](../loading/hdfs_load.md) job:

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
> If you choose Broker Load, you must use the `column_list` parameter to temporarily name the columns of the data file to create column mappings between the data file and the StarRocks table.

For detailed syntax and parameter descriptions, see [BROKER LOAD](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md).

#### Import data from Kafka cluster

If the data from `file1.csv` has been published to `topic1` of the Kafka cluster, execute the following statement to create a [Routine Load](../loading/RoutineLoad.md) job:

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
> If you choose Routine Load, you must use the `COLUMNS` parameter to temporarily name the columns of the data file to create column mappings between the data file and the StarRocks table.

For detailed syntax and parameter descriptions, see [CREATE ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/CREATE_ROUTINE_LOAD.md).

### Query data

After importing data from the local file system, HDFS cluster, or Kafka cluster, query the data in `table1` to verify whether the import was successful:

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

## Filter out rows that do not need to be imported

When you import data files into a StarRocks table, you may not want to import specific rows from the data file. In this case, you can use the WHERE clause to specify the rows to be imported. StarRocks will filter out all rows that do not meet the filter conditions specified in the WHERE clause.

This feature supports importing data from the following data sources:

- Local file system

- HDFS and cloud storage
  > **NOTE**
  >
  > This section takes HDFS as an example.

- Kafka

This section uses `file1.csv` and `table1` as an example. If you only want to import rows with `event_type` as `1` from `file1.csv` into `table1`, you can use the WHERE clause to specify the filter condition `event_type = 1`.

### Import data

#### Import data from the local file system

If `file1.csv` is stored in the local file system, run the following command to create a [Stream Load](../loading/StreamLoad.md) job:

```Bash
curl --location-trusted -u <username>:<password> \
    -H "Expect:100-continue" \
    -H "column_separator:," \
    -H "columns: user_id, user_gender, event_date, event_type" \
    -H "where: event_type=1" \
    -T file1.csv -XPUT \
    http://<fe_host>:<fe_http_port>/api/test_db/table1/_stream_load
```

For detailed syntax and parameter descriptions, see [STREAM LOAD](../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md).

#### Import data from HDFS cluster

If `file1.csv` is stored in the HDFS cluster, execute the following statement to create a [Broker Load](../loading/hdfs_load.md) job:

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

For detailed syntax and parameter descriptions, see [BROKER LOAD](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md).

#### Import data from Kafka cluster

If the data from `file1.csv` has been published to `topic1` of the Kafka cluster, execute the following statement to create a [Routine Load](../loading/RoutineLoad.md) job:

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

For detailed syntax and parameter descriptions, see [CREATE ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/CREATE_ROUTINE_LOAD.md).

### Query data

After importing data from the local file system, HDFS cluster, or Kafka cluster, query the data in `table1` to verify whether the import was successful:

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

## Generate new columns from original columns

When you import data files into a StarRocks table, some data in the data files may need to be transformed before being imported into the StarRocks table. In this case, you can use functions or expressions in the job creation command or statement to achieve data transformation.

This feature supports importing data from the following data sources:

- Local file system

- HDFS and cloud storage
  > **NOTE**
  >
  > This section takes HDFS as an example.

- Kafka

This section uses `file2.csv` and `table2` as an example. `file2.csv` contains only one column representing the date. You can use the [year](../sql-reference/sql-functions/date-time-functions/year.md), [month](../sql-reference/sql-functions/date-time-functions/month.md), and [day](../sql-reference/sql-functions/date-time-functions/day.md) functions to extract the year, month, and day for each date from `file2.csv` and import the extracted data into the `year`, `month`, and `day` columns of `table2`.

### Import data

#### Import data from the local file system

If `file2.csv` is stored in the local file system, run the following command to create a [Stream Load](../loading/StreamLoad.md) job:

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
> - In the `columns` parameter, you must first temporarily name **all columns** of the data file, and then temporarily name the new columns to be generated from the original columns of the data file. As shown in the example above, the only column of `file2.csv` is temporarily named `date`, and then the `year=year(date)`, `month=month(date)`, and `day=day(date)` functions are called to generate three new columns, temporarily named `year`, `month`, and `day`.
>
> - Stream Load does not support `column_name = function(column_name)`, but supports `column_name = function(column_name)`.

For detailed syntax and parameter descriptions, see [STREAM LOAD](../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md).

#### Import data from HDFS cluster

If `file2.csv` is stored in the HDFS cluster, execute the following statement to create a [Broker Load](../loading/hdfs_load.md) job:

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
> You must first use the `column_list` parameter to temporarily name **all columns** of the data file, and then use the SET clause to temporarily name the new columns to be generated from the original columns of the data file. As shown in the example above, the only column of `file2.csv` is temporarily named `date` in the `column_list` parameter, and then the `year=year(date)`, `month=month(date)`, and `day=day(date)` functions are called in the SET clause to generate three new columns, temporarily named `year`, `month`, and `day`.

For detailed syntax and parameter descriptions, see [BROKER LOAD](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md).

#### Import data from Kafka cluster

If the data from `file2.csv` has been published to `topic2` of the Kafka cluster, execute the following statement to create a [Routine Load](../loading/RoutineLoad.md) job:

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
> In the `COLUMNS` parameter, you must first temporarily name **all columns** of the data file, and then temporarily name the new columns to be generated from the original columns of the data file. As shown in the example above, the only column of `file2.csv` is temporarily named `date`, and then the `year=year(date)`, `month=month(date)`, and `day=day(date)` functions are called to generate three new columns, temporarily named `year`, `month`, and `day`.

For detailed syntax and parameter descriptions, see [CREATE ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/CREATE_ROUTINE_LOAD.md).

### Query data

After importing data from the local file system, HDFS cluster, or Kafka cluster, query the data in `table2` to verify whether the import was successful:

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

## Extract partition field values from file paths

If the specified file path contains partition fields, you can use the `COLUMNS FROM PATH AS` parameter to specify the partition fields to be extracted from the file path. Partition fields in the file path are equivalent to columns in the data file. The `COLUMNS FROM PATH AS` parameter is only supported when you import data from an HDFS cluster.

For example, you want to import the following four data files generated from Hive:

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

These four data files are stored in the `/user/starrocks/data/input/` path of the HDFS cluster. Each data file is partitioned by the partition field `date` and contains two columns, which sequentially represent event type and user ID.

### Import data from HDFS cluster

Execute the following statement to create a [Broker Load](../loading/hdfs_load.md) job that allows you to extract the `date` partition field value from the `/user/starrocks/data/input/` file path and use a wildcard (*) to specify that all data files in the file path are to be imported into `table1`:

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
> In the example above, the `date` partition field in the specified file path is equivalent to the `event_date` column of `table1`. Therefore, you need to use the SET clause to map the `date` partition field to the `event_date` column. If the partition field in the specified file path has the same name as a column in the StarRocks table, you do not need to use the SET clause to create a mapping.

For detailed syntax and parameter descriptions, see [BROKER LOAD](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md).

### Query data

After importing data from the HDFS cluster, query the data in `table1` to verify whether the import was successful:

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
