# -*- coding: utf-8 -*-
"""织律引擎（WeavingLawEngine）

提供状态名称到ID的映射和状态预测功能
"""

from pathlib import Path
from typing import List

from traceloom.core.config import settings
from traceloom.core.logger import logger
from traceloom.domain.pathlet import Pathlet
from traceloom.models.state_gmm import StateGMM


class WeavingLawEngine:
    """织律引擎，提供状态名称到ID的映射和状态预测功能

    示例:
        from traceloom.weaving.weaving_law import WeavingLawEngine
        from traceloom.domain.pathlet import Pathlet, BodyObservations, TailObservations, Observation

        # 初始化织律引擎
        weaving_law = WeavingLawEngine()

        # 状态名到ID映射
        state_id = weaving_law.state_name_to_id("s0")

        # 预测状态
        # 创建示例径元
        body = BodyObservations(
            observations=[Observation(delay_up=100.0, loss_up=0.01, bw_up=10.0,
                                    delay_down=100.0, loss_down=0.01, bw_down=10.0) for _ in range(100)]
        )
        tail = TailObservations(
            observations=[Observation(delay_up=100.0, loss_up=0.01, bw_up=10.0,
                                    delay_down=100.0, loss_down=0.01, bw_down=10.0) for _ in range(10)]
        )
        pathlet = Pathlet(
            pathlet_id="example_pathlet",
            trace_name="example_trace",
            start_index=0,
            body=body,
            tail=tail
        )
        state_id = weaving_law.predict_state(pathlet)

    属性:
        state_mapping: 状态名称到ID的映射
        model: StateGMM模型实例
    """

    def __init__(self, model_path: Path = None):
        """初始化织律引擎

        参数:
            model_path: GMM模型路径，默认使用settings.WEAVING_LAW_FILE
        """
        self.state_mapping = self._build_state_mapping()
        self.model_path = model_path or settings.WEAVING_LAW_FILE
        self.model = self._load_model()

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

    def _load_model(self) -> StateGMM:
        """加载StateGMM模型

        返回:
            StateGMM: 加载的StateGMM模型实例

        异常:
            FileNotFoundError: 模型文件不存在
        """
        logger.info(f"加载织律模型：{self.model_path}")

        # 尝试加载模型文件
        try:
            model = StateGMM(model_path=self.model_path)
            logger.info(f"加载织律模型成功：{self.model_path}")
            return model
        except FileNotFoundError:
            # 如果模型文件不存在，直接报错，不允许做任何处理
            logger.error(f"织律模型文件不存在：{self.model_path}，无法加载")
            raise
        except Exception as e:
            logger.error(e)
            raise

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

    def predict_state(self, pathlet: Pathlet) -> int:
        """根据径元预测状态ID

        参数:
            pathlet: 径元

        返回:
            int: 预测的状态ID
        """
        # 检查模型是否已加载
        if not self.model.is_loaded:
            raise ValueError("如果模型未加载")

        # 提取径元的观测数据
        observations = pathlet.observations
        label = self.model.predict(observations)
        return label.state_id

    def predict_state_proba(self, pathlet: Pathlet) -> List[float]:
        """预测径元属于每个状态的概率

        参数:
            pathlet: 径元

        返回:
            List[float]: 每个状态的概率列表
        """
        # 检查模型是否已加载
        if not self.model.is_loaded:
            # 如果模型未加载，返回默认概率分布
            logger.warning("StateGMM模型尚未加载，返回默认概率分布")
            return [1.0, 0.0, 0.0]  # 默认返回3个状态的概率分布

        # 提取径元的观测数据
        observations = pathlet.observations
        # 由于StateGMM的predict方法只返回单个标签和置信度
        # 这里简化处理，返回一个包含置信度的列表
        label = self.model.predict(observations)
        proba = [0.0] * 3  # 假设3个状态
        proba[label.state_id] = label.confidence
        return proba

    def state_id_to_name(self, state_id: int) -> str:
        """将状态ID转换为状态名

        参数:
            state_id: 状态ID

        返回:
            str: 状态名
        """
        return f"s{state_id}"

    def get_state_distribution(self, pathlets: List[Pathlet]) -> List[int]:
        """获取多个径元的状态分布

        参数:
            pathlets: 径元列表

        返回:
            List[int]: 每个径元的状态ID列表
        """
        # 检查模型是否已加载
        if not self.model.is_loaded:
            # 如果模型未加载，返回默认状态ID 0
            logger.warning("StateGMM模型尚未加载，返回默认状态ID 0")
            return [0] * len(pathlets)

        return [self.predict_state(pathlet) for pathlet in pathlets]


__all__ = ["WeavingLawEngine"]
