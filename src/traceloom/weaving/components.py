# -*- coding: utf-8 -*-
"""织律引擎（WeavingLawEngine）

加载GMM模型，提供predict_state()和state_name_to_id()接口
"""

from dataclasses import dataclass
from pathlib import Path
from random import choice
from typing import List, Tuple

from traceloom.core.config import settings
from traceloom.core.exceptions import PathletSamplingError
from traceloom.core.logger import logger
from traceloom.domain.raw_trace import RawTraceSegment as RawProfile
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
        from training.common.profile import RawProfile

        # 初始化织律引擎
        weaving_law = WeavingLawEngine()

        # 状态名到ID映射
        state_id = weaving_law.state_name_to_id("s0")  # 返回 0

        # 预测状态
        profile = RawProfile(...)
        state_id = weaving_law.predict_state(profile)

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

    def predict_state(self, profile: RawProfile) -> int:
        """预测网络剖面的状态ID

        参数:
            profile: 网络剖面

        返回:
            int: 预测的状态ID
        """
        # 检查模型是否已加载
        if not self.model.is_loaded:
            # 如果模型未加载，直接返回默认状态ID 0
            logger.warning("StateGMM模型尚未加载，返回默认状态ID 0")
            return 0

        label = self.model.predict(profile.observations)
        return label.state_id

    def predict_state_proba(self, profile: RawProfile) -> List[float]:
        """预测网络剖面属于每个状态的概率

        参数:
            profile: 网络剖面

        返回:
            List[float]: 每个状态的概率列表
        """
        # 检查模型是否已加载
        if not self.model.is_loaded:
            # 如果模型未加载，返回默认概率分布
            logger.warning("StateGMM模型尚未加载，返回默认概率分布")
            return [1.0, 0.0, 0.0]  # 默认返回3个状态的概率分布

        # 由于StateGMM的predict方法只返回单个标签和置信度
        # 这里简化处理，返回一个包含置信度的列表
        label = self.model.predict(profile.observations)
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

    def get_state_distribution(self, profiles: List[RawProfile]) -> List[int]:
        """获取多个网络剖面的状态分布

        参数:
            profiles: 网络剖面列表

        返回:
            List[int]: 每个剖面的状态ID列表
        """
        # 检查模型是否已加载
        if not self.model.is_loaded:
            # 如果模型未加载，返回默认状态ID 0
            logger.warning("StateGMM模型尚未加载，返回默认状态ID 0")
            return [0] * len(profiles)

        return [self.predict_state(profile) for profile in profiles]


