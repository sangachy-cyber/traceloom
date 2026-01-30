# -*- coding: utf-8 -*-
"""测试GMM聚类器

测试 GMMClusterer 类的功能，包括特征提取、模型拟合和预测。
"""

import tempfile
import warnings
from pathlib import Path

import pytest
from sklearn.exceptions import ConvergenceWarning

from traceloom.domain.pathlet import BodyObservations, Observation, Pathlet, TailObservations
from traceloom.domain.state import StateLabel
from training.pathlet_clustering.gmm_clusterer import GMMClusterer

# 忽略GMM收敛警告
warnings.filterwarnings("ignore", category=ConvergenceWarning)


@pytest.mark.filterwarnings("ignore::sklearn.exceptions.ConvergenceWarning")
class TestGMMClusterer:
    """测试 GMMClusterer 类"""

    def setup_method(self):
        """设置测试环境"""
        self.clusterer = GMMClusterer(n_components=2, confidence_threshold=0.85)
        self.test_observations = [
            Observation(delay_up=10.0, loss_up=0.01, bw_up=100.0, delay_down=12.0, loss_down=0.02, bw_down=120.0),
            Observation(delay_up=11.0, loss_up=0.01, bw_up=105.0, delay_down=13.0, loss_down=0.02, bw_down=125.0),
            Observation(delay_up=12.0, loss_up=0.02, bw_up=110.0, delay_down=14.0, loss_down=0.03, bw_down=130.0),
        ]

    def test_extract_features(self):
        """测试提取观测数据的特征"""
        features = GMMClusterer.extract_features(self.test_observations)
        assert features.shape == (16,)
        assert all(isinstance(f, float) for f in features)

    def test_extract_features_empty(self):
        """测试提取空观测数据的特征"""
        features = GMMClusterer.extract_features([])
        assert features.shape == (16,)
        assert all(f == 0.0 for f in features)

    def test_fit_predict(self):
        """测试拟合和预测"""
        # 创建测试径元
        pathlets = []
        for i in range(5):
            pathlet = Pathlet(
                pathlet_id=f"test_{i}",
                body=BodyObservations(observations=self.test_observations),
                tail=TailObservations(observations=self.test_observations[:1]),
            )
            pathlets.append(pathlet)

        # 拟合模型
        self.clusterer.fit(pathlets)
        assert self.clusterer.is_fit is True

        # 预测
        predictions = self.clusterer.predict(pathlets)
        assert len(predictions) == 5
        assert all(isinstance(pred, StateLabel) for pred in predictions)

    def test_save_load(self):
        """测试保存和加载模型"""
        # 创建测试径元
        pathlets = []
        for i in range(5):
            pathlet = Pathlet(
                pathlet_id=f"test_{i}",
                body=BodyObservations(observations=self.test_observations),
                tail=TailObservations(observations=self.test_observations[:1]),
            )
            pathlets.append(pathlet)

        # 拟合模型
        self.clusterer.fit(pathlets)

        # 保存模型
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            model_path = temp_path / "gmm_model.joblib"
            self.clusterer.save(temp_path)

            # 验证文件存在
            assert model_path.exists()

            # 加载模型
            loaded_clusterer = GMMClusterer.load(model_path)
            assert loaded_clusterer.is_fit is True
            assert loaded_clusterer.n_components == self.clusterer.n_components

            # 测试加载后的模型是否可以预测
            predictions = loaded_clusterer.predict(pathlets)
            assert len(predictions) == 5

    def test_is_fit_property(self):
        """测试 is_fit 属性"""
        assert self.clusterer.is_fit is False

        # 创建测试径元并拟合（至少需要2个样本）
        pathlets = []
        for i in range(2):
            pathlet = Pathlet(
                pathlet_id=f"test_{i}",
                body=BodyObservations(observations=self.test_observations),
                tail=TailObservations(observations=self.test_observations[:1]),
            )
            pathlets.append(pathlet)
        self.clusterer.fit(pathlets)

        assert self.clusterer.is_fit is True
