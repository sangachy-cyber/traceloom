# -*- coding: utf-8 -*-
"""【重织】阶段（reweaver）实现类。
用于拼接网络剖面序列，实现平滑过渡效果。
"""

from typing import List

from traceloom.core.logger import logger
from traceloom.domain.pathlet import Pathlet
from traceloom.domain.pattern import Pattern
from traceloom.io.adapters import HoloWANTrace
from traceloom.io.adapters._holowan import HoloWANDirection, HoloWANPoint
from traceloom.weaving.sampler.global_sampler import GlobalSampler


class Reweaver:
    """径元重织器。
    用于拼接径元序列，实现平滑过渡效果。

    示例:
        from traceloom.weaving.reweave.reweaver import Reweaver
        from traceloom.domain.pathlet import Pathlet, BodyObservations, TailObservations, Observation
        from datetime import datetime, timedelta

        # 准备两个径元序列
        seq1 = [
            Pathlet(
                pathlet_id=f"p1_{i}",
                trace_name=f"trace_1",
                start_index=i * 100,
                body=BodyObservations(
                    observations=[Observation(
                        delay_up=100.0, loss_up=0.01, bw_up=10.0,
                        delay_down=100.0, loss_down=0.01, bw_down=10.0
                    ) for _ in range(100)]
                ),
                tail=TailObservations(
                    observations=[Observation(
                        delay_up=100.0, loss_up=0.01, bw_up=10.0,
                        delay_down=100.0, loss_down=0.01, bw_down=10.0
                    ) for _ in range(10)]
                )
            )
            for i in range(10)
        ]

        seq2 = [
            Pathlet(
                pathlet_id=f"p2_{i}",
                trace_name=f"trace_2",
                start_index=i * 100,
                body=BodyObservations(
                    observations=[Observation(
                        delay_up=200.0, loss_up=0.05, bw_up=5.0,
                        delay_down=200.0, loss_down=0.05, bw_down=5.0
                    ) for _ in range(100)]
                ),
                tail=TailObservations(
                    observations=[Observation(
                        delay_up=200.0, loss_up=0.05, bw_up=5.0,
                        delay_down=200.0, loss_down=0.05, bw_down=5.0
                    ) for _ in range(10)]
                )
            )
            for i in range(10)
        ]

        # 初始化重织器
        reweaver = Reweaver()

        # 拼接序列
        reweaved_seq = reweaver.splice(seq1, seq2)

    属性:
        transition_duration: 过渡持续时间（秒）
        transition_steps: 过渡步数
    """

    def __init__(self, transition_duration: float = 1.0, transition_steps: int = 10):
        """初始化网络剖面重织器。

        参数:
            transition_duration: 过渡持续时间（秒）
            transition_steps: 过渡步数
        """
        self.transition_duration = transition_duration
        self.transition_steps = transition_steps

    def _validate_pathlet(self, pathlet: Pathlet) -> None:
        """验证径元参数

        参数:
            pathlet: 径元（Pathlet对象）

        异常:
            ValueError: 参数无效时抛出
        """
        # 简化验证，只检查基本结构
        if pathlet.body is None or pathlet.tail is None:
            raise ValueError("径元缺少必要数据")
        # 检查主体数据长度
        if len(pathlet.body.observations) != 100:
            raise ValueError(f"主体数据长度无效 {len(pathlet.body.observations)}")
        if len(pathlet.tail.observations) != 10:
            raise ValueError(f"融尾数据长度无效: {len(pathlet.tail.observations)}")

    def _splice_multiple_pathlets(self, all_pathlets: List[Pathlet]) -> List[Pathlet]:
        """拼接多个径元，直接使用 Body 拼接"""
        if len(all_pathlets) == 1:
            return all_pathlets

        # 直接返回原始径元列表，不生成过渡径元
        # 不限制径元数量，由用户指定的长度决定
        return all_pathlets

    def _generate_trace_from_single_pathlet(self, pathlet: Pathlet) -> List[List[float]]:
        """从单个径元生成轨迹数据"""
        trace_data = []
        # 获取主体观测数据
        body = pathlet.body

        for obs in body.observations:
            trace_data.append(
                [
                    obs.delay_up,
                    obs.loss_up,
                    obs.bw_up,
                    obs.delay_down,
                    obs.loss_down,
                    obs.bw_down,
                ]
            )
        return trace_data

    def _generate_trace_from_pathlets(self, pathlets: List[Pathlet]) -> List[List[float]]:
        """从多个径元生成轨迹数据"""
        trace_data = []
        for pathlet in pathlets:
            # 获取主体观测数据
            body = pathlet.body

            for obs in body.observations:
                trace_data.append(
                    [
                        obs.delay_up,
                        obs.loss_up,
                        obs.bw_up,
                        obs.delay_down,
                        obs.loss_down,
                        obs.bw_down,
                    ]
                )
        return trace_data

    def generate_trace(self, pathlet_sequence: List[Pathlet]) -> List[List[float]]:
        """生成合成轨迹

        根据径元序列生成6列HoloWAN格式的合成轨迹数据

        示例:
            from traceloom.weaving.reweave.reweaver import Reweaver
            from traceloom.io.pathlet_storage import PathletStorage

            pathlet_storage = PathletStorage()
            pathlet_sequence = [Pathlet(...), Pathlet(...)]
            reweaver = Reweaver()
            trace_data = reweaver.generate_trace(pathlet_sequence, pathlet_storage)

        参数:
            pathlet_sequence: 径元序列
            pathlet_storage: 径元存储实例

        返回:
            合成轨迹数据（6列）
        """
        if not pathlet_sequence:
            raise ValueError("输入的径元序列不能为空")

        logger.info(f"开始生成合成轨迹，共包含{len(pathlet_sequence)} 个径元")

        # 直接使用传入的 Pathlet 对象，不从存储中获取数据
        all_profiles = pathlet_sequence

        if not all_profiles:
            # 如果无法获取任何径元数据，直接退出
            logger.error("无法获取任何径元的详细数据，无法生成合成轨迹")
            raise ValueError("无法获取任何径元的详细数据，无法生成合成轨迹")

        # 使用现有的拼接功能生成合成轨迹
        if len(all_profiles) == 1:
            trace_data = self._generate_trace_from_single_pathlet(all_profiles[0])
        else:
            # 拼接多个径元
            spliced_pathlets = self._splice_multiple_pathlets(all_profiles)
            trace_data = self._generate_trace_from_pathlets(spliced_pathlets)

        # 不限制轨迹长度，由用户指定的径元数量决定
        # 直接返回生成的轨迹数据，不进行截断或填充

        logger.info(f"成功生成合成轨迹，共包含 {len(trace_data)} 个采样点")
        return trace_data

    def weave(self, pattern: Pattern, sampler: GlobalSampler):
        """执行重织操作

        根据织样生成观测数据

        参数:
            pattern: 织样对象
            sampler: 全局采样器实例，用于采样径元

        返回:
            观测数据列表
        """
        # 从织样序列生成观测数据
        logger.info(f"{pattern.sequence}")
        pathlet_sequence = sampler.sample_pathlets(pattern.sequence)
        trace_data = self.generate_trace(pathlet_sequence)
        logger.info(f"{len(trace_data)}")
        holowan_trace = HoloWANTrace()
        # 添加数据点
        points = []
        for data_point in trace_data:
            if len(data_point) >= 6:
                # 创建HoloWANDirection对象
                up = HoloWANDirection(delay=data_point[0], loss=data_point[1], bw=data_point[2])
                down = HoloWANDirection(delay=data_point[3], loss=data_point[4], bw=data_point[5])
                # 创建HoloWANPoint对象并添加到列表
                holo_point = HoloWANPoint(up=up, down=down)
                points.append(holo_point)

        # 设置轨迹点
        holowan_trace.points = points
        observations = holowan_trace.to_observations()
        logger.info(f"成功生成 {len(observations)} 个观测数据")
        return observations


__all__ = ["Reweaver"]
