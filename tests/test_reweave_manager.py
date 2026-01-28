# -*- coding: utf-8 -*-
"""WeavingEngine类的测试用例
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from traceloom.core.exceptions import SplicingError, ValidationError
from traceloom.domain.pattern import Pattern
from traceloom.weaving.engine import WeavingEngine


class TestWeavingEngine:
    """WeavingEngine类的测试用例"""

    def setup_method(self):
        """设置测试环境"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

        # 模拟PathletStorage和GlobalSampler
        with patch('traceloom.weaving.engine.PathletStorage') as mock_pathlet_storage:
            # 模拟PathletStorage实例
            mock_storage_instance = MagicMock()
            mock_storage_instance.load_pathlets.return_value = []
            mock_pathlet_storage.return_value = mock_storage_instance

            # 创建WeavingEngine实例
            self.weaving_engine = WeavingEngine()

            # 模拟GlobalSampler的sample_pathlets方法
            self.weaving_engine.global_sampler.sample_pathlets = MagicMock(return_value=[])

    def teardown_method(self):
        """清理测试环境"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_init(self):
        """测试初始化"""
        assert self.weaving_engine is not None
        assert hasattr(self.weaving_engine, 'pathlet_storage')
        assert hasattr(self.weaving_engine, 'weaving_law')
        assert hasattr(self.weaving_engine, 'global_sampler')
        assert hasattr(self.weaving_engine, 'reweaver')
        assert hasattr(self.weaving_engine, 'stitcher')
        assert hasattr(self.weaving_engine, 'dreamer')
        assert hasattr(self.weaving_engine, 'pattern_parser')

    def test_weave_string_input(self):
        """测试从字符串输入进行织径"""
        # 创建模拟的Reweaver
        with patch.object(self.weaving_engine.reweaver, 'generate_trace') as mock_generate:
            mock_generate.return_value = [[100.0, 0.01, 10.0, 100.0, 0.01, 10.0]] * 100

            # 测试重织功能
            pattern_str = "s0x2 -> s1x3"
            result = self.weaving_engine.weave(pattern_str, mode="reweave")

            # 验证结果
            assert isinstance(result, dict)
            assert "path_id" in result
            assert "duration_sec" in result
            assert "state_sequence" in result
            assert "trace_data" in result

    def test_weave_list_input(self):
        """测试从列表输入进行织径"""
        # 创建模拟的Reweaver
        with patch.object(self.weaving_engine.reweaver, 'generate_trace') as mock_generate:
            mock_generate.return_value = [[100.0, 0.01, 10.0, 100.0, 0.01, 10.0]] * 100

            # 测试重织功能
            pattern_list = [{"state": "s0", "duration": 20}, {"state": "s1", "duration": 30}]
            result = self.weaving_engine.weave(pattern_list, mode="reweave")

            # 验证结果
            assert isinstance(result, dict)
            assert "path_id" in result
            assert "duration_sec" in result
            assert "state_sequence" in result
            assert "trace_data" in result

    def test_weave_pattern_input(self):
        """测试从Pattern对象输入进行织径"""
        # 创建模拟的Reweaver
        with patch.object(self.weaving_engine.reweaver, 'generate_trace') as mock_generate:
            mock_generate.return_value = [[100.0, 0.01, 10.0, 100.0, 0.01, 10.0]] * 100

            # 测试重织功能
            pattern = Pattern.from_string("s0x2 -> s1x3")
            result = self.weaving_engine.weave(pattern, mode="reweave")

            # 验证结果
            assert isinstance(result, dict)
            assert "path_id" in result
            assert "duration_sec" in result
            assert "state_sequence" in result
            assert "trace_data" in result

    def test_weave_invalid_input(self):
        """测试使用无效输入进行织径"""
        # 测试无效输入类型
        with pytest.raises(ValidationError):
            self.weaving_engine.weave(123)

    def test_weave_invalid_mode(self):
        """测试使用无效模式进行织径"""
        # 测试无效模式
        with pytest.raises(ValidationError):
            self.weaving_engine.weave("s0x2 -> s1x3", mode="invalid_mode")

    def test_weave_splicing_error(self):
        """测试织径过程中发生拼接错误"""
        # 创建模拟的Reweaver，抛出SplicingError
        with patch.object(self.weaving_engine.reweaver, 'generate_trace') as mock_generate:
            mock_generate.side_effect = SplicingError("拼接失败")

            # 测试织径功能，应该捕获并重新抛出SplicingError
            with pytest.raises(SplicingError):
                self.weaving_engine.weave("s0x2 -> s1x3", mode="reweave")

    def test_weave_stitch_mode(self):
        """测试绣织模式"""
        # 创建模拟的Stitcher
        with patch.object(self.weaving_engine.stitcher, 'stitch') as mock_stitch:
            # 创建模拟的网络剖面
            mock_profile = MagicMock()
            mock_profile.ctx_10s.delay_up = [100.0] * 100
            mock_profile.ctx_10s.loss_up = [0.01] * 100
            mock_profile.ctx_10s.bw_up = [10.0] * 100
            mock_profile.ctx_10s.delay_down = [100.0] * 100
            mock_profile.ctx_10s.loss_down = [0.01] * 100
            mock_profile.ctx_10s.bw_down = [10.0] * 100
            mock_profile.cont_1s.delay_up = [100.0] * 10
            mock_profile.cont_1s.loss_up = [0.01] * 10
            mock_profile.cont_1s.bw_up = [10.0] * 10
            mock_profile.cont_1s.delay_down = [100.0] * 10
            mock_profile.cont_1s.loss_down = [0.01] * 10
            mock_profile.cont_1s.bw_down = [10.0] * 10

            mock_stitch.return_value = [mock_profile]

            # 测试绣织功能
            pattern_str = "s0x2 -> s1x3"
            result = self.weaving_engine.weave(pattern_str, mode="stitch")

            # 验证结果
            assert isinstance(result, dict)
            assert "path_id" in result
            assert "duration_sec" in result
            assert "state_sequence" in result
            assert "trace_data" in result

    def test_weave_dream_mode(self):
        """测试广织模式"""
        # 创建模拟的Dreamer
        with patch.object(self.weaving_engine.dreamer, 'dream') as mock_dream:
            # 创建模拟的网络剖面
            mock_profile = MagicMock()
            mock_profile.ctx_10s.delay_up = [100.0] * 100
            mock_profile.ctx_10s.loss_up = [0.01] * 100
            mock_profile.ctx_10s.bw_up = [10.0] * 100
            mock_profile.ctx_10s.delay_down = [100.0] * 100
            mock_profile.ctx_10s.loss_down = [0.01] * 100
            mock_profile.ctx_10s.bw_down = [10.0] * 100
            mock_profile.cont_1s.delay_up = [100.0] * 10
            mock_profile.cont_1s.loss_up = [0.01] * 10
            mock_profile.cont_1s.bw_up = [10.0] * 10
            mock_profile.cont_1s.delay_down = [100.0] * 10
            mock_profile.cont_1s.loss_down = [0.01] * 10
            mock_profile.cont_1s.bw_down = [10.0] * 10

            mock_dream.return_value = [mock_profile]

            # 测试广织功能
            pattern_str = "s0x2 -> s1x3"
            result = self.weaving_engine.weave(pattern_str, mode="dream")

            # 验证结果
            assert isinstance(result, dict)
            assert "path_id" in result
            assert "duration_sec" in result
            assert "state_sequence" in result
            assert "trace_data" in result

    def test_save_result(self):
        """测试保存织径结果"""
        # 创建模拟的织径结果
        result = {
            "path_id": "test_path_id",
            "duration_sec": 50,
            "state_sequence": "s0x2 -> s1x3",
            "trace_data": [[100.0, 0.01, 10.0, 100.0, 0.01, 10.0]] * 10
        }

        # 创建临时文件
        temp_file = self.temp_path / "test_result.txt"

        # 测试保存结果
        self.weaving_engine.save_result(result, str(temp_file))

        # 验证文件存在
        assert temp_file.exists()
        assert temp_file.stat().st_size > 0


class TestWeavingEnginePerformance:
    """WeavingEngine类的性能测试用例"""

    def setup_method(self):
        """设置测试环境"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def teardown_method(self):
        """清理测试环境"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_pattern_parser_performance(self):
        """测试织样解析器的性能"""
        # 创建WeavingEngine实例
        weaving_engine = WeavingEngine()

        # 测试多次解析相同的输入
        pattern_str = "s0x2 -> s1x3 -> s2x1"

        # 第一次解析
        import time
        start_time = time.time()
        result1 = weaving_engine.pattern_parser.parse(pattern_str)
        time.time() - start_time

        # 第二次解析
        start_time = time.time()
        result2 = weaving_engine.pattern_parser.parse(pattern_str)
        time.time() - start_time

        # 结果应该相同
        assert result1 == result2
