---
displayed_sidebar: docs
---

# 使用 Spark Load 批量导入数据

Spark Load 使用外部 Apache Spark™ 资源来预处理导入的数据，从而提高导入性能并节省计算资源。它主要用于 **初始迁移** 和将 **大量数据导入** 到 StarRocks 中（数据量高达 TB 级别）。

Spark Load 是一种**异步**导入方法，用户需要通过 MySQL 协议创建 Spark 类型的导入作业，并使用 `SHOW LOAD` 查看导入结果。

> **注意**
>
> - 只有对 StarRocks 表具有 INSERT 权限的用户才能将数据导入到该表中。您可以按照 [GRANT](../sql-reference/sql-statements/account-management/GRANT.md) 中提供的说明授予所需的权限。
> - Spark Load 不能用于将数据导入到主键表。

## 术语解释

- **Spark ETL**：主要负责导入过程中的数据 ETL，包括全局字典构建（BITMAP 类型）、分区、排序、聚合等。
- **Broker**：Broker 是一个独立的无状态进程。它封装了文件系统接口，并为 StarRocks 提供了从远端存储系统读取文件的能力。
- **Global Dictionary**：保存将数据从原始值映射到编码值的数据结构。原始值可以是任何数据类型，而编码值是整数。全局字典主要用于预计算精确去重的场景。

## 原理

用户通过 MySQL 客户端提交 Spark 类型的导入作业；FE 记录元数据并返回提交结果。

spark load 任务的执行分为以下几个主要阶段。

1. 用户将 spark load 作业提交给 FE。
2. FE 调度提交 ETL 任务到 Apache Spark™ 集群执行。
3. Apache Spark™ 集群执行 ETL 任务，包括全局字典构建（BITMAP 类型）、分区、排序、聚合等。
4. ETL 任务完成后，FE 获取每个预处理切片的数据路径，并调度相关的 BE 执行 Push 任务。
5. BE 通过 Broker 进程从 HDFS 读取数据，并将其转换为 StarRocks 存储格式。
    > 如果您选择不使用 Broker 进程，BE 将直接从 HDFS 读取数据。
6. FE 调度生效版本并完成导入作业。

下图说明了 spark load 的主要流程。

![Spark load](../_assets/4.3.2-1.png)

---

## Global Dictionary

### 适用场景

目前，StarRocks 中的 BITMAP 列是使用 Roaringbitmap 实现的，它只接受整数作为输入数据类型。因此，如果您想在导入过程中为 BITMAP 列实现预计算，则需要将输入数据类型转换为整数。

在 StarRocks 现有的导入过程中，全局字典的数据结构是基于 Hive 表实现的，它保存了从原始值到编码值的映射。

### 构建过程

1. 从上游数据源读取数据，并生成一个临时 Hive 表，命名为 `hive-table`。
2. 提取 `hive-table` 的非强调字段的值，以生成一个新的 Hive 表，命名为 `distinct-value-table`。
3. 创建一个新的全局字典表，命名为 `dict-table`，其中一列用于原始值，一列用于编码值。
4. 在 `distinct-value-table` 和 `dict-table` 之间进行左连接，然后使用窗口函数对该集合进行编码。最后，将去重列的原始值和编码值都写回 `dict-table`。
5. 在 `dict-table` 和 `hive-table` 之间进行连接，以完成将 `hive-table` 中的原始值替换为整数编码值的工作。
6. `hive-table` 将被下次数据预处理读取，然后在计算后导入到 StarRocks 中。

## 数据预处理

数据预处理的基本过程如下：

1. 从上游数据源（HDFS 文件或 Hive 表）读取数据。
2. 完成读取数据的字段映射和计算，然后基于分区信息生成 `bucket-id`。
3. 基于 StarRocks 表的 Rollup 元数据生成 RollupTree。
4. 迭代 RollupTree 并执行分层聚合操作。下一层级的 Rollup 可以从上一层级的 Rollup 计算得出。
5. 每次完成聚合计算后，数据将根据 `bucket-id` 进行分桶，然后写入 HDFS。
6. 后续的 Broker 进程将从 HDFS 拉取文件并将其导入到 StarRocks BE 节点。

## 基本操作

### 配置 ETL 集群

