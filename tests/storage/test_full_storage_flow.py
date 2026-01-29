# -*- coding: utf-8 -*-
"""测试完整的存储和加载流程

测试从创建数据、保存数据、加载数据到验证数据的完整流程
"""

import tempfile
import shutil
from pathlib import Path
from traceloom.domain.pathlet import Pathlet, BodyObservations, TailObservations, Observation
from traceloom.domain.raw_trace import RawTraceSegment
from traceloom.storage.pathlet_storage import PathletStorage


def test_full_storage_flow():
    """测试完整的存储和加载流程"""
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    try:
        # 创建存储实例
        storage = PathletStorage(Path(temp_dir))
        
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
        
        # 创建重叠的 RawTraceSegment
        observations2 = []
        for i in range(110):
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
            observations=observations2
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
        
        # 保存数据
        raw_trace_segment_map = {
            "pathlet_001": segment1,
            "pathlet_002": segment2
        }
        
        storage.save_pathlets([pathlet1, pathlet2], raw_trace_segment_map)
        
        # 加载数据
        loaded_pathlets = storage.load_pathlets()
        
        # 验证加载结果
        assert len(loaded_pathlets) == 2
        assert all(isinstance(p, Pathlet) for p in loaded_pathlets)
        
        # 验证 Pathlet 属性
        for pathlet in loaded_pathlets:
            assert pathlet.pathlet_id in ["pathlet_001", "pathlet_002"]
            assert isinstance(pathlet.body, BodyObservations)
            assert isinstance(pathlet.tail, TailObservations)
            assert len(pathlet.body.observations) == 100
            assert len(pathlet.tail.observations) == 10
        
        # 测试按状态ID加载
        loaded_pathlets_state = storage.load_pathlets(state_id=-1)
        assert len(loaded_pathlets_state) == 2
        
        # 测试加载指定 Pathlet 的点数据
        for pathlet_id in ["pathlet_001", "pathlet_002"]:
            points_df = storage.load_pathlet_points(pathlet_id)
            assert points_df is not None
            assert not points_df.empty
            assert "trace_name" in points_df.columns
            assert "trace_index" in points_df.columns
            assert "containing_pathlet_ids" in points_df.columns
            assert "delay_up" in points_df.columns
        
        # 测试获取原始数据
        for pathlet_id in ["pathlet_001", "pathlet_002"]:
            raw_profile = storage.get_raw_profile(pathlet_id)
            assert raw_profile is not None
            assert "trace_name" in raw_profile
            assert "start_index" in raw_profile
            assert "ctx_10s" in raw_profile
            assert "cont_1s" in raw_profile
            assert "ctx_values" in raw_profile
            assert "is_valid" in raw_profile
            assert len(raw_profile["ctx_10s"].observations) == 100
            assert len(raw_profile["cont_1s"].observations) == 10
        
        # 测试重建原始数据结构
        pathlet_id = "pathlet_001"
        points_df = storage.load_pathlet_points(pathlet_id)
        body, tail = storage.reconstruct_profile(points_df)
        assert isinstance(body, BodyObservations)
        assert isinstance(tail, TailObservations)
        assert len(body.observations) > 0
        assert len(tail.observations) >= 0
        
        print("完整存储和加载流程测试通过！")
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    # 运行测试
    test_full_storage_flow()
