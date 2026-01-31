# -*- coding: utf-8 -*-
"""网络参数指标计算模块

用于计算网络参数序列的各种指标，包括RTT、丢包率、带宽等相关指标，
以及验证网络轨迹的有效性和真实性。

示例:
    # 计算网络轨迹的各项指标
    from traceloom.validation.validator import calculate_all_metrics, validate_trace
    from traceloom.domain.raw_trace import RawTraceSegment
    import pandas as pd

    # 创建示例轨迹数据
    df = pd.DataFrame({
        'delay_up': [10.0] * 120,
        'delay_down': [8.0] * 120,
        'loss_up': [0.01] * 120,
        'loss_down': [0.005] * 120,
        'bw_up': [50.0] * 120,
        'bw_down': [100.0] * 120
    })

    # 创建原始轨迹片段
    segment = RawTraceSegment.from_dataframe(
        df=df,
        trace_name="test_trace",
        start_index=0,
        length=110
    )

    # 计算各项指标
    metrics = calculate_all_metrics([segment])
    print(f"计算的指标: {metrics}")

    # 验证轨迹
    validation_result = validate_trace([segment])
    print(f"验证结果: {validation_result}")
"""

from datetime import datetime
from typing import Dict, List, Optional, Union

import numpy as np
from scipy import stats

from traceloom.domain.pathlet import Pathlet as RawProfile

# 暂时注释掉 ProcessedProfile 的导入，因为该模块在当前架构中不存在
# from traceloom.weaving.pathlet.profile import ProcessedProfile
ProcessedProfile = RawProfile  # 临时定义为 RawProfile 的别名


def _get_profile_data(profiles: List[Union[RawProfile, ProcessedProfile]], feature: str) -> List[float]:
    """从网络剖面中提取指定特征的数据

    从给定的网络剖面列表中提取指定特征的数据，支持从 RawProfile 或 ProcessedProfile 中提取。

    Args:
        profiles: RawProfile 或 ProcessedProfile 列表
        feature: 特征名称，可为 "delay_up", "delay_down", "loss_up", "loss_down", "bw_up", "bw_down"

    Returns:
        List[float]: 特征值列表

    Examples:
        # 提取上行延迟数据
        delay_up_values = _get_profile_data(profiles, "delay_up")
        print(f"上行延迟数据: {delay_up_values}")
    """
    values = []
    for profile in profiles:
        # 确定使用哪个profile对象
        # 检查对象是否有raw_profile属性，而不是基于类型判断
        current_profile = getattr(profile, "raw_profile", profile)

        # 从observations中计算特征值的均值
        feature_values = []
        # 检查对象是否有observations属性
        if hasattr(current_profile, "observations"):
            for obs in current_profile.observations:
                if feature == "delay_up":
                    feature_values.append(obs.delay_up)
                elif feature == "delay_down":
                    feature_values.append(obs.delay_down)
                elif feature == "loss_up":
                    feature_values.append(obs.loss_up)
                elif feature == "loss_down":
                    feature_values.append(obs.loss_down)
                elif feature == "bw_up":
                    feature_values.append(obs.bw_up)
                elif feature == "bw_down":
                    feature_values.append(obs.bw_down)

        # 计算均值并添加到结果列表
        if feature_values:
            mean_value = sum(feature_values) / len(feature_values)
            values.append(mean_value)
        else:
            values.append(0.0)
    return values


