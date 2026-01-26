---
displayed_sidebar: docs
unlisted: true
---

# 从 \<SOURCE\> 模板加载数据

## 模板说明

### 关于样式的说明

技术文档通常包含指向各处其他文档的链接。查看此文档时，您可能会注意到页面上的链接很少，几乎所有链接都位于文档底部的**更多信息**部分。并非每个关键字都需要链接到另一个页面，请假定读者知道 `CREATE TABLE` 的含义，如果他们不知道，他们可以点击搜索栏来查找。可以在文档中添加注释，告诉读者还有其他选项，详细信息在**更多信息**部分中进行了描述；这可以让需要信息的人知道他们可以在完成手头的任务后***稍后***阅读它。

### 模板

此模板基于从 Amazon S3 加载数据的过程，其中的某些部分不适用于从其他来源加载数据。请专注于此模板的流程，不要担心包含每个部分；流程应为：

#### 简介

介绍性文字，让读者知道如果他们遵循本指南，最终结果会是什么。对于 S3 文档，最终结果是“以异步或同步方式从 S3 加载数据”。

#### 为什么？

- 对使用该技术解决的业务问题的描述
- 所描述方法（如果存在）的优点和缺点

#### 数据流或其他图表

图表或图像可能会有所帮助。如果您描述的技术很复杂并且图像有帮助，请使用一个。如果您描述的技术会产生一些可视化的东西（例如，使用 Superset 分析数据），那么一定要包含最终产品的图像。

如果流程不明显，请使用数据流图。当命令导致 StarRocks 运行多个进程并组合这些进程的输出，然后操作数据时，可能需要描述数据流。在此模板中，描述了两种加载数据的方法。其中一种很简单，没有数据流部分；另一种更复杂（StarRocks 正在处理复杂的工作，而不是用户！），并且复杂的选项包括数据流部分。

#### 带有验证部分的示例

请注意，示例应位于语法详细信息和其他深入的技术详细信息之前。许多读者会来阅读文档以查找他们可以复制、粘贴和修改的特定技术。

如果可能，请提供一个可以工作的示例，并包含要使用的数据集。此模板中的示例使用存储在 S3 中的数据集，任何拥有 AWS 账户并且可以使用密钥和密码进行身份验证的人都可以使用该数据集。通过提供数据集，示例对读者更有价值，因为他们可以充分体验所描述的技术。

确保示例按编写方式工作。这意味着两件事：

1. 您已按呈现的顺序运行命令
2. 您已包含必要的先决条件。例如，如果您的示例引用数据库 `foo`，那么您可能需要以 `CREATE DATABASE foo;`、`USE foo;` 作为前缀。

验证非常重要。如果您描述的过程包括多个步骤，那么每当应该完成某些事情时，都包含一个验证步骤；这有助于避免读者到达终点并意识到他们在第 10 步中存在拼写错误。在此示例中，“检查进度”和 `DESCRIBE user_behavior_inferred;` 步骤用于验证。

#### 更多信息

在模板的末尾，有一个位置可以放置指向相关信息的链接，包括您在正文中提到的可选信息的链接。

### 嵌入在模板中的注释

模板注释的格式与我们格式化文档注释的方式有意不同，以便在您处理模板时引起您的注意。请删除粗体斜体注释：

```markdown
***Note: descriptive text***
```

## 最后，模板的开始

***Note: If there are multiple recommended choices, tell the
reader this in the intro. For example, when loading from S3,
there is an option for synchronous loading, and asynchronous loading:***

StarRocks 提供了两种从 S3 加载数据的选项：

1. 使用 Broker Load 进行异步加载
2. 使用 `FILES()` 表函数进行同步加载

***Note: Tell the reader WHY they would choose one choice over the other:***

小型数据集通常使用 `FILES()` 表函数同步加载，大型数据集通常使用 Broker Load 异步加载。这两种方法各有优点，如下所述。

