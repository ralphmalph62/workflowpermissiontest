---
displayed_sidebar: docs
---

# 使用工具导入数据

StarRocks 及其生态系统合作伙伴提供以下工具，以帮助您将 StarRocks 与外部数据库无缝集成。

## [SMT](../integrations/loading_tools/SMT.md)

SMT (StarRocks Migration Tool) 是 StarRocks 提供的数据迁移工具，旨在优化复杂的数据导入管道：源数据库（如 MySQL、Oracle、PostgreSQL）---> Flink ---> 目标 StarRocks 集群。其主要功能如下：

- 简化 StarRocks 中的表创建：基于外部数据库和目标 StarRocks 集群的信息，生成在 StarRocks 中创建表的语句。
- 简化数据管道中的全量或增量数据同步过程：生成可在 Flink 的 SQL 客户端中运行的 SQL 语句，以提交 Flink 作业来同步数据。

下图说明了通过 Flink 将数据从源数据库 MySQL 导入到 StarRocks 的过程。

![img](../_assets/load_tools.png)

## [DataX](../integrations/loading_tools/DataX-starrocks-writer.md)

DataX 是一款离线数据同步工具，由阿里巴巴开源。 DataX 可以同步各种异构数据源之间的数据，包括关系数据库（MySQL、Oracle 等）、HDFS 和 Hive。 DataX 提供了 StarRocks Writer 插件，用于将 DataX 支持的数据源中的数据同步到 StarRocks。

## [CloudCanal](../integrations/loading_tools/CloudCanal.md)

CloudCanal 社区版是由 [ClouGence Co., Ltd](https://www.cloudcanalx.com/) 发布的免费数据迁移和同步平台，集成了 Schema Migration、全量数据迁移、验证、纠正和实时增量同步。 您可以直接在 CloudCanal 的可视化界面中添加 StarRocks 作为数据源，并创建任务以自动将数据从源数据库（例如，MySQL、Oracle、PostgreSQL）迁移或同步到 StarRocks。

## [Kettle connector](https://github.com/StarRocks/starrocks-connector-for-kettle)

Kettle 是一款具有可视化图形界面的 ETL (Extract, Transform, Load) 工具，允许用户通过拖动组件和配置参数来构建数据处理工作流程。 这种直观的方法大大简化了数据处理和导入的过程，使用户能够更方便地处理数据。 此外，Kettle 提供了丰富的组件库，允许用户根据需要选择合适的组件并执行各种复杂的数据处理任务。

StarRocks 提供 Kettle Connector 以与 Kettle 集成。 通过将 Kettle 强大的数据处理和转换能力与 StarRocks 的高性能数据存储和分析能力相结合，可以实现更灵活、更高效的数据处理工作流程。