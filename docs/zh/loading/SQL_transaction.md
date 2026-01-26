---
displayed_sidebar: docs
---

import Beta from '../_assets/commonMarkdown/_beta.mdx'

# SQL 事务

<Beta />

启动一个简单的 SQL 事务，以批量提交多个 DML 语句。

## 概述

自 v3.5.0 起，StarRocks 支持 SQL 事务，以确保在多个表中操作数据时，更新表的原子性。

事务由在同一原子单元中处理的多个 SQL 语句组成。 事务中的语句要么一起应用，要么一起撤消，从而保证了事务的 ACID（原子性、一致性、隔离性和持久性）属性。

目前，StarRocks 中的 SQL 事务支持以下操作：
- INSERT INTO
- UPDATE
- DELETE

:::note

- 目前不支持 INSERT OVERWRITE。
- 从 v4.0 开始，只有在存算分离集群中才支持在事务中对同一表执行多个 INSERT 语句。
- 从 v4.0 开始，只有在存算分离集群中才支持 UPDATE 和 DELETE。

:::

从 v4.0 开始，在一个 SQL 事务中：
- 支持对一个表执行**多个 INSERT 语句**。
- 允许对一个表执行**仅一个 UPDATE *或* DELETE** 语句。
- **不允许**在对同一表执行 INSERT 语句**之后**执行 **UPDATE *或* DELETE** 语句。

事务的 ACID 属性仅在有限的 READ COMMITTED 隔离级别上得到保证，即：
- 语句仅对在该语句开始之前已提交的数据进行操作。
- 如果在第一个语句和第二个语句的执行之间提交了另一个事务，则同一事务中的两个连续语句可以对不同的数据进行操作。
- 前面的 DML 语句带来的数据更改对于同一事务中的后续语句是不可见的。

一个事务与一个会话相关联。 多个会话不能共享同一个事务。

## 用法

1. 必须通过执行 START TRANSACTION 语句来启动事务。 StarRocks 还支持同义词 BEGIN。

   ```SQL
   { START TRANSACTION | BEGIN [ WORK ] }
   ```

2. 启动事务后，您可以在事务中定义多个 DML 语句。 有关详细信息，请参见 [使用说明](#usage-notes)。

3. 必须通过执行 `COMMIT` 或 `ROLLBACK` 显式结束事务。

   - 要应用（提交）事务，请使用以下语法：

     ```SQL
     COMMIT [ WORK ]
     ```

   - 要撤消（回滚）事务，请使用以下语法：

     ```SQL
     ROLLBACK [ WORK ]
     ```

## 示例

1. 在存算分离集群中创建演示表 `desT`，并将数据加载到其中。

    :::note
    如果您想在存算一体集群中尝试此示例，则必须跳过步骤 3，并且在步骤 4 中仅定义一个 INSERT 语句。
    :::

    ```SQL
    CREATE TABLE desT (
        k int,
        v int
    ) PRIMARY KEY(k);

    INSERT INTO desT VALUES
    (1,1),
    (2,2),
    (3,3);
    ```

2. 启动一个事务。

    ```SQL
    START TRANSACTION;
    ```

    或者

    ```SQL
    BEGIN WORK;
    ```

3. 定义一个 UPDATE 或 DELETE 语句。

    ```SQL
    UPDATE desT SET v = v + 1 WHERE k = 1,
    ```

    或者

    ```SQL
    DELETE FROM desT WHERE k = 1;
    ```

4. 定义多个 INSERT 语句。

    ```SQL
    -- 插入具有指定值的数据。
    INSERT INTO desT VALUES (4,4);
    -- 将数据从内表插入到另一个内表。
    INSERT INTO desT SELECT * FROM srcT;
    -- 从远端存储插入数据。
    INSERT INTO desT
        SELECT * FROM FILES(
            "path" = "s3://inserttest/parquet/srcT.parquet",
            "format" = "parquet",
            "aws.s3.access_key" = "XXXXXXXXXX",
            "aws.s3.secret_key" = "YYYYYYYYYY",
            "aws.s3.region" = "us-west-2"
    );
    ```

5. 应用或撤消事务。

    - 要应用事务中的 SQL 语句。

      ```SQL
      COMMIT WORK;
      ```

    - 要撤消事务中的 SQL 语句。

      ```SQL
      ROLLBACK WORK;
      ```

## 使用说明

- 目前，StarRocks 在 SQL 事务中支持 SELECT、INSERT、UPDATE 和 DELETE 语句。 从 v4.0 开始，只有在存算分离集群中才支持 UPDATE 和 DELETE。
- 不允许对在同一事务中数据已更改的表执行 SELECT 语句。
- 从 v4.0 开始，只有在存算分离集群中才支持在事务中对同一表执行多个 INSERT 语句。
- 在一个事务中，您只能对每个表定义一个 UPDATE 或 DELETE 语句，并且它必须位于 INSERT 语句之前。
- 后续 DML 语句无法读取同一事务中前面的语句带来的未提交更改。 例如，前面的 INSERT 语句的目标表不能是后续语句的源表。 否则，系统将返回错误。
- 事务中 DML 语句的所有目标表必须位于同一数据库中。 不允许跨数据库操作。
- 目前，不支持 INSERT OVERWRITE。
- 不允许嵌套事务。 您不能在 BEGIN-COMMIT/ROLLBACK 对中指定 BEGIN WORK。
- 如果正在进行的事务所属的会话终止或关闭，则该事务将自动回滚。
- 如上所述，StarRock 仅支持事务隔离级别的有限 READ COMMITTED。
- 不支持写入冲突检查。 当两个事务同时写入同一表时，两个事务都可以成功提交。 数据更改的可见性（顺序）取决于 COMMIT WORK 语句的执行顺序。