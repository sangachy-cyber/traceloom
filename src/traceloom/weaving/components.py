# -*- coding: utf-8 -*-
"""织律引擎（WeavingLawEngine）

加载GMM模型，提供predict_state()和state_name_to_id()接口
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List

from traceloom.core.config import settings
from traceloom.core.logger import logger
from traceloom.domain.pathlet import Pathlet
from traceloom.models.state_gmm import StateGMM


@dataclass
class PathletInfo:
    """径元信息"""

    pathlet_id: str
    state_id: int
    trace_name: str
    start_index: int


class WeavingLawEngine:
    """织律引擎，加载GMM模型，提供状态预测和映射功能

    示例:
        from traceloom.weaving.weaving_law import WeavingLawEngine
        from traceloom.domain.pathlet import Pathlet, BodyObservations, TailObservations, Observation

        # 初始化织律引擎
        weaving_law = WeavingLawEngine()

        # 状态名到ID映射
        state_id = weaving_law.state_name_to_id("s0")  # 返回 0

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
        model: StateGMM模型实例
    """

    def __init__(self, model_path: Path = None):
        """初始化织律引擎

        参数:
            model_path: GMM模型路径，默认使用settings.WEAVING_LAW_FILE
        """
        self.model_path = model_path or settings.WEAVING_LAW_FILE
        self.model = self._load_model()

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
            return StateGMM(self.model_path)
        except FileNotFoundError:
            # 如果模型文件不存在，创建一个默认的StateGMM实例
            logger.warning(f"模型文件不存在：{self.model_path}，创建默认StateGMM实例")
            return StateGMM()

    def predict_state(self, pathlet: Pathlet) -> int:
        """预测径元的状态ID

        参数:
            pathlet: 径元

        返回:
            int: 预测的状态ID
        """
        # 检查模型是否已加载
        if not self.model.is_loaded:
            # 如果模型未加载，直接返回默认状态ID 0
            logger.warning("StateGMM模型尚未加载，返回默认状态ID 0")
            return 0

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

    def state_name_to_id(self, state_name: str) -> int:
        """将状态名转换为状态ID

        支持的状态名格式:
            - "s0", "s1", ...: 返回对应的数字ID
            - "s-1": 表示混合态，返回-1

        参数:
            state_name: 状态名

        返回:
            int: 状态ID

        异常:
            ValueError: 无效的状态名格式
        """
        if not state_name.startswith("s"):
            raise ValueError(f"无效的状态名格式：{state_name}，必须以's'开头")

        try:
            return int(state_name[1:])
        except ValueError as err:
            raise ValueError(f"无效的状态名格式：{state_name}，'s'后必须跟数字") from err

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
