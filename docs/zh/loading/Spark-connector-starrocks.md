---
displayed_sidebar: docs
---

# 使用 Spark Connector 导入数据 (推荐)

StarRocks 提供了一个自主开发的 Connector，名为 StarRocks Connector for Apache Spark™ (简称 Spark Connector)，以帮助您使用 Spark 将数据导入到 StarRocks 表中。其基本原理是先积累数据，然后通过 [STREAM LOAD](../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md) 一次性将所有数据导入到 StarRocks 中。Spark Connector 基于 Spark DataSource V2 实现。DataSource 可以使用 Spark DataFrames 或 Spark SQL 创建。同时支持批量和结构化流模式。

> **注意**
>
> 只有对 StarRocks 表具有 SELECT 和 INSERT 权限的用户才能将数据导入到该表。您可以按照 [GRANT](../sql-reference/sql-statements/account-management/GRANT.md) 中提供的说明，将这些权限授予用户。

## 版本要求

| Spark connector | Spark            | StarRocks     | Java | Scala |
| --------------- | ---------------- | ------------- | ---- | ----- |
| 1.1.2           | 3.2, 3.3, 3.4, 3.5 | 2.5 及更高版本   | 8    | 2.12  |
| 1.1.1           | 3.2, 3.3, or 3.4 | 2.5 及更高版本 | 8    | 2.12  |
| 1.1.0           | 3.2, 3.3, or 3.4 | 2.5 及更高版本 | 8    | 2.12  |

