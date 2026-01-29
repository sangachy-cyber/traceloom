# -*- coding: utf-8 -*-
"""数据加载器

合并多个 NetworkProfileExtractor 的功能，实现统一的数据加载和处理。

示例:
    from training.pathlet_clustering.data_loader import DataLoader
    from pathlib import Path
    import pandas as pd

    # 创建数据加载器
    loader = DataLoader()

    # 从CSV文件加载网络剖面
    csv_path = Path("./train.csv")
    profiles = loader.load_from_csv(csv_path)
    print(f"从CSV文件加载了 {len(profiles)} 个网络剖面")

    # 将网络剖面保存为CSV文件
    output_path = Path("./output.csv")
    success = loader.profiles_to_csv(profiles, output_path)
    print(f"保存网络剖面: {'成功' if success else '失败'}")

    # 从目录中加载所有网络剖面
    directory = Path("./profiles")
    profiles_dict = loader.load_profiles_from_directory(directory)
    print(f"从目录中加载了 {len(profiles_dict)} 个轨迹的网络剖面")

    # 从DataFrame中提取网络剖面
    # 注意：需要先创建一个包含网络数据的DataFrame
    # df = pd.DataFrame(...)
    # profiles_from_df = loader.load_from_dataframe(df, "test_trace")
    # print(f"从DataFrame中提取了 {len(profiles_from_df)} 个网络剖面")
"""

from pathlib import Path
from typing import Dict, List

import pandas as pd

from traceloom.core.logger import logger
from traceloom.domain.pathlet import Observation
from traceloom.domain.raw_trace import RawTraceSegment as RawProfile


class DataLoader:
    """数据加载器

    从文件或DataFrame中加载和处理网络数据，支持提取网络剖面（RawProfile）。
    """

    def load_from_csv(self, csv_path: Path) -> List[RawProfile]:
        """从CSV文件加载网络剖面

        Args:
            csv_path: CSV文件路径

        Returns:
            List[RawProfile]: 网络剖面列表

        Examples:
            # 从CSV文件加载网络剖面
            loader = DataLoader()
            csv_path = Path("./train.csv")
            profiles = loader.load_from_csv(csv_path)
            print(f"从CSV文件加载了 {len(profiles)} 个网络剖面")
        """
        df = pd.read_csv(csv_path)
        profiles = []

        # 按trace_name和start_index分组
        grouped = df.groupby(["trace_name", "start_index"])

        for (trace_name, start_index), group in grouped:
            # 提取观测数据
            observations = []
            for _, row in group.iterrows():
                obs = Observation(
                    delay_up=row["delay_up"],
                    loss_up=row["loss_up"],
                    bw_up=row["bw_up"],
                    delay_down=row["delay_down"],
                    loss_down=row["loss_down"],
                    bw_down=row["bw_down"],
                )
                observations.append(obs)

            # 创建RawProfile对象
            profile = RawProfile(
                trace_name=trace_name, start_index=start_index, observations=observations, is_valid=True
            )
            profiles.append(profile)

        logger.info(f"从 {csv_path} 加载了 {len(profiles)} 个网络剖面")
        return profiles

    def load_from_dataframe(self, df: pd.DataFrame, trace_name: str, length: int = 110) -> List[RawProfile]:
        """从DataFrame中提取网络剖面

        Args:
            df: 轨迹数据DataFrame
            trace_name: 轨迹名称
            length: 剖面长度

        Returns:
            List[RawProfile]: 网络剖面列表

        Examples:
            # 从DataFrame中提取网络剖面
            import pandas as pd

            # 创建示例DataFrame
            data = {
                'delay_up': [10] * 220,
                'loss_up': [0] * 220,
                'bw_up': [100] * 220,
                'delay_down': [10] * 220,
                'loss_down': [0] * 220,
                'bw_down': [100] * 220
            }
            df = pd.DataFrame(data)

            loader = DataLoader()
            profiles = loader.load_from_dataframe(df, "test_trace", length=110)
            print(f"从DataFrame中提取了 {len(profiles)} 个网络剖面")
        """
        profiles = []
        total_length = len(df)

        for i in range(0, total_length - length + 1, length):
            profile = RawProfile.from_dataframe(df, trace_name, i, length)
            profiles.append(profile)

        logger.info(f"从DataFrame中提取了 {len(profiles)} 个网络剖面")
        return profiles

    def profiles_to_csv(self, profiles: List[RawProfile], output_path: Path) -> bool:
        """将网络剖面转换为CSV

        Args:
            profiles: 网络剖面列表
            output_path: 输出文件路径

        Returns:
            bool: 是否成功保存

        Examples:
            # 将网络剖面保存为CSV文件
            loader = DataLoader()
            profiles = [...]  # 网络剖面列表
            output_path = Path("./output.csv")
            success = loader.profiles_to_csv(profiles, output_path)
            print(f"保存网络剖面: {'成功' if success else '失败'}")
        """
        data = []

        for profile in profiles:
            for i, obs in enumerate(profile.observations):
                row = {
                    "trace_name": profile.trace_name,
                    "start_index": profile.start_index,
                    "sample_index": i,
                    "delay_up": obs.delay_up,
                    "loss_up": obs.loss_up,
                    "bw_up": obs.bw_up,
                    "delay_down": obs.delay_down,
                    "loss_down": obs.loss_down,
                    "bw_down": obs.bw_down,
                }
                data.append(row)

        df = pd.DataFrame(data)
        df.to_csv(output_path, index=False)
        logger.info(f"网络剖面已保存到: {output_path}")
        return True

    def load_profiles_from_directory(self, directory: Path) -> Dict[str, List[RawProfile]]:
        """从目录中加载所有网络剖面

        Args:
            directory: 包含CSV文件的目录

        Returns:
            Dict[str, List[RawProfile]]: 轨迹名称到网络剖面列表的映射

        Examples:
            # 从目录中加载所有网络剖面
            loader = DataLoader()
            directory = Path("./profiles")
            profiles_dict = loader.load_profiles_from_directory(directory)
            print(f"从目录中加载了 {len(profiles_dict)} 个轨迹的网络剖面")

            # 遍历加载的轨迹
            for trace_name, trace_profiles in profiles_dict.items():
                print(f"轨迹 {trace_name}: {len(trace_profiles)} 个网络剖面")
        """
        profiles_dict = {}

        # 遍历目录中的CSV文件
        for profile_file in directory.glob("*.csv"):
            logger.info(f"加载网络剖面: {profile_file}")
            trace_name = profile_file.stem
            profiles = self.load_from_csv(profile_file)
            profiles_dict[trace_name] = profiles

        logger.info(f"从目录中加载了 {len(profiles_dict)} 个轨迹的网络剖面")
        return profiles_dict
