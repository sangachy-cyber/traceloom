# -*- coding: utf-8 -*-
"""径元点数据管理模块"""

from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

from traceloom.core.config import settings
from traceloom.core.logger import logger
from traceloom.domain.pathlet import BodyObservations, Observation, Pathlet, TailObservations
from traceloom.storage.schemas import POINT_DATA_SCHEMA, PointDataFields


class PathletPointsManager:
    """径元点数据管理器

    负责径元点数据的读写操作，包括：
    - 点数据的保存和加载
    - 点数据的去重处理
    - 点数据的分区存储
    """

    def __init__(self, points_dir: Optional[Path] = None):
        """初始化径元点数据管理器

        Args:
            points_dir: 点数据目录路径，默认使用settings中的配置
        """
        self.points_dir = points_dir or settings.PATHLETS_DIR / "pathlets_points"
        self.points_dir.mkdir(exist_ok=True, parents=True)

    def save_points(self, pathlets: List[Pathlet]) -> pd.DataFrame:
        """保存径元点数据

        Args:
            pathlets: 径元列表

        Returns:
            pd.DataFrame: 保存的点数据DataFrame

        Raises:
            ValueError: 如果pathlets列表为空
        """
        if not pathlets:
            raise ValueError("Pathlet数据列表为空，无法保存")

        # 提取点数据（去重处理）
        unique_points = {}

        for pathlet in pathlets:
            # 确保 trace_name 是字符串类型
            trace_name = str(pathlet.trace_name)
            # 如果 trace_name 为空，尝试从 pathlet_id 中提取
            if not trace_name:
                if "_" in pathlet.pathlet_id:
                    parts = pathlet.pathlet_id.split("_")
                    for i in range(len(parts) - 1, -1, -1):
                        if parts[i].isdigit():
                            trace_name = "_".join(parts[:i])
                            break

            start_index = pathlet.start_index

            # 从 body 中提取观测数据
            for i, obs in enumerate(pathlet.body.observations):
                trace_index = start_index + i
                key = (trace_name, trace_index)

                if key not in unique_points:
                    # 新观测点
                    unique_points[key] = {
                        PointDataFields.TRACE_NAME: trace_name,
                        PointDataFields.TRACE_INDEX: trace_index,
                        PointDataFields.PATHLET_IDS: [pathlet.pathlet_id],
                        PointDataFields.DELAY_UP: obs.delay_up,
                        PointDataFields.LOSS_UP: obs.loss_up,
                        PointDataFields.BW_UP: obs.bw_up,
                        PointDataFields.DELAY_DOWN: obs.delay_down,
                        PointDataFields.LOSS_DOWN: obs.loss_down,
                        PointDataFields.BW_DOWN: obs.bw_down,
                    }
                else:
                    # 已有观测点，添加径元ID
                    if pathlet.pathlet_id not in unique_points[key][PointDataFields.PATHLET_IDS]:
                        unique_points[key][PointDataFields.PATHLET_IDS].append(pathlet.pathlet_id)

            # 从 tail 中提取观测数据
            for i, obs in enumerate(pathlet.tail.observations):
                trace_index = start_index + len(pathlet.body.observations) + i
                key = (trace_name, trace_index)

                if key not in unique_points:
                    # 新观测点
                    unique_points[key] = {
                        PointDataFields.TRACE_NAME: trace_name,
                        PointDataFields.TRACE_INDEX: trace_index,
                        PointDataFields.PATHLET_IDS: [pathlet.pathlet_id],
                        PointDataFields.DELAY_UP: obs.delay_up,
                        PointDataFields.LOSS_UP: obs.loss_up,
                        PointDataFields.BW_UP: obs.bw_up,
                        PointDataFields.DELAY_DOWN: obs.delay_down,
                        PointDataFields.LOSS_DOWN: obs.loss_down,
                        PointDataFields.BW_DOWN: obs.bw_down,
                    }
                else:
                    # 已有观测点，添加径元ID
                    if pathlet.pathlet_id not in unique_points[key][PointDataFields.PATHLET_IDS]:
                        unique_points[key][PointDataFields.PATHLET_IDS].append(pathlet.pathlet_id)

        # 创建点数据DataFrame
        points_df = pd.DataFrame(list(unique_points.values()))

        # 确保trace_name字段是字符串类型
        if PointDataFields.TRACE_NAME in points_df.columns:
            points_df[PointDataFields.TRACE_NAME] = points_df[PointDataFields.TRACE_NAME].astype(str)

        # 确保trace_index列存在并排序
        if PointDataFields.TRACE_INDEX in points_df.columns:
            points_df = points_df.sort_values([PointDataFields.TRACE_NAME, PointDataFields.TRACE_INDEX])

        # 写入点数据
        self._write_points(points_df)

        return points_df

    def load_points(self, trace_names: Optional[List[str]] = None) -> pd.DataFrame:
        """加载径元点数据

        Args:
            trace_names: 可选，指定要加载的轨迹名称列表

        Returns:
            pd.DataFrame: 加载的点数据DataFrame
        """
        try:
            # 直接使用目录结构创建dataset，让pyarrow自动识别分区
            dataset = ds.dataset(str(self.points_dir), format="parquet")

            # 读取所有数据到表
            table = dataset.to_table()

            # 转换为DataFrame
            df = table.to_pandas()

            # 确保pathlet_ids字段是列表类型
            if PointDataFields.PATHLET_IDS in df.columns:
                # 处理可能的类型问题
                def ensure_list(obj):
                    if isinstance(obj, list):
                        return obj
                    elif isinstance(obj, np.ndarray):
                        # 转换 numpy 数组为列表
                        return obj.tolist()
                    elif isinstance(obj, str):
                        return [obj]
                    else:
                        return []

                df[PointDataFields.PATHLET_IDS] = df[PointDataFields.PATHLET_IDS].apply(ensure_list)

            logger.info(f"成功读取点数据，共 {len(df)} 行")
            return df
        except Exception as e:
            logger.warning(f"读取点数据时出错: {e}")
            import traceback

            logger.warning(f"错误堆栈: {traceback.format_exc()}")
            return pd.DataFrame()

    def load_pathlet_points(self, pathlet_id: str) -> Optional[pd.DataFrame]:
        """加载指定径元的点数据

        Args:
            pathlet_id: 径元唯一标识符

        Returns:
            Optional[pd.DataFrame]: 点数据DataFrame，如果径元不存在则返回None
        """
        points_df = self.load_points()

        # 检查是否存在点数据
        if points_df.empty:
            logger.warning("点数据文件为空")
            return None

        # 检查数组字段是否包含指定的pathlet_id
        if PointDataFields.PATHLET_IDS in points_df.columns:
            pathlet_points = points_df[points_df[PointDataFields.PATHLET_IDS].apply(lambda x: pathlet_id in x)]
        else:
            logger.warning(f"点数据中不存在 {PointDataFields.PATHLET_IDS} 字段")
            return None

        if pathlet_points.empty:
            logger.warning(f"没有找到径元 {pathlet_id} 的点数据")
            return None

        # 按trace_index排序
        if PointDataFields.TRACE_INDEX in pathlet_points.columns:
            pathlet_points = pathlet_points.sort_values(PointDataFields.TRACE_INDEX)

        return pathlet_points

    def _write_points(self, points: pd.DataFrame) -> None:
        """写入点数据到Parquet文件

        Args:
            points: 点数据DataFrame

        Raises:
            ValueError: 如果points DataFrame为空
        """
        if points.empty:
            raise ValueError("点数据DataFrame为空，无法写入")

        # 确保trace_name字段是字符串类型
        if PointDataFields.TRACE_NAME in points.columns:
            points[PointDataFields.TRACE_NAME] = points[PointDataFields.TRACE_NAME].astype(str)

        # 确保trace_index列存在并排序
        if PointDataFields.TRACE_INDEX in points.columns:
            points = points.sort_values([PointDataFields.TRACE_NAME, PointDataFields.TRACE_INDEX])

        # 确保目录存在
        self.points_dir.mkdir(exist_ok=True, parents=True)

        # 转换为Arrow表，使用指定的Schema
        table = pa.Table.from_pandas(points, schema=POINT_DATA_SCHEMA, preserve_index=False)

        # 使用write_to_dataset写入分区数据
        pq.write_to_dataset(
            table,
            root_path=str(self.points_dir),
            partition_cols=[PointDataFields.TRACE_NAME],
            existing_data_behavior="overwrite_or_ignore",
            compression="ZSTD",
            basename_template="data.{i}.parquet",
        )

        logger.info(f"点数据已写入到 {self.points_dir}，使用按trace_name分区存储")

    def reconstruct_profile(
        self, pathlet_points: pd.DataFrame, start_index: Optional[int] = None
    ) -> tuple[BodyObservations, TailObservations]:
        """根据点数据重建原始数据结构

        Args:
            pathlet_points: 点数据DataFrame
            start_index: 径元在原始轨迹中的起始索引，如果提供则使用相对索引

        Returns:
            tuple[BodyObservations, TailObservations]: 主体观测数据和融尾观测数据
        """
        # 按trace_index排序
        pathlet_points = pathlet_points.sort_values(PointDataFields.TRACE_INDEX)

        # 分离上下文点和延续点
        if start_index is not None:
            # 使用相对索引：trace_index - start_index
            ctx_points = pathlet_points[
                pathlet_points[PointDataFields.TRACE_INDEX].apply(lambda x: (x - start_index) < 100)
            ]
            cont_points = pathlet_points[
                pathlet_points[PointDataFields.TRACE_INDEX].apply(lambda x: 100 <= (x - start_index) < 110)
            ]
        else:
            # 如果没有提供start_index，按前100个作为上下文点，后10个作为延续点
            ctx_points = pathlet_points.head(100)
            cont_points = pathlet_points.tail(10)

        # 构建主体观测数据
        body_observations = []
        for _, row in ctx_points.iterrows():
            obs = Observation(
                delay_up=row[PointDataFields.DELAY_UP],
                loss_up=row[PointDataFields.LOSS_UP],
                bw_up=row[PointDataFields.BW_UP],
                delay_down=row[PointDataFields.DELAY_DOWN],
                loss_down=row[PointDataFields.LOSS_DOWN],
                bw_down=row[PointDataFields.BW_DOWN],
            )
            body_observations.append(obs)
        body = BodyObservations(observations=body_observations)

        # 构建融尾观测数据
        tail_observations = []
        for _, row in cont_points.iterrows():
            obs = Observation(
                delay_up=row[PointDataFields.DELAY_UP],
                loss_up=row[PointDataFields.LOSS_UP],
                bw_up=row[PointDataFields.BW_UP],
                delay_down=row[PointDataFields.DELAY_DOWN],
                loss_down=row[PointDataFields.LOSS_DOWN],
                bw_down=row[PointDataFields.BW_DOWN],
            )
            tail_observations.append(obs)
        tail = TailObservations(observations=tail_observations)

        return body, tail

    def clear_points(self) -> None:
        """清空点数据"""
        if self.points_dir.exists():
            import shutil

            shutil.rmtree(self.points_dir)
            logger.debug(f"已删除点数据目录: {self.points_dir}")
            # 重新创建目录
            self.points_dir.mkdir(exist_ok=True, parents=True)
