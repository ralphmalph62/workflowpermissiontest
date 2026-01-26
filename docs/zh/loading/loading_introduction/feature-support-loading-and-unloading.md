---
displayed_sidebar: docs
sidebar_label: "Feature Support"
---

# 功能支持：数据导入和导出

本文档概述了 StarRocks 支持的各种数据导入和导出方法的功能。

## 文件格式

### 导入文件格式

<table align="center">
    <tr>
        <th rowspan="2"></th>
        <th rowspan="2">Data Source</th>
        <th colspan="7">File Format</th>
    </tr>
    <tr>
        <th>CSV</th>
        <th>JSON [3]</th>
        <th>Parquet</th>
        <th>ORC</th>
        <th>Avro</th>
        <th>ProtoBuf</th>
        <th>Thrift</th>
    </tr>
    <tr>
        <td>Stream Load</td>
        <td>Local file systems, applications, connectors</td>
        <td>Yes</td>
        <td>Yes</td>
        <td>To be supported</td>
        <td>To be supported</td>
        <td colspan="3">To be supported</td>
    </tr>
    <tr>
        <td>INSERT from FILES</td>
        <td rowspan="2">HDFS, S3, OSS, Azure, GCS, NFS(NAS) [5]</td>
        <td>Yes (v3.3+)</td>
        <td>To be supported</td>
        <td>Yes (v3.1+)</td>
        <td>Yes (v3.1+)</td>
        <td>Yes (v3.4.4+)</td>
        <td colspan="2">To be supported</td>
    </tr>
    <tr>
        <td>Broker Load</td>
        <td>Yes</td>
        <td>Yes (v3.2.3+)</td>
        <td>Yes</td>
        <td>Yes</td>
        <td colspan="3">To be supported</td>
    </tr>
    <tr>
        <td>Routine Load</td>
        <td>Kafka</td>
        <td>Yes</td>
        <td>Yes</td>
        <td>To be supported</td>
        <td>To be supported</td>
        <td>Yes (v3.0+) [1]</td>
        <td>To be supported</td>
        <td>To be supported</td>
    </tr>
    <tr>
        <td>Spark Load</td>
        <td></td>
        <td>Yes</td>
        <td>To be supported</td>
        <td>Yes</td>
        <td>Yes</td>
        <td colspan="3">To be supported</td>
    </tr>
    <tr>
        <td>Connectors</td>
        <td>Flink, Spark</td>
        <td>Yes</td>
        <td>Yes</td>
        <td>To be supported</td>
        <td>To be supported</td>
        <td colspan="3">To be supported</td>
    </tr>
    <tr>
        <td>Kafka Connector [2]</td>
        <td>Kafka</td>
        <td colspan="2">Yes (v3.0+)</td>
        <td>To be supported</td>
        <td>To be supported</td>
        <td colspan="2">Yes (v3.0+)</td>
        <td>To be supported</td>
    </tr>
    <tr>
        <td>PIPE [4]</td>
        <td colspan="8">Consistent with INSERT from FILES</td>
    </tr>
</table>

:::note

[1], [2]\: Schema Registry is required.

