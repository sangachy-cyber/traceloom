# -*- coding: utf-8 -*-
"""织径总控（WeavingEngine）

统一调度Reweaver/Stitcher/Dreamer，完成主流程，提供三种织径模式：重织、绣织和广织。

示例:
    from traceloom.weaving.engine import WeavingEngine

    # 初始化织径总控
    weaving_engine = WeavingEngine()

    # 重织模式
    result = weaving_engine.weave("s0x2 -> s2x3", mode="reweave")

    # 绣织模式
    result = weaving_engine.weave("s0x2 -> s2x3", mode="stitch")

    # 广织模式
    result = weaving_engine.weave("s0x2 -> s2x3", mode="dream")

    # 保存结果
    weaving_engine.save_result(result, "output.trace")
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from traceloom.core.exceptions import StateMappingError, ValidationError
from traceloom.core.logger import logger
from traceloom.domain.pattern import Pattern, PatternParser
from traceloom.io.adapters._holowan import HoloWANDirection, HoloWANPoint, HoloWANTrace
from traceloom.storage.pathlet_storage import PathletStorage
from traceloom.weaving.engines.dreamer import Dreamer
from traceloom.weaving.engines.reweaver import Reweaver
from traceloom.weaving.engines.stitcher import Stitcher
from traceloom.weaving.sampler.global_sampler import GlobalSampler
from traceloom.weaving.weaving_law import WeavingLawEngine


class WeavingEngine:
    """织径总控，统一调度Reweaver/Stitcher/Dreamer，完成主流程

    织径总控是整个织径系统的核心，负责统一调度不同的织径引擎，根据用户输入的织样或文件，
    生成符合要求的网络轨迹。支持三种织径模式：重织、绣织和广织。

    Attributes:
        pathlet_storage: 径元存储实例，用于管理和访问径元数据
        weaving_law: 织律引擎实例，用于管理状态映射和织律规则
        global_sampler: 全局采样器实例，用于从径元库中采样径元
        reweaver: 重织引擎实例，用于基于现有轨迹生成新轨迹
        stitcher: 绣织引擎实例，用于根据状态序列生成轨迹
        dreamer: 广织引擎实例，用于生成全新的轨迹
        pattern_parser: 织样解析器实例，用于解析织样字符串

    Examples:
        # 初始化织径总控
        weaving_engine = WeavingEngine()

        # 重织模式：基于现有轨迹生成新轨迹
        result = weaving_engine.weave("path/to/trace.trace", mode="reweave")

        # 绣织模式：根据状态序列生成轨迹
        result = weaving_engine.weave("s0x2 -> s2x3", mode="stitch")

        # 广织模式：生成全新的轨迹
        result = weaving_engine.weave("s0x2 -> s2x3", mode="dream")
    """

    def __init__(self, pathlet_dir: Optional[Path] = None):
        """初始化织径总控

        初始化织径总控的各个组件，包括径元存储、织律引擎、全局采样器和各种织径引擎。

        Args:
            pathlet_dir: 径元存储目录，默认使用settings.PATHLET_DIR

        Examples:
            # 使用默认径元存储目录
            weaving_engine = WeavingEngine()

            # 使用自定义径元存储目录
            from pathlib import Path
            weaving_engine = WeavingEngine(pathlet_dir=Path("/custom/pathlet/dir"))
        """
        self.pathlet_storage = PathletStorage(pathlet_dir)
        """径元存储实例"""
        self.weaving_law = WeavingLawEngine()
        """织律引擎实例"""
        self.global_sampler = GlobalSampler(self.pathlet_storage)
        """全局采样器实例"""
        self.reweaver = Reweaver()
        """重织引擎实例"""
        self.stitcher = Stitcher()
        """绣织引擎实例"""
        self.dreamer = Dreamer()
        """广织引擎实例"""
        self.pattern_parser = PatternParser()
        """织样解析器实例"""

    def weave(
        self, input_data: Union[str, List[Dict[str, Any]], Pattern, Path], mode: str = "reweave"
    ) -> Dict[str, Any]:
        """织径入口函数，根据模式调度不同的织径引擎

        织径入口函数，根据指定的模式调度不同的织径引擎，处理输入数据并生成织径结果。

        Args:
            input_data: 输入数据，可以是文件路径、织样字符串、JSON列表或Pattern对象
            mode: 织径模式，支持"reweave"（重织）、"stitch"（绣织）、"dream"（广织）

        Returns:
            Dict[str, Any]: 织径结果，包含path_id、duration_sec、state_sequence和trace_data

        Raises:
            ValidationError: 输入格式无效或模式无效
            FileNotFoundError: 指定的文件不存在
            StateMappingError: 状态名无法映射为ID
            PathletSamplingError: 无法采样到足够径元
            SplicingError: 径元拼接失败

        Examples:
            # 重织模式：基于现有轨迹生成新轨迹
            result = weaving_engine.weave("path/to/trace.trace", mode="reweave")

            # 绣织模式：根据状态序列生成轨迹
            result = weaving_engine.weave("s0x2 -> s2x3", mode="stitch")

            # 广织模式：生成全新的轨迹
            result = weaving_engine.weave("s0x2 -> s2x3", mode="dream")
        """
        # 验证模式
        if mode not in ["reweave", "stitch", "dream"]:
            raise ValidationError(f"无效的织径模式：{mode}，支持的模式有：reweave, stitch, dream")

        # 验证输入类型
        valid_types = (str, list, Pattern, Path)
        if not isinstance(input_data, valid_types):
            raise ValidationError(
                f"无效的输入类型：{type(input_data).__name__}，支持的类型有：str, list, Pattern, Path"
            )

        # 根据模式不同，对输入数据进行不同处理
        if mode == "reweave":
            # 重织模式：直接处理输入内容，不解析为Pattern
            state_list = []
            holowan_trace = HoloWANTrace.load(input_data)
            pathlets, stats = holowan_trace.get_filtered_extended_windows_with_stats(step=100)
            for pathlet in pathlets:
                state_list.append(self.weaving_law.predict_state(pathlet))

            pattern = self.pattern_parser.parse(state_list)
            result = self._reweave(pattern, [])
        else:
            # 绣织和广织模式：解析输入为Pattern
            # 1. 解析输入，转换为Pattern
            pattern = self.pattern_parser.parse(input_data)

            # 2. 将状态名映射为状态ID
            state_duration_sequence = []
            for state_name, duration in pattern.sequence:
                try:
                    state_id = self.weaving_law.state_name_to_id(state_name)
                    state_duration_sequence.append((state_id, duration))
                except ValueError as e:
                    raise StateMappingError(f"状态名映射失败：{e}") from e

            # 3. 调度对应引擎
            if mode == "stitch":
                result = self._stitch(pattern, state_duration_sequence)
            elif mode == "dream":
                result = self._dream(pattern, state_duration_sequence)

        return result

    def _reweave(self, pattern: Pattern, state_duration_sequence: List[tuple]) -> Dict[str, Any]:
        """重织模式实现

        重织模式：基于现有轨迹文件或内容，通过径元拼接生成新的轨迹。

        Args:
            input_data: 输入数据，可以是HoloWAN文件路径或文件内容

        Returns:
            Dict[str, Any]: 重织结果，包含path_id、duration_sec、state_sequence和trace_data

        Examples:
            # 从文件路径重织
            result = weaving_engine._reweave("path/to/trace.trace")

            # 从文件内容重织
            with open("path/to/trace.trace", 'r') as f:
                content = f.read()
            result = weaving_engine._reweave(content)
        """
        logger.info("开始重织操作")
        pathlet_sequence = self.global_sampler.sample_pathlets(pattern.sequence)

        # 2. 生成合成轨迹
        trace_data = self.reweaver.generate_trace(pathlet_sequence, self.pathlet_storage)

        # 3. 构建结果
        # 计算总持续时间，根据pattern中的序列
        duration_sec = sum(duration for _, duration in pattern.sequence)
        result = {
            "path_id": f"tl_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "duration_sec": duration_sec,
            "state_sequence": "reweave_from_holowan",
            "trace_data": trace_data,
        }

        return result

    def _stitch(self, pattern: Pattern, state_duration_sequence: List[tuple]) -> Dict[str, Any]:
        """绣织模式实现

        绣织模式：根据指定的状态序列，从径元库中选择合适的径元并拼接成轨迹。

        Args:
            pattern: 织样对象
            state_duration_sequence: 状态ID和持续时间的序列

        Returns:
            Dict[str, Any]: 绣织结果，包含path_id、duration_sec、state_sequence和trace_data

        Examples:
            # 内部方法，通常通过weave方法调用
            # result = weaving_engine._stitch(pattern, state_duration_sequence)
        """
        logger.info(f"开始绣织操作，状态序列：{pattern.sequence}")

        # 提取状态序列
        state_sequence = [state_id for state_id, _ in state_duration_sequence]

        # 1. 执行绣织
        profiles = self.stitcher.stitch(
            state_sequence=state_sequence, duration=sum(duration for _, duration in state_duration_sequence)
        )

        # 2. 生成输出结果
        trace_data = self._pathlets_to_trace_data(profiles)

        return self._build_result(pattern, trace_data)

    def _dream(self, pattern: Pattern, state_duration_sequence: List[tuple]) -> Dict[str, Any]:
        """广织模式实现

        广织模式：根据指定的状态序列，生成全新的轨迹数据，不依赖于现有的径元库。

        Args:
            pattern: 织样对象
            state_duration_sequence: 状态ID和持续时间的序列

        Returns:
            Dict[str, Any]: 广织结果，包含path_id、duration_sec、state_sequence和trace_data

        Examples:
            # 内部方法，通常通过weave方法调用
            # result = weaving_engine._dream(pattern, state_duration_sequence)
        """
        logger.info(f"开始广织操作，状态序列：{pattern.sequence}")

        # 提取状态序列和总持续时间
        state_sequence = [state_id for state_id, _ in state_duration_sequence]
        duration = sum(duration for _, duration in state_duration_sequence)

        # 1. 执行广织
        profiles = self.dreamer.dream(state_sequence=state_sequence, duration=duration)

        # 2. 生成输出结果
        trace_data = self._pathlets_to_trace_data(profiles)

        return self._build_result(pattern, trace_data)

    @staticmethod
    def _build_result(pattern: Pattern, trace_data: List[List[float]]) -> Dict[str, Any]:
        """构建织径结果

        根据织样和生成的轨迹数据，构建完整的织径结果字典。

        Args:
            pattern: 织样对象
            trace_data: 轨迹数据，格式为[[delay_up, loss_up, bw_up, delay_down, loss_down, bw_down], ...]

        Returns:
            Dict[str, Any]: 织径结果，包含path_id、duration_sec、state_sequence和trace_data

        Examples:
            # 内部方法，通常通过_stitch或_dream方法调用
            # result = weaving_engine._build_result(pattern, trace_data)
        """
        # 生成path_id
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path_id = f"tl_{timestamp}"

        # 计算总持续时间
        duration_sec = sum(duration for _, duration in pattern.sequence)

        # 构建结果
        result = {
            "path_id": path_id,
            "duration_sec": duration_sec,
            "state_sequence": pattern.to_string(),
            "trace_data": trace_data,
        }

        return result

    @staticmethod
    def _pathlets_to_trace_data(pathlets) -> List[List[float]]:
        """将径元转换为轨迹数据格式

        将不同类型的径元（如Pathlet对象或其他包含body和tail的对象）转换为统一的轨迹数据格式。

        Args:
            pathlets: 径元列表

        Returns:
            List[List[float]]: 轨迹数据，格式为[[delay_up, loss_up, bw_up, delay_down, loss_down, bw_down], ...]

        Examples:
            # 内部方法，通常通过_stitch或_dream方法调用
            # trace_data = weaving_engine._pathlets_to_trace_data(pathlets)
        """
        trace_data = []
        for pathlet in pathlets:
            # 检查pathlet对象的属性，处理不同的属性结构
            if hasattr(pathlet, "body") and hasattr(pathlet, "tail"):
                # 提取主体观测数据
                for obs in pathlet.body.observations:
                    trace_data.append(
                        [obs.delay_up, obs.loss_up, obs.bw_up, obs.delay_down, obs.loss_down, obs.bw_down]
                    )

                # 提取融尾观测数据
                for obs in pathlet.tail.observations:
                    trace_data.append(
                        [obs.delay_up, obs.loss_up, obs.bw_up, obs.delay_down, obs.loss_down, obs.bw_down]
                    )
            elif hasattr(pathlet, "observations"):
                # 处理包含observations属性的对象
                for obs in pathlet.observations:
                    trace_data.append(
                        [obs.delay_up, obs.loss_up, obs.bw_up, obs.delay_down, obs.loss_down, obs.bw_down]
                    )

        return trace_data

    @staticmethod
    def save_result(result: Dict[str, Any], output_file: Union[str, Path]) -> None:
        """保存织径结果到文件

        将织径结果保存为HoloWAN格式的轨迹文件，可直接用于HoloWAN模拟器。

        Args:
            result: 织径结果，由weave方法返回
            output_file: 输出文件路径

        Examples:
            # 保存织径结果
            result = weaving_engine.weave("s0x2 -> s2x3", mode="stitch")
            weaving_engine.save_result(result, "output.trace")
        """

        # 创建HoloWANTrace对象并保存
        holowan_trace = HoloWANTrace()

        # 添加数据点
        points = []
        for data_point in result["trace_data"]:
            if len(data_point) >= 6:
                # 创建HoloWANDirection对象
                up = HoloWANDirection(delay=data_point[0], loss=data_point[1], bw=data_point[2])
                down = HoloWANDirection(delay=data_point[3], loss=data_point[4], bw=data_point[5])
                # 创建HoloWANPoint对象并添加到列表
                holo_point = HoloWANPoint(up=up, down=down)
                points.append(holo_point)

        # 设置轨迹点
        holowan_trace.points = points

        # 写入文件
        holowan_trace.dump(output_file)

        logger.info(f"织径结果已保存到：{output_file}")