class GlobalSampler:
    """全局采样器，根据状态和持续时间从全局库采样径元ID序列

    示例:

        from traceloom.io.pathlet_storage import PathletStorage

        # 初始化采样器
        pathlet_storage = PathletStorage()
        sampler = GlobalSampler(pathlet_storage)

        # 采样径元
        pathlet_sequence = sampler.sample_pathlets([(0, 20), (1, 30)])

    属性
        pathlet_storage: 径元存储实例
        state_pathlet_map: 状态ID到径元列表的映射表
        all_pathlets: 所有径元列表，用于容错处理
    """

    def __init__(self, pathlet_storage):
        """初始化全局采样器

        参数:
            pathlet_storage: 径元存储实例，用于获取径元数据
        """
        self.pathlet_storage = pathlet_storage
        self.state_pathlet_map = self._build_state_pathlet_map()
        self.all_pathlets = self._build_all_pathlets_list()

    def _build_state_pathlet_map(self) -> dict:
        """构建状态ID到径元列表的映射表

        返回:
            dict: 状态ID到径元列表的映射表
        """
        # 获取所有径元
        all_pathlets = self.pathlet_storage.load_pathlets()

        # 构建映射表
        state_pathlet_map = {}
        for pathlet in all_pathlets:
            state_id = pathlet.state_id
            if state_id not in state_pathlet_map:
                state_pathlet_map[state_id] = []
            state_pathlet_map[state_id].append(pathlet)

        return state_pathlet_map

    def _build_all_pathlets_list(self) -> List:
        """构建所有径元的列表，用于容错处理

        返回:
            List: 所有径元的列表
        """
        all_pathlets = []
        for pathlets in self.state_pathlet_map.values():
            all_pathlets.extend(pathlets)
        return all_pathlets

    def sample_pathlets(self, state_duration_sequence: List[Tuple[int, int]]) -> List[PathletInfo]:
        """根据状态和持续时间序列采样径元ID序列

        每个径元代表10秒数据，所以需要的径元数量为 duration_sec / 10 向上取整

        参数:
            state_duration_sequence: 状态ID和持续时间的序列，格式为 List[Tuple[int, int]]

        返回:
            List[PathletInfo]: 采样的径元序列

        异常:
            PathletSamplingError: 无法采样到足够径元
        """
        pathlet_sequence = []
        has_all_pathlets = len(self.all_pathlets) > 0

        for state_id, duration_sec in state_duration_sequence:
            # 计算需要的径元数量
            num_pathlets = duration_sec // 10
            if duration_sec % 10 != 0:
                num_pathlets += 1

            logger.info(f"采样状态ID {state_id} 从{num_pathlets} 个径元，持续时间 {duration_sec} 秒")

            # 从预构建的状态-径元映射表中获取径元，O(1)查询
            state_pathlets = self.state_pathlet_map.get(state_id, [])

            # 实现径元采样容错：若某状态无径元，使用全局随机径元
            if not state_pathlets:
                if has_all_pathlets:
                    logger.warning(f"状态ID {state_id} 无径元，使用全局随机径元")
                    state_pathlets = self.all_pathlets
                else:
                    # 创建默认径元数据
                    logger.warning(f"状态ID {state_id} 无径元，创建默认径元")
                    # 这里创建一个默认的径元信息
                    default_pathlet = PathletInfo(
                        pathlet_id=f"default_{state_id}_0",
                        state_id=state_id,
                        trace_name="default",
                        start_index=0
                    )
                    state_pathlets = [default_pathlet]
                    logger.info(f"创建默认径元: {default_pathlet.pathlet_id}")

            # 如果采样到的径元数量不足，循环使用
            if len(state_pathlets) < num_pathlets:
                logger.warning(f"状态ID {state_id} 的径元数量不足，循环使用")
                state_pathlets = state_pathlets * (num_pathlets // len(state_pathlets) + 1)

            # 构建PathletInfo列表
            for i in range(num_pathlets):
                pathlet = state_pathlets[i]
                pathlet_info = PathletInfo(
                    pathlet_id=pathlet.pathlet_id,
                    state_id=pathlet.state_id,
                    trace_name=pathlet.pathlet_id.split("_")[0],
                    start_index=int(pathlet.pathlet_id.split("_")[1])
                )
                pathlet_sequence.append(pathlet_info)

        return pathlet_sequence

    def sample_single_pathlet(self, state_id: int) -> PathletInfo:
        """采样单个径元

        参数:
            state_id: 状态ID

        返回:
            PathletInfo: 采样的径元信息

        异常:
            PathletSamplingError: 无法采样到径元
        """
        # 从状态-径元映射表中获取径元
        state_pathlets = self.state_pathlet_map.get(state_id, [])

        # 实现径元采样容错：若某状态无径元，使用全局随机径元
        if not state_pathlets:
            if self.all_pathlets:
                logger.warning(f"状态ID {state_id} 无径元，使用全局随机径元")
                state_pathlets = self.all_pathlets
            else:
                raise PathletSamplingError(f"无法采样到状态ID {state_id} 的径元，且无全局径元可用")

        # 随机选择一个径元
        pathlet = choice(state_pathlets)

        return PathletInfo(
            pathlet_id=pathlet.pathlet_id,
            state_id=pathlet.state_id,
            trace_name=pathlet.pathlet_id.split("_")[0],
            start_index=int(pathlet.pathlet_id.split("_")[1])
        )
