# TraceLoom 规则

- 业务逻辑仅在src/traceloom/；scripts/无业务，只串接。
- 所有配置（含目录路径）用Pydantic Settings集中于src/traceloom/core/config.py，UPPER_SNAKE_CASE。
- scripts/中路径必须从config读取，禁止硬编码。
- 临时文件必须写入tmp/目录，禁止在项目根目录或其他位置创建临时文件。
- 图表用中文，时延0-2000ms，丢包率-0.01～1.01，输出到settings.OUTPUT_DIR。
- 日志与中文字体设置已封装，必须调用core中的公共函数，禁止重复实现。
- 新模块测试覆盖100%，整体≥80%。
- 异常定义在core/exceptions.py，日志用loguru。
- 所有设计文档由mkdocs管理于docs/；修改代码前，须同步更新对应文档（如架构、接口或调试指南）。
- 使用 uv 管理依赖，所有依赖在pyproject.toml中声明。
- 项目处于早期阶段，不用考虑兼容性。
- 所有代码必须符合PEP 8规范。