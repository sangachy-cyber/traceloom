# -*- coding: utf-8 -*-
"""测试验证模块的边缘场景和边界条件"""

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
    validate_trace_realism,
)
from traceloom.domain.raw_trace import RawTraceSegment, TraceContextValues
from traceloom.domain.pathlet import Observation


@pytest.fixture
def empty_profiles():
    """创建空网络剖面列表"""
    return []


@pytest.fixture
def single_profile():
    """创建单个网络剖面"""
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
    profile = RawTraceSegment(
        trace_name="test_trace",
        start_index=0,
        observations=observations,
        is_valid=True,
    )
    profile.ctx_values = ctx_values
    
    return [profile]


@pytest.fixture
def extreme_profiles():
    """创建包含极端值的网络剖面"""
    # 创建观测数据
    observations = []
    for i in range(10):
        obs = Observation(
            delay_up=2000 + i * 100,  # 极端高延迟
            loss_up=0.9 + i * 0.01,     # 极端高丢包率
            bw_up=0.1 - i * 0.01,        # 极端低带宽
            delay_down=2100 + i * 100,
            loss_down=0.95 + i * 0.005,
            bw_down=0.05 - i * 0.005,
        )
        observations.append(obs)
    
    # 创建上下文值
    ctx_values = TraceContextValues(
        delay_up_mean=2450.0,  # 极端高延迟
        loss_up_mean=0.95,     # 极端高丢包率
        bw_up_mean=0.055,       # 极端低带宽
        delay_down_mean=2550.0,
        loss_down_mean=0.975,
        bw_down_mean=0.025,
    )
    
    # 创建网络剖面
    profiles = []
    for i in range(5):
        profile = RawTraceSegment(
            trace_name=f"extreme_trace_{i}",
            start_index=i * 10,
            observations=observations,
            is_valid=True,
        )
        profile.ctx_values = ctx_values
        profiles.append(profile)
    
    return profiles


@pytest.fixture
def boundary_profiles():
    """创建包含边界值的网络剖面"""
    # 创建观测数据
    observations = []
    for i in range(10):
        obs = Observation(
            delay_up=2000,  # 延迟刚好等于阈值
            loss_up=1.0,     # 丢包率刚好等于最大值
            bw_up=0.0,      # 带宽刚好等于最小值
            delay_down=2000,
            loss_down=1.0,
            bw_down=0.0,
        )
        observations.append(obs)
    
    # 创建上下文值
    ctx_values = TraceContextValues(
        delay_up_mean=2000.0,  # 延迟刚好等于阈值
        loss_up_mean=1.0,      # 丢包率刚好等于最大值
        bw_up_mean=0.0,        # 带宽刚好等于最小值
        delay_down_mean=2000.0,
        loss_down_mean=1.0,
        bw_down_mean=0.0,
    )
    
    # 创建网络剖面
    profile = RawTraceSegment(
        trace_name="boundary_trace",
        start_index=0,
        observations=observations,
        is_valid=True,
    )
    profile.ctx_values = ctx_values
    
    return [profile]


def test_calculate_rtt_metrics_empty(empty_profiles):
    """测试空输入计算RTT指标"""
    metrics = calculate_rtt_metrics(empty_profiles)
    assert metrics["avg_rtt"] == 0.0
    assert metrics["max_rtt"] == 0.0
    assert metrics["min_rtt"] == 0.0
    assert metrics["std_rtt"] == 0.0
    assert metrics["skew_rtt"] == 0.0
    assert metrics["kurtosis_rtt"] == 0.0
    assert metrics["rtt_cv"] == 0.0


def test_calculate_loss_metrics_empty(empty_profiles):
    """测试空输入计算丢包率指标"""
    metrics = calculate_loss_metrics(empty_profiles)
    assert metrics["avg_loss_rate"] == 0.0
    assert metrics["max_loss_rate"] == 0.0
    assert metrics["min_loss_rate"] == 0.0
    assert metrics["std_loss_rate"] == 0.0
    assert metrics["loss_rate_cv"] == 0.0
    assert metrics["packet_loss_ratio"] == 0.0