Apache Spark™ 在 StarRocks 中用作外部计算资源，用于 ETL 工作。可能还有其他外部资源添加到 StarRocks 中，例如用于查询的 Spark/GPU、用于外部存储的 HDFS/S3、用于 ETL 的 MapReduce 等。因此，我们引入了 `Resource Management` 来管理 StarRocks 使用的这些外部资源。

在提交 Apache Spark™ 导入作业之前，请配置 Apache Spark™ 集群以执行 ETL 任务。操作语法如下：

~~~sql
-- 创建 Apache Spark™ 资源
CREATE EXTERNAL RESOURCE resource_name
PROPERTIES
(
 type = spark,
 spark_conf_key = spark_conf_value,
 working_dir = path,
 broker = broker_name,
 broker.property_key = property_value
);

-- 删除 Apache Spark™ 资源
DROP RESOURCE resource_name;

-- 显示资源
SHOW RESOURCES
SHOW PROC "/resources";

-- 权限
GRANT USAGE_PRIV ON RESOURCE resource_name TO user_identityGRANT USAGE_PRIV ON RESOURCE resource_name TO ROLE role_name;
REVOKE USAGE_PRIV ON RESOURCE resource_name FROM user_identityREVOKE USAGE_PRIV ON RESOURCE resource_name FROM ROLE role_name;
~~~

- 创建资源

**例如**：

~~~sql
-- yarn 集群模式
CREATE EXTERNAL RESOURCE "spark0"
PROPERTIES
(
    "type" = "spark",
    "spark.master" = "yarn",
    "spark.submit.deployMode" = "cluster",
    "spark.jars" = "xxx.jar,yyy.jar",
    "spark.files" = "/tmp/aaa,/tmp/bbb",
    "spark.executor.memory" = "1g",
    "spark.yarn.queue" = "queue0",
    "spark.hadoop.yarn.resourcemanager.address" = "127.0.0.1:9999",
    "spark.hadoop.fs.defaultFS" = "hdfs://127.0.0.1:10000",
    "working_dir" = "hdfs://127.0.0.1:10000/tmp/starrocks",
    "broker" = "broker0",
    "broker.username" = "user0",
    "broker.password" = "password0"
);

-- yarn HA 集群模式
CREATE EXTERNAL RESOURCE "spark1"
PROPERTIES
(
    "type" = "spark",
    "spark.master" = "yarn",
    "spark.submit.deployMode" = "cluster",
    "spark.hadoop.yarn.resourcemanager.ha.enabled" = "true",
    "spark.hadoop.yarn.resourcemanager.ha.rm-ids" = "rm1,rm2",
    "spark.hadoop.yarn.resourcemanager.hostname.rm1" = "host1",
    "spark.hadoop.yarn.resourcemanager.hostname.rm2" = "host2",
    "spark.hadoop.fs.defaultFS" = "hdfs://127.0.0.1:10000",
    "working_dir" = "hdfs://127.0.0.1:10000/tmp/starrocks",
    "broker" = "broker1"
);
~~~

`resource-name` 是在 StarRocks 中配置的 Apache Spark™ 资源的名称。

`PROPERTIES` 包括与 Apache Spark™ 资源相关的参数，如下所示：
> **注意**
>
> 有关 Apache Spark™ 资源 PROPERTIES 的详细说明，请参见 [CREATE RESOURCE](../sql-reference/sql-statements/Resource/CREATE_RESOURCE.md)。

- Spark 相关参数：
  - `type`：资源类型，必需，目前仅支持 `spark`。
  - `spark.master`：必需，目前仅支持 `yarn`。
    - `spark.submit.deployMode`：Apache Spark™ 程序的部署模式，必需，目前支持 `cluster` 和 `client`。
    - `spark.hadoop.fs.defaultFS`：如果 master 是 yarn，则为必需。
    - 与 yarn 资源管理器相关的参数，必需。
      - 单个节点上的一个 ResourceManager
        `spark.hadoop.yarn.resourcemanager.address`：单点资源管理器的地址。
      - ResourceManager HA
        > 您可以选择指定 ResourceManager 的主机名或地址。
        - `spark.hadoop.yarn.resourcemanager.ha.enabled`：启用资源管理器 HA，设置为 `true`。
        - `spark.hadoop.yarn.resourcemanager.ha.rm-ids`：资源管理器逻辑 ID 列表。
        - `spark.hadoop.yarn.resourcemanager.hostname.rm-id`：对于每个 rm-id，指定与资源管理器对应的主机名。
        - `spark.hadoop.yarn.resourcemanager.address.rm-id`：对于每个 rm-id，指定客户端提交作业的 `host:port`。

