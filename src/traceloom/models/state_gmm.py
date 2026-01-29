# -*- coding: utf-8 -*-
"""GMM 模型

实现 GMM 模型，支持训练和推理，包含与训练侧完全一致的特征提取逻辑。
"""

from pathlib import Path
from typing import List, Optional

import joblib
import numpy as np
import warnings
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from sklearn.exceptions import ConvergenceWarning

from traceloom.core.logger import logger
from traceloom.domain.pathlet import Observation, Pathlet
from traceloom.domain.state import StateLabel


# 忽略GMM收敛警告
warnings.filterwarnings("ignore", category=ConvergenceWarning)


class StateGMM:
    """GMM 模型

    实现 GMM 模型，支持训练和推理，包含与训练侧完全一致的特征提取逻辑。
    """

    def __init__(
        self,
        n_components: int = 3,
        confidence_threshold: float = 0.85,
        random_state: int = 42,
        model_path: Optional[Path] = None,
    ):
        """初始化 GMM 模型

        参数:
            n_components: 聚类数量
            confidence_threshold: 置信度阈值
            random_state: 随机种子
            model_path: 模型路径
        """
        self.n_components = n_components
        self.confidence_threshold = confidence_threshold
        self.random_state = random_state
        self.gmm: Optional[GaussianMixture] = None
        self.scaler: Optional[StandardScaler] = None
        self._is_loaded = False
        self._is_fit = False
        self._features: Optional[np.ndarray] = None  # 保存拟合时的特征
        self._labels: Optional[np.ndarray] = None  # 保存拟合时的标签

        if model_path:
            self.load(model_path)
        else:
            self.gmm = GaussianMixture(n_components=n_components, random_state=random_state)
            self.scaler = StandardScaler()

    @staticmethod
    def extract_features(observations: List[Observation]) -> np.ndarray:
        """提取观测数据的特征

        实现与训练侧完全一致的 16 维特征提取逻辑，对每个方向（上行/下行）生成 8 维特征向量。

        参数:
            observations: 观测数据列表

        返回:
            np.ndarray: 16 维特征向量
        """
        if not observations:
            return np.zeros(16)

        # 提取上行和下行的延迟、丢包
        delay_up = np.array([obs.delay_up for obs in observations])
        loss_up = np.array([obs.loss_up for obs in observations])
        delay_down = np.array([obs.delay_down for obs in observations])
        loss_down = np.array([obs.loss_down for obs in observations])

        # 计算每个方向的 8 维特征
        def compute_direction_features(delay, loss):
            # 步骤 1：对延迟进行 log 变换
            delay_log = np.log(delay + 1)

            # 步骤 2：从 delay_log 提取 4 个延迟特征
            delay_log_mean = np.mean(delay_log)
            delay_log_std = np.std(delay_log, ddof=1)
            delay_log_p95 = np.percentile(delay_log, 95)
            delay_log_max = np.max(delay_log)

            # 步骤 3：从原始丢包率提取 4 个丢包特征
            has_loss = 1 if np.any(loss > 0) else 0
            cond_loss_mean = np.mean(loss[loss > 0]) if np.any(loss > 0) else 0.0
            loss_ratio = np.sum(loss > 0) / len(loss)
            loss_mean = np.mean(loss)

            return [
                delay_log_mean,
                delay_log_std,
                delay_log_p95,
                delay_log_max,
                has_loss,
                cond_loss_mean,
                loss_ratio,
                loss_mean,
            ]

        # 计算上行和下行的特征
        up_features = compute_direction_features(delay_up, loss_up)
        down_features = compute_direction_features(delay_down, loss_down)

        # 构建 16 维特征向量
        features = np.array(up_features + down_features)

        return features

    def fit(self, pathlets: List[Pathlet]) -> None:
        """拟合 GMM 模型

        参数:
            pathlets: 径元列表
        """
        if not pathlets:
            raise ValueError("输入的 pathlets 列表不能为空")

        # 提取特征
        features = []
        for pathlet in pathlets:
            # 从主干观测数据中提取特征
            observations = pathlet.body.observations
            feature = self.extract_features(observations)
            features.append(feature)

        features = np.array(features)

        # 缩放特征
        features = self.scaler.fit_transform(features)

        # 拟合 GMM 模型
        if self.gmm:
            self.gmm.fit(features)
            # 保存特征和标签，用于后续分析
            self._features = features
            self._labels = self.gmm.predict(features)
            self._is_fit = True
            self._is_loaded = True
            logger.info(f"GMM 模型拟合完成，n_components={self.n_components}")
        else:
            raise ValueError("GMM 模型未初始化")

    def predict(self, observations: List[Observation]) -> StateLabel:
        """预测观测数据的状态

        参数:
            observations: 观测数据列表

        返回:
            StateLabel: 状态标签
        """
        if not self._is_loaded and not self._is_fit:
            raise ValueError("模型尚未加载或拟合，请先调用 load 或 fit 方法")

        # 提取特征
        features = self.extract_features(observations)
        features = features.reshape(1, -1)

        # 缩放特征
        if self.scaler:
            features = self.scaler.transform(features)

        # 预测状态
        if self.gmm:
            prediction = self.gmm.predict(features)[0]
            probabilities = self.gmm.predict_proba(features)[0]
            confidence = max(probabilities)

            return StateLabel(state_id=prediction, confidence=confidence)
        else:
            raise ValueError("GMM 模型未初始化")

    def save(self, model_path: Path) -> None:
        """保存模型

        参数:
            model_path: 模型路径
        """
        if not self.gmm or not self.scaler:
            raise ValueError("模型尚未加载或初始化")

        model_data = {
            "n_components": self.n_components,
            "confidence_threshold": self.confidence_threshold,
            "random_state": self.random_state,
            "gmm": self.gmm,
            "scaler": self.scaler,
            "_is_fit": self._is_fit,
        }

        model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model_data, model_path)

        logger.info(f"GMM 模型保存到: {model_path}")

    def load(self, model_path: Path) -> None:
        """加载模型

        参数:
            model_path: 模型路径
        """
        if not model_path.exists():
            raise FileNotFoundError(f"模型文件不存在: {model_path}")

        model_data = joblib.load(model_path)
        self.gmm = model_data["gmm"]
        self.scaler = model_data["scaler"]
        self.n_components = model_data["n_components"]
        self.confidence_threshold = model_data["confidence_threshold"]
        self.random_state = model_data.get("random_state", 42)
        self._is_fit = model_data.get("_is_fit", False)
        self._is_loaded = True

        logger.info(f"GMM 模型从 {model_path} 加载完成")

    @property
    def is_loaded(self) -> bool:
        """模型是否已经加载

        返回:
            bool: 模型是否已经加载
        """
        return self._is_loaded

    @property
    def is_fit(self) -> bool:
        """模型是否已经拟合

        返回:
            bool: 模型是否已经拟合
        """
        return self._is_fit
