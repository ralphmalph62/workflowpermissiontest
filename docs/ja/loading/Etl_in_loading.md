---
displayed_sidebar: docs
---

# ロード時のデータ変換

import InsertPrivNote from '../_assets/commonMarkdown/insertPrivNote.mdx'
StarRocks は ロード時のデータ変換 をサポートしています。

この機能は、[Stream Load](../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md)、[Broker Load](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md)、および [Routine Load](../sql-reference/sql-statements/loading_unloading/routine_load/CREATE_ROUTINE_LOAD.md) をサポートしていますが、[Spark Load](../sql-reference/sql-statements/loading_unloading/SPARK_LOAD.md) はサポートしていません。

<InsertPrivNote />


このトピックでは、ロード時にデータを抽出および変換する方法を、CSV データを例にとって説明します。サポートされるデータファイル形式は、選択した ロード 方法によって異なります。

:::note
CSV データの場合、カンマ (,)、タブ、パイプ (|) など、長さが 50 バイトを超えない UTF-8 文字列をテキスト区切り文字として使用できます。
:::

### シナリオ

データファイルを StarRocks テーブルに ロード する際、データファイルのデータが StarRocks テーブルのデータに完全にマッピングされない場合があります。このような状況では、StarRocks テーブルに ロード する前にデータを抽出または変換する必要はありません。StarRocks は ロード 中にデータの抽出と変換をサポートします。

- ロード する必要のないカラムをスキップする。
  
  ロード する必要のないカラムをスキップできます。さらに、データファイルのカラムが StarRocks テーブルのカラムと異なる順序である場合、データファイルと StarRocks テーブル間のカラムマッピングを作成できます。

- ロード したくない行をフィルタリングする。
  
  フィルタ条件を指定することで、StarRocks は ロード したくない行をフィルタリングします。

- 元のカラムから新しいカラムを生成する。
  
  生成列 は、データファイルの元となるカラムから計算される特殊なカラムです。生成列 を StarRocks テーブルのカラムにマッピングできます。

- ファイルパスからパーティションフィールド値を抽出する。
  
  データファイルが Apache Hive™ から生成されたものである場合、ファイルパスからパーティションフィールド値を抽出できます。

## データ例

1.  ローカルファイルシステムにデータファイルを作成します。

    a. `file1.csv` という名前のデータファイルを作成します。このファイルは、ユーザー ID、ユーザーの性別、イベント日付、イベントタイプを順に表す 4 つのカラムで構成されています。

    ```Plain
    354,female,2020-05-20,1
    465,male,2020-05-21,2
    576,female,2020-05-22,1
    687,male,2020-05-23,2
    ```

    b. `file2.csv` という名前のデータファイルを作成します。このファイルは、日付を表す 1 つのカラムのみで構成されています。

    ```Plain
    2020-05-20
    2020-05-21
    2020-05-22
    2020-05-23
    ```

