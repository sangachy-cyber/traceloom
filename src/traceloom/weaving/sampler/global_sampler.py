# -*- coding: utf-8 -*-
"""全局采样器（GlobalSampler）

根据状态ID和持续时间从全局径元库中采样径元
"""

from typing import List, Tuple

from traceloom.core.exceptions import PathletSamplingError
from traceloom.core.logger import logger


class GlobalSampler:
    """全局采样器，根据状态ID和持续时间从全局径元库中采样径元

    示例:
        from traceloom.weaving.sampler.global_sampler import GlobalSampler
        from traceloom.storage.pathlet_storage import PathletStorage

        pathlet_storage = PathletStorage()
        sampler = GlobalSampler(pathlet_storage)
        pathlet_sequence = sampler.sample_pathlets([(0, 20), (1, 30)])

    属性:
        pathlet_storage: 径元存储实例
        state_pathlet_map: 状态ID到径元列表的映射
    """

    def __init__(self, pathlet_storage):
        """初始化全局采样器

        参数:
            pathlet_storage: 径元存储实例
        """
        self.pathlet_storage = pathlet_storage
        self.state_pathlet_map = self._build_state_pathlet_map()

    def _build_state_pathlet_map(self) -> dict:
        """构建状态ID到径元列表的映射

        返回:
            dict: 状态ID到径元列表的映射
        """
        state_pathlet_map = {}
        try:
            # 尝试获取状态分布
            state_distribution = self.pathlet_storage.get_state_distribution()
            for state_id in state_distribution.keys():
                # 加载指定状态的径元
                pathlets = self.pathlet_storage.load_pathlets(state_id=state_id)
                if pathlets:
                    state_pathlet_map[state_id] = pathlets
        except Exception as e:
            logger.warning(f"构建状态-径元映射失败: {e}")
        return state_pathlet_map

    def sample_pathlets(self, state_duration_sequence: List[Tuple[int, int]]) -> List:
        """根据状态ID和持续时间序列采样径元

        参数:
            state_duration_sequence: 状态ID和持续时间的序列

        返回:
            List: 采样的径元列表

        异常:
            PathletSamplingError: 无法采样到足够径元
        """
        logger.info(f"开始采样径元，状态-持续时间序列：{state_duration_sequence}")

        pathlet_sequence = []
        for state_id, duration in state_duration_sequence:
            # 计算需要的径元数量（每10秒一个径元）
            pathlet_count = duration // 10
            if duration % 10 > 0:
                pathlet_count += 1

            # 从状态-径元映射中获取径元
            pathlets = self.state_pathlet_map.get(state_id, [])
            if not pathlets:
                # 如果没有找到对应状态的径元，尝试从所有径元中随机选择
                try:
                    all_pathlets = self.pathlet_storage.load_pathlets()
                    if all_pathlets:
                        pathlets = all_pathlets
                        logger.warning(f"未找到状态 {state_id} 的径元，使用所有径元进行采样")
                    else:
                        raise PathletSamplingError(f"无法为状态 {state_id} 采样到任何径元")
                except Exception as e:
                    raise PathletSamplingError(f"无法为状态 {state_id} 采样到任何径元: {e}") from e

            # 采样径元
            for i in range(pathlet_count):
                # 简单实现：循环使用可用径元
                pathlet = pathlets[i % len(pathlets)]
                pathlet_sequence.append(pathlet)

        logger.info(f"径元采样完成，共采样 {len(pathlet_sequence)} 个径元")
        return pathlet_sequence


__all__ = ["GlobalSampler"]
