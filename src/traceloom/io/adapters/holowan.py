# -*- coding: utf-8 -*-
"""HoloWAN 格式定义

提供纯格式解析功能，可与 TraceLoom 核心模型集成
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from traceloom.domain.pathlet import Observation

from .holowan_parser import HoloWANParser


@dataclass
class HoloWANDirection:
    """单向网络参数

    Attributes:
        delay: 延迟 (ms)
        loss: 丢包率 (%)
        bw: 带宽 (Mbps)
    """

    delay: float = 0.0
    loss: float = 0.0
    bw: float = 0.0

    def to_list(self) -> List[float]:
        """转换为列表格式

        Returns:
            List[float]: [delay, loss, bw]
        """
        return [self.delay, self.loss, self.bw]

    @classmethod
    def from_list(cls, values: List[float]) -> "HoloWANDirection":
        """从列表创建

        Args:
            values: [delay, loss, bw]

        Returns:
            HoloWANDirection: 创建的对象
        """
        return cls(*values)


@dataclass
class HoloWANDataPoint:
    """HoloWAN 数据点

    Attributes:
        up: 上行网络参数
        down: 下行网络参数
    """

    up: HoloWANDirection = field(default_factory=HoloWANDirection)
    down: HoloWANDirection = field(default_factory=HoloWANDirection)

    def to_list(self) -> List[float]:
        """转换为列表格式

        Returns:
            List[float]: [up.delay, up.loss, up.bw, down.delay, down.loss, down.bw]
        """
        return self.up.to_list() + self.down.to_list()

    @classmethod
    def from_list(cls, values: List[float]) -> "HoloWANDataPoint":
        """从列表创建

        Args:
            values: [up.delay, up.loss, up.bw, down.delay, down.loss, down.bw]

        Returns:
            HoloWANDataPoint: 创建的对象
        """
        up_values = values[:3]
        down_values = values[3:]
        return cls(up=HoloWANDirection.from_list(up_values), down=HoloWANDirection.from_list(down_values))


@dataclass
class HoloWANTrace:
    """HoloWAN 轨迹

    Attributes:
        operator: 运营商
        network_type: 网络类型
        signal_strength: 信号强度 (dbm)
        test_name: 测试名称
        destination: 目标地址
        interval_sec: 采样间隔 (秒)
        packet_size: 数据包大小 (字节)
        enable_reordering: 是否启用重排序
        switch: 开关配置
        start_time: 开始时间
        end_time: 结束时间
        loss_average: 平均丢包率
        data_points: 数据点列表
    """

    operator: str = "Generated"
    network_type: str = "CoreLab"
    signal_strength: int = -100
    test_name: str = field(default_factory=lambda: f"generated_{datetime.now().strftime('%y%m%d_%H%M%S')}")
    destination: str = "127.0.0.1:8080"
    interval_sec: float = 0.1
    packet_size: int = 500
    enable_reordering: bool = True
    switch: str = "1,1,0,1,1,0"
    start_time: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    end_time: Optional[str] = None
    loss_average: float = 0.0
    data_points: List[HoloWANDataPoint] = field(default_factory=list)

    def __post_init__(self, observations: Optional[List[Observation]] = None):
        """初始化后处理

        Args:
            observations: 观元列表（可选）
        """
        # 如果提供了观元列表，转换为数据点
        if observations:
            self.data_points = [self._observation_to_data_point(obs) for obs in observations]

    @classmethod
    def load(cls, file_path: str) -> "HoloWANTrace":
        """从文件加载

        Args:
            file_path: 文件路径

        Returns:
            HoloWANFile: 加载的文件对象
        """
        # 委托给 HoloWANParser 解析原始文件
        observations = HoloWANParser.parse_file(file_path)
        # 创建实例
        holowan_trace = cls()
        # 转换并设置数据点
        holowan_trace.data_points = [holowan_trace._observation_to_data_point(obs) for obs in observations]
        return holowan_trace

    def _observation_to_data_point(self, obs: Observation) -> HoloWANDataPoint:
        """将 Observation 转换为 HoloWANDataPoint

        Args:
            obs: 观元对象

        Returns:
            HoloWANDataPoint: 转换后的数据点
        """
        up = HoloWANDirection(
            delay=obs.delay_up,
            loss=obs.loss_up,
            bw=obs.bw_up
        )
        down = HoloWANDirection(
            delay=obs.delay_down,
            loss=obs.loss_down,
            bw=obs.bw_down
        )
        return HoloWANDataPoint(up=up, down=down)

    def _data_point_to_observation(self, dp: HoloWANDataPoint) -> Observation:
        """将 HoloWANDataPoint 转换为 Observation

        Args:
            dp: 数据点对象

        Returns:
            Observation: 转换后的观元
        """
        return Observation(
            delay_up=dp.up.delay,
            loss_up=dp.up.loss,
            bw_up=dp.up.bw,
            delay_down=dp.down.delay,
            loss_down=dp.down.loss,
            bw_down=dp.down.bw
        )

    def to_observations(self) -> List[Observation]:
        """转换为观元列表

        Returns:
            List[Observation]: 观元列表
        """
        return [self._data_point_to_observation(dp) for dp in self.data_points]

    @classmethod
    def _create_from_header(cls, header: dict, data_points: List[HoloWANDataPoint]) -> "HoloWANTrace":
        """从头部信息创建

        Args:
            header: 头部信息
            data_points: 数据点列表

        Returns:
            HoloWANFile: 创建的文件对象
        """
        # 创建 HoloWANTrace 实例
        holowan_trace = cls(**header)
        # 添加数据点
        holowan_trace.data_points = data_points
        return holowan_trace

    @staticmethod
    def save(file_path: Path, holowan_trace: "HoloWANTrace") -> None:
        """保存到文件

        Args:
            file_path: 文件路径
            holowan_trace: 要保存的轨迹对象
        """
        # 确保输出目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 计算统计信息
        holowan_trace._calculate_statistics()

        # 准备文件内容
        file_content = []

        # 写入标准 HoloWAN 文件头
        file_content.append("# HoloWAN Playback v1.0")
        file_content.append(f'Operator: "{holowan_trace.operator}" NetworkType: "{holowan_trace.network_type}"')
        file_content.append(f" SignalStrength: {holowan_trace.signal_strength}(dbm)")
        file_content.append(f'test_name: "{holowan_trace.test_name}"')
        file_content.append(f'Destination: "{holowan_trace.destination}"')
        file_content.append(f"Start Time: {holowan_trace.start_time}")
        file_content.append(f"End Time: {holowan_trace.end_time}")
        file_content.append(f"Interval(sec): {holowan_trace.interval_sec}")
        file_content.append(f"Packet Size(byte): {holowan_trace.packet_size}")
        file_content.append(f"Loss Average: {holowan_trace.loss_average:.2f}")
        file_content.append(f"Enable Reordering: {holowan_trace.enable_reordering}")
        file_content.append("Contents: Delay1(ms),Loss1(%),Bandwidth1(Mbps),Delay2(ms),Loss2(%),Bandwidth2(Mbps)")
        file_content.append(f"Switch: {holowan_trace.switch}")

        # 写入分隔线
        file_content.append("------------------------------------------------")

        # 写入数据
        for data_point in holowan_trace.data_points:
            values = data_point.to_list()
            file_content.append(
                f"{values[0]:.2f},{values[1]:.2f},{values[2]:.6f},{values[3]:.2f},{values[4]:.2f},{values[5]:.6f}"
            )

        # 写入文件
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(file_content))

    @staticmethod
    def _parse_header_line(header: dict, line: str) -> None:
        """解析文件头行

        Args:
            header: 存储解析结果的字典
            line: 要解析的行
        """
        # 解析操作符行
        if line.startswith("Operator:"):
            parts = line.split()
            if len(parts) >= 5:
                header["operator"] = parts[1].strip('"')
                header["network_type"] = parts[3].strip('"')
            return

        # 解析信号强度行
        if "SignalStrength:" in line:
            parts = line.split("SignalStrength:")
            if len(parts) > 1:
                header["signal_strength"] = int(parts[1].strip().split("(")[0])
            return

        # 定义前缀到键的映射
        prefix_map = {
            "test_name:": "test_name",
            "Destination:": "destination",
            "Start Time:": "start_time",
            "End Time:": "end_time",
            "Interval(sec):": "interval_sec",
            "Packet Size(byte):": "packet_size",
            "Loss Average:": "loss_average",
            "Enable Reordering:": "enable_reordering",
            "Switch:": "switch",
        }

        # 定义键到类型转换器的映射
        converters = {
            "interval_sec": float,
            "loss_average": float,
            "packet_size": int,
            "enable_reordering": lambda x: x.lower() == "true",
            "test_name": lambda x: x.strip('"'),
            "destination": lambda x: x.strip('"'),
        }

        # 解析通用行
        for prefix, key in prefix_map.items():
            if line.startswith(prefix):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    value = parts[1].strip()
                    # 应用类型转换
                    if key in converters:
                        try:
                            value = converters[key](value)
                        except (ValueError, TypeError):
                            pass
                    header[key] = value
                return

    @staticmethod
    def _parse_data_line(data_points: List[HoloWANDataPoint], line: str) -> None:
        """解析数据行

        Args:
            data_points: 存储数据点的列表
            line: 要解析的行
        """
        parts = line.split(",")
        if len(parts) >= 6:
            try:
                # 提取数据
                values = [float(part) for part in parts[:6]]
                # 创建数据点对象
                data_point = HoloWANDataPoint.from_list(values)
                data_points.append(data_point)
            except (ValueError, IndexError):
                pass  # 跳过格式错误的行



    def _calculate_statistics(self) -> None:
        """计算统计信息

        计算平均丢包率和结束时间
        """
        if not self.data_points:
            return

        # 计算平均丢包率
        total_loss = sum(dp.up.loss + dp.down.loss for dp in self.data_points)
        self.loss_average = total_loss / (len(self.data_points) * 2) if self.data_points else 0.0

        # 计算结束时间
        if self.start_time and self.interval_sec:
            from datetime import datetime, timedelta

            try:
                start_dt = datetime.strptime(self.start_time, "%Y-%m-%d %H:%M:%S")
                total_time = len(self.data_points) * self.interval_sec
                end_dt = start_dt + timedelta(seconds=total_time)
                self.end_time = end_dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                self.end_time = None  # 时间格式错误时保留 None

    def dump(self) -> str:
        """生成严格格式的 HoloWAN 回放内容

        Returns:
            str: 回放文件内容
        """
        # 计算统计信息
        self._calculate_statistics()

        # 准备文件内容
        file_content = []

        # 写入标准 HoloWAN 文件头
        file_content.append("# HoloWAN Playback v1.0")
        file_content.append(f'Operator: "{self.operator}" NetworkType: "{self.network_type}"')
        file_content.append(f" SignalStrength: {self.signal_strength}(dbm)")
        file_content.append(f'test_name: "{self.test_name}"')
        file_content.append(f'Destination: "{self.destination}"')
        file_content.append(f"Start Time: {self.start_time}")
        file_content.append(f"End Time: {self.end_time}")
        file_content.append(f"Interval(sec): {self.interval_sec}")
        file_content.append(f"Packet Size(byte): {self.packet_size}")
        file_content.append(f"Loss Average: {self.loss_average:.2f}")
        file_content.append(f"Enable Reordering: {self.enable_reordering}")
        file_content.append("Contents: Delay1(ms),Loss1(%),Bandwidth1(Mbps),Delay2(ms),Loss2(%),Bandwidth2(Mbps)")
        file_content.append(f"Switch: {self.switch}")

        # 写入分隔线
        file_content.append("------------------------------------------------")

        # 写入数据
        for data_point in self.data_points:
            values = data_point.to_list()
            file_content.append(
                f"{values[0]:.2f},{values[1]:.2f},{values[2]:.6f},{values[3]:.2f},{values[4]:.2f},{values[5]:.6f}"
            )

        return "\n".join(file_content)
