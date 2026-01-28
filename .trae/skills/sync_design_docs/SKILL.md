---
name: sync_design_docs
description: 检查代码变更是否需要更新 doc/ 下的相关设计文档，并生成建议
---

Compare the current code changes (git diff) with all files under doc/.
  If logic, interface, or behavior has changed and affects any design document:
    - Highlight mismatches in Chinese
    - Suggest updated content for affected documents
  If no relevant design document exists but significant logic is added, suggest creating one.
command: git diff --name-only