2.  StarRocks データベース `test_db` にテーブルを作成します。

    :::note

    v2.5.7 以降、StarRocks はテーブル作成時またはパーティション追加時にバケット数 (BUCKETS) を自動的に設定できます。手動でバケット数を設定する必要はありません。詳細については、「[バケット数の設定](../table_design/data_distribution/Data_distribution.md#set-the-number-of-buckets)」を参照してください。

    :::

    a. `event_date`、`event_type`、および `user_id` の 3 つのカラムで構成される `table1` という名前のテーブルを作成します。

    ```SQL
    MySQL [test_db]> CREATE TABLE table1
    (
        `event_date` DATE COMMENT "event date",
        `event_type` TINYINT COMMENT "event type",
        `user_id` BIGINT COMMENT "user ID"
    )
    DISTRIBUTED BY HASH(user_id);
    ```

    b. `date`、`year`、`month`、および `day` の 4 つのカラムで構成される `table2` という名前のテーブルを作成します。

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

3.  `file1.csv` と `file2.csv` を HDFS クラスタの `/user/starrocks/data/input/` パスにアップロードし、`file1.csv` のデータを Kafka クラスタの `topic1` にパブリッシュし、`file2.csv` のデータを Kafka クラスタの `topic2` にパブリッシュします。

## ロード する必要のないカラムをスキップする

StarRocks テーブルに ロード するデータファイルには、StarRocks テーブルのどのカラムにもマッピングできないカラムが含まれている場合があります。この状況では、StarRocks はデータファイルから StarRocks テーブルのカラムにマッピングできるカラムのみを ロード することをサポートします。

この機能は、以下のデータソースからのデータ ロード をサポートします。

- ローカルファイルシステム

- HDFS および クラウドストレージ
  
  > **NOTE**
  >
  > このセクションでは、HDFS を例として使用します。

- Kafka

ほとんどの場合、CSV ファイルのカラムには名前がありません。一部の CSV ファイルでは、最初の行がカラム名で構成されていますが、StarRocks は最初の行の内容をカラム名ではなく通常のデータとして処理します。したがって、CSV ファイルを ロード する際は、ジョブ作成ステートメントまたはコマンドで CSV ファイルのカラムに**順に**一時的に名前を付ける必要があります。これらの一時的に名前が付けられたカラムは、StarRocks テーブルのカラムに**名前で**マッピングされます。データファイルのカラムについては、以下の点に注意してください。

- StarRocks テーブルのカラム名を使用してマッピングされ、一時的に名前が付けられたカラムのデータは直接 ロード されます。

- StarRocks テーブルのカラムにマッピングできないカラムは無視され、これらのカラムのデータは ロード されません。

- 一部のカラムが StarRocks テーブルのカラムにマッピングできるが、ジョブ作成ステートメントまたはコマンドで一時的に名前が付けられていない場合、ロード ジョブはエラーを報告します。

このセクションでは、`file1.csv` と `table1` を例として使用します。`file1.csv` の 4 つのカラムは、順に `user_id`、`user_gender`、`event_date`、`event_type` として一時的に名前が付けられています。`file1.csv` の一時的に名前が付けられたカラムのうち、`user_id`、`event_date`、および `event_type` は `table1` の特定カラムにマッピングできますが、`user_gender` は `table1` のどのカラムにもマッピングできません。したがって、`user_id`、`event_date`、および `event_type` は `table1` に ロード されますが、`user_gender` は ロード されません。

### データロード

#### ローカルファイルシステムからデータを ロード する

`file1.csv` がローカルファイルシステムに保存されている場合、次のコマンドを実行して [Stream Load](../loading/StreamLoad.md) ジョブを作成します。

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
> Stream Load を選択する場合、`columns` パラメータを使用してデータファイルのカラムに一時的に名前を付け、データファイルと StarRocks テーブル間のカラムマッピングを作成する必要があります。

詳細な構文とパラメータの説明については、「[STREAM LOAD](../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md)」を参照してください。

#### HDFS クラスタからデータを ロード する

`file1.csv` が HDFS クラスタに保存されている場合、次のステートメントを実行して [Broker Load](../loading/hdfs_load.md) ジョブを作成します。

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
> Broker Load を選択する場合、`column_list` パラメータを使用してデータファイルのカラムに一時的に名前を付け、データファイルと StarRocks テーブル間のカラムマッピングを作成する必要があります。

詳細な構文とパラメータの説明については、「[BROKER LOAD](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md)」を参照してください。

#### Kafka クラスタからデータを ロード する

`file1.csv` のデータが Kafka クラスタの `topic1` にパブリッシュされている場合、次のステートメントを実行して [Routine Load](../loading/RoutineLoad.md) ジョブを作成します。

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
> Routine Load を選択する場合、`COLUMNS` パラメータを使用してデータファイルのカラムに一時的に名前を付け、データファイルと StarRocks テーブル間のカラムマッピングを作成する必要があります。

詳細な構文とパラメータの説明については、「[CREATE ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/CREATE_ROUTINE_LOAD.md)」を参照してください。

### データクエリ

ローカルファイルシステム、HDFS クラスタ、または Kafka クラスタからのデータ ロード が完了したら、`table1` のデータをクエリして ロード が成功したことを確認します。

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

## ロード したくない行をフィルタリングする

データファイルを StarRocks テーブルに ロード する際、データファイルの特定の行を ロード したくない場合があります。この状況では、WHERE 句を使用して ロード したい行を指定できます。StarRocks は、WHERE 句で指定されたフィルタ条件を満たさないすべての行をフィルタリングします。

この機能は、以下のデータソースからのデータ ロード をサポートします。

- ローカルファイルシステム

- HDFS および クラウドストレージ
  > **NOTE**
  >
  > このセクションでは、HDFS を例として使用します。

- Kafka

このセクションでは、`file1.csv` と `table1` を例として使用します。`file1.csv` からイベントタイプが `1` の行のみを `table1` に ロード したい場合、WHERE 句を使用してフィルタ条件 `event_type = 1` を指定できます。

### データロード

#### ローカルファイルシステムからデータを ロード する

`file1.csv` がローカルファイルシステムに保存されている場合、次のコマンドを実行して [Stream Load](../loading/StreamLoad.md) ジョブを作成します。

```Bash
curl --location-trusted -u <username>:<password> \
    -H "Expect:100-continue" \
    -H "column_separator:," \
    -H "columns: user_id, user_gender, event_date, event_type" \
    -H "where: event_type=1" \
    -T file1.csv -XPUT \
    http://<fe_host>:<fe_http_port>/api/test_db/table1/_stream_load
```

詳細な構文とパラメータの説明については、「[STREAM LOAD](../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md)」を参照してください。

#### HDFS クラスタからデータを ロード する

`file1.csv` が HDFS クラスタに保存されている場合、次のステートメントを実行して [Broker Load](../loading/hdfs_load.md) ジョブを作成します。

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

詳細な構文とパラメータの説明については、「[BROKER LOAD](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md)」を参照してください。

#### Kafka クラスタからデータを ロード する

`file1.csv` のデータが Kafka クラスタの `topic1` にパブリッシュされている場合、次のステートメントを実行して [Routine Load](../loading/RoutineLoad.md) ジョブを作成します。

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

詳細な構文とパラメータの説明については、「[CREATE ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/CREATE_ROUTINE_LOAD.md)」を参照してください。

### データクエリ

ローカルファイルシステム、HDFS クラスタ、または Kafka クラスタからのデータ ロード が完了したら、`table1` のデータをクエリして ロード が成功したことを確認します。

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

## 元のカラムから新しいカラムを生成する

データファイルを StarRocks テーブルに ロード する際、データファイルの一部のデータは、StarRocks テーブルに ロード する前に変換が必要な場合があります。この状況では、ジョブ作成コマンドまたはステートメントで関数または式を使用してデータ変換を実装できます。

この機能は、以下のデータソースからのデータ ロード をサポートします。

- ローカルファイルシステム

- HDFS および クラウドストレージ
  > **NOTE**
  >
  > このセクションでは、HDFS を例として使用します。

- Kafka

このセクションでは、`file2.csv` と `table2` を例として使用します。`file2.csv` は日付を表す 1 つのカラムのみで構成されています。`file2.csv` から各日付の年、月、日を抽出するために、[year](../sql-reference/sql-functions/date-time-functions/year.md)、[month](../sql-reference/sql-functions/date-time-functions/month.md)、および [day](../sql-reference/sql-functions/date-time-functions/day.md) 関数を使用し、抽出したデータを `table2` の `year`、`month`、および `day` カラムに ロード できます。

### データロード

#### ローカルファイルシステムからデータを ロード する

`file2.csv` がローカルファイルシステムに保存されている場合、次のコマンドを実行して [Stream Load](../loading/StreamLoad.md) ジョブを作成します。

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
> - `columns` パラメータでは、まずデータファイルの**すべてをカラムに**一時的に名前を付け、次にデータファイルの元となるカラムから生成したい新しいカラムに一時的に名前を付ける必要があります。上記の例に示すように、`file2.csv` の唯一のカラムは一時的に `date` と名前が付けられ、その後 `year=year(date)`、`month=month(date)`、および `day=day(date)` 関数が呼び出されて、一時的に `year`、`month`、および `day` と名前が付けられた 3 つの新しいカラムが生成されます。
>
> - Stream Load は `column_name = function(column_name)` をサポートしませんが、`column_name = function(column_name)` をサポートします。

詳細な構文とパラメータの説明については、「[STREAM LOAD](../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md)」を参照してください。

#### HDFS クラスタからデータを ロード する

`file2.csv` が HDFS クラスタに保存されている場合、次のステートメントを実行して [Broker Load](../loading/hdfs_load.md) ジョブを作成します。

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
> まず `column_list` パラメータを使用してデータファイルの**すべてのカラムに**一時的に名前を付け、次に SET 句を使用してデータファイルの元となるカラムから生成したい新しいカラムに一時的に名前を付ける必要があります。上記の例に示すように、`file2.csv` の唯一のカラムは `column_list` パラメータで一時的に `date` と名前が付けられ、その後 SET 句で `year=year(date)`、`month=month(date)`、および `day=day(date)` 関数が呼び出されて、一時的に `year`、`month`、および `day` と名前が付けられた 3 つの新しいカラムが生成されます。

詳細な構文とパラメータの説明については、「[BROKER LOAD](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md)」を参照してください。

#### Kafka クラスタからデータを ロード する

`file2.csv` のデータが Kafka クラスタの `topic2` にパブリッシュされている場合、次のステートメントを実行して [Routine Load](../loading/RoutineLoad.md) ジョブを作成します。

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
> `COLUMNS` パラメータでは、まずデータファイルの**すべてのカラムに**一時的に名前を付け、次にデータファイルの元となるカラムから生成したい新しいカラムに一時的に名前を付ける必要があります。上記の例に示すように、`file2.csv` の唯一のカラムは一時的に `date` と名前が付けられ、その後 `year=year(date)`、`month=month(date)`、および `day=day(date)` 関数が呼び出されて、一時的に `year`、`month`、および `day` と名前が付けられた 3 つの新しいカラムが生成されます。

詳細な構文とパラメータの説明については、「[CREATE ROUTINE LOAD](../sql-reference/sql-statements/loading_unloading/routine_load/CREATE_ROUTINE_LOAD.md)」を参照してください。

### データクエリ

ローカルファイルシステム、HDFS クラスタ、または Kafka クラスタからのデータ ロード が完了したら、`table2` のデータをクエリして ロード が成功したことを確認します。

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

## ファイルパスからパーティションフィールド値を抽出する

指定したファイルパスにパーティションフィールドが含まれている場合、`COLUMNS FROM PATH AS` パラメータを使用して、ファイルパスから抽出したいパーティションフィールドを指定できます。ファイルパス内のパーティションフィールドは、データファイル内のカラムと同等です。`COLUMNS FROM PATH AS` パラメータは、HDFS クラスタからデータを ロード する場合にのみサポートされます。

たとえば、Hive から生成された以下の 4 つのデータファイルを ロード したいとします。

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

この 4 つのデータファイルは、HDFS クラスタの `/user/starrocks/data/input/` パスに保存されています。これらのデータファイルはそれぞれ、パーティションフィールド `date` でパーティション化されており、イベントタイプとユーザー ID を順に表す 2 つのカラムで構成されています。

### HDFS クラスタからデータを ロード する

次のステートメントを実行して [Broker Load](../loading/hdfs_load.md) ジョブを作成します。これにより、`/user/starrocks/data/input/` ファイルパスから `date` パーティションフィールド値が抽出され、ワイルドカード (*) を使用して、ファイルパス内のすべてのデータファイルを `table1` に ロード するように指定できます。

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
> 上記の例では、指定されたファイルパス内の `date` パーティションフィールドは、`table1` の `event_date` カラムと同等です。したがって、SET 句を使用して `date` パーティションフィールドを `event_date` カラムにマッピングする必要があります。指定されたファイルパス内のパーティションフィールドが StarRocks テーブルのカラムと同じ名前である場合、SET 句を使用してマッピングを作成する必要はありません。

詳細な構文とパラメータの説明については、「[BROKER LOAD](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md)」を参照してください。

### データクエリ

HDFS クラスタからのデータ ロード が完了したら、`table1` のデータをクエリして ロード が成功したことを確認します。

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
