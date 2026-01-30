# -*- coding: utf-8 -*-
"""测试存储适配器功能

测试 PathletStorage 的数据去重和转换功能
"""

import pytest

from traceloom.domain.pathlet import BodyObservations, Observation, Pathlet, TailObservations
from traceloom.storage.pathlet_storage import PathletStorage


@pytest.fixture
def test_data():
    """创建测试数据"""
    # 创建主体观测数据
    body_observations = []
    for i in range(100):  # 100个主体点
        obs = Observation(
            delay_up=10.0 + i * 0.1,
            loss_up=0.01 + i * 0.0001,
            bw_up=50.0 - i * 0.05,
            delay_down=8.0 + i * 0.08,
            loss_down=0.005 + i * 0.00005,
            bw_down=100.0 - i * 0.1,
        )
        body_observations.append(obs)

    # 创建融尾观测数据
    tail_observations = []
    for i in range(10):  # 10个融尾点
        obs = Observation(
            delay_up=20.0 + i * 0.1,
            loss_up=0.02 + i * 0.0001,
            bw_up=40.0 - i * 0.05,
            delay_down=16.0 + i * 0.08,
            loss_down=0.01 + i * 0.00005,
            bw_down=80.0 - i * 0.1,
        )
        tail_observations.append(obs)

    # 创建 Pathlet 对象
    pathlet1 = Pathlet(
        pathlet_id="pathlet_001",
        trace_name="test_trace",
        start_index=0,
        dataset="train",
        body=BodyObservations(observations=body_observations),
        tail=TailObservations(observations=tail_observations),
        is_valid=True,
    )

    # 创建部分重叠的 Pathlet 对象
    body_observations2 = []
    for i in range(100):  # 100个主体点
        obs = Observation(
            delay_up=15.0 + i * 0.1,
            loss_up=0.015 + i * 0.0001,
            bw_up=45.0 - i * 0.05,
            delay_down=12.0 + i * 0.08,
            loss_down=0.0075 + i * 0.00005,
            bw_down=90.0 - i * 0.1,
        )
        body_observations2.append(obs)

    tail_observations2 = []
    for i in range(10):  # 10个融尾点
        obs = Observation(
            delay_up=25.0 + i * 0.1,
            loss_up=0.025 + i * 0.0001,
            bw_up=35.0 - i * 0.05,
            delay_down=20.0 + i * 0.08,
            loss_down=0.0125 + i * 0.00005,
            bw_down=70.0 - i * 0.1,
        )
        tail_observations2.append(obs)

    pathlet2 = Pathlet(
        pathlet_id="pathlet_002",
        trace_name="test_trace",
        start_index=50,
        dataset="train",
        body=BodyObservations(observations=body_observations2),
        tail=TailObservations(observations=tail_observations2),
        is_valid=True,
    )

    return [pathlet1, pathlet2]


def test_pathlets_to_storage(test_data):
    """测试 pathlets_to_storage 方法"""
    pathlets = test_data

    # 转换数据
    metadata_df, points_df = PathletStorage.pathlets_to_storage(pathlets)

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
    assert "pathlet_ids" in points_df.columns
    assert "delay_up" in points_df.columns
    assert "loss_up" in points_df.columns
    assert "bw_up" in points_df.columns
    assert "delay_down" in points_df.columns
    assert "loss_down" in points_df.columns
    assert "bw_down" in points_df.columns

    # 验证数据去重
    # pathlet1 有110个点(100+10)，索引范围0-109
    # pathlet2 有110个点，索引范围50-159
    # 重叠部分是索引50-109，共60个点
    # 去重后应该有 110 + 110 - 60 = 160 个点
    assert len(points_df) == 160

    # 验证 pathlet_ids 数组
    for _, row in points_df.iterrows():
        assert isinstance(row["pathlet_ids"], list)
        assert len(row["pathlet_ids"]) >= 1


def test_storage_to_pathlets(test_data):
    """测试 storage_to_pathlets 方法"""
    pathlets = test_data

    # 先转换为存储结构
    metadata_df, points_df = PathletStorage.pathlets_to_storage(pathlets)

    # 再转换回 Pathlet 对象
    reconstructed_pathlets = PathletStorage.storage_to_pathlets(metadata_df, points_df)

    # 验证结果
    assert len(reconstructed_pathlets) == 2
    assert all(isinstance(p, Pathlet) for p in reconstructed_pathlets)

    # 验证 Pathlet 属性
    for pathlet in reconstructed_pathlets:
        assert pathlet.pathlet_id in ["pathlet_001", "pathlet_002"]
        assert isinstance(pathlet.body, BodyObservations)
        assert isinstance(pathlet.tail, TailObservations)
        # 验证观测数据数量
        assert len(pathlet.body.observations) == 100
        assert len(pathlet.tail.observations) == 10


def test_round_trip_conversion(test_data):
    """测试往返转换"""
    pathlets = test_data

    # 第一次转换
    metadata_df, points_df = PathletStorage.pathlets_to_storage(pathlets)

    # 第二次转换
    reconstructed_pathlets = PathletStorage.storage_to_pathlets(metadata_df, points_df)

    # 第三次转换
    metadata_df2, points_df2 = PathletStorage.pathlets_to_storage(reconstructed_pathlets)

    # 验证两次转换的结果一致
    assert len(metadata_df) == len(metadata_df2)
    assert len(points_df) == len(points_df2)

    # 验证点数据内容一致
    assert set(points_df["trace_index"]) == set(points_df2["trace_index"])


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
