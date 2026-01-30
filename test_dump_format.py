#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证HoloWANTrace dump方法的格式

此脚本创建一个HoloWANTrace对象并调用dump方法，验证生成的文件格式是否正确。
"""

from traceloom.io.adapters._holowan import HoloWANTrace, HoloWANPoint
from traceloom.domain.pathlet import Observation
import tempfile
import os


def test_dump_format_integer_loss_average():
    """
    测试dump方法生成的文件格式 - 整数Loss Average
    """
    print("\n" + "="*80)
    print("开始测试HoloWANTrace dump方法的格式 (整数Loss Average)...")
    print("="*80)
    
    # 创建一些测试数据
    observations = [
        Observation(delay_up=14.23, loss_up=0.0, bw_up=0.1664, delay_down=14.23, loss_down=0.0, bw_down=0.1664),
        Observation(delay_up=14.43, loss_up=0.0, bw_up=0.0832, delay_down=14.43, loss_down=0.0, bw_down=0.208),
        Observation(delay_up=14.37, loss_up=0.0, bw_up=0.1248, delay_down=14.37, loss_down=0.0, bw_down=0.208),
        Observation(delay_up=14.49, loss_up=0.0, bw_up=0.0832, delay_down=14.49, loss_down=0.2, bw_down=0.1664),
        Observation(delay_up=14.94, loss_up=0.3333, bw_up=0.0832, delay_down=14.94, loss_down=0.0, bw_down=0.2496),
    ]
    
    # 创建HoloWANTrace对象，设置loss_average为整数10
    trace = HoloWANTrace.from_observations(
        observations,
        loss_average=10.0,  # 整数
        enable_reordering=True,
        switch="1,1,1,1,1,1"
    )
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
        temp_file_path = tmp.name
    
    try:
        # 调用dump方法
        trace.dump(temp_file_path)
        print(f"成功生成文件: {temp_file_path}")
        
        # 读取生成的文件并显示内容
        print("\n生成的文件内容:")
        print("=" * 80)
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                print(line.rstrip())
        print("=" * 80)
        
        # 验证文件格式
        print("\n验证文件格式...")
        
        # 读取所有行（包括空行）以检查最后一行
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        # 检查最后一行是否不为空
        if all_lines and all_lines[-1].strip():
            print("✓ 最后一行不为空")
        else:
            print("✗ 最后一行为空")
        
        # 处理非空行
        lines = [line.rstrip() for line in all_lines if line.rstrip()]
        
        # 检查Loss Average行
        loss_average_line = next((line for line in lines if line.startswith("Loss Average")), None)
        if loss_average_line:
            print(f"Loss Average行: {loss_average_line}")
            if "Loss Average: 10" in loss_average_line:
                print("✓ Loss Average格式正确（整数无小数）")
            else:
                print("✗ Loss Average格式错误")
        
        # 检查数据行格式
        data_section_start = False
        data_lines = []
        
        for line in lines:
            if line == "------------------------------------------------":
                data_section_start = True
                continue
            if data_section_start:
                data_lines.append(line)
        
        print(f"\n找到 {len(data_lines)} 个数据行")
        
        # 验证前几个数据行
        for i, line in enumerate(data_lines[:3]):
            print(f"数据行 {i+1}: {line}")
            # 检查是否使用逗号分隔
            if ',' in line:
                print("✓ 使用逗号分隔")
            else:
                print("✗ 未使用逗号分隔")
            
            # 检查字段数量
            fields = line.split(',')
            if len(fields) == 6:
                print("✓ 字段数量正确（6个）")
            else:
                print(f"✗ 字段数量错误，期望6个，实际{len(fields)}个")
            
            # 检查小数位数
            try:
                # 延迟：两位小数
                float(fields[0])
                float(fields[3])
                # 丢包率：两位小数
                float(fields[1])
                float(fields[4])
                # 带宽：六位小数
                float(fields[2])
                float(fields[5])
                print("✓ 小数位数格式正确")
            except ValueError:
                print("✗ 小数格式错误")
        
        print("\n测试完成！")
        
    finally:
        # 清理临时文件
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            print(f"\n临时文件已清理: {temp_file_path}")


def test_dump_format_decimal_loss_average():
    """
    测试dump方法生成的文件格式 - 小数Loss Average
    """
    print("\n" + "="*80)
    print("开始测试HoloWANTrace dump方法的格式 (小数Loss Average)...")
    print("="*80)
    
    # 创建一些测试数据
    observations = [
        Observation(delay_up=10.5, loss_up=0.05, bw_up=1.234567, delay_down=10.5, loss_down=0.05, bw_down=1.234567),
    ]
    
    # 创建HoloWANTrace对象，设置loss_average为小数
    trace = HoloWANTrace.from_observations(
        observations,
        loss_average=15.75,  # 小数
        enable_reordering=True,
        switch="1,1,1,1,1,1"
    )
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
        temp_file_path = tmp.name
    
    try:
        # 调用dump方法
        trace.dump(temp_file_path)
        print(f"成功生成文件: {temp_file_path}")
        
        # 读取生成的文件并显示内容
        print("\n生成的文件内容:")
        print("=" * 80)
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                print(line.rstrip())
        print("=" * 80)
        
        # 验证文件格式
        print("\n验证文件格式...")
        
        # 读取所有行（包括空行）以检查最后一行
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        # 检查最后一行是否不为空
        if all_lines and all_lines[-1].strip():
            print("✓ 最后一行不为空")
        else:
            print("✗ 最后一行为空")
        
        # 处理非空行
        lines = [line.rstrip() for line in all_lines if line.rstrip()]
        
        # 检查Loss Average行
        loss_average_line = next((line for line in lines if line.startswith("Loss Average")), None)
        if loss_average_line:
            print(f"Loss Average行: {loss_average_line}")
            if "Loss Average: 15.75" in loss_average_line:
                print("✓ Loss Average格式正确（两位小数）")
            else:
                print("✗ Loss Average格式错误")
        
        print("\n测试完成！")
        
    finally:
        # 清理临时文件
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            print(f"\n临时文件已清理: {temp_file_path}")


def test_dump_format_single_data_point():
    """
    测试dump方法生成的文件格式 - 单个数据点
    """
    print("\n" + "="*80)
    print("开始测试HoloWANTrace dump方法的格式 (单个数据点)...")
    print("="*80)
    
    # 创建只有一个数据点的测试数据
    observations = [
        Observation(delay_up=20.0, loss_up=0.1, bw_up=0.5, delay_down=20.0, loss_down=0.1, bw_down=0.5),
    ]
    
    # 创建HoloWANTrace对象
    trace = HoloWANTrace.from_observations(
        observations,
        loss_average=5.0,  # 整数
        enable_reordering=False,
        switch="0,0,0,0,0,0"
    )
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
        temp_file_path = tmp.name
    
    try:
        # 调用dump方法
        trace.dump(temp_file_path)
        print(f"成功生成文件: {temp_file_path}")
        
        # 读取生成的文件并显示内容
        print("\n生成的文件内容:")
        print("=" * 80)
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                print(line.rstrip())
        print("=" * 80)
        
        # 验证文件格式
        print("\n验证文件格式...")
        
        # 读取所有行（包括空行）以检查最后一行
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        # 检查最后一行是否不为空
        if all_lines and all_lines[-1].strip():
            print("✓ 最后一行不为空")
        else:
            print("✗ 最后一行为空")
        
        print("\n测试完成！")
        
    finally:
        # 清理临时文件
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            print(f"\n临时文件已清理: {temp_file_path}")


if __name__ == "__main__":
    print("HoloWANTrace dump方法格式测试")
    print("=" * 80)
    
    # 运行所有测试
    test_dump_format_integer_loss_average()
    test_dump_format_decimal_loss_average()
    test_dump_format_single_data_point()
    
    print("\n" + "=" * 80)
    print("所有测试完成！")
    print("=" * 80)