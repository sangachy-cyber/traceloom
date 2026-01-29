# -*- coding: utf-8 -*-
"""编织引擎模块

包含各种编织引擎的实现和选择逻辑
"""

from traceloom.domain.pattern import Pattern
from traceloom.weaving.engines.dreamer import Dreamer
from traceloom.weaving.engines.reweaver.reweaver import Reweaver
from traceloom.weaving.engines.stitcher import Stitcher


def select_engine(pattern: Pattern):
    """根据织样选择合适的编织引擎

    参数:
        pattern: 织样对象

    返回:
        选择的编织引擎实例
    """
    # 根据设计文档实现引擎选择逻辑
    # 1. 包含 `->` 且基于单 trace 重放 → Reweaver
    # 2. 包含多个 trace 标识（如 `t0`, `t1`） → Stitcher
    # 3. 完全由参数生成（如 `gaussian(delay=50, loss=0.1)`） → Dreamer

    weaving_pattern = pattern.to_string()

    # 检查是否包含 `->` 符号
    if "->" in weaving_pattern:
        return Reweaver()
    # 检查是否包含多个 trace 标识
    elif any(f"t{i}" in weaving_pattern for i in range(10)):
        return Stitcher()
    # 检查是否包含参数生成模式
    elif any(func in weaving_pattern for func in ["gaussian", "uniform", "poisson"]):
        return Dreamer()
    # 默认使用 Dreamer
    else:
        return Dreamer()


__all__ = [
    "Dreamer",
    "Stitcher",
    "Reweaver",
    "select_engine",
]
