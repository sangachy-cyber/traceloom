# -*- coding: utf-8 -*-
"""测试模型加载功能"""

from traceloom.weaving.weaving_law import WeavingLawEngine
from pathlib import Path

# 使用一个不存在的模型路径
print("测试使用不存在的模型路径...")
try:
    weaving_law = WeavingLawEngine(model_path=Path("non_existent_model.pkl"))
    print("错误：模型加载失败，但程序继续执行了")
except FileNotFoundError as e:
    print(f"正确：模型加载失败，直接抛出异常：{e}")
except Exception as e:
    print(f"错误：模型加载失败，但抛出了其他异常：{e}")