def calculate_rtt_metrics(profiles: List[Union[RawProfile, ProcessedProfile]]) -> Dict[str, float]:
    """计算 RTT 相关指标

    计算网络轨迹的 RTT（往返时间）相关指标，包括均值、最大值、最小值、标准差、偏度、峰度等。

    Args:
        profiles: RawProfile 或 ProcessedProfile 列表

    Returns:
        Dict[str, float]: RTT 指标字典，包含均值、最大值、最小值、标准差、偏度、峰度等

    Examples:
        # 计算 RTT 相关指标
        rtt_metrics = calculate_rtt_metrics(profiles)
        print(f"RTT 指标: {rtt_metrics}")
    """
    if not profiles:
        return {
            "avg_rtt": 0.0,
            "max_rtt": 0.0,
            "min_rtt": 0.0,
            "std_rtt": 0.0,
            "skew_rtt": 0.0,
            "kurtosis_rtt": 0.0,
            "rtt_cv": 0.0,
        }

    # 提取上下行RTT数据并计算平均值
    delay_up_values = _get_profile_data(profiles, "delay_up")
    delay_down_values = _get_profile_data(profiles, "delay_down")
    rtt_values = np.array([(up + down) / 2 for up, down in zip(delay_up_values, delay_down_values, strict=False)])

    # 计算指标
    avg_rtt = np.mean(rtt_values)
    max_rtt = np.max(rtt_values)
    min_rtt = np.min(rtt_values)
    std_rtt = np.std(rtt_values)

    # 使用 warnings 模块捕获和忽略精度损失警告
    import warnings

    with warnings.catch_warnings():
        # 忽略精度损失警告
        warnings.filterwarnings("ignore", message="Precision loss occurred in moment calculation")
        # 计算偏度和峰度
        try:
            skew_rtt = stats.skew(rtt_values)
        except (RuntimeWarning, ValueError):
            skew_rtt = 0.0

        try:
            kurtosis_rtt = stats.kurtosis(rtt_values)
        except (RuntimeWarning, ValueError):
            kurtosis_rtt = 0.0

    rtt_cv = std_rtt / avg_rtt if avg_rtt > 0 else 0.0

    return {
        "avg_rtt": float(avg_rtt),
        "max_rtt": float(max_rtt),
        "min_rtt": float(min_rtt),
        "std_rtt": float(std_rtt),
        "skew_rtt": float(skew_rtt),
        "kurtosis_rtt": float(kurtosis_rtt),
        "rtt_cv": float(rtt_cv),
    }


def calculate_loss_metrics(profiles: List[Union[RawProfile, ProcessedProfile]]) -> Dict[str, float]:
    """计算丢包率相关指标

    计算网络轨迹的丢包率相关指标，包括均值、最大值、最小值、标准差等。

    Args:
        profiles: RawProfile 或 ProcessedProfile 列表

    Returns:
        Dict[str, float]: 丢包率指标字典，包含均值、最大值、最小值、标准差等

    Examples:
        # 计算丢包率相关指标
        loss_metrics = calculate_loss_metrics(profiles)
        print(f"丢包率指标: {loss_metrics}")
    """
    if not profiles:
        return {
            "avg_loss_rate": 0.0,
            "max_loss_rate": 0.0,
            "min_loss_rate": 0.0,
            "std_loss_rate": 0.0,
            "loss_rate_cv": 0.0,
            "packet_loss_ratio": 0.0,
        }

    # 提取上下行丢包率数据并计算平均值
    loss_up_values = _get_profile_data(profiles, "loss_up")
    loss_down_values = _get_profile_data(profiles, "loss_down")
    loss_values = np.array([(up + down) / 2 for up, down in zip(loss_up_values, loss_down_values, strict=False)])

    # 计算指标
    avg_loss_rate = np.mean(loss_values)
    max_loss_rate = np.max(loss_values)
    min_loss_rate = np.min(loss_values)
    std_loss_rate = np.std(loss_values)
    loss_rate_cv = std_loss_rate / avg_loss_rate if avg_loss_rate > 0 else 0.0

    # 计算丢包比例（丢包率大于0的样本比例）
    packet_loss_ratio = float(np.sum(loss_values > 0) / len(loss_values))

    return {
        "avg_loss_rate": float(avg_loss_rate),
        "max_loss_rate": float(max_loss_rate),
        "min_loss_rate": float(min_loss_rate),
        "std_loss_rate": float(std_loss_rate),
        "loss_rate_cv": float(loss_rate_cv),
        "packet_loss_ratio": float(packet_loss_ratio),
    }