- `*working_dir`：ETL 使用的目录。如果 Apache Spark™ 用作 ETL 资源，则为必需。例如：`hdfs://host:port/tmp/starrocks`。

- Broker 相关参数：
  - `broker`：Broker 名称。如果 Apache Spark™ 用作 ETL 资源，则为必需。您需要提前使用 `ALTER SYSTEM ADD BROKER` 命令完成配置。
  - `broker.property_key`：Broker 进程读取 ETL 生成的中间文件时要指定的信息（例如，身份验证信息）。

**注意**：

以上是通过 Broker 进程加载的参数说明。如果您打算在没有 Broker 进程的情况下加载数据，则应注意以下事项。

- 您无需指定 `broker`。
- 如果您需要配置用户身份验证和 NameNode 节点的 HA，则需要在 HDFS 集群中的 hdfs-site.xml 文件中配置参数，有关参数的说明，请参见 [broker_properties](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md#hdfs)。并且您需要将 **hdfs-site.xml** 文件移动到每个 FE 的 **$FE_HOME/conf** 下和每个 BE 的 **$BE_HOME/conf** 下。

> 注意
>
> 如果 HDFS 文件只能由特定用户访问，您仍然需要在 `broker.name` 中指定 HDFS 用户名，并在 `broker.password` 中指定用户密码。

- 查看资源

常规帐户只能查看他们具有 `USAGE-PRIV` 访问权限的资源。root 和 admin 帐户可以查看所有资源。

- 资源权限

资源权限通过 `GRANT REVOKE` 进行管理，目前仅支持 `USAGE-PRIV` 权限。您可以将 `USAGE-PRIV` 权限授予用户或角色。

~~~sql
-- 授予 user0 访问 spark0 资源的权限
GRANT USAGE_PRIV ON RESOURCE "spark0" TO "user0"@"%";

-- 授予 role0 访问 spark0 资源的权限
GRANT USAGE_PRIV ON RESOURCE "spark0" TO ROLE "role0";

-- 授予 user0 访问所有资源的权限
GRANT USAGE_PRIV ON RESOURCE* TO "user0"@"%";

-- 授予 role0 访问所有资源的权限
GRANT USAGE_PRIV ON RESOURCE* TO ROLE "role0";

-- 撤销 user0 对 spark0 资源的使用权限
REVOKE USAGE_PRIV ON RESOURCE "spark0" FROM "user0"@"%";
~~~

### 配置 Spark Client

为 FE 配置 Spark 客户端，以便后者可以通过执行 `spark-submit` 命令来提交 Spark 任务。建议使用官方版本的 Spark2 2.4.5 或更高版本 [spark download address](https://archive.apache.org/dist/spark/)。下载后，请按照以下步骤完成配置。

- 配置 `SPARK-HOME`
  
将 Spark 客户端放置在与 FE 相同的机器上的目录中，并在 FE 配置文件中将 `spark_home_default_dir` 配置为此目录，默认情况下，该目录是 FE 根目录中的 `lib/spark2x` 路径，并且不能为空。

- **配置 SPARK 依赖包**
  
要配置依赖包，请压缩并归档 Spark 客户端下 jars 文件夹中的所有 jar 文件，并将 FE 配置中的 `spark_resource_path` 项配置为此 zip 文件。如果此配置为空，FE 将尝试在 FE 根目录中查找 `lib/spark2x/jars/spark-2x.zip` 文件。如果 FE 无法找到它，它将报告错误。

提交 spark load 作业时，归档的依赖文件将上传到远程存储库。默认存储库路径位于 `working_dir/{cluster_id}` 目录下，并以 `--spark-repository--{resource-name}` 命名，这意味着集群中的一个资源对应于一个远程存储库。目录结构引用如下：

~~~bash
---spark-repository--spark0/

   |---archive-1.0.0/

   |        |\---lib-990325d2c0d1d5e45bf675e54e44fb16-spark-dpp-1.0.0\-jar-with-dependencies.jar

   |        |\---lib-7670c29daf535efe3c9b923f778f61fc-spark-2x.zip

   |---archive-1.1.0/

   |        |\---lib-64d5696f99c379af2bee28c1c84271d5-spark-dpp-1.1.0\-jar-with-dependencies.jar

   |        |\---lib-1bbb74bb6b264a270bc7fca3e964160f-spark-2x.zip

   |---archive-1.2.0/

   |        |-...

~~~

除了 spark 依赖项（默认情况下命名为 `spark-2x.zip`）之外，FE 还会将 DPP 依赖项上传到远程存储库。如果 spark load 提交的所有依赖项已经存在于远程存储库中，则无需再次上传依赖项，从而节省了每次重复上传大量文件的时间。

### 配置 YARN Client

为 FE 配置 yarn 客户端，以便 FE 可以执行 yarn 命令来获取正在运行的应用程序的状态或终止它。建议使用官方版本的 Hadoop2 2.5.2 或更高版本 ([hadoop download address](https://archive.apache.org/dist/hadoop/common/))。下载后，请按照以下步骤完成配置：

- **配置 YARN 可执行路径**
  
将下载的 yarn 客户端放置在与 FE 相同的机器上的目录中，并在 FE 配置文件中将 `yarn_client_path` 项配置为 yarn 的二进制可执行文件，默认情况下，该文件是 FE 根目录中的 `lib/yarn-client/hadoop/bin/yarn` 路径。

- **配置生成 YARN 所需的配置文件的路径（可选）**
  
当 FE 通过 yarn 客户端获取应用程序的状态或终止应用程序时，默认情况下，StarRocks 会在 FE 根目录的 `lib/yarn-config` 路径中生成执行 yarn 命令所需的配置文件。可以通过配置 FE 配置文件中的 `yarn_config_dir` 条目来修改此路径，该条目当前包括 `core-site.xml` 和 `yarn-site.xml`。

### 创建导入作业

**语法：**

~~~sql
LOAD LABEL load_label
    (data_desc, ...)
WITH RESOURCE resource_name 
[resource_properties]
[PROPERTIES (key1=value1, ... )]

* load_label:
    db_name.label_name

* data_desc:
    DATA INFILE ('file_path', ...)
    [NEGATIVE]
    INTO TABLE tbl_name
    [PARTITION (p1, p2)]
    [COLUMNS TERMINATED BY separator ]
    [(col1, ...)]
    [COLUMNS FROM PATH AS (col2, ...)]
    [SET (k1=f1(xx), k2=f2(xx))]
    [WHERE predicate]

    DATA FROM TABLE hive_external_tbl
    [NEGATIVE]
    INTO TABLE tbl_name
    [PARTITION (p1, p2)]
    [SET (k1=f1(xx), k2=f2(xx))]
    [WHERE predicate]

* resource_properties:
 (key2=value2, ...)
~~~

**示例 1**：上游数据源为 HDFS 的情况

~~~sql
LOAD LABEL db1.label1
(
    DATA INFILE("hdfs://abc.com:8888/user/starrocks/test/ml/file1")
    INTO TABLE tbl1
    COLUMNS TERMINATED BY ","
    (tmp_c1,tmp_c2)
    SET
    (
        id=tmp_c2,
        name=tmp_c1
    ),
    DATA INFILE("hdfs://abc.com:8888/user/starrocks/test/ml/file2")
    INTO TABLE tbl2
    COLUMNS TERMINATED BY ","
    (col1, col2)
    where col1 > 1
)
WITH RESOURCE 'spark0'
(
    "spark.executor.memory" = "2g",
    "spark.shuffle.compress" = "true"
)
PROPERTIES
(
    "timeout" = "3600"
);
~~~

**示例 2**：上游数据源为 Hive 的情况。

- 步骤 1：创建一个新的 Hive 资源

~~~sql
CREATE EXTERNAL RESOURCE hive0
PROPERTIES
( 
    "type" = "hive",
    "hive.metastore.uris" = "thrift://xx.xx.xx.xx:8080"
);
 ~~~

- 步骤 2：创建一个新的 Hive 外部表

~~~sql
CREATE EXTERNAL TABLE hive_t1
(
    k1 INT,
    K2 SMALLINT,
    k3 varchar(50),
    uuid varchar(100)
)
ENGINE=hive
PROPERTIES
( 
    "resource" = "hive0",
    "database" = "tmp",
    "table" = "t1"
);
 ~~~

- 步骤 3：提交 load 命令，要求导入的 StarRocks 表中的列存在于 Hive 外部表中。

~~~sql
LOAD LABEL db1.label1
(
    DATA FROM TABLE hive_t1
    INTO TABLE tbl1
    SET
    (
        uuid=bitmap_dict(uuid)
    )
)
WITH RESOURCE 'spark0'
(
    "spark.executor.memory" = "2g",
    "spark.shuffle.compress" = "true"
)
PROPERTIES
(
    "timeout" = "3600"
);
 ~~~

Spark load 中参数的介绍：

- **Label**
  
导入作业的 Label。每个导入作业都有一个 Label，该 Label 在数据库中是唯一的，遵循与 broker load 相同的规则。

- **数据描述类参数**
  
目前，支持的数据源是 CSV 和 Hive 表。其他规则与 broker load 相同。

- **导入作业参数**
  
导入作业参数是指属于导入语句的 `opt_properties` 部分的参数。这些参数适用于整个导入作业。规则与 broker load 相同。

- **Spark 资源参数**
  
Spark 资源需要提前配置到 StarRocks 中，并且用户需要被授予 USAGE-PRIV 权限，然后才能将资源应用于 Spark load。
当用户有临时需求时，可以设置 Spark 资源参数，例如为作业添加资源和修改 Spark 配置。该设置仅对该作业生效，不影响 StarRocks 集群中的现有配置。

~~~sql
WITH RESOURCE 'spark0'
(
    "spark.driver.memory" = "1g",
    "spark.executor.memory" = "3g"
)
~~~

- **当数据源为 Hive 时导入**
  
目前，要在导入过程中使用 Hive 表，您需要创建 `Hive` 类型的外部表，然后在提交导入命令时指定其名称。

- **导入过程以构建全局字典**
  
在 load 命令中，您可以按以下格式指定构建全局字典所需的字段：`StarRocks 字段名称=bitmap_dict(hive 表字段名称)` 请注意，目前**仅当上游数据源是 Hive 表时才支持全局字典**。

- **加载二进制类型数据**

从 v2.5.17 开始，Spark Load 支持 bitmap_from_binary 函数，该函数可以将二进制数据转换为 bitmap 数据。如果 Hive 表或 HDFS 文件的列类型为二进制，并且 StarRocks 表中对应的列是 bitmap 类型的聚合列，则可以在 load 命令中按以下格式指定字段，`StarRocks 字段名称=bitmap_from_binary(Hive 表字段名称)`。这样就不需要构建全局字典。

## 查看导入作业

Spark load 导入是异步的，broker load 也是如此。用户必须记录导入作业的 label，并在 `SHOW LOAD` 命令中使用它来查看导入结果。查看导入的命令对于所有导入方法都是通用的。示例如下。

有关返回参数的详细说明，请参阅 Broker Load。不同之处如下。

~~~sql
mysql> show load order by createtime desc limit 1\G
*************************** 1. row ***************************
  JobId: 76391
  Label: label1
  State: FINISHED
 Progress: ETL:100%; LOAD:100%
  Type: SPARK
 EtlInfo: unselected.rows=4; dpp.abnorm.ALL=15; dpp.norm.ALL=28133376
 TaskInfo: cluster:cluster0; timeout(s):10800; max_filter_ratio:5.0E-5
 ErrorMsg: N/A
 CreateTime: 2019-07-27 11:46:42
 EtlStartTime: 2019-07-27 11:46:44
 EtlFinishTime: 2019-07-27 11:49:44
 LoadStartTime: 2019-07-27 11:49:44
LoadFinishTime: 2019-07-27 11:50:16
  URL: http://1.1.1.1:8089/proxy/application_1586619723848_0035/
 JobDetails: {"ScannedRows":28133395,"TaskNumber":1,"FileNumber":1,"FileSize":200000}
~~~

- **State**
  
导入作业的当前阶段。
PENDING：已提交作业。
ETL：已提交 Spark ETL。
LOADING：FE 调度 BE 执行 push 操作。
FINISHED：push 已完成，版本已生效。

导入作业有两个最终阶段 – `CANCELLED` 和 `FINISHED`，都表示 load 作业已完成。`CANCELLED` 表示导入失败，`FINISHED` 表示导入成功。

- **Progress**
  
导入作业进度的描述。有两种类型的进度 – ETL 和 LOAD，它们对应于导入过程的两个阶段，ETL 和 LOADING。

- LOAD 的进度范围为 0~100%。
  
`LOAD 进度 = 当前已完成的所有副本导入的 tablet 数量 / 此导入作业的 tablet 总数 * 100%`。

- 如果所有表都已导入，则 LOAD 进度为 99%，当导入进入最终验证阶段时，将更改为 100%。

- 导入进度不是线性的。如果在一段时间内进度没有变化，并不意味着导入没有执行。

- **Type**

 导入作业的类型。SPARK 表示 spark load。

- **CreateTime/EtlStartTime/EtlFinishTime/LoadStartTime/LoadFinishTime**

这些值表示创建导入的时间、ETL 阶段开始的时间、ETL 阶段完成的时间、LOADING 阶段开始的时间以及整个导入作业完成的时间。

- **JobDetails**

显示作业的详细运行状态，包括导入的文件数、总大小（以字节为单位）、子任务数、正在处理的原始行数等。例如：

~~~json
 {"ScannedRows":139264,"TaskNumber":1,"FileNumber":1,"FileSize":940754064}
~~~

- **URL**

您可以将输入复制到浏览器以访问相应应用程序的 Web 界面。

### 查看 Apache Spark™ Launcher 提交日志

有时，用户需要查看在 Apache Spark™ 作业提交期间生成的详细日志。默认情况下，日志保存在 FE 根目录中的 `log/spark_launcher_log` 路径中，命名为 `spark-launcher-{load-job-id}-{label}.log`。日志在此目录中保存一段时间，并在 FE 元数据中的导入信息被清除时删除。默认保留时间为 3 天。

### 取消导入

当 Spark load 作业状态不是 `CANCELLED` 或 `FINISHED` 时，用户可以通过指定导入作业的 Label 手动取消它。

---

## 相关系统配置

**FE 配置：** 以下配置是 Spark load 的系统级配置，适用于所有 Spark load 导入作业。可以通过修改 `fe.conf` 来调整配置值。

- enable-spark-load：启用 Spark load 和资源创建，默认值为 false。
- spark-load-default-timeout-second：作业的默认超时时间为 259200 秒（3 天）。
- spark-home-default-dir：Spark 客户端路径 (`fe/lib/spark2x`)。
- spark-resource-path：打包的 S park 依赖项文件的路径（默认为空）。
- spark-launcher-log-dir：Spark 客户端的提交日志存储的目录 (`fe/log/spark-launcher-log`)。
- yarn-client-path：yarn 二进制可执行文件的路径 (`fe/lib/yarn-client/hadoop/bin/yarn`)。
- yarn-config-dir：Yarn 的配置文件路径 (`fe/lib/yarn-config`)。

---

## 最佳实践

使用 Spark load 最合适的场景是原始数据位于文件系统 (HDFS) 中，并且数据量在数十 GB 到 TB 级别。对于较小的数据量，请使用 Stream Load 或 Broker Load。

有关完整的 spark load 导入示例，请参阅 github 上的演示：[https://github.com/StarRocks/demo/blob/master/docs/03_sparkLoad2StarRocks.md](https://github.com/StarRocks/demo/blob/master/docs/03_sparkLoad2StarRocks.md)

## 常见问题解答

- `Error: When running with master 'yarn' either HADOOP-CONF-DIR or YARN-CONF-DIR must be set in the environment.`

 使用 Spark Load 时，未在 Spark 客户端的 `spark-env.sh` 中配置 `HADOOP-CONF-DIR` 环境变量。

- `Error: Cannot run program "xxx/bin/spark-submit": error=2, No such file or directory`

 使用 Spark Load 时，`spark_home_default_dir` 配置项未指定 Spark 客户端根目录。

- `Error: File xxx/jars/spark-2x.zip does not exist.`

 使用 Spark load 时，`spark-resource-path` 配置项未指向打包的 zip 文件。

- `Error: yarn client does not exist in path: xxx/yarn-client/hadoop/bin/yarn`

 使用 Spark load 时，yarn-client-path 配置项未指定 yarn 可执行文件。

- `ERROR: Cannot execute hadoop-yarn/bin/... /libexec/yarn-config.sh`

 将 Hadoop 与 CDH 结合使用时，需要配置 `HADOOP_LIBEXEC_DIR` 环境变量。
 由于 `hadoop-yarn` 和 hadoop 目录不同，因此默认的 `libexec` 目录将查找 `hadoop-yarn/bin/... /libexec`，而 `libexec` 位于 hadoop 目录中。
 ```yarn application status`` 命令获取 Spark 任务状态报告错误，导致导入作业失败。