> **注意**
>
> - 请参阅 [升级 Spark connector](#upgrade-spark-connector) 以了解不同版本的 Spark Connector 之间的行为变更。
> - 从 1.1.1 版本开始，Spark Connector 不提供 MySQL JDBC 驱动程序，您需要手动将驱动程序导入到 Spark classpath 中。您可以在 [MySQL site](https://dev.mysql.com/downloads/connector/j/) 或 [Maven Central](https://repo1.maven.org/maven2/mysql/mysql-connector-java/) 上找到该驱动程序。

## 获取 Spark connector

您可以通过以下方式获取 Spark Connector JAR 文件：

- 直接下载已编译的 Spark Connector JAR 文件。
- 在您的 Maven 项目中添加 Spark Connector 作为依赖项，然后下载 JAR 文件。
- 自行将 Spark Connector 的源代码编译为 JAR 文件。

Spark Connector JAR 文件的命名格式为 `starrocks-spark-connector-${spark_version}_${scala_version}-${connector_version}.jar`。

例如，如果您在您的环境中安装了 Spark 3.2 和 Scala 2.12，并且您想使用 Spark Connector 1.1.0，您可以使用 `starrocks-spark-connector-3.2_2.12-1.1.0.jar`。

> **注意**
>
> 通常，最新版本的 Spark Connector 仅保持与最近三个版本的 Spark 的兼容性。

### 下载已编译的 Jar 文件

直接从 [Maven Central Repository](https://repo1.maven.org/maven2/com/starrocks) 下载相应版本的 Spark Connector JAR。

### Maven 依赖

1. 在您的 Maven 项目的 `pom.xml` 文件中，按照以下格式添加 Spark Connector 作为依赖项。将 `spark_version`、`scala_version` 和 `connector_version` 替换为相应的版本。

    ```xml
    <dependency>
    <groupId>com.starrocks</groupId>
    <artifactId>starrocks-spark-connector-${spark_version}_${scala_version}</artifactId>
    <version>${connector_version}</version>
    </dependency>
    ```

2. 例如，如果您的环境中的 Spark 版本是 3.2，Scala 版本是 2.12，并且您选择 Spark Connector 1.1.0，您需要添加以下依赖项：

    ```xml
    <dependency>
    <groupId>com.starrocks</groupId>
    <artifactId>starrocks-spark-connector-3.2_2.12</artifactId>
    <version>1.1.0</version>
    </dependency>
    ```

### 自行编译

1. 下载 [Spark connector package](https://github.com/StarRocks/starrocks-connector-for-apache-spark)。
2. 执行以下命令将 Spark Connector 的源代码编译为 JAR 文件。请注意，`spark_version` 替换为相应的 Spark 版本。

      ```bash
      sh build.sh <spark_version>
      ```

   例如，如果您的环境中的 Spark 版本是 3.2，您需要执行以下命令：

      ```bash
      sh build.sh 3.2
      ```

3. 转到 `target/` 目录以查找 Spark Connector JAR 文件，例如编译后生成的 `starrocks-spark-connector-3.2_2.12-1.1.0-SNAPSHOT.jar`。

> **注意**
>
> 非正式发布的 Spark Connector 的名称包含 `SNAPSHOT` 后缀。

## 参数

### starrocks.fe.http.url

**是否必须**:  是<br/>
**默认值**:  无<br/>
**描述**:  StarRocks 集群中 FE 的 HTTP URL。您可以指定多个 URL，这些 URL 必须用逗号 (,) 分隔。格式：`<fe_host1>:<fe_http_port1>,<fe_host2>:<fe_http_port2>`。从 1.1.1 版本开始，您还可以向 URL 添加 `http://` 前缀，例如 `http://<fe_host1>:<fe_http_port1>,http://<fe_host2>:<fe_http_port2>`。

### starrocks.fe.jdbc.url

**是否必须**:  是<br/>
**默认值**:  无<br/>
**描述**:  用于连接到 FE 的 MySQL 服务器的地址。格式：`jdbc:mysql://<fe_host>:<fe_query_port>`。

### starrocks.table.identifier

**是否必须**:  是<br/>
**默认值**:  无<br/>
**描述**:  StarRocks 表的名称。格式：`<database_name>.<table_name>`。

### starrocks.user

**是否必须**:  是<br/>
**默认值**:  无<br/>
**描述**:  StarRocks 集群帐户的用户名。该用户需要对 StarRocks 表具有 [SELECT 和 INSERT 权限](../sql-reference/sql-statements/account-management/GRANT.md)。

### starrocks.password

**是否必须**:  是<br/>
**默认值**:  无<br/>
**描述**:  StarRocks 集群帐户的密码。

### starrocks.write.label.prefix

**是否必须**:  否<br/>
**默认值**:  spark-<br/>
**描述**:  Stream Load 使用的 Label 前缀。

### starrocks.write.enable.transaction-stream-load

**是否必须**:  否<br/>
**默认值**:  TRUE<br/>
**描述**:  是否使用 [Stream Load 事务接口](../loading/Stream_Load_transaction_interface.md) 加载数据。它需要 StarRocks v2.5 或更高版本。此功能可以在事务中加载更多数据，同时减少内存使用，并提高性能。<br/> **注意：** 从 1.1.1 开始，此参数仅当 `starrocks.write.max.retries` 的值为非正数时才生效，因为 Stream Load 事务接口不支持重试。

### starrocks.write.buffer.size

**是否必须**:  否<br/>
**默认值**:  104857600<br/>
**描述**:  在一次发送到 StarRocks 之前可以在内存中累积的最大数据量。将此参数设置为较大的值可以提高加载性能，但可能会增加加载延迟。

### starrocks.write.buffer.rows

**是否必须**:  否<br/>
**默认值**:  Integer.MAX_VALUE<br/>
**描述**:  自 1.1.1 版本起支持。在一次发送到 StarRocks 之前可以在内存中累积的最大行数。

### starrocks.write.flush.interval.ms

**是否必须**:  否<br/>
**默认值**:  300000<br/>
**描述**:  将数据发送到 StarRocks 的间隔。此参数用于控制加载延迟。

### starrocks.write.max.retries

**是否必须**:  否<br/>
**默认值**:  3<br/>
**描述**:  自 1.1.1 版本起支持。如果加载失败，Connector 重试对同一批数据执行 Stream Load 的次数。<br/> **注意：** 因为 Stream Load 事务接口不支持重试。如果此参数为正数，则 Connector 始终使用 Stream Load 接口并忽略 `starrocks.write.enable.transaction-stream-load` 的值。

### starrocks.write.retry.interval.ms

**是否必须**:  否<br/>
**默认值**:  10000<br/>
**描述**:  自 1.1.1 版本起支持。如果加载失败，重试对同一批数据执行 Stream Load 的间隔。

### starrocks.columns

**是否必须**:  否<br/>
**默认值**:  无<br/>
**描述**:  您要将数据加载到的 StarRocks 表列。您可以指定多个列，这些列必须用逗号 (,) 分隔，例如 `"col0,col1,col2"`。

### starrocks.column.types

**是否必须**: 否<br/>
**默认值**:  无<br/>
**描述**:  自 1.1.1 版本起支持。自定义 Spark 的列数据类型，而不是使用从 StarRocks 表和 [默认映射](#data-type-mapping-between-spark-and-starrocks) 推断的默认值。参数值是 DDL 格式的 Schema，与 Spark [StructType#toDDL](https://github.com/apache/spark/blob/master/sql/api/src/main/scala/org/apache/spark/sql/types/StructType.scala#L449) 的输出相同，例如 `col0 INT, col1 STRING, col2 BIGINT`。请注意，您只需要指定需要自定义的列。一个用例是将数据加载到 [BITMAP](#load-data-into-columns-of-bitmap-type) 或 [HLL](#load-data-into-columns-of-hll-type) 类型的列中。

### starrocks.write.properties.*

**是否必须**:  否<br/>
**默认值**:  无<br/>
**描述**:  用于控制 Stream Load 行为的参数。例如，参数 `starrocks.write.properties.format` 指定要加载的数据的格式，例如 CSV 或 JSON。有关支持的参数及其描述的列表，请参阅 [STREAM LOAD](../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md)。

### starrocks.write.properties.format

**是否必须**:  否<br/>
**默认值**:  CSV<br/>
**描述**:  Spark Connector 在将每批数据发送到 StarRocks 之前转换数据的基于的文件格式。有效值：CSV 和 JSON。

### starrocks.write.properties.row_delimiter

**是否必须**:  否<br/>
**默认值**:  \n<br/>
**描述**:  CSV 格式数据的行分隔符。

### starrocks.write.properties.column_separator

**是否必须**:  否<br/>
**默认值**:  \t<br/>
**描述**:  CSV 格式数据的列分隔符。

### starrocks.write.properties.partial_update

**是否必须**:  否<br/>
**默认值**: `FALSE`<br/>
**描述**: 是否使用部分更新。有效值：`TRUE` 和 `FALSE`。默认值：`FALSE`，表示禁用此功能。

### starrocks.write.properties.partial_update_mode

**是否必须**:  否<br/>
**默认值**: `row`<br/>
**描述**: 指定部分更新的模式。有效值：`row` 和 `column`。<ul><li>值 `row` (默认) 表示行模式下的部分更新，更适合于具有许多列和小批量的实时更新。</li><li>值 `column` 表示列模式下的部分更新，更适合于具有少量列和许多行的批量更新。在这种情况下，启用列模式可以提供更快的更新速度。例如，在一个具有 100 列的表中，如果仅更新所有行的 10 列（总数的 10%），则列模式的更新速度快 10 倍。</li></ul>

### starrocks.write.num.partitions

**是否必须**:  否<br/>
**默认值**:  无<br/>
**描述**:  Spark 可以并行写入数据的分区数。当数据量较小时，您可以减少分区数以降低加载并发和频率。此参数的默认值由 Spark 确定。但是，此方法可能会导致 Spark Shuffle 成本。

### starrocks.write.partition.columns

**是否必须**:  否<br/>
**默认值**:  无<br/>
**描述**:  Spark 中的分区列。该参数仅当指定了 `starrocks.write.num.partitions` 时才生效。如果未指定此参数，则所有正在写入的列都用于分区。

### starrocks.timezone

**是否必须**:  否<br/>
**默认值**:  JVM 的默认时区<br/>
**描述**:  自 1.1.1 起支持。用于将 Spark `TimestampType` 转换为 StarRocks `DATETIME` 的时区。默认值是由 `ZoneId#systemDefault()` 返回的 JVM 时区。格式可以是时区名称，例如 `Asia/Shanghai`，或时区偏移量，例如 `+08:00`。

## Spark 和 StarRocks 之间的数据类型映射

- 默认数据类型映射如下：

  | Spark 数据类型 | StarRocks 数据类型                                          |
  | --------------- | ------------------------------------------------------------ |
  | BooleanType     | BOOLEAN                                                      |
  | ByteType        | TINYINT                                                      |
  | ShortType       | SMALLINT                                                     |
  | IntegerType     | INT                                                          |
  | LongType        | BIGINT                                                       |
  | StringType      | LARGEINT                                                     |
  | FloatType       | FLOAT                                                        |
  | DoubleType      | DOUBLE                                                       |
  | DecimalType     | DECIMAL                                                      |
  | StringType      | CHAR                                                         |
  | StringType      | VARCHAR                                                      |
  | StringType      | STRING                                                       |
  | StringType      | JSON                                                       |
  | DateType        | DATE                                                         |
  | TimestampType   | DATETIME                                                     |
  | ArrayType       | ARRAY <br /> **注意：** <br /> **自 1.1.1 版本起支持**。有关详细步骤，请参阅 [将数据加载到 ARRAY 类型的列中](#load-data-into-columns-of-array-type)。 |

- 您还可以自定义数据类型映射。

  例如，StarRocks 表包含 BITMAP 和 HLL 列，但 Spark 不支持这两种数据类型。您需要在 Spark 中自定义相应的数据类型。有关详细步骤，请参阅将数据加载到 [BITMAP](#load-data-into-columns-of-bitmap-type) 和 [HLL](#load-data-into-columns-of-hll-type) 列中。**自 1.1.1 版本起支持 BITMAP 和 HLL**。

## 升级 Spark connector

### 从 1.1.0 版本升级到 1.1.1 版本

- 从 1.1.1 版本开始，Spark Connector 不提供 `mysql-connector-java`，它是 MySQL 的官方 JDBC 驱动程序，因为 `mysql-connector-java` 使用的 GPL 许可存在限制。
  但是，Spark Connector 仍然需要 MySQL JDBC 驱动程序来连接到 StarRocks 以获取表元数据，因此您需要手动将驱动程序添加到 Spark classpath 中。您可以在 [MySQL site](https://dev.mysql.com/downloads/connector/j/) 或 [Maven Central](https://repo1.maven.org/maven2/mysql/mysql-connector-java/) 上找到该驱动程序。
- 从 1.1.1 版本开始，Connector 默认使用 Stream Load 接口，而不是 1.1.0 版本中的 Stream Load 事务接口。如果您仍然想使用 Stream Load 事务接口，您可以
  将选项 `starrocks.write.max.retries` 设置为 `0`。有关详细信息，请参阅 `starrocks.write.enable.transaction-stream-load` 和 `starrocks.write.max.retries` 的描述。

## 示例

以下示例展示了如何使用 Spark Connector 通过 Spark DataFrames 或 Spark SQL 将数据加载到 StarRocks 表中。Spark DataFrames 支持批量和结构化流模式。

有关更多示例，请参阅 [Spark Connector Examples](https://github.com/StarRocks/starrocks-connector-for-apache-spark/tree/main/src/test/java/com/starrocks/connector/spark/examples)。

### 准备工作

#### 创建 StarRocks 表

创建一个数据库 `test` 并创建一个主键表 `score_board`。

```sql
CREATE DATABASE `test`;

CREATE TABLE `test`.`score_board`
(
    `id` int(11) NOT NULL COMMENT "",
    `name` varchar(65533) NULL DEFAULT "" COMMENT "",
    `score` int(11) NOT NULL DEFAULT "0" COMMENT ""
)
ENGINE=OLAP
PRIMARY KEY(`id`)
COMMENT "OLAP"
DISTRIBUTED BY HASH(`id`);
```

#### 网络配置

确保 Spark 所在的机器可以通过 [`http_port`](../administration/management/FE_configuration.md#http_port) (默认值：`8030`) 和 [`query_port`](../administration/management/FE_configuration.md#query_port) (默认值：`9030`) 访问 StarRocks 集群的 FE 节点，并通过 [`be_http_port`](../administration/management/BE_configuration.md#be_http_port) (默认值：`8040`) 访问 BE 节点。

#### 设置您的 Spark 环境

请注意，以下示例在 Spark 3.2.4 中运行，并使用 `spark-shell`、`pyspark` 和 `spark-sql`。在运行示例之前，请确保将 Spark Connector JAR 文件放在 `$SPARK_HOME/jars` 目录中。

### 使用 Spark DataFrames 加载数据

以下两个示例说明了如何使用 Spark DataFrames 批量或结构化流模式加载数据。

#### 批量

在内存中构造数据并将数据加载到 StarRocks 表中。

1. 您可以使用 Scala 或 Python 编写 Spark 应用程序。

  对于 Scala，在 `spark-shell` 中运行以下代码片段：

  ```Scala
  // 1. 从序列创建 DataFrame。
  val data = Seq((1, "starrocks", 100), (2, "spark", 100))
  val df = data.toDF("id", "name", "score")

  // 2. 通过将格式配置为 "starrocks" 和以下选项来写入 StarRocks。
  // 您需要根据自己的环境修改选项。
  df.write.format("starrocks")
      .option("starrocks.fe.http.url", "127.0.0.1:8030")
      .option("starrocks.fe.jdbc.url", "jdbc:mysql://127.0.0.1:9030")
      .option("starrocks.table.identifier", "test.score_board")
      .option("starrocks.user", "root")
      .option("starrocks.password", "")
      .mode("append")
      .save()
  ```

  对于 Python，在 `pyspark` 中运行以下代码片段：

   ```python
   from pyspark.sql import SparkSession
   
   spark = SparkSession \
        .builder \
        .appName("StarRocks Example") \
        .getOrCreate()
   
    # 1. 从序列创建 DataFrame。
    data = [(1, "starrocks", 100), (2, "spark", 100)]
    df = spark.sparkContext.parallelize(data) \
            .toDF(["id", "name", "score"])

    # 2. 通过将格式配置为 "starrocks" 和以下选项来写入 StarRocks。
    # 您需要根据自己的环境修改选项。
    df.write.format("starrocks") \
        .option("starrocks.fe.http.url", "127.0.0.1:8030") \
        .option("starrocks.fe.jdbc.url", "jdbc:mysql://127.0.0.1:9030") \
        .option("starrocks.table.identifier", "test.score_board") \
        .option("starrocks.user", "root") \
        .option("starrocks.password", "") \
        .mode("append") \
        .save()
    ```

2. 在 StarRocks 表中查询数据。

    ```sql
    MySQL [test]> SELECT * FROM `score_board`;
    +------+-----------+-------+
    | id   | name      | score |
    +------+-----------+-------+
    |    1 | starrocks |   100 |
    |    2 | spark     |   100 |
    +------+-----------+-------+
    2 rows in set (0.00 sec)
    ```

#### 结构化流

构造从 CSV 文件读取数据的流，并将数据加载到 StarRocks 表中。

1. 在目录 `csv-data` 中，创建一个包含以下数据的 CSV 文件 `test.csv`：

    ```csv
    3,starrocks,100
    4,spark,100
    ```

2. 您可以使用 Scala 或 Python 编写 Spark 应用程序。

  对于 Scala，在 `spark-shell` 中运行以下代码片段：

    ```Scala
    import org.apache.spark.sql.types.StructType

    // 1. 从 CSV 创建 DataFrame。
    val schema = (new StructType()
            .add("id", "integer")
            .add("name", "string")
            .add("score", "integer")
        )
    val df = (spark.readStream
            .option("sep", ",")
            .schema(schema)
            .format("csv") 
            // 将其替换为您的目录 "csv-data" 的路径。
            .load("/path/to/csv-data")
        )
    
    // 2. 通过将格式配置为 "starrocks" 和以下选项来写入 StarRocks。
    // 您需要根据自己的环境修改选项。
    val query = (df.writeStream.format("starrocks")
            .option("starrocks.fe.http.url", "127.0.0.1:8030")
            .option("starrocks.fe.jdbc.url", "jdbc:mysql://127.0.0.1:9030")
            .option("starrocks.table.identifier", "test.score_board")
            .option("starrocks.user", "root")
            .option("starrocks.password", "")
            // 将其替换为您的检查点目录
            .option("checkpointLocation", "/path/to/checkpoint")
            .outputMode("append")
            .start()
        )
    ```

  对于 Python，在 `pyspark` 中运行以下代码片段：
   
   ```python
   from pyspark.sql import SparkSession
   from pyspark.sql.types import IntegerType, StringType, StructType, StructField
   
   spark = SparkSession \
        .builder \
        .appName("StarRocks SS Example") \
        .getOrCreate()
   
    # 1. 从 CSV 创建 DataFrame。
    schema = StructType([
            StructField("id", IntegerType()),
            StructField("name", StringType()),
            StructField("score", IntegerType())
        ])
    df = (
        spark.readStream
        .option("sep", ",")
        .schema(schema)
        .format("csv")
        # 将其替换为您的目录 "csv-data" 的路径。
        .load("/path/to/csv-data")
    )

    # 2. 通过将格式配置为 "starrocks" 和以下选项来写入 StarRocks。
    # 您需要根据自己的环境修改选项。
    query = (
        df.writeStream.format("starrocks")
        .option("starrocks.fe.http.url", "127.0.0.1:8030")
        .option("starrocks.fe.jdbc.url", "jdbc:mysql://127.0.0.1:9030")
        .option("starrocks.table.identifier", "test.score_board")
        .option("starrocks.user", "root")
        .option("starrocks.password", "")
        # 将其替换为您的检查点目录
        .option("checkpointLocation", "/path/to/checkpoint")
        .outputMode("append")
        .start()
    )
    ```

3. 在 StarRocks 表中查询数据。

    ```SQL
    MySQL [test]> select * from score_board;
    +------+-----------+-------+
    | id   | name      | score |
    +------+-----------+-------+
    |    4 | spark     |   100 |
    |    3 | starrocks |   100 |
    +------+-----------+-------+
    2 rows in set (0.67 sec)
    ```

### 使用 Spark SQL 加载数据

以下示例说明了如何通过使用 [Spark SQL CLI](https://spark.apache.org/docs/latest/sql-distributed-sql-engine-spark-sql-cli.html) 中的 `INSERT INTO` 语句使用 Spark SQL 加载数据。

1. 在 `spark-sql` 中执行以下 SQL 语句：

    ```SQL
    -- 1. 通过将数据源配置为 `starrocks` 和以下选项来创建表。
    -- 您需要根据自己的环境修改选项。
    CREATE TABLE `score_board`
    USING starrocks
    OPTIONS(
    "starrocks.fe.http.url"="127.0.0.1:8030",
    "starrocks.fe.jdbc.url"="jdbc:mysql://127.0.0.1:9030",
    "starrocks.table.identifier"="test.score_board",
    "starrocks.user"="root",
    "starrocks.password"=""
    );

    -- 2. 将两行插入到表中。
    INSERT INTO `score_board` VALUES (5, "starrocks", 100), (6, "spark", 100);
    ```

2. 在 StarRocks 表中查询数据。

    ```SQL
    MySQL [test]> select * from score_board;
    +------+-----------+-------+
    | id   | name      | score |
    +------+-----------+-------+
    |    6 | spark     |   100 |
    |    5 | starrocks |   100 |
    +------+-----------+-------+
    2 rows in set (0.00 sec)
    ```

## 最佳实践

### 导入数据到主键表

本节将展示如何将数据导入到 StarRocks 主键表以实现部分更新和条件更新。
您可以参阅 [通过导入更改数据](../loading/Load_to_Primary_Key_tables.md) 以获取这些功能的详细介绍。
这些示例使用 Spark SQL。

#### 准备工作

在 StarRocks 中创建一个数据库 `test` 并创建一个主键表 `score_board`。

```SQL
CREATE DATABASE `test`;

CREATE TABLE `test`.`score_board`
(
    `id` int(11) NOT NULL COMMENT "",
    `name` varchar(65533) NULL DEFAULT "" COMMENT "",
    `score` int(11) NOT NULL DEFAULT "0" COMMENT ""
)
ENGINE=OLAP
PRIMARY KEY(`id`)
COMMENT "OLAP"
DISTRIBUTED BY HASH(`id`);
```

#### 部分更新

本示例将展示如何仅通过导入更新列 `name` 中的数据：

1. 在 MySQL 客户端中将初始数据插入到 StarRocks 表中。

   ```sql
   mysql> INSERT INTO `score_board` VALUES (1, 'starrocks', 100), (2, 'spark', 100);

   mysql> select * from score_board;
   +------+-----------+-------+
   | id   | name      | score |
   +------+-----------+-------+
   |    1 | starrocks |   100 |
   |    2 | spark     |   100 |
   +------+-----------+-------+
   2 rows in set (0.02 sec)
   ```

2. 在 Spark SQL 客户端中创建一个 Spark 表 `score_board`。

   - 将选项 `starrocks.write.properties.partial_update` 设置为 `true`，这会告诉 Connector 执行部分更新。
   - 将选项 `starrocks.columns` 设置为 `"id,name"`，以告诉 Connector 要写入哪些列。

   ```SQL
   CREATE TABLE `score_board`
   USING starrocks
   OPTIONS(
       "starrocks.fe.http.url"="127.0.0.1:8030",
       "starrocks.fe.jdbc.url"="jdbc:mysql://127.0.0.1:9030",
       "starrocks.table.identifier"="test.score_board",
       "starrocks.user"="root",
       "starrocks.password"="",
       "starrocks.write.properties.partial_update"="true",
       "starrocks.columns"="id,name"
    );
   ```

3. 在 Spark SQL 客户端中将数据插入到表中，并且仅更新列 `name`。

   ```SQL
   INSERT INTO `score_board` VALUES (1, 'starrocks-update'), (2, 'spark-update');
   ```

4. 在 MySQL 客户端中查询 StarRocks 表。

   您可以看到只有 `name` 的值发生了变化，而 `score` 的值没有发生变化。

   ```SQL
   mysql> select * from score_board;
   +------+------------------+-------+
   | id   | name             | score |
   +------+------------------+-------+
   |    1 | starrocks-update |   100 |
   |    2 | spark-update     |   100 |
   +------+------------------+-------+
   2 rows in set (0.02 sec)
   ```

#### 条件更新

本示例将展示如何根据列 `score` 的值执行条件更新。仅当 `score` 的新值大于或等于旧值时，对 `id` 的更新才会生效。

1. 在 MySQL 客户端中将初始数据插入到 StarRocks 表中。

    ```SQL
    mysql> INSERT INTO `score_board` VALUES (1, 'starrocks', 100), (2, 'spark', 100);

    mysql> select * from score_board;
    +------+-----------+-------+
    | id   | name      | score |
    +------+-----------+-------+
    |    1 | starrocks |   100 |
    |    2 | spark     |   100 |
    +------+-----------+-------+
    2 rows in set (0.02 sec)
    ```

2. 通过以下方式创建一个 Spark 表 `score_board`。

   - 将选项 `starrocks.write.properties.merge_condition` 设置为 `score`，这会告诉 Connector 使用列 `score` 作为条件。
   - 确保 Spark Connector 使用 Stream Load 接口加载数据，而不是 Stream Load 事务接口，因为后者不支持此功能。

   ```SQL
   CREATE TABLE `score_board`
   USING starrocks
   OPTIONS(
       "starrocks.fe.http.url"="127.0.0.1:8030",
       "starrocks.fe.jdbc.url"="jdbc:mysql://127.0.0.1:9030",
       "starrocks.table.identifier"="test.score_board",
       "starrocks.user"="root",
       "starrocks.password"="",
       "starrocks.write.properties.merge_condition"="score"
    );
   ```

3. 将数据插入到 Spark SQL 客户端中的表中，并使用较小的 Score 值更新 `id` 为 1 的行，并使用较大的 Score 值更新 `id` 为 2 的行。

   ```SQL
   INSERT INTO `score_board` VALUES (1, 'starrocks-update', 99), (2, 'spark-update', 101);
   ```

4. 在 MySQL 客户端中查询 StarRocks 表。

   您可以看到只有 `id` 为 2 的行发生了变化，而 `id` 为 1 的行没有发生变化。

   ```SQL
   mysql> select * from score_board;
   +------+--------------+-------+
   | id   | name         | score |
   +------+--------------+-------+
   |    1 | starrocks    |   100 |
   |    2 | spark-update |   101 |
   +------+--------------+-------+
   2 rows in set (0.03 sec)
   ```

### 将数据加载到 BITMAP 类型的列中

[`BITMAP`](../sql-reference/data-types/other-data-types/BITMAP.md) 通常用于加速 Count Distinct，例如计算 UV，请参阅 [使用 Bitmap 进行精确的 Count Distinct](../using_starrocks/distinct_values/Using_bitmap.md)。
这里我们以 UV 的计数为例，展示如何将数据加载到 `BITMAP` 类型的列中。**自 1.1.1 版本起支持 `BITMAP`**。

1. 创建一个 StarRocks 聚合表。

   在数据库 `test` 中，创建一个聚合表 `page_uv`，其中列 `visit_users` 定义为 `BITMAP` 类型，并配置了聚合函数 `BITMAP_UNION`。

    ```SQL
    CREATE TABLE `test`.`page_uv` (
      `page_id` INT NOT NULL COMMENT '页面 ID',
      `visit_date` datetime NOT NULL COMMENT '访问时间',
      `visit_users` BITMAP BITMAP_UNION NOT NULL COMMENT '用户 ID'
    ) ENGINE=OLAP
    AGGREGATE KEY(`page_id`, `visit_date`)
    DISTRIBUTED BY HASH(`page_id`);
    ```

2. 创建一个 Spark 表。

    Spark 表的 Schema 是从 StarRocks 表推断出来的，并且 Spark 不支持 `BITMAP` 类型。因此，您需要在 Spark 中自定义相应的列数据类型，例如作为 `BIGINT`，通过配置选项 `"starrocks.column.types"="visit_users BIGINT"`。当使用 Stream Load 摄取数据时，Connector 使用 [`to_bitmap`](../sql-reference/sql-functions/bitmap-functions/to_bitmap.md) 函数将 `BIGINT` 类型的数据转换为 `BITMAP` 类型。

    在 `spark-sql` 中运行以下 DDL：

    ```SQL
    CREATE TABLE `page_uv`
    USING starrocks
    OPTIONS(
       "starrocks.fe.http.url"="127.0.0.1:8030",
       "starrocks.fe.jdbc.url"="jdbc:mysql://127.0.0.1:9030",
       "starrocks.table