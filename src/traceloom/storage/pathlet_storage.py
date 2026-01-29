# -*- coding: utf-8 -*-
"""径元数据存储模块。

用于读写径元数据，支持Parquet格式存储。
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
from traceloom.domain.pathlet import BodyObservations, Observation, Pathlet, PathletMeta, TailObservations
from traceloom.storage.adapters import PathletStorageAdapter


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
            pathlet_dir: Pathlet数据存储目录，默认使用settings.PATHLETS_DIR

        示例:
            from traceloom.storage.pathlet_storage import PathletStorage
            from traceloom.core.config import settings
            from pathlib import Path

            # 使用默认存储目录
            storage = PathletStorage()

            # 使用自定义存储目录
            custom_dir = Path("/path/to/custom/pathlets")
            storage = PathletStorage(custom_dir)
        """
        self.pathlet_dir = pathlet_dir or settings.PATHLETS_DIR
        self.pathlet_dir.mkdir(exist_ok=True, parents=True)

        self.metadata_file = self.pathlet_dir / "pathlets_meta.parquet"
        self.points_file = self.pathlet_dir / "pathlets_points.parquet"
        self.gmm_model_file = self.pathlet_dir / "gmm_model.joblib"
        self.state_mapping_file = self.pathlet_dir / "state_mapping.json"

        # 缓存配置
        self._metadata_cache: Optional[pd.DataFrame] = None
        self._points_cache: Optional[pd.DataFrame] = None
        self._cache_timestamp: Dict[str, float] = {}
        self._cache_expiry_seconds = 300  # 缓存过期时间，5分钟

        # 存储适配器
        self.storage_adapter = PathletStorageAdapter()

    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效

        参数:
            cache_key: 缓存键

        返回:
            bool: 缓存是否有效
        """
        import time
        
        if cache_key not in self._cache_timestamp:
            return False
        
        current_time = time.time()
        return current_time - self._cache_timestamp[cache_key] < self._cache_expiry_seconds

    def _update_cache_timestamp(self, cache_key: str) -> None:
        """更新缓存时间戳

        参数:
            cache_key: 缓存键
        """
        import time
        self._cache_timestamp[cache_key] = time.time()

    def clear_cache(self) -> None:
        """清除所有缓存

        示例:
            from traceloom.storage.pathlet_storage import PathletStorage

            # 初始化存储
            storage = PathletStorage()

            # 清除缓存
            storage.clear_cache()
            print("缓存已清除")
        """
        self._metadata_cache = None
        self._points_cache = None
        self._cache_timestamp.clear()
        logger.info("缓存已清除")

    def save_pathlets(self, pathlets: List[Pathlet], pathlet_meta_map: Dict[str, PathletMeta]) -> None:
        """保存Pathlet数据。

        将Pathlet数据分离为元信息和点数据，分别写入Parquet文件。

        参数:
            pathlets: Pathlet列表
            pathlet_meta_map: 径元ID到PathletMeta的映射

        示例:
            from traceloom.storage.pathlet_storage import PathletStorage
            from traceloom.domain.pathlet import Pathlet, BodyObservations, TailObservations, PathletMeta, Observation

            # 初始化存储
            storage = PathletStorage()

            # 准备Pathlet数据
            pathlet1 = Pathlet(
                pathlet_id="pathlet_001",
                body=BodyObservations(),
                tail=TailObservations()
            )

            pathlet2 = Pathlet(
                pathlet_id="pathlet_002",
                body=BodyObservations(),
                tail=TailObservations()
            )

            # 准备pathlet_meta_map（实际使用中应包含真实的观测数据）
            # 创建观测数据
            observations = [Observation() for _ in range(110)]

            pathlet_meta_map = {
                "pathlet_001": PathletMeta(
                    trace_name="trace_001",
                    start_index=0,
                    is_valid=True,
                    observations=observations
                ),
                "pathlet_002": PathletMeta(
                    trace_name="trace_002",
                    start_index=100,
                    is_valid=True,
                    observations=observations
                )
            }

            # 保存Pathlet数据
            storage.save_pathlets([pathlet1, pathlet2], pathlet_meta_map)
        """
        if not pathlets:
            logger.warning("没有Pathlet数据可保存")
            return

        # 假设所有传入的Pathlet对象都是有效的
        valid_pathlets = pathlets

        logger.info(f"开始保存{len(valid_pathlets)} 个有效Pathlet数据")

        # 使用适配器转换数据
        metadata_df, points_df = self.storage_adapter.pathlets_to_storage(valid_pathlets, pathlet_meta_map)

        # 写入Parquet文件
        self._write_metadata(metadata_df)
        self._write_points(points_df)
        self._write_external_manifest(metadata_df)

        # 清除缓存，确保下次读取时能获取最新数据
        self.clear_cache()

        logger.info(f"成功保存 {len(valid_pathlets)} 个有效Pathlet数据到{self.pathlet_dir}")

    def load_pathlets(self, state_id: Optional[int] = None) -> List[Pathlet]:
        """加载Pathlet数据。

        从Parquet文件加载元信息和点数据，合并为Pathlet列表。

        参数:
            state_id: 可选，按状态ID筛选

        返回:
            List[Pathlet]: Pathlet列表

        示例:
            from traceloom.storage.pathlet_storage import PathletStorage

            # 初始化存储
            storage = PathletStorage()

            # 加载所有Pathlet数据
            all_pathlets = storage.load_pathlets()
            print(f"加载了 {len(all_pathlets)} 个Pathlet")

            # 按状态ID筛选加载
            state_0_pathlets = storage.load_pathlets(state_id=0)
            print(f"加载了 {len(state_0_pathlets)} 个状态为0的Pathlet")
        """

        if not self.metadata_file.exists():
            logger.warning(f"Pathlet元数据文件不存在: {self.pathlet_dir}")
            return []

        logger.info("开始加载Pathlet数据")

        # 读取元信息，使用谓词下推
        metadata_table = pq.read_table(self.metadata_file)
        
        # 按状态ID筛选
        if state_id is not None:
            metadata_table = metadata_table.filter(pa.compute.equal(metadata_table["state_id"], state_id))
            if metadata_table.num_rows == 0:
                logger.info(f"没有找到状态ID为{state_id} 的Pathlet数据")
                return []
        
        metadata_df = metadata_table.to_pandas()

        # 只有当有元数据时才读取点数据
        if metadata_df.empty:
            logger.info("没有找到Pathlet数据")
            return []

        # 读取点数据
        points_df = self._read_points()

        # 使用适配器转换数据
        pathlets = self.storage_adapter.storage_to_pathlets(metadata_df, points_df)

        logger.info(f"成功加载 {len(pathlets)} 个Pathlet数据")
        return pathlets

    @staticmethod
    def _extract_metadata(pathlets: List[Pathlet], profiles_dict: Dict[str, Any]) -> pd.DataFrame:
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
                    "pathlet_id": pathlet.pathlet_id,
                    "is_valid": True,  # 假设所有Pathlet都是有效的
                    "state_id": state_id,  # 默认为-1表示未标记
                    "source_trace": profile.trace_name,
                    "start_index": profile.start_index,
                }
            )

        return pd.DataFrame(metadata)

    @staticmethod
    def _extract_points(pathlets: List[Pathlet], profiles_dict: Dict[str, Any]) -> pd.DataFrame:
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
                            "pathlet_id": pathlet.pathlet_id,
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
                            "pathlet_id": pathlet.pathlet_id,
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

    def _write_external_manifest(self, metadata: pd.DataFrame) -> None:
        """写入对外清单文件pathlets.parquet。

        参数:
            metadata: 元信息DataFrame
        """
        if metadata.empty:
            logger.warning("无数据可写入对外清单")
            return
            
        logger.info(f"写入对外清单到 {self.pathlet_dir / 'pathlets.parquet'}")
        
        # 生成对外清单DataFrame
        external_df = metadata[[
            "pathlet_id",
            "state_id",
            "trace_name",
            "start_index"
        ]].copy()
        external_df.rename(columns={"trace_name": "source_file"}, inplace=True)
        
        # 转换为Arrow表
        table = pa.Table.from_pandas(external_df)
        
        # 写入Parquet文件
        pq.write_table(table, self.pathlet_dir / "pathlets.parquet", compression="ZSTD")
        
        logger.info(f"成功写入 {len(external_df)} 条对外清单记录")

    def _write_points(self, points: pd.DataFrame) -> None:
        """写入点数据到Parquet文件。

        参数:
            points: 点数据DataFrame
        """
        if points.empty:
            logger.warning("无点数据可写入")
            return
            
        logger.info(f"写入点数据到 {self.points_file}")

        # 确保trace_index列存在并排序
        if "trace_index" in points.columns:
            points = points.sort_values(["trace_name", "trace_index"])

        # 转换为Arrow表
        table = pa.Table.from_pandas(points)

        # 按trace_name分区写入
        pq.write_to_dataset(
            table,
            root_path=str(self.points_file),
            partition_cols=["trace_name"],
            compression="ZSTD",
            use_dictionary=True
        )

        logger.info(f"成功写入 {len(points)} 条点数据")

    def _read_metadata(self) -> pd.DataFrame:
        """从Parquet文件读取元信息。

        返回:
            pd.DataFrame: 元信息DataFrame
        """
        # 使用缓存
        if self._metadata_cache is not None and self._is_cache_valid("metadata"):
            self._update_cache_timestamp("metadata")
            return self._metadata_cache

        logger.info(f"读取元信息从 {self.metadata_file}")

        # 读取Parquet文件
        table = pq.read_table(self.metadata_file)
        df = table.to_pandas()

        logger.info(f"成功读取 {len(df)} 条元信息")

        # 缓存结果
        self._metadata_cache = df
        self._update_cache_timestamp("metadata")
        return df

    def _read_points(self) -> pd.DataFrame:
        """从Parquet文件读取点数据。

        返回:
            pd.DataFrame: 点数据DataFrame
        """
        # 使用缓存
        if self._points_cache is not None and self._is_cache_valid("points"):
            self._update_cache_timestamp("points")
            return self._points_cache

        logger.info(f"读取点数据从 {self.points_file}")

        # 检查点数据是否存在
        if not self.points_file.exists():
            logger.warning(f"点数据文件不存在: {self.points_file}")
            return pd.DataFrame()

        # 读取Parquet数据集（支持分区）
        dataset = pq.ParquetDataset(self.points_file)
        table = dataset.read()
        df = table.to_pandas()

        logger.info(f"成功读取 {len(df)} 条点数据")

        # 缓存结果
        self._points_cache = df
        self._update_cache_timestamp("points")
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
                pathlet_id=metadata_row["pathlet_id"],
                body=BodyObservations(),  # 空的BodyObservations
                tail=TailObservations(),  # 空的TailObservations
            )

            pathlets.append(pathlet)

        return pathlets

    def get_pathlet_count(self) -> int:
        """获取Pathlet数量。

        返回:
            int: Pathlet数量

        示例:
            from traceloom.storage.pathlet_storage import PathletStorage

            # 初始化存储
            storage = PathletStorage()

            # 获取Pathlet数量
            count = storage.get_pathlet_count()
            print(f"总共有 {count} 个Pathlet")
        """

        if not self.metadata_file.exists():
            return 0

        metadata_df = self._read_metadata()
        return len(metadata_df)

    def get_state_distribution(self) -> Dict[int, int]:
        """获取状态分布。

        返回:
            Dict[int, int]: 状态ID到数量的映射

        示例:
            from traceloom.storage.pathlet_storage import PathletStorage

            # 初始化存储
            storage = PathletStorage()

            # 获取状态分布
            distribution = storage.get_state_distribution()
            print("状态分布:")
            for state_id, count in distribution.items():
                print(f"状态 {state_id}: {count} 个Pathlet")
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

        示例:
            from traceloom.storage.pathlet_storage import PathletStorage

            # 初始化存储
            storage = PathletStorage()

            # 加载指定Pathlet的点数据
            pathlet_id = "pathlet_001"
            points_df = storage.load_pathlet_points(pathlet_id)

            if points_df is not None:
                print(f"成功加载Pathlet {pathlet_id} 的点数据")
                print(f"点数据行数: {len(points_df)}")
                print("前5行数据:")
                print(points_df.head())
            else:
                print(f"Pathlet {pathlet_id} 不存在或无点数据")
        """

        if not self.points_file.exists():
            logger.warning(f"点数据文件不存在: {self.points_file}")
            return None

        points_df = self._read_points()
        
        # 检查是否存在点数据
        if points_df.empty:
            logger.warning(f"点数据文件为空")
            return None

        # 确定使用哪个字段来存储径元ID
        id_column = "containing_pathlet_ids" if "containing_pathlet_ids" in points_df.columns else "pathlet_ids"
        
        # 检查数组字段是否包含指定的pathlet_id
        if id_column in points_df.columns:
            pathlet_points = points_df[points_df[id_column].apply(lambda x: pathlet_id in x)]
        else:
            logger.warning(f"点数据中不存在 {id_column} 字段")
            return None

        if pathlet_points.empty:
            logger.warning(f"没有找到Pathlet {pathlet_id} 的点数据")
            return None

        # 按trace_index排序
        if "trace_index" in pathlet_points.columns:
            pathlet_points = pathlet_points.sort_values("trace_index")

        return pathlet_points

    def get_raw_profile(self, pathlet_id: str) -> Optional[Dict[str, Any]]:
        """获取指定径元ID对应的原始数据

        参数:
            pathlet_id: 径元唯一标识符

        返回:
            Optional[Dict[str, Any]]: 包含原始数据的字典，如果径元不存在则返回None

        示例:
            from traceloom.storage.pathlet_storage import PathletStorage

            # 初始化存储
            storage = PathletStorage()

            # 获取指定径元的原始数据
            pathlet_id = "pathlet_001"
            raw_profile = storage.get_raw_profile(pathlet_id)

            if raw_profile is not None:
                print(f"成功获取径元 {pathlet_id} 的原始数据")
                print(f"轨迹名称: {raw_profile['trace_name']}")
                print(f"起始索引: {raw_profile['start_index']}")
                print(f"是否有效: {raw_profile['is_valid']}")
                print(f"上下文数据点数: {len(raw_profile['ctx_10s'].observations)}")
                print(f"延续数据点数: {len(raw_profile['cont_1s'].observations)}")
            else:
                print(f"径元 {pathlet_id} 不存在或无数据")
        """

        if not self.metadata_file.exists() or not self.points_file.exists():
            logger.warning(f"Pathlet数据文件不存在: {self.pathlet_dir}")
            return None

        # 读取元信息
        metadata_df = self._read_metadata()
        metadata_row = metadata_df[metadata_df["pathlet_id"] == pathlet_id]

        if metadata_row.empty:
            logger.warning(f"没有找到径元 {pathlet_id} 的元信息")
            return None

        # 读取点数据
        points_df = self.load_pathlet_points(pathlet_id)
        if points_df is None:
            logger.warning(f"没有找到径元 {pathlet_id} 的点数据")
            return None

        # 获取起始索引
        start_index = int(metadata_row["start_index"].iloc[0])

        # 分离上下文点和延续点
        # 计算相对索引：trace_index - start_index
        ctx_points = points_df[points_df["trace_index"].apply(lambda x: (x - start_index) < 100)]
        cont_points = points_df[points_df["trace_index"].apply(lambda x: 100 <= (x - start_index) < 110)]

        # 构建BodyObservations
        body_observations = []
        for _, row in ctx_points.iterrows():
            obs = Observation(
                delay_up=row["delay_up"],
                loss_up=row["loss_up"],
                bw_up=row["bw_up"],
                delay_down=row["delay_down"],
                loss_down=row["loss_down"],
                bw_down=row["bw_down"],
            )
            body_observations.append(obs)
        ctx_10s = BodyObservations(observations=body_observations)

        # 构建TailObservations
        tail_observations = []
        for _, row in cont_points.iterrows():
            obs = Observation(
                delay_up=row["delay_up"],
                loss_up=row["loss_up"],
                bw_up=row["bw_up"],
                delay_down=row["delay_down"],
                loss_down=row["loss_down"],
                bw_down=row["bw_down"],
            )
            tail_observations.append(obs)
        cont_1s = TailObservations(observations=tail_observations)

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
        trace_name = metadata_row["trace_name"].iloc[0]

        return {
            "trace_name": trace_name,
            "start_index": start_index,
            "ctx_10s": ctx_10s,
            "cont_1s": cont_1s,
            "ctx_values": ctx_values,
            "is_valid": bool(metadata_row["is_valid"].iloc[0]),
        }

    def reconstruct_profile(
        self, pathlet_points: pd.DataFrame, start_index: Optional[int] = None
    ) -> tuple[BodyObservations, TailObservations]:
        """根据点数据重建原始数据结构

        参数:
            pathlet_points: 点数据DataFrame
            start_index: 径元在原始轨迹中的起始索引，如果提供则使用相对索引

        返回:
            tuple[BodyObservations, TailObservations]: 主体观测数据和融尾观测数据

        示例:
            from traceloom.storage.pathlet_storage import PathletStorage

            # 初始化存储
            storage = PathletStorage()

            # 先加载点数据
            pathlet_id = "pathlet_001"
            points_df = storage.load_pathlet_points(pathlet_id)

            if points_df is not None:
                # 重建原始数据结构
                body, tail = storage.reconstruct_profile(points_df)

                print(f"成功重建Pathlet {pathlet_id} 的数据结构")
                print(f"主体观测数据点数: {len(body.observations)}")
                print(f"融尾观测数据点数: {len(tail.observations)}")
            else:
                print(f"Pathlet {pathlet_id} 不存在或无点数据")
        """

        # 按trace_index排序
        pathlet_points = pathlet_points.sort_values("trace_index")

        # 分离上下文点和延续点
        if start_index is not None:
            # 使用相对索引：trace_index - start_index
            ctx_points = pathlet_points[pathlet_points["trace_index"].apply(lambda x: (x - start_index) < 100)]
            cont_points = pathlet_points[pathlet_points["trace_index"].apply(lambda x: 100 <= (x - start_index) < 110)]
        else:
            # 如果没有提供start_index，按前100个作为上下文点，后10个作为延续点
            ctx_points = pathlet_points.head(100)
            cont_points = pathlet_points.tail(10)

        # 构建主体观测数据
        body_observations = []
        for _, row in ctx_points.iterrows():
            obs = Observation(
                delay_up=row["delay_up"],
                loss_up=row["loss_up"],
                bw_up=row["bw_up"],
                delay_down=row["delay_down"],
                loss_down=row["loss_down"],
                bw_down=row["bw_down"],
            )
            body_observations.append(obs)
        body = BodyObservations(observations=body_observations)

        # 构建融尾观测数据
        tail_observations = []
        for _, row in cont_points.iterrows():
            obs = Observation(
                delay_up=row["delay_up"],
                loss_up=row["loss_up"],
                bw_up=row["bw_up"],
                delay_down=row["delay_down"],
                loss_down=row["loss_down"],
                bw_down=row["bw_down"],
            )
            tail_observations.append(obs)
        tail = TailObservations(observations=tail_observations)

        return body, tail

    def clear(self) -> None:
        """清空Pathlet数据

        删除所有Pathlet数据文件

        示例:
            from traceloom.storage.pathlet_storage import PathletStorage

            # 初始化存储
            storage = PathletStorage()

            # 清空所有Pathlet数据
            print("开始清空Pathlet数据...")
            storage.clear()
            print("Pathlet数据已清空")

            # 验证清空结果
            count = storage.get_pathlet_count()
            print(f"清空后Pathlet数量: {count}")
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

        示例:
            from traceloom.storage.pathlet_storage import PathletStorage

            # 初始化存储
            storage = PathletStorage()

            # 假设我们有一个训练好的GMM模型和状态映射
            # model = train_gmm_model()  # 实际训练模型的代码
            # state_mapping = {"0": "normal", "1": "congested", "2": "lossy"}

            # 保存模型和状态映射
            # storage.save_gmm_model(model, state_mapping)
            # print("GMM模型和状态映射已保存")
        """

        # 保存模型
        joblib.dump(model, self.gmm_model_file)
        logger.info(f"GMM模型已保存到: {self.gmm_model_file}")

        # 保存状态映射
        import json

        with open(self.state_mapping_file, "w", encoding="utf-8") as f:
            json.dump(state_mapping, f, ensure_ascii=False, indent=2)
        logger.info(f"状态映射已保存到: {self.state_mapping_file}")

    def load_gmm_model(self) -> Optional[Any]:
        """加载GMM模型

        返回:
            Optional[Any]: 加载的GMM模型对象，如果文件不存在则返回None

        示例:
            from traceloom.storage.pathlet_storage import PathletStorage

            # 初始化存储
            storage = PathletStorage()

            # 加载GMM模型
            model = storage.load_gmm_model()

            if model is not None:
                print("成功加载GMM模型")
                # 可以使用加载的模型进行预测等操作
                # predictions = model.predict(data)
            else:
                print("GMM模型文件不存在")
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

        示例:
            from traceloom.storage.pathlet_storage import PathletStorage

            # 初始化存储
            storage = PathletStorage()

            # 加载状态映射
            state_mapping = storage.load_state_mapping()

            if state_mapping is not None:
                print("成功加载状态映射")
                print("状态映射内容:")
                for state_id, state_info in state_mapping.items():
                    print(f"状态 {state_id}: {state_info}")
            else:
                print("状态映射文件不存在")
        """

        if not self.state_mapping_file.exists():
            logger.warning(f"状态映射文件不存在: {self.state_mapping_file}")
            return None

        import json

        with open(self.state_mapping_file, "r", encoding="utf-8") as f:
            state_mapping = json.load(f)
        logger.info(f"状态映射已从: {self.state_mapping_file} 加载")
        return state_mapping

    def save_state_gmm_model(self, model_data: Dict[str, Any]) -> None:
        """保存轻量级StateGMM模型

        参数:
            model_data: 模型数据字典，包含gmm、scaler等组件

        示例:
            from traceloom.storage.pathlet_storage import PathletStorage

            # 初始化存储
            storage = PathletStorage()

            # 假设我们有一个构建好的StateGMM模型数据
            # model_data = {
            #     "gmm": gmm_model,
            #     "scaler": scaler,
            #     "n_components": 3,
            #     "state_mapping": {"0": "normal", "1": "congested", "2": "lossy"}
            # }

            # 保存轻量级StateGMM模型
            # storage.save_state_gmm_model(model_data)
            # print("轻量级StateGMM模型已保存")
        """

        joblib.dump(model_data, self.gmm_model_file)
        logger.info(f"轻量级StateGMM模型已保存到: {self.gmm_model_file}")

    def load_state_gmm_model(self) -> Optional[Dict[str, Any]]:
        """加载轻量级StateGMM模型

        返回:
            Optional[Dict[str, Any]]: 模型数据字典，如果文件不存在则返回None

        示例:
            from traceloom.storage.pathlet_storage import PathletStorage

            # 初始化存储
            storage = PathletStorage()

            # 加载轻量级StateGMM模型
            model_data = storage.load_state_gmm_model()

            if model_data is not None:
                print("成功加载轻量级StateGMM模型")
                print(f"模型组件: {list(model_data.keys())}")
                if "n_components" in model_data:
                    print(f"GMM组件数: {model_data['n_components']}")
                if "state_mapping" in model_data:
                    print("状态映射:")
                    for state_id, state_info in model_data["state_mapping"].items():
                        print(f"状态 {state_id}: {state_info}")
            else:
                print("轻量级StateGMM模型文件不存在")
        """

        if not self.gmm_model_file.exists():
            logger.warning(f"StateGMM模型文件不存在: {self.gmm_model_file}")
            return None

        model_data = joblib.load(self.gmm_model_file)
        logger.info(f"轻量级StateGMM模型已从: {self.gmm_model_file} 加载")
        return model_data
