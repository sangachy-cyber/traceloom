# -*- coding: utf-8 -*-
"""全局采样器（GlobalSampler）

根据状态ID和持续时间从全局径元库中采样径元
"""

import random
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
            # 一次加载所有有效的径元
            all_valid_pathlets = self.pathlet_storage.load_pathlets(is_valid=True)

            # 在内存中按状态ID分组
            for pathlet in all_valid_pathlets:
                state_id = pathlet.state_label.state_id
                if state_id not in state_pathlet_map:
                    state_pathlet_map[state_id] = []
                state_pathlet_map[state_id].append(pathlet)
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
            state_id = int(str(state_id).replace("s", ""))
            # 计算需要的径元数量（每10秒一个径元）
            pathlet_count = duration // 10
            if duration % 10 > 0:
                pathlet_count += 1

            # 从状态-径元映射中获取径元
            pathlets = self.state_pathlet_map.get(state_id, [])
            if len(pathlets) == 0:
                raise PathletSamplingError(f"无法为状态 {state_id} 采样到任何径元")

            # 采样径元
            for _ in range(pathlet_count):
                pathlet_sequence.append(random.choice(pathlets))

        logger.info(f"径元采样完成，共采样 {len(pathlet_sequence)} 个径元")
        return pathlet_sequence


__all__ = ["GlobalSampler"]
