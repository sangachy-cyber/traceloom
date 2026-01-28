---
name: check_font_support
description: 生成跨平台中文字体配置代码（适配 Mac/Win/Linux）
---

Generate Python code to configure matplotlib (or other viz lib) 
  with fallback fonts for Chinese text:
  - macOS: PingFang SC
  - Windows: Microsoft YaHei
  - Linux: WenQuanYi Zen Hei
  Include a try-except to verify font availability and log warnings via loguru.