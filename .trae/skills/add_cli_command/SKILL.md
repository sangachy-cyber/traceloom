---
name: add_cli_command
description: 为 Typer CLI 添加新命令（中文提示、loguru 日志）
---

Add a new Typer command named "{{cmd_name}}" that {{desc}}.
  - Print user messages in Chinese
  - Use loguru for internal logging
  - Handle errors by raising ClickException or typer.Exit
  - Ensure cross-platform compatibility
inputs:
  - name: cmd_name
    description: 命令名称（如 export_data）
  - name: desc
    description: 命令功能描述（中文）