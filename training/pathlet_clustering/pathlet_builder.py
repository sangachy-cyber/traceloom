# -*- coding: utf-8 -*-
"""径元构建器

将连续观测数据切片构建径元

示例:
    from training.pathlet_clustering.pathlet_builder import PathletBuilder
    from traceloom.domain.pathlet import Observation
    from pathlib import Path

    # 创建径元构建器
    builder = PathletBuilder(body_size=100, tail_size=10)

    # 创建观测序列
    observations = [
        Observation(delay_up=10, loss_up=0, bw_up=100, delay_down=10, loss_down=0, bw_down=100)
        for _ in range(220)
    ]

    # 创建状态序列
    states = [0] * 220  # 假设所有观测都属于状态0

    # 添加观测序列和状态序列
    builder.add_sequence(observations, "test_trace")
    print(f"添加了 {len(builder.pathlets)} 个径元")

    # 保存径元到Parquet文件
    output_dir = Path("./pathlets")
    builder.save_to_parquet(output_dir)

    # 保存径元到PathletStorage
    # 注意：需要先创建一个包含RawProfile的字典
    # profiles_dict = {...}
    # builder.save_to_storage(profiles_dict)
"""

from pathlib import Path
from typing import List

import pandas as pd

from traceloom.core.config import settings
from traceloom.core.logger import logger
from traceloom.domain.pathlet import BodyObservations, Observation, Pathlet, TailObservations
from traceloom.domain.state import StateLabel
from traceloom.storage.pathlet_storage import PathletStorage


