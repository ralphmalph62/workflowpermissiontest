---
displayed_sidebar: docs
---

# map_keys

指定されたマップ内のすべてのキーの配列を返します。

この関数は v2.5 からサポートされています。

## 構文

```Haskell
map_keys(any_map)
```

## パラメータ

`any_map`: キーを取得する MAP 値。

## 戻り値

戻り値は `array<keyType>` 形式です。配列内の要素の型は、マップ内のキーの型と一致します。

入力が NULL の場合、NULL が返されます。MAP 値のキーまたは値が NULL の場合、NULL は通常の値として処理され、結果に含まれます。

## 例

### StarRocks の 内部テーブル から MAP データをクエリする

v3.1 以降、StarRocks はテーブルの作成時に MAP 列の定義をサポートしています。この例では、次のデータを含むテーブル `test_map` を使用します。

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

`col_map` 列の各行からすべてのキーを取得します。

```Plaintext
select map_keys(col_map) from test_map order by col_int;
+-------------------+
| map_keys(col_map) |
+-------------------+
| ["a","b"]         |
| ["c"]             |
| ["d","e"]         |
+-------------------+
3 rows in set (0.05 sec)
```

### データレイクから MAP データをクエリする

この例では、次のデータを含む Hive テーブル `hive_map` を使用します。

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

[Hive catalog](../../../data_source/catalog/hive_catalog.md #create-a-hive-catalog) がクラスタに作成された後、この catalog と map_keys() 関数を使用して、`col_map` 列の各行からすべてのキーを取得できます。

```Plaintext
select map_keys(col_map) from hive_map order by col_int;
+-------------------+
| map_keys(col_map) |
+-------------------+
| ["a","b"]         |
| ["c"]             |
| ["d","e"]         |
+-------------------+
3 rows in set (0.05 sec)
```