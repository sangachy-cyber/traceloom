# -*- coding: utf-8 -*-
"""HoloWAN 设备管理测试"""

import json
import pytest
from unittest.mock import MagicMock, patch

from traceloom.devices._holowan import HoloWAN


class TestHoloWAN:
    """测试 HoloWAN 设备管理模块"""

    def setup_method(self):
        """设置测试环境"""
        self.host = "192.168.1.1"
        self.port = 8080
        self.engine_id = 1
        self.holowan = HoloWAN(self.host, self.port, self.engine_id)

    def test_init(self):
        """测试初始化方法"""
        assert self.holowan.host == self.host
        assert self.holowan.port == str(self.port)
        assert self.holowan.engine_id == self.engine_id
        assert self.holowan.engine is None
        assert self.holowan.playback is None

    @patch("traceloom.devices._holowan.Engine")
    @patch("traceloom.devices._holowan.PlayBack")
    def test_connect(self, mock_playback, mock_engine):
        """测试连接方法"""
        # 模拟 Engine 和 PlayBack
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance
        mock_playback_instance = MagicMock()
        mock_playback.return_value = mock_playback_instance

        # 执行连接
        self.holowan.connect()

        # 验证调用
        mock_engine.assert_called_once_with(self.host, str(self.port), self.engine_id)
        mock_engine_instance.update.assert_called_once()
        mock_playback.assert_called_once_with(holowan_ip=self.host, holowan_port=str(self.port))
        assert self.holowan.engine == mock_engine_instance
        assert self.holowan.playback == mock_playback_instance

    @patch("traceloom.devices._holowan.Engine")
    @patch("traceloom.devices._holowan.PlayBack")
    def test_connect_exception(self, mock_playback, mock_engine):
        """测试连接方法异常"""
        # 模拟 Engine 抛出异常
        mock_engine.side_effect = Exception("Connection error")

        # 验证异常
        with pytest.raises(RuntimeError, match="Failed to connect to HoloWAN device"):
            self.holowan.connect()

    @patch("traceloom.devices._holowan.Engine")
    @patch("traceloom.devices._holowan.PlayBack")
    def test_find_path_id(self, mock_playback, mock_engine):
        """测试查找路径 ID 方法"""
        # 模拟 Engine 和 Path
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance

        # 模拟路径查找
        mock_path = MagicMock()
        mock_path.path_name = "LoomNet"
        mock_engine_instance.get_path_by_id.side_effect = [
            None,
            None,
            mock_path,
            None,  # 第三个路径是 LoomNet
        ]

        # 执行连接
        self.holowan.connect()

        # 测试 find_path_id
        path_id = self.holowan.find_path_id()
        assert path_id == 3  # 第三个路径，索引为 2，返回 3

    @patch("traceloom.devices._holowan.Engine")
    @patch("traceloom.devices._holowan.PlayBack")
    def test_find_path_id_not_found(self, mock_playback, mock_engine):
        """测试查找路径 ID 方法 - 未找到路径"""
        # 模拟 Engine
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance

        # 模拟所有路径都不是 LoomNet
        mock_engine_instance.get_path_by_id.return_value = None

        # 执行连接
        self.holowan.connect()

        # 验证异常
        with pytest.raises(RuntimeError, match="未找到 LoomNet 虚拟链路"):
            self.holowan.find_path_id()

    @patch("traceloom.devices._holowan.Engine")
    @patch("traceloom.devices._holowan.PlayBack")
    def test_get_path_id_by_name(self, mock_playback, mock_engine):
        """测试根据路径名称查找路径 ID 方法"""
        # 模拟 Engine 和 Path
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance

        # 模拟路径查找
        mock_path = MagicMock()
        mock_path.path_name = "MyPath"
        mock_engine_instance.get_path_by_id.side_effect = [
            None,
            None,
            mock_path,
            None,  # 第三个路径是 MyPath
        ]

        # 执行连接
        self.holowan.connect()

        # 测试 get_path_id_by_name
        path_id = self.holowan.get_path_id_by_name("MyPath")
        assert path_id == 3  # 第三个路径，索引为 2，返回 3

    @patch("traceloom.devices._holowan.Engine")
    @patch("traceloom.devices._holowan.PlayBack")
    def test_get_path_id_by_name_not_connected(self, mock_playback, mock_engine):
        """测试根据路径名称查找路径 ID 方法 - 未连接"""
        # 未执行连接
        with pytest.raises(RuntimeError, match="HoloWAN device not connected"):
            self.holowan.get_path_id_by_name("MyPath")

    @patch("traceloom.devices._holowan.Engine")
    @patch("traceloom.devices._holowan.PlayBack")
    def test_get_path_id_by_name_not_found(self, mock_playback, mock_engine):
        """测试根据路径名称查找路径 ID 方法 - 未找到路径"""
        # 模拟 Engine
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance

        # 模拟所有路径都不是目标路径
        mock_engine_instance.get_path_by_id.return_value = None

        # 执行连接
        self.holowan.connect()

        # 验证异常
        with pytest.raises(ValueError, match="Path 'MyPath' not found"):
            self.holowan.get_path_id_by_name("MyPath")

    @patch("traceloom.devices._holowan.Engine")
    @patch("traceloom.devices._holowan.PlayBack")
    @patch("traceloom.devices._holowan.RawByteRule")
    def test_bind_ip_to_path(self, mock_raw_byte_rule, mock_playback, mock_engine):
        """测试绑定 IP 到路径方法"""
        # 模拟 Engine 和相关对象
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance

        # 模拟 RawByteRule
        mock_rule1 = MagicMock()
        mock_rule2 = MagicMock()
        mock_raw_byte_rule.side_effect = [mock_rule1, mock_rule2]

        # 执行连接
        self.holowan.connect()

        # 保存原始方法
        original_remove_rule = self.holowan._remove_rule_by_label
        # 模拟 _remove_rule_by_label 方法
        self.holowan._remove_rule_by_label = MagicMock()

        # 测试 bind_ip_to_path
        target_ip = "192.168.1.100"
        path_id = 1
        self.holowan.bind_ip_to_path(target_ip, path_id)

        # 验证调用
        # 验证清理旧规则
        self.holowan._remove_rule_by_label.assert_any_call(port=1, label=f"AutoGenFor_{target_ip}_1")
        self.holowan._remove_rule_by_label.assert_any_call(port=2, label=f"AutoGenFor_{target_ip}_2")

        # 验证创建新规则
        mock_raw_byte_rule.assert_any_call(type=1, action=path_id)
        mock_raw_byte_rule.assert_any_call(type=1, action=path_id)

        # 验证应用规则
        mock_engine_instance.apply_rule_to_classifier.assert_any_call(mock_rule1, port=1)
        mock_engine_instance.apply_rule_to_classifier.assert_any_call(mock_rule2, port=2)

        # 恢复原始方法
        self.holowan._remove_rule_by_label = original_remove_rule

    @patch("traceloom.devices._holowan.Engine")
    @patch("traceloom.devices._holowan.PlayBack")
    def test_upload_and_apply_playback(self, mock_playback, mock_engine):
        """测试上传并应用回放文件方法"""
        # 模拟 Engine 和 PlayBack
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance
        mock_playback_instance = MagicMock()
        mock_playback.return_value = mock_playback_instance

        # 模拟回放文件列表
        mock_playback_instance.get_playback_file_list.return_value = json.dumps(
            {"data": {"list": [{"name": "existing_playback"}]}}
        )

        # 模拟上传和应用
        mock_playback_instance.upload_playback_file.return_value = '{"code": 0}'
        mock_playback_instance.apply_playback_file.return_value = json.dumps({"code": 0})

        # 执行连接
        self.holowan.connect()

        # 测试 upload_and_apply_playback
        file_path = "/path/to/file.hwan"
        playback_name = "new_playback"
        path_id = 1
        self.holowan.upload_and_apply_playback(file_path, playback_name, path_id)

        # 验证调用
        mock_playback_instance.get_playback_file_list.assert_called_once()
        mock_playback_instance.upload_playback_file.assert_called_once_with(file_path=file_path)
        mock_playback_instance.apply_playback_file.assert_called_once_with(
            engine_id=self.engine_id, path_id=path_id, file_name=playback_name
        )

    @patch("traceloom.devices._holowan.Engine")
    @patch("traceloom.devices._holowan.PlayBack")
    def test_upload_and_apply_playback_upload_failure(self, mock_playback, mock_engine):
        """测试上传并应用回放文件方法 - 上传失败"""
        # 模拟 Engine 和 PlayBack
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance
        mock_playback_instance = MagicMock()
        mock_playback.return_value = mock_playback_instance

        # 模拟回放文件列表
        mock_playback_instance.get_playback_file_list.return_value = json.dumps({"data": {"list": []}})

        # 模拟上传失败
        mock_playback_instance.upload_playback_file.return_value = '{"code": 1, "message": "Upload failed"}'

        # 执行连接
        self.holowan.connect()

        # 验证异常
        file_path = "/path/to/file.hwan"
        playback_name = "new_playback"
        path_id = 1
        with pytest.raises(RuntimeError, match="上传失败"):
            self.holowan.upload_and_apply_playback(file_path, playback_name, path_id)

    @patch("traceloom.devices._holowan.Engine")
    @patch("traceloom.devices._holowan.PlayBack")
    def test_upload_and_apply_playback_apply_failure(self, mock_playback, mock_engine):
        """测试上传并应用回放文件方法 - 应用失败"""
        # 模拟 Engine 和 PlayBack
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance
        mock_playback_instance = MagicMock()
        mock_playback.return_value = mock_playback_instance

        # 模拟回放文件列表
        mock_playback_instance.get_playback_file_list.return_value = json.dumps({"data": {"list": []}})

        # 模拟上传成功但应用失败
        mock_playback_instance.upload_playback_file.return_value = '{"code": 0}'
        mock_playback_instance.apply_playback_file.return_value = json.dumps({"code": 1, "message": "Apply failed"})

        # 执行连接
        self.holowan.connect()

        # 验证异常
        file_path = "/path/to/file.hwan"
        playback_name = "new_playback"
        path_id = 1
        with pytest.raises(RuntimeError, match="应用失败"):
            self.holowan.upload_and_apply_playback(file_path, playback_name, path_id)

    @patch("traceloom.devices._holowan.Engine")
    @patch("traceloom.devices._holowan.PlayBack")
    def test_cleanup(self, mock_playback, mock_engine):
        """测试清理方法"""
        # 模拟 Engine 和 PlayBack
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance
        mock_playback_instance = MagicMock()
        mock_playback.return_value = mock_playback_instance

        # 执行连接
        self.holowan.connect()

        # 保存原始方法
        original_remove_rule = self.holowan._remove_rule_by_label
        # 模拟 _remove_rule_by_label 方法
        self.holowan._remove_rule_by_label = MagicMock()

        # 测试 cleanup
        target_ip = "192.168.1.100"
        playback_name = "playback1"
        path_id = 1
        self.holowan.cleanup(target_ip, playback_name, path_id)

        # 验证调用
        mock_playback_instance.release_playback_file.assert_called_once_with(engine_id=self.engine_id, path_id=path_id)
        self.holowan._remove_rule_by_label.assert_any_call(port=1, label=f"AutoGenFor_{target_ip}_1")
        self.holowan._remove_rule_by_label.assert_any_call(port=2, label=f"AutoGenFor_{target_ip}_2")
        mock_playback_instance.delete_playback_file.assert_called_once_with(file_name=playback_name)

        # 恢复原始方法
        self.holowan._remove_rule_by_label = original_remove_rule

    @patch("traceloom.devices._holowan.Engine")
    @patch("traceloom.devices._holowan.PlayBack")
    def test_remove_rule_by_label(self, mock_playback, mock_engine):
        """测试删除规则方法"""
        # 模拟 Engine 和 Classifier
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance
        mock_classifier = MagicMock()
        mock_engine_instance.packet_classifier = mock_classifier

        # 模拟规则列表
        mock_rule1 = {"label": "rule1"}
        mock_rule2 = {"label": "rule2"}
        mock_rule3 = {"label": "rule3"}
        mock_classifier.port1.nodes = [mock_rule1, mock_rule2, mock_rule3]

        # 执行连接
        self.holowan.connect()

        # 测试 _remove_rule_by_label
        self.holowan._remove_rule_by_label(port=1, label="rule2")

        # 验证调用
        mock_classifier.remove_rule.assert_called_once_with(1, 1)  # 移除第二个规则（索引为 1）


if __name__ == "__main__":
    pytest.main([__file__])