def calculate_bandwidth_metrics(profiles: List[Union[RawProfile, ProcessedProfile]]) -> Dict[str, float]:
    """计算带宽相关指标

    计算网络轨迹的带宽相关指标，包括均值、最大值、最小值、标准差等。

    Args:
        profiles: RawProfile 或 ProcessedProfile 列表

    Returns:
        Dict[str, float]: 带宽指标字典，包含均值、最大值、最小值、标准差等

    Examples:
        # 计算带宽相关指标
        bandwidth_metrics = calculate_bandwidth_metrics(profiles)
        print(f"带宽指标: {bandwidth_metrics}")
    """
    if not profiles:
        return {
            "avg_bandwidth": 0.0,
            "max_bandwidth": 0.0,
            "min_bandwidth": 0.0,
            "std_bandwidth": 0.0,
            "bandwidth_cv": 0.0,
            "bandwidth_utilization": 0.0,
        }

    # 提取上下行带宽数据并计算平均值
    bw_up_values = _get_profile_data(profiles, "bw_up")
    bw_down_values = _get_profile_data(profiles, "bw_down")
    bandwidth_values = np.array([(up + down) / 2 for up, down in zip(bw_up_values, bw_down_values, strict=False)])

    # 计算指标
    avg_bandwidth = np.mean(bandwidth_values)
    max_bandwidth = np.max(bandwidth_values)
    min_bandwidth = np.min(bandwidth_values)
    std_bandwidth = np.std(bandwidth_values)
    bandwidth_cv = std_bandwidth / avg_bandwidth if avg_bandwidth > 0 else 0.0

    # 计算带宽利用率（假设最大可能带宽为 100 Mbps）
    max_possible_bandwidth = 100.0
    bandwidth_utilization = avg_bandwidth / max_possible_bandwidth

    return {
        "avg_bandwidth": float(avg_bandwidth),
        "max_bandwidth": float(max_bandwidth),
        "min_bandwidth": float(min_bandwidth),
        "std_bandwidth": float(std_bandwidth),
        "bandwidth_cv": float(bandwidth_cv),
        "bandwidth_utilization": float(bandwidth_utilization),
    }


def calculate_sequence_metrics(profiles: List[Union[RawProfile, ProcessedProfile]]) -> Dict[str, float]:
    """计算序列相关指标

    计算网络轨迹的序列相关指标，包括持续时间、采样率、跳变次数等。

    Args:
        profiles: RawProfile 或 ProcessedProfile 列表

    Returns:
        Dict[str, float]: 序列指标字典，包含持续时间、采样率、跳变次数等

    Examples:
        # 计算序列相关指标
        sequence_metrics = calculate_sequence_metrics(profiles)
        print(f"序列指标: {sequence_metrics}")
    """
    if not profiles:
        return {
            "duration": 0.0,
            "sample_rate": 0.0,
            "rtt_jump_count": 0.0,
            "loss_jump_count": 0.0,
            "bandwidth_jump_count": 0.0,
        }

    # 提取start_index,假设每个profile间隔10秒（根据ctx_10s的名称）
    start_indices = []
    for profile in profiles:
        current_profile = getattr(profile, "raw_profile", profile)
        start_indices.append(current_profile.start_index)

    # 计算持续时间（假设每个索引对应10秒）
    duration = (max(start_indices) - min(start_indices)) / 10.0  # 转换为秒

    # 计算采样率
    sample_rate = len(profiles) / duration if duration > 0 else 0.0

    # 提取数据用于跳变次数计算
    # 提取上下行RTT数据并计算平均值
    delay_up_values = _get_profile_data(profiles, "delay_up")
    delay_down_values = _get_profile_data(profiles, "delay_down")
    rtt_values = np.array([(up + down) / 2 for up, down in zip(delay_up_values, delay_down_values, strict=False)])

    # 提取上下行丢包率数据并计算平均值
    loss_up_values = _get_profile_data(profiles, "loss_up")
    loss_down_values = _get_profile_data(profiles, "loss_down")
    loss_values = np.array([(up + down) / 2 for up, down in zip(loss_up_values, loss_down_values, strict=False)])

    # 提取上下行带宽数据并计算平均值
    bw_up_values = _get_profile_data(profiles, "bw_up")
    bw_down_values = _get_profile_data(profiles, "bw_down")
    bandwidth_values = np.array([(up + down) / 2 for up, down in zip(bw_up_values, bw_down_values, strict=False)])

    # 计算差分
    rtt_diff = np.abs(np.diff(rtt_values))
    loss_diff = np.abs(np.diff(loss_values))
    bandwidth_diff = np.abs(np.diff(bandwidth_values))

    # 跳变阈值（根据实际情况调整）
    rtt_jump_threshold = 10.0  # RTT 跳变阈值为 10ms
    loss_jump_threshold = 0.1  # 丢包率跳变阈值为 0.1
    bandwidth_jump_threshold = 5.0  # 带宽跳变阈值为 5 Mbps

    # 计算跳变次数
    rtt_jump_count = float(np.sum(rtt_diff > rtt_jump_threshold))
    loss_jump_count = float(np.sum(loss_diff > loss_jump_threshold))
    bandwidth_jump_count = float(np.sum(bandwidth_diff > bandwidth_jump_threshold))

    return {
        "duration": float(duration),
        "sample_rate": float(sample_rate),
        "rtt_jump_count": rtt_jump_count,
        "loss_jump_count": loss_jump_count,
        "bandwidth_jump_count": bandwidth_jump_count,
    }