> **NOTE**
>
> 只有对 StarRocks 表具有 INSERT 权限的用户才能将数据加载到 StarRocks 表中。如果您没有 INSERT 权限，请按照 [GRANT](../sql-reference/sql-statements/account-management/GRANT.md) 中提供的说明，将 INSERT 权限授予用于连接到 StarRocks 集群的用户。

## 使用 Broker Load

异步 Broker Load 进程处理与 S3 的连接、提取数据以及将数据存储在 StarRocks 中。

### Broker Load 的优点

- Broker Load 支持在加载期间进行数据转换、UPSERT 和 DELETE 操作。
- Broker Load 在后台运行，客户端无需保持连接即可继续作业。
- Broker Load 是长时间运行作业的首选，默认超时时间为 4 小时。
- 除了 Parquet 和 ORC 文件格式外，Broker Load 还支持 CSV 文件。

### 数据流

***Note: Processes that involve multiple components or steps may be easier to understand with a diagram. This example includes a diagram that helps describe the steps that happen when a user chooses the Broker Load option.***

![Broker Load 的工作流程](../_assets/broker_load_how-to-work_en.png)

1. 用户创建一个 load job。
2. 前端 (FE) 创建一个查询计划并将该计划分发到后端节点 (BE)。
3. 后端 (BE) 节点从源提取数据并将数据加载到 StarRocks 中。

### 典型示例

创建一个表，启动一个从 S3 提取 Parquet 文件的 load 进程，并验证数据加载的进度和成功。

> **NOTE**
>
> 这些示例使用 Parquet 格式的示例数据集，如果您想加载 CSV 或 ORC 文件，该信息链接在此页面的底部。

#### 创建表

为您的表创建一个数据库：

```SQL
CREATE DATABASE IF NOT EXISTS project;
USE project;
```

创建表。此 schema 匹配 StarRocks 账户中托管的 S3 bucket 中的示例数据集。

```SQL
DROP TABLE IF EXISTS user_behavior;

CREATE TABLE `user_behavior` (
    `UserID` int(11),
    `ItemID` int(11),
    `CategoryID` int(11),
    `BehaviorType` varchar(65533),
    `Timestamp` datetime
) ENGINE=OLAP 
DUPLICATE KEY(`UserID`)
DISTRIBUTED BY HASH(`UserID`)
PROPERTIES (
    "replication_num" = "1"
);
```

#### 收集连接详细信息

> **NOTE**
>
> 这些示例使用基于 IAM 用户的身份验证。其他身份验证方法可用，并链接在此页面的底部。

从 S3 加载数据需要具有：

- S3 bucket
- S3 对象键（对象名称），如果访问 bucket 中的特定对象。请注意，如果您的 S3 对象存储在子文件夹中，则对象键可以包含前缀。完整语法链接在**更多信息**中。
- S3 区域
- 访问密钥和密码

#### 启动 Broker Load

此作业有四个主要部分：

- `LABEL`：查询 `LOAD` 作业状态时使用的字符串。
- `LOAD` 声明：源 URI、目标表和源数据格式。
- `BROKER`：源的连接详细信息。
- `PROPERTIES`：超时值和应用于此作业的任何其他属性。

> **NOTE**
>
> 这些示例中使用的数据集托管在 StarRocks 账户的 S3 bucket 中。可以使用任何有效的 `aws.s3.access_key` 和 `aws.s3.secret_key`，因为任何 AWS 身份验证用户都可以读取该对象。在下面的命令中，将您的凭据替换为 `AAA` 和 `BBB`。

```SQL
LOAD LABEL user_behavior
(
    DATA INFILE("s3://starrocks-examples/user_behavior_sample_data.parquet")
    INTO TABLE user_behavior
    FORMAT AS "parquet"
 )
 WITH BROKER
 (
    "aws.s3.enable_ssl" = "true",
    "aws.s3.use_instance_profile" = "false",
    "aws.s3.region" = "us-east-1",
    "aws.s3.access_key" = "AAAAAAAAAAAAAAAAAAAA",
    "aws.s3.secret_key" = "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
 )
PROPERTIES
(
    "timeout" = "72000"
);
```

#### 检查进度

