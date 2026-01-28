---
name: create_module
description: 创建符合规范的 Python 模块（含中文文档、Ruff 兼容）
---

Create a new module named "{{module_name}}" under ./src/.
  Include:
  - __init__.py
  - {module_name}.py with a main class/function, Google-style Chinese docstring, "示例", type hints
  - Basic pytest placeholder in tests/
  - All comments/docstrings in Chinese
  - Use loguru, raise early on error
inputs:
  - name: module_name
    description: 模块名（如 data_processor）