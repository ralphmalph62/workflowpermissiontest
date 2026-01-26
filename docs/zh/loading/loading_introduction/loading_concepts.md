---
displayed_sidebar: docs
toc_max_heading_level: 4
---

# 数据导入概念

import InsertPrivNote from '../../_assets/commonMarkdown/insertPrivNote.mdx'

本文介绍数据导入相关的常用概念和信息。

## 权限

<InsertPrivNote />

## Label

您可以通过运行数据导入作业将数据导入到 StarRocks 中。每个数据导入作业都有一个唯一的 label。该 label 由用户指定或由 StarRocks 自动生成，用于标识该作业。每个 label 只能用于一个数据导入作业。数据导入作业完成后，其 label 不能用于任何其他数据导入作业。只有失败的数据导入作业的 label 才能被重复使用。

## 原子性

StarRocks 提供的所有数据导入方法都保证原子性。原子性是指一个数据导入作业中，所有符合条件的数据必须全部成功导入，或者全部不成功导入。不会出现部分符合条件的数据被导入，而其他数据没有被导入的情况。请注意，符合条件的数据不包括由于数据质量问题（如数据类型转换错误）而被过滤掉的数据。

## 协议

StarRocks 支持两种可用于提交数据导入作业的通信协议：MySQL 和 HTTP。在 StarRocks 支持的所有数据导入方法中，只有 Stream Load 使用 HTTP，而所有其他方法都使用 MySQL。

## 数据类型

StarRocks 支持导入所有数据类型的数据。您只需要注意一些特定数据类型导入的限制。更多信息，请参见 [数据类型](../../sql-reference/data-types/README.md)。

## 严格模式

严格模式是您可以为数据导入配置的可选属性。它会影响数据导入的行为和最终导入的数据。详情请参见 [严格模式](../load_concept/strict_mode.md)。

## 导入模式

StarRocks 支持两种数据导入模式：同步导入模式和异步导入模式。

:::note

如果您使用外部程序导入数据，您必须在选择数据导入方法之前，选择最适合您业务需求的导入模式。

:::

### 同步导入

在同步导入模式下，提交数据导入作业后，StarRocks 会同步运行该作业以导入数据，并在作业完成后返回作业结果。您可以根据作业结果检查作业是否成功。

StarRocks 提供了两种支持同步导入的数据导入方法：[Stream Load](../StreamLoad.md) 和 [INSERT](../InsertInto.md)。

同步导入的流程如下：

1. 创建一个数据导入作业。

2. 查看 StarRocks 返回的作业结果。

3. 根据作业结果检查作业是否成功。如果作业结果表明导入失败，您可以重试该作业。

### 异步导入

在异步导入模式下，提交数据导入作业后，StarRocks 会立即返回作业创建结果。

- 如果结果表明作业创建成功，StarRocks 会异步运行该作业。但这并不意味着数据已成功导入。您必须使用语句或命令来检查作业的状态。然后，您可以根据作业状态确定数据是否已成功导入。

- 如果结果表明作业创建失败，您可以根据失败信息确定是否需要重试该作业。

:::tip

您可以为表设置不同的写入仲裁，即在 StarRocks 确定数据导入任务成功之前，需要有多少个副本返回数据导入成功。您可以通过在 [CREATE TABLE](../../sql-reference/sql-statements/table_bucket_part_index/CREATE_TABLE.md) 时添加属性 `write_quorum` 来指定写入仲裁，或者使用 [ALTER TABLE](../../sql-reference/sql-statements/table_bucket_part_index/ALTER_TABLE.md) 将此属性添加到现有表中。

:::

StarRocks 提供了四种支持异步导入的数据导入方法：[Broker Load](../../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md)、[Pipe](../../sql-reference/sql-statements/loading_unloading/pipe/CREATE_PIPE.md)、[Routine Load](../../sql-reference/sql-statements/loading_unloading/routine_load/CREATE_ROUTINE_LOAD.md) 和 [Spark Load](../../sql-reference/sql-statements/loading_unloading/SPARK_LOAD.md)。

异步导入的流程如下：

1. 创建一个数据导入作业。

2. 查看 StarRocks 返回的作业创建结果，并确定作业是否成功创建。

   - 如果作业创建成功，请转到步骤 3。

   - 如果作业创建失败，请返回到步骤 1。

3. 使用语句或命令检查作业的状态，直到作业状态显示为 **FINISHED** 或 **CANCELLED**。

#### Broker Load 或 Spark Load 的工作流程

Broker Load 或 Spark Load 作业的工作流程包括五个阶段，如下图所示。

![Broker Load or Spark Load overflow](../../_assets/4.1-1.png)

工作流程描述如下：

1. **PENDING**

   作业在队列中等待 FE 调度。

2. **ETL**

   FE 预处理数据，包括数据清洗、分区、排序和聚合。

   只有 Spark Load 作业有 ETL 阶段。Broker Load 作业跳过此阶段。

3. **LOADING**

   FE 清洗和转换数据，然后将数据发送到 BE 或 CN。加载完所有数据后，数据在队列中等待生效。此时，作业的状态保持为 **LOADING**。

4. **FINISHED**

   当数据导入完成并且所有涉及的数据生效时，作业的状态变为 **FINISHED**。此时，可以查询数据。**FINISHED** 是最终作业状态。

5. **CANCELLED**

   在作业的状态变为 **FINISHED** 之前，您可以随时取消该作业。此外，如果发生数据导入错误，StarRocks 可以自动取消该作业。作业取消后，作业的状态变为 **CANCELLED**，并且在取消之前所做的所有数据更新都将被还原。**CANCELLED** 也是最终作业状态。

#### Pipe 的工作流程

Pipe 作业的工作流程描述如下：

1. 从 MySQL 客户端将作业提交到 FE。

2. FE 根据指定路径中存储的数据文件的数量或大小拆分数据文件，将作业分解为更小的顺序任务。任务进入队列，等待调度，创建后。

3. FE 从队列中获取任务，并调用 INSERT INTO SELECT FROM FILES 语句来执行每个任务。

4. 数据导入完成：

   - 如果在作业创建时为作业指定了 `"AUTO_INGEST" = "FALSE"`，则在加载完指定路径中存储的所有数据文件的数据后，作业将完成。

   - 如果在作业创建时为作业指定了 `"AUTO_INGEST" = "TRUE"`，则 FE 将继续监视数据文件的更改，并自动将数据文件中的新数据或更新数据加载到目标 StarRocks 表中。

#### Routine Load 的工作流程

Routine Load 作业的工作流程描述如下：

1. 从 MySQL 客户端将作业提交到 FE。

2. FE 将作业拆分为多个任务。每个任务都设计为从多个分区加载数据。

3. FE 将任务分发到指定的 BE 或 CN。

4. BE 或 CN 执行任务，并在完成任务后向 FE 报告。

5. FE 生成后续任务，重试失败的任务（如果有），或根据 BE 的报告暂停任务调度。