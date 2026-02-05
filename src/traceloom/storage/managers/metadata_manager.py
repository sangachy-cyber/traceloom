# -*- coding: utf-8 -*-
"""径元元数据管理模块"""

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from traceloom.core.config import settings
from traceloom.core.logger import logger
from traceloom.domain.pathlet import Pathlet
from traceloom.storage.schemas import PATHLET_METADATA_SCHEMA, PathletMetadataFields


class PathletMetadataManager:
    """径元元数据管理器

    负责径元元数据的读写操作，包括：
    - 元数据的保存和加载
    - 按条件筛选径元
    - 元数据统计信息
    """

    def __init__(self, metadata_file: Optional[Path] = None):
        """初始化径元元数据管理器

        Args:
            metadata_file: 元数据文件路径，默认使用settings中的配置
        """
        self.metadata_file = metadata_file or settings.PATHLETS_DIR / "pathlets.parquet"
        self.metadata_file.parent.mkdir(exist_ok=True, parents=True)

    def save_metadata(self, pathlets: List[Pathlet]) -> pd.DataFrame:
        """保存径元元数据

        Args:
            pathlets: 径元列表

        Returns:
            pd.DataFrame: 保存的元数据DataFrame

        Raises:
            ValueError: 如果pathlets列表为空
        """
        if not pathlets:
            raise ValueError("Pathlet数据列表为空，无法保存")

        # 提取元数据
        metadata = []
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

            # 从 state_label 中提取 state_id
            if pathlet.state_label:
                state_id = pathlet.state_label.state_id
            else:
                state_id = -1

            # 提取元数据
            metadata.append(
                {
                    PathletMetadataFields.PATHLET_ID: pathlet.pathlet_id,
                    PathletMetadataFields.IS_VALID: pathlet.is_valid,
                    PathletMetadataFields.STATE_ID: state_id,
                    PathletMetadataFields.TRACE_NAME: trace_name,
                    PathletMetadataFields.START_INDEX: pathlet.start_index,
                    PathletMetadataFields.DATASET: pathlet.dataset,
                }
            )

        # 创建元数据DataFrame
        metadata_df = pd.DataFrame(metadata)

        # 确保trace_name字段是字符串类型
        if PathletMetadataFields.TRACE_NAME in metadata_df.columns:
            metadata_df[PathletMetadataFields.TRACE_NAME] = metadata_df[PathletMetadataFields.TRACE_NAME].astype(str)

        # 如果文件已存在，读取现有数据并合并
        if self.metadata_file.exists():
            existing_metadata_df = self.load_metadata()
            # 合并数据，去重（基于pathlet_id）
            combined_metadata_df = pd.concat([existing_metadata_df, metadata_df], ignore_index=True)
            combined_metadata_df = combined_metadata_df.drop_duplicates(subset=[PathletMetadataFields.PATHLET_ID], keep="last")
        else:
            combined_metadata_df = metadata_df

        # 写入Parquet文件
        self._write_metadata(combined_metadata_df)

        return combined_metadata_df

    def load_metadata(
        self,
        state_id: Optional[int] = None,
        is_valid: Optional[bool] = None,
        dataset: Optional[str] = None
    ) -> pd.DataFrame:
        """加载径元元数据

        Args:
            state_id: 可选，按状态ID筛选
            is_valid: 可选，按有效性筛选
            dataset: 可选，按数据集划分筛选

        Returns:
            pd.DataFrame: 加载的元数据DataFrame
        """
        if not self.metadata_file.exists():
            logger.warning(f"径元元数据文件不存在: {self.metadata_file}")
            return pd.DataFrame()

        # 读取元数据
        metadata_table = pq.read_table(self.metadata_file)

        # 按条件筛选
        if state_id is not None:
            metadata_table = metadata_table.filter(pa.compute.equal(metadata_table["state_id"], state_id))
            if metadata_table.num_rows == 0:
                return pd.DataFrame()

        if is_valid is not None:
            metadata_table = metadata_table.filter(pa.compute.equal(metadata_table["is_valid"], is_valid))
            if metadata_table.num_rows == 0:
                return pd.DataFrame()

        if dataset is not None:
            metadata_table = metadata_table.filter(pa.compute.equal(metadata_table["dataset"], dataset))
            if metadata_table.num_rows == 0:
                return pd.DataFrame()

        return metadata_table.to_pandas()

    def _write_metadata(self, metadata: pd.DataFrame) -> None:
        """写入元数据到Parquet文件

        Args:
            metadata: 元数据DataFrame
        """
        # 确保trace_name字段是字符串类型
        if PathletMetadataFields.TRACE_NAME in metadata.columns:
            metadata[PathletMetadataFields.TRACE_NAME] = metadata[PathletMetadataFields.TRACE_NAME].astype(str)

        # 转换为Arrow表，使用指定的Schema
        table = pa.Table.from_pandas(metadata, schema=PATHLET_METADATA_SCHEMA, preserve_index=False)

        # 写入Parquet文件
        pq.write_table(table, self.metadata_file, compression="ZSTD")

    def get_pathlet_count(self) -> int:
        """获取径元数量

        Returns:
            int: 径元数量
        """
        if not self.metadata_file.exists():
            return 0

        metadata_df = self.load_metadata()
        return len(metadata_df)

    def get_state_distribution(self) -> Dict[int, int]:
        """获取状态分布

        Returns:
            Dict[int, int]: 状态ID到数量的映射
        """
        if not self.metadata_file.exists():
            return {}

        metadata_df = self.load_metadata()
        state_counts = metadata_df[PathletMetadataFields.STATE_ID].value_counts().to_dict()

        return state_counts

    def clear_metadata(self) -> None:
        """清空元数据
        """
        if self.metadata_file.exists():
            self.metadata_file.unlink()
            logger.debug(f"已删除元数据文件: {self.metadata_file}")