[3]\: JSON 支持多种 CDC 格式。有关 StarRocks 支持的 JSON CDC 格式的详细信息，请参见 [JSON CDC format](#json-cdc-formats)。

[4]\: 目前，仅 INSERT from FILES 支持使用 PIPE 进行导入。

[5]\: 您需要将 NAS 设备作为 NFS 挂载在每个 BE 或 CN 节点的相同目录下，才能通过 `file://` 协议访问 NFS 中的文件。

:::

#### JSON CDC formats

<table align="center">
    <tr>
        <th></th>
        <th>Stream Load</th>
        <th>Routine Load</th>
        <th>Broker Load</th>
        <th>INSERT from FILES</th>
        <th>Kafka Connector [1]</th>
    </tr>
    <tr>
        <td>Debezium</td>
        <td>To be supported</td>
        <td>To be supported</td>
        <td>To be supported</td>
        <td>To be supported</td>
        <td>Yes (v3.0+)</td>
    </tr>
    <tr>
        <td>Canal</td>
        <td colspan="5" rowspan="2">To be supported</td>
    </tr>
    <tr>
        <td>Maxwell</td>
    </tr>
</table>

:::note

[1]\: 将 Debezium CDC 格式数据导入到 StarRocks 的主键表时，必须配置 `transforms` 参数。

:::

### 导出文件格式

<table align="center">
    <tr>
        <th rowspan="2"></th>
        <th colspan="2">Target</th>
        <th colspan="4">File format</th>
    </tr>
    <tr>
        <th>Table format</th>
        <th>Remote storage</th>
        <th>CSV</th>
        <th>JSON</th>
        <th>Parquet</th>
        <th>ORC</th>
    </tr>
    <tr>
        <td>INSERT INTO FILES</td>
        <td>N/A</td>
        <td>HDFS, S3, OSS, Azure, GCS, NFS(NAS) [3]</td>
        <td>Yes (v3.3+)</td>
        <td>To be supported</td>
        <td>Yes (v3.2+)</td>
        <td>Yes (v3.3+)</td>
    </tr>
    <tr>
        <td rowspan="3">INSERT INTO Catalog</td>
        <td>Hive</td>
        <td>HDFS, S3, OSS, Azure, GCS</td>
        <td>Yes (v3.3+)</td>
        <td>To be supported</td>
        <td>Yes (v3.2+)</td>
        <td>Yes (v3.3+)</td>
    </tr>
    <tr>
        <td>Iceberg</td>
        <td>HDFS, S3, OSS, Azure, GCS</td>
        <td>To be supported</td>
        <td>To be supported</td>
        <td>Yes (v3.2+)</td>
        <td>To be supported</td>
    </tr>
    <tr>
        <td>Hudi/Delta</td>
        <td></td>
        <td colspan="4">To be supported</td>
    </tr>
    <tr>
        <td>EXPORT</td>
        <td>N/A</td>
        <td>HDFS, S3, OSS, Azure, GCS</td>
        <td>Yes [1]</td>
        <td>To be supported</td>
        <td>To be supported</td>
        <td>To be supported</td>
    </tr>
    <tr>
        <td>PIPE</td>
        <td colspan="6">To be supported [2]</td>
    </tr>
</table>

:::note

[1]\: Configuring Broker process is supported.

[2]\: Currently, unloading data using PIPE is not supported.

[3]\: 您需要将 NAS 设备作为 NFS 挂载在每个 BE 或 CN 节点的相同目录下，才能通过 `file://` 协议访问 NFS 中的文件。

:::

## 文件格式相关参数

### 导入文件格式相关参数

<table align="center">
    <tr>
        <th rowspan="2">File format</th>
        <th rowspan="2">Parameter</th>
        <th colspan="5">Loading method</th>
    </tr>
    <tr>
        <th>Stream Load</th>
        <th>INSERT from FILES</th>
        <th>Broker Load</th>
        <th>Routine Load</th>
        <th>Spark Load</th>
    </tr>
    <tr>
        <td rowspan="6">CSV</td>
        <td>column_separator</td>
        <td>Yes</td>
        <td rowspan="6">Yes (v3.3+)</td>
        <td colspan="3">Yes [1]</td>
    </tr>
    <tr>
        <td>row_delimiter</td>
        <td>Yes</td>
        <td>Yes [2] (v3.1+)</td>
        <td>Yes [3] (v2.2+)</td>
        <td>To be supported</td>
    </tr>
    <tr>
        <td>enclose</td>
        <td rowspan="4">Yes (v3.0+)</td>
        <td rowspan="4">Yes (v3.0+)</td>
        <td rowspan="2">Yes (v3.0+)</td>
        <td rowspan="4">To be supported</td>
    </tr>
    <tr>
        <td>escape</td>
    </tr>
    <tr>
        <td>skip_header</td>
        <td>To be supported</td>
    </tr>
    <tr>
        <td>trim_space</td>
        <td>Yes (v3.0+)</td>
    </tr>
    <tr>
        <td rowspan="4">JSON</td>
        <td>jsonpaths</td>
        <td rowspan="4">Yes</td>
        <td rowspan="4">To be supported</td>
        <td rowspan="4">Yes (v3.2.3+)</td>
        <td rowspan="3">Yes</td>
        <td rowspan="4">To be supported</td>
    </tr>
    <tr>
        <td>strip_outer_array</td>
    </tr>
    <tr>
        <td>json_root</td>
    </tr>
    <tr>
        <td>ignore_json_size</td>
        <td>To be supported</td>
    </tr>
</table>

:::note

[1]\: 对应的参数是 `COLUMNS TERMINATED BY`。

[2]\: 对应的参数是 `ROWS TERMINATED BY`。

[3]\: 对应的参数是 `ROWS TERMINATED BY`。

:::

### 导出文件格式相关参数

<table align="center">
    <tr>
        <th rowspan="2">File format</th>
        <th rowspan="2">Parameter</th>
        <th colspan="2">Unloading method</th>
    </tr>
    <tr>
        <th>INSERT INTO FILES</th>
        <th>EXPORT</th>
    </tr>
    <tr>
        <td rowspan="2">CSV</td>
        <td>column_separator</td>
        <td rowspan="2">Yes (v3.3+)</td>
        <td rowspan="2">Yes</td>
    </tr>
    <tr>
        <td>line_delimiter [1]</td>
    </tr>
</table>

:::note

[1]\: 数据导入中对应的参数是 `row_delimiter`。

:::

## 压缩格式

### 导入压缩格式

<table align="center">
    <tr>
        <th rowspan="2">File format</th>
        <th rowspan="2">Compression format</th>
        <th colspan="5">Loading method</th>
    </tr>
    <tr>
        <th>Stream Load</th>
        <th>Broker Load</th>
        <th>INSERT from FILES</th>
        <th>Routine Load</th>
        <th>Spark Load</th>
    </tr>
    <tr>
        <td>CSV</td>
        <td rowspan="2">
            <ul>
                <li>deflate</li>
                <li>bzip2</li>
                <li>gzip</li>
                <li>lz4_frame</li>
                <li>zstd</li>
            </ul>
        </td>
        <td>Yes [1]</td>
        <td>Yes [2]</td>
        <td>To be supported</td>
        <td>To be supported</td>
        <td>To be supported</td>
    </tr>
    <tr>
        <td>JSON</td>
        <td>Yes (v3.2.7+) [3]</td>
        <td>To be supported</td>
        <td>N/A</td>
        <td>To be supported</td>
        <td>N/A</td>
    </tr>
    <tr>
        <td>Parquet</td>
        <td rowspan="2">
            <ul>
                <li>gzip</li>
                <li>lz4</li>
                <li>snappy</li>
                <li>zlib</li>
                <li>zstd</li>
            </ul>
        </td>
        <td rowspan="2">N/A</td>
        <td rowspan="2" colspan="2">Yes [4]</td>
        <td rowspan="2">To be supported</td>
        <td rowspan="2">Yes [4]</td>
    </tr>
    <tr>
        <td>ORC</td>
    </tr>
</table>

:::note

[1]\: 目前，仅当使用 Stream Load 导入 CSV 文件时，才能使用 `format=gzip` 指定压缩格式，表示 gzip 压缩的 CSV 文件。`deflate` 和 `bzip2` 格式也支持。

[2]\: Broker Load 不支持使用参数 `format` 指定 CSV 文件的压缩格式。Broker Load 通过文件的后缀名来识别压缩格式。gzip 压缩文件的后缀名为 `.gz`，zstd 压缩文件的后缀名为 `.zst`。此外，不支持其他与 `format` 相关的参数，例如 `trim_space` 和 `enclose`。

[3]\: 支持使用 `compression = gzip` 指定压缩格式。

[4]\: 由 Arrow Library 支持。您无需配置 `compression` 参数。

:::

### 导出压缩格式

<table align="center">
    <tr>
        <th rowspan="3">File format</th>
        <th rowspan="3">Compression format</th>
        <th colspan="5">Unloading method</th>
    </tr>
    <tr>
        <th rowspan="2">INSERT INTO FILES</th>
        <th colspan="3">INSERT INTO Catalog</th>
        <th rowspan="2">EXPORT</th>
    </tr>
    <tr>
        <td>Hive</td>
        <td>Iceberg</td>
        <td>Hudi/Delta</td>
    </tr>
    <tr>
        <td>CSV</td>
        <td>
            <ul>
                <li>deflate</li>
                <li>bzip2</li>
                <li>gzip</li>
                <li>lz4_frame</li>
                <li>zstd</li>
            </ul>
        </td>
        <td>To be supported</td>
        <td>To be supported</td>
        <td>To be supported</td>
        <td>To be supported</td>
        <td>To be supported</td>
    </tr>
    <tr>
        <td>JSON</td>
        <td>N/A</td>
        <td>N/A</td>
        <td>N/A</td>
        <td>N/A</td>
        <td>N/A</td>
        <td>N/A</td>
    </tr>
    <tr>
        <td>Parquet</td>
        <td rowspan="2">
            <ul>
                <li>gzip</li>
                <li>lz4</li>
                <li>snappy</li>
                <li>zstd</li>
            </ul>
        </td>
        <td rowspan="2">Yes (v3.2+)</td>
        <td rowspan="2">Yes (v3.2+)</td>
        <td rowspan="2">Yes (v3.2+)</td>
        <td rowspan="2">To be supported</td>
        <td rowspan="2">N/A</td>
    </tr>
    <tr>
        <td>ORC</td>
    </tr>
</table>

## 凭据

### 导入 - 身份验证

<table align="center">
    <tr>
        <th rowspan="2">Authentication</th>
        <th colspan="5">Loading method</th>
    </tr>
    <tr>
        <th>Stream Load</th>
        <th>INSERT from FILES</th>
        <th>Broker Load</th>
        <th>Routine Load</th>
        <th>External Catalog</th>
    </tr>
    <tr>
        <td>Single Kerberos</td>
        <td>N/A</td>
        <td>Yes (v3.1+)</td>
        <td>Yes [1] (versions earlier than v2.5)</td>
        <td>Yes [2] (v3.1.4+)</td>
        <td>Yes</td>
    </tr>
    <tr>
        <td>Kerberos Ticket Granting Ticket (TGT)</td>
        <td>N/A</td>
        <td rowspan="2" colspan="3">To be supported</td>
        <td rowspan="2">Yes (v3.1.10+/v3.2.1+)</td>
    </tr>
    <tr>
        <td>Single KDC Multiple Kerberos</td>
        <td>N/A</td>
    </tr>
    <tr>
        <td>Basic access authentications (Access Key pair, IAM Role)</td>
        <td>N/A</td>
        <td colspan="2">Yes (HDFS and S3-compatible object storage)</td>
        <td>Yes [3]</td>
        <td>Yes</td>
    </tr>
</table>

:::note

[1]\: 对于 HDFS，StarRocks 支持简单身份验证和 Kerberos 身份验证。

[2]\: 当安全协议设置为 `sasl_plaintext` 或 `sasl_ssl` 时，支持 SASL 和 GSSAPI (Kerberos) 身份验证。

[3]\: 当安全协议设置为 `sasl_plaintext` 或 `sasl_ssl` 时，支持 SASL 和 PLAIN 身份验证。

:::

### 导出 - 身份验证

|                 | INSERT INTO FILES  | EXPORT          |
| :-------------- | :----------------: | :-------------: |
| Single Kerberos | To be supported    | To be supported |

## 导入 - 其他参数和功能

<table align="center">
    <tr>
        <th rowspan="2">Parameter and feature</th>
        <th colspan="8">Loading method</th>
    </tr>
    <tr>
        <th>Stream Load</th>
        <th>INSERT from FILES</th>
        <th>INSERT from SELECT/VALUES</th>
        <th>Broker Load</th>
        <th>PIPE</th>
        <th>Routine Load</th>
        <th>Spark Load</th>
    </tr>
    <tr>
        <td>partial_update</td>
        <td>Yes (v3.0+)</td>
        <td colspan="2">Yes [1] (v3.3+)</td>
        <td>Yes (v3.0+)</td>
        <td>N/A</td>
        <td>Yes (v3.0+)</td>
        <td>To be supported</td>
    </tr>
    <tr>
        <td>partial_update_mode</td>
        <td>Yes (v3.1+)</td>
        <td colspan="2">To be supported</td>
        <td>Yes (v3.1+)</td>
        <td>N/A</td>
        <td>To be supported</td>
        <td>To be supported</td>
    </tr>
    <tr>
        <td>COLUMNS FROM PATH</td>
        <td>N/A</td>
        <td>Yes (v3.2+)</td>
        <td>N/A</td>
        <td>Yes</td>
        <td>N/A</td>
        <td>N/A</td>
        <td>Yes</td>
    </tr>
    <tr>
        <td>timezone or session variable time_zone [2]</td>
        <td>Yes [3]</td>
        <td>Yes [4]</td>
        <td>Yes [4]</td>
        <td>Yes [4]</td>
        <td>To be supported</td>
        <td>Yes [4]</td>
        <td>To be supported</td>
    </tr>
    <tr>
        <td>Time accuracy - Microsecond</td>
        <td>Yes</td>
        <td>Yes</td>
        <td>Yes</td>
        <td>Yes (v3.1.11+/v3.2.6+)</td>
        <td>To be supported</td>
        <td>Yes</td>
        <td>Yes</td>
    </tr>
</table>

:::note

[1]\: 从 v3.3 开始，StarRocks 支持在行模式下通过指定列列表对 INSERT INTO 进行部分更新。

[2]\: 通过参数或会话变量设置时区会影响 strftime()、alignment_timestamp() 和 from_unixtime() 等函数返回的结果。

[3]\: 仅支持参数 `timezone`。

[4]\: 仅支持会话变量 `time_zone`。

:::

## 导出 - 其他参数和功能

<table align="center">
    <tr>
        <th>Parameter and feature</th>
        <th>INSERT INTO FILES</th>
        <th>EXPORT</th>
    </tr>
    <tr>
        <td>target_max_file_size</td>
        <td rowspan="3">Yes (v3.2+)</td>
        <td rowspan="4">To be supported</td>
    </tr>
    <tr>
        <td>single</td>
    </tr>
    <tr>
        <td>Partitioned_by</td>
    </tr>
    <tr>
        <td>Session variable time_zone</td>
        <td>To be supported</td>
    </tr>
    <tr>
        <td>Time accuracy - Microsecond</td>
        <td>To be supported</td>
        <td>To be supported</td>
    </tr>
</table>