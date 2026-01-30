# -*- coding: utf-8 -*-
"""数据预处理器

将原始轨迹数据转换为径元库
"""

from pathlib import Path
from typing import List

from traceloom.core.config import settings
from traceloom.core.logger import logger
from traceloom.io import HoloWANTrace
from traceloom.storage.pathlet_storage import PathletStorage


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

    def build_pathlets(self):
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
        pathlet_storage = PathletStorage(self.pathlet_dir)
        pathlets = []
        for txt_file in txt_files:
            holowan_trace = HoloWANTrace.load(txt_file)
            pathlets.extend(list(holowan_trace.extended_sliding_windows()))

        pathlet_storage.save_pathlets(pathlets, update_points=True)
        return pathlets

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

        # 创建 PathletStorage 实例
        storage = PathletStorage(self.pathlet_dir)

        # 构建 raw_trace_segment_map
        raw_trace_segment_map = {}
        for pathlet in pathlets:
            try:
                trace_name = pathlet.trace_name
                start_index = pathlet.start_index

                # 从径元的 body 和 tail 中提取观测数据
                observations = []

                # 提取 body 中的观测数据
                if hasattr(pathlet.body, "observations") and pathlet.body.observations:
                    observations.extend(pathlet.body.observations)

                # 提取 tail 中的观测数据
                if hasattr(pathlet.tail, "observations") and pathlet.tail.observations:
                    observations.extend(pathlet.tail.observations)
            except (ValueError, IndexError):
                logger.warning(f"无法从径元 ID {pathlet.pathlet_id} 中提取轨迹信息")

        # 使用 PathletStorage 保存径元
        storage.save_pathlets(pathlets, update_points=True)
        logger.info("径元保存完成")

    def run(self) -> List:
        """运行预处理流程

        返回:
            List: 生成的径元列表
        """
        logger.info("=" * 60)
        logger.info("开始预处理流程")
        logger.info("=" * 60)

        # 3. 构建径元
        logger.info("构建径元...")
        pathlets = self.build_pathlets()
        logger.info(f"生成了 {len(pathlets)} 个径元")

        logger.info("=" * 60)
        return pathlets