class PathletBuilder:
    """径元构建器

    将连续观测数据切片构建径元
    """

    def __init__(self, body_size: int = 100, tail_size: int = 10):
        """初始化径元构建器

        Args:
            body_size: 主干大小（观元数量）
            tail_size: 融尾大小（观元数量）

        Examples:
            # 创建径元构建器
            builder = PathletBuilder(body_size=100, tail_size=10)
            print(f"径元构建器初始化完成，主干大小: {builder.body_size}, 融尾大小: {builder.tail_size}")
        """
        self.body_size = body_size
        self.tail_size = tail_size
        self.pathlets: List[Pathlet] = []
        self.current_id = 0

    def add_sequence(self, obs_seq, states, source_file: str):
        """添加观测序列和状态序列

        Args:
            obs_seq: 观测序列，可以是List[Observation]或pd.DataFrame
            states: 状态序列
            source_file: 源文件路径

        Raises:
            ValueError: 当obs_seq没有长度或形状属性时抛出

        Examples:
            # 添加观测序列
            builder = PathletBuilder()
            observations = [Observation(...)] * 220
            states = [0] * 220
            builder.add_sequence(observations, states, "test_trace")
            print(f"添加了 {len(builder.pathlets)} 个径元")
        """
        total_size = self.body_size + self.tail_size

        # 确定序列长度
        if isinstance(obs_seq, list) or (hasattr(obs_seq, "__len__") and not isinstance(obs_seq, dict)):
            seq_length = len(obs_seq)
        elif hasattr(obs_seq, "shape"):
            seq_length = obs_seq.shape[0]
        else:
            raise ValueError("obs_seq must have length or shape attribute")

        for i in range(0, seq_length - total_size + 1, 1):
            # 确定当前径元的状态ID
            state_id = -1
            if states and i < len(states):
                state_id = states[i]

            pathlet = Pathlet(
                pathlet_id=f"{source_file}_{i}",
                trace_name=source_file,
                start_index=i,
                body=self._extract_body(obs_seq, i),
                tail=self._extract_tail(obs_seq, i + self.body_size),
                state_label=StateLabel(state_id=state_id, confidence=1.0),
            )
            self.pathlets.append(pathlet)
            self.current_id += 1

    def _extract_body(self, obs_seq, start_index: int) -> BodyObservations:
        """提取主干观测数据

        Args:
            obs_seq: 观测序列
            start_index: 起始索引

        Returns:
            BodyObservations: 主干观测数据

        Examples:
            # 提取主干观测数据
            # 注意：此方法通常由 add_sequence 方法内部调用
            # body_obs = builder._extract_body(observations, 0)
            # print(f"提取了 {len(body_obs.observations)} 个主干观测数据")
        """
        observations = []
        for i in range(start_index, start_index + self.body_size):
            if isinstance(obs_seq, pd.DataFrame):
                # 从DataFrame中提取数据
                obs = Observation(
                    delay_up=obs_seq.iloc[i]["delay_up"],
                    loss_up=obs_seq.iloc[i]["loss_up"],
                    bw_up=obs_seq.iloc[i]["bw_up"],
                    delay_down=obs_seq.iloc[i]["delay_down"],
                    loss_down=obs_seq.iloc[i]["loss_down"],
                    bw_down=obs_seq.iloc[i]["bw_down"],
                )
            else:
                # 假设是List[Observation]
                obs = obs_seq[i]
            observations.append(obs)
        return BodyObservations(observations=observations)

    def _extract_tail(self, obs_seq, start_index: int) -> TailObservations:
        """提取融尾观测数据

        Args:
            obs_seq: 观测序列
            start_index: 起始索引

        Returns:
            TailObservations: 融尾观测数据

        Examples:
            # 提取融尾观测数据
            # 注意：此方法通常由 add_sequence 方法内部调用
            # tail_obs = builder._extract_tail(observations, 100)
            # print(f"提取了 {len(tail_obs.observations)} 个融尾观测数据")
        """
        observations = []
        for i in range(start_index, start_index + self.tail_size):
            if isinstance(obs_seq, pd.DataFrame):
                # 从DataFrame中提取数据
                obs = Observation(
                    delay_up=obs_seq.iloc[i]["delay_up"],
                    loss_up=obs_seq.iloc[i]["loss_up"],
                    bw_up=obs_seq.iloc[i]["bw_up"],
                    delay_down=obs_seq.iloc[i]["delay_down"],
                    loss_down=obs_seq.iloc[i]["loss_down"],
                    bw_down=obs_seq.iloc[i]["bw_down"],
                )
            else:
                # 假设是List[Observation]
                obs = obs_seq[i]
            observations.append(obs)
        return TailObservations(observations=observations)

    def save_to_parquet(self, output_dir: Path):
        """保存径元到Parquet文件

        Args:
            output_dir: 输出目录

        Examples:
            # 保存径元到Parquet文件
            builder = PathletBuilder()
            # 添加观测序列...
            output_dir = Path("./pathlets")
            builder.save_to_parquet(output_dir)
            print(f"保存了 {len(builder.pathlets)} 个径元")
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # 构建DataFrame
        data = {
            "pathlet_id": [p.pathlet_id for p in self.pathlets],
            "state_id": [p.state_label.state_id for p in self.pathlets],
            "source_file": [p.pathlet_id.split("_")[0] for p in self.pathlets],
            "start_index": [int(p.pathlet_id.split("_")[-1]) for p in self.pathlets],
        }

        df = pd.DataFrame(data)
        output_file = output_dir / "pathlets.parquet"
        df.to_parquet(output_file, index=False)
        logger.info(f"保存了 {len(self.pathlets)} 个径元到 {output_file}")

    def save_to_storage(self, profiles_dict: dict):
        """保存径元到PathletStorage

        Args:
            profiles_dict: RawProfile字典，键为pathlet_id

        Examples:
            # 保存径元到PathletStorage
            builder = PathletBuilder()
            # 添加观测序列...
            profiles_dict = {...}  # RawProfile字典
            builder.save_to_storage(profiles_dict)
            print("径元已保存到PathletStorage")
        """
        storage = PathletStorage(settings.PATHLETS_DIR)
        storage.save_pathlets(self.pathlets, profiles_dict)
        logger.info("径元已保存到PathletStorage")