def calculate_correlation_metrics(profiles: List[Union[RawProfile, ProcessedProfile]]) -> Dict[str, float]:
    """计算相关性指标

    计算网络轨迹的相关性指标，包括RTT与丢包率、RTT与带宽、丢包率与带宽之间的相关系数。

    Args:
        profiles: RawProfile 或 ProcessedProfile 列表

    Returns:
        Dict[str, float]: 相关性指标字典，包含各参数之间的相关系数

    Examples:
        # 计算相关性指标
        correlation_metrics = calculate_correlation_metrics(profiles)
        print(f"相关性指标: {correlation_metrics}")
    """
    if len(profiles) < 2:
        return {
            "rtt_loss_corr": 0.0,
            "rtt_bandwidth_corr": 0.0,
            "loss_bandwidth_corr": 0.0,
        }

    # 提取上下行RTT数据并计算平均值
    delay_up_values = _get_profile_data(profiles, "delay_up")
    delay_down_values = _get_profile_data(profiles, "delay_down")
    rtt_values = np.array([(up + down) / 2 for up, down in zip(delay_up_values, delay_down_values, strict=False)])

    # 提取上下行丢包率数据并计算平均值
    loss_up_values = _get_profile_data(profiles, "loss_up")
    loss_down_values = _get_profile_data(profiles, "loss_down")
    loss_values = np.array([(up + down) / 2 for up, down in zip(loss_up_values, loss_down_values, strict=False)])

    # 提取上下行带宽数据并计算平均值
    bw_up_values = _get_profile_data(profiles, "bw_up")
    bw_down_values = _get_profile_data(profiles, "bw_down")
    bandwidth_values = np.array([(up + down) / 2 for up, down in zip(bw_up_values, bw_down_values, strict=False)])

    # 计算相关系数，添加错误处理和警告过滤
    with np.errstate(invalid="ignore", divide="ignore"):
        try:
            # 检查数据是否有足够的变化
            if np.std(rtt_values) == 0 or np.std(loss_values) == 0:
                rtt_loss_corr = 0.0
            else:
                rtt_loss_corr = np.corrcoef(rtt_values, loss_values)[0, 1]
        except (RuntimeWarning, ValueError):
            rtt_loss_corr = 0.0

        try:
            if np.std(rtt_values) == 0 or np.std(bandwidth_values) == 0:
                rtt_bandwidth_corr = 0.0
            else:
                rtt_bandwidth_corr = np.corrcoef(rtt_values, bandwidth_values)[0, 1]
        except (RuntimeWarning, ValueError):
            rtt_bandwidth_corr = 0.0

        try:
            if np.std(loss_values) == 0 or np.std(bandwidth_values) == 0:
                loss_bandwidth_corr = 0.0
            else:
                loss_bandwidth_corr = np.corrcoef(loss_values, bandwidth_values)[0, 1]
        except (RuntimeWarning, ValueError):
            loss_bandwidth_corr = 0.0

    return {
        "rtt_loss_corr": float(rtt_loss_corr),
        "rtt_bandwidth_corr": float(rtt_bandwidth_corr),
        "loss_bandwidth_corr": float(loss_bandwidth_corr),
    }


