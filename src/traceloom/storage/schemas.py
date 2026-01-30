# -*- coding: utf-8 -*-
"""数据结构定义模块。

定义用于存储径元数据的 PyArrow Schema 和字段名常量。
"""

import pyarrow as pa

# ----------------------------
# 1. 观测点数据 Schema (每个轨迹点关联的 pathlet_ids 和观测数据)
# ----------------------------
POINT_DATA_SCHEMA = pa.schema(
    [
        ("trace_name", pa.string()),  # 轨迹名称（分区键）
        ("trace_index", pa.int32()),  # 轨迹内索引（从0开始）
        ("pathlet_ids", pa.list_(pa.string())),  # 该点所属的 pathlet ID 列表
        ("delay_up", pa.float64()),  # 上行时延
        ("loss_up", pa.float64()),  # 上行丢包率
        ("bw_up", pa.float64()),  # 上行带宽
        ("delay_down", pa.float64()),  # 下行时延
        ("loss_down", pa.float64()),  # 下行丢包率
        ("bw_down", pa.float64()),  # 下行带宽
    ]
)


# 提取字段名常量（方便 pandas 操作）
class PointDataFields:
    TRACE_NAME = "trace_name"
    TRACE_INDEX = "trace_index"
    PATHLET_IDS = "pathlet_ids"
    DELAY_UP = "delay_up"
    LOSS_UP = "loss_up"
    BW_UP = "bw_up"
    DELAY_DOWN = "delay_down"
    LOSS_DOWN = "loss_down"
    BW_DOWN = "bw_down"


# ----------------------------
# 2. 径元元数据 Schema (每个 pathlet 的描述信息)
# ----------------------------
PATHLET_METADATA_SCHEMA = pa.schema(
    [
        ("pathlet_id", pa.string()),  # 径元唯一 ID
        ("state_id", pa.int32()),  # 状态 ID
        ("trace_name", pa.string()),  # 所属轨迹名
        ("start_index", pa.int32()),  # 在轨迹中的起始索引
        ("is_valid", pa.bool_()),  # 是否有效径元
        ("dataset", pa.string()),  # 数据集信息
    ]
)


class PathletMetadataFields:
    PATHLET_ID = "pathlet_id"
    STATE_ID = "state_id"
    TRACE_NAME = "trace_name"
    START_INDEX = "start_index"
    IS_VALID = "is_valid"
    DATASET = "dataset"
