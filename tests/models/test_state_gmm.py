# -*- coding: utf-8 -*-
"""测试StateGMM模型

测试 StateGMM 类的功能，包括特征提取、模型加载和预测。
"""

import tempfile
from pathlib import Path

import pytest

from traceloom.domain.pathlet import Observation
from traceloom.models.state_gmm import StateGMM


class TestStateGMM:
    """测试 StateGMM 类"""

    def setup_method(self):
        """设置测试环境"""
        self.model = StateGMM()
        self.test_observations = [
            Observation(delay_up=10.0, loss_up=0.01, bw_up=100.0, delay_down=12.0, loss_down=0.02, bw_down=120.0),
            Observation(delay_up=11.0, loss_up=0.01, bw_up=105.0, delay_down=13.0, loss_down=0.02, bw_down=125.0),
            Observation(delay_up=12.0, loss_up=0.02, bw_up=110.0, delay_down=14.0, loss_down=0.03, bw_down=130.0),
        ]

    def test_extract_features(self):
        """测试提取观测数据的特征"""
        features = StateGMM.extract_features(self.test_observations)
        assert features.shape == (16,)
        assert all(isinstance(f, float) for f in features)

    def test_extract_features_empty(self):
        """测试提取空观测数据的特征"""
        with pytest.raises(ValueError):
            StateGMM.extract_features([])

    def test_is_loaded_property(self):
        """测试 is_loaded 属性"""
        assert self.model.is_loaded is False

    def test_save_load(self):
        """测试保存和加载模型"""
        # 测试文件不存在的情况
        non_existent_path = Path("non_existent_model.joblib")
        with pytest.raises(FileNotFoundError):
            self.model.load(non_existent_path)

        # 测试保存方法（现在模型在初始化时会自动创建 gmm 和 scaler 对象）
        with tempfile.NamedTemporaryFile(suffix=".joblib", delete=False) as f:
            model_path = Path(f.name)

        try:
            # 现在保存方法不会失败，因为模型已经初始化了
            # 但是保存的模型可能不是训练好的模型
            self.model.save(model_path)
            assert model_path.exists()
            
            # 测试加载模型
            loaded_model = StateGMM()
            loaded_model.load(model_path)
            assert loaded_model.is_loaded is True
        finally:
            # 清理临时文件
            if model_path.exists():
                model_path.unlink()
