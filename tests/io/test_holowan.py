#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试HoloWAN相关功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from traceloom.io.adapters.holowan import HoloWANTrace


def test_holowan_file_basic():
    """测试HoloWANTrace类的基本功能"""
    print("测试HoloWANTrace类...")

    # 创建HoloWANTrace实例
    holowan_trace = HoloWANTrace()
    print("✓ 创建HoloWANTrace实例成功")
    assert isinstance(holowan_trace, HoloWANTrace)

    # 添加数据点
    from traceloom.io.adapters.holowan import HoloWANDataPoint, HoloWANDirection
    data_point1 = HoloWANDataPoint(
        up=HoloWANDirection(delay=100.0, loss=0.1, bw=10.0),
        down=HoloWANDirection(delay=95.0, loss=0.0, bw=12.0)
    )
    data_point2 = HoloWANDataPoint(
        up=HoloWANDirection(delay=105.0, loss=0.2, bw=9.5),
        down=HoloWANDirection(delay=98.0, loss=0.1, bw=11.5)
    )
    holowan_trace.data_points.append(data_point1)
    holowan_trace.data_points.append(data_point2)
    print(f"✓ 添加数据点成功，共添加了 {len(holowan_trace.data_points)} 个数据点")
    assert len(holowan_trace.data_points) == 2

    # 计算统计信息
    holowan_trace._calculate_statistics()
    print(f"✓ 计算统计信息成功，平均丢包率: {holowan_trace.loss_average:.2f}%")
    assert holowan_trace.loss_average > 0

    # 生成文件（不带状态序列）
    output_path = Path("test_output.hwan")
    HoloWANTrace.save(output_path, holowan_trace)
    print(f"✓ 生成HoloWAN文件成功: {output_path}")
    assert output_path.exists()

    # 验证文件内容（无状态序列）
    with open(output_path, "r") as f:
        content = f.read()
    assert "# HoloWAN Playback v1.0" in content
    print("✓ 验证无状态序列文件内容成功")

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

    # 测试save方法是否存在
    assert hasattr(HoloWANTrace, "save"), "HoloWANTrace.save静态方法不存在"
    print("✓ HoloWANTrace.save静态方法存在")


def test_holowan_file_with_compact_state_str():
    """测试HoloWANTrace的基本功能"""
    print("\n测试HoloWANTrace基本功能...")

    # 创建HoloWANTrace实例
    holowan_trace = HoloWANTrace()

    # 添加数据点
    from traceloom.io.adapters.holowan import HoloWANDataPoint, HoloWANDirection
    data_point1 = HoloWANDataPoint(
        up=HoloWANDirection(delay=100.0, loss=0.1, bw=10.0),
        down=HoloWANDirection(delay=95.0, loss=0.0, bw=12.0)
    )
    data_point2 = HoloWANDataPoint(
        up=HoloWANDirection(delay=105.0, loss=0.2, bw=9.5),
        down=HoloWANDirection(delay=98.0, loss=0.1, bw=11.5)
    )
    data_point3 = HoloWANDataPoint(
        up=HoloWANDirection(delay=110.0, loss=0.15, bw=9.8),
        down=HoloWANDirection(delay=100.0, loss=0.05, bw=11.0)
    )
    holowan_trace.data_points.append(data_point1)
    holowan_trace.data_points.append(data_point2)
    holowan_trace.data_points.append(data_point3)
    print(f"✓ 添加数据点成功，共添加了 {len(holowan_trace.data_points)} 个数据点")

    # 生成文件
    output_path = Path("test_output_with_state.hwan")
    HoloWANTrace.save(output_path, holowan_trace)
    print(f"✓ 生成HoloWAN文件成功: {output_path}")
    assert output_path.exists()

    # 验证文件内容
    with open(output_path, "r") as f:
        content = f.read()
    assert "# HoloWAN Playback v1.0" in content
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











def run_all_tests():
    """运行所有HoloWAN相关测试"""
    print("=== 运行所有HoloWAN相关测试 ===")

    # 运行所有测试
    test_holowan_file_basic()
    test_holowan_file_enhanced_features()
    test_holowan_file_with_compact_state_str()

    print("\n=== 测试结果汇总 ===")
    print("✅ 所有测试通过！")
    return 0


if __name__ == "__main__":
    sys.exit(run_all_tests())
