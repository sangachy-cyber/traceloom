# -*- coding: utf-8 -*-
"""测试 WeaverService 服务层实现"""

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from traceloom.app.api.v1.schemas import WeaveRequest
from traceloom.services.weaver_service import WeaverService
from traceloom.storage.pathlet_storage import PathletStorage
from traceloom.storage.task_store import TaskStore


class TestWeaverService:
    """测试 WeaverService 类"""

    def setup_method(self):
        """设置测试环境"""
        # 创建模拟的任务存储
        self.mock_task_store = MagicMock(spec=TaskStore)
        self.mock_task_store.create_task.return_value = None
        self.mock_task_store.update_status.return_value = None
        self.mock_task_store.update_playback_file.return_value = None
        self.mock_task_store.update_started_at.return_value = None

        # 创建模拟的径元存储
        self.mock_pathlet_storage = MagicMock(spec=PathletStorage)

        # 创建 WeaverService 实例
        self.weaver_service = WeaverService(self.mock_task_store, self.mock_pathlet_storage)

    def test_init(self):
        """测试初始化方法"""
        # 验证初始化是否成功
        assert self.weaver_service is not None
        assert self.weaver_service.task_store == self.mock_task_store
        assert self.weaver_service.pathlet_storage == self.mock_pathlet_storage
        assert hasattr(self.weaver_service, "sampler")
        assert hasattr(self.weaver_service, "playback_dir")

    def test_execute_task(self):
        """测试执行织径任务"""
        # 创建模拟的编织请求
        mock_request = MagicMock(spec=WeaveRequest)
        mock_request.target_ip = "10.10.10.10"
        mock_request.weaving_pattern = "s0x2 -> s1x3"
        mock_request.impairment_device = MagicMock()
        mock_request.impairment_device.host = "192.168.1.1"
        mock_request.impairment_device.port = 8080
        mock_request.impairment_device.engine_id = 1
        mock_request.impairment_device.path_name = "MyLink"

        # 模拟 PatternParser.parse
        mock_pattern = MagicMock()
        with patch("traceloom.services.weaver_service.PatternParser.parse", return_value=mock_pattern):
            # 模拟 select_engine
            mock_engine = MagicMock()
            mock_engine.weave.return_value = []
            with patch("traceloom.services.weaver_service.select_engine", return_value=mock_engine):
                # 模拟 HoloWANTrace.from_observations
                mock_holowan_trace = MagicMock()
                mock_holowan_trace.dump = MagicMock()
                with patch(
                    "traceloom.services.weaver_service.HoloWANTrace.from_observations", return_value=mock_holowan_trace
                ):
                    # 模拟文件操作
                    with patch("builtins.open", MagicMock()):
                        # 模拟 os.unlink
                        with patch("os.unlink", MagicMock()):
                            # 模拟 Path.exists
                            with patch("pathlib.Path.exists", return_value=True):
                                # 模拟 HoloWAN 设备管理
                                mock_holowan = MagicMock()
                                mock_holowan.connect.return_value = None
                                mock_holowan.get_path_id_by_name.return_value = 1
                                mock_holowan.bind_ip_to_path.return_value = None
                                mock_holowan.upload_and_apply_playback.return_value = None
                                with patch("traceloom.services.weaver_service.HoloWAN", return_value=mock_holowan):
                                    # 模拟临时文件
                                    mock_temp_file = MagicMock()
                                    mock_temp_file.name = "temp_file.txt"
                                    with patch("tempfile.NamedTemporaryFile", return_value=mock_temp_file):
                                        # 执行任务
                                        self.weaver_service.execute_task("task_123", mock_request)

                                        # 验证方法调用
                                        self.mock_task_store.update_started_at.assert_called_with("task_123")
                                        self.mock_task_store.update_status.assert_any_call("task_123", "running")

    def test_execute_task_exception(self):
        """测试执行织径任务时发生异常"""
        # 创建模拟的编织请求
        mock_request = MagicMock(spec=WeaveRequest)
        mock_request.target_ip = "10.10.10.10"
        mock_request.weaving_pattern = "s0x2 -> s1x3"
        mock_request.impairment_device = MagicMock()

        # 模拟 PatternParser.parse 抛出异常
        with patch("traceloom.services.weaver_service.PatternParser.parse", side_effect=Exception("解析失败")):
            # 执行任务
            self.weaver_service.execute_task("task_123", mock_request)

            # 验证任务状态被更新为失败
            self.mock_task_store.update_status.assert_called_with("task_123", "failed", error="解析失败")

    def test_execute_reweave(self):
        """测试执行重织任务"""
        # 创建模拟的编织请求
        mock_request = MagicMock(spec=WeaveRequest)

        # 模拟 execute_task 方法
        with patch.object(self.weaver_service, "execute_task") as mock_execute_task:
            # 执行重织任务
            self.weaver_service.execute_reweave("task_123", mock_request)

            # 验证调用了 execute_task
            mock_execute_task.assert_called_with("task_123", mock_request)

    def test_execute_stitch(self):
        """测试执行绣织任务"""
        # 创建模拟的编织请求
        mock_request = MagicMock(spec=WeaveRequest)

        # 模拟 execute_task 方法
        with patch.object(self.weaver_service, "execute_task") as mock_execute_task:
            # 执行绣织任务
            self.weaver_service.execute_stitch("task_123", mock_request)

            # 验证调用了 execute_task
            mock_execute_task.assert_called_with("task_123", mock_request)

    def test_execute_dream(self):
        """测试执行广织任务"""
        # 创建模拟的编织请求
        mock_request = MagicMock(spec=WeaveRequest)

        # 模拟 execute_task 方法
        with patch.object(self.weaver_service, "execute_task") as mock_execute_task:
            # 执行广织任务
            self.weaver_service.execute_dream("task_123", mock_request)

            # 验证调用了 execute_task
            mock_execute_task.assert_called_with("task_123", mock_request)

    def test_get_playback_file_path(self):
        """测试获取回放文件路径"""
        # 模拟任务存储的 get_task 方法
        self.mock_task_store.get_task.return_value = {"playback_file_path": "/tmp/playback/task_123.txt"}

        # 获取回放文件路径
        result = self.weaver_service.get_playback_file_path("task_123")

        # 验证结果
        assert result == "/tmp/playback/task_123.txt"
        self.mock_task_store.get_task.assert_called_with("task_123")

    def test_get_playback_file_path_nonexistent(self):
        """测试获取不存在的回放文件路径"""
        # 模拟任务存储的 get_task 方法返回 None
        self.mock_task_store.get_task.return_value = None

        # 获取回放文件路径
        result = self.weaver_service.get_playback_file_path("non_existent_task")

        # 验证结果
        assert result is None
        self.mock_task_store.get_task.assert_called_with("non_existent_task")

    def test_cleanup_expired_files(self):
        """测试清理过期的回放文件"""
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 修改回放文件目录
            self.weaver_service.playback_dir = Path(temp_dir)

            # 创建测试文件
            file1 = Path(temp_dir) / "test1.txt"
            file2 = Path(temp_dir) / "test2.txt"

            # 创建文件
            file1.write_text("test1")
            file2.write_text("test2")

            # 设置文件的修改时间为过去
            past_time = time.time() - 25 * 60 * 60  # 25小时前
            # 使用os.utime来设置文件的修改时间
            import os

            os.utime(file1, (past_time, past_time))
            os.utime(file2, (past_time, past_time))

            # 执行清理
            self.weaver_service.cleanup_expired_files()

            # 验证文件是否被删除
            assert not file1.exists()
            assert not file2.exists()

    def test_cancel_task(self):
        """测试取消任务"""
        # 模拟任务存储的 get_task 方法
        self.mock_task_store.get_task.return_value = {
            "task_id": "task_123",
            "target_ip": "10.10.10.10",
            "weaving_pattern": "s0x2 -> s1x3",
            "engine": "reweaver",
            "host": "192.168.1.1",
            "port": 8080,
            "engine_id": 1,
            "path_name": "MyLink",
        }

        # 模拟 HoloWAN 设备管理
        mock_holowan = MagicMock()
        mock_holowan.connect.return_value = None
        mock_holowan.get_path_id_by_name.return_value = 1
        mock_holowan.cleanup.return_value = None

        with patch("traceloom.services.weaver_service.HoloWAN", return_value=mock_holowan):
            # 执行取消任务
            self.weaver_service.cancel_task("task_123")

            # 验证调用
            self.mock_task_store.update_status.assert_called_with("task_123", "completed", error="任务被用户取消")
            mock_holowan.cleanup.assert_called_with("10.10.10.10", "task_123.txt", 1)

    def test_cancel_task_nonexistent(self):
        """测试取消不存在的任务"""
        # 模拟任务存储的 get_task 方法返回 None
        self.mock_task_store.get_task.return_value = None

        # 执行取消任务
        self.weaver_service.cancel_task("non_existent_task")

        # 验证任务状态被更新为失败
        self.mock_task_store.update_status.assert_called_with(
            "non_existent_task", "failed", error="取消任务失败: 任务 non_existent_task 不存在"
        )

    def test_cancel_task_exception(self):
        """测试取消任务时发生异常"""
        # 模拟任务存储的 get_task 方法
        self.mock_task_store.get_task.return_value = {
            "task_id": "task_123",
            "host": "192.168.1.1",
            "port": 8080,
            "engine_id": 1,
            "path_name": "MyLink",
            "target_ip": "10.10.10.10",
        }

        # 模拟 HoloWAN 设备管理抛出异常
        mock_holowan = MagicMock()
        mock_holowan.connect.side_effect = Exception("连接失败")

        with patch("traceloom.services.weaver_service.HoloWAN", return_value=mock_holowan):
            # 执行取消任务
            self.weaver_service.cancel_task("task_123")

            # 验证任务状态被更新为失败
            self.mock_task_store.update_status.assert_called_with("task_123", "failed", error="取消任务失败: 连接失败")


if __name__ == "__main__":
    pytest.main([__file__])
