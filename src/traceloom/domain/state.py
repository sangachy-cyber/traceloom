# -*- coding: utf-8 -*-
"""状态管理模块

定义网络状态标签和状态命名器，用于网络状态的标识和管理。

示例:
    # 使用状态标签
    from traceloom.domain.state import StateLabel, StateNamer

    # 创建状态标签
    label = StateLabel(state_id=0, confidence=0.95)
    print(f"状态 ID: {label.state_id}, 置信度: {label.confidence}")

    # 使用状态命名器
    namer = StateNamer()
    state_name = namer.get_state_name(1)
    print(f"状态 ID 1 的名称: {state_name}")

    # 根据概率分配状态
    probabilities = [0.1, 0.8, 0.1]
    state_info = namer.assign_state(probabilities, 0.85)
    print(f"分配的状态: {state_info}")
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class StateLabel:
    """状态标签

    表示网络状态的标签，包含状态ID和置信度。

    Attributes:
        state_id: 状态 ID
        confidence: 置信度

    Examples:
        # 创建状态标签
        label = StateLabel(state_id=0, confidence=0.95)
        print(f"状态 ID: {label.state_id}, 置信度: {label.confidence}")
    """

    state_id: int
    """状态 ID"""
    confidence: float = 1.0
    """置信度"""


class StateNamer:
    """状态命名器（轻量版）

    加载状态映射表，提供 ID 到语义名的映射，以及状态分配功能。

    Attributes:
        state_mapping: 状态 ID 到状态名称的映射
        state_metadata: 状态元数据
        n_components: 组件数量
        confidence_threshold: 置信度阈值

    Examples:
        # 使用默认状态映射
        namer = StateNamer()
        state_name = namer.get_state_name(1)
        print(f"状态 ID 1 的名称: {state_name}")

        # 从文件加载状态映射
        # namer = StateNamer(state_mapping_path=Path("state_mapping.json"))
    """

    def __init__(self, state_mapping_path: Optional[Path] = None):
        """初始化状态命名器

        Args:
            state_mapping_path: 状态映射表文件路径

        Examples:
            # 初始化状态命名器
            namer = StateNamer()
        """
        self.state_mapping: Dict[int, str] = {}
        """状态 ID 到状态名称的映射"""
        self.state_metadata: Dict = {}
        """状态元数据"""
        self.n_components: int = 3
        """组件数量"""
        self.confidence_threshold: float = 0.85
        """置信度阈值"""

        if state_mapping_path and state_mapping_path.exists():
            self.load_state_mapping(state_mapping_path)
        else:
            # 使用默认状态映射
            self._load_default_mapping()

    def load_state_mapping(self, state_mapping_path: Path) -> None:
        """加载状态映射表

        Args:
            state_mapping_path: 状态映射表文件路径

        Examples:
            # 加载状态映射表
            namer.load_state_mapping(Path("state_mapping.json"))
        """
        with open(state_mapping_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 提取状态映射
        if "states" in data:
            for state in data["states"]:
                if "state_id" in state and "state_name" in state:
                    self.state_mapping[state["state_id"]] = state["state_name"]

        # 保存元数据
        self.state_metadata = data

        # 更新组件数量和置信度阈值
        if "n_components" in data:
            self.n_components = data["n_components"]
        if "confidence_threshold" in data:
            self.confidence_threshold = data["confidence_threshold"]

    def _load_default_mapping(self) -> None:
        """加载默认状态映射

        加载默认的状态映射表，包含稳定、抖动、异常三种状态。

        Examples:
            # 内部方法，无需手动调用
            # namer._load_default_mapping()
        """
        # 默认状态映射
        self.state_mapping = {0: "稳定", 1: "抖动", 2: "异常"}

        # 默认元数据
        self.state_metadata = {
            "algorithm": "gmm",
            "n_components": 3,
            "confidence_threshold": 0.85,
            "states": [
                {"state_id": 0, "state_name": "稳定", "type": "pure"},
                {"state_id": 1, "state_name": "抖动", "type": "pure"},
                {"state_id": 2, "state_name": "异常", "type": "pure"},
            ],
        }

    def get_state_name(self, state_id: int) -> str:
        """根据状态 ID 获取状态名称

        Args:
            state_id: 状态 ID

        Returns:
            str: 状态名称

        Examples:
            # 获取状态名称
            state_name = namer.get_state_name(1)
            print(f"状态 ID 1 的名称: {state_name}")  # 输出: 抖动
        """
        return self.state_mapping.get(state_id, f"未知状态_{state_id}")

    def get_state_id(self, state_name: str) -> Optional[int]:
        """根据状态名称获取状态 ID

        Args:
            state_name: 状态名称

        Returns:
            Optional[int]: 状态 ID, 不存在则返回 None

        Examples:
            # 获取状态 ID
            state_id = namer.get_state_id("抖动")
            print(f"状态名称 '抖动' 的 ID: {state_id}")  # 输出: 1
        """
        for state_id, name in self.state_mapping.items():
            if name == state_name:
                return state_id
        return None

    def get_state_metadata(self) -> Dict:
        """获取状态元数据

        Returns:
            Dict: 状态元数据

        Examples:
            # 获取状态元数据
            metadata = namer.get_state_metadata()
            print(f"状态元数据: {metadata}")
        """
        return self.state_metadata

    def assign_state(self, probabilities: List[float], confidence_threshold: float) -> Dict[str, Any]:
        """根据概率分配状态

        根据给定的状态概率列表和置信度阈值，分配最可能的状态。

        Args:
            probabilities: 状态概率列表
            confidence_threshold: 置信度阈值

        Returns:
            Dict[str, Any]: 状态信息，包含状态 ID、状态名称、是否纯净、置信度等

        Examples:
            # 根据概率分配状态
            probabilities = [0.1, 0.8, 0.1]
            state_info = namer.assign_state(probabilities, 0.85)
            print(f"分配的状态: {state_info}")
        """
        if not probabilities:
            return {
                "state_id": -1,
                "state_name": "未知状态",
                "is_pure": False,
                "state_proba": 0.0,
                "top2_state_ids": [-1, -1],
                "top2_state_probas": [0.0, 0.0],
                "base_state_id": -1,
            }

        # 计算最高概率和对应的状态 ID
        max_prob = max(probabilities)
        state_id = probabilities.index(max_prob)
        state_name = self.get_state_name(state_id)
        is_pure = max_prob >= confidence_threshold

        # 获取前两个最高概率的状态
        sorted_indices = sorted(range(len(probabilities)), key=lambda i: probabilities[i], reverse=True)
        top2_state_ids = (
            sorted_indices[:2] if len(sorted_indices) >= 2 else sorted_indices + [-1] * (2 - len(sorted_indices))
        )
        top2_state_probas = [probabilities[i] if i != -1 else 0.0 for i in top2_state_ids]

        return {
            "state_id": state_id,
            "state_name": state_name,
            "is_pure": is_pure,
            "state_proba": max_prob,
            "top2_state_ids": top2_state_ids,
            "top2_state_probas": top2_state_probas,
            "base_state_id": state_id,
        }

    def update_n_components(self, n_components: int) -> None:
        """更新聚类数量

        Args:
            n_components: 聚类数量

        Examples:
            # 更新聚类数量
            namer.update_n_components(5)
            print(f"更新后的聚类数量: {namer.n_components}")  # 输出: 5
        """
        self.n_components = n_components
        self.state_metadata["n_components"] = n_components

    def update_confidence_threshold(self, confidence_threshold: float) -> None:
        """更新置信度阈值

        Args:
            confidence_threshold: 置信度阈值

        Examples:
            # 更新置信度阈值
            namer.update_confidence_threshold(0.9)
            print(f"更新后的置信度阈值: {namer.confidence_threshold}")  # 输出: 0.9
        """
        self.confidence_threshold = confidence_threshold
        self.state_metadata["confidence_threshold"] = confidence_threshold
