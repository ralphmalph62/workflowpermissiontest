---
displayed_sidebar: docs
---

# `AUTO_INCREMENT`

自 3.0 版本起，StarRocks 支持 `AUTO_INCREMENT` 列属性，可以简化数据管理。本文档介绍 `AUTO_INCREMENT` 列属性的应用场景、用法和特性。

## 介绍

当新的数据行被导入到表中，并且没有为 `AUTO_INCREMENT` 列指定值时，StarRocks 会自动为该行的 `AUTO_INCREMENT` 列分配一个整数值，作为其在整个表中的唯一 ID。后续的 `AUTO_INCREMENT` 列的值将从该行的 ID 开始，以特定的步长自动递增。`AUTO_INCREMENT` 列可用于简化数据管理并加速某些查询。以下是 `AUTO_INCREMENT` 列的一些应用场景：

- 作为主键：`AUTO_INCREMENT` 列可以用作主键，以确保每行都有唯一的 ID，并方便查询和管理数据。
- 关联表：当多个表进行关联时，`AUTO_INCREMENT` 列可以用作关联键，与使用数据类型为 STRING 的列（例如 UUID）相比，可以加快查询速度。
- 统计高基数列中的不同值数量：`AUTO_INCREMENT` 列可用于表示字典中的唯一值列。与直接统计不同的 STRING 值相比，统计 `AUTO_INCREMENT` 列的不同整数值有时可以将查询速度提高几倍甚至几十倍。

