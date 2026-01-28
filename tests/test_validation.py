# -*- coding: utf-8 -*-
"""测试验证模块"""

import pytest
import numpy as np

from traceloom.validation.validator import (
    calculate_rtt_metrics,
    calculate_loss_metrics,
    calculate_bandwidth_metrics,
    calculate_sequence_metrics,
    calculate_correlation_metrics,
    calculate_all_metrics,
    validate_trace,
    compare_traces,
    generate_trace_report,
    validate_trace_realism,
)
from traceloom.domain.raw_trace import RawTraceSegment, TraceContextValues
from traceloom.domain.pathlet import Observation


@pytest.fixture
def sample_profiles():
    """创建示例网络剖面"""
    # 创建观测数据
    observations = []
    for i in range(10):
        obs = Observation(
            delay_up=100 + i * 10,
            loss_up=0.01 + i * 0.01,
            bw_up=10 - i * 0.5,
            delay_down=110 + i * 10,
            loss_down=0.02 + i * 0.01,
            bw_down=12 - i * 0.5,
        )
        observations.append(obs)
    
    # 创建上下文值
    ctx_values = TraceContextValues(
        delay_up_mean=145.0,
        loss_up_mean=0.055,
        bw_up_mean=7.75,
        delay_down_mean=155.0,
        loss_down_mean=0.065,
        bw_down_mean=9.75,
    )
    
    # 创建网络剖面
    profiles = []
    for i in range(5):
        profile = RawTraceSegment(
            trace_name=f"test_trace_{i}",
            start_index=i * 10,
            observations=observations,
            is_valid=True,
        )
        profile.ctx_values = ctx_values
        profiles.append(profile)
    
    return profiles


def test_calculate_rtt_metrics(sample_profiles):
    """测试 RTT 指标计算"""
    metrics = calculate_rtt_metrics(sample_profiles)
    assert "avg_rtt" in metrics
    assert "max_rtt" in metrics
    assert "min_rtt" in metrics
    assert "std_rtt" in metrics
    assert "skew_rtt" in metrics
    assert "kurtosis_rtt" in metrics
    assert "rtt_cv" in metrics
    
    # 测试空输入
    empty_metrics = calculate_rtt_metrics([])
    assert empty_metrics["avg_rtt"] == 0.0


def test_calculate_loss_metrics(sample_profiles):
    """测试丢包率指标计算"""
    metrics = calculate_loss_metrics(sample_profiles)
    assert "avg_loss_rate" in metrics
    assert "max_loss_rate" in metrics
    assert "min_loss_rate" in metrics
    assert "std_loss_rate" in metrics
    assert "loss_rate_cv" in metrics
    assert "packet_loss_ratio" in metrics
    
    # 测试空输入
    empty_metrics = calculate_loss_metrics([])
    assert empty_metrics["avg_loss_rate"] == 0.0


def test_calculate_bandwidth_metrics(sample_profiles):
    """测试带宽指标计算"""
    metrics = calculate_bandwidth_metrics(sample_profiles)
    assert "avg_bandwidth" in metrics
    assert "max_bandwidth" in metrics
    assert "min_bandwidth" in metrics
    assert "std_bandwidth" in metrics
    assert "bandwidth_cv" in metrics
    assert "bandwidth_utilization" in metrics
    
    # 测试空输入
    empty_metrics = calculate_bandwidth_metrics([])
    assert empty_metrics["avg_bandwidth"] == 0.0


def test_calculate_sequence_metrics(sample_profiles):
    """测试序列指标计算"""
    metrics = calculate_sequence_metrics(sample_profiles)
    assert "duration" in metrics
    assert "sample_rate" in metrics
    assert "rtt_jump_count" in metrics
    assert "loss_jump_count" in metrics
    assert "bandwidth_jump_count" in metrics
    
    # 测试空输入
    empty_metrics = calculate_sequence_metrics([])
    assert empty_metrics["duration"] == 0.0


def test_calculate_correlation_metrics(sample_profiles):
    """测试相关性指标计算"""
    metrics = calculate_correlation_metrics(sample_profiles)
    assert "rtt_loss_corr" in metrics
    assert "rtt_bandwidth_corr" in metrics
    assert "loss_bandwidth_corr" in metrics
    
    # 测试少于2个剖面的情况
    single_profile_metrics = calculate_correlation_metrics([sample_profiles[0]])
    assert single_profile_metrics["rtt_loss_corr"] == 0.0


def test_calculate_all_metrics(sample_profiles):
    """测试计算所有指标"""
    metrics = calculate_all_metrics(sample_profiles)
    assert len(metrics) > 0
    
    # 测试空输入
    empty_metrics = calculate_all_metrics([])
    assert empty_metrics == {}


def test_validate_trace(sample_profiles):
    """测试验证网络轨迹"""
    result = validate_trace(sample_profiles)
    assert "metrics" in result
    assert "valid" in result
    assert "message" in result
    assert "score" in result
    
    # 测试空输入
    empty_result = validate_trace([])
    assert not empty_result["valid"]
    assert empty_result["message"] == "输入的网络剖面列表为空"


def test_compare_traces(sample_profiles):
    """测试比较两个网络轨迹"""
    result = compare_traces(sample_profiles, sample_profiles)
    assert "similarity_score" in result
    assert "differences" in result
    assert "metrics1" in result
    assert "metrics2" in result
    assert "message" in result


def test_generate_trace_report(sample_profiles):
    """测试生成轨迹评估报告"""
    report = generate_trace_report(sample_profiles)
    assert isinstance(report, str)
    assert "=== 网络参数序列评估报告 ===" in report
    assert "评估结果:" in report
    assert "评估分数:" in report


def test_validate_trace_realism(sample_profiles):
    """测试验证网络轨迹的真实性"""
    result = validate_trace_realism(sample_profiles)
    assert "realism_checks" in result
    assert "realism_score" in result
    assert "metrics" in result
    assert "message" in result
