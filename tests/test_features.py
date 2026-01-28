#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试特征提取功能
"""

import sys
from pathlib import Path

import numpy as np

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from traceloom.core.logger import setup_logger
from traceloom.domain.features import FeatureExtractor
from traceloom.domain.pathlet import Observation
from traceloom.domain.raw_trace import RawTraceSegment as RawProfile


def test_extract_16d_features():
    """测试16维特征提取"""
    # 初始化日志
    setup_logger()

    # 创建测试数据
    observations = []
    for _i in range(100):
        obs = Observation(
            delay_up=100.5,
            loss_up=0.01,
            bw_up=10.0,
            delay_down=100.5,
            loss_down=0.01,
            bw_down=10.0
        )
        observations.append(obs)

    # 初始化特征提取器
    extractor = FeatureExtractor()

    # 测试提取16d特征
    features = extractor.extract_features(observations)
    assert features.shape == (16,), f"特征维度不正确，期望16维，实际{features.shape[0]}维"

    print("✅ 16维特征提取测试通过")


def test_extract_features_with_raw_profile():
    """测试从 RawProfile 提取特征"""
    # 初始化日志
    setup_logger()

    # 创建测试数据
    observations = []
    for _i in range(110):
        obs = Observation(
            delay_up=100.5,
            loss_up=0.01,
            bw_up=10.0,
            delay_down=100.5,
            loss_down=0.01,
            bw_down=10.0
        )
        observations.append(obs)

    # 创建 RawProfile
    raw_profile = RawProfile(
        trace_name="test_trace",
        start_index=0,
        observations=observations,
        is_valid=True
    )

    # 初始化特征提取器
    extractor = FeatureExtractor()

    # 测试从 RawProfile 提取特征
    features = extractor.extract_features(raw_profile.observations)
    assert features.shape == (16,), f"从 RawProfile 提取的特征维度不正确，期望16维，实际{features.shape[0]}维"

    print("✅ 从 RawProfile 提取特征测试通过")





def test_extract_features_batch():
    """测试批量特征提取"""
    # 初始化日志
    setup_logger()

    # 创建多个测试观察列表
    observations_list = []
    for i in range(5):
        observations = []
        for _j in range(100):
            obs = Observation(
                delay_up=100.5 + i,
                loss_up=0.01 + i * 0.001,
                bw_up=10.0 + i,
                delay_down=100.5 + i,
                loss_down=0.01 + i * 0.001,
                bw_down=10.0 + i
            )
            observations.append(obs)
        observations_list.append(observations)

    # 初始化特征提取器
    extractor = FeatureExtractor()

    # 测试批量特征提取
    batch_features = extractor.extract_features_batch(observations_list)
    assert batch_features.shape == (5, 16), f"批量特征形状不正确，期望(5, 16)，实际{batch_features.shape}"

    # 验证每个特征向量与单独提取的结果一致
    for i, observations in enumerate(observations_list):
        single_feature = extractor.extract_features(observations)
        assert np.allclose(batch_features[i], single_feature), f"第{i}个样本的批量提取结果与单独提取结果不一致"

    print("✅ 批量特征提取测试通过")











if __name__ == "__main__":
    test_extract_16d_features()
    test_extract_features_with_raw_profile()
    test_extract_features_batch()
    print("\n🎉 所有特征提取测试通过！")
