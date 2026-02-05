# -*- coding: utf-8 -*-
"""径元数据存储模块。

用于读写径元数据，支持Parquet格式存储。
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from traceloom.core.config import settings
from traceloom.core.logger import logger
from traceloom.domain.pathlet import BodyObservations, Observation, Pathlet, TailObservations
from traceloom.storage.managers import (
    PathletCacheManager,
    PathletMetadataManager,
    PathletModelManager,
    PathletPointsManager,
)
from traceloom.storage.schemas import PathletMetadataFields, PointDataFields


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
    实现了单例模式，确保同一目录的PathletStorage只被初始化一次。

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

    # 单例模式实现
    _instances: Dict[str, "PathletStorage"] = {}

    def __new__(cls, pathlet_dir: Optional[Path] = None):
        """创建或获取PathletStorage实例

        使用单例模式，确保同一目录的PathletStorage只被初始化一次。

        参数:
            pathlet_dir: Pathlet数据存储目录，默认使用settings.PATHLETS_DIR

        返回:
            PathletStorage: PathletStorage实例
        """
        # 确定存储目录路径
        storage_dir = pathlet_dir or settings.PATHLETS_DIR
        dir_key = str(storage_dir.absolute())

        # 检查实例是否已存在
        if dir_key not in cls._instances:
            cls._instances[dir_key] = super(PathletStorage, cls).__new__(cls)

        return cls._instances[dir_key]

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
        # 确保存储目录路径一致
        storage_dir = pathlet_dir or settings.PATHLETS_DIR

        # 检查是否已经初始化过
        if hasattr(self, "_initialized") and self._initialized:
            return

        self.pathlet_dir = storage_dir
        self.pathlet_dir.mkdir(exist_ok=True, parents=True)

        # 初始化各个管理器
        self.metadata_manager = PathletMetadataManager(self.pathlet_dir / "pathlets.parquet")
        self.points_manager = PathletPointsManager(self.pathlet_dir / "pathlets_points")
        self.cache_manager = PathletCacheManager()
        self.model_manager = PathletModelManager(self.pathlet_dir)

        # 标记初始化完成
        self._initialized = True

    @staticmethod
    def pathlets_to_storage(pathlets: List[Pathlet]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """将 Pathlet 对象转换为存储结构

        参数:
            pathlets: Pathlet 列表

        返回:
            Tuple[pd.DataFrame, pd.DataFrame]: 元数据和点数据的 DataFrame
        """
        metadata = []
        unique_points = {}

        for pathlet in pathlets:
            # 确保 trace_name 是字符串类型
            trace_name = str(pathlet.trace_name)
            # 如果 trace_name 为空，尝试从 pathlet_id 中提取
            if not trace_name:
                # 尝试从 pathlet_id 中提取 trace_name（格式：{trace_name}_{index}）
                if "_" in pathlet.pathlet_id:
                    # 例如：20260118_231050_VAj-playback_0 -> 20260118_231050_VAj-playback
                    parts = pathlet.pathlet_id.split("_")
                    # 找到最后一个数字部分的索引
                    for i in range(len(parts) - 1, -1, -1):
                        if parts[i].isdigit():
                            # 提取前面的部分作为 trace_name
                            trace_name = "_".join(parts[:i])
                            break
            start_index = pathlet.start_index
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
                    PathletMetadataFields.START_INDEX: start_index,
                    PathletMetadataFields.DATASET: pathlet.dataset,
                }
            )

            # 提取点数据（去重处理）
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

        # 创建点数据 DataFrame
        points_df = pd.DataFrame(list(unique_points.values()))

        return pd.DataFrame(metadata), points_df

    @staticmethod
    def storage_to_pathlets(metadata_df: pd.DataFrame, points_df: pd.DataFrame) -> List[Pathlet]:
        """将存储结构转换为 Pathlet 对象

        参数:
            metadata_df: 元数据 DataFrame
            points_df: 点数据 DataFrame

        返回:
            List[Pathlet]: Pathlet 列表
        """
        pathlets = []

        # 按径元分组点数据
        pathlet_points = {}
        if not points_df.empty:
            # 使用固定字段名
            id_column = PointDataFields.PATHLET_IDS

            for _idx, row in points_df.iterrows():
                # 直接使用 pathlet_ids 字段
                pathlet_ids = row[id_column]

                for pathlet_id in pathlet_ids:
                    if pathlet_id not in pathlet_points:
                        pathlet_points[pathlet_id] = []
                    pathlet_points[pathlet_id].append(row)
        else:
            logger.warning("点数据为空，将创建不含观测数据的 Pathlet 对象")

        # 构建 Pathlet 对象
        for _, metadata_row in metadata_df.iterrows():
            pathlet_id = metadata_row[PathletMetadataFields.PATHLET_ID]
            logger.debug(f"处理径元: {pathlet_id}")

            start_index = metadata_row[PathletMetadataFields.START_INDEX]
            trace_name = metadata_row[PathletMetadataFields.TRACE_NAME]

            # 提取该径元的点数据
            pathlet_points_list = pathlet_points.get(pathlet_id, [])

            # 按 trace_index 排序
            pathlet_points_list.sort(key=lambda x: x[PointDataFields.TRACE_INDEX])

            # 构建 BodyObservations 和 TailObservations
            body_observations = []
            tail_observations = []

            # 计算预期的 trace_index 范围
            expected_trace_indices = set(range(start_index, start_index + 110))
            actual_trace_indices = set()

            for point in pathlet_points_list:
                trace_index = point[PointDataFields.TRACE_INDEX]
                actual_trace_indices.add(trace_index)

                # 计算相对索引
                relative_index = trace_index - start_index

                # 创建观测数据
                obs = Observation(
                    delay_up=point[PointDataFields.DELAY_UP],
                    loss_up=point[PointDataFields.LOSS_UP],
                    bw_up=point[PointDataFields.BW_UP],
                    delay_down=point[PointDataFields.DELAY_DOWN],
                    loss_down=point[PointDataFields.LOSS_DOWN],
                    bw_down=point[PointDataFields.BW_DOWN],
                )

                # 按相对索引分配到 body 或 tail
                if relative_index < 100:
                    body_observations.append(obs)
                elif relative_index < 110:
                    tail_observations.append(obs)

            # 验证数据完整性
            missing_indices = expected_trace_indices - actual_trace_indices
            if missing_indices:
                logger.warning(
                    f"径元 {pathlet_id} 缺少 {len(missing_indices)} 个点数据: {sorted(missing_indices)[:5]}..."
                )

            # 从 metadata_row 中提取 state_id
            state_id = metadata_row[PathletMetadataFields.STATE_ID]
            from traceloom.domain.state import StateLabel

            state_label = StateLabel(state_id=state_id)

            # 创建 Pathlet 对象
            pathlet = Pathlet(
                pathlet_id=pathlet_id,
                trace_name=trace_name,
                start_index=start_index,
                body=BodyObservations(observations=body_observations),
                tail=TailObservations(observations=tail_observations),
                state_label=state_label,  # 从 metadata_row 中恢复
                is_valid=metadata_row[PathletMetadataFields.IS_VALID],
                dataset=metadata_row[PathletMetadataFields.DATASET],
            )

            pathlets.append(pathlet)

        return pathlets

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
        self.cache_manager.clear_cache()

    def save_pathlets(self, pathlets: List[Pathlet], update_points: bool = False) -> None:
        """保存Pathlet数据。

        将Pathlet数据分离为元信息和点数据，分别写入Parquet文件。

        参数:
            pathlets: Pathlet列表
            update_points: 是否更新点数据，默认为False（点数据为静态数据）

        Raises:
            ValueError:
                如果pathlets列表为空

        示例:
            from traceloom.storage.pathlet_storage import PathletStorage
            from traceloom.domain.pathlet import Pathlet, BodyObservations, TailObservations, Observation

            # 初始化存储
            storage = PathletStorage()

            # 准备Pathlet数据
            pathlet1 = Pathlet(
                pathlet_id="pathlet_001",
                trace_name="trace_001",
                start_index=0,
                dataset="train",
                body=BodyObservations(),
                tail=TailObservations()
            )

            pathlet2 = Pathlet(
                pathlet_id="pathlet_002",
                trace_name="trace_002",
                start_index=100,
                dataset="train",
                body=BodyObservations(),
                tail=TailObservations()
            )

            # 保存Pathlet数据，不更新点数据
            storage.save_pathlets([pathlet1, pathlet2], update_points=False)
        """
        if not pathlets:
            raise ValueError("Pathlet数据列表为空，无法保存")

        # 保存元数据
        self.metadata_manager.save_metadata(pathlets)

        # 只有在必要时才更新点数据
        if update_points:
            self.points_manager.save_points(pathlets)
            self.cache_manager.set_points_loaded(True)
            logger.info("点数据已更新")

        # 清除缓存，确保下次读取时能获取最新数据
        self.clear_cache()

    def load_pathlets(
        self,
        state_id: Optional[int] = None,
        is_valid: Optional[bool] = None,
        dataset: Optional[str] = None,
        batch_size: Optional[int] = None,
    ) -> List[Pathlet]:
        """加载Pathlet数据。

        从Parquet文件加载元信息和点数据，合并为Pathlet列表。
        支持批量处理，减少内存使用。

        参数:
            state_id: 可选，按状态ID筛选
            is_valid: 可选，按有效性筛选
            dataset: 可选，按数据集划分筛选（如 train/test/val）
            batch_size: 可选，批量处理大小，用于减少内存使用

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

            # 加载所有有效的Pathlet
            valid_pathlets = storage.load_pathlets(is_valid=True)
            print(f"加载了 {len(valid_pathlets)} 个有效的Pathlet")

            # 加载训练集的Pathlet
            train_pathlets = storage.load_pathlets(dataset="train")
            print(f"加载了 {len(train_pathlets)} 个训练集的Pathlet")

            # 组合过滤条件
            filtered_pathlets = storage.load_pathlets(state_id=0, is_valid=True, dataset="train")
            print(f"加载了 {len(filtered_pathlets)} 个符合条件的Pathlet")

            # 使用批量处理加载大量数据
            large_pathlets = storage.load_pathlets(batch_size=1000)
            print(f"批量加载了 {len(large_pathlets)} 个Pathlet")
        """
        logger.info(f"加载径元[state_id:{state_id}, is_valid:{is_valid}, dataset:{dataset}, batch_size:{batch_size}]")

        # 生成缓存键
        cache_key = f"main_data_{state_id}_{is_valid}_{dataset}"

        # 尝试从缓存加载
        cached_metadata = self.cache_manager.get_main_data(cache_key)
        if cached_metadata is not None:
            metadata_df = cached_metadata
        else:
            # 加载元数据
            metadata_df = self.metadata_manager.load_metadata(state_id, is_valid, dataset)
            # 缓存元数据
            if not metadata_df.empty:
                self.cache_manager.set_main_data(cache_key, metadata_df)

        # 只有当有主数据时才继续处理
        if metadata_df.empty:
            logger.info("没有找到符合条件的径元")
            return []

        # 提取唯一的trace_name列表
        trace_names = metadata_df[PathletMetadataFields.TRACE_NAME].unique().tolist()

        # 尝试从缓存加载点数据
        points_cache_key = f"points_{'_'.join(trace_names[:5])}"  # 使用前5个trace_name作为缓存键
        cached_points = self.cache_manager.get_points_data(points_cache_key)

        if cached_points is not None:
            points_df = cached_points
        else:
            # 加载点数据，只加载需要的trace_name
            points_df = self.points_manager.load_points(trace_names)
            # 缓存点数据
            if not points_df.empty:
                self.cache_manager.set_points_data(points_cache_key, points_df)
            # 设置点数据加载标记
            self.cache_manager.set_points_loaded(True)

        # 如果指定了批量大小，使用批量处理
        if batch_size and batch_size > 0:
            pathlets = []
            # 分批处理元数据
            for i in range(0, len(metadata_df), batch_size):
                batch_metadata = metadata_df.iloc[i : i + batch_size]
                batch_pathlets = self._batch_process_pathlets(batch_metadata, points_df)
                pathlets.extend(batch_pathlets)
        else:
            # 一次性处理所有数据
            pathlets = self._process_pathlets(metadata_df, points_df)

        # 打印统计信息
        logger.info(f"成功加载 {len(pathlets)} 个径元")
        filter_info = []
        if state_id is not None:
            filter_info.append(f"state_id={state_id}")
        if is_valid is not None:
            filter_info.append(f"is_valid={is_valid}")
        if dataset is not None:
            filter_info.append(f"dataset={dataset}")
        if filter_info:
            logger.info(f"筛选条件: {', '.join(filter_info)}")

        # 统计状态分布
        if pathlets:
            state_counts = {}
            for pathlet in pathlets:
                state_id = pathlet.state_label.state_id if pathlet.state_label else -1
                state_counts[state_id] = state_counts.get(state_id, 0) + 1
            logger.info(f"状态分布: {state_counts}")

            # 统计时延、丢包的最大、最小、均值
            import numpy as np

            delays_up = []
            delays_down = []
            losses_up = []
            losses_down = []

            for pathlet in pathlets:
                # 从观测数据中提取时延和丢包数据
                for obs in pathlet.observations:
                    delays_up.append(obs.delay_up)
                    delays_down.append(obs.delay_down)
                    losses_up.append(obs.loss_up)
                    losses_down.append(obs.loss_down)

            # 计算统计值
            if delays_up:
                logger.info(
                    f"时延上行 - 最大值: {np.max(delays_up):.2f}ms, 最小值: {np.min(delays_up):.2f}ms, 均值: {np.mean(delays_up):.2f}ms"
                )
                logger.info(
                    f"时延下行 - 最大值: {np.max(delays_down):.2f}ms, 最小值: {np.min(delays_down):.2f}ms, 均值: {np.mean(delays_down):.2f}ms"
                )
                logger.info(
                    f"丢包上行 - 最大值: {np.max(losses_up):.4f}, 最小值: {np.min(losses_up):.4f}, 均值: {np.mean(losses_up):.4f}"
                )
                logger.info(
                    f"丢包下行 - 最大值: {np.max(losses_down):.4f}, 最小值: {np.min(losses_down):.4f}, 均值: {np.mean(losses_down):.4f}"
                )

        return pathlets

    def _process_pathlets(self, metadata_df: pd.DataFrame, points_df: pd.DataFrame) -> List[Pathlet]:
        """处理Pathlet数据

        根据元数据和点数据，构建Pathlet对象列表。

        参数:
            metadata_df: 元数据DataFrame
            points_df: 点数据DataFrame

        返回:
            List[Pathlet]: Pathlet列表
        """
        pathlets = []

        # 按径元分组点数据
        pathlet_points = {}
        if not points_df.empty:
            # 使用固定字段名
            id_column = PointDataFields.PATHLET_IDS

            for _idx, row in points_df.iterrows():
                # 直接使用 pathlet_ids 字段
                pathlet_ids = row[id_column]

                for pathlet_id in pathlet_ids:
                    if pathlet_id not in pathlet_points:
                        pathlet_points[pathlet_id] = []
                    pathlet_points[pathlet_id].append(row)
        else:
            logger.warning("点数据为空，将创建不含观测数据的 Pathlet 对象")

        # 构建 Pathlet 对象
        for _, metadata_row in metadata_df.iterrows():
            pathlet = self._build_pathlet(metadata_row, pathlet_points)
            if pathlet:
                pathlets.append(pathlet)

        return pathlets

    def _batch_process_pathlets(self, metadata_df: pd.DataFrame, points_df: pd.DataFrame) -> List[Pathlet]:
        """批量处理Pathlet数据

        根据元数据和点数据，批量构建Pathlet对象列表。

        参数:
            metadata_df: 元数据DataFrame
            points_df: 点数据DataFrame

        返回:
            List[Pathlet]: Pathlet列表
        """
        return self._process_pathlets(metadata_df, points_df)

    def _build_pathlet(self, metadata_row: pd.Series, pathlet_points: Dict[str, List[pd.Series]]) -> Optional[Pathlet]:
        """构建单个Pathlet对象

        根据元数据行和点数据，构建单个Pathlet对象。

        参数:
            metadata_row: 元数据行
            pathlet_points: 按径元ID分组的点数据

        返回:
            Optional[Pathlet]: Pathlet对象，如果构建失败则返回None
        """
        pathlet_id = metadata_row[PathletMetadataFields.PATHLET_ID]
        logger.debug(f"处理径元: {pathlet_id}")

        start_index = metadata_row[PathletMetadataFields.START_INDEX]
        trace_name = metadata_row[PathletMetadataFields.TRACE_NAME]
        dataset = metadata_row[PathletMetadataFields.DATASET]

        # 提取该径元的点数据
        pathlet_points_list = pathlet_points.get(pathlet_id, [])

        # 按 trace_index 排序
        pathlet_points_list.sort(key=lambda x: x[PointDataFields.TRACE_INDEX])

        # 构建 BodyObservations 和 TailObservations
        body_observations = []
        tail_observations = []

        # 计算预期的 trace_index 范围
        expected_trace_indices = set(range(start_index, start_index + 110))
        actual_trace_indices = set()

        for point in pathlet_points_list:
            trace_index = point[PointDataFields.TRACE_INDEX]
            actual_trace_indices.add(trace_index)

            # 计算相对索引
            relative_index = trace_index - start_index

            # 创建观测数据
            obs = Observation(
                delay_up=point[PointDataFields.DELAY_UP],
                loss_up=point[PointDataFields.LOSS_UP],
                bw_up=point[PointDataFields.BW_UP],
                delay_down=point[PointDataFields.DELAY_DOWN],
                loss_down=point[PointDataFields.LOSS_DOWN],
                bw_down=point[PointDataFields.BW_DOWN],
            )

            # 按相对索引分配到 body 或 tail
            if relative_index < 100:
                body_observations.append(obs)
            elif relative_index < 110:
                tail_observations.append(obs)

        # 验证数据完整性
        missing_indices = expected_trace_indices - actual_trace_indices
        if missing_indices:
            logger.warning(f"径元 {pathlet_id} 缺少 {len(missing_indices)} 个点数据: {sorted(missing_indices)[:5]}...")

        # 检查是否有观测数据
        total_obs = len(body_observations) + len(tail_observations)
        if total_obs == 0:
            logger.warning(f"径元 {pathlet_id} 没有观测数据，跳过")
            return None

        # 从 metadata_row 中提取 state_id
        state_id = metadata_row[PathletMetadataFields.STATE_ID]
        from traceloom.domain.state import StateLabel

        state_label = StateLabel(state_id=state_id)

        # 创建 Pathlet 对象
        try:
            pathlet = Pathlet(
                pathlet_id=pathlet_id,
                trace_name=trace_name,
                start_index=start_index,
                dataset=dataset,
                body=BodyObservations(observations=body_observations),
                tail=TailObservations(observations=tail_observations),
                state_label=state_label,  # 从 metadata_row 中恢复
                is_valid=metadata_row[PathletMetadataFields.IS_VALID],
            )
            return pathlet
        except Exception as e:
            logger.error(f"构建径元 {pathlet_id} 时出错: {e}")
            return None

    def _write_metadata(self, metadata: pd.DataFrame) -> None:
        """写入元信息到Parquet文件。

        参数:
            metadata: 元信息DataFrame
        """
        # 转换为Arrow表
        # 注意：这里不需要保存Arrow表，因为我们直接使用Pandas DataFrame

    def _write_points(self, points: pd.DataFrame) -> None:
        """写入点数据到Parquet文件。

        参数:
            points: 点数据DataFrame

        Raises:
            ValueError:
                如果points DataFrame为空
        """
        if points.empty:
            raise ValueError("点数据DataFrame为空，无法写入")

        # 确保trace_name字段是字符串类型
        if PointDataFields.TRACE_NAME in points.columns:
            # 检查并转换trace_name字段的类型
            logger.debug(
                f"写入前 points DataFrame 中 trace_name 字段的类型: {str(points[PointDataFields.TRACE_NAME].dtype)}"
            )
            # 强制转换为字符串类型
            points[PointDataFields.TRACE_NAME] = points[PointDataFields.TRACE_NAME].astype(str)
            logger.debug(
                f"写入前 points DataFrame 中 trace_name 字段转换后的类型: {str(points[PointDataFields.TRACE_NAME].dtype)}"
            )
        else:
            # 如果trace_name字段不存在，添加一个空字符串字段
            points[PointDataFields.TRACE_NAME] = ""

        # 确保trace_index列存在并排序
        if PointDataFields.TRACE_INDEX in points.columns:
            points = points.sort_values([PointDataFields.TRACE_NAME, PointDataFields.TRACE_INDEX])

        # 确保目录存在
        self.points_file.mkdir(exist_ok=True, parents=True)

        # 从schemas.py导入Schema
        from traceloom.storage.schemas import POINT_DATA_SCHEMA

        # 转换为Arrow表，使用指定的Schema
        table = pa.Table.from_pandas(points, schema=POINT_DATA_SCHEMA, preserve_index=False)

        # 使用write_to_dataset写入分区数据
        # existing_data_behavior="overwrite_or_ignore"会覆盖已存在的分区
        # basename_template指定固定的文件名模板，确保每次写入时都使用可预测的文件名
        pq.write_to_dataset(
            table,
            root_path=str(self.points_file),
            partition_cols=[PointDataFields.TRACE_NAME],
            existing_data_behavior="overwrite_or_ignore",
            compression="ZSTD",
            basename_template="data.{i}.parquet",
        )

        logger.info(f"点数据已写入到 {self.points_file}，使用按trace_name分区存储")

    def _read_main_data(self) -> pd.DataFrame:
        """从Parquet文件读取主数据（pathlets.parquet）。

        返回:
            pd.DataFrame: 主数据DataFrame
        """
        # 使用缓存
        if self._main_data_cache is not None and self._is_cache_valid("main_data"):
            self._update_cache_timestamp("main_data")
            return self._main_data_cache

        # 读取Parquet文件
        table = pq.read_table(self.main_data_file)
        df = table.to_pandas()

        # 检查缓存大小
        if len(df) <= self._cache_size_limit:
            # 缓存结果
            self._main_data_cache = df
            self._update_cache_timestamp("main_data")

        return df

    def _write_main_data(self, main_data: pd.DataFrame) -> None:
        """写入主数据到Parquet文件（pathlets.parquet）。

        参数:
            main_data: 主数据DataFrame
        """
        # 确保trace_name字段是字符串类型
        if PathletMetadataFields.TRACE_NAME in main_data.columns:
            main_data[PathletMetadataFields.TRACE_NAME] = main_data[PathletMetadataFields.TRACE_NAME].astype(str)

        # 从schemas.py导入Schema
        from traceloom.storage.schemas import PATHLET_METADATA_SCHEMA

        # 转换为Arrow表，使用指定的Schema
        table = pa.Table.from_pandas(main_data, schema=PATHLET_METADATA_SCHEMA, preserve_index=False)

        # 写入Parquet文件
        pq.write_table(table, self.main_data_file, compression="ZSTD")

    def _read_points(self) -> pd.DataFrame:
        """从Parquet文件读取点数据。

        返回:
            pd.DataFrame: 点数据DataFrame
        """
        # 使用缓存
        if self._points_cache is not None:
            # 静态数据，一旦加载就不再刷新
            return self._points_cache

        # 检查点数据是否存在
        if not self.points_file.exists():
            logger.warning(f"点数据目录不存在: {self.points_file}")
            return pd.DataFrame()

        try:
            # 使用pyarrow.dataset读取分区数据
            import pyarrow.dataset as ds

            # 创建分区 schema，明确指定trace_name为分区列
            partition_schema = pa.schema([(PointDataFields.TRACE_NAME, pa.string())])
            partitioning = ds.partitioning(schema=partition_schema)

            # 创建dataset，指定分区格式
            dataset = ds.dataset(str(self.points_file), format="parquet", partitioning=partitioning)

            # 读取所有数据到表
            table = dataset.to_table()

            # 转换为DataFrame
            df = table.to_pandas()

            # 确保trace_name字段是字符串类型
            if PointDataFields.TRACE_NAME in df.columns:
                # 强制转换为字符串类型
                df[PointDataFields.TRACE_NAME] = df[PointDataFields.TRACE_NAME].astype(str)

            # 确保pathlet_ids字段是列表类型
            if PointDataFields.PATHLET_IDS in df.columns:
                # 处理可能的类型问题
                def ensure_list(obj):
                    import numpy as np

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

            # 缓存结果（静态数据，只加载一次）
            if len(df) <= self._cache_size_limit:
                self._points_cache = df

            # 标记点数据已加载
            self._points_loaded = True

            logger.info(f"成功读取点数据，共 {len(df)} 行")
            return df
        except Exception as e:
            logger.warning(f"读取点数据时出错: {e}")
            import traceback

            logger.warning(f"错误堆栈: {traceback.format_exc()}")
            return pd.DataFrame()

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
        return self.metadata_manager.get_pathlet_count()

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
        return self.metadata_manager.get_state_distribution()

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
        return self.points_manager.load_pathlet_points(pathlet_id)

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

        # 检查元数据文件是否存在
        if not self.metadata_manager.metadata_file.exists():
            logger.warning(f"Pathlet元数据文件不存在: {self.pathlet_dir}")
            return None

        # 读取元数据
        metadata_df = self.metadata_manager.load_metadata()
        if metadata_df is None or metadata_df.empty:
            logger.warning(f"Pathlet元数据文件为空: {self.pathlet_dir}")
            return None

        metadata_row = metadata_df[metadata_df[PathletMetadataFields.PATHLET_ID] == pathlet_id]

        if metadata_row.empty:
            logger.warning(f"没有找到径元 {pathlet_id} 的元信息")
            return None

        # 读取点数据
        points_df = self.load_pathlet_points(pathlet_id)
        if points_df is None:
            logger.warning(f"没有找到径元 {pathlet_id} 的点数据")
            return None

        # 获取起始索引
        start_index = int(metadata_row[PathletMetadataFields.START_INDEX].iloc[0])

        # 分离上下文点和延续点
        # 计算相对索引：trace_index - start_index
        ctx_points = points_df[points_df[PointDataFields.TRACE_INDEX].apply(lambda x: (x - start_index) < 100)]
        cont_points = points_df[points_df[PointDataFields.TRACE_INDEX].apply(lambda x: 100 <= (x - start_index) < 110)]

        # 构建BodyObservations
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
        ctx_10s = BodyObservations(observations=body_observations)

        # 构建TailObservations
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
        cont_1s = TailObservations(observations=tail_observations)

        # 计算PathletStatistics
        ctx_values = PathletStatistics(
            delay_up_mean=ctx_points[PointDataFields.DELAY_UP].mean(),
            delay_up_std=ctx_points[PointDataFields.DELAY_UP].std(),
            delay_down_mean=ctx_points[PointDataFields.DELAY_DOWN].mean(),
            delay_down_std=ctx_points[PointDataFields.DELAY_DOWN].std(),
            loss_up_mean=ctx_points[PointDataFields.LOSS_UP].mean(),
            loss_up_max=ctx_points[PointDataFields.LOSS_UP].max(),
            loss_down_mean=ctx_points[PointDataFields.LOSS_DOWN].mean(),
            loss_down_max=ctx_points[PointDataFields.LOSS_DOWN].max(),
            bw_up_mean=ctx_points[PointDataFields.BW_UP].mean(),
            bw_up_max=ctx_points[PointDataFields.BW_UP].max(),
            bw_down_mean=ctx_points[PointDataFields.BW_DOWN].mean(),
            bw_down_max=ctx_points[PointDataFields.BW_DOWN].max(),
        )

        # 构建返回数据
        trace_name = metadata_row[PathletMetadataFields.TRACE_NAME].iloc[0]

        return {
            "trace_name": trace_name,
            "start_index": start_index,
            "ctx_10s": ctx_10s,
            "cont_1s": cont_1s,
            "ctx_values": ctx_values,
            "is_valid": bool(metadata_row[PathletMetadataFields.IS_VALID].iloc[0]),
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
        return self.points_manager.reconstruct_profile(pathlet_points, start_index)

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

        if self.main_data_file.exists():
            self.main_data_file.unlink()
            logger.debug(f"已删除主数据文件: {self.main_data_file}")

        if self.points_file.exists():
            import shutil

            shutil.rmtree(self.points_file)
            logger.debug(f"已删除点数据目录: {self.points_file}")

        if self.gmm_model_file.exists():
            self.gmm_model_file.unlink()
            logger.debug(f"已删除GMM模型文件: {self.gmm_model_file}")

        if self.state_mapping_file.exists():
            self.state_mapping_file.unlink()
            logger.debug(f"已删除状态映射文件: {self.state_mapping_file}")

        # 重置静态数据加载标记
        self._points_loaded = False

        logger.debug(f"已清空Pathlet数据目录: {self.pathlet_dir}")

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
        logger.debug(f"GMM模型已保存到: {self.gmm_model_file}")

        # 保存状态映射
        import json

        with open(self.state_mapping_file, "w", encoding="utf-8") as f:
            json.dump(state_mapping, f, ensure_ascii=False, indent=2)
        logger.debug(f"状态映射已保存到: {self.state_mapping_file}")

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
        logger.debug(f"GMM模型已从: {self.gmm_model_file} 加载")
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
