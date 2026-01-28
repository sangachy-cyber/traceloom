# -*- coding: utf-8 -*-
"""织律引擎（WeavingLawEngine）

提供状态名称到ID的映射和状态预测功能
"""

from traceloom.core.logger import logger


class WeavingLawEngine:
    """织律引擎，提供状态名称到ID的映射和状态预测功能

    示例:
        from traceloom.weaving.weaving_law import WeavingLawEngine

        weaving_law = WeavingLawEngine()
        state_id = weaving_law.state_name_to_id("s0")

    属性:
        state_mapping: 状态名称到ID的映射
    """

    def __init__(self):
        """初始化织律引擎"""
        self.state_mapping = self._build_state_mapping()

    def _build_state_mapping(self) -> dict:
        """构建状态名称到ID的映射

        返回:
            dict: 状态名称到ID的映射
        """
        # 简单实现：基于状态名称的数字部分构建映射
        state_mapping = {}
        # 预定义一些常见的状态映射
        for i in range(10):
            state_mapping[f"s{i}"] = i
        return state_mapping

    def state_name_to_id(self, state_name: str) -> int:
        """将状态名称映射为状态ID

        参数:
            state_name: 状态名称，如 "s0", "s1" 等

        返回:
            int: 状态ID

        异常:
            ValueError: 状态名称无法映射为ID
        """
        # 首先尝试从预构建的映射中获取
        if state_name in self.state_mapping:
            return self.state_mapping[state_name]

        # 尝试解析状态名称中的数字部分
        try:
            # 解析状态名称，如 "s0" -> 0
            if state_name.startswith("s"):
                state_id = int(state_name[1:])
                # 更新映射
                self.state_mapping[state_name] = state_id
                return state_id
            else:
                raise ValueError(f"无效的状态名称格式: {state_name}")
        except ValueError as e:
            logger.error(f"状态名称映射失败: {e}")
            raise

    def predict_state(self, observations) -> int:
        """根据观测数据预测状态ID

        参数:
            observations: 观测数据

        返回:
            int: 预测的状态ID
        """
        # 简单实现：基于观测数据的均值预测状态
        try:
            # 计算平均延迟
            if hasattr(observations, '__iter__'):
                # 假设observations是一个观测数据列表
                total_delay = 0
                count = 0
                for obs in observations:
                    if hasattr(obs, 'delay_up') and hasattr(obs, 'delay_down'):
                        total_delay += (obs.delay_up + obs.delay_down) / 2
                        count += 1
                if count > 0:
                    avg_delay = total_delay / count
                    # 根据平均延迟预测状态ID
                    if avg_delay < 50:
                        return 0
                    elif avg_delay < 100:
                        return 1
                    elif avg_delay < 150:
                        return 2
                    else:
                        return 3
        except Exception as e:
            logger.warning(f"状态预测失败: {e}")
        # 默认返回状态ID 0
        return 0


__all__ = ["WeavingLawEngine"]
