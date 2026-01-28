# -*- coding: utf-8 -*-
"""测试织样（Pattern）类"""

import pytest

from traceloom.domain.pattern import Pattern


def test_pattern_from_string():
    """测试从字符串创建织样"""
    # 测试基本功能
    pattern_str = "s0x2 -> s2x6"
    pattern = Pattern.from_string(pattern_str)
    assert pattern.sequence == [("s0", 20), ("s2", 60)]
    assert pattern.to_string() == pattern_str

    # 测试空白处理
    pattern_str = "s0x2->s2x6"
    pattern = Pattern.from_string(pattern_str)
    assert pattern.to_string() == "s0x2 -> s2x6"

    # 测试单个状态
    pattern_str = "s1x5"
    pattern = Pattern.from_string(pattern_str)
    assert pattern.sequence == [("s1", 50)]
    assert pattern.to_string() == pattern_str


def test_pattern_from_json():
    """测试从JSON列表创建织样"""
    # 测试基本功能
    json_data = [{"state": "s0", "duration": 20}, {"state": "s2", "duration": 60}]
    pattern = Pattern.from_json(json_data)
    assert pattern.sequence == [("s0", 20), ("s2", 60)]

    # 测试转换为字符串
    assert pattern.to_string() == "s0x2 -> s2x6"

    # 测试单个状态
    json_data = [{"state": "s1", "duration": 50}]
    pattern = Pattern.from_json(json_data)
    assert pattern.sequence == [("s1", 50)]


def test_pattern_validation():
    """测试织样验证"""
    # 测试无效状态名
    with pytest.raises(ValueError, match="无效的状态名"):
        Pattern([("invalid_state", 20)])

    # 测试无效持续时间
    with pytest.raises(ValueError, match="持续时间必须为正数"):
        Pattern([("s0", -1)])

    with pytest.raises(ValueError, match="持续时间必须为正数"):
        Pattern([("s0", 0)])


def test_pattern_equality():
    """测试织样相等性比较"""
    pattern1 = Pattern.from_string("s0x2 -> s2x6")
    pattern2 = Pattern.from_string("s0x2 -> s2x6")
    pattern3 = Pattern.from_string("s0x1 -> s2x6")

    assert pattern1 == pattern2
    assert pattern1 != pattern3
    assert pattern1 != "s0x2 -> s2x6"  # 与字符串比较


def test_pattern_len():
    """测试织样长度计算"""
    pattern1 = Pattern.from_string("s0x2")
    pattern2 = Pattern.from_string("s0x2 -> s2x6")
    pattern3 = Pattern.from_string("s0x2 -> s2x6 -> s1x3")

    assert len(pattern1) == 1
    assert len(pattern2) == 2
    assert len(pattern3) == 3


def test_pattern_repr():
    """测试织样字符串表示"""
    pattern_str = "s0x2 -> s2x6"
    pattern = Pattern.from_string(pattern_str)
    assert repr(pattern) == f"Pattern({pattern_str})"


def test_pattern_to_json():
    """测试织样转换为JSON"""
    # 测试基本功能
    pattern = Pattern.from_string("s0x2 -> s2x6")
    json_data = pattern.to_json()
    assert json_data == [{"state": "s0", "duration": 20}, {"state": "s2", "duration": 60}]

    # 测试从JSON创建再转换回JSON
    pattern2 = Pattern.from_json(json_data)
    assert pattern2.to_json() == json_data


def test_pattern_invalid_string():
    """测试无效字符串格式"""
    # 测试无效格式
    with pytest.raises(ValueError, match="无效的织样段"):
        Pattern.from_string("invalid_format")

    # 测试缺少x分隔符
    with pytest.raises(ValueError, match="无效的织样段"):
        Pattern.from_string("s0 2 -> s2 6")


def test_pattern_invalid_json():
    """测试无效JSON格式"""
    # 测试缺少state字段
    with pytest.raises(ValueError, match="织样项必须包含'state'和'duration'"):
        Pattern.from_json([{"duration": 20}])

    # 测试缺少duration字段
    with pytest.raises(ValueError, match="织样项必须包含'state'和'duration'"):
        Pattern.from_json([{"state": "s0"}])

    # 测试非字典项
    with pytest.raises(ValueError, match="织样项必须是字典"):
        Pattern.from_json(["s0", 20])


def test_pattern_roundtrip():
    """测试织样往返转换"""
    original_str = "s0x2 -> s2x6 -> s1x3"
    pattern = Pattern.from_string(original_str)
    converted_str = pattern.to_string()
    assert converted_str == original_str

    # 测试JSON往返
    json_data = [{"state": "s0", "duration": 20}, {"state": "s2", "duration": 60}]
    pattern = Pattern.from_json(json_data)
    converted_json = pattern.to_json()
    assert converted_json == json_data
