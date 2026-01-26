### 注意事项

本文档介绍在运行数据导入作业之前需要考虑的一些系统限制和配置。

## 内存限制

StarRocks 提供了参数来限制每个导入作业的内存使用量，从而减少内存消耗，尤其是在高并发场景下。但是，不要指定过低的内存使用量限制。如果内存使用量限制过低，则可能因为导入作业的内存使用量达到指定限制，导致数据频繁地从内存刷新到磁盘。建议您根据您的业务场景指定合适的内存使用量限制。

用于限制内存使用量的参数因每种导入方式而异。更多信息，请参见 [Stream Load](../../sql-reference/sql-statements/loading_unloading/STREAM_LOAD.md)、[Broker Load](../../sql-reference/sql-statements/loading_unloading/BROKER_LOAD.md)、[Routine Load](../../sql-reference/sql-statements/loading_unloading/routine_load/CREATE_ROUTINE_LOAD.md)、[Spark Load](../../sql-reference/sql-statements/loading_unloading/SPARK_LOAD.md) 和 [INSERT](../../sql-reference/sql-statements/loading_unloading/INSERT.md)。请注意，一个导入作业通常在多个 BE 或 CN 上运行。因此，这些参数限制的是每个导入作业在每个涉及的 BE 或 CN 上的内存使用量，而不是导入作业在所有涉及的 BE 或 CN 上的总内存使用量。

StarRocks 还提供了参数来限制每个 BE 或 CN 上运行的所有导入作业的总内存使用量。更多信息，请参见下面的“[系统配置](#system-configurations)”部分。

## 系统配置

本节介绍一些适用于 StarRocks 提供的所有导入方法的参数配置。

### FE 配置

您可以在每个 FE 的配置文件 **fe.conf** 中配置以下参数：

- `max_load_timeout_second` 和 `min_load_timeout_second`
  
  这些参数指定每个导入作业的最大超时时间和最小超时时间。超时时间以秒为单位。默认的最大超时时间为 3 天，默认的最小超时时间为 1 秒。您指定的最大超时时间和最小超时时间必须在 1 秒到 3 天的范围内。这些参数对同步导入作业和异步导入作业都有效。

- `desired_max_waiting_jobs`
  
  此参数指定队列中可以等待的最大导入作业数。默认值为 **1024**（v2.4 及更早版本中为 100，v2.5 及更高版本中为 1024）。当 FE 上处于 **PENDING** 状态的导入作业数达到您指定的最大数量时，FE 将拒绝新的导入请求。此参数仅对异步导入作业有效。

- `max_running_txn_num_per_db`
  
  此参数指定您的 StarRocks 集群的每个数据库中允许的最大并发导入事务数。一个导入作业可以包含一个或多个事务。默认值为 **100**。当数据库中运行的导入事务数达到您指定的最大数量时，您提交的后续导入作业将不会被调度。在这种情况下，如果您提交的是同步导入作业，则该作业将被拒绝。如果您提交的是异步导入作业，则该作业将在队列中等待。

  :::note
  
  StarRocks 将所有导入作业一起计数，不区分同步导入作业和异步导入作业。

  :::

- `label_keep_max_second`
  
  此参数指定已完成且处于 **FINISHED** 或 **CANCELLED** 状态的导入作业的历史记录的保留期限。默认保留期限为 3 天。此参数对同步导入作业和异步导入作业都有效。

### BE/CN 配置

您可以在每个 BE 的配置文件 **be.conf** 或每个 CN 的配置文件 **cn.conf** 中配置以下参数：

- `write_buffer_size`
  
  此参数指定最大内存块大小。默认大小为 100 MB。导入的数据首先写入 BE 或 CN 上的内存块。当导入的数据量达到您指定的最大内存块大小时，数据将刷新到磁盘。您必须根据您的业务场景指定合适的内存块大小。

  - 如果最大内存块大小过小，则可能在 BE 或 CN 上生成大量小文件。在这种情况下，[查询性能] 会下降。您可以增加最大内存块大小以减少生成的文件数。
  - 如果最大内存块大小过大，则远程过程调用 (RPC) 可能会超时。在这种情况下，您可以根据您的业务需求调整此参数的值。

- `streaming_load_rpc_max_alive_time_sec`
  
  每个 Writer 进程的等待超时时间。默认值为 1200 秒。在数据导入过程中，StarRocks 启动一个 Writer 进程来接收数据并将数据写入每个 tablet。如果在您指定的等待超时时间内，Writer 进程没有收到任何数据，StarRocks 将停止该 Writer 进程。当您的 StarRocks 集群以低速处理数据时，Writer 进程可能在很长一段时间内没有收到下一批数据，因此报告“TabletWriter add batch with unknown id”错误。在这种情况下，您可以增加此参数的值。

- `load_process_max_memory_limit_bytes` 和 `load_process_max_memory_limit_percent`
  
  这些参数指定每个 BE 或 CN 上所有导入作业可以消耗的最大内存量。StarRocks 将这两个参数值中较小的内存消耗量确定为允许的最终内存消耗量。

  - `load_process_max_memory_limit_bytes`: 指定最大内存大小。默认最大内存大小为 100 GB。
  - `load_process_max_memory_limit_percent`: 指定最大内存使用率。默认值为 30%。此参数与 `mem_limit` 参数不同。`mem_limit` 参数指定您的 StarRocks 集群的总最大内存使用量，默认值为 90% x 90%。

    如果 BE 或 CN 所在的机器的内存容量为 M，则可以为导入作业消耗的最大内存量计算如下：`M x 90% x 90% x 30%`。

### 系统变量配置

您可以配置以下 [系统变量](../../sql-reference/System_variable.md)：

- `insert_timeout`

  INSERT 超时时间。单位：秒。取值范围：`1` 到 `259200`。默认值：`14400`。此变量将作用于当前连接中所有涉及 INSERT 作业的操作（例如，UPDATE、DELETE、CTAS、物化视图刷新、统计信息收集和 PIPE）。