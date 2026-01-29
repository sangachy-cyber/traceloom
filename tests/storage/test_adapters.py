# -*- coding: utf-8 -*-
"""测试存储适配器功能

测试 PathletStorageAdapter 的数据去重和转换功能
"""

import pytest
import pandas as pd
from traceloom.domain.pathlet import Pathlet, BodyObservations, TailObservations, Observation
from traceloom.domain.raw_trace import RawTraceSegment
from traceloom.storage.adapters import PathletStorageAdapter


@pytest.fixture
def test_data():
    """创建测试数据"""
    # 创建观测数据
    observations = []
    for i in range(110):  # 100个上下文点 + 10个延续点
        obs = Observation(
            delay_up=10.0 + i * 0.1,
            loss_up=0.01 + i * 0.0001,
            bw_up=50.0 - i * 0.05,
            delay_down=8.0 + i * 0.08,
            loss_down=0.005 + i * 0.00005,
            bw_down=100.0 - i * 0.1
        )
        observations.append(obs)
    
    # 创建 RawTraceSegment
    segment1 = RawTraceSegment(
        trace_name="test_trace",
        start_index=0,
        observations=observations
    )
    
    # 创建重叠的 RawTraceSegment（从索引10开始）
    # 创建新的观测数据，确保有一些不重叠的部分
    observations2 = []
    for i in range(110):  # 110个点
        obs = Observation(
            delay_up=20.0 + i * 0.1,
            loss_up=0.02 + i * 0.0001,
            bw_up=40.0 - i * 0.05,
            delay_down=16.0 + i * 0.08,
            loss_down=0.01 + i * 0.00005,
            bw_down=80.0 - i * 0.1
        )
        observations2.append(obs)
    
    segment2 = RawTraceSegment(
        trace_name="test_trace",
        start_index=10,
        observations=observations2  # 110个点，与segment1部分重叠
    )
    
    # 创建 Pathlet 对象
    pathlet1 = Pathlet(
        pathlet_id="pathlet_001",
        body=BodyObservations(),
        tail=TailObservations()
    )
    
    pathlet2 = Pathlet(
        pathlet_id="pathlet_002",
        body=BodyObservations(),
        tail=TailObservations()
    )
    
    return {
        "pathlets": [pathlet1, pathlet2],
        "raw_trace_segment_map": {
            "pathlet_001": segment1,
            "pathlet_002": segment2
        }
    }


def test_pathlets_to_storage(test_data):
    """测试 pathlets_to_storage 方法"""
    adapter = PathletStorageAdapter()
    pathlets = test_data["pathlets"]
    raw_trace_segment_map = test_data["raw_trace_segment_map"]
    
    # 转换数据
    metadata_df, points_df = adapter.pathlets_to_storage(pathlets, raw_trace_segment_map)
    
    # 验证元数据
    assert len(metadata_df) == 2
    assert "pathlet_id" in metadata_df.columns
    assert "is_valid" in metadata_df.columns
    assert "state_id" in metadata_df.columns
    assert "trace_name" in metadata_df.columns
    assert "start_index" in metadata_df.columns
    
    # 验证点数据
    assert "trace_name" in points_df.columns
    assert "trace_index" in points_df.columns
    assert "containing_pathlet_ids" in points_df.columns
    assert "delay_up" in points_df.columns
    assert "loss_up" in points_df.columns
    assert "bw_up" in points_df.columns
    assert "delay_down" in points_df.columns
    assert "loss_down" in points_df.columns
    assert "bw_down" in points_df.columns
    
    # 验证数据去重
    # segment1 有110个点，segment2 有100个点，重叠90个点
    # 去重后应该有 110 + 100 - 90 = 120 个点
    assert len(points_df) == 120
    
    # 验证 containing_pathlet_ids 数组
    for _, row in points_df.iterrows():
        assert isinstance(row["containing_pathlet_ids"], list)
        assert len(row["containing_pathlet_ids"]) >= 1


def test_storage_to_pathlets(test_data):
    """测试 storage_to_pathlets 方法"""
    adapter = PathletStorageAdapter()
    pathlets = test_data["pathlets"]
    raw_trace_segment_map = test_data["raw_trace_segment_map"]
    
    # 先转换为存储结构
    metadata_df, points_df = adapter.pathlets_to_storage(pathlets, raw_trace_segment_map)
    
    # 再转换回 Pathlet 对象
    reconstructed_pathlets = adapter.storage_to_pathlets(metadata_df, points_df)
    
    # 验证结果
    assert len(reconstructed_pathlets) == 2
    assert all(isinstance(p, Pathlet) for p in reconstructed_pathlets)
    
    # 验证 Pathlet 属性
    for pathlet in reconstructed_pathlets:
        assert pathlet.pathlet_id in ["pathlet_001", "pathlet_002"]
        assert isinstance(pathlet.body, BodyObservations)
        assert isinstance(pathlet.tail, TailObservations)
        # 验证观测数据数量
        if pathlet.pathlet_id == "pathlet_001":
            assert len(pathlet.body.observations) == 100
            assert len(pathlet.tail.observations) == 10
        elif pathlet.pathlet_id == "pathlet_002":
            assert len(pathlet.body.observations) == 100
            assert len(pathlet.tail.observations) == 10  # segment2 有110个点


def test_round_trip_conversion(test_data):
    """测试往返转换"""
    adapter = PathletStorageAdapter()
    pathlets = test_data["pathlets"]
    raw_trace_segment_map = test_data["raw_trace_segment_map"]
    
    # 第一次转换
    metadata_df, points_df = adapter.pathlets_to_storage(pathlets, raw_trace_segment_map)
    
    # 第二次转换
    reconstructed_pathlets = adapter.storage_to_pathlets(metadata_df, points_df)
    
    # 第三次转换
    metadata_df2, points_df2 = adapter.pathlets_to_storage(reconstructed_pathlets, raw_trace_segment_map)
    
    # 验证两次转换的结果一致
    assert len(metadata_df) == len(metadata_df2)
    assert len(points_df) == len(points_df2)
    
    # 验证点数据内容一致
    assert set(points_df["trace_index"]) == set(points_df2["trace_index"])


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
