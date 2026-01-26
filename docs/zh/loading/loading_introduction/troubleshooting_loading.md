---
displayed_sidebar: docs
sidebar_label: "Troubleshooting"
---

# 数据导入问题排查

本文档旨在帮助DBA和运维工程师通过SQL界面监控数据导入作业的状态，而无需依赖外部监控系统。同时，本文档还提供了在导入操作期间识别性能瓶颈和排除异常情况的指导。

## 术语

**导入作业 (Load Job):** 连续的数据导入过程，例如 **Routine Load Job** 或 **Pipe Job**。

**导入任务 (Load Task):** 一次性的数据导入过程，通常对应于单个导入事务。例如 **Broker Load**、**Stream Load**、**Spark Load** 和 **INSERT INTO**。Routine Load 作业和 Pipe 作业会持续生成任务以执行数据摄取。

## 观察导入作业

有两种方法可以观察导入作业：

- 使用 SQL 语句 **[SHOW ROUTINE LOAD](../../sql-reference/sql-statements/loading_unloading/routine_load/SHOW_ROUTINE_LOAD.md)** 和 **[SHOW PIPES](../../sql-reference/sql-statements/loading_unloading/pipe/SHOW_PIPES.md)**。
- 使用系统视图 **[information_schema.routine_load_jobs](../../sql-reference/information_schema/routine_load_jobs.md)** 和 **[information_schema.pipes](../../sql-reference/information_schema/pipes.md)**。

## 观察导入任务

也可以通过两种方式监控导入任务：

- 使用 SQL 语句 **[SHOW LOAD](../../sql-reference/sql-statements/loading_unloading/SHOW_LOAD.md)** 和 **[SHOW ROUTINE LOAD TASK](../../sql-reference/sql-statements/loading_unloading/routine_load/SHOW_ROUTINE_LOAD_TASK.md)**。
- 使用系统视图 **[information_schema.loads](../../sql-reference/information_schema/loads.md)** 和 statistics.loads_history。

### SQL 语句

**SHOW** 语句显示当前数据库正在进行和最近完成的导入任务，从而快速了解任务状态。检索到的信息是 **statistics.loads_history** 系统视图的子集。

SHOW LOAD 语句返回 Broker Load、Insert Into 和 Spark Load 任务的信息，SHOW ROUTINE LOAD TASK 语句返回 Routine Load 任务的信息。

### 系统视图

#### information_schema.loads

**information_schema.loads** 系统视图存储最近的导入任务的信息，包括正在进行和最近完成的任务。StarRocks 定期将数据同步到 **statistics.loads_history** 系统表以进行持久存储。

**information_schema.loads** 提供以下字段：

| 字段 (Field)         | 描述 (Description)