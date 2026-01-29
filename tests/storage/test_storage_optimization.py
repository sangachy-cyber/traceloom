# -*- coding: utf-8 -*-
"""测试存储空间优化效果

比较使用新存储结构前后的存储空间使用情况
"""

import tempfile
import shutil
import os
from pathlib import Path
from traceloom.domain.pathlet import Pathlet, BodyObservations, TailObservations, Observation
from traceloom.domain.raw_trace import RawTraceSegment
from traceloom.storage.pathlet_storage import PathletStorage


def get_directory_size(directory):
    """获取目录大小（字节）"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.isfile(filepath):
                total_size += os.path.getsize(filepath)
    return total_size

def test_storage_optimization():
    """测试存储空间优化效果"""
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    try:
        # 创建存储实例
        storage = PathletStorage(Path(temp_dir))
        
        # 创建大量重叠的径元数据
        num_pathlets = 5
        base_observations = []
        for i in range(110):  # 100个上下文点 + 10个延续点
            obs = Observation(
                delay_up=10.0 + i * 0.1,
                loss_up=0.01 + i * 0.0001,
                bw_up=50.0 - i * 0.05,
                delay_down=8.0 + i * 0.08,
                loss_down=0.005 + i * 0.00005,
                bw_down=100.0 - i * 0.1
            )
            base_observations.append(obs)
        
        # 创建重叠的径元
        pathlets = []
        raw_trace_segment_map = {}
        
        for i in range(num_pathlets):
            # 每个径元从不同的起始索引开始，与前一个径元重叠
            start_index = i * 10
            
            # 创建 RawTraceSegment
            segment = RawTraceSegment(
                trace_name=f"test_trace_{i % 2}",  # 交替使用两个轨迹名
                start_index=start_index,
                observations=base_observations
            )
            
            # 创建 Pathlet 对象
            pathlet = Pathlet(
                pathlet_id=f"pathlet_{i:03d}",
                body=BodyObservations(),
                tail=TailObservations()
            )
            
            pathlets.append(pathlet)
            raw_trace_segment_map[pathlet.pathlet_id] = segment
        
        # 保存数据
        storage.save_pathlets(pathlets, raw_trace_segment_map)
        
        # 计算存储大小
        storage_size = get_directory_size(temp_dir)
        print(f"存储大小: {storage_size} 字节")
        print(f"每个径元平均存储大小: {storage_size / num_pathlets:.2f} 字节")
        
        # 加载数据验证
        loaded_pathlets = storage.load_pathlets()
        assert len(loaded_pathlets) == num_pathlets
        
        # 计算理论上不进行去重的存储大小
        # 每个径元 110 个点，每个点约 8 * 6 = 48 字节（6个float字段）
        # 加上其他元数据
        estimated_size_no_optimization = num_pathlets * 110 * 48
        print(f"理论上不进行去重的存储大小: {estimated_size_no_optimization} 字节")
        
        # 计算优化比例
        optimization_ratio = (estimated_size_no_optimization - storage_size) / estimated_size_no_optimization * 100
        print(f"存储优化比例: {optimization_ratio:.2f}%")

        # 验证去重效果（通过检查存储文件中的实际点数据数量）
        # 直接读取点数据文件，检查去重后的实际点数据数量
        points_df = storage._read_points()
        actual_points_count = len(points_df)
        print(f"存储文件中的实际点数据数量: {actual_points_count}")
        print(f"理论点数据数量（无去重）: {num_pathlets * 110}")
        assert actual_points_count < num_pathlets * 110, "数据去重失败"
        print(f"去重成功！减少了 {num_pathlets * 110 - actual_points_count} 个重复点")
        
        print(f"存储优化成功！实际点数据数量比理论值少 {num_pathlets * 110 - actual_points_count} 个")
        
        return {
            "num_pathlets": num_pathlets,
            "storage_size": storage_size,
            "estimated_size_no_optimization": estimated_size_no_optimization,
            "optimization_ratio": optimization_ratio
        }
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    # 运行测试
    result = test_storage_optimization()
    print("\n测试结果:")
    print(f"径元数量: {result['num_pathlets']}")
    print(f"实际存储大小: {result['storage_size']} 字节")
    print(f"理论未优化大小: {result['estimated_size_no_optimization']} 字节")
    print(f"优化比例: {result['optimization_ratio']:.2f}%")
