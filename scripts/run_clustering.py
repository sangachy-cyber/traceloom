#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""聚类脚本
将 before_label/ 目录下的 CSV 文件转换为 after_label/ 目录下的带状态标注的 CSV 文件

示例:
    # 默认运行（GMM 3类，θ=0.85，t-SNE 可视化）
    uv run python scripts/run_clustering.py --assign-test-states

    # 自定义置信度阈值
    uv run python scripts/run_clustering.py --confidence-threshold 0.8
"""

import sys
from pathlib import Path

import typer

# 添加项目根目录到 Python 搜索路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from training.pathlet_clustering.pipeline import run as clustering_run

app = typer.Typer(help="LoomNet 聚类流水线", add_completion=False)


@app.command("run")
def run(
    n_components: int = typer.Option(3, help="聚类数量"),
    confidence_threshold: float = typer.Option(0.85, help="置信度阈值，用于区分纯净态和混合态"),
    assign_test_states: bool = typer.Option(True, help="是否为测试集分配状态"),
    visualize: bool = typer.Option(True, help="是否生成 t-SNE 可视化"),
):
    """运行聚类流水线"""
    clustering_run(n_components, confidence_threshold, assign_test_states, visualize)


if __name__ == "__main__":
    app()
