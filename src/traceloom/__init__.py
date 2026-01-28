# -*- coding: utf-8 -*-
"""TraceLoom（织径）
从真实轨迹中，织就可编程之径。

以实为丝，以律为梭，织就可编程之径
不生成流量 —— 而是生成 App 信以为真的网络路径。
"""

import sys

__version__ = "0.1.0"
__author__ = "TraceLoom Team"
__description__ = "Weaving programmable paths from real traces"

# 导入核心组件
from traceloom.domain.pattern import Pattern
from traceloom.weaving.engine import WeavingEngine

# 创建默认的 WeavingEngine 实例
weaving_engine = WeavingEngine()

# 核心织径函数
def reweave(input_file: str, output: str = "output.txt") -> dict:
    """重织：从真实 HoloWAN 文件提取并重组路径（【故径】）。

    参数:
        input_file (str): 真实 HoloWAN 文件路径
        output (str or Path, optional): 输出文件路径，默认为"output.txt"

    返回:
        dict: 包含路径信息的字典
    """
    # 读取输入文件
    with open(input_file, 'r') as f:
        content = f.read()

    # 使用 WeavingEngine 进行重织
    result = weaving_engine.weave(content, mode="reweave")

    # 保存结果
    weaving_engine.save_result(result, output)

    return result

def embroider(input_pattern: str, output: str = "output.txt") -> dict:
    """绣织：按织样构造高质量路径（【质径】）。

    参数:
        input_pattern (str): 织样字符串，支持两种格式：
            - 紧凑文本格式："s0x2 -> s2x6"（状态名x时长倍数，时长倍数×10=实际秒数）
            - JSON格式：'[{"state": "s0", "duration": 20}, {"state": "s2", "duration": 60}]'
        output (str or Path, optional): 输出文件路径，默认为"output.txt"

    返回:
        dict: 包含路径信息的字典
    """
    # 使用 WeavingEngine 进行绣织
    result = weaving_engine.weave(input_pattern, mode="stitch")

    # 保存结果
    weaving_engine.save_result(result, output)

    return result

def dream(input_pattern: str, output: str = "output.txt") -> dict:
    """广织：生成全新的虚拟路径（【幻径】）。

    参数:
        input_pattern (str): 织样字符串，格式同 embroider 函数
        output (str or Path, optional): 输出文件路径，默认为"output.txt"

    返回:
        dict: 包含路径信息的字典
    """
    # 使用 WeavingEngine 进行广织
    result = weaving_engine.weave(input_pattern, mode="dream")

    # 保存结果
    weaving_engine.save_result(result, output)

    return result

# 支持 traceloom 别名
__all__ = ["reweave", "embroider", "dream", "Pattern", "WeavingEngine"]

# 实现 traceloom 别名
# 获取当前模块对象
current_module = sys.modules[__name__]

# 创建 tl 模块别名
sys.modules["tl"] = current_module
