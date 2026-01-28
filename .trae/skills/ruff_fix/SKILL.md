---
name: ruff_fix
description: 运行 ruff --fix 并总结修复项
---

Run: uv run ruff check --fix .
Then summarize what was fixed in Chinese, including any complexity (C901) or style issues resolved.
command: uv run ruff check --fix .