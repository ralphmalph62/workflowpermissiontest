---
displayed_sidebar: docs
---

# `AUTO_INCREMENT`

StarRocks バージョン 3.0 以降では、データ管理を簡素化できる `AUTO_INCREMENT` カラム属性がサポートされています。このトピックでは、`AUTO_INCREMENT` カラム属性のアプリケーションシナリオ、使用法、および機能について紹介します。

## 概要

新しいデータ行がテーブルにロードされ、`AUTO_INCREMENT` カラムの値が指定されていない場合、StarRocks は行の `AUTO_INCREMENT` カラムに、テーブル全体で一意の ID として整数値を自動的に割り当てます。その後の `AUTO_INCREMENT` カラムの値は、行の ID から始まる特定のステップで自動的に増加します。`AUTO_INCREMENT` カラムは、データ管理を簡素化し、一部のクエリを高速化するために使用できます。`AUTO_INCREMENT` カラムのアプリケーションシナリオを以下に示します。

- 主キーとして機能する: `AUTO_INCREMENT` カラムは、各行に一意の ID を持たせ、データのクエリと管理を容易にするために、主キーとして使用できます。
- テーブルのジョイン: 複数のテーブルをジョインする場合、`AUTO_INCREMENT` カラムをジョインキーとして使用できます。これにより、たとえば UUID など、データ型が STRING のカラムを使用するよりもクエリを高速化できます。
- カーディナリティの高いカラムの重複排除カウント数をカウントする: `AUTO_INCREMENT` カラムは、辞書内の一意の値カラムを表すために使用できます。STRING 値の重複排除カウントを直接カウントするのに比べて、`AUTO_INCREMENT` カラムの整数値の重複排除カウントをカウントすると、クエリ速度が数倍、あるいは数十倍向上する場合があります。

