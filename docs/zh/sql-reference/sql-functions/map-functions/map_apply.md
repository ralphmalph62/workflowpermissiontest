---
displayed_sidebar: docs
---

# map_apply

将 [Lambda expression](../Lambda_expression.md) 应用于原始 Map 的键和值，并生成新的 Map。此函数从 v3.0 版本开始支持。

## 语法

```Haskell
MAP map_apply(lambda_func, any_map)
```

## 参数

- `lambda_func`: Lambda 表达式。

- `any_map`: 要应用 Lambda 表达式的 map。

## 返回值

返回一个 map 值。结果 map 中键和值的数据类型由 Lambda 表达式的结果决定。

如果任何输入参数为 NULL，则返回 NULL。

如果原始 map 中的键或值为 NULL，则 NULL 将作为正常值处理。

Lambda 表达式必须有两个参数。第一个参数表示键。第二个参数表示值。

## 示例

以下示例使用 [map_from_arrays()](map_from_arrays.md) 生成一个 map 值 `{1:"ab",3:"cd"}`。然后，Lambda 表达式将每个键递增 1，并计算每个值的长度。例如，"ab" 的长度为 2。

```SQL
mysql> select map_apply((k,v)->(k+1,length(v)), col_map)
from (select map_from_arrays([1,3],["ab","cd"]) as col_map)A;
+--------------------------------------------------+
| map_apply((k, v) -> (k + 1, length(v)), col_map) |
+--------------------------------------------------+
| {2:2,4:2}                                        |
+--------------------------------------------------+
1 row in set (0.01 sec)

mysql> select map_apply((k,v)->(k+1,length(v)), col_map)
from (select map_from_arrays(null,null) as col_map)A;
+--------------------------------------------------+
| map_apply((k, v) -> (k + 1, length(v)), col_map) |
+--------------------------------------------------+
| NULL                                             |
+--------------------------------------------------+
1 row in set (0.02 sec)

mysql> select map_apply((k,v)->(k+1,length(v)), col_map)
from (select map_from_arrays([1,null],["ab","cd"]) as col_map)A;
+--------------------------------------------------+
| map_apply((k, v) -> (k + 1, length(v)), col_map) |
+--------------------------------------------------+
| NULL                                             |
+--------------------------------------------------+
```