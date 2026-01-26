---
displayed_sidebar: docs
---

# Strict mode

Strict mode 是一个可选属性，您可以为数据导入配置它。它会影响导入行为和最终导入的数据。

本主题介绍 strict mode 是什么以及如何设置 strict mode。

## 了解 strict mode

在数据导入期间，源列的数据类型可能与目标列的数据类型不完全一致。在这种情况下，StarRocks 会对数据类型不一致的源列值执行转换。由于各种问题，例如不匹配的字段数据类型和字段长度溢出，数据转换可能会失败。未能正确转换的源列值是不合格的列值，包含不合格列值的源行被称为“不合格行”。Strict mode 用于控制在数据导入期间是否过滤掉不合格的行。

Strict mode 的工作方式如下：

- 如果启用了 strict mode，StarRocks 仅导入合格的行。它会过滤掉不合格的行，并返回有关不合格行的详细信息。
- 如果禁用了 strict mode，StarRocks 会将不合格的列值转换为 `NULL`，并将包含这些 `NULL` 值的不合格行与合格行一起导入。

请注意以下几点：

- 在实际业务场景中，合格行和不合格行都可能包含 `NULL` 值。如果目标列不允许 `NULL` 值，StarRocks 会报告错误并过滤掉包含 `NULL` 值的行。

- 可以为导入作业过滤掉的不合格行的最大百分比由可选作业属性 `max_filter_ratio` 控制。

:::note

从 v3.4.0 开始支持 INSERT 的 `max_filter_ratio` 属性。

:::

例如，您想要将 CSV 格式的数据文件中的四行数据（分别包含 `\N`（`\N` 表示 `NULL` 值）、`abc`、`2000` 和 `1` 值）导入到 StarRocks 表的某一列中，并且目标 StarRocks 表列的数据类型为 TINYINT [-128, 127]。

- 源列值 `\N` 在转换为 TINYINT 时会被处理为 `NULL`。

  > **NOTE**
  >
  > 无论目标数据类型如何，`\N` 在转换时始终会被处理为 `NULL`。

- 源列值 `abc` 会被处理为 `NULL`，因为其数据类型不是 TINYINT 并且转换失败。

- 源列值 `2000` 会被处理为 `NULL`，因为它超出了 TINYINT 支持的范围并且转换失败。

- 源列值 `1` 可以被正确转换为 TINYINT 类型的值 `1`。

如果禁用了 strict mode，StarRocks 会导入所有这四行数据。

如果启用了 strict mode，StarRocks 仅导入包含 `\N` 或 `1` 的行，并过滤掉包含 `abc` 或 `2000` 的行。过滤掉的行会计入 `max_filter_ratio` 参数指定的最大行百分比，这些行由于数据质量不足而被过滤掉。

### 禁用 strict mode 后最终导入的数据

| 源列值 | 转换为 TINYINT 后的列值 | 目标列允许 NULL 值时的导入结果 | 目标列不允许 NULL 值时的导入结果 |
| ------------------- | --------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------ |
| \N                 | NULL                                    | 导入 `NULL` 值。                            | 报告错误。                                        |
| abc                 | NULL                                    | 导入 `NULL` 值。                            | 报告错误。                                        |
| 2000                | NULL                                    | 导入 `NULL` 值。                            | 报告错误。                                        |
| 1                   | 1                                       | 导入 `1` 值。                               | 导入 `1` 值。                                     |

### 启用 strict mode 后最终导入的数据

| 源列值 | 转换为 TINYINT 后的列值 | 目标列允许 NULL 值时的导入结果       | 目标列不允许 NULL 值时的导入结果 |
| ------------------- | --------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| \N                 | NULL                                    | 导入 `NULL` 值。                                  | 报告错误。                                        |
| abc                 | NULL                                    | 不允许 `NULL` 值，因此被过滤掉。 | 报告错误。                                        |
| 2000                | NULL                                    | 不允许 `NULL` 值，因此被过滤掉。 | 报告错误。                                        |
| 1                   | 1                                       | 导入 `1` 值。                                     | 导入 `1` 值。                                     |

