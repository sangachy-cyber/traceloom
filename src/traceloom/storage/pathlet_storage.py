# -*- coding: utf-8 -*-
"""Atom数据存储模块。

用于读写Atom数据，支持Parquet格式存储。
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from traceloom.core.config import settings
from traceloom.core.logger import logger
from traceloom.domain.pathlet import BodyObservations, Pathlet, TailObservations


@dataclass
class ContextData:
    """上下文数据"""
    delay_up: List[float]
    loss_up: List[float]
    bw_up: List[float]
    delay_down: List[float]
    loss_down: List[float]
    bw_down: List[float]


@dataclass
class ContinuationData:
    """延续数据"""
    delay_up: List[float]
    loss_up: List[float]
    bw_up: List[float]
    delay_down: List[float]
    loss_down: List[float]
    bw_down: List[float]


@dataclass
class PathletStatistics:
    """径元统计信息"""
    delay_up_mean: float
    delay_up_std: float
    delay_down_mean: float
    delay_down_std: float
    loss_up_mean: float
    loss_up_max: float
    loss_down_mean: float
    loss_down_max: float
    bw_up_mean: float
    bw_up_max: float
    bw_down_mean: float
    bw_down_max: float


class PathletStorage:
    """Pathlet（【径元】）数据存储管理器。

    负责Pathlet数据的读写操作，支持将Pathlet数据分离为元信息和点数据
    使用Parquet格式存储，支持按状态ID查询。

    示例:
        from traceloom.io.pathlet_storage import PathletStorage
        from traceloom.core.config import settings

        # 初始化PathletStorage
        pathlet_storage = PathletStorage(settings.ATOM_DIR)

        # 保存Pathlet数据
        pathlet_storage.save_pathlets(atoms)

        # 加载所有Pathlet数据
        atoms = pathlet_storage.load_pathlets()

        # 按状态ID加载Pathlet数据
        stable_atoms = pathlet_storage.load_pathlets(state_id=0)

    属性:
        atom_dir: Pathlet数据存储目录
        metadata_file: 元信息文件路径
        points_file: 点数据文件路径
    """

    def __init__(self, pathlet_dir: Optional[Path] = None):
        """初始化PathletStorage。

        参数:
            atom_dir: Pathlet数据存储目录，默认使用settings.ATOM_DIR
        """
        self.pathlet_dir = pathlet_dir or settings.PATHLETS_DIR
        self.pathlet_dir.mkdir(exist_ok=True, parents=True)

        self.metadata_file = self.pathlet_dir / "pathlets_meta.parquet"
        self.points_file = self.pathlet_dir / "pathlets_points.parquet"
        self.gmm_model_file = self.pathlet_dir / "gmm_model.joblib"
        self.state_mapping_file = self.pathlet_dir / "state_mapping.json"

        # 缓存
        self._metadata_cache: Optional[pd.DataFrame] = None
        self._points_cache: Optional[pd.DataFrame] = None

    def save_pathlets(self, pathlets: List[Pathlet], profiles_dict: Dict[str, Any]) -> None:
        """保存Pathlet数据。

        将Pathlet数据分离为元信息和点数据，分别写入Parquet文件。

        参数:
            pathlets: Pathlet列表
            profiles_dict: RawProfile字典，键为pathlet_id
        """
        if not pathlets:
            logger.warning("没有Pathlet数据可保存")
            return

        # 假设所有传入的Pathlet对象都是有效的
        valid_pathlets = pathlets

        logger.info(f"开始保存{len(valid_pathlets)} 个有效Pathlet数据")

        # 分离元信息和点数据
        metadata = self._extract_metadata(valid_pathlets, profiles_dict)
        points = self._extract_points(valid_pathlets, profiles_dict)

        # 写入Parquet文件
        self._write_metadata(metadata)
        self._write_points(points)

        logger.info(f"成功保存 {len(valid_pathlets)} 个有效Pathlet数据到{self.pathlet_dir}")

    def load_pathlets(self, state_id: Optional[int] = None) -> List[Pathlet]:
        """加载Pathlet数据。

        从Parquet文件加载元信息和点数据，合并为Pathlet列表。

        参数:
            state_id: 可选，按状态ID筛选

        返回:
            List[Pathlet]: Pathlet列表
        """
        if not self.metadata_file.exists() or not self.points_file.exists():
            logger.warning(f"Pathlet数据文件不存在: {self.pathlet_dir}")
            return []

        logger.info("开始加载Pathlet数据")

        # 读取元信息和点数据
        metadata_df = self._read_metadata()
        points_df = self._read_points()

        # 按状态ID筛选
        if state_id is not None:
            metadata_df = metadata_df[metadata_df["state_id"] == state_id]
            if metadata_df.empty:
                logger.info(f"没有找到状态ID为{state_id} 的Pathlet数据")
                return []

        # 合并数据，构建Pathlet列表
        pathlets = self._merge_data(metadata_df, points_df)

        logger.info(f"成功加载 {len(pathlets)} 个Pathlet数据")
        return pathlets

    def _extract_metadata(self, pathlets: List[Pathlet], profiles_dict: Dict[str, Any]) -> pd.DataFrame:
        """提取Pathlet元信息。

        参数:
            pathlets: Pathlet列表
            profiles_dict: RawProfile字典，键为pathlet_id

        返回:
            pd.DataFrame: 元信息DataFrame
        """
        metadata = []
        for pathlet in pathlets:
            profile = profiles_dict[pathlet.pathlet_id]
            # 如果有state_label，使用其state_id，否则设置为-1表示未标记
            state_id = pathlet.state_label.state_id if pathlet.state_label else -1
            metadata.append(
                {
                    "atom_id": pathlet.pathlet_id,
                    "is_valid": True,  # 假设所有Pathlet都是有效的
                    "state_id": state_id,  # 默认为-1表示未标记
                    "source_trace": profile.trace_name,
                    "start_index": profile.start_index,
                }
            )

        return pd.DataFrame(metadata)

    def _extract_points(self, pathlets: List[Pathlet], profiles_dict: Dict[str, Any]) -> pd.DataFrame:
        """提取Pathlet点数据。

        参数:
            pathlets: Pathlet列表
            profiles_dict: RawProfile字典，键为pathlet_id

        返回:
            pd.DataFrame: 点数据DataFrame
        """
        points = []

        for pathlet in pathlets:
            profile = profiles_dict[pathlet.pathlet_id]

            # 添加上下文点（100个，sample_index 0-99）
            for sample_index in range(100):
                if sample_index < len(profile.observations):
                    obs = profile.observations[sample_index]
                    points.append(
                        {
                            "atom_id": pathlet.pathlet_id,
                            "sample_index": sample_index,
                            "delay_up": obs.delay_up,
                            "loss_up": obs.loss_up,
                            "bw_up": obs.bw_up,
                            "delay_down": obs.delay_down,
                            "loss_down": obs.loss_down,
                            "bw_down": obs.bw_down,
                        }
                    )

            # 添加延续点（10个，sample_index 100-109）
            for i in range(10):
                sample_index = 100 + i
                if sample_index < len(profile.observations):
                    obs = profile.observations[sample_index]
                    points.append(
                        {
                            "atom_id": pathlet.pathlet_id,
                            "sample_index": sample_index,
                            "delay_up": obs.delay_up,
                            "loss_up": obs.loss_up,
                            "bw_up": obs.bw_up,
                            "delay_down": obs.delay_down,
                            "loss_down": obs.loss_down,
                            "bw_down": obs.bw_down,
                        }
                    )

        return pd.DataFrame(points)

    def _write_metadata(self, metadata: pd.DataFrame) -> None:
        """写入元信息到Parquet文件。

        参数:
            metadata: 元信息DataFrame
        """
        logger.info(f"写入元信息到 {self.metadata_file}")

        # 转换为Arrow表
        table = pa.Table.from_pandas(metadata)

        # 写入Parquet文件
        pq.write_table(table, self.metadata_file, compression="snappy")

        logger.info(f"成功写入 {len(metadata)} 条元信息")

    def _write_points(self, points: pd.DataFrame) -> None:
        """写入点数据到Parquet文件。

        参数:
            points: 点数据DataFrame
        """
        logger.info(f"写入点数据到 {self.points_file}")

        # 转换为Arrow表
        table = pa.Table.from_pandas(points)

        # 写入Parquet文件
        pq.write_table(table, self.points_file, compression="snappy")

        logger.info(f"成功写入 {len(points)} 条点数据")

    def _read_metadata(self) -> pd.DataFrame:
        """从Parquet文件读取元信息。

        返回:
            pd.DataFrame: 元信息DataFrame
        """
        # 使用缓存
        if self._metadata_cache is not None:
            return self._metadata_cache

        logger.info(f"读取元信息从 {self.metadata_file}")

        # 读取Parquet文件
        table = pq.read_table(self.metadata_file)
        df = table.to_pandas()

        logger.info(f"成功读取 {len(df)} 条元信息")

        # 缓存结果
        self._metadata_cache = df
        return df

    def _read_points(self) -> pd.DataFrame:
        """从Parquet文件读取点数据。

        返回:
            pd.DataFrame: 点数据DataFrame
        """
        # 使用缓存
        if self._points_cache is not None:
            return self._points_cache

        logger.info(f"读取点数据从 {self.points_file}")

        # 读取Parquet文件
        table = pq.read_table(self.points_file)
        df = table.to_pandas()

        logger.info(f"成功读取 {len(df)} 条点数据")

        # 缓存结果
        self._points_cache = df
        return df

    def _merge_data(self, metadata_df: pd.DataFrame, points_df: pd.DataFrame) -> List[Pathlet]:
        """合并元信息和点数据，构建Pathlet列表。

        参数:
            metadata_df: 元信息DataFrame
            points_df: 点数据DataFrame（当前未使用，保留参数是为了向后兼容）

        返回:
            List[Pathlet]: Pathlet列表
        """
        pathlets = []

        for _, metadata_row in metadata_df.iterrows():
            # 构建简化的Pathlet对象，只使用必需的属性
            pathlet = Pathlet(
                pathlet_id=metadata_row["atom_id"],
                body=BodyObservations(),  # 空的BodyObservations
                tail=TailObservations(),  # 空的TailObservations
            )

            pathlets.append(pathlet)

        return pathlets

    def get_pathlet_count(self) -> int:
        """获取Pathlet数量。

        返回:
            int: Pathlet数量
        """
        if not self.metadata_file.exists():
            return 0

        metadata_df = self._read_metadata()
        return len(metadata_df)

    def get_state_distribution(self) -> Dict[int, int]:
        """获取状态分布。

        返回:
            Dict[int, int]: 状态ID到数量的映射
        """
        if not self.metadata_file.exists():
            return {}

        metadata_df = self._read_metadata()
        state_counts = metadata_df["state_id"].value_counts().to_dict()

        return state_counts

    def load_pathlet_points(self, pathlet_id: str) -> Optional[pd.DataFrame]:
        """加载指定Pathlet的点数据。

        参数:
            pathlet_id: Pathlet唯一标识符

        返回:
            Optional[pd.DataFrame]: 点数据DataFrame，如果Pathlet不存在则返回None
        """
        if not self.points_file.exists():
            logger.warning(f"点数据文件不存在: {self.points_file}")
            return None

        points_df = self._read_points()
        pathlet_points = points_df[points_df["atom_id"] == pathlet_id]

        if pathlet_points.empty:
            logger.warning(f"没有找到Pathlet {pathlet_id} 的点数据")
            return None

        return pathlet_points.sort_values("sample_index")

    def get_raw_profile(self, pathlet_id: str) -> Optional[Dict[str, Any]]:
        """获取指定径元ID对应的原始数据

        参数:
            pathlet_id: 径元唯一标识符

        返回:
            Optional[Dict[str, Any]]: 包含原始数据的字典，如果径元不存在则返回None
        """
        if not self.metadata_file.exists() or not self.points_file.exists():
            logger.warning(f"Pathlet数据文件不存在: {self.pathlet_dir}")
            return None

        # 读取元信息
        metadata_df = self._read_metadata()
        metadata_row = metadata_df[metadata_df["atom_id"] == pathlet_id]

        if metadata_row.empty:
            logger.warning(f"没有找到径元 {pathlet_id} 的元信息")
            return None

        # 读取点数据
        points_df = self.load_pathlet_points(pathlet_id)
        if points_df is None:
            logger.warning(f"没有找到径元 {pathlet_id} 的点数据")
            return None

        # 分离上下文点和延续点
        ctx_points = points_df[points_df["sample_index"] < 100]
        cont_points = points_df[points_df["sample_index"] >= 100]

        # 构建ContextData
        ctx_10s = ContextData(
            delay_up=ctx_points["delay_up"].tolist(),
            loss_up=ctx_points["loss_up"].tolist(),
            bw_up=ctx_points["bw_up"].tolist(),
            delay_down=ctx_points["delay_down"].tolist(),
            loss_down=ctx_points["loss_down"].tolist(),
            bw_down=ctx_points["bw_down"].tolist(),
        )

        # 构建ContinuationData
        cont_1s = ContinuationData(
            delay_up=cont_points["delay_up"].tolist(),
            loss_up=cont_points["loss_up"].tolist(),
            bw_up=cont_points["bw_up"].tolist(),
            delay_down=cont_points["delay_down"].tolist(),
            loss_down=cont_points["loss_down"].tolist(),
            bw_down=cont_points["bw_down"].tolist(),
        )

        # 计算PathletStatistics
        ctx_values = PathletStatistics(
            delay_up_mean=ctx_points["delay_up"].mean(),
            delay_up_std=ctx_points["delay_up"].std(),
            delay_down_mean=ctx_points["delay_down"].mean(),
            delay_down_std=ctx_points["delay_down"].std(),
            loss_up_mean=ctx_points["loss_up"].mean(),
            loss_up_max=ctx_points["loss_up"].max(),
            loss_down_mean=ctx_points["loss_down"].mean(),
            loss_down_max=ctx_points["loss_down"].max(),
            bw_up_mean=ctx_points["bw_up"].mean(),
            bw_up_max=ctx_points["bw_up"].max(),
            bw_down_mean=ctx_points["bw_down"].mean(),
            bw_down_max=ctx_points["bw_down"].max(),
        )

        # 构建返回数据
        trace_name = metadata_row["source_trace"].iloc[0]
        start_index = int(metadata_row["start_index"].iloc[0])

        return {
            "trace_name": trace_name,
            "start_index": start_index,
            "ctx_10s": ctx_10s,
            "cont_1s": cont_1s,
            "ctx_values": ctx_values,
            "is_valid": bool(metadata_row["is_valid"].iloc[0]),
        }

    def reconstruct_profile(self, pathlet_points: pd.DataFrame) -> tuple[ContextData, ContinuationData]:
        """根据点数据重建原始数据结构

        参数:
            pathlet_points: 点数据DataFrame

        返回:
            tuple[ContextData, ContinuationData]: 上下文数据和延续数据
        """
        # 按sample_index排序
        pathlet_points = pathlet_points.sort_values("sample_index")

        # 分离上下文点和延续点
        # 上下文点：sample_index 0-99
        ctx_points = pathlet_points[pathlet_points["sample_index"] < 100]
        # 延续点：sample_index 100-109
        cont_points = pathlet_points[pathlet_points["sample_index"] >= 100]

        # 构建上下文数据
        ctx_10s = ContextData(
            delay_up=ctx_points["delay_up"].tolist(),
            loss_up=ctx_points["loss_up"].tolist(),
            bw_up=ctx_points["bw_up"].tolist(),
            delay_down=ctx_points["delay_down"].tolist(),
            loss_down=ctx_points["loss_down"].tolist(),
            bw_down=ctx_points["bw_down"].tolist(),
        )

        # 构建延续数据
        cont_1s = ContinuationData(
            delay_up=cont_points["delay_up"].tolist(),
            loss_up=cont_points["loss_up"].tolist(),
            bw_up=cont_points["bw_up"].tolist(),
            delay_down=cont_points["delay_down"].tolist(),
            loss_down=cont_points["loss_down"].tolist(),
            bw_down=cont_points["bw_down"].tolist(),
        )

        return ctx_10s, cont_1s

    def clear(self) -> None:
        """清空Pathlet数据

        删除所有Pathlet数据文件
        """
        if self.metadata_file.exists():
            self.metadata_file.unlink()
            logger.info(f"已删除元信息文件: {self.metadata_file}")

        if self.points_file.exists():
            self.points_file.unlink()
            logger.info(f"已删除点数据文件: {self.points_file}")

        if self.gmm_model_file.exists():
            self.gmm_model_file.unlink()
            logger.info(f"已删除GMM模型文件: {self.gmm_model_file}")

        if self.state_mapping_file.exists():
            self.state_mapping_file.unlink()
            logger.info(f"已删除状态映射文件: {self.state_mapping_file}")

        logger.info(f"已清空Pathlet数据目录: {self.pathlet_dir}")

    def save_gmm_model(self, model: Any, state_mapping: Dict[str, Any]) -> None:
        """保存GMM模型和状态映射

        参数:
            model: GMM模型对象
            state_mapping: 状态映射字典
        """
        # 保存模型
        joblib.dump(model, self.gmm_model_file)
        logger.info(f"GMM模型已保存到: {self.gmm_model_file}")

        # 保存状态映射
        import json
        with open(self.state_mapping_file, 'w', encoding='utf-8') as f:
            json.dump(state_mapping, f, ensure_ascii=False, indent=2)
        logger.info(f"状态映射已保存到: {self.state_mapping_file}")

    def load_gmm_model(self) -> Optional[Any]:
        """加载GMM模型

        返回:
            Optional[Any]: 加载的GMM模型对象，如果文件不存在则返回None
        """
        if not self.gmm_model_file.exists():
            logger.warning(f"GMM模型文件不存在: {self.gmm_model_file}")
            return None

        model = joblib.load(self.gmm_model_file)
        logger.info(f"GMM模型已从: {self.gmm_model_file} 加载")
        return model

    def load_state_mapping(self) -> Optional[Dict[str, Any]]:
        """加载状态映射

        返回:
            Optional[Dict[str, Any]]: 状态映射字典，如果文件不存在则返回None
        """
        if not self.state_mapping_file.exists():
            logger.warning(f"状态映射文件不存在: {self.state_mapping_file}")
            return None

        import json
        with open(self.state_mapping_file, 'r', encoding='utf-8') as f:
            state_mapping = json.load(f)
        logger.info(f"状态映射已从: {self.state_mapping_file} 加载")
        return state_mapping

    def save_state_gmm_model(self, model_data: Dict[str, Any]) -> None:
        """保存轻量级StateGMM模型

        参数:
            model_data: 模型数据字典，包含gmm、scaler等组件
        """
        joblib.dump(model_data, self.gmm_model_file)
        logger.info(f"轻量级StateGMM模型已保存到: {self.gmm_model_file}")

    def load_state_gmm_model(self) -> Optional[Dict[str, Any]]:
        """加载轻量级StateGMM模型

        返回:
            Optional[Dict[str, Any]]: 模型数据字典，如果文件不存在则返回None
        """
        if not self.gmm_model_file.exists():
            logger.warning(f"StateGMM模型文件不存在: {self.gmm_model_file}")
            return None

        model_data = joblib.load(self.gmm_model_file)
        logger.info(f"轻量级StateGMM模型已从: {self.gmm_model_file} 加载")
        return model_data
