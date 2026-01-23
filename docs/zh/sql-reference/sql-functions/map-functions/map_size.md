---
displayed_sidebar: docs
---

# map_size

返回 MAP 值中元素的数量。MAP 是键值对的无序集合，例如，`{"a":1, "b":2}`。一个键值对构成一个元素，例如，`{"a":1, "b":2}` 包含两个元素。

此函数具有别名 [cardinality()](cardinality.md)。自 v2.5 起支持。

## 语法

```Haskell
INT map_size(any_map)
```

## 参数

`any_map`: 要从中检索元素数量的 MAP 值。

## 返回值

返回 INT 类型的值。

如果输入为 NULL，则返回 NULL。

如果 MAP 值中的键或值为 NULL，则 NULL 将被视为正常值。

## 示例

### 从 StarRocks 内表查询 MAP 数据

从 v3.1 开始，StarRocks 支持在创建表时定义 MAP 列。此示例使用表 `test_map`，其中包含以下数据：

```Plain
CREATE TABLE test_map(
    col_int INT,
    col_map MAP<VARCHAR(50),INT>
  )
DUPLICATE KEY(col_int);

INSERT INTO test_map VALUES
(1,map{"a":1,"b":2}),
(2,map{"c":3}),
(3,map{"d":4,"e":5});

SELECT * FROM test_map ORDER BY col_int;
+---------+---------------+
| col_int | col_map       |
+---------+---------------+
|       1 | {"a":1,"b":2} |
|       2 | {"c":3}       |
|       3 | {"d":4,"e":5} |
+---------+---------------+
3 rows in set (0.05 sec)
```

获取 `col_map` 列中每一行的元素数量。

```Plaintext
select map_size(col_map) from test_map order by col_int;
+-------------------+
| map_size(col_map) |
+-------------------+
|                 2 |
|                 1 |
|                 2 |
+-------------------+
3 rows in set (0.05 sec)
```

### 从数据湖查询 MAP 数据

此示例使用 Hive 表 `hive_map`，其中包含以下数据：

```Plaintext
SELECT * FROM hive_map ORDER BY col_int;
+---------+---------------+
| col_int | col_map       |
+---------+---------------+
|       1 | {"a":1,"b":2} |
|       2 | {"c":3}       |
|       3 | {"d":4,"e":5} |
+---------+---------------+
```

在您的集群中创建 [Hive catalog](../../../data_source/catalog/hive_catalog.md#create-a-hive-catalog) 之后，您可以使用此 catalog 和 map_size() 函数来获取 `col_map` 列中每一行的元素数量。

```Plaintext
select map_size(col_map) from hive_map order by col_int;
+-------------------+
| map_size(col_map) |
+-------------------+
|                 2 |
|                 1 |
|                 2 |
+-------------------+
3 rows in set (0.05 sec)