查询 `information_schema.loads` 表以跟踪进度。如果您有多个 `LOAD` 作业正在运行，则可以按与该作业关联的 `LABEL` 进行过滤。在下面的输出中，load job `user_behavior` 有两个条目。第一个记录显示 `CANCELLED` 状态；滚动到输出的末尾，您会看到 `listPath failed`。第二个记录显示使用有效的 AWS IAM 访问密钥和密码成功。

```SQL
SELECT * FROM information_schema.loads;
```

```SQL
SELECT * FROM information_schema.loads WHERE LABEL = 'user_behavior';
```

```plaintext
JOB_ID|LABEL                                      |DATABASE_NAME|STATE    |PROGRESS           |TYPE  |PRIORITY|SCAN_ROWS|FILTERED_ROWS|UNSELECTED_ROWS|SINK_ROWS|ETL_INFO|TASK_INFO                                           |CREATE_TIME        |ETL_START_TIME     |ETL_FINISH_TIME    |LOAD_START_TIME    |LOAD_FINISH_TIME   |JOB_DETAILS                                                                                                                                                                                                                                                    |ERROR_MSG                             |TRACKING_URL|TRACKING_SQL|REJECTED_RECORD_PATH|
------+-------------------------------------------+-------------+---------+-------------------+------+--------+---------+-------------+---------------+---------+--------+----------------------------------------------------+-------------------+-------------------+-------------------+-------------------+-------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+--------------------------------------+------------+------------+--------------------+
 10121|user_behavior                              |project      |CANCELLED|ETL:N/A; LOAD:N/A  |BROKER|NORMAL  |        0|            0|              0|        0|        |resource:N/A; timeout(s):72000; max_filter_ratio:0.0|2023-08-10 14:59:30|                   |                   |                   |2023-08-10 14:59:34|{"All backends":{},"FileNumber":0,"FileSize":0,"InternalTableLoadBytes":0,"InternalTableLoadRows":0,"ScanBytes":0,"ScanRows":0,"TaskNumber":0,"Unfinished backends":{}}                                                                                        |type:ETL_RUN_FAIL; msg:listPath failed|            |            |                    |
 10106|user_behavior                              |project      |FINISHED |ETL:100%; LOAD:100%|BROKER|NORMAL  | 86953525|            0|              0| 86953525|        |resource:N/A; timeout(s):72000; max_filter_ratio:0.0|2023-08-10 14:50:15|2023-08-10 14:50:19|2023-08-10 14:50:19|2023-08-10 14:50:19|2023-08-10 14:55:10|{"All backends":{"a5fe5e1d-d7d0-4826-ba99-c7348f9a5f2f":[10004]},"FileNumber":1,"FileSize":1225637388,"InternalTableLoadBytes":2710603082,"InternalTableLoadRows":86953525,"ScanBytes":1225637388,"ScanRows":86953525,"TaskNumber":1,"Unfinished backends":{"a5|                                      |            |            |                    |
```

您也可以在此处检查数据的子集。

```SQL
SELECT * from user_behavior LIMIT 10;
```

```plaintext
UserID|ItemID|CategoryID|BehaviorType|Timestamp          |
------+------+----------+------------+-------------------+
171146| 68873|   3002561|pv          |2017-11-30 07:11:14|
171146|146539|   4672807|pv          |2017-11-27 09:51:41|
171146|146539|   4672807|pv          |2017-11-27 14:08:33|
171146|214198|   1320293|pv          |2017-11-25 22:38:27|
171146|260659|   4756105|pv          |2017-11-30 05:11:25|
171146|267617|   4565874|pv          |2017-11-27 14:01:25|
171146|329115|   2858794|pv          |2017-12-01 02:10:51|
171146|458604|   1349561|pv          |2017-11-25 22:49:39|
171146|458604|   1349561|pv          |2017-11-27 14:03:44|
171146|478802|    541347|pv          |2017-12-02 04:52:39|
```

## 使用 `FILES()` 表函数

### `FILES()` 的优点

