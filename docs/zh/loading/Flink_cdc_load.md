---
displayed_sidebar: docs
keywords:
  - MySql
  - mysql
  - sync
  - Flink CDC
---

# 从 MySQL 实时同步

import InsertPrivNote from '../_assets/commonMarkdown/insertPrivNote.mdx'

StarRocks 支持多种方法将数据从 MySQL 实时同步到 StarRocks，从而实现海量数据的低延迟实时分析。

本主题介绍如何通过 Apache Flink® 将数据从 MySQL 实时同步到 StarRocks（在几秒钟内）。

<InsertPrivNote />

## 原理

:::tip

Flink CDC 用于从 MySQL 到 Flink 的同步。本主题使用版本低于 3.0 的 Flink CDC，因此使用 SMT 来同步表结构。但是，如果使用 Flink CDC 3.0，则无需使用 SMT 将表结构同步到 StarRocks。Flink CDC 3.0 甚至可以同步整个 MySQL 数据库的 schema、分片数据库和表，并且还支持 schema 变更同步。有关详细用法，请参见 [Streaming ELT from MySQL to StarRocks](https://nightlies.apache.org/flink/flink-cdc-docs-stable/docs/get-started/quickstart/mysql-to-starrocks)。

:::

下图说明了整个同步过程。

![img](../_assets/4.9.2.png)

通过 Flink 将 MySQL 实时同步到 StarRocks 分为两个阶段实现：同步数据库和表结构以及同步数据。首先，SMT 将 MySQL 数据库和表结构转换为 StarRocks 的表创建语句。然后，Flink 集群运行 Flink 作业，将 MySQL 的完整数据和增量数据同步到 StarRocks。

:::info

同步过程保证了 exactly-once 语义。

:::

**同步过程**：

1. 同步数据库和表结构。

   SMT 读取要同步的 MySQL 数据库和表的 schema，并生成用于在 StarRocks 中创建目标数据库和表的 SQL 文件。此操作基于 SMT 配置文件中的 MySQL 和 StarRocks 信息。

2. 同步数据。

   a. Flink SQL 客户端执行数据导入语句 `INSERT INTO SELECT`，以将一个或多个 Flink 作业提交到 Flink 集群。

   b. Flink 集群运行 Flink 作业以获取数据。Flink CDC 连接器首先从源数据库读取完整的历史数据，然后无缝切换到增量读取，并将数据发送到 flink-connector-starrocks。

   c. flink-connector-starrocks 在 mini-batch 中累积数据，并将每批数据同步到 StarRocks。

    :::info

    只有 MySQL 中的数据操作语言 (DML) 操作可以同步到 StarRocks。数据定义语言 (DDL) 操作无法同步。

    :::

## 适用场景

从 MySQL 实时同步具有广泛的用例，其中数据不断变化。以“商品销售实时排名”的实际用例为例。

Flink 基于 MySQL 中原始订单表计算商品销售的实时排名，并将排名实时同步到 StarRocks 的主键表。用户可以将可视化工具连接到 StarRocks，以实时查看排名，从而获得按需运营洞察。

## 前提条件

### 下载并安装同步工具

要从 MySQL 同步数据，您需要安装以下工具：SMT、Flink、Flink CDC 连接器和 flink-connector-starrocks。

1. 下载并安装 Flink，然后启动 Flink 集群。您也可以按照 [Flink 官方文档](https://nightlies.apache.org/flink/flink-docs-release-1.13/docs/try-flink/local_installation/) 中的说明执行此步骤。

   a. 在运行 Flink 之前，请在操作系统中安装 Java 8 或 Java 11。您可以运行以下命令来检查已安装的 Java 版本。

    ```Bash
        # 查看 Java 版本。
        java -version
        
        # 如果返回以下输出，则表示已安装 Java 8。
        java version "1.8.0_301"
        Java(TM) SE Runtime Environment (build 1.8.0_301-b09)
        Java HotSpot(TM) 64-Bit Server VM (build 25.301-b09, mixed mode)
    ```

   b. 下载 [Flink 安装包](https://flink.apache.org/downloads.html) 并解压缩。建议您使用 Flink 1.14 或更高版本。允许的最低版本为 Flink 1.11。本主题使用 Flink 1.14.5。

   ```Bash
      # 下载 Flink。
      wget https://archive.apache.org/dist/flink/flink-1.14.5/flink-1.14.5-bin-scala_2.11.tgz
      # 解压缩 Flink。  
      tar -xzf flink-1.14.5-bin-scala_2.11.tgz
      # 进入 Flink 目录。
      cd flink-1.14.5
    ```

   c. 启动 Flink 集群。

   ```Bash
      # 启动 Flink 集群。
      ./bin/start-cluster.sh
      
      # 如果返回以下输出，则表示已启动 Flink 集群。
      Starting cluster.
      Starting standalonesession daemon on host.
      Starting taskexecutor daemon on host.
    ```

2. 下载 [Flink CDC connector](https://github.com/ververica/flink-cdc-connectors/releases)。本主题使用 MySQL 作为数据源，因此下载 `flink-sql-connector-mysql-cdc-x.x.x.jar`。连接器版本必须与 [Flink](https://github.com/ververica/flink-cdc-connectors/releases) 版本匹配。本主题使用 Flink 1.14.5，您可以下载 `flink-sql-connector-mysql-cdc-2.2.0.jar`。

    ```Bash
    wget https://repo1.maven.org/maven2/com/ververica/flink-sql-connector-mysql-cdc/2.1.1/flink-sql-connector-mysql-cdc-2.2.0.jar
    ```

3. 下载 [flink-connector-starrocks](https://search.maven.org/artifact/com.starrocks/flink-connector-starrocks)。该版本必须与 Flink 版本匹配。

    > flink-connector-starrocks 包 `x.x.x_flink-y.yy _ z.zz.jar` 包含三个版本号：
    >
    > - `x.x.x` 是 flink-connector-starrocks 的版本号。
    > - `y.yy` 是支持的 Flink 版本。
    > - `z.zz` 是 Flink 支持的 Scala 版本。如果 Flink 版本为 1.14.x 或更早版本，则必须下载具有 Scala 版本的包。
    >
    > 本主题使用 Flink 1.14.5 和 Scala 2.11。因此，您可以下载以下包：`1.2.3_flink-14_2.11.jar`。

4. 将 Flink CDC 连接器 (`flink-sql-connector-mysql-cdc-2.2.0.jar`) 和 flink-connector-starrocks (`1.2.3_flink-1.14_2.11.jar`) 的 JAR 包移动到 Flink 的 `lib` 目录。

    > **注意**
    >
    > 如果您的系统中已在运行 Flink 集群，则必须停止 Flink 集群并重新启动它才能加载和验证 JAR 包。
    >
    > ```Bash
    > $ ./bin/stop-cluster.sh
    > $ ./bin/start-cluster.sh
    > ```

5. 下载并解压缩 [SMT 包](https://www.starrocks.io/download/community)，并将其放置在 `flink-1.14.5` 目录中。StarRocks 提供适用于 Linux x86 和 macos ARM64 的 SMT 包。您可以根据您的操作系统和 CPU 选择一个。

    ```Bash
    # for Linux x86
    wget https://releases.starrocks.io/resources/smt.tar.gz
    # for macOS ARM64
    wget https://releases.starrocks.io/resources/smt_darwin_arm64.tar.gz
    ```

### 启用 MySQL 二进制日志

要从 MySQL 实时同步数据，系统需要从 MySQL 二进制日志 (binlog) 中读取数据，解析数据，然后将数据同步到 StarRocks。确保已启用 MySQL 二进制日志。

1. 编辑 MySQL 配置文件 `my.cnf`（默认路径：`/etc/my.cnf`）以启用 MySQL 二进制日志。

    ```Bash
    # 启用 MySQL Binlog。
    log_bin = ON
    # 配置 Binlog 的保存路径。
    log_bin =/var/lib/mysql/mysql-bin
    # 配置 server_id。
    # 如果未为 MySQL 5.7.3 或更高版本配置 server_id，则无法使用 MySQL 服务。
    server_id = 1
    # 将 Binlog 格式设置为 ROW。
    binlog_format = ROW
    # Binlog 文件的基本名称。附加一个标识符以标识每个 Binlog 文件。
    log_bin_basename =/var/lib/mysql/mysql-bin
    # Binlog 文件的索引文件，用于管理所有 Binlog 文件的目录。
    log_bin_index =/var/lib/mysql/mysql-bin.index
    ```

2. 运行以下命令之一以重新启动 MySQL，以使修改后的配置文件生效。

    ```Bash
    # 使用 service 重新启动 MySQL。
    service mysqld restart
    # 使用 mysqld 脚本重新启动 MySQL。
    /etc/init.d/mysqld restart
    ```

3. 连接到 MySQL 并检查是否已启用 MySQL 二进制日志。

    ```Plain
    -- 连接到 MySQL。
    mysql -h xxx.xx.xxx.xx -P 3306 -u root -pxxxxxx

    -- 检查是否已启用 MySQL 二进制日志。
    mysql> SHOW VARIABLES LIKE 'log_bin'; 
    +---------------+-------+
    | Variable_name | Value |
    +---------------+-------+
    | log_bin       | ON    |
    +---------------+-------+
    1 row in set (0.00 sec)
    ```

## 同步数据库和表结构

1. 编辑 SMT 配置文件。
   转到 SMT `conf` 目录并编辑配置文件 `config_prod.conf`，例如 MySQL 连接信息、要同步的数据库和表的匹配规则以及 flink-connector-starrocks 的配置信息。

    ```Bash
    [db]
    type = mysql
    host = xxx.xx.xxx.xx
    port = 3306
    user = user1
    password = xxxxxx

    [other]
    # StarRocks 中 BE 的数量
    be_num = 3
    # StarRocks-1.18.1 及更高版本支持 `decimal_v3`。
    use_decimal_v3 = true
    # 用于保存转换后的 DDL SQL 的文件
    output_dir = ./result

    [table-rule.1]
    # 用于匹配数据库以设置属性的模式
    database = ^demo.*$
    # 用于匹配表以设置属性的模式
    table = ^.*$

    ############################################
    ### Flink sink configurations
    ### DO NOT set `connector`, `table-name`, `database-name`. They are auto-generated.
    ############################################
    flink.starrocks.jdbc-url=jdbc:mysql://<fe_host>:<fe_query_port>
    flink.starrocks.load-url= <fe_host>:<fe_http_port>
    flink.starrocks.username=user2
    flink.starrocks.password=xxxxxx
    flink.starrocks.sink.properties.format=csv
    flink.starrocks.sink.properties.column_separator=\x01
    flink.starrocks.sink.properties.row_delimiter=\x02
    flink.starrocks.sink.buffer-flush.interval-ms=15000
    ```

    - `[db]`: 用于访问源数据库的信息。
       - `type`: 源数据库的类型。在本主题中，源数据库为 `mysql`。
       - `host`: MySQL 服务器的 IP 地址。
       - `port`: MySQL 数据库的端口号，默认为 `3306`
       - `user`: 用于访问 MySQL 数据库的用户名
       - `password`: 用户名的密码

    - `[table-rule]`: 数据库和表匹配规则以及相应的 flink-connector-starrocks 配置。

       - `Database`、`table`: MySQL 中数据库和表的名称。支持正则表达式。
       - `flink.starrocks.*`: flink-connector-starrocks 的配置信息。有关更多配置和信息，请参见 [flink-connector-starrocks](../loading/Flink-connector-starrocks.md)。

       > 如果您需要为不同的表使用不同的 flink-connector-starrocks 配置。例如，如果某些表经常更新，并且您需要加速数据导入，请参见 [为不同的表使用不同的 flink-connector-starrocks 配置](#use-different-flink-connector-starrocks-configurations-for-different-tables)。如果您需要将从 MySQL 分片获得的多个表加载到同一个 StarRocks 表中，请参见 [将 MySQL 分片后的多个表同步到一个 StarRocks 表中](#synchronize-multiple-tables-after-mysql-sharding-to-one-table-in-starrocks)。

    - `[other]`: 其他信息
       - `be_num`: StarRocks 集群中 BE 的数量（此参数将用于在后续 StarRocks 表创建中设置合理的 tablet 数量）。
       - `use_decimal_v3`: 是否启用 [Decimal V3](../sql-reference/data-types/numeric/DECIMAL.md)。启用 Decimal V3 后，将数据同步到 StarRocks 时，MySQL decimal 数据将转换为 Decimal V3 数据。
       - `output_dir`: 用于保存要生成的 SQL 文件的路径。SQL 文件将用于在 StarRocks 中创建数据库和表，并将 Flink 作业提交到 Flink 集群。默认路径为 `./result`，建议您保留默认设置。

2. 运行 SMT 以读取 MySQL 中的数据库和表结构，并根据配置文件在 `./result` 目录中生成 SQL 文件。`starrocks-create.all.sql` 文件用于在 StarRocks 中创建数据库和表，`flink-create.all.sql` 文件用于将 Flink 作业提交到 Flink 集群。

    ```Bash
    # 运行 SMT。
    ./starrocks-migrate-tool

    # 转到 result 目录并检查此目录中的文件。
    cd result
    ls result
    flink-create.1.sql    smt.tar.gz              starrocks-create.all.sql
    flink-create.all.sql  starrocks-create.1.sql
    ```

3. 运行以下命令以连接到 StarRocks 并执行 `starrocks-create.all.sql` 文件，以在 StarRocks 中创建数据库和表。建议您使用 SQL 文件中的默认表创建语句来创建 [主键表](../table_design/table_types/primary_key_table.md)。

    > **注意**
    >
    > 您还可以根据您的业务需求修改表创建语句，并创建一个不使用主键表的表。但是，源 MySQL 数据库中的 DELETE 操作无法同步到非主键表。创建此类表时请谨慎。

    ```Bash
    mysql -h <fe_host> -P <fe_query_port> -u user2 -pxxxxxx < starrocks-create.all.sql
    ```

    如果数据需要在写入目标 StarRocks 表之前由 Flink 处理，则源表和目标表之间的表结构将不同。在这种情况下，您必须修改表创建语句。在此示例中，目标表仅需要 `product_id` 和 `product_name` 列以及商品销售的实时排名。您可以使用以下表创建语句。

    ```Bash
    CREATE DATABASE IF NOT EXISTS `demo`;

    CREATE TABLE IF NOT EXISTS `demo`.`orders` (
    `product_id` INT(11) NOT NULL COMMENT "",
    `product_name` STRING NOT NULL COMMENT "",
    `sales_cnt` BIGINT NOT NULL COMMENT ""
    ) ENGINE=olap
    PRIMARY KEY(`product_id`)
    DISTRIBUTED BY HASH(`product_id`)
    PROPERTIES (
    "replication_num" = "3"
    );
    ```

    > **注意**
    >
    > 从 v2.5.7 开始，StarRocks 可以在您创建表或添加分区时自动设置 bucket 数量 (BUCKETS)。您不再需要手动设置 bucket 数量。有关详细信息，请参见 [设置 bucket 数量](../table_design/data_distribution/Data_distribution.md#set-the-number-of-buckets)。

## 同步数据

运行 Flink 集群并提交 Flink 作业，以将 MySQL 中的完整数据和增量数据持续同步到 StarRocks。

1. 转到 Flink 目录并运行以下命令，以在 Flink SQL 客户端上运行 `flink-create.all.sql` 文件。

    ```Bash
    ./bin/sql-client.sh -f flink-create.all.sql
    ```

    此 SQL 文件定义了动态表 `source table` 和 `sink table`、查询语句 `INSERT INTO SELECT`，并指定了连接器、源数据库和目标数据库。执行此文件后，会将 Flink 作业提交到 Flink 集群以启动数据同步。

    > **注意**
    >
    > - 确保已启动 Flink 集群。您可以通过运行 `flink/bin/start-cluster.sh` 来启动 Flink 集群。
    > - 如果您的 Flink 版本早于 1.13，您可能无法直接运行 SQL 文件 `flink-create.all.sql`。您需要在 SQL 客户端的命令行界面 (CLI) 中逐个执行此文件中的 SQL 语句。您还需要转义 `\` 字符。
    >
    > ```Bash
    > 'sink.properties.column_separator' = '\\x01'
    > 'sink.properties.row_delimiter' = '\\x02'  
    > ```

    **在同步期间处理数据**：

    如果您需要在同步期间处理数据，例如对数据执行 GROUP BY 或 JOIN，您可以修改 `flink-create.all.sql` 文件。以下示例通过执行 COUNT (*) 和 GROUP BY 来计算商品销售的实时排名。

    ```Bash
        $ ./bin/sql-client.sh -f flink-create.all.sql
        No default environment is specified.
        Searching for '/home/disk1/flink-1.13.6/conf/sql-client-defaults.yaml'...not found.
        [INFO] Executing SQL from file.

        Flink SQL> CREATE DATABASE IF NOT EXISTS `default_catalog`.`demo`;
        [INFO] Execute statement succeed.

        -- 基于 MySQL 中的 order 表创建一个动态表 `source table`。
        Flink SQL> 
        CREATE TABLE IF NOT EXISTS `default_catalog`.`demo`.`orders_src` (`order_id` BIGINT NOT NULL,
        `product_id` INT NULL,
        `order_date` TIMESTAMP NOT NULL,
        `customer_name` STRING NOT NULL,
        `product_name` STRING NOT NULL,
        `price` DECIMAL(10, 5) NULL,
        PRIMARY KEY(`order_id`)
        NOT ENFORCED
        ) with ('connector' = 'mysql-cdc',
        'hostname' = 'xxx.xx.xxx.xxx',
        'port' = '3306',
        'username' = 'root',
        'password' = '',
        'database-name' = 'demo',
        'table-name' = 'orders'
        );
        [INFO] Execute statement succeed.

        -- 创建一个动态表 `sink table`。
        Flink SQL> 
        CREATE TABLE IF NOT EXISTS `default_catalog`.`demo`.`orders_sink` (`product_id` INT NOT NULL,
        `product_name` STRING NOT NULL,
        `sales_cnt` BIGINT NOT NULL,
        PRIMARY KEY(`product_id`)
        NOT ENFORCED
        ) with ('sink.max-retries' = '10',
        'jdbc-url' = 'jdbc:mysql://<fe_host>:<fe_query_port>',
        'password' = '',
        'sink.properties.strip_outer_array' = 'true',
        'sink.properties.format' = 'json',
        'load-url' = '<fe_host>:<fe_http_port>',
        'username' = 'root',
        'sink.buffer-flush.interval-ms' = '15000',
        'connector' = 'starrocks',
        'database-name' = 'demo',
        'table-name' = 'orders'
        );
        [INFO] Execute statement succeed.

        -- 实现商品销售的实时排名，其中 `sink table` 动态更新以反映 `source table` 中的数据更改。
        Flink SQL> 
        INSERT INTO `default_catalog`.`demo`.`orders_sink` select product_id,product_name, count(*) as cnt from `default_catalog`.`demo`.`orders_src` group by product_id,product_name;
        [INFO] Submitting SQL update statement to the cluster...
        [INFO] SQL update statement has been successfully submitted to the cluster:
        Job ID: 5ae005c4b3425d8bb13fe660260a35da
    ```

    如果您只需要同步一部分数据，例如付款时间晚于 2021 年 12 月 21 日的数据，您可以使用 `INSERT INTO SELECT` 中的 `WHERE` 子句来设置筛选条件，例如 `WHERE pay_dt > '2021-12-21'`。不满足此条件的数据将不会同步到 StarRocks。

    如果返回以下结果，则表示已提交 Flink 作业以进行完整和增量同步。

    ```SQL
    [INFO] Submitting SQL update statement to the cluster...
    [INFO] SQL update statement has been successfully submitted to the cluster:
    Job ID: 5ae005c4b3425d8bb13fe660260a35da
    ```

2. 您可以使用 [Flink WebUI](https://nightlies.apache.org/flink/flink-docs-master/docs/try-flink/flink-operations-playground/#flink-webui) 或在 Flink SQL 客户端上运行 `bin/flink list -running` 命令，以查看 Flink 集群中正在运行的 Flink 作业和作业 ID。

    - Flink WebUI
      ![img](../_assets/4.9.3.png)

    - `bin/flink list -running`

    ```Bash
        $ bin/flink list -running
        Waiting for response...
        ------------------ Running/Restarting Jobs -------------------
        13.10.2022 15:03:54 : 040a846f8b58e82eb99c8663424294d5 : insert-into_default_catalog.lily.example_tbl1_sink (RUNNING)
        --------------------------------------------------------------
    ```

    > **注意**
    >
    > 如果作业异常，您可以使用 Flink WebUI 或通过查看 Flink 1.14.5 的 `/log` 目录中的日志文件来执行故障排除。

## 常见问题

### 为不同的表使用不同的 flink-connector-starrocks 配置

如果数据源中的某些表经常更新，并且您想要加速 flink-connector-starrocks 的加载速度，则必须在 SMT 配置文件 `config_prod.conf` 中为每个表设置单独的 flink-connector-starrocks 配置。

```Bash
[table-rule.1]
# 用于匹配数据库以设置属性的模式
database = ^order.*$
# 用于匹配表以设置属性的模式
table = ^.*$

############################################
### Flink sink configurations
### DO NOT set `connector`, `table-name`, `database-name`. They are auto-generated
############################################
flink.starrocks.jdbc-url=jdbc:mysql://<fe_host>:<fe_query_port>
flink.starrocks.load-url= <fe_host>:<fe_http_port>
flink.starrocks.username=user2
flink.starrocks.password=xxxxxx
flink.starrocks.sink.properties.format=csv
flink.starrocks.sink.properties.column_separator=\x01
flink.starrocks.sink.properties.row_delimiter=\x02
flink.starrocks.sink.buffer-flush.interval-ms=15000

[table-rule.2]
# 用于匹配数据库以设置属性的模式
database = ^order2.*$
# 用于匹配表以设置属性的模式
table = ^.*$

############################################
### Flink sink configurations
### DO NOT set `connector`, `table-name`, `database-name`. They are auto-generated
############################################
flink.starrocks.jdbc-url=jdbc:mysql://<fe_host>:<fe_query_port>
flink.starrocks.load-url= <fe_host>:<fe_http_port>
flink.starrocks.username=user2
flink.starrocks.password=xxxxxx
flink.starrocks.sink.properties.format=csv
flink.starrocks.sink.properties.column_separator=\x01
flink.starrocks.sink.properties.row_delimiter=\x02
flink.starrocks.sink.buffer-flush.interval-ms=10000
```

### 将 MySQL 分片后的多个表同步到一个 StarRocks 表中

执行分片后，一个 MySQL 表中的数据可能会拆分为多个表，甚至分布到多个数据库中。所有表都具有相同的 schema。在这种情况下，您可以设置 `[table-rule]` 以将这些表同步到一个 StarRocks 表中。例如，MySQL 有两个数据库 `edu_db_1` 和 `edu_db_2`，每个数据库都有两个表 `course_1 和 course_2`，并且所有表的 schema 都相同。您可以使用以下 `[table-rule]` 配置将所有表同步到一个 StarRocks 表中。

> **注意**
>
> StarRocks 表的名称默认为 `course__auto_shard`。如果您需要使用其他名称，您可以在 SQL 文件 `starrocks-create.all.sql` 和 `flink-create.all.sql` 中修改它。

```Bash
[table-rule.1]
# 用于匹配数据库以设置属性的模式
database = ^edu_db_[0-9]*$
# 用于匹配表以设置属性的模式
table = ^course_[0-9]*$

############################################
### Flink sink configurations
### DO NOT set `connector`, `table-name`, `database-name`. They are auto-generated
############################################
flink.starrocks.jdbc-url = jdbc: mysql://xxx.xxx.x.x:xxxx
flink.starrocks.load-url = xxx.xxx.x.x:xxxx
flink.starrocks.username = user2
flink.starrocks.password = xxxxxx
flink.starrocks.sink.properties.format=csv
flink.starrocks.sink.properties.column_separator =\x01
flink.starrocks.sink.properties.row_delimiter =\x02
flink.starrocks.sink.buffer-flush.interval-ms = 5000
```

### 导入 JSON 格式的数据

在前面的示例中，数据以 CSV 格式导入。如果您无法选择合适的分隔符，则需要替换 `[table-rule]` 中 `flink.starrocks.*` 的以下参数。

```Plain
flink.starrocks.sink.properties.format=csv
flink.starrocks.sink.properties.column_separator =\x01
flink.starrocks.sink.properties.row_delimiter =\x02
```

传入以下参数后，将以 JSON 格式导入数据。

```Plain
flink.starrocks.sink.properties.format=json
flink.starrocks.sink.properties.strip_outer_array=true
```

> **注意**
>
> 此方法会稍微降低加载速度。

### 将多个 INSERT INTO 语句作为一个 Flink 作业执行

您可以使用 `flink-create.all.sql` 文件中的 [STATEMENT SET](https://nightlies.apache.org/flink/flink-docs-master/docs/dev/table/sqlclient/#execute-a-set-of-sql-statements) 语法将多个 INSERT INTO 语句作为一个 Flink 作业执行，这可以防止多个语句占用过多的 Flink 作业资源，并提高执行多个查询的效率。

> **注意**
>
> Flink 从 1.13 开始支持 STATEMENT SET 语法。

1. 打开 `result/flink-create.all.sql` 文件。

2. 修改文件中的 SQL 语句。将所有 INSERT INTO 语句移动到文件末尾。将 `EXECUTE STATEMENT SET BEGIN` 放在第一个 INSERT INTO 语句之前，并将 `END;` 放在最后一个 INSERT INTO 语句之后。

> **注意**
>
> CREATE DATABASE 和 CREATE TABLE 的位置保持不变。

```SQL
CREATE DATABASE IF NOT EXISTS db;
CREATE TABLE IF NOT EXISTS db.a1;
CREATE TABLE IF NOT EXISTS db.b1;
CREATE TABLE IF NOT EXISTS db.a2;
CREATE TABLE IF NOT EXISTS db.b2;
EXECUTE STATEMENT SET 
BEGIN-- one or more INSERT INTO statements
INSERT INTO db.a1 SELECT * FROM db.b1;
INSERT INTO db.a2 SELECT * FROM db.b2;
END;
```