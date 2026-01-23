---
displayed_sidebar: docs
---

# transform_keys

使用 [Lambda 表达式](../Lambda_expression.md)转换 map 中的 key，并为 map 中的每个条目生成一个新的 key。

该函数从 v3.1 版本开始支持。

## 语法

```Haskell
MAP transform_keys(lambda_func, any_map)
```

`lambda_func` 也可以放在 `any_map` 之后：

```Haskell
MAP transform_keys(any_map, lambda_func)
```

## 参数

- `any_map`: Map。

- `lambda_func`: 要应用于 `any_map` 的 Lambda 表达式。

## 返回值

返回一个 map 值，其中 key 的数据类型由 Lambda 表达式的结果决定，value 的数据类型与 `any_map` 中的 value 相同。

如果任何输入参数为 NULL，则返回 NULL。

如果原始 map 中的 key 或 value 为 NULL，则 NULL 将被视为正常值处理。

Lambda 表达式必须有两个参数。第一个参数表示 key。第二个参数表示 value。

## 示例

以下示例使用 [map_from_arrays](map_from_arrays.md) 生成一个 map 值 `{1:"ab",3:"cdd",2:null,null:"abc"}`。然后，将 Lambda 表达式应用于每个 key，使 key 递增 1。

```SQL
mysql> select transform_keys((k,v)->(k+1), col_map) from (select map_from_arrays([1,3,null,2,null],['ab','cdd',null,null,'abc']) as col_map)A;
+------------------------------------------+
| transform_keys((k, v) -> k + 1, col_map) |
+------------------------------------------+
| {2:"ab",4:"cdd",3:null,null:"abc"}       |
+------------------------------------------+