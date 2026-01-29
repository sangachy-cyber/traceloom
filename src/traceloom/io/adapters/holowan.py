# -*- coding: utf-8 -*-
"""HoloWAN 轨迹解析模块

此模块提供了 HoloWAN 轨迹文件的解析、处理和生成功能。

功能包括：
- 解析 HoloWAN 轨迹文件
- 生成滑动窗口和过滤窗口
- 转换轨迹数据为观测对象
- 从观测对象生成轨迹数据

示例：
    # 加载 HoloWAN 轨迹文件
    from traceloom.io.adapters.holowan import HoloWANTrace
    trace = HoloWANTrace.load("path/to/trace.txt")

    # 生成过滤后的滑动窗口
    windows = list(trace.filtered_sliding_windows())

    # 转换为观测对象
    observations = trace.to_observations()
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, List, Optional

from traceloom.core.exceptions import DataError, FileOperationError, ValidationError
from traceloom.core.logger import get_logger
from traceloom.domain.pathlet import Observation, PathletMeta
from traceloom.domain.pathlet import Pathlet

# 获取日志实例
logger = get_logger()


@dataclass
class HoloWANDirection:
    """HoloWAN 方向参数

    表示网络轨迹中一个方向（上行或下行）的网络参数。

    Attributes:
        delay: float
            延迟，单位为毫秒
        loss: float
            丢包率，范围为 [0.0, 1.0]
        bw: float
            带宽，单位为 Mbps

    示例:
        # 创建一个上行方向参数
        up_dir = HoloWANDirection(delay=10.0, loss=0.01, bw=100.0)
    """

    delay: float  # milliseconds
    loss: float  # proportion in [0.0, 1.0]
    bw: float  # Mbps


@dataclass
class HoloWANPoint:
    """HoloWAN 轨迹点

    表示 HoloWAN 轨迹文件中的一行原始采样数据。

    Attributes:
        up: HoloWANDirection
            上行方向的网络参数
        down: HoloWANDirection
            下行方向的网络参数

    示例:
        # 从原始数据行创建
        point = HoloWANPoint.from_raw_row([10.0, 1.0, 100.0, 8.0, 0.5, 200.0])

        # 从观测对象创建
        from traceloom.domain.pathlet import Observation
        obs = Observation(delay_up=10.0, loss_up=0.01, bw_up=100.0,
                         delay_down=8.0, loss_down=0.005, bw_down=200.0)
        point = HoloWANPoint.from_observation(obs)
    """

    up: HoloWANDirection
    down: HoloWANDirection

    @classmethod
    def from_raw_row(cls, row: List[float]) -> "HoloWANPoint":
        """从原始数据行创建 HoloWANPoint 对象

        Args:
            row: List[float]
                原始数据行，包含6个浮点数：
                [上行延迟, 上行丢包率(%), 上行带宽, 下行延迟, 下行丢包率(%), 下行带宽]

        Returns:
            HoloWANPoint
                创建的 HoloWANPoint 对象

        Raises:
            ValidationError
                如果数据行长度不正确
            ValidationError
                如果丢包率超出有效范围

        示例:
            point = HoloWANPoint.from_raw_row([10.0, 1.0, 100.0, 8.0, 0.5, 200.0])
        """
        if len(row) != 6:
            raise ValidationError(f"Expected 6 values, got {len(row)}: {row}")
        u_d, u_l_pct, u_b, d_d, d_l_pct, d_b = row

        # Convert loss from percentage to proportion [0,1]
        u_l = u_l_pct / 100.0
        d_l = d_l_pct / 100.0

        # Validate loss range (after conversion)
        if not (0.0 <= u_l <= 1.0):
            raise ValidationError(f"Invalid up loss: {u_l} (from {u_l_pct}%)")
        if not (0.0 <= d_l <= 1.0):
            raise ValidationError(f"Invalid down loss: {d_l} (from {d_l_pct}%)")

        # If bandwidth is zero, force loss to 1.0
        if u_b == 0.0:
            u_l = 1.0
        if d_b == 0.0:
            d_l = 1.0

        return cls(up=HoloWANDirection(u_d, u_l, u_b), down=HoloWANDirection(d_d, d_l, d_b))

    def to_raw_row(self) -> List[float]:
        """将 HoloWANPoint 对象转换为原始数据行

        Returns:
            List[float]
                原始数据行，包含6个浮点数：
                [上行延迟, 上行丢包率(%), 上行带宽, 下行延迟, 下行丢包率(%), 下行带宽]

        示例:
            row = point.to_raw_row()
            # 输出: [10.0, 1.0, 100.0, 8.0, 0.5, 200.0]
        """
        # Convert loss back to percentage for file output
        return [
            self.up.delay,
            self.up.loss * 100.0,
            self.up.bw,
            self.down.delay,
            self.down.loss * 100.0,
            self.down.bw,
        ]

    @classmethod
    def from_observation(cls, obs: Observation) -> "HoloWANPoint":
        """从观测对象创建 HoloWANPoint 对象

        Args:
            obs: Observation
                观测对象，包含网络参数信息

        Returns:
            HoloWANPoint
                创建的 HoloWANPoint 对象

        示例:
            from traceloom.domain.pathlet import Observation
            obs = Observation(delay_up=10.0, loss_up=0.01, bw_up=100.0,
                             delay_down=8.0, loss_down=0.005, bw_down=200.0)
            point = HoloWANPoint.from_observation(obs)
        """
        return cls(
            up=HoloWANDirection(obs.delay_up, obs.loss_up, obs.bw_up),
            down=HoloWANDirection(obs.delay_down, obs.loss_down, obs.bw_down),
        )

    def to_observation(self) -> Observation:
        """将 HoloWANPoint 对象转换为 Observation 对象

        Returns:
            Observation
                转换后的 Observation 对象

        示例:
            obs = point.to_observation()
        """
        return Observation(
            delay_up=self.up.delay,
            loss_up=self.up.loss,
            bw_up=self.up.bw,
            delay_down=self.down.delay,
            loss_down=self.down.loss,
            bw_down=self.down.bw,
        )


def _has_large_delay(window: List[HoloWANPoint], threshold: float = 2000.0) -> bool:
    """检查窗口中是否有延迟超过阈值的点

    Args:
        window: List[HoloWANPoint]
            轨迹点窗口
        threshold: float, optional
            延迟阈值，单位为毫秒，默认值为 2000.0

    Returns:
        bool
            如果窗口中有任何点的上行或下行延迟超过阈值，返回 True；否则返回 False

    示例:
        has_large = _has_large_delay(window, threshold=1000.0)
    """
    for point in window:
        if point.up.delay > threshold or point.down.delay > threshold:
            return True
    return False


def _has_consecutive_equal_delays(delays: List[float], min_consecutive: int = 10) -> bool:
    """检查是否有连续相同的延迟值

    Args:
        delays: List[float]
            延迟值列表
        min_consecutive: int, optional
            最小连续次数，默认值为 10

    Returns:
        bool
            如果有至少 min_consecutive 个连续相同的延迟值，返回 True；否则返回 False

    示例:
        has_consecutive = _has_consecutive_equal_delays(delays, min_consecutive=5)
    """
    if len(delays) < min_consecutive:
        return False
    count = 1
    for i in range(1, len(delays)):
        if delays[i] == delays[i - 1]:
            count += 1
            if count >= min_consecutive:
                return True
        else:
            count = 1
    return False


def _is_window_valid(window: List[HoloWANPoint], check_size: int = 100) -> bool:
    """检查窗口是否有效

    应用过滤规则：
    - 无延迟 > 2000 ms
    - 无 10+ 个连续相同的延迟值（上行或下行）

    Args:
        window: List[HoloWANPoint]
            轨迹点窗口
        check_size: int, optional
            检查的数据点数量，默认值为 100，表示只检查前100个数据点

    Returns:
        bool
            如果窗口有效，返回 True；否则返回 False

    示例:
        is_valid = _is_window_valid(window)  # 检查前100个数据点
        is_valid = _is_window_valid(window, check_size=50)  # 只检查前50个数据点
    """
    # 只检查窗口的前 check_size 个数据点
    check_window = window[:check_size]

    if _has_large_delay(check_window, threshold=2000.0):
        return False

    up_delays = [p.up.delay for p in check_window]
    down_delays = [p.down.delay for p in check_window]

    if _has_consecutive_equal_delays(up_delays, min_consecutive=10):
        return False
    if _has_consecutive_equal_delays(down_delays, min_consecutive=10):
        return False

    return True


@dataclass(frozen=True)
class ValidHoloWANWindow:
    """
    A filtered, valid 100-sample window from a HoloWAN trace.

    Guaranteed to:
      - Have exactly 100 points
      - Contain no delay > 2000 ms
      - Have no 10+ consecutive equal delays (up or down)
    """

    trace_name: str
    start_index: int


@dataclass
class HoloWANTrace:
    """HoloWAN 轨迹

    表示完整的 HoloWAN 轨迹文件，包含头部信息和轨迹点数据。

    Attributes:
        operator: str
            运营商名称
        network_type: str
            网络类型
        signal_strength: int
            信号强度（dbm）
        test_name: str
            测试名称
        destination: str
            目标地址
        start_time: str
            开始时间
        end_time: Optional[str]
            结束时间
        timezone: str
            时区
        description: str
            轨迹描述
        interval_sec: float
            间隔时间（秒）
        packet_size: int
            数据包大小（字节）
        enable_reordering: bool
            是否启用重排序
        switch: str
            开关配置
        loss_average: float
            平均丢包率
        points: List[HoloWANPoint]
            轨迹点列表

    示例:
        # 加载轨迹文件
        trace = HoloWANTrace.load("path/to/trace.txt")

        # 从观测对象创建轨迹
        from traceloom.domain.pathlet import Observation
        observations = [Observation(...), Observation(...)]
        trace = HoloWANTrace.from_observations(observations, operator="China Mobile")
    """

    operator: str = "Generated"
    network_type: str = "CoreLab"
    signal_strength: int = -100
    test_name: str = field(default_factory=lambda: f"generated_{datetime.now().strftime('%y%m%d_%H%M%S')}")
    destination: str = "127.0.0.1:8080"
    start_time: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    end_time: Optional[str] = None
    timezone: str = "UTC"
    description: str = ""
    interval_sec: float = 0.1
    packet_size: int = 500
    enable_reordering: bool = True
    switch: str = "1,1,0,1,1,0"
    loss_average: float = 0.0
    points: List[HoloWANPoint] = field(default_factory=list)
    file_name: str = ""

    @classmethod
    def _parse_file_lines(cls, file_path: str) -> tuple[dict, list]:
        """解析文件行，提取头部信息和数据行

        Args:
            file_path: str
                轨迹文件路径

        Returns:
            tuple[dict, list]
                头部信息字典和数据行列表

        Raises:
            FileOperationError
                如果文件操作失败
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = [line.rstrip() for line in f if line.rstrip()]
        except Exception as e:
            raise FileOperationError(f"Failed to read file: {file_path}") from e

        header_info: dict[str, str] = {}
        data_lines: list[str] = []
        in_data_section = False

        for line in lines:
            if line == "------------------------------------------------":
                in_data_section = True
                continue

            if not in_data_section:
                if line.startswith("#"):
                    continue
                if ":" not in line:
                    # 跳过不包含冒号的行，如文件开头的注释行
                    continue
                cls._parse_header_line(header_info, line)
            else:
                data_lines.append(line)

        return header_info, data_lines

    @classmethod
    def _validate_header(cls, header_info: dict, file_path: str) -> None:
        """验证头部信息

        Args:
            header_info: dict
                头部信息字典
            file_path: str
                轨迹文件路径

        Raises:
            ValidationError
                如果缺少必要的头部字段
        """
        # 只验证最基本的必要字段，其他字段使用默认值
        required_fields = ["start_time"]
        for required_field in required_fields:
            if required_field not in header_info:
                raise ValidationError(f"Missing required header field: '{required_field}' in {file_path}")

    @classmethod
    def _parse_data_lines(cls, data_lines: list) -> list:
        """解析数据行

        Args:
            data_lines: list
                数据行列表

        Returns:
            list
                HoloWANPoint 对象列表

        Raises:
            DataError
                如果数据解析失败
        """
        points = []
        for i, line in enumerate(data_lines):
            try:
                nums = list(map(float, line.split(",")))
            except Exception as e:
                raise DataError(f"Failed to parse data line {i + 1}: '{line}'") from e
            if len(nums) != 6:
                raise DataError(f"Line {i + 1} must have 6 numbers, got {len(nums)}")

            points.append(HoloWANPoint.from_raw_row(nums))

        return points

    @classmethod
    def load(cls, file_path: str) -> "HoloWANTrace":
        """从文件加载 HoloWANTrace 对象

        Args:
            file_path: str
                轨迹文件路径

        Returns:
            HoloWANTrace
                加载的 HoloWANTrace 对象

        Raises:
            FileOperationError
                如果文件操作失败
            ValidationError
                如果文件格式无效或缺少必要的头部字段
            DataError
                如果数据解析失败

        示例:
            trace = HoloWANTrace.load("data/raw/trace.txt")
        """
        logger.info(f"正在加载 HoloWAN 轨迹文件: {file_path}")
        # 解析文件行
        header_info, data_lines = cls._parse_file_lines(file_path)

        # 验证头部信息
        cls._validate_header(header_info, file_path)

        # 解析数据行
        points = cls._parse_data_lines(data_lines)

        logger.info(f"成功加载 HoloWAN 轨迹文件，包含 {len(points)} 个轨迹点")
        # 使用字典的 get 方法获取字段值，如果不存在则使用默认值
        return cls(
            operator=header_info.get("operator", "Generated"),
            network_type=header_info.get("network_type", "CoreLab"),
            signal_strength=header_info.get("signal_strength", -100),
            test_name=header_info.get("test_name", f"generated_{datetime.now().strftime('%y%m%d_%H%M%S')}"),
            destination=header_info.get("destination", "127.0.0.1:8080"),
            start_time=header_info.get("start_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            end_time=header_info.get("end_time"),
            timezone=header_info.get("timezone", "UTC"),
            description=header_info.get("description", ""),
            interval_sec=header_info.get("interval_sec", 0.1),
            packet_size=header_info.get("packet_size", 500),
            enable_reordering=header_info.get("enable_reordering", True),
            switch=header_info.get("switch", "1,1,0,1,1,0"),
            loss_average=header_info.get("loss_average", 0.0),
            points=points,
            file_name=Path(file_path).stem,
        )

    @staticmethod
    def _parse_header_line(header_dict: dict, line: str) -> None:
        """解析头部行

        Args:
            header_dict: dict
                存储头部信息的字典
            line: str
                头部行字符串

        Raises:
            ValidationError
                如果头部行格式无效

        示例:
            header_info = {}
            HoloWANTrace._parse_header_line(header_info, "Operator: China Mobile")
        """
        if ":" not in line:
            raise ValidationError(f"Invalid header line (no colon): {line}")

        # 处理包含多个键值对的行，如 "Operator: \"Generated\" NetworkType: \"CoreLab\""
        if "NetworkType:" in line:
            HoloWANTrace._parse_network_type_line(header_dict, line)
        else:
            # 常规行解析
            HoloWANTrace._parse_regular_header_line(header_dict, line)

    @staticmethod
    def _parse_network_type_line(header_dict: dict, line: str) -> None:
        """解析包含 NetworkType 的头部行

        Args:
            header_dict: dict
                存储头部信息的字典
            line: str
                头部行字符串
        """
        parts = line.split("NetworkType:")
        operator_part = parts[0].strip()
        network_type_part = parts[1].strip()

        # 解析 operator
        if ":" in operator_part:
            op_key, op_value = operator_part.split(":", 1)
            op_key = op_key.strip().lower().replace(" ", "_")
            op_value = op_value.strip().strip('"')
            header_dict[op_key] = op_value

        # 解析 network_type
        nt_value = network_type_part.strip().strip('"')
        header_dict["network_type"] = nt_value

    @staticmethod
    def _parse_regular_header_line(header_dict: dict, line: str) -> None:
        """解析常规头部行

        Args:
            header_dict: dict
                存储头部信息的字典
            line: str
                头部行字符串
        """
        key, value = line.split(":", 1)
        key = key.strip().lower().replace(" ", "_")
        value = value.strip()

        # 处理带引号的值
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]

        # 处理带有单位的值
        if key == "signal_strength" and "(dbm)" in value:
            value = value.replace("(dbm)", "").strip()

        # 转换数值类型
        value = HoloWANTrace._convert_value_type(key, value)

        header_dict[key] = value

    @staticmethod
    def _convert_value_type(key: str, value: str) -> Any:
        """转换值的类型

        Args:
            key: str
                键名
            value: str
                原始值

        Returns:
            Any
                转换后的值
        """
        if key in ["signal_strength", "packet_size"]:
            try:
                return int(value)
            except ValueError:
                pass
        elif key in ["interval_sec", "loss_average"]:
            try:
                return float(value)
            except ValueError:
                pass
        elif key == "enable_reordering":
            return value.lower() == "true"
        return value

    def dump(self, file_path: str) -> None:
        """将 HoloWANTrace 对象写入文件

        Args:
            file_path: str
                输出文件路径

        Raises:
            FileOperationError
                如果文件操作失败

        示例:
            trace.dump("output/trace.txt")
        """
        try:
            logger.info(f"正在写入 HoloWAN 轨迹文件: {file_path}")
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                # 写入标准 HoloWAN 文件头
                f.write("# HoloWAN Playback v1.0\n")
                f.write(f'Operator: "{self.operator}" NetworkType: "{self.network_type}"\n')
                f.write(f" SignalStrength: {self.signal_strength}(dbm)\n")
                f.write(f'test_name: "{self.test_name}"\n')
                f.write(f'Destination: "{self.destination}"\n')
                f.write(f"Start Time: {self.start_time}\n")
                f.write(f"End Time: {self.end_time}\n")
                f.write(f"Interval(sec): {self.interval_sec}\n")
                f.write(f"Packet Size(byte): {self.packet_size}\n")
                f.write(f"Loss Average: {self.loss_average:.2f}\n")
                f.write(f"Enable Reordering: {self.enable_reordering}\n")
                f.write("Contents: Delay1(ms),Loss1(%),Bandwidth1(Mbps),Delay2(ms),Loss2(%),Bandwidth2(Mbps)\n")
                f.write(f"Switch: {self.switch}\n")

                # 写入分隔线
                f.write("------------------------------------------------\n")

                # 写入数据点
                for point in self.points:
                    row_str = " ".join(f"{x}" for x in point.to_raw_row())
                    f.write(row_str + "\n")
            logger.info(f"成功写入 HoloWAN 轨迹文件，包含 {len(self.points)} 个轨迹点")
        except Exception as e:
            raise FileOperationError(f"Failed to write file: {file_path}") from e

    # def sliding_windows(self, window_size: int = 100, step: int = 50) -> Iterator[List[HoloWANPoint]]:
    #     """生成滑动窗口
    #
    #     生成滑动窗口（长度=100，步长=50），不应用过滤。
    #
    #     Args:
    #         window_size: int, optional
    #             窗口大小，默认值为 100
    #         step: int, optional
    #             步长，默认值为 50
    #
    #     Returns:
    #         Iterator[List[HoloWANPoint]]
    #             滑动窗口的迭代器
    #
    #     Raises:
    #         ValidationError
    #             如果 window_size 或 step 不是正整数
    #
    #     示例:
    #         for window in trace.sliding_windows(window_size=50, step=25):
    #             print(f"Window size: {len(window)}")
    #     """
    #     if window_size <= 0 or step <= 0:
    #         raise ValidationError("window_size and step must be positive integers.")
    #     n = len(self.points)
    #     if n < window_size:
    #         logger.warning(f"轨迹点数量 ({n}) 小于窗口大小 ({window_size})，无法生成滑动窗口")
    #         return
    #     start = 0
    #     while start + window_size <= n:
    #         yield self.points[start : start + window_size]
    #         start += step

    def extended_sliding_windows(
        self, window_size: int = 100, extension_size: int = 10, step: int = 50
    ) -> Iterator[tuple[PathletMeta, "Pathlet"]]:
        """生成带延长数据点的滑动窗口

        生成滑动窗口（长度=100，步长=50），并在每个窗口后添加10个延长数据点，不应用过滤。

        Args:
            window_size: int, optional
                窗口大小，默认值为 100
            extension_size: int, optional
                延长数据点数量，默认值为 10
            step: int, optional
                步长，默认值为 50

        Returns:
            Iterator[tuple[PathletMeta, Pathlet]]
                带延长数据点的滑动窗口的迭代器，每个元素为 (PathletMeta, Pathlet) 元组

        Raises:
            ValidationError
                如果 window_size、extension_size 或 step 不是正整数

        示例:
            for pathlet_meta, pathlet in trace.extended_sliding_windows():
                print(f"Trace name: {pathlet_meta.trace_name}")
                print(f"Start index: {pathlet_meta.start_index}")
                print(f"Pathlet ID: {pathlet.pathlet_id}")
                print(f"Observations count: {len(pathlet_meta.observations)}")  # 输出: 110
        """

        if window_size <= 0 or extension_size <= 0 or step <= 0:
            raise ValidationError("window_size, extension_size and step must be positive integers.")
        n = len(self.points)
        total_window_size = window_size + extension_size
        if n < total_window_size:
            logger.warning(
                f"轨迹点数量 ({n}) 小于窗口大小 + 延长数据点数量 ({total_window_size})，无法生成带延长数据点的滑动窗口"
            )
            return
        start = 0
        while start + total_window_size <= n:
            window = self.points[start : start + total_window_size]
            # Convert HoloWANPoint objects to Observation objects
            observations = [point.to_observation() for point in window]
            # Create Pathlet object
            pathlet_id = f"{self.file_name}_{start}"
            # Create PathletMeta object
            pathlet_meta = PathletMeta(
                pathlet_id=pathlet_id,
                trace_name=self.file_name,  # Use test_name as trace_name
                start_index=start,
                is_valid=True,  # Default to valid, filtering is handled elsewhere
                observations=observations,
            )

            pathlet = Pathlet(
                pathlet_id=pathlet_id,
                trace_name=self.file_name,
                start_index=start,
                body=pathlet_meta.get_body_observations(),
                tail=pathlet_meta.get_tail_observations(),
            )
            yield pathlet_meta, pathlet
            start += step

    # def filtered_sliding_windows(self, window_size: int = 100, step: int = 50) -> Iterator[List[HoloWANPoint]]:
    #     """生成过滤后的滑动窗口
    #
    #     生成滑动窗口并应用质量过滤器：
    #     - 丢弃任何延迟 > 2000 ms 的窗口
    #     - 丢弃包含 10+ 个连续相同延迟值（上行或下行）的窗口
    #
    #     Args:
    #         window_size: int, optional
    #             窗口大小，默认值为 100
    #         step: int, optional
    #             步长，默认值为 50
    #
    #     Returns:
    #         Iterator[List[HoloWANPoint]]
    #             过滤后的滑动窗口的迭代器
    #
    #     示例:
    #         valid_windows = list(trace.filtered_sliding_windows())
    #         print(f"Valid windows: {len(valid_windows)}")
    #     """
    #     for window in self.sliding_windows(window_size, step):
    #         if _is_window_valid(window, check_size=window_size):
    #             yield window

    def filtered_extended_sliding_windows(
        self, window_size: int = 100, extension_size: int = 10, step: int = 50
    ) -> Iterator[tuple[PathletMeta, "Pathlet"]]:
        """生成过滤后的带延长数据点的滑动窗口

        生成带延长数据点的滑动窗口并应用质量过滤器：
        - 丢弃任何延迟 > 2000 ms
        - 丢弃包含 10+ 个连续相同延迟值（上行或下行）的窗口
        - 只检查前 100 个数据点的质量，延长的 10 个数据点不参与质量检查

        Args:
            window_size: int, optional
                窗口大小，默认值为 100
            extension_size: int, optional
                延长数据点数量，默认值为 10
            step: int, optional
                步长，默认值为 50

        Returns:
            Iterator[tuple[PathletMeta, Pathlet]]
                过滤后的带延长数据点的滑动窗口的迭代器，每个元素为 (PathletMeta, Pathlet) 元组

        示例:
            valid_pairs = list(trace.filtered_extended_sliding_windows())
            print(f"Valid pairs: {len(valid_pairs)}")
            print(f"Pathlet ID: {valid_pairs[0][1].pathlet_id}")
            print(f"Observations count: {len(valid_pairs[0][0].observations)}")  # 输出: 110
        """
        from traceloom.domain.pathlet import Pathlet

        for pathlet_meta, pathlet in self.extended_sliding_windows(window_size, extension_size, step):
            # Convert Observation objects back to HoloWANPoint objects for validation
            window_points = [HoloWANPoint.from_observation(obs) for obs in pathlet_meta.observations]
            if _is_window_valid(window_points, check_size=window_size):
                yield pathlet_meta, pathlet

    # def get_filtered_windows_with_stats(
    #     self, window_size: int = 100, step: int = 50
    # ) -> tuple[List[List[HoloWANPoint]], dict]:
    #     """获取过滤后的窗口和统计信息
    #
    #     返回所有有效的窗口和详细的过滤统计信息。
    #
    #     Args:
    #         window_size: int, optional
    #             窗口大小，默认值为 100
    #         step: int, optional
    #             步长，默认值为 50
    #
    #     Returns:
    #         tuple[List[List[HoloWANPoint]], dict]
    #             - 有效的窗口列表
    #             - 统计信息字典，包含以下键：
    #                 - total_windows: 总窗口数
    #                 - valid_windows: 有效窗口数
    #                 - filtered_by_large_delay: 因大延迟被过滤的窗口数
    #                 - filtered_by_consecutive_delay: 因连续延迟被过滤的窗口数
    #                 - valid_ratio: 有效窗口比例
    #
    #     示例:
    #         windows, stats = trace.get_filtered_windows_with_stats()
    #         print(f"Valid ratio: {stats['valid_ratio']:.2f}")
    #     """
    #     total = 0
    #     valid = 0
    #     by_large_delay = 0
    #     by_consecutive = 0
    #
    #     valid_windows = []
    #
    #     for window in self.sliding_windows(window_size, step):
    #         total += 1
    #
    #         # 只检查窗口的前 window_size 个数据点
    #         check_window = window[:window_size]
    #
    #         # Check large delay
    #         if _has_large_delay(check_window, threshold=2000.0):
    #             by_large_delay += 1
    #             continue
    #
    #         # Check consecutive equal delays
    #         up_delays = [p.up.delay for p in check_window]
    #         down_delays = [p.down.delay for p in check_window]
    #         has_consec_up = _has_consecutive_equal_delays(up_delays, min_consecutive=10)
    #         has_consec_down = _has_consecutive_equal_delays(down_delays, min_consecutive=10)
    #
    #         if has_consec_up or has_consec_down:
    #             by_consecutive += 1
    #             continue
    #
    #         # If passed all checks
    #         valid += 1
    #         valid_windows.append(window)
    #
    #     stats = {
    #         "total_windows": total,
    #         "valid_windows": valid,
    #         "filtered_by_large_delay": by_large_delay,
    #         "filtered_by_consecutive_delay": by_consecutive,
    #         "valid_ratio": valid / total if total > 0 else 0.0,
    #     }
    #     logger.info(f"窗口过滤统计: {stats}")
    #     return valid_windows, stats

    def get_filtered_extended_windows_with_stats(
        self, window_size: int = 100, extension_size: int = 10, step: int = 50
    ) -> tuple[List[tuple[PathletMeta, "Pathlet"]], dict]:
        """获取过滤后的带延长数据点的窗口和统计信息

        返回所有有效的带延长数据点的窗口和详细的过滤统计信息。

        Args:
            window_size: int, optional
                窗口大小，默认值为 100
            extension_size: int, optional
                延长数据点数量，默认值为 10
            step: int, optional
                步长，默认值为 50

        Returns:
            tuple[List[tuple[PathletMeta, Pathlet]], dict]
                - 有效的带延长数据点的窗口列表，每个元素为 (PathletMeta, Pathlet) 元组
                - 统计信息字典，包含以下键：
                    - total_windows: 总窗口数
                    - valid_windows: 有效窗口数
                    - filtered_by_large_delay: 因大延迟被过滤的窗口数
                    - filtered_by_consecutive_delay: 因连续延迟被过滤的窗口数
                    - valid_ratio: 有效窗口比例

        示例:
            valid_pairs, stats = trace.get_filtered_extended_windows_with_stats()
            print(f"Valid ratio: {stats['valid_ratio']:.2f}")
            print(f"Pathlet ID: {valid_pairs[0][1].pathlet_id}")
            print(f"Observations count: {len(valid_pairs[0][0].observations)}")  # 输出: 110
        """
        from traceloom.domain.pathlet import Pathlet

        total = 0
        valid = 0
        by_large_delay = 0
        by_consecutive = 0

        valid_windows = []

        for pathlet_meta, pathlet in self.extended_sliding_windows(window_size, extension_size, step):
            total += 1

            # Convert Observation objects back to HoloWANPoint objects for validation
            window_points = [HoloWANPoint.from_observation(obs) for obs in pathlet_meta.observations]

            # 只检查窗口的前 window_size 个数据点
            check_window = window_points[:window_size]

            # Check large delay
            if _has_large_delay(check_window, threshold=2000.0):
                by_large_delay += 1
                continue

            # Check consecutive equal delays
            up_delays = [p.up.delay for p in check_window]
            down_delays = [p.down.delay for p in check_window]
            has_consec_up = _has_consecutive_equal_delays(up_delays, min_consecutive=10)
            has_consec_down = _has_consecutive_equal_delays(down_delays, min_consecutive=10)

            if has_consec_up or has_consec_down:
                by_consecutive += 1
                continue

            # If passed all checks
            valid += 1
            valid_windows.append((pathlet_meta, pathlet))

        stats = {
            "total_windows": total,
            "valid_windows": valid,
            "filtered_by_large_delay": by_large_delay,
            "filtered_by_consecutive_delay": by_consecutive,
            "valid_ratio": valid / total if total > 0 else 0.0,
        }
        logger.info(f"带延长数据点的窗口过滤统计: {stats}")
        return valid_windows, stats

    def to_observations(self) -> List[Observation]:
        """将 HoloWANTrace 对象转换为 Observation 对象列表

        Returns:
            List[Observation]
                转换后的 Observation 对象列表

        示例:
            observations = trace.to_observations()
            print(f"Observations count: {len(observations)}")
        """
        return [point.to_observation() for point in self.points]

    @classmethod
    def from_observations(
        cls,
        observations: List[Observation],
        *,
        operator: str = "Generated",
        network_type: str = "CoreLab",
        signal_strength: int = -100,
        test_name: Optional[str] = None,
        destination: str = "127.0.0.1:8080",
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        timezone: str = "UTC",
        description: str = "",
        interval_sec: float = 0.1,
        packet_size: int = 500,
        enable_reordering: bool = True,
        switch: str = "1,1,0,1,1,0",
        loss_average: float = 0.0,
    ) -> "HoloWANTrace":
        """从 Observation 对象列表创建 HoloWANTrace 对象

        Args:
            observations: List[Observation]
                Observation 对象列表
            operator: str, optional
                运营商名称，默认值为 "Generated"
            network_type: str, optional
                网络类型，默认值为 "CoreLab"
            signal_strength: int, optional
                信号强度（dbm），默认值为 -100
            test_name: Optional[str], optional
                测试名称，默认值为自动生成
            destination: str, optional
                目标地址，默认值为 "127.0.0.1:8080"
            start_time: Optional[str], optional
                开始时间，默认值为当前时间
            end_time: Optional[str], optional
                结束时间，默认值为 None
            timezone: str, optional
                时区，默认值为 "UTC"
            description: str, optional
                轨迹描述，默认值为空字符串
            interval_sec: float, optional
                间隔时间（秒），默认值为 0.1
            packet_size: int, optional
                数据包大小（字节），默认值为 500
            enable_reordering: bool, optional
                是否启用重排序，默认值为 True
            switch: str, optional
                开关配置，默认值为 "1,1,0,1,1,0"
            loss_average: float, optional
                平均丢包率，默认值为 0.0

        Returns:
            HoloWANTrace
                创建的 HoloWANTrace 对象

        示例:
            from traceloom.domain.pathlet import Observation
            observations = [Observation(...), Observation(...)]
            trace = HoloWANTrace.from_observations(
                observations,
                operator="China Mobile",
                description="4G trace"
            )
        """
        # 使用默认值工厂函数生成值
        if test_name is None:
            test_name = f"generated_{datetime.now().strftime('%y%m%d_%H%M%S')}"
        if start_time is None:
            start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        points = [HoloWANPoint.from_observation(obs) for obs in observations]
        return cls(
            operator=operator,
            network_type=network_type,
            signal_strength=signal_strength,
            test_name=test_name,
            destination=destination,
            start_time=start_time,
            end_time=end_time,
            timezone=timezone,
            description=description,
            interval_sec=interval_sec,
            packet_size=packet_size,
            enable_reordering=enable_reordering,
            switch=switch,
            loss_average=loss_average,
            points=points,
        )
