# -*- coding: utf-8 -*-
"""HoloWAN 设备管理模块。

用于管理 HoloWAN 网络损伤仪设备，包括连接设备、绑定 IP 到路径、上传和应用回放文件等操作。
"""

import json
import time

from holowan.v2.engine import Engine
from holowan.v2.playback import PlayBack


class HoloWANManager:
    """HoloWAN 设备管理器。

    用于管理 HoloWAN 网络损伤仪设备，提供连接设备、绑定 IP 到路径、上传和应用回放文件等功能。

    示例:
        from traceloom.devices.holowan_manager import HoloWANManager

        # 初始化 HoloWANManager
        holowan_manager = HoloWANManager(host="192.168.1.100", port="8888", engine_id=1)

        # 连接设备
        holowan_manager.connect()

        # 根据路径名称获取路径 ID
        path_id = holowan_manager.get_path_id_by_name("LoomNet")

        # 绑定 IP 到路径
        holowan_manager.bind_ip_to_path("192.168.2.100", path_id)

        # 上传并应用回放文件
        holowan_manager.upload_and_apply_playback("path/to/file.hwan", "playback1", path_id)

        # 清理
        holowan_manager.cleanup("192.168.2.100", "playback1", path_id)

    属性:
        host: HoloWAN 设备主机地址
        port: HoloWAN 设备端口
        engine_id: 引擎 ID
        engine: HoloWAN Engine 实例
        playback: HoloWAN PlayBack 实例
    """

    def __init__(self, host: str, port: str, engine_id: int = 1):
        """初始化 HoloWAN 设备管理器。

        参数:
            host: HoloWAN 设备主机地址
            port: HoloWAN 设备端口
            engine_id: 引擎 ID，默认为 1
        """
        self.host = host
        self.port = port
        self.engine_id = engine_id
        self.engine = None
        self.playback = None

    def connect(self):
        """初始化 Engine 和 PlayBack 实例，建立与 HoloWAN 设备的连接。

        异常:
            RuntimeError: 连接 HoloWAN 设备失败
        """
        try:
            self.engine = Engine(self.host, self.port, self.engine_id)
            self.engine.update()
            self.playback = PlayBack(holowan_ip=self.host, holowan_port=self.port)
        except Exception as e:
            raise RuntimeError(f"Failed to connect to HoloWAN device {self.host}:{self.port}: {str(e)}") from e

    def find_path_id(self) -> int:
        """查找名为 'LoomNet' 的 Path ID（保留方法，兼容旧代码）"""
        for i in range(15):
            path = self.engine.get_path_by_id(i + 1)
            if path and path.path_name == "LoomNet":
                return i + 1
        raise RuntimeError("未找到 LoomNet 虚拟链路")

    def get_path_id_by_name(self, path_name: str) -> int:
        """根据路径名称查找 Path ID

        参数:
            path_name: 路径名称

        返回:
            int: 路径 ID

        异常:
            RuntimeError: 设备未连接
            ValueError: 未找到指定名称的路径
        """
        if not self.engine:
            raise RuntimeError("HoloWAN device not connected. Call connect() first.")

        for i in range(1, 16):
            path = self.engine.get_path_by_id(i)
            if path and path.path_name == path_name:
                return i
        raise ValueError(f"Path '{path_name}' not found on HoloWAN device")

    def bind_ip_to_path(self, target_ip: str, path_id: int):
        """在 Port1/Port2 上添加 RawByteRule 绑定 IP 到 Path。

        参数:
            target_ip: 目标 IP 地址
            path_id: 路径 ID
        """
        last_octet = int(target_ip.split('.')[-1])
        hex_value = f"0x{last_octet:02X}"
        label_1 = f"AutoGenFor_{target_ip}_1"
        label_2 = f"AutoGenFor_{target_ip}_2"

        # 清理旧规则
        self._remove_rule_by_label(port=1, label=label_1)
        self._remove_rule_by_label(port=2, label=label_2)

        # 添加新规则
        from holowan.v2.engine.classifier import RawByteRule
        rule1 = RawByteRule(type=1, action=path_id)
        rule1.add_raw_byte(layer=3, offset=59, mask="0xFF", value=hex_value)
        rule1.set_custom_name(label_1)
        self.engine.apply_rule_to_classifier(rule1, port=1)

        rule2 = RawByteRule(type=1, action=path_id)
        rule2.add_raw_byte(layer=3, offset=63, mask="0xFF", value=hex_value)
        rule2.set_custom_name(label_2)
        self.engine.apply_rule_to_classifier(rule2, port=2)

    def upload_and_apply_playback(self, file_path: str, playback_name: str, path_id: int):
        """上传并应用回放文件。

        参数:
            file_path: 回放文件路径
            playback_name: 回放文件名称
            path_id: 路径 ID

        异常:
            RuntimeError: 上传或应用回放文件失败
        """
        # 检查是否已存在
        files = json.loads(self.playback.get_playback_file_list())
        exists = any(f["name"] == playback_name for f in files["data"]["list"])

        if not exists:
            result = self.playback.upload_playback_file(file_path=file_path)
            if '"code": 0' not in result:
                raise RuntimeError(f"上传失败: {result}")
            time.sleep(2)  # 等待设备处理

        # 应用回放
        result = self.playback.apply_playback_file(
            engine_id=self.engine_id,
            path_id=path_id,
            file_name=playback_name
        )
        if json.loads(result)["code"] != 0:
            raise RuntimeError(f"应用失败: {result}")

    def cleanup(self, target_ip: str, playback_name: str, path_id: int):
        """清理：释放回放 + 删除规则 + 删除文件。

        参数:
            target_ip: 目标 IP 地址
            playback_name: 回放文件名称
            path_id: 路径 ID
        """
        # 释放回放
        self.playback.release_playback_file(engine_id=self.engine_id, path_id=path_id)
        time.sleep(1)

        # 删除规则
        label_1 = f"AutoGenFor_{target_ip}_1"
        label_2 = f"AutoGenFor_{target_ip}_2"
        self._remove_rule_by_label(port=1, label=label_1)
        self._remove_rule_by_label(port=2, label=label_2)

        # 删除回放文件
        self.playback.delete_playback_file(file_name=playback_name)

    def _remove_rule_by_label(self, port: int, label: str):
        """内部方法：按 label 删除分类规则。

        参数:
            port: 端口号，1 或 2
            label: 规则标签
        """
        classifier = self.engine.packet_classifier
        nodes = classifier.port1.nodes if port == 1 else classifier.port2.nodes
        for i, rule in enumerate(nodes):
            if rule.get("label") == label:
                classifier.remove_rule(port, i)
                break
