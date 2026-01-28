# -*- coding: utf-8 -*-
"""绣织（Stitcher）引擎实现

根据给定的状态序列和持续时间，从现有的径元库中选择和拼接径元
"""

from typing import List

from traceloom.core.logger import logger
from traceloom.domain.raw_trace import RawTraceSegment as RawProfile
from traceloom.storage.pathlet_storage import ContextData, ContinuationData, PathletStatistics


class Stitcher:
    """绣织引擎，根据给定的状态序列和持续时间，从现有的径元库中选择和拼接径元

    示例:
        from traceloom.weaving.engines.stitcher import Stitcher

        stitcher = Stitcher()
        profiles = stitcher.stitch(state_sequence=[0, 1, 2], duration=60)

    属性:
        None
    """

    def __init__(self):
        """初始化绣织引擎"""
        pass

    def stitch(self, state_sequence: List[int], duration: int) -> List[RawProfile]:
        """根据状态序列和持续时间生成网络剖面

        参数:
            state_sequence: 状态ID序列
            duration: 总持续时间（秒）

        返回:
            List[RawProfile]: 生成的网络剖面列表
        """
        logger.info(f"开始绣织操作，状态序列：{state_sequence}，总持续时间：{duration}秒")

        profiles = []
        # 简单实现：为每个状态生成一个网络剖面
        for i, state_id in enumerate(state_sequence):
            # 根据状态ID生成不同的网络参数
            base_delay = state_id * 30  # 每个状态增加30ms延迟
            base_loss = state_id * 0.01  # 每个状态增加1%丢包率
            base_bw = 80 - state_id * 5  # 每个状态减少5Mbps带宽

            # 创建上下文数据（100个点）
            ctx_10s = ContextData(
                delay_up=[base_delay + 5] * 100,  # 上行延迟
                loss_up=[base_loss + 0.005] * 100,  # 上行丢包率
                bw_up=[base_bw] * 100,  # 上行带宽
                delay_down=[base_delay] * 100,  # 下行延迟
                loss_down=[base_loss] * 100,  # 下行丢包率
                bw_down=[base_bw + 5] * 100  # 下行带宽
            )

            # 创建延续数据（10个点）
            cont_1s = ContinuationData(
                delay_up=[base_delay + 5] * 10,
                loss_up=[base_loss + 0.005] * 10,
                bw_up=[base_bw] * 10,
                delay_down=[base_delay] * 10,
                loss_down=[base_loss] * 10,
                bw_down=[base_bw + 5] * 10
            )

            # 创建上下文值
            # 注意：ctx_values 变量未使用，仅作为示例保留
            PathletStatistics(
                delay_up_mean=base_delay + 5,
                delay_up_std=0.0,
                delay_down_mean=base_delay,
                delay_down_std=0.0,
                loss_up_mean=base_loss + 0.005,
                loss_up_max=base_loss + 0.005,
                loss_down_mean=base_loss,
                loss_down_max=base_loss,
                bw_up_mean=base_bw,
                bw_up_max=base_bw,
                bw_down_mean=base_bw + 5,
                bw_down_max=base_bw + 5
            )

            # 创建观测数据列表
            observations = []

            # 添加上下文数据（100个点）
            for i in range(100):
                from traceloom.domain.pathlet import Observation
                obs = Observation(
                    delay_up=ctx_10s.delay_up[i],
                    loss_up=ctx_10s.loss_up[i],
                    bw_up=ctx_10s.bw_up[i],
                    delay_down=ctx_10s.delay_down[i],
                    loss_down=ctx_10s.loss_down[i],
                    bw_down=ctx_10s.bw_down[i]
                )
                observations.append(obs)

            # 添加延续数据（10个点）
            for i in range(10):
                from traceloom.domain.pathlet import Observation
                obs = Observation(
                    delay_up=cont_1s.delay_up[i],
                    loss_up=cont_1s.loss_up[i],
                    bw_up=cont_1s.bw_up[i],
                    delay_down=cont_1s.delay_down[i],
                    loss_down=cont_1s.loss_down[i],
                    bw_down=cont_1s.bw_down[i]
                )
                observations.append(obs)

            # 创建网络剖面
            profile = RawProfile(
                trace_name=f"stitch_{i}_{state_id}",
                start_index=i * 100,
                observations=observations,
                is_valid=True
            )

            profiles.append(profile)

        logger.info(f"绣织完成，生成 {len(profiles)} 个网络剖面")
        return profiles

    def weave(self, pattern):
        """织径方法，与其他引擎保持一致的接口

        参数:
            pattern: 织样对象

        返回:
            List[Any]: 织径结果
        """
        # 提取状态序列
        state_sequence = [state_id for state_id, _ in pattern.sequence]
        duration = sum(duration for _, duration in pattern.sequence)

        # 调用stitch方法生成网络剖面
        profiles = self.stitch(state_sequence, duration)

        # 转换为观测数据
        observations = []
        for profile in profiles:
            for i in range(100):
                obs = {
                    "delay_up": profile.ctx_10s.delay_up[i],
                    "loss_up": profile.ctx_10s.loss_up[i],
                    "bw_up": profile.ctx_10s.bw_up[i],
                    "delay_down": profile.ctx_10s.delay_down[i],
                    "loss_down": profile.ctx_10s.loss_down[i],
                    "bw_down": profile.ctx_10s.bw_down[i]
                }
                observations.append(obs)

        return observations


__all__ = ["Stitcher"]