`FILES()` 可以推断 Parquet 数据列的数据类型，并为 StarRocks 表生成 schema。这提供了使用 `SELECT` 直接从 S3 查询文件，或者让 StarRocks 根据 Parquet 文件 schema 自动为您创建表的能力。

> **NOTE**
>
> Schema 推断是 3.1 版本中的一项新功能，仅适用于 Parquet 格式，并且尚不支持嵌套类型。

### 典型示例

有三个使用 `FILES()` 表函数的示例：

- 直接从 S3 查询数据
- 使用 schema 推断创建和加载表
- 手动创建表，然后加载数据

> **NOTE**
>
> 这些示例中使用的数据集托管在 StarRocks 账户的 S3 bucket 中。可以使用任何有效的 `aws.s3.access_key` 和 `aws.s3.secret_key`，因为任何 AWS 身份验证用户都可以读取该对象。在下面的命令中，将您的凭据替换为 `AAA` 和 `BBB`。

#### 直接从 S3 查询

使用 `FILES()` 直接从 S3 查询可以在创建表之前很好地预览数据集的内容。例如：

- 获取数据集的预览，而无需存储数据。
- 查询最小值和最大值，并确定要使用的数据类型。
- 检查 null 值。

```sql
SELECT * FROM FILES(
    "path" = "s3://starrocks-examples/user_behavior_sample_data.parquet",
    "format" = "parquet",
    "aws.s3.region" = "us-east-1",
    "aws.s3.access_key" = "AAAAAAAAAAAAAAAAAAAA",
    "aws.s3.secret_key" = "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
) LIMIT 10;
```

> **NOTE**
>
> 请注意，列名由 Parquet 文件提供。

```plaintext
UserID|ItemID |CategoryID|BehaviorType|Timestamp          |
------+-------+----------+------------+-------------------+
     1|2576651|    149192|pv          |2017-11-25 01:21:25|
     1|3830808|   4181361|pv          |2017-11-25 07:04:53|
     1|4365585|   2520377|pv          |2017-11-25 07:49:06|
     1|4606018|   2735466|pv          |2017-11-25 13:28:01|
     1| 230380|    411153|pv          |2017-11-25 21:22:22|
     1|3827899|   2920476|pv          |2017-11-26 16:24:33|
     1|3745169|   2891509|pv          |2017-11-26 19:44:31|
     1|1531036|   2920476|pv          |2017-11-26 22:02:12|
     1|2266567|   4145813|pv          |2017-11-27 00:11:11|
     1|2951368|   1080785|pv          |2017-11-27 02:47:08|
```

#### 使用 schema 推断创建表

这是前一个示例的延续；之前的查询包装在 `CREATE TABLE` 中，以使用 schema 推断自动创建表。使用带有 Parquet 文件的 `FILES()` 表函数时，不需要列名和类型来创建表，因为 Parquet 格式包括列名和类型，StarRocks 将推断 schema。

> **NOTE**
>
> 使用 schema 推断时，`CREATE TABLE` 的语法不允许设置副本数，因此请在创建表之前设置它。以下示例适用于具有单个副本的系统：
>
> `ADMIN SET FRONTEND CONFIG ('default_replication_num' ="1");`

```sql
CREATE DATABASE IF NOT EXISTS project;
USE project;

CREATE TABLE `user_behavior_inferred` AS
SELECT * FROM FILES(
    "path" = "s3://starrocks-examples/user_behavior_sample_data.parquet",
    "format" = "parquet",
    "aws.s3.region" = "us-east-1",
    "aws.s3.access_key" = "AAAAAAAAAAAAAAAAAAAA",
    "aws.s3.secret_key" = "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
);
```

```SQL
DESCRIBE user_behavior_inferred;
```

```plaintext
Field       |Type            |Null|Key  |Default|Extra|
------------+----------------+----+-----+-------+-----+
UserID      |bigint          |YES |true |       |     |
ItemID      |bigint          |YES |true |       |     |
CategoryID  |bigint          |YES |true |       |     |
BehaviorType|varchar(1048576)|YES |false|       |     |
Timestamp   |varchar(1048576)|YES |false|       |     |
```

