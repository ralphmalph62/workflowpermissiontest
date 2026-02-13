---
displayed_sidebar: docs
sidebar_position: 4
description: 基于 Apache Hudi 的数据湖仓
toc_max_heading_level: 3
---
import DataLakeIntro from '../_assets/commonMarkdown/datalakeIntro.mdx'
import Clients from '../_assets/quick-start/_clientsCompose.mdx'
import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Apache Hudi 数据湖仓

- 使用 Docker Compose 部署对象存储、Apache Spark、Hudi 和 StarRocks
- 使用 Apache Spark 将少量数据集加载到 Hudi 中
- 配置 StarRocks 以使用外部目录访问 Hive Metastore
- 使用 StarRocks 在数据所在位置查询数据

<DataLakeIntro />

## 先决条件

### StarRocks `demo` 仓库

将 [StarRocks demo 仓库](https://github.com/StarRocks/demo/) 克隆到本地机器。

本指南中的所有步骤都将从您克隆 `demo` GitHub 仓库的目录中的 `demo/documentation-samples/hudi/` 目录运行。

### Docker

- Docker 设置：对于 Mac，请按照 [在 Mac 上安装 Docker Desktop](https://docs.docker.com/desktop/install/mac-install/) 中定义的步骤进行操作。为了运行 Spark-SQL 查询，请确保为 Docker 分配至少 5 GB 内存和 4 个 CPU（参见 Docker → Preferences → Advanced）。否则，Spark-SQL 查询可能会因内存问题而被终止。
- 为 Docker 分配 20 GB 可用磁盘空间
  
### SQL 客户端

您可以使用 Docker 环境中提供的 SQL 客户端，或者使用您系统上的客户端。许多兼容 MySQL 的客户端都可以工作。

## 配置

将目录更改为 `demo/documentation-samples/hudi` 并查看文件。这不是一个关于 Hudi 的教程，因此不会描述每个配置文件；但对于读者来说，了解在哪里查看配置方式很重要。在 `hudi/` 目录中，您会找到用于在 Docker 中启动和配置服务的 `docker-compose.yml` 文件。以下是这些服务及其简要说明：

### Docker 服务

| 服务                   | 职责                                    |
|----------------------|-----------------------------------------|
| **`starrocks-fe`**   | 元数据管理、客户端连接、查询计划和调度    |
| **`starrocks-be`**   | 运行查询计划                              |
| **`metastore_db`**   | 用于存储 Hive 元数据的 Postgres 数据库  |
| **`hive_metastore`** | 提供 Apache Hive Metastore                |
| **`minio`** 和 **`mc`** | MinIO 对象存储和 MinIO 命令行客户端       |
| **`spark-hudi`**     | 分布式计算和事务型数据湖平台              |

### 配置文件

在 `hudi/conf/` 目录中，您会找到挂载到 `spark-hudi` 容器中的配置文件。

##### `core-site.xml`

此文件包含对象存储相关设置。有关此文件和文档末尾其他项目的链接，请参见“更多信息”部分。

##### `spark-defaults.conf`

Hive、MinIO 和 Spark SQL 的设置。

##### `hudi-defaults.conf`

用于消除 `spark-shell` 中警告的默认文件。

##### `hadoop-metrics2-hbase.properties`

用于消除 `spark-shell` 中警告的空文件。

##### `hadoop-metrics2-s3a-file-system.properties`

用于消除 `spark-shell` 中警告的空文件。

## 启动演示集群

该演示系统由 StarRocks、Hudi、MinIO 和 Spark 服务组成。运行 Docker Compose 启动集群：

```bash
docker compose up --detach --wait --wait-timeout 60
```

```plaintext
[+] Running 8/8
 ✔ Network hudi                     Created                                                   0.0s
 ✔ Container hudi-starrocks-fe-1    Healthy                                                   0.1s
 ✔ Container hudi-minio-1           Healthy                                                   0.1s
 ✔ Container hudi-metastore_db-1    Healthy                                                   0.1s
 ✔ Container hudi-starrocks-be-1    Healthy                                                   0.0s
 ✔ Container hudi-mc-1              Healthy                                                   0.0s
 ✔ Container hudi-hive-metastore-1  Healthy                                                   0.0s
 ✔ Container hudi-spark-hudi-1      Healthy                                                   0.1s
 ```

:::tip

当有许多容器运行时，如果您将其通过管道传输到 `jq`，`docker compose ps` 的输出会更易读：

```bash
docker compose ps --format json | \
jq '{Service: .Service, State: .State, Status: .Status}'
```

```json
{
  "Service": "hive-metastore",
  "State": "running",
  "Status": "Up About a minute (healthy)"
}
{
  "Service": "mc",
  "State": "running",
  "Status": "Up About a minute"
}
{
  "Service": "metastore_db",
  "State": "running",
  "Status": "Up About a minute"
}
{
  "Service": "minio",
  "State": "running",
  "Status": "Up About a minute"
}
{
  "Service": "spark-hudi",
  "State": "running",
  "Status": "Up 33 seconds (healthy)"
}
{
  "Service": "starrocks-be",
  "State": "running",
  "Status": "Up About a minute (healthy)"
}
{
  "Service": "starrocks-fe",
  "State": "running",
  "Status": "Up About a minute (healthy)"
}
```

:::

## 配置 MinIO

当您运行 Spark 命令时，您会将要创建的表的 `basepath` 设置为 `s3a` URI：

```java
val basePath = "s3a://huditest/hudi_coders"
```

在此步骤中，您将在 MinIO 中创建名为 `huditest` 的存储桶。MinIO 控制台运行在端口 `9000` 上。

### 认证到 MinIO

在浏览器中打开 [http://localhost:9000/](http://localhost:9000/) 并进行身份验证。用户名和密码在 `docker-compose.yml` 中指定；它们分别是 `admin` 和 `password`。

### 创建存储桶

在左侧导航栏中选择 **Buckets**，然后选择 **Create Bucket +**。将存储桶命名为 `huditest` 并选择 **Create Bucket**。

![Create bucket huditest](../_assets/quick-start/hudi-test-bucket.png)

## 创建并填充表，然后同步到 Hive

:::tip

从包含 `docker-compose.yml` 文件的目录运行此命令以及任何其他 `docker compose` 命令。
:::

在 `spark-hudi` 服务中打开 `spark-shell`

```bash
docker compose exec spark-hudi spark-shell
```

:::note
当 `spark-shell` 启动时，会有关于非法反射访问的警告。您可以忽略这些警告。
:::

在 `scala>` 提示符下运行这些命令以：

- 配置此 Spark 会话以加载、处理和写入数据
- 创建数据框并将其写入 Hudi 表
- 同步到 Hive Metastore

```scala
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._
import org.apache.spark.sql.Row
import org.apache.spark.sql.SaveMode._
import org.apache.hudi.DataSourceReadOptions._
import org.apache.hudi.DataSourceWriteOptions._
import org.apache.hudi.config.HoodieWriteConfig._
import scala.collection.JavaConversions._

val schema = StructType( Array(
                 StructField("language", StringType, true),
                 StructField("users", StringType, true),
                 StructField("id", StringType, true)
             ))

val rowData= Seq(Row("Java", "20000", "a"),
               Row("Python", "100000", "b"),
               Row("Scala", "3000", "c"))


val df = spark.createDataFrame(rowData,schema)

val databaseName = "hudi_sample"
val tableName = "hudi_coders_hive"
val basePath = "s3a://huditest/hudi_coders"

df.write.format("hudi").
  option(org.apache.hudi.config.HoodieWriteConfig.TABLE_NAME, tableName).
  option(RECORDKEY_FIELD_OPT_KEY, "id").
  option(PARTITIONPATH_FIELD_OPT_KEY, "language").
  option(PRECOMBINE_FIELD_OPT_KEY, "users").
  option("hoodie.datasource.write.hive_style_partitioning", "true").
  option("hoodie.datasource.hive_sync.enable", "true").
  option("hoodie.datasource.hive_sync.mode", "hms").
  option("hoodie.datasource.hive_sync.database", databaseName).
  option("hoodie.datasource.hive_sync.table", tableName).
  option("hoodie.datasource.hive_sync.partition_fields", "language").
  option("hoodie.datasource.hive_sync.partition_extractor_class", "org.apache.hudi.hive.MultiPartKeysValueExtractor").
  option("hoodie.datasource.hive_sync.metastore.uris", "thrift://hive-metastore:9083").
  mode(Overwrite).
  save(basePath)
System.exit(0)
```

:::note
您将看到一个警告：

```java
WARN
org.apache.hudi.metadata.HoodieBackedTableMetadata - 
Metadata table was not found at path 
s3a://huditest/hudi_coders/.hoodie/metadata
```

可以忽略此警告，文件将在本次 `spark-shell` 会话期间自动创建。

还会有一个警告：

```bash
78184 [main] WARN  org.apache.hadoop.fs.s3a.S3ABlockOutputStream  - 
Application invoked the Syncable API against stream writing to 
hudi_coders/.hoodie/metadata/files/.files-0000_00000000000000.log.1_0-0-0. 
This is unsupported
```

此警告告知您，当使用对象存储时，不支持同步处于写入打开状态的日志文件。该文件只会在关闭时同步。请参阅 [Stack Overflow](https://stackoverflow.com/a/74886836/10424890)。
:::

上述 spark-shell 会话中的最后一个命令应该会退出容器，如果它没有退出，请按回车键即可退出。

## 配置 StarRocks

### 连接到 StarRocks

使用 `starrocks-fe` 服务提供的 MySQL 客户端连接到 StarRocks，或者使用您喜欢的 SQL 客户端并将其配置为使用 MySQL 协议连接到 `localhost:9030`。

```bash
docker compose exec starrocks-fe \
  mysql -P 9030 -h 127.0.0.1 -u root --prompt="StarRocks > "
```

### 创建 StarRocks 和 Hudi 之间的链接

本指南末尾有一个链接，其中包含有关外部目录的更多信息。此步骤中创建的外部目录充当与 Docker 中运行的 Hive Metastore (HMS) 的链接。

```sql
CREATE EXTERNAL CATALOG hudi_catalog_hms
PROPERTIES
(
    "type" = "hudi",
    "hive.metastore.type" = "hive",
    "hive.metastore.uris" = "thrift://hive-metastore:9083",
    "aws.s3.use_instance_profile" = "false",
    "aws.s3.access_key" = "admin",
    "aws.s3.secret_key" = "password",
    "aws.s3.enable_ssl" = "false",
    "aws.s3.enable_path_style_access" = "true",
    "aws.s3.endpoint" = "http://minio:9000"
);
```

```plaintext
Query OK, 0 rows affected (0.59 sec)
```

### 使用新目录

```sql
SET CATALOG hudi_catalog_hms;
```

```plaintext
Query OK, 0 rows affected (0.01 sec)
```

### 导航到 Spark 插入的数据

```sql
SHOW DATABASES;
```

```plaintext
+--------------------+
| Database           |
+--------------------+
| default            |
| hudi_sample        |
| information_schema |
+--------------------+
2 rows in set (0.40 sec)
```

```sql
USE hudi_sample;
```

```plaintext
Reading table information for completion of table and column names
You can turn off this feature to get a quicker startup with -A

Database changed
```

```sql
SHOW TABLES;
```

```plaintext
+-----------------------+
| Tables_in_hudi_sample |
+-----------------------+
| hudi_coders_hive      |
+-----------------------+
1 row in set (0.07 sec)
```

### 使用 StarRocks 查询 Hudi 中的数据

运行此查询两次，第一次可能需要大约五秒才能完成，因为数据尚未在 StarRocks 中缓存。第二次查询会非常快。

```sql
SELECT * from hudi_coders_hive\G
```

:::tip
StarRocks 文档中的一些 SQL 查询以 `\G` 结尾而不是分号。`\G` 会导致 mysql CLI 垂直渲染查询结果。

许多 SQL 客户端不解释垂直格式输出，因此如果您不使用 mysql CLI，则应将 `\G` 替换为 `;`。
:::

```plaintext
*************************** 1. row ***************************
   _hoodie_commit_time: 20240208165522561
  _hoodie_commit_seqno: 20240208165522561_0_0
    _hoodie_record_key: c
_hoodie_partition_path: language=Scala
     _hoodie_file_name: bb29249a-b69d-4c32-843b-b7142d8dc51c-0_0-27-1221_20240208165522561.parquet
              language: Scala
                 users: 3000
                    id: c
*************************** 2. row ***************************
   _hoodie_commit_time: 20240208165522561
  _hoodie_commit_seqno: 20240208165522561_2_0
    _hoodie_record_key: a
_hoodie_partition_path: language=Java
     _hoodie_file_name: 12fc14aa-7dc4-454c-b710-1ad0556c9386-0_2-27-1223_20240208165522561.parquet
              language: Java
                 users: 20000
                    id: a
*************************** 3. row ***************************
   _hoodie_commit_time: 20240208165522561
  _hoodie_commit_seqno: 20240208165522561_1_0
    _hoodie_record_key: b
_hoodie_partition_path: language=Python
     _hoodie_file_name: 51977039-d71e-4dd6-90d4-0c93656dafcf-0_1-27-1222_20240208165522561.parquet
              language: Python
                 users: 100000
                    id: b
3 rows in set (0.15 sec)
```

## 总结

本教程向您展示了如何使用 StarRocks 外部目录来查询 Hudi 外部目录中的数据。还可以使用 Iceberg、Delta Lake 和 JDBC 目录进行许多其他集成。

在本教程中，您：

- 在 Docker 中部署了 StarRocks 和 Hudi/Spark/MinIO 环境
- 使用 Apache Spark 将少量数据集加载到 Hudi 中
- 配置了 StarRocks 外部目录以提供对 Hudi 目录的访问
- 在 StarRocks 中使用 SQL 查询数据，而无需从数据湖复制数据

## 更多信息

[StarRocks 目录](../data_source/catalog/catalog_overview.md)

[Apache Hudi 快速入门](https://hudi.apache.org/docs/quick-start-guide/)（包含 Spark）

[Apache Hudi S3 配置](https://hudi.apache.org/docs/s3_hoodie/)

[Apache Spark 配置文档](https://spark.apache.org/docs/latest/configuration.html)
