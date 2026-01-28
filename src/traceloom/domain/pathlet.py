# -*- coding: utf-8 -*-
"""共享数据结构

定义推理与训练共用的数据结构，包括网络观测模型、径元等核心域对象。

示例:
    # 创建观测数据
    from traceloom.domain.pathlet import Observation, BodyObservations, TailObservations, Pathlet

    # 创建单个观测数据
    obs = Observation(
        delay_up=10.5,
        delay_down=8.2,
        loss_up=0.01,
        loss_down=0.005,
        bw_up=50.0,
        bw_down=100.0
    )

    # 创建主体和融尾观测数据
    body = BodyObservations(observations=[obs] * 100)
    tail = TailObservations(observations=[obs] * 10)

    # 创建径元
    pathlet = Pathlet(
        pathlet_id="pathlet_1",
        body=body,
        tail=tail
    )
"""

from dataclasses import dataclass, field
from typing import List, Optional

from .state import StateLabel


@dataclass
class Observation:
    """核心网络观测模型（领域对象）

    字段命名约定：{metric}_{direction}
    - direction: 'up' (client→server), 'down' (server→client)
    - metric: 'delay' (ms), 'loss' (0~1), 'bw' (Mbps)

    注意：此模型独立于任何具体数据源（如 HoloWAN），
    适配逻辑在 io/adapters/ 中实现。

    Attributes:
        delay_up: 上行延迟 (ms)
        delay_down: 下行延迟 (ms)
        loss_up: 上行丢包率
        loss_down: 下行丢包率
        bw_up: 上行带宽 (Mbps)
        bw_down: 下行带宽 (Mbps)

    Examples:
        # 创建观测数据
        obs = Observation(
            delay_up=10.5,
            delay_down=8.2,
            loss_up=0.01,
            loss_down=0.005,
            bw_up=50.0,
            bw_down=100.0
        )
    """

    delay_up: float = 0.0
    """上行延迟 (ms)"""
    delay_down: float = 0.0
    """下行延迟 (ms)"""
    loss_up: float = 0.0
    """上行丢包率"""
    loss_down: float = 0.0
    """下行丢包率"""
    bw_up: float = 0.0
    """上行带宽 (Mbps)"""
    bw_down: float = 0.0
    """下行带宽 (Mbps)"""


@dataclass
class BodyObservations:
    """主体观测数据序列（100个观元）

    包含径元的主体部分，由100个连续的观测数据组成。

    Attributes:
        observations: 观测数据列表

    Examples:
        # 创建主体观测数据
        body = BodyObservations(
            observations=[Observation()] * 100
        )
    """

    observations: List[Observation] = field(default_factory=list)
    """观测数据列表，长度为100"""


@dataclass
class TailObservations:
    """融尾观测数据序列（10个观元）

    包含径元的融合尾部，由10个连续的观测数据组成，用于径元之间的平滑过渡。

    Attributes:
        observations: 观测数据列表

    Examples:
        # 创建融尾观测数据
        tail = TailObservations(
            observations=[Observation()] * 10
        )
    """

    observations: List[Observation] = field(default_factory=list)
    """观测数据列表，长度为10"""


@dataclass
class Pathlet:
    """径元

    径元是网络轨迹的基本构建块，由主体和融尾组成。

    Attributes:
        pathlet_id: 径元 ID
        body: 主体观测数据
        tail: 融尾观测数据
        state_label: 状态标签（可选）

    Examples:
        # 创建径元
        pathlet = Pathlet(
            pathlet_id="pathlet_1",
            body=BodyObservations(),
            tail=TailObservations()
        )
    """

    pathlet_id: str
    """径元 ID"""
    body: BodyObservations
    """主体观测数据"""
    tail: TailObservations
    """融尾观测数据"""
    state_label: Optional[StateLabel] = None
    """状态标签（可选）"""

