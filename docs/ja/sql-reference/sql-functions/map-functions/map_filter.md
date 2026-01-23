---
displayed_sidebar: docs
---

# map_filter

Boolean配列または [Lambda expression](../Lambda_expression.md) を各キーと値のペアに適用して、map内のキーと値のペアをフィルタリングします。`true` と評価されるペアが返されます。

この関数は v3.1 以降でサポートされています。

## 構文

```Haskell
MAP map_filter(any_map, array<boolean>)
MAP map_filter(lambda_func, any_map)
```

- `map_filter(any_map, array<boolean>)`

  `any_map` 内のキーと値のペアを `array<boolean>` と照らし合わせて 1 つずつ評価し、`true` と評価されるキーと値のペアを返します。

- `map_filter(lambda_func, any_map)`

  `lambda_func` を `any_map` 内のキーと値のペアに 1 つずつ適用し、結果が `true` であるキーと値のペアを返します。

## パラメータ

- `any_map`: map の値。

- `array<boolean>`: map 値の評価に使用される Boolean 配列。

- `lambda_func`: map 値の評価に使用される Lambda expression。

## 戻り値

データ型が `any_map` と同じ map を返します。

`any_map` が NULL の場合、NULL が返されます。`array<boolean>` が null の場合、空の map が返されます。

map 値のキーまたは値が NULL の場合、NULL は通常の値として処理されます。

Lambda expression には 2 つのパラメータが必要です。最初のパラメータはキーを表します。2 番目のパラメータは値を表します。

## 例

### `array<boolean>` を使用する

次の例では、[map_from_arrays()](map_from_arrays.md) を使用して、map 値 `{1:"ab",3:"cdd",2:null,null:"abc"}` を生成します。次に、各キーと値のペアが `array<boolean>` と照らし合わせて評価され、結果が `true` であるペアが返されます。

```SQL
mysql> select map_filter(col_map, array<boolean>[0,0,0,1,1]) from (select map_from_arrays([1,3,null,2,null],['ab','cdd',null,null,'abc']) as col_map)A;
+----------------------------------------------------+
| map_filter(col_map, ARRAY<BOOLEAN>[0, 0, 0, 1, 1]) |
+----------------------------------------------------+
| {null:"abc"}                                       |
+----------------------------------------------------+
1 row in set (0.02 sec)

mysql> select map_filter(null, array<boolean>[0,0,0,1,1]);
+-------------------------------------------------+
| map_filter(NULL, ARRAY<BOOLEAN>[0, 0, 0, 1, 1]) |
+-------------------------------------------------+
| NULL                                            |
+-------------------------------------------------+
1 row in set (0.02 sec)

mysql> select map_filter(col_map, null) from (select map_from_arrays([1,3,null,2,null],['ab','cdd',null,null,'abc']) as col_map)A;
+---------------------------+
| map_filter(col_map, NULL) |
+---------------------------+
| {}                        |
+---------------------------+
1 row in set (0.01 sec)
```

### Lambda expression を使用する

次の例では、map_from_arrays() を使用して、map 値 `{1:"ab",3:"cdd",2:null,null:"abc"}` を生成します。次に、各キーと値のペアが Lambda expression と照らし合わせて評価され、値が null でないキーと値のペアが返されます。

```SQL

mysql> select map_filter((k,v) -> v is not null,col_map) from (select map_from_arrays([1,3,null,2,null],['ab','cdd',null,null,'abc']) as col_map)A;
+------------------------------------------------+
| map_filter((k,v) -> v is not null, col_map)    |
+------------------------------------------------+
| {1:"ab",3:"cdd",null:'abc'}                        |
+------------------------------------------------+
1 row in set (0.02 sec)
```