CREATE TABLE ステートメントで `AUTO_INCREMENT` カラムを指定する必要があります。`AUTO_INCREMENT` カラムのデータ型は BIGINT である必要があります。AUTO_INCREMENT カラムの値は、[暗黙的に割り当てるか、明示的に指定](#assign-values-for-auto_increment-column)できます。1 から始まり、新しい行ごとに 1 ずつ増加します。

## 基本操作

### テーブル作成時に `AUTO_INCREMENT` カラムを指定する

`id` と `number` の 2 つのカラムを持つ `test_tbl1` という名前のテーブルを作成します。カラム `number` を `AUTO_INCREMENT` カラムとして指定します。

```SQL
CREATE TABLE test_tbl1
(
    id BIGINT NOT NULL, 
    number BIGINT NOT NULL AUTO_INCREMENT
) 
PRIMARY KEY (id) 
DISTRIBUTED BY HASH(id)
PROPERTIES("replicated_storage" = "true");
```

### `AUTO_INCREMENT` カラムに値を割り当てる

#### 暗黙的に値を割り当てる

データを StarRocks テーブルにロードするときに、`AUTO_INCREMENT` カラムの値を指定する必要はありません。StarRocks は、そのカラムに一意の整数値を自動的に割り当て、テーブルに挿入します。

```SQL
INSERT INTO test_tbl1 (id) VALUES (1);
INSERT INTO test_tbl1 (id) VALUES (2);
INSERT INTO test_tbl1 (id) VALUES (3),(4),(5);
```

テーブル内のデータを表示します。

```SQL
mysql > SELECT * FROM test_tbl1 ORDER BY id;
+------+--------+
| id   | number |
+------+--------+
|    1 |      1 |
|    2 |      2 |
|    3 |      3 |
|    4 |      4 |
|    5 |      5 |
+------+--------+
5 rows in set (0.02 sec)
```

データを StarRocks テーブルにロードするときに、`AUTO_INCREMENT` カラムの値を `DEFAULT` として指定することもできます。StarRocks は、そのカラムに一意の整数値を自動的に割り当て、テーブルに挿入します。

```SQL
INSERT INTO test_tbl1 (id, number) VALUES (6, DEFAULT);
```

テーブル内のデータを表示します。

```SQL
mysql > SELECT * FROM test_tbl1 ORDER BY id;
+------+--------+
| id   | number |
+------+--------+
|    1 |      1 |
|    2 |      2 |
|    3 |      3 |
|    4 |      4 |
|    5 |      5 |
|    6 |      6 |
+------+--------+
6 rows in set (0.02 sec)
```

実際の使用では、テーブル内のデータを表示すると、次の結果が返される場合があります。これは、StarRocks が `AUTO_INCREMENT` カラムの値が厳密に単調であることを保証できないためです。ただし、StarRocks は、値がほぼ時系列順に増加することを保証できます。詳細については、[単調性](#monotonicity)を参照してください。

```SQL
mysql > SELECT * FROM test_tbl1 ORDER BY id;
+------+--------+
| id   | number |
+------+--------+
|    1 |      1 |
|    2 | 100001 |
|    3 | 200001 |
|    4 | 200002 |
|    5 | 200003 |
|    6 | 200004 |
+------+--------+
6 rows in set (0.01 sec)
```

#### 明示的に値を指定する

`AUTO_INCREMENT` カラムの値を明示的に指定して、テーブルに挿入することもできます。

```SQL
INSERT INTO test_tbl1 (id, number) VALUES (7, 100);

-- view data in the table.

mysql > SELECT * FROM test_tbl1 ORDER BY id;
+------+--------+
| id   | number |
+------+--------+
|    1 |      1 |
|    2 | 100001 |
|    3 | 200001 |
|    4 | 200002 |
|    5 | 200003 |
|    6 | 200004 |
|    7 |    100 |
+------+--------+
7 rows in set (0.01 sec)
```

さらに、値を明示的に指定しても、新しく挿入されたデータ行に対して StarRocks によって生成される後続の値には影響しません。

```SQL
INSERT INTO test_tbl1 (id) VALUES (8);

-- view data in the table.

mysql > SELECT * FROM test_tbl1 ORDER BY id;
+------+--------+
| id   | number |
+------+--------+
|    1 |      1 |
|    2 | 100001 |
|    3 | 200001 |
|    4 | 200002 |
|    5 | 200003 |
|    6 | 200004 |
|    7 |    100 |
|    8 |      2 |
+------+--------+
8 rows in set (0.01 sec)
```

**注意**

`AUTO_INCREMENT` カラムに対して、暗黙的に割り当てられた値と明示的に指定された値を同時に使用しないことをお勧めします。指定された値が StarRocks によって生成された値と同じになる可能性があり、[自動インクリメント ID のグローバルな一意性](#uniqueness)が損なわれるためです。

## 基本機能

### 一意性

一般に、StarRocks は、`AUTO_INCREMENT` カラムの値がテーブル全体でグローバルに一意であることを保証します。`AUTO_INCREMENT` カラムに対して、暗黙的に値を割り当て、明示的に値を指定することを同時に行わないことをお勧めします。そうすると、自動インクリメント ID のグローバルな一意性が損なわれる可能性があります。簡単な例を次に示します。`id` と `number` の 2 つのカラムを持つ `test_tbl2` という名前のテーブルを作成します。カラム `number` を `AUTO_INCREMENT` カラムとして指定します。

```SQL
CREATE TABLE test_tbl2
(
    id BIGINT NOT NULL,
    number BIGINT NOT NULL AUTO_INCREMENT
 ) 
PRIMARY KEY (id) 
DISTRIBUTED BY HASH(id)
PROPERTIES("replicated_storage" = "true");
```

テーブル `test_tbl2` の `AUTO_INCREMENT` カラム `number` に、暗黙的に値を割り当て、明示的に値を指定します。

```SQL
INSERT INTO test_tbl2 (id, number) VALUES (1, DEFAULT);
INSERT INTO test_tbl2 (id, number) VALUES (2, 2);
INSERT INTO test_tbl2 (id) VALUES (3);
```

テーブル `test_tbl2` をクエリします。

```SQL
mysql > SELECT * FROM test_tbl2 ORDER BY id;
+------+--------+
| id   | number |
+------+--------+
|    1 |      1 |
|    2 |      2 |
|    3 | 100001 |
+------+--------+
3 rows in set (0.08 sec)
```

### 単調性

自動インクリメント ID の割り当てのパフォーマンスを向上させるために、BE は一部の自動インクリメント ID をローカルにキャッシュします。この状況では、StarRocks は `AUTO_INCREMENT` カラムの値が厳密に単調であることを保証できません。値がほぼ時系列順に増加することのみを保証できます。

> **注**
>
> BE によってキャッシュされる自動インクリメント ID の数は、FE の動的パラメータ `auto_increment_cache_size` によって決定されます。デフォルト値は `100,000` です。`ADMIN SET FRONTEND CONFIG ("auto_increment_cache_size" = "xxx");` を使用して値を変更できます。

たとえば、StarRocks クラスタには 1 つの FE ノードと 2 つの BE ノードがあります。`test_tbl3` という名前のテーブルを作成し、次のように 5 行のデータを挿入します。

```SQL
CREATE TABLE test_tbl3
(
    id BIGINT NOT NULL,
    number BIGINT NOT NULL AUTO_INCREMENT
) 
PRIMARY KEY (id)
DISTRIBUTED BY HASH(id)
PROPERTIES("replicated_storage" = "true");

INSERT INTO test_tbl3 VALUES (1, DEFAULT);
INSERT INTO test_tbl3 VALUES (2, DEFAULT);
INSERT INTO test_tbl3 VALUES (3, DEFAULT);
INSERT INTO test_tbl3 VALUES (4, DEFAULT);
INSERT INTO test_tbl3 VALUES (5, DEFAULT);
```

2 つの BE ノードがそれぞれ自動インクリメント ID [1, 100000] と [100001, 200000] をキャッシュするため、テーブル `test_tbl3` の自動インクリメント ID は単調に増加しません。複数の INSERT ステートメントを使用してデータをロードすると、データは異なる BE ノードに送信され、自動インクリメント ID が個別に割り当てられます。したがって、自動インクリメント ID が厳密に単調であることは保証できません。

```SQL
mysql > SELECT * FROM test_tbl3 ORDER BY id;
+------+--------+
| id   | number |
+------+--------+
|    1 |      1 |
|    2 | 100001 |
|    3 | 200001 |
|    4 |      2 |
|    5 | 100002 |
+------+--------+
5 rows in set (0.07 sec)
```

## 部分更新と `AUTO_INCREMENT` カラム

このセクションでは、`AUTO_INCREMENT` カラムを含むテーブルで、指定されたいくつかのカラムのみを更新する方法について説明します。

> **注**
>
> 現在、Primary Key テーブルのみが部分更新をサポートしています。

### `AUTO_INCREMENT` カラムが主キーである

部分更新中に主キーを指定する必要があります。したがって、`AUTO_INCREMENT` カラムが主キーであるか、主キーの一部である場合、部分更新のユーザーの動作は、`AUTO_INCREMENT` カラムが定義されていない場合とまったく同じです。

1. データベース `example_db` にテーブル `test_tbl4` を作成し、1 つのデータ行を挿入します。

    ```SQL
    -- Create a table.
    CREATE TABLE test_tbl4
    (
        id BIGINT AUTO_INCREMENT,
        name BIGINT NOT NULL,
        job1 BIGINT NOT NULL,
        job2 BIGINT NOT NULL
    ) 
    PRIMARY KEY (id, name)
    DISTRIBUTED BY HASH(id)
    PROPERTIES("replicated_storage" = "true");

    -- Prepared data.
    mysql > INSERT INTO test_tbl4 (id, name, job1, job2) VALUES (0, 0, 1, 1);
    Query OK, 1 row affected (0.04 sec)
    {'label':'insert_6af28e77-7d2b-11ed-af6e-02424283676b', 'status':'VISIBLE', 'txnId':'152'}

    -- Query the table.
    mysql > SELECT * FROM test_tbl4 ORDER BY id;
    +------+------+------+------+
    | id   | name | job1 | job2 |
    +------+------+------+------+
    |    0 |    0 |    1 |    1 |
    +------+------+------+------+
    1 row in set (0.01 sec)
    ```

2. テーブル `test_tbl4` を更新するための CSV ファイル **my_data4.csv** を準備します。CSV ファイルには `AUTO_INCREMENT` カラムの値が含まれており、カラム `job1` の値は含まれていません。最初の行の主キーはテーブル `test_tbl4` に既に存在しますが、2 番目の行の主キーはテーブルに存在しません。

    ```Plaintext
    0,0,99
    1,1,99
    ```

3. [Stream Load](../loading_unloading/STREAM_LOAD.md) ジョブを実行し、CSV ファイルを使用してテーブル `test_tbl4` を更新します。

    ```Bash
    curl --location-trusted -u <username>:<password> -H "label:1" \
        -H "column_separator:," \
        -H "partial_update:true" \
        -H "columns:id,name,job2" \
        -T my_data4.csv -XPUT \
        http://<fe_host>:<fe_http_port>/api/example_db/test_tbl4/_stream_load
    ```

4. 更新されたテーブルをクエリします。最初の行のデータはテーブル `test_tbl4` に既に存在し、カラム `job1` の値は変更されていません。2 番目の行のデータは新しく挿入され、カラム `job1` のデフォルト値が指定されていないため、部分更新フレームワークはこのカラムの値を `0` に直接設定します。

    ```SQL
    mysql > SELECT * FROM test_tbl4 ORDER BY id;
    +------+------+------+------+
    | id   | name | job1 | job2 |
    +------+------+------+------+
    |    0 |    0 |    1 |   99 |
    |    1 |    1 |    0 |   99 |
    +------+------+------+------+
    2 rows in set (0.01 sec)
    ```

### `AUTO_INCREMENT` カラムが主キーではない

`AUTO_INCREMENT` カラムが主キーではないか、主キーの一部ではない場合、Stream Load ジョブで自動インクリメント ID が提供されないと、次の状況が発生します。

- 行がテーブルに既に存在する場合、StarRocks は自動インクリメント ID を更新しません。
- 行がテーブルに新しくロードされた場合、StarRocks は新しい自動インクリメント ID を生成します。

この機能は、重複排除 STRING 値をすばやく計算するための辞書テーブルを構築するために使用できます。

1. データベース `example_db` で、テーブル `test_tbl5` を作成し、カラム `job1` を `AUTO_INCREMENT` カラムとして指定し、データ行をテーブル `test_tbl5` に挿入します。

    ```SQL
    -- Create a table.
    CREATE TABLE test_tbl5
    (
        id BIGINT NOT NULL,
        name BIGINT NOT NULL,
        job1 BIGINT NOT NULL AUTO_INCREMENT,
        job2 BIGINT NOT NULL
    )
    PRIMARY KEY (id, name)
    DISTRIBUTED BY HASH(id)
    PROPERTIES("replicated_storage" = "true");

    -- Prepare data.
    mysql > INSERT INTO test_tbl5 VALUES (0, 0, -1, -1);
    Query OK, 1 row affected (0.04 sec)
    {'label':'insert_458d9487-80f6-11ed-ae56-aa528ccd0ebf', 'status':'VISIBLE', 'txnId':'94'}

    -- Query the table.
    mysql > SELECT * FROM test_tbl5 ORDER BY id;
    +------+------+------+------+
    | id   | name | job1 | job2 |
    +------+------+------+------+
    |    0 |    0 |   -1 |   -1 |
    +------+------+------+------+
    1 row in set (0.01 sec)
    ```

2. テーブル `test_tbl5` を更新するための CSV ファイル **my_data5.csv** を準備します。CSV ファイルには、`AUTO_INCREMENT` カラム `job1` の値が含まれていません。最初の行の主キーはテーブルに既に存在しますが、2 番目と 3 番目の行の主キーは存在しません。

    ```Plaintext
    0,0,99
    1,1,99
    2,2,99
    ```

3. [Stream Load](../loading_unloading/STREAM_LOAD.md) ジョブを実行して、CSV ファイルからテーブル `test_tbl5` にデータをロードします。

    ```Bash
    curl --location-trusted -u <username>:<password> -H "label:2" \
        -H "column_separator:," \
        -H "partial_update:true" \
        -H "columns: id,name,job2" \
        -T my_data5.csv -XPUT \
        http://<fe_host>:<fe_http_port>/api/example_db/test_tbl5/_stream_load
    ```

4. 更新されたテーブルをクエリします。最初の行のデータはテーブル `test_tbl5` に既に存在するため、`AUTO_INCREMENT` カラム `job1` は元の値を保持します。2 番目と 3 番目の行のデータは新しく挿入されるため、StarRocks は `AUTO_INCREMENT` カラム `job1` の新しい値を生成します。

    ```SQL
    mysql > SELECT * FROM test_tbl5 ORDER BY id;
    +------+------+--------+------+
    | id   | name | job1   | job2 |
    +------+------+--------+------+
    |    0 |    0 |     -1 |   99 |
    |    1 |    1 |      1 |   99 |
    |    2 |    2 | 100001 |   99 |
    +------+------+--------+------+
    3 rows in set (0.01 sec)
    ```

## 制限事項

- `AUTO_INCREMENT` カラムを持つテーブルを作成する場合は、すべてのレプリカが同じ自動インクリメント ID を持つように、`'replicated_storage' = 'true'` を設定する必要があります。
- 各テーブルに含めることができる `AUTO_INCREMENT` カラムは 1 つのみです。
- `AUTO_INCREMENT` カラムのデータ型は BIGINT である必要があります。
- `AUTO_INCREMENT` カラムは `NOT NULL` であり、デフォルト値を持つことはできません。
- `AUTO_INCREMENT` カラムを持つ Primary Key テーブルからデータを削除できます。ただし、`AUTO_INCREMENT` カラムが主キーではないか、主キーの一部ではない場合は、次のシナリオでデータを削除するときに、次の制限事項に注意する必要があります。

  - DELETE 操作中に、UPSERT 操作のみを含む部分更新のロードジョブもあります。UPSERT 操作と DELETE 操作の両方が同じデータ行にヒットし、UPSERT 操作が DELETE 操作の後に実行される場合、UPSERT 操作は有効にならない可能性があります。
  - 部分更新のロードジョブがあり、同じデータ行に対して複数の UPSERT 操作と DELETE 操作が含まれています。特定の UPSERT 操作が DELETE 操作の後に実行される場合、UPSERT 操作は有効にならない可能性があります。

- ALTER TABLE を使用して `AUTO_INCREMENT` 属性を追加することはサポートされていません。
- バージョン 3.1 以降、StarRocks の共有データモードは `AUTO_INCREMENT` 属性をサポートしています。
- バージョン 3.1 以降、StarRocks の共有データは `AUTO_INCREMENT` 属性をサポートしています。
- StarRocks は、`AUTO_INCREMENT` カラムの開始値とステップサイズの指定をサポートしていません。

## キーワード

AUTO_INCREMENT, AUTO INCREMENT