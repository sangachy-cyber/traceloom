# -*- coding: utf-8 -*-
"""验证模块测试"""

import pytest
from unittest.mock import MagicMock

from traceloom.validation.validator import (
    calculate_all_metrics,
    calculate_rtt_metrics,
    calculate_loss_metrics,
    calculate_bandwidth_metrics,
    calculate_sequence_metrics,
    calculate_correlation_metrics,
    validate_trace,
    compare_traces,
    generate_trace_report,
    validate_trace_realism,
    _get_profile_data,
    _validate_metrics,
    _calculate_score,
    _calculate_similarity_score,
)


class TestValidator:
    """测试验证模块"""

    def setup_method(self):
        """设置测试环境"""
        # 创建模拟的网络剖面
        self.mock_observation = MagicMock()
        self.mock_observation.delay_up = 10.0
        self.mock_observation.delay_down = 8.0
        self.mock_observation.loss_up = 0.01
        self.mock_observation.loss_down = 0.005
        self.mock_observation.bw_up = 50.0
        self.mock_observation.bw_down = 100.0

        self.mock_profile = MagicMock()
        self.mock_profile.observations = [self.mock_observation]
        self.mock_profile.start_index = 0

        # 创建多个模拟剖面用于序列测试
        self.mock_profiles = []
        for i in range(5):
            profile = MagicMock()
            profile.observations = [self.mock_observation]
            profile.start_index = i * 10  # 每个剖面间隔10秒
            self.mock_profiles.append(profile)

    def test_get_profile_data(self):
        """测试从网络剖面中提取数据"""

        # 创建一个更简单的模拟对象，直接返回观测值
        class SimpleMockProfile:
            def __init__(self, observations):
                self.observations = observations
                self.start_index = 0

        # 创建一个实际的 Observation 对象
        from traceloom.domain.pathlet import Observation

        real_observation = Observation(
            delay_up=10.0, delay_down=8.0, loss_up=0.01, loss_down=0.005, bw_up=50.0, bw_down=100.0
        )

        # 测试提取延迟数据
        profile = SimpleMockProfile([real_observation])
        delay_up_values = _get_profile_data([profile], "delay_up")
        assert len(delay_up_values) == 1
        assert delay_up_values[0] == 10.0

        # 测试提取丢包率数据
        loss_up_values = _get_profile_data([profile], "loss_up")
        assert len(loss_up_values) == 1
        assert loss_up_values[0] == 0.01

        # 测试提取带宽数据
        bw_up_values = _get_profile_data([profile], "bw_up")
        assert len(bw_up_values) == 1
        assert bw_up_values[0] == 50.0

        # 测试空观测值的情况
        empty_profile = SimpleMockProfile([])
        empty_values = _get_profile_data([empty_profile], "delay_up")
        assert len(empty_values) == 1
        assert empty_values[0] == 0.0

    def test_calculate_rtt_metrics(self):
        """测试计算RTT相关指标"""
        # 创建一个实际的 Observation 对象
        from traceloom.domain.pathlet import Observation

        real_observation = Observation(
            delay_up=10.0, delay_down=8.0, loss_up=0.01, loss_down=0.005, bw_up=50.0, bw_down=100.0
        )

        # 创建一个简单的模拟对象
        class SimpleMockProfile:
            def __init__(self, observations):
                self.observations = observations
                self.start_index = 0

        # 测试空输入
        empty_result = calculate_rtt_metrics([])
        assert empty_result["avg_rtt"] == 0.0
        assert empty_result["max_rtt"] == 0.0
        assert empty_result["min_rtt"] == 0.0
        assert empty_result["std_rtt"] == 0.0

        # 测试正常输入
        profile = SimpleMockProfile([real_observation])
        result = calculate_rtt_metrics([profile])
        assert result["avg_rtt"] == 9.0  # (10 + 8) / 2

    def test_calculate_loss_metrics(self):
        """测试计算丢包率相关指标"""
        # 创建一个实际的 Observation 对象
        from traceloom.domain.pathlet import Observation

        real_observation = Observation(
            delay_up=10.0, delay_down=8.0, loss_up=0.01, loss_down=0.005, bw_up=50.0, bw_down=100.0
        )

        # 创建一个简单的模拟对象
        class SimpleMockProfile:
            def __init__(self, observations):
                self.observations = observations
                self.start_index = 0

        # 测试空输入
        empty_result = calculate_loss_metrics([])
        assert empty_result["avg_loss_rate"] == 0.0
        assert empty_result["max_loss_rate"] == 0.0
        assert empty_result["min_loss_rate"] == 0.0

        # 测试正常输入
        profile = SimpleMockProfile([real_observation])
        result = calculate_loss_metrics([profile])
        assert result["avg_loss_rate"] == 0.0075  # (0.01 + 0.005) / 2

    def test_calculate_bandwidth_metrics(self):
        """测试计算带宽相关指标"""
        # 创建一个实际的 Observation 对象
        from traceloom.domain.pathlet import Observation

        real_observation = Observation(
            delay_up=10.0, delay_down=8.0, loss_up=0.01, loss_down=0.005, bw_up=50.0, bw_down=100.0
        )

        # 创建一个简单的模拟对象
        class SimpleMockProfile:
            def __init__(self, observations):
                self.observations = observations
                self.start_index = 0

        # 测试空输入
        empty_result = calculate_bandwidth_metrics([])
        assert empty_result["avg_bandwidth"] == 0.0
        assert empty_result["max_bandwidth"] == 0.0
        assert empty_result["min_bandwidth"] == 0.0

        # 测试正常输入
        profile = SimpleMockProfile([real_observation])
        result = calculate_bandwidth_metrics([profile])
        assert result["avg_bandwidth"] == 75.0  # (50 + 100) / 2

    def test_calculate_sequence_metrics(self):
        """测试计算序列相关指标"""
        # 创建一个实际的 Observation 对象
        from traceloom.domain.pathlet import Observation

        real_observation = Observation(
            delay_up=10.0, delay_down=8.0, loss_up=0.01, loss_down=0.005, bw_up=50.0, bw_down=100.0
        )

        # 创建一个简单的模拟对象
        class SimpleMockProfile:
            def __init__(self, observations, start_index):
                self.observations = observations
                self.start_index = start_index

        # 测试空输入
        empty_result = calculate_sequence_metrics([])
        assert empty_result["duration"] == 0.0
        assert empty_result["sample_rate"] == 0.0

        # 创建多个模拟剖面用于序列测试
        mock_profiles = []
        for i in range(5):
            profile = SimpleMockProfile([real_observation], i * 10)  # 每个剖面间隔10秒
            mock_profiles.append(profile)

        # 测试正常输入
        result = calculate_sequence_metrics(mock_profiles)
        assert result["duration"] == 4.0  # (40 - 0) / 10
        assert result["sample_rate"] == 1.25  # 5 / 4

    def test_calculate_correlation_metrics(self):
        """测试计算相关性指标"""
        # 创建一个实际的 Observation 对象
        from traceloom.domain.pathlet import Observation

        real_observation = Observation(
            delay_up=10.0, delay_down=8.0, loss_up=0.01, loss_down=0.005, bw_up=50.0, bw_down=100.0
        )

        # 创建一个简单的模拟对象
        class SimpleMockProfile:
            def __init__(self, observations, start_index):
                self.observations = observations
                self.start_index = start_index

        # 创建单个模拟剖面
        single_profile = SimpleMockProfile([real_observation], 0)

        # 测试输入不足的情况
        insufficient_result = calculate_correlation_metrics([single_profile])
        assert insufficient_result["rtt_loss_corr"] == 0.0
        assert insufficient_result["rtt_bandwidth_corr"] == 0.0
        assert insufficient_result["loss_bandwidth_corr"] == 0.0

        # 创建多个模拟剖面用于相关性测试
        mock_profiles = []
        for i in range(5):
            profile = SimpleMockProfile([real_observation], i * 10)  # 每个剖面间隔10秒
            mock_profiles.append(profile)

        # 测试正常输入
        result = calculate_correlation_metrics(mock_profiles)
        # 由于所有剖面数据相同，相关性应该为0或接近0
        assert result["rtt_loss_corr"] == 0.0

    def test_calculate_all_metrics(self):
        """测试计算所有指标"""
        # 创建一个实际的 Observation 对象
        from traceloom.domain.pathlet import Observation

        real_observation = Observation(
            delay_up=10.0, delay_down=8.0, loss_up=0.01, loss_down=0.005, bw_up=50.0, bw_down=100.0
        )

        # 创建一个简单的模拟对象
        class SimpleMockProfile:
            def __init__(self, observations, start_index):
                self.observations = observations
                self.start_index = start_index

        # 测试空输入
        empty_result = calculate_all_metrics([])
        assert empty_result == {}

        # 创建模拟剖面
        profile = SimpleMockProfile([real_observation], 0)

        # 测试正常输入
        result = calculate_all_metrics([profile])
        assert "avg_rtt" in result
        assert "avg_loss_rate" in result
        assert "avg_bandwidth" in result

    def test_validate_metrics(self):
        """测试验证指标是否符合阈值"""
        # 测试通过的情况
        metrics = {
            "max_rtt": 1000.0,
            "max_loss_rate": 0.5,
            "min_bandwidth": 10.0,
            "rtt_cv": 0.5,
            "loss_rate_cv": 0.5,
            "bandwidth_cv": 0.5,
        }
        thresholds = {
            "max_rtt": 2000.0,
            "max_loss_rate": 1.0,
            "min_bandwidth": 0.0,
            "rtt_cv": 1.0,
            "loss_rate_cv": 1.0,
            "bandwidth_cv": 1.0,
        }
        assert _validate_metrics(metrics, thresholds) is True

        # 测试不通过的情况
        metrics["max_rtt"] = 3000.0
        assert _validate_metrics(metrics, thresholds) is False

    def test_calculate_score(self):
        """测试计算评估分数"""
        metrics = {
            "avg_rtt": 100.0,
            "rtt_cv": 0.1,
            "avg_loss_rate": 0.01,
            "loss_rate_cv": 0.1,
            "avg_bandwidth": 50.0,
            "bandwidth_cv": 0.1,
            "rtt_jump_count": 0.0,
            "loss_jump_count": 0.0,
            "bandwidth_jump_count": 0.0,
        }
        score = _calculate_score(metrics)
        assert 0 <= score <= 100

    def test_validate_trace(self):
        """测试验证网络轨迹"""
        # 创建一个实际的 Observation 对象
        from traceloom.domain.pathlet import Observation

        real_observation = Observation(
            delay_up=10.0, delay_down=8.0, loss_up=0.01, loss_down=0.005, bw_up=50.0, bw_down=100.0
        )

        # 创建一个简单的模拟对象
        class SimpleMockProfile:
            def __init__(self, observations, start_index):
                self.observations = observations
                self.start_index = start_index

        # 测试空输入
        empty_result = validate_trace([])
        assert empty_result["valid"] is False
        assert empty_result["score"] == 0.0

        # 创建模拟剖面
        profile = SimpleMockProfile([real_observation], 0)

        # 测试正常输入
        result = validate_trace([profile])
        assert "metrics" in result
        assert "valid" in result
        assert "score" in result

    def test_calculate_similarity_score(self):
        """测试计算相似性分数"""
        # 测试完全相同的指标
        metrics1 = {
            "avg_rtt": 100.0,
            "std_rtt": 10.0,
            "avg_loss_rate": 0.01,
            "std_loss_rate": 0.001,
            "avg_bandwidth": 50.0,
            "std_bandwidth": 5.0,
            "rtt_cv": 0.1,
            "loss_rate_cv": 0.1,
            "bandwidth_cv": 0.1,
        }
        metrics2 = metrics1.copy()
        score = _calculate_similarity_score(metrics1, metrics2)
        assert score == 100.0

        # 测试不同的指标
        metrics2["avg_rtt"] = 200.0
        score = _calculate_similarity_score(metrics1, metrics2)
        assert score < 100.0

    def test_compare_traces(self):
        """测试比较两个网络轨迹"""
        # 创建一个实际的 Observation 对象
        from traceloom.domain.pathlet import Observation

        real_observation = Observation(
            delay_up=10.0, delay_down=8.0, loss_up=0.01, loss_down=0.005, bw_up=50.0, bw_down=100.0
        )

        # 创建一个简单的模拟对象
        class SimpleMockProfile:
            def __init__(self, observations, start_index):
                self.observations = observations
                self.start_index = start_index

        # 创建模拟剖面
        profile = SimpleMockProfile([real_observation], 0)

        # 测试比较两个轨迹
        result = compare_traces([profile], [profile])
        assert "similarity_score" in result
        assert "differences" in result
        assert "metrics1" in result
        assert "metrics2" in result

    def test_generate_trace_report(self):
        """测试生成轨迹评估报告"""
        # 创建一个实际的 Observation 对象
        from traceloom.domain.pathlet import Observation

        real_observation = Observation(
            delay_up=10.0, delay_down=8.0, loss_up=0.01, loss_down=0.005, bw_up=50.0, bw_down=100.0
        )

        # 创建一个简单的模拟对象
        class SimpleMockProfile:
            def __init__(self, observations, start_index):
                self.observations = observations
                self.start_index = start_index

        # 创建模拟剖面
        profile = SimpleMockProfile([real_observation], 0)

        # 测试生成报告
        report = generate_trace_report([profile])
        assert isinstance(report, str)
        assert "网络参数序列评估报告" in report

    def test_validate_trace_realism(self):
        """测试验证网络轨迹的真实性"""
        # 创建一个实际的 Observation 对象
        from traceloom.domain.pathlet import Observation

        real_observation = Observation(
            delay_up=10.0, delay_down=8.0, loss_up=0.01, loss_down=0.005, bw_up=50.0, bw_down=100.0
        )

        # 创建一个简单的模拟对象
        class SimpleMockProfile:
            def __init__(self, observations, start_index):
                self.observations = observations
                self.start_index = start_index

        # 测试空输入
        empty_result = validate_trace_realism([])
        assert empty_result["realism_score"] == 0.0

        # 创建模拟剖面
        profile = SimpleMockProfile([real_observation], 0)

        # 测试正常输入
        result = validate_trace_realism([profile])
        assert "realism_checks" in result
        assert "realism_score" in result
        assert "metrics" in result


if __name__ == "__main__":
    pytest.main([__file__])
