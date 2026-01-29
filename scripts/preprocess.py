#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""预处理脚本
将原始 HoloWAN .txt 日志转换为 before_label/ 目录下的 CSV 文件

示例:
    uv run python scripts/preprocess.py
"""

import sys
from pathlib import Path

import typer

# 添加项目根目录到 Python 搜索路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from training.pathlet_clustering.preprocessor import Preprocessor

app = typer.Typer(help="LoomNet 预处理流水线", add_completion=False)


@app.command("run")
def run():
    """运行预处理流水线"""
    Preprocessor().run()


if __name__ == "__main__":
    app()