def calculate_all_metrics(profiles: List[Union[RawProfile, ProcessedProfile]]) -> Dict[str, float]:
    """计算所有指标

    计算网络轨迹的所有指标，包括RTT、丢包率、带宽、序列和相关性等指标。

    Args:
        profiles: RawProfile 或 ProcessedProfile 列表

    Returns:
        Dict[str, float]: 所有指标的字典，包含RTT、丢包率、带宽、序列和相关性等指标

    Examples:
        # 计算所有指标
        all_metrics = calculate_all_metrics(profiles)
        print(f"所有指标: {all_metrics}")
    """
    if not profiles:
        return {}

    # 计算各项指标
    rtt_metrics = calculate_rtt_metrics(profiles)
    loss_metrics = calculate_loss_metrics(profiles)
    bandwidth_metrics = calculate_bandwidth_metrics(profiles)
    sequence_metrics = calculate_sequence_metrics(profiles)
    correlation_metrics = calculate_correlation_metrics(profiles)

    # 合并所有指标
    all_metrics = {
        **rtt_metrics,
        **loss_metrics,
        **bandwidth_metrics,
        **sequence_metrics,
        **correlation_metrics,
    }

    return all_metrics


def validate_trace(
    trace_data: List[Union[RawProfile, ProcessedProfile]], threshold_config: Optional[Dict[str, float]] = None
) -> Dict[str, any]:
    """验证网络轨迹数据

    验证网络轨迹数据是否符合预期的阈值要求，并计算验证分数。

    Args:
        trace_data: RawProfile 或 ProcessedProfile 列表
        threshold_config: 评估阈值配置，用于判断指标是否符合要求

    Returns:
        Dict[str, any]: 验证结果，包含各项指标和验证结论

    Examples:
        # 验证网络轨迹数据
        result = validate_trace(trace_data)
        print(f"验证结果: {result}")
    """
    # 默认阈值配置
    default_thresholds = {
        "max_rtt": 2000.0,
        "max_loss_rate": 1.0,
        "min_bandwidth": 0.0,
        "rtt_cv": 1.0,
        "loss_rate_cv": 1.0,
        "bandwidth_cv": 1.0,
    }
    threshold_config = threshold_config or default_thresholds

    if not trace_data:
        return {
            "metrics": {},
            "valid": False,
            "message": "输入的网络剖面列表为空",
            "score": 0.0,
        }

    # 计算各项指标
    metrics = calculate_all_metrics(trace_data)

    # 评估指标是否符合阈值
    valid = _validate_metrics(metrics, threshold_config)

    # 计算评估分数(0-100)
    score = _calculate_score(metrics)

    # 生成评估报告
    return {
        "metrics": metrics,
        "valid": valid,
        "message": "网络参数序列评估通过" if valid else "网络参数序列评估未通过",
        "score": score,
    }


def _validate_metrics(metrics: Dict[str, float], threshold_config: Dict[str, float]) -> bool:
    """验证指标是否符合阈值

    验证计算得到的指标是否符合给定的阈值配置。

    Args:
        metrics: 指标字典
        threshold_config: 阈值配置字典

    Returns:
        bool: 是否符合阈值

    Examples:
        # 验证指标是否符合阈值
        valid = _validate_metrics(metrics, threshold_config)
        print(f"指标是否符合阈值: {valid}")
    """
    # 检查RTT 最大值
    if metrics["max_rtt"] > threshold_config.get("max_rtt", 2000.0):
        return False

    # 检查丢包率最大值
    if metrics["max_loss_rate"] > threshold_config.get("max_loss_rate", 1.0):
        return False

    # 检查带宽最小值
    if metrics["min_bandwidth"] < threshold_config.get("min_bandwidth", 0.0):
        return False

    # 检查RTT 变异系数
    if metrics["rtt_cv"] > threshold_config.get("rtt_cv", 1.0):
        return False

    # 检查丢包率变异系数
    if metrics["loss_rate_cv"] > threshold_config.get("loss_rate_cv", 1.0):
        return False

    # 检查带宽变异系数
    if metrics["bandwidth_cv"] > threshold_config.get("bandwidth_cv", 1.0):
        return False

    return True


