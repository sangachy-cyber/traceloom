# -*- coding: utf-8 -*-
"""路径聚类训练流水线脚本

运行完整的路径聚类训练流水线，包括数据加载、聚类、状态映射生成、可视化和结果保存。

示例:
    # 基本使用
    python scripts/run_pathlet_clustering.py

    # 自定义参数
    python scripts/run_pathlet_clustering.py --n-components 4 --confidence-threshold 0.9

    # 禁用可视化
    python scripts/run_pathlet_clustering.py --visualize false
"""

import sys
from pathlib import Path

import typer

# 添加项目根目录到Python搜索路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from traceloom.core.logger import logger
from training.pathlet_clustering.pipeline import run

# 创建Typer应用
app = typer.Typer(name="run_pathlet_clustering", help="运行路径聚类训练流水线", add_completion=False)


@app.command()
def main(
    n_components: int = typer.Option(3, "--n-components", "-n", help="聚类数量"),
    confidence_threshold: float = typer.Option(0.85, "--confidence-threshold", "-c", help="置信度阈值"),
    assign_test_states: bool = typer.Option(True, "--assign-test-states", "-a", help="是否为测试集分配状态"),
    visualize: bool = typer.Option(True, "--visualize", "-v", help="是否生成可视化"),
):
    """运行路径聚类训练流水线

    调用training/pathlet_clustering/pipeline.py中的run函数，执行完整的聚类训练流程。

    参数:
        n_components: 聚类数量
        confidence_threshold: 置信度阈值
        assign_test_states: 是否为测试集分配状态
        visualize: 是否生成可视化
    """
    try:
        # 显示运行参数
        logger.info("=" * 60)
        logger.info("路径聚类训练流水线启动")
        logger.info("=" * 60)
        logger.info("运行参数:")
        logger.info(f"  聚类数量: {n_components}")
        logger.info(f"  置信度阈值: {confidence_threshold}")
        logger.info(f"  为测试集分配状态: {assign_test_states}")
        logger.info(f"  生成可视化: {visualize}")
        logger.info("=" * 60)

        # 运行聚类训练流水线
        run(
            n_components=n_components,
            confidence_threshold=confidence_threshold,
            assign_test_states=assign_test_states,
            visualize=visualize,
        )

        logger.info("=" * 60)
        logger.info("路径聚类训练流水线完成!")
        logger.info("=" * 60)
        logger.info("训练结果已保存到以下位置:")
        logger.info("  - 状态元数据: data/after_label/state_metadata.json")
        logger.info("  - 训练集: data/after_label/train.csv")
        logger.info("  - 测试集: data/after_label/test.csv")
        logger.info("  - 聚类模型: data/models/gmm_model.joblib")
        logger.info("  - 状态映射: data/models/state_mapping.json")
        if visualize:
            logger.info("  - 可视化结果: data/after_label/clustering_gmm_tsne.png")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"运行过程中出现错误: {e}")
        logger.error("请检查输入参数和数据文件是否正确")
        logger.debug("详细错误信息:", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    app()
