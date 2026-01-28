# -*- coding: utf-8 -*-
"""数据预处理器

将原始轨迹数据转换为径元库
"""

from pathlib import Path
from typing import Dict, List

import pandas as pd

from traceloom.core.config import settings
from traceloom.core.logger import logger
from traceloom.domain.pathlet import Observation
from traceloom.domain.raw_trace import RawTraceSegment as RawProfile
from training.pathlet_clustering.pathlet_builder import PathletBuilder


class Preprocessor:
    """数据预处理器

    将原始轨迹数据转换为径元库
    """

    def __init__(self, raw_data_dir: Path = None, pathlet_dir: Path = None):
        """初始化数据预处理器

        参数:
            raw_data_dir: 原始数据目录，默认使用 settings.RAW_DIR
            pathlet_dir: 径元库目录，默认使用 settings.PATHLETS_DIR
        """
        self.raw_data_dir = raw_data_dir or settings.RAW_DIR
        self.pathlet_dir = pathlet_dir or settings.PATHLETS_DIR

    def load_raw_data(self) -> Dict[str, pd.DataFrame]:
        """加载原始数据

        返回:
            Dict[str, pd.DataFrame]: 轨迹名称到 DataFrame 的映射
        """
        raw_data = {}

        # 加载所有 .txt 文件
        txt_files = list(self.raw_data_dir.glob("*.txt"))
        if not txt_files:
            logger.warning(f"未找到原始轨迹文件: {self.raw_data_dir}")
            return raw_data

        logger.info(f"加载原始轨迹数据，共找到 {len(txt_files)} 个文件")
        
        for txt_file in txt_files:
            trace_name = txt_file.stem
            try:
                # 假设是空格分隔的文本文件
                df = pd.read_csv(txt_file, sep="\s+")
                raw_data[trace_name] = df
                logger.debug(f"加载文件成功: {txt_file}")
            except Exception as e:
                logger.error(f"加载文件 {txt_file} 失败: {e}")

        return raw_data

    def process_traces(self, raw_data: Dict[str, pd.DataFrame]) -> List[RawProfile]:
        """处理轨迹数据

        参数:
            raw_data: 轨迹名称到 DataFrame 的映射

        返回:
            List[RawProfile]: 原始网络剖面列表
        """
        profiles = []

        if not raw_data:
            logger.warning("没有原始数据需要处理")
            return profiles

        logger.info("处理轨迹数据生成原始网络剖面...")

        for trace_name, df in raw_data.items():
            # 处理每个轨迹，生成原始网络剖面
            # 假设采样率为 10Hz，每 110 个点生成一个剖面
            max_idx = len(df) - 110 + 1
            if max_idx <= 0:
                logger.warning(f"轨迹 {trace_name} 数据长度不足，跳过处理")
                continue

            for start_idx in range(0, max_idx, 100):
                try:
                    profile = RawProfile.from_dataframe(df, trace_name, start_idx)
                    if profile.is_valid:
                        profiles.append(profile)
                except Exception as e:
                    logger.error(f"处理轨迹 {trace_name} 失败: {e}")

        logger.info(f"成功生成 {len(profiles)} 个原始网络剖面")
        return profiles

    def build_pathlets(self, profiles: List[RawProfile]) -> List:
        """构建径元

        参数:
            profiles: 原始网络剖面列表

        返回:
            List: 径元列表
        """
        if not profiles:
            logger.warning("没有网络剖面需要处理")
            return []

        logger.info("构建径元...")
        builder = PathletBuilder(body_size=100, tail_size=10)

        for profile in profiles:
            try:
                # 提取观测数据
                observations = profile.observations
                # 简单起见，使用默认状态
                states = [0] * len(observations)
                # 添加序列
                builder.add_sequence(observations, states, profile.trace_name)
            except Exception as e:
                logger.error(f"处理网络剖面失败: {e}")

        logger.info(f"成功生成 {len(builder.pathlets)} 个径元")
        return builder.pathlets

    def save_pathlets(self, pathlets: List) -> None:
        """保存径元到文件

        参数:
            pathlets: 径元列表
        """
        if not pathlets:
            logger.warning("没有径元需要保存")
            return

        # 确保目录存在
        self.pathlet_dir.mkdir(parents=True, exist_ok=True)

        # 保存径元
        logger.info(f"保存径元到 {self.pathlet_dir}")
        builder = PathletBuilder(body_size=100, tail_size=10)
        builder.pathlets = pathlets
        builder.save_to_parquet(self.pathlet_dir)
        logger.info("径元保存完成")

    def run(self) -> List:
        """运行预处理流程

        返回:
            List: 生成的径元列表
        """
        logger.info("=" * 60)
        logger.info("开始预处理流程")
        logger.info("=" * 60)

        # 1. 加载原始数据
        logger.info(f"加载原始数据从 {self.raw_data_dir}")
        raw_data = self.load_raw_data()
        logger.info(f"加载了 {len(raw_data)} 个轨迹文件")

        # 2. 处理轨迹数据
        logger.info("处理轨迹数据...")
        profiles = self.process_traces(raw_data)
        logger.info(f"生成了 {len(profiles)} 个原始网络剖面")

        # 3. 构建径元
        logger.info("构建径元...")
        pathlets = self.build_pathlets(profiles)
        logger.info(f"生成了 {len(pathlets)} 个径元")

        # 4. 保存径元
        if pathlets:
            logger.info(f"保存径元到 {self.pathlet_dir}")
            self.save_pathlets(pathlets)
            logger.info("预处理流程完成！")
        else:
            logger.warning("未生成径元，预处理流程结束")

        logger.info("=" * 60)
        return pathlets