def _calculate_score(metrics: Dict[str, float]) -> float:
    """计算评估分数(0-100)

    根据计算得到的指标，计算网络轨迹的评估分数（0-100分）。

    Args:
        metrics: 指标字典

    Returns:
        float: 评估分数

    Examples:
        # 计算评估分数
        score = _calculate_score(metrics)
        print(f"评估分数: {score}")
    """
    # RTT 分数(30分)
    # 较低的RTT 和RTT 变异系数得分更高
    rtt_score = 30.0
    rtt_score -= min(metrics["avg_rtt"] / 2000.0 * 15.0, 15.0)  # 平均 RTT 占 15 分
    rtt_score -= min(metrics["rtt_cv"] / 1.0 * 15.0, 15.0)  # RTT 变异系数占 15 分

    # 丢包率分数(30分)
    # 较低的丢包率和丢包率变异系数得分更高
    loss_score = 30.0
    loss_score -= min(metrics["avg_loss_rate"] / 1.0 * 15.0, 15.0)  # 平均丢包率占 15 分
    loss_score -= min(metrics["loss_rate_cv"] / 1.0 * 15.0, 15.0)  # 丢包率变异系数占 15 分

    # 带宽分数(30分)
    # 较高的带宽和较低的带宽变异系数得分更高
    bandwidth_score = 30.0
    bandwidth_score -= min(1.0 - metrics["avg_bandwidth"] / 100.0 * 15.0, 15.0)  # 平均带宽占 15 分
    bandwidth_score -= min(metrics["bandwidth_cv"] / 1.0 * 15.0, 15.0)  # 带宽变异系数占 15 分

    # 序列分数(10分)
    # 较低的跳变次数得分更高
    sequence_score = 10.0
    total_jumps = metrics["rtt_jump_count"] + metrics["loss_jump_count"] + metrics["bandwidth_jump_count"]
    sequence_score -= min(total_jumps / 100.0 * 10.0, 10.0)  # 跳变次数占 10 分

    # 计算总分
    total_score = rtt_score + loss_score + bandwidth_score + sequence_score

    # 确保分数在0-100 范围内
    return max(0.0, min(total_score, 100.0))


def compare_traces(
    trace1: List[Union[RawProfile, ProcessedProfile]], trace2: List[Union[RawProfile, ProcessedProfile]]
) -> Dict[str, any]:
    """比较两个网络轨迹的相似性

    比较两个网络轨迹的相似性，计算相似性分数和各项指标的差异。

    Args:
        trace1: 第一个 RawProfile 或 ProcessedProfile 列表
        trace2: 第二个 RawProfile 或 ProcessedProfile 列表

    Returns:
        Dict[str, any]: 比较结果，包含相似性分数和各项指标的差异

    Examples:
        # 比较两个网络轨迹
        result = compare_traces(trace1, trace2)
        print(f"比较结果: {result}")
    """
    # 计算两个序列的指标
    metrics1 = calculate_all_metrics(trace1)
    metrics2 = calculate_all_metrics(trace2)

    # 计算指标差异
    differences = {}
    for key in metrics1:
        if key in metrics2:
            diff = abs(metrics1[key] - metrics2[key])
            differences[key] = diff

    # 计算相似性分数(0-100)
    similarity_score = _calculate_similarity_score(metrics1, metrics2)

    return {
        "similarity_score": similarity_score,
        "differences": differences,
        "metrics1": metrics1,
        "metrics2": metrics2,
        "message": f"两个网络参数序列的相似性得分为 {similarity_score:.2f}",
    }


def _calculate_similarity_score(metrics1: Dict[str, float], metrics2: Dict[str, float]) -> float:
    """计算两个指标字典的相似性分数(0-100)

    计算两个指标字典的相似性分数，基于关键指标的相对差异。

    Args:
        metrics1: 第一个指标字典
        metrics2: 第二个指标字典

    Returns:
        float: 相似性分数

    Examples:
        # 计算相似性分数
        similarity_score = _calculate_similarity_score(metrics1, metrics2)
        print(f"相似性分数: {similarity_score}")
    """
    # 选择关键指标进行比较
    key_metrics = [
        "avg_rtt",
        "std_rtt",
        "avg_loss_rate",
        "std_loss_rate",
        "avg_bandwidth",
        "std_bandwidth",
        "rtt_cv",
        "loss_rate_cv",
        "bandwidth_cv",
    ]

    # 计算每个关键指标的相似度
    similarities = []
    for metric_name in key_metrics:
        if metric_name in metrics1 and metric_name in metrics2:
            val1 = metrics1[metric_name]
            val2 = metrics2[metric_name]

            # 计算相对差异
            if val1 == 0 and val2 == 0:
                similarity = 1.0
            elif val1 == 0 or val2 == 0:
                similarity = 0.0
            else:
                similarity = 1.0 - min(abs(val1 - val2) / max(val1, val2), 1.0)

            similarities.append(similarity)

    # 计算平均相似性
    if not similarities:
        return 0.0

    avg_similarity = sum(similarities) / len(similarities)

    # 转换为0-100 分数
    return avg_similarity * 100.0


