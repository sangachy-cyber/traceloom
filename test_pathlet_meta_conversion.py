#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 PathletMeta 转换功能"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from traceloom.io.adapters.holowan import HoloWANTrace, HoloWANPoint, HoloWANDirection
from traceloom.domain.pathlet import PathletMeta

def test_extended_sliding_windows_returns_pathlet_meta_and_pathlet():
    """测试 extended_sliding_windows 函数返回 (PathletMeta, Pathlet) 元组"""
    print("测试 extended_sliding_windows 函数...")
    
    # 创建HoloWANTrace实例
    holowan_trace = HoloWANTrace()
    
    # 添加足够的数据点（至少110个）
    for i in range(120):
        data_point = HoloWANPoint(
            up=HoloWANDirection(delay=100.0 + i, loss=0.01, bw=10.0), 
            down=HoloWANDirection(delay=95.0 + i, loss=0.01, bw=12.0)
        )
        holowan_trace.points.append(data_point)
    
    print(f"✓ 添加数据点成功，共添加了 {len(holowan_trace.points)} 个数据点")
    
    # 调用 extended_sliding_windows 函数
    results = list(holowan_trace.extended_sliding_windows())
    
    print(f"✓ 调用 extended_sliding_windows 成功，返回了 {len(results)} 个 (PathletMeta, Pathlet) 元组")
    
    # 验证返回类型
    from traceloom.domain.pathlet import Pathlet
    for i, (pathlet_meta, pathlet) in enumerate(results):
        assert isinstance(pathlet_meta, PathletMeta), f"第 {i} 个元素的第一个值不是 PathletMeta 对象"
        assert isinstance(pathlet, Pathlet), f"第 {i} 个元素的第二个值不是 Pathlet 对象"
        assert len(pathlet_meta.observations) == 110, f"第 {i} 个 PathletMeta 对象的 observations 长度不是 110"
        assert len(pathlet.body.observations) == 100, f"第 {i} 个 Pathlet 对象的 body.observations 长度不是 100"
        assert len(pathlet.tail.observations) == 10, f"第 {i} 个 Pathlet 对象的 tail.observations 长度不是 10"
        print(f"✓ 第 {i} 个返回值是 (PathletMeta, Pathlet) 元组，Pathlet ID: {pathlet.pathlet_id}")
    
    return True

def test_filtered_extended_sliding_windows_returns_pathlet_meta_and_pathlet():
    """测试 filtered_extended_sliding_windows 函数返回 (PathletMeta, Pathlet) 元组"""
    print("\n测试 filtered_extended_sliding_windows 函数...")
    
    # 创建HoloWANTrace实例
    holowan_trace = HoloWANTrace()
    
    # 添加足够的数据点（至少110个）
    for i in range(120):
        data_point = HoloWANPoint(
            up=HoloWANDirection(delay=100.0 + i, loss=0.01, bw=10.0), 
            down=HoloWANDirection(delay=95.0 + i, loss=0.01, bw=12.0)
        )
        holowan_trace.points.append(data_point)
    
    print(f"✓ 添加数据点成功，共添加了 {len(holowan_trace.points)} 个数据点")
    
    # 调用 filtered_extended_sliding_windows 函数
    results = list(holowan_trace.filtered_extended_sliding_windows())
    
    print(f"✓ 调用 filtered_extended_sliding_windows 成功，返回了 {len(results)} 个 (PathletMeta, Pathlet) 元组")
    
    # 验证返回类型
    from traceloom.domain.pathlet import Pathlet
    for i, (pathlet_meta, pathlet) in enumerate(results):
        assert isinstance(pathlet_meta, PathletMeta), f"第 {i} 个元素的第一个值不是 PathletMeta 对象"
        assert isinstance(pathlet, Pathlet), f"第 {i} 个元素的第二个值不是 Pathlet 对象"
        assert len(pathlet_meta.observations) == 110, f"第 {i} 个 PathletMeta 对象的 observations 长度不是 110"
        assert len(pathlet.body.observations) == 100, f"第 {i} 个 Pathlet 对象的 body.observations 长度不是 100"
        assert len(pathlet.tail.observations) == 10, f"第 {i} 个 Pathlet 对象的 tail.observations 长度不是 10"
        print(f"✓ 第 {i} 个返回值是 (PathletMeta, Pathlet) 元组，Pathlet ID: {pathlet.pathlet_id}")
    
    return True

def test_get_filtered_extended_windows_with_stats_returns_pathlet_meta_and_pathlet():
    """测试 get_filtered_extended_windows_with_stats 函数返回 (PathletMeta, Pathlet) 元组列表"""
    print("\n测试 get_filtered_extended_windows_with_stats 函数...")
    
    # 创建HoloWANTrace实例
    holowan_trace = HoloWANTrace()
    
    # 添加足够的数据点（至少110个）
    for i in range(120):
        data_point = HoloWANPoint(
            up=HoloWANDirection(delay=100.0 + i, loss=0.01, bw=10.0), 
            down=HoloWANDirection(delay=95.0 + i, loss=0.01, bw=12.0)
        )
        holowan_trace.points.append(data_point)
    
    print(f"✓ 添加数据点成功，共添加了 {len(holowan_trace.points)} 个数据点")
    
    # 调用 get_filtered_extended_windows_with_stats 函数
    results, stats = holowan_trace.get_filtered_extended_windows_with_stats()
    
    print(f"✓ 调用 get_filtered_extended_windows_with_stats 成功，返回了 {len(results)} 个 (PathletMeta, Pathlet) 元组和统计信息")
    print(f"  统计信息: {stats}")
    
    # 验证返回类型
    from traceloom.domain.pathlet import Pathlet
    for i, (pathlet_meta, pathlet) in enumerate(results):
        assert isinstance(pathlet_meta, PathletMeta), f"第 {i} 个元素的第一个值不是 PathletMeta 对象"
        assert isinstance(pathlet, Pathlet), f"第 {i} 个元素的第二个值不是 Pathlet 对象"
        assert len(pathlet_meta.observations) == 110, f"第 {i} 个 PathletMeta 对象的 observations 长度不是 110"
        assert len(pathlet.body.observations) == 100, f"第 {i} 个 Pathlet 对象的 body.observations 长度不是 100"
        assert len(pathlet.tail.observations) == 10, f"第 {i} 个 Pathlet 对象的 tail.observations 长度不是 10"
        print(f"✓ 第 {i} 个返回值是 (PathletMeta, Pathlet) 元组，Pathlet ID: {pathlet.pathlet_id}")
    
    return True

def run_all_tests():
    """运行所有测试"""
    print("=== 运行所有 PathletMeta 转换测试 ===")
    
    # 运行所有测试
    test_extended_sliding_windows_returns_pathlet_meta_and_pathlet()
    test_filtered_extended_sliding_windows_returns_pathlet_meta_and_pathlet()
    test_get_filtered_extended_windows_with_stats_returns_pathlet_meta_and_pathlet()
    
    print("\n=== 测试结果汇总 ===")
    print("✅ 所有测试通过！")
    return 0

if __name__ == "__main__":
    sys.exit(run_all_tests())
