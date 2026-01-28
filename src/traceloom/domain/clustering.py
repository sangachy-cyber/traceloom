# -*- coding: utf-8 -*-
"""聚类模块

实现 GMM 聚类器和 t-SNE 可视化工具
"""

from pathlib import Path
from typing import Any, Dict, List

import matplotlib.pyplot as plt
import numpy as np
from sklearn.manifold import TSNE
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import RobustScaler

from traceloom.core.logger import logger
from traceloom.domain.features import FeatureExtractor


class GMMClusterer:
    """GMM 聚类器

    使用高斯混合模型进行聚类，支持置信度阈值设置
    """

    def __init__(self, n_components: int = 3, confidence_threshold: float = 0.85, random_state: int = 42):
        """初始化 GMM 聚类器

        参数:
            n_components: 聚类数量
            confidence_threshold: 置信度阈值
            random_state: 随机种子
        """
        self.n_components = n_components
        self.confidence_threshold = confidence_threshold
        self.random_state = random_state
        self.gmm = GaussianMixture(n_components=n_components, random_state=random_state)
        self.scaler = RobustScaler()
        self._is_fit = False

    def fit(self, profiles: list) -> None:
        """拟合 GMM 聚类器

        参数:
            profiles: 网络剖面列表，每个剖面应包含 observations 属性
        """
        if not profiles:
            raise ValueError("输入的 profiles 列表不能为空")

        # 提取特征
        features = []
        for profile in profiles:
            # 从观测数据中提取特征
            features.append(self._extract_features(profile))

        features = np.array(features)

        # 缩放特征
        features = self.scaler.fit_transform(features)

        # 拟合 GMM 模型
        self.gmm.fit(features)
        self._is_fit = True

    def predict(self, profiles: list) -> List[int]:
        """预测网络剖面的状态

        参数:
            profiles: 网络剖面列表

        返回:
            List[int]: 状态 ID 列表
        """
        if not self._is_fit:
            raise ValueError("模型尚未拟合，请先调用 fit 方法")

        # 提取特征
        features = []
        for profile in profiles:
            features.append(self._extract_features(profile))

        features = np.array(features)

        # 缩放特征
        features = self.scaler.transform(features)

        # 预测状态
        return self.gmm.predict(features).tolist()

    def predict_proba(self, profiles: list) -> List[List[float]]:
        """预测网络剖面的状态概率

        参数:
            profiles: 网络剖面列表

        返回:
            List[List[float]]: 状态概率列表，每个元素是一个概率向量
        """
        if not self._is_fit:
            raise ValueError("模型尚未拟合，请先调用 fit 方法")

        # 提取特征
        features = []
        for profile in profiles:
            features.append(self._extract_features(profile))

        features = np.array(features)

        # 缩放特征
        features = self.scaler.transform(features)

        # 预测状态概率
        return self.gmm.predict_proba(features).tolist()

    def _extract_features(self, profile) -> np.ndarray:
        """从网络剖面中提取特征

        参数:
            profile: 网络剖面

        返回:
            np.ndarray: 特征向量
        """
        extractor = FeatureExtractor()
        return extractor.extract_features(profile.observations)

    @property
    def is_fit(self) -> bool:
        """模型是否已经拟合

        返回:
            bool: 模型是否已经拟合
        """
        return self._is_fit


class TSNEVisualizer:
    """t-SNE 可视化工具

    使用 t-SNE 算法进行降维可视化
    """

    def __init__(self, n_components: int = 2, perplexity: int = 30, random_state: int = 42):
        """初始化 t-SNE 可视化工具

        参数:
            n_components: 降维后的维度
            perplexity: t-SNE 的困惑度参数
            random_state: 随机种子
        """
        self.n_components = n_components
        self.perplexity = perplexity
        self.random_state = random_state

    def visualize(self, features: List[np.ndarray], labels: List[int], state_metadata: Dict[str, Any], output_path: Path) -> None:
        """生成 t-SNE 可视化

        参数:
            features: 特征列表
            labels: 标签列表
            state_metadata: 状态元数据
            output_path: 输出路径
        """
        # 转换特征为 numpy 数组
        features = np.array(features)
        labels = np.array(labels)

        # 检查输入维度
        if features.shape[0] != labels.shape[0]:
            raise ValueError("特征数量和标签数量不匹配")

        # 执行 t-SNE 降维
        logger.info(f"执行 t-SNE 降维，特征维度: {features.shape}")
        tsne = TSNE(
            n_components=self.n_components,
            perplexity=self.perplexity,
            random_state=self.random_state,
            init='pca',
            learning_rate='auto'
        )
        tsne_result = tsne.fit_transform(features)

        # 生成可视化
        self._plot_tsne(tsne_result, labels, state_metadata, output_path)

    def _plot_tsne(self, tsne_result: np.ndarray, labels: np.ndarray, state_metadata: Dict[str, Any], output_path: Path) -> None:
        """绘制 t-SNE 结果

        参数:
            tsne_result: t-SNE 降维结果
            labels: 标签列表
            state_metadata: 状态元数据
            output_path: 输出路径
        """
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

        # 创建画布
        plt.figure(figsize=(10, 8))

        # 获取状态信息
        state_names = {}
        if 'states' in state_metadata:
            for state in state_metadata['states']:
                if 'state_id' in state and 'state_name' in state:
                    state_names[state['state_id']] = state['state_name']
        else:
            # 默认状态名称
            state_names = {0: "稳定", 1: "抖动", 2: "异常"}

        # 绘制散点图
        unique_labels = np.unique(labels)
        colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6']

        for i, label in enumerate(unique_labels):
            mask = labels == label
            color = colors[i % len(colors)]
            plt.scatter(
                tsne_result[mask, 0],
                tsne_result[mask, 1],
                c=color,
                label=state_names.get(label, f"状态_{label}"),
                alpha=0.6,
                s=50
            )

        # 添加标题和图例
        plt.title('网络状态聚类 t-SNE 可视化', fontsize=16)
        plt.xlabel('t-SNE 维度 1', fontsize=12)
        plt.ylabel('t-SNE 维度 2', fontsize=12)
        plt.legend(fontsize=10)
        plt.grid(True, alpha=0.3)

        # 保存图像
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"t-SNE 可视化已保存到: {output_path}")