## 设置 strict mode

您可以使用 `strict_mode` 参数为导入作业设置 strict mode。有效值为 `true` 和 `false`。默认值为 `false`。值 `true` 启用 strict mode，值 `false` 禁用 strict mode。请注意，从 v3.4.0 开始支持 INSERT 的 `strict_mode` 参数，默认值为 `true`。现在，除了 Stream Load 之外，对于所有其他导入方法，`strict_mode` 在 PROPERTIES 子句中以相同的方式设置。

您还可以使用 `enable_insert_strict` 会话变量来设置 strict mode。有效值为 `true` 和 `false`。默认值为 `true`。值 `true` 启用 strict mode，值 `false` 禁用 strict mode。

:::note

从 v3.4.0 开始，当 `enable_insert_strict` 设置为 `true` 时，系统仅导入合格的行。它会过滤掉不合格的行，并返回有关不合格行的详细信息。相反，在早于 v3.4.0 的版本中，当 `enable_insert_strict` 设置为 `true` 时，如果存在不合格的行，则 INSERT 作业会失败。

:::

示例如下：

### Stream Load

```Bash
curl --location-trusted -u <username>:<password> \
    -H "strict_mode: {true | false}" \
    -T <file_name> -XPUT \
    http://<fe_host>:<fe_http_port>/api/<database_name>/<table_name>/_stream_load
```

有关 Stream Load 的详细语法和参数，请参见 [STREAM LOAD](../../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md)。

### Broker Load

```SQL
LOAD LABEL [<database_name>.]<label_name>
(
    DATA INFILE ("<file_path>"[, "<file_path>" ...])
    INTO TABLE <table_name>
)
WITH BROKER
(
    "username" = "<hdfs_username>",
    "password" = "<hdfs_password>"
)
PROPERTIES
(
    "strict_mode" = "{true | false}"
)
```

上面的代码片段使用 HDFS 作为示例。有关 Broker Load 的详细语法和参数，请参见 [BROKER LOAD](../../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md)。

### Routine Load

```SQL
CREATE ROUTINE LOAD [<database_name>.]<job_name> ON <table_name>
PROPERTIES
(
    "strict_mode" = "{true | false}"
) 
FROM KAFKA
(
    "kafka_broker_list" ="<kafka_broker1_ip>:<kafka_broker1_port>[,<kafka_broker2_ip>:<kafka_broker2_port>...]",
    "kafka_topic" = "<topic_name>"
)
```

上面的代码片段使用 Apache Kafka® 作为示例。有关 Routine Load 的详细语法和参数，请参见 [CREATE ROUTINE LOAD](../../sql-reference/sql-statements/loading_unloading/routine_load/CREATE_ROUTINE_LOAD.md)。

### Spark Load

```SQL
LOAD LABEL [<database_name>.]<label_name>
(
    DATA INFILE ("<file_path>"[, "<file_path>" ...])
    INTO TABLE <table_name>
)
WITH RESOURCE <resource_name>
(
    "spark.executor.memory" = "3g",
    "broker.username" = "<hdfs_username>",
    "broker.password" = "<hdfs_password>"
)
PROPERTIES
(
    "strict_mode" = "{true | false}"   
)
```

上面的代码片段使用 HDFS 作为示例。有关 Spark Load 的详细语法和参数，请参见 [SPARK LOAD](../../sql-reference/sql-statements/loading_unloading/SPARK_LOAD.md)。

### INSERT

```SQL
INSERT INTO [<database_name>.]<table_name>
PROPERTIES(
    "strict_mode" = "{true | false}"
)
<query_statement>
```

有关 INSERT 的详细语法和参数，请参见 [INSERT](../../sql-reference/sql-statements/loading_unloading/INSERT.md)。