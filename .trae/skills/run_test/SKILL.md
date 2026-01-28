---
name: run_test
description: 运行 pytest 并用中文总结结果（支持 uv）
---

Run: uv run pytest {{args}} -v
  If tests fail, explain the reason in Chinese and suggest fixes.
  If all pass, summarize coverage and key tested behaviors.
command: uv run pytest {{args}} -v
inputs:
  - name: args
    description: pytest 参数（如 tests/test_xxx.py::test_yyy，留空则运行全部）
    default: ""