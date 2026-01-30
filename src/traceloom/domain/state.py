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

from dataclasses import dataclass


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
