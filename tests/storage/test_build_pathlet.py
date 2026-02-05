# -*- coding: utf-8 -*-
"""测试 PathletStorage._build_pathlet 方法"""


import pandas as pd

from traceloom.storage.pathlet_storage import PathletStorage
from traceloom.storage.schemas import PathletMetadataFields


def test_build_pathlet_without_observations():
    """测试当没有观测数据时，_build_pathlet 方法返回 None"""
    # 创建存储实例
    storage = PathletStorage()

    # 创建元数据行
    metadata_row = pd.Series({
        PathletMetadataFields.PATHLET_ID: "test_pathlet",
        PathletMetadataFields.START_INDEX: 0,
        PathletMetadataFields.TRACE_NAME: "test_trace",
        PathletMetadataFields.STATE_ID: -1,
        PathletMetadataFields.IS_VALID: True,
        PathletMetadataFields.DATASET: "train"
    })

    # 空的点数据
    pathlet_points = {}

    # 调用 _build_pathlet 方法
    pathlet = storage._build_pathlet(metadata_row, pathlet_points)

    # 验证返回 None
    assert pathlet is None


def test_build_pathlet_with_observations():
    """测试当有观测数据时，_build_pathlet 方法正确构建径元对象"""
    # 创建存储实例
    storage = PathletStorage()

    # 创建元数据行
    metadata_row = pd.Series({
        PathletMetadataFields.PATHLET_ID: "test_pathlet",
        PathletMetadataFields.START_INDEX: 0,
        PathletMetadataFields.TRACE_NAME: "test_trace",
        PathletMetadataFields.STATE_ID: -1,
        PathletMetadataFields.IS_VALID: True,
        PathletMetadataFields.DATASET: "train"
    })

    # 创建点数据
    point_row = pd.Series({
        "trace_index": 0,
        "pathlet_ids": ["test_pathlet"],
        "delay_up": 10.0,
        "loss_up": 0.0,
        "bw_up": 50.0,
        "delay_down": 8.0,
        "loss_down": 0.0,
        "bw_down": 100.0
    })

    pathlet_points = {
        "test_pathlet": [point_row]
    }

    # 调用 _build_pathlet 方法
    pathlet = storage._build_pathlet(metadata_row, pathlet_points)

    # 验证返回径元对象
    assert pathlet is not None
    assert pathlet.pathlet_id == "test_pathlet"
    assert pathlet.trace_name == "test_trace"
    assert pathlet.start_index == 0
    assert len(pathlet.body.observations) == 1
    assert len(pathlet.tail.observations) == 0


if __name__ == "__main__":
    # 运行测试
    test_build_pathlet_without_observations()
    print("✓ test_build_pathlet_without_observations 测试通过")

    test_build_pathlet_with_observations()
    print("✓ test_build_pathlet_with_observations 测试通过")

    print("所有测试通过！")