def generate_trace_report(trace_data: List[Union[RawProfile, ProcessedProfile]]) -> str:
    """生成轨迹评估报告(文本格式)

    生成网络轨迹的评估报告，包含各项指标和评估结论。

    Args:
        trace_data: RawProfile 或 ProcessedProfile 列表

    Returns:
        str: 评估报告文本

    Examples:
        # 生成轨迹评估报告
        report = generate_trace_report(trace_data)
        print(report)
    """
    evaluation = validate_trace(trace_data)

    # 生成报告
    report = [
        "=== 网络参数序列评估报告 ===",
        f"评估结果: {'通过' if evaluation['valid'] else '未通过'}",
        f"评估分数: {evaluation['score']:.2f}/100",
        f"评估时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "=== 各项指标 ===",
    ]

    # 添加指标信息
    metrics = evaluation["metrics"]
    for key, value in metrics.items():
        report.append(f"{key}: {value:.4f}")

    # 添加评估结论
    report.append("")
    report.append(f"评估结论: {evaluation['message']}")

    return "\n".join(report)


def validate_trace_realism(
    trace_data: List[Union[RawProfile, ProcessedProfile]], threshold_config: Optional[Dict[str, float]] = None
) -> Dict[str, any]:
    """验证网络轨迹的真实性

    验证网络轨迹的真实性，检查各项指标是否符合真实网络的特征。

    Args:
        trace_data: RawProfile 或 ProcessedProfile 列表
        threshold_config: 评估阈值配置

    Returns:
        Dict[str, any]: 真实性验证结果

    Examples:
        # 验证网络轨迹的真实性
        realism = validate_trace_realism(trace_data)
        print(f"真实性验证结果: {realism}")
    """
    # 默认阈值配置
    default_thresholds = {
        "rtt_cv": 1.0,
        "loss_rate_cv": 1.0,
        "bandwidth_cv": 1.0,
    }
    threshold_config = threshold_config or default_thresholds

    # 计算指标
    metrics = calculate_all_metrics(trace_data)

    # 处理空输入的情况
    if not metrics:
        return {
            "realism_checks": {
                "rtt_bandwidth_correlation": False,
                "loss_bandwidth_correlation": False,
                "rtt_loss_correlation": False,
                "reasonable_cv": False,
            },
            "realism_score": 0.0,
            "metrics": {},
            "message": "输入的网络剖面列表为空，无法评估真实性",
        }

    # 验证真实性
    realism_checks = {
        # 检查RTT 和带宽的负相关性
        "rtt_bandwidth_correlation": metrics["rtt_bandwidth_corr"] < 0,
        # 检查丢包率和带宽的负相关性
        "loss_bandwidth_correlation": metrics["loss_bandwidth_corr"] < 0,
        # 检查RTT 和丢包率的正相关性
        "rtt_loss_correlation": metrics["rtt_loss_corr"] > 0,
        # 检查变异系数是否合理
        "reasonable_cv": (
            metrics["rtt_cv"] < threshold_config.get("rtt_cv", 1.0)
            and metrics["loss_rate_cv"] < threshold_config.get("loss_rate_cv", 1.0)
            and metrics["bandwidth_cv"] < threshold_config.get("bandwidth_cv", 1.0)
        ),
    }

    # 计算真实性分数(0-100)
    realism_score = sum(realism_checks.values()) / len(realism_checks) * 100.0

    return {
        "realism_checks": realism_checks,
        "realism_score": realism_score,
        "metrics": metrics,
        "message": f"网络参数序列的真实性得分为 {realism_score:.2f}",
    }
