# -*- coding: utf-8 -*-
"""测试径元构建器

测试 PathletBuilder 类的功能，包括添加观测序列和保存径元。
"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from traceloom.domain.pathlet import Observation
from training.pathlet_clustering.pathlet_builder import PathletBuilder


class TestPathletBuilder:
    """测试 PathletBuilder 类"""

    def setup_method(self):
        """设置测试环境"""
        self.builder = PathletBuilder(body_size=2, tail_size=1)
        self.test_observations = [
            Observation(delay_up=10.0, loss_up=0.01, bw_up=100.0, delay_down=12.0, loss_down=0.02, bw_down=120.0),
            Observation(delay_up=11.0, loss_up=0.01, bw_up=105.0, delay_down=13.0, loss_down=0.02, bw_down=125.0),
            Observation(delay_up=12.0, loss_up=0.02, bw_up=110.0, delay_down=14.0, loss_down=0.03, bw_down=130.0),
            Observation(delay_up=13.0, loss_up=0.02, bw_up=115.0, delay_down=15.0, loss_down=0.03, bw_down=135.0),
        ]

    def test_add_sequence_list(self):
        """测试添加观测序列（列表形式）"""
        states = [0, 1, 0, 1]
        self.builder.add_sequence(self.test_observations, states, "test_file")
        assert len(self.builder.pathlets) == 2  # 4 - (2+1) + 1 = 2

    def test_add_sequence_dataframe(self):
        """测试添加观测序列（DataFrame形式）"""
        # 创建测试DataFrame
        data = []
        for obs in self.test_observations:
            data.append(
                {
                    "delay_up": obs.delay_up,
                    "loss_up": obs.loss_up,
                    "bw_up": obs.bw_up,
                    "delay_down": obs.delay_down,
                    "loss_down": obs.loss_down,
                    "bw_down": obs.bw_down,
                }
            )
        df = pd.DataFrame(data)

        states = [0, 1, 0, 1]
        self.builder.add_sequence(df, states, "test_file")
        assert len(self.builder.pathlets) == 2

    def test_add_sequence_invalid(self):
        """测试添加无效的观测序列"""
        states = [0, 1, 0, 1]
        with pytest.raises(ValueError):
            self.builder.add_sequence({}, states, "test_file")

    def test_save_to_parquet(self):
        """测试保存径元到Parquet文件"""
        # 添加测试数据
        states = [0, 1, 0, 1]
        self.builder.add_sequence(self.test_observations, states, "test_file")

        # 创建临时输出目录
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            self.builder.save_to_parquet(output_dir)

            # 验证文件存在
            output_file = output_dir / "pathlets.parquet"
            assert output_file.exists()

            # 验证文件内容
            df = pd.read_parquet(output_file)
            assert len(df) == 2
            assert "pathlet_id" in df.columns
            assert "state_id" in df.columns
            assert "source_file" in df.columns
            assert "start_index" in df.columns
