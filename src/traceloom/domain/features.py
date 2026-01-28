# -*- coding: utf-8 -*-
"""特征提取模块.

定义网络状态特征提取逻辑，提供统一的特征提取接口。
"""

from typing import List

import numpy as np

from .pathlet import Observation


class FeatureExtractor:
    """特征提取器.

    从观测数据列表中提取网络状态特征。
    """

    @staticmethod
    def extract_features(observations: List[Observation]) -> np.ndarray:
        """从观测数据列表中提取特征.

        参数:
            observations: 观测数据列表

        返回:
            np.ndarray: 特征向量
        """
        if not observations:
            return np.zeros(16)  # 返回全零特征向量

        features = []

        # 处理每个方向（上行和下行）
        for direction in ["up", "down"]:
            # 提取延迟和丢包数据
            delay_data = []
            loss_data = []

            for obs in observations:
                if direction == "up":
                    delay_data.append(obs.delay_up)
                    loss_data.append(obs.loss_up)
                else:
                    delay_data.append(obs.delay_down)
                    loss_data.append(obs.loss_down)

            # 延迟特征（4个）
            delay_log = np.log1p(delay_data)  # log(1 + x)
            delay_log_mean = np.mean(delay_log)
            delay_log_std = np.std(delay_log)
            delay_log_p95 = np.percentile(delay_log, 95)
            delay_log_max = np.max(delay_log)

            # 丢包特征（4个）
            loss_array = np.array(loss_data)
            has_loss = 1.0 if any(loss_array > 0) else 0.0

            # 条件丢包均值（仅当有丢包时）
            if has_loss > 0:
                cond_loss_mean = np.mean(loss_array[loss_array > 0])
            else:
                cond_loss_mean = 0.0

            loss_ratio = np.sum(loss_array > 0) / len(loss_array)
            loss_mean = np.mean(loss_array)

            # 添加当前方向8个特征
            features.extend(
                [
                    delay_log_mean,
                    delay_log_std,
                    delay_log_p95,
                    delay_log_max,
                    has_loss,
                    cond_loss_mean,
                    loss_ratio,
                    loss_mean,
                ]
            )

        return np.array(features)

    @staticmethod
    def extract_features_batch(observations_list: List[List[Observation]]) -> np.ndarray:
        """批量提取特征.

        参数:
            observations_list: 观测数据列表的列表

        返回:
            np.ndarray: 特征矩阵，形状为 (n_samples, 16)
        """
        return np.array([FeatureExtractor.extract_features(observations) for observations in observations_list])
