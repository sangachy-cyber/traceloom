# -*- coding: utf-8 -*-
"""广织（Dreamer）引擎实现

根据给定的状态序列生成全新的网络剖面序列
"""

from typing import List

from traceloom.core.logger import logger
from traceloom.domain.pathlet import BodyObservations, TailObservations
from traceloom.storage.pathlet_storage import PathletStatistics


class DreamerProfile:
    """Dreamer 引擎使用的网络剖面

    替代 training.profile.raw_profile.RawProfile，避免依赖 training 模块
    """

    def __init__(
        self,
        trace_name: str,
        start_index: int,
        ctx_10s: BodyObservations,
        cont_1s: TailObservations,
        ctx_values: PathletStatistics,
        is_valid: bool,
    ):
        """初始化 DreamerProfile

        参数:
            trace_name: 轨迹名称
            start_index: 起始索引
            ctx_10s: 主体观测数据
            cont_1s: 融尾观测数据
            ctx_values: 上下文值
            is_valid: 是否有效
        """
        self.trace_name = trace_name
        self.start_index = start_index
        self.ctx_10s = ctx_10s
        self.cont_1s = cont_1s
        self.ctx_values = ctx_values
        self.is_valid = is_valid


class Dreamer:
    """广织引擎，根据给定的状态序列生成全新的网络剖面序列

    示例:
        from traceloom.weaving.engines.dreamer import Dreamer

        dreamer = Dreamer()
        profiles = dreamer.dream(state_sequence=[0, 1, 2], duration=60)

    属性:
        None
    """

    def __init__(self):
        """初始化广织引擎"""
        pass

    def dream(self, state_sequence: List[int], duration: int) -> List[DreamerProfile]:
        """根据状态序列生成网络剖面

        参数:
            state_sequence: 状态ID序列
            duration: 总持续时间（秒）

        返回:
            List[DreamerProfile]: 生成的网络剖面列表
        """
        logger.info(f"开始广织操作，状态序列：{state_sequence}，总持续时间：{duration}秒")

        profiles = []
        # 简单实现：为每个状态生成一个网络剖面
        for i, state_id in enumerate(state_sequence):
            # 根据状态ID生成不同的网络参数
            base_delay = state_id * 50  # 每个状态增加50ms延迟
            base_loss = state_id * 0.02  # 每个状态增加2%丢包率
            base_bw = 100 - state_id * 10  # 每个状态减少10Mbps带宽

            # 创建上下文数据（100个点）
            ctx_10s = ContextData(
                delay_up=[base_delay + 10] * 100,  # 上行延迟
                loss_up=[base_loss + 0.01] * 100,  # 上行丢包率
                bw_up=[base_bw] * 100,  # 上行带宽
                delay_down=[base_delay] * 100,  # 下行延迟
                loss_down=[base_loss] * 100,  # 下行丢包率
                bw_down=[base_bw + 10] * 100,  # 下行带宽
            )

            # 创建延续数据（10个点）
            cont_1s = ContinuationData(
                delay_up=[base_delay + 10] * 10,
                loss_up=[base_loss + 0.01] * 10,
                bw_up=[base_bw] * 10,
                delay_down=[base_delay] * 10,
                loss_down=[base_loss] * 10,
                bw_down=[base_bw + 10] * 10,
            )

            # 创建上下文值
            ctx_values = PathletStatistics(
                delay_up_mean=base_delay + 10,
                delay_up_std=0.0,
                delay_down_mean=base_delay,
                delay_down_std=0.0,
                loss_up_mean=base_loss + 0.01,
                loss_up_max=base_loss + 0.01,
                loss_down_mean=base_loss,
                loss_down_max=base_loss,
                bw_up_mean=base_bw,
                bw_up_max=base_bw,
                bw_down_mean=base_bw + 10,
                bw_down_max=base_bw + 10,
            )

            # 创建网络剖面
            profile = DreamerProfile(
                trace_name=f"dream_{i}_{state_id}",
                start_index=i * 100,
                ctx_10s=ctx_10s,
                cont_1s=cont_1s,
                ctx_values=ctx_values,
                is_valid=True,
            )

            profiles.append(profile)

        logger.info(f"广织完成，生成 {len(profiles)} 个网络剖面")
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

        # 调用dream方法生成网络剖面
        profiles = self.dream(state_sequence, duration)

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
                    "bw_down": profile.ctx_10s.bw_down[i],
                }
                observations.append(obs)

        return observations


__all__ = ["Dreamer"]
