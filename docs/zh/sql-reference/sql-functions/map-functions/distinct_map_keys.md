---
displayed_sidebar: docs
---

# distinct_map_keys

删除 map 中的重复键，因为从语义上来说，map 中的键必须是唯一的。此函数仅保留相同键的最后一个值，称为 LAST WIN。当从外部表查询 MAP 数据，并且 map 中存在重复键时，可以使用此函数。 StarRocks 内表本身可以删除 map 中的重复键。

该函数从 v3.1 版本开始支持。

## 语法

```Haskell
distinct_map_keys(any_map)
```

## 参数

`any_map`: 要从中删除重复键的 MAP 值。

## 返回值

返回一个新 map，其中每个 map 都没有重复的键。

如果输入为 NULL，则返回 NULL。

## 示例

示例 1：简单用法。

```plain
select distinct_map_keys(map{"a":1,"a":2});
+-------------------------------------+
| distinct_map_keys(map{'a':1,'a':2}) |
+-------------------------------------+
| {"a":2}                             |
+-------------------------------------+
```

示例 2：从外部表查询 MAP 数据，并删除 `col_map` 列中的重复键。

```plain
select distinct_map_keys(col_map) as unique, col_map from external_table;
+---------------+---------------+
|      unique   | col_map       |
+---------------+---------------+
|       {"c":2} | {"c":1,"c":2} |
|           NULL|          NULL |
| {"e":4,"d":5} | {"e":4,"d":5} |
+---------------+---------------+
3 rows in set (0.05 sec)