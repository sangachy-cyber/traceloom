---
name: add_test
description: 为指定函数生成 pytest 测试（含中文注释、异常覆盖）
---

Generate a pytest test file for the function/class "{{target}}".
  - Test normal cases, edge cases, and error cases (where exceptions should be raised)
  - Use parametrize when applicable
  - Add Chinese comments explaining each test case
  - Import from loguru only if needed; focus on pure test logic
  - Save to tests/test_{{filename}}.py
inputs:
  - name: target
    description: 要测试的函数或类名（如 calculate_tax）
  - name: filename
    description: 测试文件名（如 test_tax.py 中的 tax）