def test_calculate_bandwidth_metrics_empty(empty_profiles):
    """测试空输入计算带宽指标"""
    metrics = calculate_bandwidth_metrics(empty_profiles)
    assert metrics["avg_bandwidth"] == 0.0
    assert metrics["max_bandwidth"] == 0.0
    assert metrics["min_bandwidth"] == 0.0
    assert metrics["std_bandwidth"] == 0.0
    assert metrics["bandwidth_cv"] == 0.0
    assert metrics["bandwidth_utilization"] == 0.0


def test_calculate_sequence_metrics_empty(empty_profiles):
    """测试空输入计算序列指标"""
    metrics = calculate_sequence_metrics(empty_profiles)
    assert metrics["duration"] == 0.0
    assert metrics["sample_rate"] == 0.0
    assert metrics["rtt_jump_count"] == 0.0
    assert metrics["loss_jump_count"] == 0.0
    assert metrics["bandwidth_jump_count"] == 0.0


def test_calculate_correlation_metrics_empty(empty_profiles):
    """测试空输入计算相关性指标"""
    metrics = calculate_correlation_metrics(empty_profiles)
    assert metrics["rtt_loss_corr"] == 0.0
    assert metrics["rtt_bandwidth_corr"] == 0.0
    assert metrics["loss_bandwidth_corr"] == 0.0


def test_calculate_all_metrics_empty(empty_profiles):
    """测试空输入计算所有指标"""
    metrics = calculate_all_metrics(empty_profiles)
    assert metrics == {}


def test_validate_trace_empty(empty_profiles):
    """测试验证空网络轨迹"""
    result = validate_trace(empty_profiles)
    assert not result["valid"]
    assert result["message"] == "输入的网络剖面列表为空"
    assert result["score"] == 0.0


def test_compare_traces_empty():
    """测试比较两个空网络轨迹"""
    result = compare_traces([], [])
    assert result["similarity_score"] == 0.0
    assert result["differences"] == {}


def test_validate_trace_realism_empty(empty_profiles):
    """测试验证空网络轨迹的真实性"""
    result = validate_trace_realism(empty_profiles)
    assert "realism_checks" in result
    assert "realism_score" in result
    assert "metrics" in result
    assert "message" in result


def test_calculate_correlation_metrics_single(single_profile):
    """测试单元素输入计算相关性指标"""
    metrics = calculate_correlation_metrics(single_profile)
    assert metrics["rtt_loss_corr"] == 0.0
    assert metrics["rtt_bandwidth_corr"] == 0.0
    assert metrics["loss_bandwidth_corr"] == 0.0


def test_validate_trace_extreme(extreme_profiles):
    """测试验证包含极端值的网络轨迹"""
    result = validate_trace(extreme_profiles)
    assert "metrics" in result
    assert "valid" in result
    assert "message" in result
    assert "score" in result
    # 极端值的轨迹应该被标记为无效
    assert not result["valid"]


def test_validate_trace_boundary(boundary_profiles):
    """测试验证包含边界值的网络轨迹"""
    result = validate_trace(boundary_profiles)
    assert "metrics" in result
    assert "valid" in result
    assert "message" in result
    assert "score" in result


def test_validate_trace_realism_extreme(extreme_profiles):
    """测试验证包含极端值的网络轨迹的真实性"""
    result = validate_trace_realism(extreme_profiles)
    assert "realism_checks" in result
    assert "realism_score" in result
    assert "metrics" in result
    assert "message" in result


def test_compare_traces_different(single_profile, extreme_profiles):
    """测试比较两个不同的网络轨迹"""
    result = compare_traces(single_profile, extreme_profiles)
    assert "similarity_score" in result
    assert "differences" in result
    assert "metrics1" in result
    assert "metrics2" in result
    assert "message" in result
