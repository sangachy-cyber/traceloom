# -*- coding: utf-8 -*-
"""存储适配器模块

负责 Pathlet 对象与存储结构之间的双向转换，实现数据的去重和优化存储。
"""

from typing import Dict, List, Tuple

import pandas as pd

from traceloom.domain.pathlet import BodyObservations, Observation, Pathlet, TailObservations


class PathletStorageAdapter:
    """Pathlet 存储适配器

    负责 Pathlet 对象与存储结构之间的双向转换，实现数据的去重和优化存储。

    Examples:
        # 创建存储适配器
        adapter = PathletStorageAdapter()

        # 将 Pathlet 对象转换为存储结构
        metadata_df, points_df = adapter.pathlets_to_storage(pathlets)

        # 将存储结构转换为 Pathlet 对象
        pathlets = adapter.storage_to_pathlets(metadata_df, points_df)
    """

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
            trace_name = pathlet.trace_name
            start_index = pathlet.start_index
            state_id = getattr(pathlet, 'state_id', -1)

            # 提取元数据
            metadata.append(
                {
                    "pathlet_id": pathlet.pathlet_id,
                    "is_valid": pathlet.is_valid,
                    "state_id": state_id,
                    "trace_name": trace_name,
                    "start_index": start_index,
                }
            )

            # 提取点数据（去重处理）
            for i, obs in enumerate(pathlet.observations):
                trace_index = start_index + i
                key = (trace_name, trace_index)

                if key not in unique_points:
                    # 新观测点
                    unique_points[key] = {
                        "trace_name": trace_name,
                        "trace_index": trace_index,
                        "containing_pathlet_ids": [pathlet.pathlet_id],
                        "delay_up": obs.delay_up,
                        "loss_up": obs.loss_up,
                        "bw_up": obs.bw_up,
                        "delay_down": obs.delay_down,
                        "loss_down": obs.loss_down,
                        "bw_down": obs.bw_down,
                    }
                else:
                    # 已有观测点，添加径元ID
                    if pathlet.pathlet_id not in unique_points[key]["containing_pathlet_ids"]:
                        unique_points[key]["containing_pathlet_ids"].append(pathlet.pathlet_id)

        return pd.DataFrame(metadata), pd.DataFrame(list(unique_points.values()))

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
        points_by_pathlet = {}
        # 兼容旧的字段名
        id_column = "containing_pathlet_ids" if "containing_pathlet_ids" in points_df.columns else "pathlet_ids"

        for _, row in points_df.iterrows():
            for pathlet_id in row[id_column]:
                if pathlet_id not in points_by_pathlet:
                    points_by_pathlet[pathlet_id] = []
                points_by_pathlet[pathlet_id].append(row)

        # 构建 Pathlet 对象
        for _, metadata_row in metadata_df.iterrows():
            pathlet_id = metadata_row["pathlet_id"]
            start_index = metadata_row["start_index"]

            # 提取该径元的点数据
            pathlet_points = points_by_pathlet.get(pathlet_id, [])

            # 按 trace_index 排序
            pathlet_points.sort(key=lambda x: x["trace_index"])

            # 构建 BodyObservations 和 TailObservations
            body_observations = []
            tail_observations = []

            for point in pathlet_points:
                relative_index = point["trace_index"] - start_index
                obs = Observation(
                    delay_up=point["delay_up"],
                    loss_up=point["loss_up"],
                    bw_up=point["bw_up"],
                    delay_down=point["delay_down"],
                    loss_down=point["loss_down"],
                    bw_down=point["bw_down"],
                )

                if relative_index < 100:
                    body_observations.append(obs)
                elif relative_index < 110:
                    tail_observations.append(obs)

            # 创建 Pathlet 对象
            pathlet = Pathlet(
                pathlet_id=pathlet_id,
                trace_name=metadata_row.get("trace_name", ""),
                start_index=start_index,
                body=BodyObservations(observations=body_observations),
                tail=TailObservations(observations=tail_observations),
                state_label=None,  # 可以根据需要从 metadata_row 中恢复
                is_valid=metadata_row.get("is_valid", True),
            )

            pathlets.append(pathlet)

        return pathlets
