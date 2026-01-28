---
name: update_docs
description: 根据代码变更建议更新 mkdocs 文档
---

Code changed in {{module}}.
Suggest which docs/ file(s) need update:
  - Architecture? → 01-architecture/
  - API? → 02-implementation/api-reference.md
  - Debugging? → 02-implementation/debugging-guide.md
  - New strategy? → 01-architecture/stages/{{stage}}.md
inputs:
  - name: module
    description: e.g., simcore.strategies.craft
  - name: stage
    description: replace / craft / explore