#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试数据加载器"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from traceloom.core.logger import setup_logger
from training.pathlet_clustering.data_loader import DataLoader


def test_data_loader():
    """测试数据加载器"""
    # 初始化日志
    setup_logger()

    # 创建测试数据
    n_rows = 200
    df = pd.DataFrame(
        {
            "delay_up": np.random.normal(100, 10, n_rows),
            "loss_up": np.random.normal(0.01, 0.005, n_rows),
            "bw_up": np.random.normal(10, 2, n_rows),
            "delay_down": np.random.normal(100, 10, n_rows),
            "loss_down": np.random.normal(0.01, 0.005, n_rows),
            "bw_down": np.random.normal(10, 2, n_rows),
        }
    )

    # 确保所有值为正数，且丢包率在0-1之间
    df["delay_up"] = df["delay_up"].abs()
    df["loss_up"] = df["loss_up"].clip(0, 1)
    df["bw_up"] = df["bw_up"].abs()
    df["delay_down"] = df["delay_down"].abs()
    df["loss_down"] = df["loss_down"].clip(0, 1)
    df["bw_down"] = df["bw_down"].abs()

    # 初始化数据加载器
    loader = DataLoader()

    # 从DataFrame中提取网络剖面
    profiles = loader.load_from_dataframe(df, trace_name="test_trace")

    # 检查结果
    assert len(profiles) > 0, "没有提取到网络剖面"

    # 保存到临时文件
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "test_profiles.csv"
        success = loader.profiles_to_csv(profiles, output_path)
        assert success, "保存网络剖面失败"

        # 从文件加载
        loaded_profiles = loader.load_from_csv(output_path)
        assert len(loaded_profiles) == len(profiles), "加载的网络剖面数量不匹配"

    print("✅ 数据加载器测试通过")


if __name__ == "__main__":
    test_data_loader()
