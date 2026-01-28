# -*- coding: utf-8 -*-
"""测试数据加载器

测试 DataLoader 类的功能，包括从CSV加载网络剖面和将网络剖面保存为CSV。
"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from traceloom.domain.pathlet import Observation
from traceloom.domain.raw_trace import RawTraceSegment as RawProfile
from training.pathlet_clustering.data_loader import DataLoader


class TestDataLoader:
    """测试 DataLoader 类"""

    def setup_method(self):
        """设置测试环境"""
        self.loader = DataLoader()
        self.test_data = [
            Observation(
                delay_up=10.0, loss_up=0.01, bw_up=100.0,
                delay_down=12.0, loss_down=0.02, bw_down=120.0
            ),
            Observation(
                delay_up=11.0, loss_up=0.01, bw_up=105.0,
                delay_down=13.0, loss_down=0.02, bw_down=125.0
            ),
            Observation(
                delay_up=12.0, loss_up=0.02, bw_up=110.0,
                delay_down=14.0, loss_down=0.03, bw_down=130.0
            )
        ]

    def test_load_from_csv(self):
        """测试从CSV加载网络剖面"""
        # 创建测试CSV文件
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            csv_path = Path(f.name)
            
        # 构建测试数据
        data = []
        for i, obs in enumerate(self.test_data):
            data.append({
                'trace_name': 'test_trace',
                'start_index': 0,
                'sample_index': i,
                'delay_up': obs.delay_up,
                'loss_up': obs.loss_up,
                'bw_up': obs.bw_up,
                'delay_down': obs.delay_down,
                'loss_down': obs.loss_down,
                'bw_down': obs.bw_down
            })
        
        df = pd.DataFrame(data)
        df.to_csv(csv_path, index=False)
        
        # 测试加载
        profiles = self.loader.load_from_csv(csv_path)
        
        # 验证结果
        assert len(profiles) == 1
        profile = profiles[0]
        assert profile.trace_name == 'test_trace'
        assert profile.start_index == 0
        assert len(profile.observations) == 3
        
        # 清理临时文件
        csv_path.unlink()

    def test_profiles_to_csv(self):
        """测试将网络剖面保存为CSV"""
        # 创建测试网络剖面
        profile = RawProfile(
            trace_name='test_trace',
            start_index=0,
            observations=self.test_data,
            is_valid=True
        )
        
        # 创建临时输出文件
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            output_path = Path(f.name)
        
        # 测试保存
        result = self.loader.profiles_to_csv([profile], output_path)
        assert result is True
        
        # 验证文件存在
        assert output_path.exists()
        
        # 验证文件内容
        df = pd.read_csv(output_path)
        assert len(df) == 3
        assert df['trace_name'].tolist() == ['test_trace'] * 3
        assert df['start_index'].tolist() == [0] * 3
        
        # 清理临时文件
        output_path.unlink()

    def test_load_from_dataframe(self):
        """测试从DataFrame加载网络剖面"""
        # 创建测试DataFrame
        data = []
        for i, obs in enumerate(self.test_data):
            data.append({
                'delay_up': obs.delay_up,
                'loss_up': obs.loss_up,
                'bw_up': obs.bw_up,
                'delay_down': obs.delay_down,
                'loss_down': obs.loss_down,
                'bw_down': obs.bw_down
            })
        df = pd.DataFrame(data)
        
        # 测试加载
        profiles = self.loader.load_from_dataframe(df, 'test_trace', length=3)
        
        # 验证结果
        assert len(profiles) == 1
        profile = profiles[0]
        assert profile.trace_name == 'test_trace'
        assert profile.start_index == 0
        assert len(profile.observations) == 3

    def test_load_profiles_from_directory(self):
        """测试从目录加载网络剖面"""
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # 创建测试CSV文件
            data = []
            for i, obs in enumerate(self.test_data):
                data.append({
                    'trace_name': 'test_trace',
                    'start_index': 0,
                    'sample_index': i,
                    'delay_up': obs.delay_up,
                    'loss_up': obs.loss_up,
                    'bw_up': obs.bw_up,
                    'delay_down': obs.delay_down,
                    'loss_down': obs.loss_down,
                    'bw_down': obs.bw_down
                })
            df = pd.DataFrame(data)
            df.to_csv(temp_path / 'test.csv', index=False)
            
            # 测试加载
            profiles_dict = self.loader.load_profiles_from_directory(temp_path)
            
            # 验证结果
            assert 'test' in profiles_dict
            profiles = profiles_dict['test']
            assert len(profiles) == 1
            assert profiles[0].trace_name == 'test_trace'
