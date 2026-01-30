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
from traceloom.core.utils import setup_chinese_font
from traceloom.domain.features import GMMFeatureExtractor


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

    @staticmethod
    def _extract_features(profile) -> np.ndarray:
        """从网络剖面中提取特征

        参数:
            profile: 网络剖面

        返回:
            np.ndarray: 特征向量
        """
        extractor = GMMFeatureExtractor()
        return extractor.extract_features(profile.observations)

    @property
    def is_fit(self) -> bool:
        """模型是否已经拟合

        返回:
            bool: 模型是否已经拟合
        """
        return self._is_fit
