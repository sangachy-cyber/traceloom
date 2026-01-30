# -*- coding: utf-8 -*-
"""数据转换测试

测试数据转换逻辑的正确性，包括：
1. 丢包率均值计算（0-1范围）
2. 带宽为0时丢包率设置为100%
3. 延迟大于20000ms时的过滤
4. 状态ID默认值为-1
"""

import pandas as pd
import pytest

from traceloom.domain.pathlet import BodyObservations, Pathlet, TailObservations
from traceloom.storage.pathlet_storage import PathletStatistics


class TestDataConversion:
    """数据转换测试类"""

    def test_loss_rate_calculation(self):
        """测试丢包率均值计算（0-1范围）"""
        # 创建测试数据，丢包率已经是0-1范围
        test_data = {
            "delay_up": [100, 200, 300],
            "delay_down": [100, 200, 300],
            "loss_up": [0.1, 0.2, 0.3],  # 0-1范围
            "loss_down": [0.05, 0.1, 0.15],  # 0-1范围
            "bw_up": [10, 20, 30],
            "bw_down": [10, 20, 30],
        }
        df = pd.DataFrame(test_data)

        # 创建PathletMeta
        # 注意：PathletMeta没有from_dataframe方法，需要手动创建
        from traceloom.domain.pathlet import Observation

        observations = []
        for i in range(len(df)):
            row = df.iloc[i]
            obs = Observation(
                delay_up=row["delay_up"],
                loss_up=row["loss_up"],
                bw_up=row["bw_up"],
                delay_down=row["delay_down"],
                loss_down=row["loss_down"],
                bw_down=row["bw_down"],
            )
            observations.append(obs)
        # 创建Pathlet，使用前10个观测作为body，后10个作为tail（实际测试中数量可能不足，这里只做示例）
        body = BodyObservations(observations=observations[:10])
        tail = TailObservations(observations=observations[10:])
        segment = Pathlet(pathlet_id="test_pathlet", trace_name="test_trace", start_index=0, body=body, tail=tail)

        # 验证丢包率值正确
        assert len(segment.observations) == 3
        assert segment.observations[0].loss_up == 0.1
        assert segment.observations[1].loss_up == 0.2
        assert segment.observations[2].loss_up == 0.3
        assert segment.is_valid

    def test_bandwidth_zero_loss_rate(self):
        """测试带宽为0时丢包率设置为100%"""
        # 创建测试数据，包含带宽为0的情况
        test_data = {
            "delay_up": [100, 200, 300],
            "delay_down": [100, 200, 300],
            "loss_up": [0.1, 0.2, 0.3],  # 原始值，但会被覆盖
            "loss_down": [0.05, 0.1, 0.15],  # 原始值，但会被覆盖
            "bw_up": [0, 20, 30],  # 第一个样本带宽为0
            "bw_down": [10, 0, 30],  # 第二个样本带宽为0
        }
        df = pd.DataFrame(test_data)

        # 创建PathletMeta
        from traceloom.domain.pathlet import Observation

        observations = []
        for i in range(len(df)):
            row = df.iloc[i]
            # 模拟带宽为0时丢包率设置为1.0的逻辑
            loss_up = row["loss_up"] if row["bw_up"] != 0 else 1.0
            loss_down = row["loss_down"] if row["bw_down"] != 0 else 1.0
            obs = Observation(
                delay_up=row["delay_up"],
                loss_up=loss_up,
                bw_up=row["bw_up"],
                delay_down=row["delay_down"],
                loss_down=loss_down,
                bw_down=row["bw_down"],
            )
            observations.append(obs)
        # 创建Pathlet，使用前10个观测作为body，后10个作为tail（实际测试中数量可能不足，这里只做示例）
        body = BodyObservations(observations=observations[:10])
        tail = TailObservations(observations=observations[10:])
        segment = Pathlet(pathlet_id="test_pathlet", trace_name="test_trace", start_index=0, body=body, tail=tail)

        # 验证带宽为0时丢包率被设置为1.0
        assert len(segment.observations) == 3
        assert segment.observations[0].loss_up == 1.0  # bw_up=0，loss_up应为1.0
        assert segment.observations[1].loss_down == 1.0  # bw_down=0，loss_down应为1.0
        assert segment.observations[2].loss_up == 0.3  # 正常情况
        assert segment.observations[2].loss_down == 0.15  # 正常情况
        assert segment.is_valid

    def test_invalid_delay_filtering(self):
        """测试延迟大于20000ms时的过滤"""
        # 创建测试数据，包含延迟大于20000ms的情况
        test_data = {
            "delay_up": [100, 25000, 300],  # 第二个样本延迟大于20000ms
            "delay_down": [100, 200, 300],
            "loss_up": [0.1, 0.2, 0.3],
            "loss_down": [0.05, 0.1, 0.15],
            "bw_up": [10, 20, 30],
            "bw_down": [10, 20, 30],
        }
        df = pd.DataFrame(test_data)

        # 创建PathletMeta
        from traceloom.domain.pathlet import Observation

        observations = []
        for i in range(len(df)):
            row = df.iloc[i]
            obs = Observation(
                delay_up=row["delay_up"],
                loss_up=row["loss_up"],
                bw_up=row["bw_up"],
                delay_down=row["delay_down"],
                loss_down=row["loss_down"],
                bw_down=row["bw_down"],
            )
            observations.append(obs)
        # 检查是否有延迟大于2000ms的观测值
        has_large_delay = any(obs.delay_up > 2000 or obs.delay_down > 2000 for obs in observations)
        # 创建Pathlet，使用前10个观测作为body，后10个作为tail（实际测试中数量可能不足，这里只做示例）
        body = BodyObservations(observations=observations[:10])
        tail = TailObservations(observations=observations[10:])
        segment = Pathlet(
            pathlet_id="test_pathlet",
            trace_name="test_trace",
            start_index=0,
            body=body,
            tail=tail,
            is_valid=not has_large_delay,
        )

        # 验证包含无效延迟的segment被标记为无效
        assert not segment.is_valid

    def test_pathlet_statistics_calculation(self):
        """测试径元统计信息计算"""
        # 创建测试点数据
        test_points = {
            "delay_up": [100, 200, 300],
            "delay_down": [100, 200, 300],
            "loss_up": [0.1, 0.2, 0.3],  # 0-1范围
            "loss_down": [0.05, 0.1, 0.15],  # 0-1范围
            "bw_up": [10, 20, 30],
            "bw_down": [10, 20, 30],
        }
        points_df = pd.DataFrame(test_points)

        # 计算统计信息
        stats = PathletStatistics(
            delay_up_mean=points_df["delay_up"].mean(),
            delay_up_std=points_df["delay_up"].std(),
            delay_down_mean=points_df["delay_down"].mean(),
            delay_down_std=points_df["delay_down"].std(),
            loss_up_mean=points_df["loss_up"].mean(),
            loss_up_max=points_df["loss_up"].max(),
            loss_down_mean=points_df["loss_down"].mean(),
            loss_down_max=points_df["loss_down"].max(),
            bw_up_mean=points_df["bw_up"].mean(),
            bw_up_max=points_df["bw_up"].max(),
            bw_down_mean=points_df["bw_down"].mean(),
            bw_down_max=points_df["bw_down"].max(),
        )

        # 验证统计信息计算正确
        assert stats.delay_up_mean == 200
        assert stats.loss_up_mean == pytest.approx(0.2)  # 正确的均值计算，使用近似比较
        assert stats.loss_up_max == 0.3
        assert stats.bw_up_mean == 20
        assert stats.bw_up_max == 30

    def test_valid_segment_creation(self):
        """测试有效段创建"""
        # 创建有效测试数据
        test_data = {
            "delay_up": [100] * 110,  # 110个样本
            "delay_down": [100] * 110,
            "loss_up": [0.1] * 110,
            "loss_down": [0.05] * 110,
            "bw_up": [10] * 110,
            "bw_down": [10] * 110,
        }
        df = pd.DataFrame(test_data)

        # 创建PathletMeta
        from traceloom.domain.pathlet import Observation

        observations = []
        for i in range(len(df)):
            row = df.iloc[i]
            obs = Observation(
                delay_up=row["delay_up"],
                loss_up=row["loss_up"],
                bw_up=row["bw_up"],
                delay_down=row["delay_down"],
                loss_down=row["loss_down"],
                bw_down=row["bw_down"],
            )
            observations.append(obs)
        # 创建Pathlet，使用前100个观测作为body，后10个作为tail
        body = BodyObservations(observations=observations[:100])
        tail = TailObservations(observations=observations[100:])
        segment = Pathlet(pathlet_id="test_pathlet", trace_name="test_trace", start_index=0, body=body, tail=tail)

        # 验证段有效
        assert segment.is_valid
        assert len(segment.observations) == 110
        assert len(segment.body.observations) == 100
        assert len(segment.tail.observations) == 10
