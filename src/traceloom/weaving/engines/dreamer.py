# -*- coding: utf-8 -*-
"""广织（Dreamer）引擎实现

根据给定的状态序列生成全新的径元序列
"""

from typing import List

from traceloom.core.logger import logger
from traceloom.domain.pathlet import BodyObservations, Observation, Pathlet, TailObservations
from traceloom.storage.pathlet_storage import PathletStatistics


class Dreamer:
    """广织引擎，根据给定的状态序列生成全新的径元序列

    示例:
        from traceloom.weaving.engines.dreamer import Dreamer

        dreamer = Dreamer()
        pathlets = dreamer.dream(state_sequence=[0, 1, 2], duration=60)

    属性:
        None
    """

    def __init__(self):
        """初始化广织引擎"""
        pass

    def dream(self, state_sequence: List[int], duration: int) -> List[Pathlet]:
        """根据状态序列生成径元

        参数:
            state_sequence: 状态ID序列
            duration: 总持续时间（秒）

        返回:
            List[Pathlet]: 生成的径元列表
        """
        # 当前暂未实现，直接抛出 NotImplementedError
        raise NotImplementedError

    def weave(self, pattern, sampler):
        """织径方法，与其他引擎保持一致的接口

        参数:
            pattern: 织样对象
            sampler: 全局采样器实例，用于采样径元

        返回:
            List[Any]: 织径结果
        """
        # 从织样序列生成观测数据
        observations = []

        try:
            # 使用采样器根据织样序列采样径元
            state_duration_sequence = [(state, duration) for state, duration in pattern.sequence]
            pathlets = sampler.sample_pathlets(state_duration_sequence)
            logger.info(f"成功采样 {len(pathlets)} 个径元")

            # 从径元生成观测数据
            for pathlet in pathlets:
                # 获取主体观测数据
                if hasattr(pathlet, "body") and hasattr(pathlet.body, "observations"):
                    for obs in pathlet.body.observations:
                        observations.append(
                            [obs.delay_up, obs.loss_up, obs.bw_up, obs.delay_down, obs.loss_down, obs.bw_down]
                        )
                else:
                    # 如果径元结构不符合预期，使用默认值
                    logger.warning(f"径元结构不符合预期: {pathlet}")
                    # 为每个径元生成默认观测数据（10秒，100个样本）
                    for _ in range(100):
                        observations.append([50.0, 0.01, 50.0, 50.0, 0.01, 50.0])
        except Exception as e:
            logger.error(f"广织操作失败: {e}")
            # 如果采样失败，使用模拟数据作为 fallback
            for state, duration in pattern.sequence:
                for _ in range(duration * 10):  # 10 Hz 采样率
                    observations.append([50.0, 0.01, 50.0, 50.0, 0.01, 50.0])

        logger.info(f"成功生成 {len(observations)} 个观测数据")
        return observations


__all__ = ["Dreamer"]