> **NOTE**
>
> 将推断的 schema 与手动创建的 schema 进行比较：
>
> - 数据类型
> - 可为空
> - 键字段

```SQL
SELECT * from user_behavior_inferred LIMIT 10;
```

```plaintext
UserID|ItemID|CategoryID|BehaviorType|Timestamp          |
------+------+----------+------------+-------------------+
171146| 68873|   3002561|pv          |2017-11-30 07:11:14|
171146|146539|   4672807|pv          |2017-11-27 09:51:41|
171146|146539|   4672807|pv          |2017-11-27 14:08:33|
171146|214198|   1320293|pv          |2017-11-25 22:38:27|
171146|260659|   4756105|pv          |2017-11-30 05:11:25|
171146|267617|   4565874|pv          |2017-11-27 14:01:25|
171146|329115|   2858794|pv          |2017-12-01 02:10:51|
171146|458604|   1349561|pv          |2017-11-25 22:49:39|
171146|458604|   1349561|pv          |2017-11-27 14:03:44|
171146|478802|    541347|pv          |2017-12-02 04:52:39|
```

#### 加载到现有表

您可能想要自定义要插入的表，例如：

- 列数据类型、可为空设置或默认值
- 键类型和列
- 分布
- 等等。

> **NOTE**
>
> 创建最有效的表结构需要了解数据的使用方式和列的内容。本文档不涵盖表设计，在页面末尾的**更多信息**中有一个链接。

在此示例中，我们基于对表查询方式和 Parquet 文件中数据的了解来创建表。可以通过直接在 S3 中查询文件来获得对 Parquet 文件中数据的了解。

- 由于 S3 中文件的查询表明 `Timestamp` 列包含与 `datetime` 数据类型匹配的数据，因此在以下 DDL 中指定了列类型。
- 通过查询 S3 中的数据，您可以发现数据集中没有空值，因此 DDL 不会将任何列设置为可为空。
- 根据对预期查询类型的了解，排序键和分桶列设置为列 `UserID`（您的用例可能对此数据有所不同，您可能会决定除了 `UserID` 之外或代替 `UserID` 使用 `ItemID` 作为排序键：

```SQL
CREATE TABLE `user_behavior_declared` (
    `UserID` int(11),
    `ItemID` int(11),
    `CategoryID` int(11),
    `BehaviorType` varchar(65533),
    `Timestamp` datetime
) ENGINE=OLAP 
DUPLICATE KEY(`UserID`)
DISTRIBUTED BY HASH(`UserID`)
PROPERTIES (
    "replication_num" = "1"
);
```

创建表后，您可以使用 `INSERT INTO` … `SELECT FROM FILES()` 加载它：

```SQL
INSERT INTO user_behavior_declared
  SELECT * FROM FILES(
    "path" = "s3://starrocks-examples/user_behavior_sample_data.parquet",
    "format" = "parquet",
    "aws.s3.region" = "us-east-1",
    "aws.s3.access_key" = "AAAAAAAAAAAAAAAAAAAA",
    "aws.s3.secret_key" = "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
);
```

## 更多信息

- 有关同步和异步数据加载的更多详细信息，请参见 [加载概念](./loading_introduction/loading_concepts.md)。
- 了解 Broker Load 如何在加载期间支持数据转换，请参见 [加载时转换数据](../loading/Etl_in_loading.md) 和 [通过加载更改数据](../loading/Load_to_Primary_Key_tables.md)。
- 本文档仅涵盖基于 IAM 用户的身份验证。有关其他选项，请参见 [验证到 AWS 资源的身份](../integrations/authenticate_to_aws_resources.md)。
- [AWS CLI 命令参考](https://awscli.amazonaws.com/v2/documentation/api/latest/reference/s3/index.html) 详细介绍了 S3 URI。
- 了解有关 [表设计](../table_design/StarRocks_table_design.md) 的更多信息。
- Broker Load 提供了比上述示例更多的配置和使用选项，详细信息请参见 [Broker Load](../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md)