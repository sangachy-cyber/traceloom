---
name: add_function
description: 生成一个符合规范的 Python 函数（中文注释、Google 风格、含示例）
---

Create a Python function named "{{name}}" that {{purpose}}.
  - Use type hints
  - Add Google-style docstring in Chinese with "Args", "Returns", and "示例" sections
  - Use loguru for logging if needed
  - Raise exceptions on error (fail fast)
  - No unnecessary dependencies
inputs:
  - name: name
    description: 函数名
  - name: purpose
    description: 函数用途（中文描述）