您需要在 CREATE TABLE 语句中指定 `AUTO_INCREMENT` 列。`AUTO_INCREMENT` 列的数据类型必须为 BIGINT。AUTO_INCREMENT 列的值可以[隐式分配或显式指定](#assign-values-for-auto_increment-column)。它从 1 开始，并且每个新行递增 1。

## 基本操作

### 在创建表时指定 `AUTO_INCREMENT` 列

创建一个名为 `test_tbl1` 的表，其中包含两列 `id` 和 `number`。将列 `number` 指定为 `AUTO_INCREMENT` 列。

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

### 为 `AUTO_INCREMENT` 列赋值

#### 隐式赋值

当您将数据导入到 StarRocks 表中时，无需为 `AUTO_INCREMENT` 列指定值。StarRocks 会自动为该列分配唯一的整数值，并将它们插入到表中。

```SQL
INSERT INTO test_tbl1 (id) VALUES (1);
INSERT INTO test_tbl1 (id) VALUES (2);
INSERT INTO test_tbl1 (id) VALUES (3),(4),(5);
```

查看表中的数据。

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

当您将数据导入到 StarRocks 表中时，您还可以为 `AUTO_INCREMENT` 列指定值 `DEFAULT`。StarRocks 会自动为该列分配唯一的整数值，并将它们插入到表中。

```SQL
INSERT INTO test_tbl1 (id, number) VALUES (6, DEFAULT);
```

查看表中的数据。

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

在实际使用中，当您查看表中的数据时，可能会返回以下结果。这是因为 StarRocks 无法保证 `AUTO_INCREMENT` 列的值是严格单调的。但是 StarRocks 可以保证这些值大致按时间顺序递增。有关更多信息，请参见[单调性](#monotonicity)。

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

#### 显式赋值

您还可以显式地为 `AUTO_INCREMENT` 列指定值，并将它们插入到表中。

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

此外，显式指定值不会影响 StarRocks 为新插入的数据行生成的后续值。

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

建议您不要同时使用隐式赋值和显式指定的值来设置 `AUTO_INCREMENT` 列。因为指定的值可能与 StarRocks 生成的值相同，从而破坏[自增 ID 的全局唯一性](#uniqueness)。

## 基本特性

### 唯一性

通常，StarRocks 保证 `AUTO_INCREMENT` 列的值在整个表中是全局唯一的。建议您不要同时隐式赋值和显式指定 `AUTO_INCREMENT` 列的值。如果这样做，可能会破坏自增 ID 的全局唯一性。这是一个简单的示例：创建一个名为 `test_tbl2` 的表，其中包含两列 `id` 和 `number`。将列 `number` 指定为 `AUTO_INCREMENT` 列。

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

在表 `test_tbl2` 中，隐式赋值和显式指定 `AUTO_INCREMENT` 列 `number` 的值。

```SQL
INSERT INTO test_tbl2 (id, number) VALUES (1, DEFAULT);
INSERT INTO test_tbl2 (id, number) VALUES (2, 2);
INSERT INTO test_tbl2 (id) VALUES (3);
```

查询表 `test_tbl2`。

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

### 单调性

为了提高分配自增 ID 的性能，BE 会在本地缓存一些自增 ID。在这种情况下，StarRocks 无法保证 `AUTO_INCREMENT` 列的值是严格单调的。只能保证这些值大致按时间顺序递增。

> **注意**
>
> BE 缓存的自增 ID 的数量由 FE 动态参数 `auto_increment_cache_size` 决定，默认为 `100,000`。您可以使用 `ADMIN SET FRONTEND CONFIG ("auto_increment_cache_size" = "xxx");` 修改该值。

例如，一个 StarRocks 集群有一个 FE 节点和两个 BE 节点。创建一个名为 `test_tbl3` 的表，并插入五行数据，如下所示：

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

表 `test_tbl3` 中的自增 ID 不会单调递增，因为两个 BE 节点分别缓存自增 ID [1, 100000] 和 [100001, 200000]。当使用多个 INSERT 语句加载数据时，数据会被发送到不同的 BE 节点，这些节点独立分配自增 ID。因此，无法保证自增 ID 是严格单调的。

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

## 部分更新和 `AUTO_INCREMENT` 列

本节介绍如何仅更新包含 `AUTO_INCREMENT` 列的表中的一些指定列。

> **注意**
>
> 目前，只有主键表支持部分更新。

### `AUTO_INCREMENT` 列是主键

您需要在部分更新期间指定主键。因此，如果 `AUTO_INCREMENT` 列是主键或主键的一部分，则部分更新的用户行为与未定义 `AUTO_INCREMENT` 列时完全相同。

1. 在数据库 `example_db` 中创建一个表 `test_tbl4`，并插入一行数据。

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

2. 准备 CSV 文件 **my_data4.csv** 以更新表 `test_tbl4`。CSV 文件包含 `AUTO_INCREMENT` 列的值，但不包含列 `job1` 的值。第一行的主键已存在于表 `test_tbl4` 中，而第二行的主键不存在于表中。

    ```Plaintext
    0,0,99
    1,1,99
    ```

3. 运行 [Stream Load](../loading_unloading/STREAM_LOAD.md) 作业，并使用 CSV 文件更新表 `test_tbl4`。

    ```Bash
    curl --location-trusted -u <username>:<password> -H "label:1" \
        -H "column_separator:," \
        -H "partial_update:true" \
        -H "columns:id,name,job2" \
        -T my_data4.csv -XPUT \
        http://<fe_host>:<fe_http_port>/api/example_db/test_tbl4/_stream_load
    ```

4. 查询更新后的表。第一行数据已存在于表 `test_tbl4` 中，并且列 `job1` 的值保持不变。新插入第二行数据，并且由于未指定列 `job1` 的默认值，因此部分更新框架直接将此列的值设置为 `0`。

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

### `AUTO_INCREMENT` 列不是主键

如果 `AUTO_INCREMENT` 列不是主键或主键的一部分，并且在 Stream Load 作业中未提供自增 ID，则会发生以下情况：

- 如果该行已存在于表中，则 StarRocks 不会更新自增 ID。
- 如果该行是新加载到表中的，则 StarRocks 会生成一个新的自增 ID。

此功能可用于构建字典表，以快速计算不同的 STRING 值。

1. 在数据库 `example_db` 中，创建一个表 `test_tbl5`，并将列 `job1` 指定为 `AUTO_INCREMENT` 列，并将一行数据插入到表 `test_tbl5` 中。

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

2. 准备一个 CSV 文件 **my_data5.csv** 以更新表 `test_tbl5`。CSV 文件不包含 `AUTO_INCREMENT` 列 `job1` 的值。第一行的主键已存在于表中，而第二行和第三行的主键不存在。

    ```Plaintext
    0,0,99
    1,1,99
    2,2,99
    ```

3. 运行 [Stream Load](../loading_unloading/STREAM_LOAD.md) 作业以将数据从 CSV 文件加载到表 `test_tbl5` 中。

    ```Bash
    curl --location-trusted -u <username>:<password> -H "label:2" \
        -H "column_separator:," \
        -H "partial_update:true" \
        -H "columns: id,name,job2" \
        -T my_data5.csv -XPUT \
        http://<fe_host>:<fe_http_port>/api/example_db/test_tbl5/_stream_load
    ```

4. 查询更新后的表。第一行数据已存在于表 `test_tbl5` 中，因此 `AUTO_INCREMENT` 列 `job1` 保留其原始值。第二行和第三行数据是新插入的，因此 StarRocks 为 `AUTO_INCREMENT` 列 `job1` 生成新值。

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

## 限制

- 创建具有 `AUTO_INCREMENT` 列的表时，必须设置 `'replicated_storage' = 'true'`，以确保所有副本都具有相同的自增 ID。
- 每个表只能有一个 `AUTO_INCREMENT` 列。
- `AUTO_INCREMENT` 列的数据类型必须为 BIGINT。
- `AUTO_INCREMENT` 列必须为 `NOT NULL`，并且没有默认值。
- 您可以从具有 `AUTO_INCREMENT` 列的主键表中删除数据。但是，如果 `AUTO_INCREMENT` 列不是主键或主键的一部分，则在以下情况下删除数据时，您需要注意以下限制：

  - 在 DELETE 操作期间，还有一个用于部分更新的导入作业，该作业仅包含 UPSERT 操作。如果 UPSERT 和 DELETE 操作都命中同一数据行，并且 UPSERT 操作在 DELETE 操作之后执行，则 UPSERT 操作可能不会生效。
  - 有一个用于部分更新的导入作业，其中包括对同一数据行的多个 UPSERT 和 DELETE 操作。如果在 DELETE 操作之后执行某个 UPSERT 操作，则该 UPSERT 操作可能不会生效。

- 不支持使用 ALTER TABLE 添加 `AUTO_INCREMENT` 属性。
- 从 3.1 版本开始，StarRocks 的存算分离模式支持 `AUTO_INCREMENT` 属性。
- 从 3.1 版本开始，StarRocks 的存算分离支持 `AUTO_INCREMENT` 属性。
- StarRocks 不支持指定 `AUTO_INCREMENT` 列的起始值和步长。

## 关键词

AUTO_INCREMENT, AUTO INCREMENT