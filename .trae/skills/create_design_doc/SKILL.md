---
name: create_design_doc
description: 为新功能生成设计文档草稿（中文，含接口和示例）
---

Create a design document for "{{feature}}" under the docs/ directory.
  Include in Chinese:
  - 目标
  - 设计思路（可包含架构图、流程图等）
  - 函数/类接口（带类型注解）
  - 异常处理策略
  - 使用示例（与未来代码 docstring 一致）
  - 测试要点
  Save as docs/{{filename}}.md where {{filename}} is based on the feature name.
inputs:
  - name: feature
    description: 功能描述（中文，如“用户登录验证”）
  - name: filename
    description: 文件名（默认为功能名的小写短横线格式，如 user-login-validation）
    default: ""