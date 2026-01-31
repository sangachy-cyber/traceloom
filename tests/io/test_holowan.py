#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试HoloWAN相关功能"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from traceloom.io.adapters._holowan import HoloWANTrace, HoloWANPoint, HoloWANDirection
from traceloom.domain.pathlet import Observation


def test_holowan_file_basic():
    """测试HoloWANTrace类的基本功能"""
    print("测试HoloWANTrace类...")

    # 创建HoloWANTrace实例
    holowan_trace = HoloWANTrace()
    print("✓ 创建HoloWANTrace实例成功")
    assert isinstance(holowan_trace, HoloWANTrace)

    # 添加数据点
    data_point1 = HoloWANPoint(
        up=HoloWANDirection(delay=100.0, loss=0.1, bw=10.0), down=HoloWANDirection(delay=95.0, loss=0.0, bw=12.0)
    )
    data_point2 = HoloWANPoint(
        up=HoloWANDirection(delay=105.0, loss=0.2, bw=9.5), down=HoloWANDirection(delay=98.0, loss=0.1, bw=11.5)
    )
    holowan_trace.points.append(data_point1)
    holowan_trace.points.append(data_point2)
    print(f"✓ 添加数据点成功，共添加了 {len(holowan_trace.points)} 个数据点")
    assert len(holowan_trace.points) == 2

    # 生成文件
    output_path = Path("test_output.hwan")
    holowan_trace.dump(output_path)
    print(f"✓ 生成HoloWAN文件成功: {output_path}")
    assert output_path.exists()

    # 验证文件内容
    with open(output_path, "r") as f:
        content = f.read()
    assert "HoloWAN Recorder File" in content
    print("✓ 验证文件内容成功")

    # 清理生成的文件
    output_path.unlink()
    print("✓ 清理生成的文件成功")
    assert not output_path.exists()

    print("HoloWANTrace类基本功能测试完成！")


def test_holowan_file_enhanced_features():
    """测试HoloWANTrace的增强功能"""
    print("\n测试HoloWANTrace增强功能...")

    # 测试load方法是否存在
    assert hasattr(HoloWANTrace, "load"), "HoloWANTrace.load静态方法不存在"
    print("✓ HoloWANTrace.load静态方法存在")

    # 测试from_observations方法是否存在
    assert hasattr(HoloWANTrace, "from_observations"), "HoloWANTrace.from_observations静态方法不存在"
    print("✓ HoloWANTrace.from_observations静态方法存在")


def test_holowan_file_with_compact_state_str():
    """测试HoloWANTrace的基本功能"""
    print("\n测试HoloWANTrace基本功能...")

    # 创建HoloWANTrace实例
    holowan_trace = HoloWANTrace()

    # 添加数据点
    data_point1 = HoloWANPoint(
        up=HoloWANDirection(delay=100.0, loss=0.1, bw=10.0), down=HoloWANDirection(delay=95.0, loss=0.0, bw=12.0)
    )
    data_point2 = HoloWANPoint(
        up=HoloWANDirection(delay=105.0, loss=0.2, bw=9.5), down=HoloWANDirection(delay=98.0, loss=0.1, bw=11.5)
    )
    data_point3 = HoloWANPoint(
        up=HoloWANDirection(delay=110.0, loss=0.15, bw=9.8), down=HoloWANDirection(delay=100.0, loss=0.05, bw=11.0)
    )
    holowan_trace.points.append(data_point1)
    holowan_trace.points.append(data_point2)
    holowan_trace.points.append(data_point3)
    print(f"✓ 添加数据点成功，共添加了 {len(holowan_trace.points)} 个数据点")

    # 生成文件
    output_path = Path("test_output_with_state.hwan")
    holowan_trace.dump(output_path)
    print(f"✓ 生成HoloWAN文件成功: {output_path}")
    assert output_path.exists()

    # 验证文件内容
    with open(output_path, "r") as f:
        content = f.read()
    assert "HoloWANDirection Recorder File" not in content  # 检查是否是正确的文件格式
    print("✓ 验证文件内容成功")

    # 验证原有头信息也存在
    assert 'Operator: "' in content
    assert "test_name:" in content
    assert "------------------------------------------------" in content
    print("✓ 验证原有头信息成功")

    # 清理生成的文件
    output_path.unlink()
    print("✓ 清理生成的文件成功")
    assert not output_path.exists()

    print("HoloWANTrace基本功能测试完成！")


def test_holowan_from_observations():
    """测试从观测数据创建HoloWANTrace"""
    print("\n测试从观测数据创建HoloWANTrace...")

    # 创建观测数据
    observations = [
        Observation(delay_up=100.0, loss_up=0.1, bw_up=10.0, delay_down=95.0, loss_down=0.0, bw_down=12.0),
        Observation(delay_up=105.0, loss_up=0.2, bw_up=9.5, delay_down=98.0, loss_down=0.1, bw_down=11.5),
    ]

    # 从观测数据创建HoloWANTrace
    holowan_trace = HoloWANTrace.from_observations(observations)
    print(f"✓ 从观测数据创建HoloWANTrace成功，共包含 {len(holowan_trace.points)} 个数据点")
    assert len(holowan_trace.points) == 2

    # 验证数据点转换正确
    assert holowan_trace.points[0].up.delay == 100.0
    assert holowan_trace.points[0].down.delay == 95.0
    print("✓ 验证数据点转换正确")

    print("从观测数据创建HoloWANTrace测试完成！")


def run_all_tests():
    """运行所有HoloWAN相关测试"""
    print("=== 运行所有HoloWAN相关测试 ===")

    # 运行所有测试
    test_holowan_file_basic()
    test_holowan_file_enhanced_features()
    test_holowan_file_with_compact_state_str()
    test_holowan_from_observations()

    print("\n=== 测试结果汇总 ===")
    print("✅ 所有测试通过！")
    return 0


if __name__ == "__main__":
    sys.exit(run_all_tests())
