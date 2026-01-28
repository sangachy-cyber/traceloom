# -*- coding: utf-8 -*-
"""原始轨迹片段

加载原始轨迹数据，转换为观测数据列表，用于径元提取和轨迹分析。

示例:
    # 创建原始轨迹片段
    from traceloom.domain.raw_trace import RawTraceSegment
    import pandas as pd

    # 创建示例 DataFrame
    df = pd.DataFrame({
        'delay_up': [10.0] * 120,
        'delay_down': [8.0] * 120,
        'loss_up': [0.01] * 120,
        'loss_down': [0.005] * 120,
        'bw_up': [50.0] * 120,
        'bw_down': [100.0] * 120
    })

    # 从 DataFrame 创建原始轨迹片段
    segment = RawTraceSegment.from_dataframe(
        df=df,
        trace_name="test_trace",
        start_index=0,
        length=110
    )

    # 获取主体和融尾观测数据
    body_obs = segment.get_body_observations()
    tail_obs = segment.get_tail_observations()

    # 检查是否有效
    print(f"轨迹片段是否有效: {segment.is_valid}")
"""

from dataclasses import dataclass
from typing import List

import pandas as pd

from traceloom.domain.pathlet import Observation


@dataclass
class TraceContextValues:
    """轨迹上下文值

    包含轨迹的各种统计指标，用于快速访问常用的统计信息。

    Attributes:
        delay_up_mean: 上行时延平均值
        loss_up_mean: 上行丢包率平均值
        bw_up_mean: 上行带宽平均值
        delay_down_mean: 下行时延平均值
        loss_down_mean: 下行丢包率平均值
        bw_down_mean: 下行带宽平均值

    Examples:
        # 创建轨迹上下文值
        ctx_values = TraceContextValues(
            delay_up_mean=10.5,
            loss_up_mean=0.01,
            bw_up_mean=50.0,
            delay_down_mean=8.2,
            loss_down_mean=0.005,
            bw_down_mean=100.0
        )
    """

    delay_up_mean: float
    """上行时延平均值"""

    loss_up_mean: float
    """上行丢包率平均值"""

    bw_up_mean: float
    """上行带宽平均值"""

    delay_down_mean: float
    """下行时延平均值"""

    loss_down_mean: float
    """下行丢包率平均值"""

    bw_down_mean: float
    """下行带宽平均值"""


@dataclass
class RawTraceSegment:
    """原始轨迹片段

    表示原始轨迹的一个片段，包含110个观测数据（100个主体观测数据+10个融尾观测数据）。

    Attributes:
        trace_name: 轨迹名称
        start_index: 起始索引
        observations: 观测数据列表
        is_valid: 是否有效

    Examples:
        # 直接创建原始轨迹片段
        segment = RawTraceSegment(
            trace_name="test_trace",
            start_index=0,
            observations=[Observation()] * 110,
            is_valid=True
        )
    """

    trace_name: str
    """轨迹名称"""
    start_index: int
    """起始索引"""
    observations: List[Observation]
    """观测数据列表"""
    is_valid: bool = True
    """是否有效"""

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, trace_name: str, start_index: int, length: int = 110) -> "RawTraceSegment":
        """从 DataFrame 创建原始轨迹片段

        从给定的 DataFrame 中提取指定长度的轨迹片段，并转换为 RawTraceSegment 实例。

        Args:
            df: 轨迹数据 DataFrame
            trace_name: 轨迹名称
            start_index: 起始索引
            length: 片段长度，默认110（100个主体观测数据+10个融尾观测数据）

        Returns:
            RawTraceSegment: 原始轨迹片段实例

        Raises:
            ValueError: 如果丢包率值不在0-1之间

        Examples:
            # 从 DataFrame 创建原始轨迹片段
            segment = RawTraceSegment.from_dataframe(
                df=df,
                trace_name="test_trace",
                start_index=0,
                length=110
            )
        """
        observations = []
        end_index = start_index + length
        has_invalid_delay = False

        # 提取观测数据
        for i in range(start_index, end_index):
            if i >= len(df):
                break

            row = df.iloc[i]

            # 检查时延是否超过2000ms
            delay_up = row.get('raw_delay_up', row.get('delay_up', 0.0))
            delay_down = row.get('raw_delay_down', row.get('delay_down', 0.0))
            if delay_up > 2000 or delay_down > 2000:
                has_invalid_delay = True

            # 处理带宽为0的情况
            bw_up = row.get('raw_bw_up', row.get('bw_up', 0.0))
            bw_down = row.get('raw_bw_down', row.get('bw_down', 0.0))
            loss_up = row.get('raw_loss_up', row.get('loss_up', 0.0))
            loss_down = row.get('raw_loss_down', row.get('loss_down', 0.0))

            # 确保丢包率是0-1范围
            # 如果raw_loss_up存在，它是百分比，需要转换为0-1
            if 'raw_loss_up' in row:
                loss_up = loss_up / 100.0
                loss_down = loss_down / 100.0
            # 验证丢包率在0-1之间
            if not (0.0 <= loss_up <= 1.0):
                raise ValueError(f"丢包率值无效: loss_up = {loss_up}，必须在0-1之间")
            if not (0.0 <= loss_down <= 1.0):
                raise ValueError(f"丢包率值无效: loss_down = {loss_down}，必须在0-1之间")

            # 如果带宽为0，将丢包率设置为100%（1.0）
            if bw_up == 0:
                loss_up = 1.0
            if bw_down == 0:
                loss_down = 1.0

            obs = Observation(
                delay_up=delay_up,
                loss_up=loss_up,
                bw_up=bw_up,
                delay_down=delay_down,
                loss_down=loss_down,
                bw_down=bw_down
            )
            observations.append(obs)

        # 检查是否有效
        is_valid = len(observations) == length and not has_invalid_delay

        return cls(
            trace_name=trace_name,
            start_index=start_index,
            observations=observations,
            is_valid=is_valid
        )

    def to_observations_list(self) -> List[Observation]:
        """将原始轨迹片段转换为观测数据列表

        Returns:
            List[Observation]: 观测数据列表

        Examples:
            # 获取观测数据列表
            obs_list = segment.to_observations_list()
            print(f"观测数据数量: {len(obs_list)}")
        """
        return self.observations

    def get_body_observations(self) -> List[Observation]:
        """获取主干观测数据（前100个观元）

        Returns:
            List[Observation]: 主干观测数据列表（前100个观元）

        Examples:
            # 获取主干观测数据
            body_obs = segment.get_body_observations()
            print(f"主干观测数据数量: {len(body_obs)}")
        """
        return self.observations[:100]

    def get_tail_observations(self) -> List[Observation]:
        """获取融尾观测数据（后10个）

        Returns:
            List[Observation]: 融尾观测数据列表

        Examples:
            # 获取融尾观测数据
            tail_obs = segment.get_tail_observations()
            print(f"融尾观测数据数量: {len(tail_obs)}")
        """
        return self.observations[100:]
