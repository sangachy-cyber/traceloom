# -*- coding: utf-8 -*-
"""输入验证模块测试

测试validators模块的功能
"""

import pytest

from traceloom.core.exceptions import ValidationError as TraceLoomValidationError
from traceloom.core.validators import (
    APIValidator,
    BaseValidator,
    PathletCreate,
    PathletQuery,
    PathletValidator,
    PatternValidator,
    WeaveRequest,
    validate_input,
)


def test_base_validator_pathlet_id():
    """测试径元ID验证"""
    # 有效的径元ID
    assert BaseValidator.validate_pathlet_id("pathlet_001") is True
    assert BaseValidator.validate_pathlet_id("PATHLET_123") is True
    assert BaseValidator.validate_pathlet_id("p123") is True

    # 无效的径元ID
    assert BaseValidator.validate_pathlet_id("pathlet-001") is False
    assert BaseValidator.validate_pathlet_id("pathlet@001") is False
    assert BaseValidator.validate_pathlet_id("") is False


def test_base_validator_trace_name():
    """测试轨迹名称验证"""
    # 有效的轨迹名称
    assert BaseValidator.validate_trace_name("trace_001") is True
    assert BaseValidator.validate_trace_name("trace-001") is True
    assert BaseValidator.validate_trace_name("TRACE_123") is True

    # 无效的轨迹名称
    assert BaseValidator.validate_trace_name("trace@001") is False
    assert BaseValidator.validate_trace_name("") is False


def test_base_validator_state_id():
    """测试状态ID验证"""
    # 有效的状态ID
    assert BaseValidator.validate_state_id(0) is True
    assert BaseValidator.validate_state_id(5) is True
    assert BaseValidator.validate_state_id(-1) is True

    # 无效的状态ID
    assert BaseValidator.validate_state_id(-2) is False
    assert BaseValidator.validate_state_id("0") is False
    assert BaseValidator.validate_state_id(None) is False


def test_base_validator_delay():
    """测试时延值验证"""
    # 有效的时延值
    assert BaseValidator.validate_delay(0) is True
    assert BaseValidator.validate_delay(1000) is True
    assert BaseValidator.validate_delay(2000) is True
    assert BaseValidator.validate_delay(500.5) is True

    # 无效的时延值
    assert BaseValidator.validate_delay(-1) is False
    assert BaseValidator.validate_delay(2001) is False
    assert BaseValidator.validate_delay("100") is False


def test_base_validator_loss():
    """测试丢包率验证"""
    # 有效的丢包率
    assert BaseValidator.validate_loss(0) is True
    assert BaseValidator.validate_loss(0.5) is True
    assert BaseValidator.validate_loss(1.0) is True
    assert BaseValidator.validate_loss(-0.01) is True
    assert BaseValidator.validate_loss(1.01) is True

    # 无效的丢包率
    assert BaseValidator.validate_loss(-0.02) is False
    assert BaseValidator.validate_loss(1.02) is False
    assert BaseValidator.validate_loss("0.5") is False


def test_base_validator_bandwidth():
    """测试带宽验证"""
    # 有效的带宽
    assert BaseValidator.validate_bandwidth(0) is True
    assert BaseValidator.validate_bandwidth(100) is True
    assert BaseValidator.validate_bandwidth(1000.5) is True

    # 无效的带宽
    assert BaseValidator.validate_bandwidth(-1) is False
    assert BaseValidator.validate_bandwidth("100") is False


def test_base_validator_dataset():
    """测试数据集划分验证"""
    # 有效的数据集划分
    assert BaseValidator.validate_dataset("train") is True
    assert BaseValidator.validate_dataset("test") is True
    assert BaseValidator.validate_dataset("val") is True

    # 无效的数据集划分
    assert BaseValidator.validate_dataset("training") is False
    assert BaseValidator.validate_dataset("") is False


def test_pathlet_validator_validate_pathlet_data():
    """测试径元数据验证"""
    # 有效的径元数据
    valid_data = {"pathlet_id": "pathlet_001", "trace_name": "trace_001", "start_index": 0, "dataset": "train"}
    result = PathletValidator.validate_pathlet_data(valid_data)
    assert result == valid_data

    # 无效的径元ID
    invalid_data = {"pathlet_id": "pathlet@001", "trace_name": "trace_001", "start_index": 0, "dataset": "train"}
    with pytest.raises(TraceLoomValidationError):
        PathletValidator.validate_pathlet_data(invalid_data)


def test_pattern_validator_validate_pattern_string():
    """测试织样字符串验证"""
    # 有效的织样字符串
    assert PatternValidator.validate_pattern_string("s0x2 -> s1x3") is True
    assert PatternValidator.validate_pattern_string("s0x2") is True
    assert PatternValidator.validate_pattern_string("s0x2 -> s1x3 -> s2x1") is True

    # 无效的织样字符串
    assert PatternValidator.validate_pattern_string("s0x2 -> ") is False
    assert PatternValidator.validate_pattern_string("") is False


def test_pattern_validator_validate_state_duration():
    """测试状态-持续时间对验证"""
    # 有效的状态-持续时间对
    assert PatternValidator.validate_state_duration(("s0", 2)) is True
    assert PatternValidator.validate_state_duration(("s1", 3.5)) is True

    # 无效的状态-持续时间对
    assert PatternValidator.validate_state_duration(("s0", -1)) is False
    assert PatternValidator.validate_state_duration(("s0", "2")) is False
    assert PatternValidator.validate_state_duration(("s0",)) is False


def test_api_validator_validate_api_input():
    """测试API输入类型验证"""
    assert APIValidator.validate_api_input("test", str) is True
    assert APIValidator.validate_api_input(123, int) is True
    assert APIValidator.validate_api_input("test", int) is False


def test_api_validator_validate_query_params():
    """测试查询参数验证"""
    params = {"state_id": 0, "dataset": "train"}
    required = ["state_id", "dataset"]
    assert APIValidator.validate_query_params(params, required) is True

    params = {"state_id": 0}
    required = ["state_id", "dataset"]
    assert APIValidator.validate_query_params(params, required) is False


def test_pydantic_models():
    """测试Pydantic模型验证"""
    # 测试PathletCreate
    valid_pathlet = PathletCreate(pathlet_id="pathlet_001", trace_name="trace_001", start_index=0, dataset="train")
    assert valid_pathlet.pathlet_id == "pathlet_001"

    # 测试无效的PathletCreate
    with pytest.raises(TraceLoomValidationError):
        PathletCreate(
            pathlet_id="pathlet@001",  # 无效的径元ID
            trace_name="trace_001",
            start_index=0,
            dataset="train",
        )

    # 测试WeaveRequest
    valid_weave = WeaveRequest(input_data="s0x2 -> s1x3", mode="reweave")
    assert valid_weave.mode == "reweave"

    # 测试无效的WeaveRequest
    with pytest.raises(TraceLoomValidationError):
        WeaveRequest(
            input_data="s0x2 -> s1x3",
            mode="invalid_mode",  # 无效的模式
        )

    # 测试PathletQuery
    valid_query = PathletQuery(state_id=0, is_valid=True, dataset="train", batch_size=10)
    assert valid_query.state_id == 0


def test_validate_input():
    """测试通用输入验证函数"""
    # 测试基本验证
    data = {"key": "value"}
    result = validate_input(data)
    assert result == data

    # 测试带验证器的验证
    valid_data = {"pathlet_id": "pathlet_001", "trace_name": "trace_001", "start_index": 0, "dataset": "train"}
    result = validate_input(valid_data, PathletValidator)
    assert result == valid_data


if __name__ == "__main__":
    pytest.main([__file__])
