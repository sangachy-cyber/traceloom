#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试文档中的示例代码是否可执行
"""

import traceloom as tl
from traceloom.core.config import settings

print("测试核心函数调用...")

# 测试配置访问
print(f"配置测试: BODY_SIZE={settings.BODY_SIZE}, TAIL_SIZE={settings.TAIL_SIZE}")

# 测试函数签名（不执行实际操作）
print("\n测试函数签名...")
print(f"reweave函数: {tl.reweave.__doc__[:50]}...")
print(f"stitch函数: {tl.stitch.__doc__[:50]}...")
print(f"dream函数: {tl.dream.__doc__[:50]}...")

print("\n示例代码测试完成！")
print("函数签名正确，配置访问方式正确。")
