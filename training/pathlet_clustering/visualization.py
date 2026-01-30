# -*- coding: utf-8 -*-
"""可视化工具

实现 t-SNE 可视化和其他聚类相关的可视化功能。

示例:
    from training.pathlet_clustering.visualization import TSNEVisualizer
    from pathlib import Path
    import numpy as np

    # 创建可视化工具
    visualizer = TSNEVisualizer(n_components=2, perplexity=30)

    # 生成示例数据
    features = [np.random.rand(24) for _ in range(100)]
    labels = [0, 1, 2] * 34  # 示例标签
    probabilities = [0.9, 0.8, 0.7] * 34  # 示例置信度

    # 状态元数据
    state_metadata = {
        "states": [
            {"state_id": 0, "state_name": "稳定", "type": "pure"},
            {"state_id": 1, "state_name": "抖动", "type": "pure"},
            {"state_id": 2, "state_name": "异常", "type": "pure"}
        ]
    }

    # 生成 t-SNE 可视化
    output_path = Path("./visualization_tsne.png")
    visualizer.visualize(features, labels, state_metadata, output_path, probabilities, method='tsne')
    print(f"t-SNE 可视化已保存到: {output_path}")

    # 尝试生成 UMAP 可视化
    try:
        output_path_umap = Path("./visualization_umap.png")
        visualizer.visualize(features, labels, state_metadata, output_path_umap, probabilities, method='umap')
        print(f"UMAP 可视化已保存到: {output_path_umap}")
    except ImportError as e:
        print(f"UMAP 可视化失败: {e}")
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.cm import get_cmap
from sklearn.manifold import TSNE
from umap import UMAP

from traceloom.core.logger import logger
from traceloom.core.utils import setup_chinese_font

# 设置中文字体
setup_chinese_font()


class TSNEVisualizer:
    """t-SNE 可视化工具

    使用 t-SNE 算法进行降维可视化
    """

    def __init__(self, n_components: int = 2, perplexity: int = 30, random_state: int = 42):
        """初始化 t-SNE 可视化工具

        Args:
            n_components: 降维后的维度
            perplexity: t-SNE 的困惑度参数
            random_state: 随机种子

        Examples:
            # 初始化可视化工具
            visualizer = TSNEVisualizer(n_components=2, perplexity=30)
            print(f"可视化工具初始化完成，困惑度: {visualizer.perplexity}")
        """
        self.n_components = n_components
        self.perplexity = perplexity
        self.random_state = random_state

    @staticmethod
    def _get_color_mapping(state_names: List[str]) -> Dict[str, Any]:
        """根据状态名自动生成颜色映射

        Args:
            state_names: 状态名列表

        Returns:
            Dict[str, Any]: 状态名到颜色的映射

        Examples:
            # 生成颜色映射
            state_names = ["稳定", "抖动", "异常"]
            color_map = visualizer._get_color_mapping(state_names)
            print(f"生成的颜色映射: {color_map}")
        """
        unique_states = sorted(set(state_names))
        n_colors = len(unique_states)
        cmap = get_cmap("tab10" if n_colors <= 10 else "tab20")
        return {state: cmap(i / max(1, n_colors - 1)) for i, state in enumerate(unique_states)}

    def visualize(
        self,
        features: List[np.ndarray],
        labels: List[int],
        state_metadata: Dict[str, Any],
        output_path: Path,
        probabilities: Optional[List[float]] = None,
        method: str = "tsne",
    ) -> None:
        """生成降维可视化

        Args:
            features: 特征列表
            labels: 标签列表
            state_metadata: 状态元数据
            output_path: 输出路径
            probabilities: 置信度列表
            method: 降维方法，可选值: 'tsne' 或 'umap'

        Raises:
            ValueError: 特征数量和标签数量不匹配时抛出
            ValueError: 概率值数量和特征数量不匹配时抛出
            ValueError: 不支持的降维方法时抛出
            ImportError: UMAP 库不可用时抛出

        Examples:
            # 生成 t-SNE 可视化
            visualizer.visualize(features, labels, state_metadata, output_path, probabilities, method='tsne')
            print(f"t-SNE 可视化已保存到: {output_path}")
        """
        # 转换特征为 numpy 数组
        features = np.array(features)
        labels = np.array(labels)

        # 检查输入维度
        if features.shape[0] != labels.shape[0]:
            raise ValueError("特征数量和标签数量不匹配")

        # 检查概率值维度
        if probabilities is not None and len(probabilities) != features.shape[0]:
            raise ValueError("概率值数量和特征数量不匹配")

        # 执行降维
        if method == "tsne":
            logger.info(f"执行 t-SNE 降维，特征维度: {features.shape}")
            tsne = TSNE(
                n_components=self.n_components,
                perplexity=self.perplexity,
                random_state=self.random_state,
                init="pca",
                learning_rate="auto",
            )
            result = tsne.fit_transform(features)
        elif method == "umap":
            if UMAP is None:
                raise ImportError("UMAP 库不可用，请先安装 umap-learn 包")
            logger.info(f"执行 UMAP 降维，特征维度: {features.shape}")
            umap = UMAP(n_components=self.n_components, random_state=self.random_state, n_neighbors=15, min_dist=0.1)
            result = umap.fit_transform(features)
        else:
            raise ValueError(f"不支持的降维方法: {method}，可选值: 'tsne' 或 'umap'")

        # 生成可视化
        self._plot_embedding(result, labels, state_metadata, output_path, probabilities, method)

    def _plot_embedding(
        self,
        embedding_result: np.ndarray,
        labels: np.ndarray,
        state_metadata: Dict[str, Any],
        output_path: Path,
        probabilities: Optional[np.ndarray] = None,
        method: str = "tsne",
    ) -> None:
        """绘制降维结果

        Args:
            embedding_result: 降维结果
            labels: 标签列表
            state_metadata: 状态元数据
            output_path: 输出路径
            probabilities: 置信度列表
            method: 降维方法，可选值: 'tsne' 或 'umap'

        Examples:
            # 绘制降维结果
            # 注意：此方法通常由 visualize 方法内部调用
            visualizer._plot_embedding(result, labels, state_metadata, output_path, probabilities, method='tsne')
        """

        # 创建画布
        plt.figure(figsize=(10, 8))

        # 获取状态信息
        state_info = self._get_state_info(state_metadata, labels)

        # 绘制散点图
        self._plot_scatter(embedding_result, labels, state_info, probabilities)

        # 添加标题和图例
        self._add_plot_details(method)

        # 保存图像
        self._save_plot(output_path, method)

    def _get_state_info(self, state_metadata: Dict[str, Any], labels: np.ndarray) -> Dict[str, Any]:
        """获取状态信息

        Args:
            state_metadata: 状态元数据
            labels: 标签列表

        Returns:
            Dict[str, Any]: 状态信息，包含状态名、颜色和是否为纯状态
        """
        state_names = {}
        state_colors = {}
        state_is_pure = {}

        if "states" in state_metadata:
            for state in state_metadata["states"]:
                if "state_id" in state:
                    state_names[state["state_id"]] = state.get("state_name", f"状态_{state['state_id']}")
                    state_colors[state["state_id"]] = state.get("color", None)
                    state_is_pure[state["state_id"]] = state.get("type", "pure") == "pure"
        else:
            # 默认状态信息
            unique_labels = np.unique(labels)
            for label in unique_labels:
                state_names[label] = f"状态_{label}"
                state_is_pure[label] = True

        # 生成状态名到颜色的映射（如果没有提供颜色）
        if not state_colors:
            state_name_list = [state_names.get(label, f"状态_{label}") for label in np.unique(labels)]
            color_map = self._get_color_mapping(state_name_list)
            for label in np.unique(labels):
                state_name = state_names.get(label, f"状态_{label}")
                state_colors[label] = color_map[state_name]

        return {"state_names": state_names, "state_colors": state_colors, "state_is_pure": state_is_pure}

    @staticmethod
    def _plot_scatter(
        embedding_result: np.ndarray,
        labels: np.ndarray,
        state_info: Dict[str, Any],
        probabilities: Optional[np.ndarray] = None,
    ) -> None:
        """绘制散点图

        Args:
            embedding_result: 降维结果
            labels: 标签列表
            state_info: 状态信息
            probabilities: 置信度列表
        """
        state_names = state_info["state_names"]
        state_colors = state_info["state_colors"]
        state_is_pure = state_info["state_is_pure"]

        for label in np.unique(labels):
            mask = labels == label
            state_name = state_names.get(label, f"状态_{label}")
            color = state_colors.get(label, (0.5, 0.5, 0.5, 1.0))  # 默认灰色
            is_pure = state_is_pure.get(label, True)

            # 计算透明度
            if probabilities is not None:
                # 对当前标签的所有点计算平均置信度
                avg_prob = np.mean(np.array(probabilities)[mask])
                alpha = min(1.0, avg_prob * 1.2)
            else:
                alpha = 0.6

            # 绘制散点
            scatter = plt.scatter(
                embedding_result[mask, 0], embedding_result[mask, 1], c=color, label=state_name, alpha=alpha, s=50
            )

            # 非纯状态添加灰色细边框
            if not is_pure:
                scatter.set_edgecolor("gray")
                scatter.set_linewidth(0.5)

    @staticmethod
    def _add_plot_details(method: str) -> None:
        """添加图表细节

        Args:
            method: 降维方法
        """
        if method == "tsne":
            plt.title("网络状态聚类 t-SNE 可视化", fontsize=16)
            plt.xlabel("t-SNE 维度 1", fontsize=12)
            plt.ylabel("t-SNE 维度 2", fontsize=12)
        else:  # umap
            plt.title("网络状态聚类 UMAP 可视化", fontsize=16)
            plt.xlabel("UMAP 维度 1", fontsize=12)
            plt.ylabel("UMAP 维度 2", fontsize=12)
        plt.legend(fontsize=10)
        plt.grid(True, alpha=0.3)

    @staticmethod
    def _save_plot(output_path: Path, method: str) -> None:
        """保存图表

        Args:
            output_path: 输出路径
            method: 降维方法
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        logger.info(f"{method.upper()} 可视化已保存到: {output_path}")

    def visualize_pathlets(self, pathlets: List, clusterer, output_path: Path) -> None:
        """可视化径元聚类结果

        Args:
            pathlets: 径元列表
            clusterer: 聚类器实例
            output_path: 输出路径

        Examples:
            # 可视化径元聚类结果
            visualizer.visualize_pathlets(pathlets, clusterer, output_path)
            print(f"径元聚类可视化已保存到: {output_path}")
        """
        from training.pathlet_clustering.gmm_clusterer import GMMClusterer

        # 提取特征和标签
        features = []
        labels = []
        probabilities = []

        for pathlet in pathlets:
            # 提取特征
            feature = GMMClusterer.extract_features(pathlet.body.observations)
            features.append(feature)

            # 预测标签
            if hasattr(clusterer, "predict"):
                # 注意：这里需要根据聚类器的实际接口调整
                prediction = clusterer.predict([pathlet])[0]
                label = prediction.state_id
                labels.append(label)
                probabilities.append(prediction.confidence)
            else:
                labels.append(0)  # 默认标签
                probabilities.append(0.5)  # 默认置信度

        # 生成状态元数据
        state_metadata = {
            "states": [
                {"state_id": 0, "state_name": "稳定", "type": "pure"},
                {"state_id": 1, "state_name": "抖动", "type": "pure"},
                {"state_id": 2, "state_name": "异常", "type": "pure"},
            ]
        }

        # 执行可视化
        self.visualize(features, labels, state_metadata, output_path, probabilities)
