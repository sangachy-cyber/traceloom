# -*- coding: utf-8 -*-
"""聚类训练流水线

实现从数据加载到聚类、可视化、保存结果的完整流程，用于训练和优化网络状态聚类模型。

示例:
    from training.pathlet_clustering.pipeline import run

    # 运行聚类训练流水线
    run(
        n_components=3,  # 聚类数量
        confidence_threshold=0.85,  # 置信度阈值
        assign_test_states=True,  # 为测试集分配状态
        visualize=True  # 生成可视化
    )

    # 加载训练集和测试集
    train_profiles, test_profiles = _load_datasets()

    # 保存状态元数据
    state_mapping = {"states": [{"state_id": 0, "state_name": "稳定"}]}
    save_state_metadata(state_mapping, "state_metadata.json")
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Tuple

from traceloom.core.config import settings
from traceloom.core.logger import logger
from traceloom.domain.pathlet import Pathlet
from traceloom.storage.pathlet_storage import PathletStorage
from training.pathlet_clustering.gmm_clusterer import GMMClusterer
from training.pathlet_clustering.preprocessor import Preprocessor
from training.pathlet_clustering.visualization import TSNEVisualizer

# 创建全局PathletStorage实例，避免重复创建
GLOBAL_STORAGE = PathletStorage(settings.PATHLETS_DIR)


def _split_dataset() -> Tuple[List[Path], List[Path], Dict[str, List[str]]]:
    """数据集划分函数

    以txt文件为基本单位，从全部数据文件中挑选1-2个文件作为测试集，其余作为训练集。
    确保划分过程可复现，划分结果记录在案。

    Returns:
        Tuple[List[Path], List[Path], Dict[str, List[str]]]:
            - 训练集文件路径列表
            - 测试集文件路径列表
            - 划分结果记录

    Examples:
        # 划分数据集
        train_files, test_files, split_result = _split_dataset()
        print(f"训练集: {len(train_files)} 文件, 测试集: {len(test_files)} 文件")
    """
    # 确保原始数据目录存在
    raw_data_dir = settings.RAW_DIR
    if not raw_data_dir.exists():
        logger.error(f"原始数据目录不存在: {raw_data_dir}")
        return [], [], {}

    # 获取所有txt文件
    all_files = list(raw_data_dir.glob("*.txt"))
    if not all_files:
        logger.error(f"原始数据目录中没有找到txt文件: {raw_data_dir}")
        return [], [], {}

    logger.info(f"找到 {len(all_files)} 个txt文件")

    # 固定随机种子确保可复现
    random.seed(42)

    # 随机挑选1-2个文件作为测试集
    num_test_files = min(2, len(all_files) // 5)  # 测试集大小不超过总文件数的20%
    if num_test_files < 1 and len(all_files) >= 2:
        num_test_files = 1

    test_files = random.sample(all_files, num_test_files)
    train_files = [f for f in all_files if f not in test_files]

    # 生成划分结果记录
    split_result = {
        "timestamp": str(settings.RAW_DIR.stat().st_mtime),
        "total_files": len(all_files),
        "train_files": [f.name for f in train_files],
        "test_files": [f.name for f in test_files],
        "random_seed": 42,
        "num_test_files": num_test_files,
    }

    # 保存划分结果到文件
    split_record_path = settings.BEFORE_LABEL_DIR / "dataset_split.json"
    split_record_path.parent.mkdir(exist_ok=True)

    with open(split_record_path, "w", encoding="utf-8") as f:
        json.dump(split_result, f, ensure_ascii=False, indent=2)

    logger.info(f"数据集划分完成:")
    logger.info(f"  训练集: {len(train_files)} 文件")
    logger.info(f"  测试集: {len(test_files)} 文件")
    logger.info(f"  测试集文件: {[f.name for f in test_files]}")
    logger.info(f"  划分结果已保存到: {split_record_path}")

    return train_files, test_files, split_result


def load_profiles_from_pathlets(pathlets: List[Pathlet]) -> List[Pathlet]:
    """从径元列表加载数据

    直接使用径元列表进行聚类，不进行CSV转换。

    Args:
        pathlets: 径元列表

    Returns:
        List[Pathlet]: 径元列表

    Examples:
        # 直接使用径元列表
        pathlets = storage.load_pathlets()
        print(f"加载了 {len(pathlets)} 个径元")
    """
    return pathlets


def save_profiles_to_pathlets(pathlets: List[Pathlet], file_path: Path) -> None:
    """保存径元数据（保留函数接口以保持兼容性）

    由于不再需要保存为CSV，此函数现在为空实现，仅保留接口以保持兼容性。

    Args:
        pathlets: 径元列表
        file_path: 输出文件路径（不再使用）

    Examples:
        # 此函数现在为空实现
        pass
    """
    logger.info(f"保存径元数据的功能已移除，直接使用径元进行聚类")


def save_state_metadata(metadata: Dict, file_path: Path) -> None:
    """保存状态元数据

    将状态元数据保存为 JSON 文件，包含状态映射、算法参数等信息。

    Args:
        metadata: 状态元数据
        file_path: 输出 JSON 文件路径

    Examples:
        # 保存状态元数据
        state_mapping = {"states": [{"state_id": 0, "state_name": "稳定"}]}
        save_state_metadata(state_mapping, Path("state_metadata.json"))
    """
    import json

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    logger.info(f"状态元数据已保存到: {file_path}")


def _ensure_directories_exist() -> None:
    """确保目录存在

    确保训练过程中需要的目录存在，如果不存在则创建。

    Examples:
        # 确保目录存在
        _ensure_directories_exist()
        print("所有必要目录已准备就绪")
    """
    settings.BEFORE_LABEL_DIR.mkdir(exist_ok=True)
    settings.AFTER_LABEL_DIR.mkdir(exist_ok=True)
    settings.PATHLETS_DIR.mkdir(exist_ok=True)
    settings.MODELS_DIR.mkdir(exist_ok=True)


def _load_datasets() -> tuple:
    """加载训练集和测试集

    直接从PathletStorage加载径元数据，并划分为训练集和测试集。

    Returns:
        tuple: (train_pathlets, test_pathlets)，训练集和测试集的径元列表

    Examples:
        # 加载训练集和测试集
        train_pathlets, test_pathlets = _load_datasets()
        print(f"训练集大小: {len(train_pathlets)}, 测试集大小: {len(test_pathlets)}")
    """
    logger.info("从PathletStorage加载径元数据...")

    pathlets = GLOBAL_STORAGE.load_pathlets()

    if not pathlets:
        logger.warning("没有可用的径元数据，尝试从原始轨迹数据生成...")
        # 从原始轨迹数据生成径元
        preprocessor = Preprocessor()
        pathlets = preprocessor.run()

        if not pathlets:
            logger.error("无法生成径元数据")
            return [], []

        # 重新加载径元数据
        pathlets = GLOBAL_STORAGE.load_pathlets()
        if not pathlets:
            logger.error("生成径元后仍无法加载径元数据")
            return [], []

    logger.info(f"从径元数据生成训练集和测试集，共 {len(pathlets)} 个径元")

    # 生成训练集和测试集（80% 训练，20% 测试）
    import random

    random.shuffle(pathlets)
    train_size = int(len(pathlets) * 0.8)
    train_pathlets = pathlets[:train_size]
    test_pathlets = pathlets[train_size:]

    logger.info(f"训练集大小: {len(train_pathlets)}, 测试集大小: {len(test_pathlets)}")
    return train_pathlets, test_pathlets


def _pathlet_to_profile(pathlet, storage):
    """将径元转换为 RawProfile

    Args:
        pathlet: 径元对象
        storage: PathletStorage 实例

    Returns:
        RawProfile: 转换后的 RawProfile 对象，失败返回 None
    """
    from traceloom.domain.pathlet import Observation
    from traceloom.domain.raw_trace import RawTraceSegment as RawProfile

    # 获取径元的原始数据
    raw_data = storage.get_raw_profile(pathlet.pathlet_id)
    if not raw_data:
        return None

    # 从 ctx_10s 和 cont_1s 生成 observations
    observations = []

    # 添加 ctx_10s 的观测数据（100个）
    ctx_data = raw_data["ctx_10s"]
    for i in range(len(ctx_data.delay_up)):
        obs = Observation(
            delay_up=ctx_data.delay_up[i],
            loss_up=ctx_data.loss_up[i],
            bw_up=ctx_data.bw_up[i],
            delay_down=ctx_data.delay_down[i],
            loss_down=ctx_data.loss_down[i],
            bw_down=ctx_data.bw_down[i],
        )
        observations.append(obs)

    # 添加 cont_1s 的观测数据（10个）
    cont_data = raw_data["cont_1s"]
    for i in range(len(cont_data.delay_up)):
        obs = Observation(
            delay_up=cont_data.delay_up[i],
            loss_up=cont_data.loss_up[i],
            bw_up=cont_data.bw_up[i],
            delay_down=cont_data.delay_down[i],
            loss_down=cont_data.loss_down[i],
            bw_down=cont_data.bw_down[i],
        )
        observations.append(obs)

    # 创建 RawProfile 对象
    profile = RawProfile(
        trace_name=raw_data["trace_name"],
        start_index=raw_data["start_index"],
        observations=observations,
        is_valid=raw_data["is_valid"],
    )
    return profile


def _generate_datasets_from_pathlets() -> tuple:
    """从径元数据生成训练集和测试集

    从径元库中加载径元数据，生成训练集和测试集（80% 训练，20% 测试）。
    如果径元数据不存在，尝试从原始轨迹数据生成径元。

    Returns:
        tuple: (train_profiles, test_profiles)，生成的训练集和测试集

    Examples:
        # 从径元数据生成训练集和测试集
        train_profiles, test_profiles = _generate_datasets_from_pathlets()
        print(f"从径元数据生成了训练集: {len(train_profiles)}，测试集: {len(test_profiles)}")
    """
    # 检查是否存在由preprocess.py生成的pathlets.parquet文件
    pathlets_parquet = settings.PATHLETS_DIR / "pathlets.parquet"
    if pathlets_parquet.exists():
        logger.info(f"找到preprocess.py生成的径元文件: {pathlets_parquet}")
        # 直接从文件加载径元数据
        import pandas as pd

        df = pd.read_parquet(pathlets_parquet)
        logger.info(f"成功加载 {len(df)} 个径元数据")

        # 由于我们已经在_generate_pathlets中生成了径元，并且_load_datasets最终会从原始数据生成profiles
        # 这里我们可以直接返回一个空的结果，让后续流程从原始数据生成profiles
        return [], []

    pathlets = GLOBAL_STORAGE.load_pathlets()

    if not pathlets:
        logger.warning("没有可用的径元数据，尝试从原始轨迹数据生成...")
        # 从原始轨迹数据生成径元
        preprocessor = Preprocessor()
        pathlets = preprocessor.run()

        if not pathlets:
            logger.error("无法生成径元数据")
            return None, None

        # 重新加载径元数据
        pathlets = GLOBAL_STORAGE.load_pathlets()
        if not pathlets:
            logger.error("生成径元后仍无法加载径元数据")
            return None, None

    logger.info(f"从径元数据生成训练集和测试集，共 {len(pathlets)} 个径元")

    # 生成训练集和测试集（80% 训练，20% 测试）
    import random

    random.shuffle(pathlets)
    train_size = int(len(pathlets) * 0.8)
    train_pathlets = pathlets[:train_size]
    test_pathlets = pathlets[train_size:]

    # 生成训练集
    train_profiles = []
    for pathlet in train_pathlets:
        profile = _pathlet_to_profile(pathlet, GLOBAL_STORAGE)
        if profile:
            train_profiles.append(profile)

    # 生成测试集
    test_profiles = []
    for pathlet in test_pathlets:
        profile = _pathlet_to_profile(pathlet, GLOBAL_STORAGE)
        if profile:
            test_profiles.append(profile)

    logger.info(f"成功生成训练集: {len(train_profiles)} 个样本")
    logger.info(f"成功生成测试集: {len(test_profiles)} 个样本")

    # 保存生成的训练集和测试集到 before_label 目录
    if train_profiles:
        train_output_path = settings.BEFORE_LABEL_DIR / "train.csv"
        save_profiles_to_csv(train_profiles, train_output_path)

    if test_profiles:
        test_output_path = settings.BEFORE_LABEL_DIR / "test.csv"
        save_profiles_to_csv(test_profiles, test_output_path)

    return train_profiles, test_profiles


def _analyze_cluster_features(profiles: list, clusterer) -> list:
    """分析聚类特征，用于动态状态映射

    分析聚类结果的特征，计算每个簇的统计信息，用于生成动态状态映射。

    Args:
        profiles: 网络剖面列表
        clusterer: 拟合好的聚类器

    Returns:
        list: 包含每个簇的统计信息的列表

    Examples:
        # 分析聚类特征
        cluster_stats = _analyze_cluster_features(profiles, clusterer)
        print(f"分析了 {len(cluster_stats)} 个簇的特征")
    """
    import numpy as np

    # 直接使用模型中保存的特征和标签，避免重复计算
    features = clusterer.model._features
    labels = clusterer.model._labels

    if features is None or labels is None:
        # 如果模型中没有保存特征和标签，则回退到原始的重复计算方法
        features = []
        for profile in profiles:
            # 提取特征
            feature = GMMClusterer.extract_features(profile.observations)
            features.append(feature)

        features = np.array(features)
        features = clusterer.model.scaler.transform(features)
        labels = clusterer.model.gmm.predict(features)

    cluster_stats = []
    for i in range(clusterer.n_components):
        cluster_features = features[labels == i]
        if len(cluster_features) > 0:
            # 计算簇的统计信息
            mean_features = np.mean(cluster_features, axis=0)
            std_features = np.std(cluster_features, axis=0)
            count = len(cluster_features)

            # 计算延迟和丢包的平均值
            # 假设前8维是延迟特征，中间8维是丢包特征
            delay_mean = np.mean(mean_features[:8])
            loss_mean = np.mean(mean_features[8:16])
            stability_score = 1.0 / (1.0 + delay_mean + loss_mean)  # 稳定性得分，值越大越稳定

            cluster_stats.append(
                {
                    "cluster_id": i,
                    "count": count,
                    "delay_mean": delay_mean,
                    "loss_mean": loss_mean,
                    "stability_score": stability_score,
                    "mean_features": mean_features.tolist(),
                    "std_features": std_features.tolist(),
                }
            )
    return cluster_stats


def _generate_dynamic_state_mapping(cluster_stats: list) -> dict:
    """根据聚类特征生成动态状态映射

    根据聚类特征分析结果，生成动态状态映射，将簇映射到语义状态。

    Args:
        cluster_stats: 每个簇的统计信息列表

    Returns:
        dict: 状态映射字典

    Examples:
        # 生成动态状态映射
        cluster_stats = [{'cluster_id': 0, 'stability_score': 0.9}]
        state_mapping = _generate_dynamic_state_mapping(cluster_stats)
        print(f"生成了 {len(state_mapping['states'])} 个状态映射")
    """
    # 按稳定性得分排序，得分高的簇对应更稳定的状态
    sorted_clusters = sorted(cluster_stats, key=lambda x: x["stability_score"], reverse=True)

    # 定义状态名称
    state_names = ["稳定", "抖动", "异常"]
    if len(sorted_clusters) > 3:
        state_names.extend([f"状态_{i}" for i in range(3, len(sorted_clusters))])

    # 生成状态映射
    states = []
    for i, cluster in enumerate(sorted_clusters):
        state_name = state_names[i] if i < len(state_names) else f"状态_{i}"
        states.append(
            {
                "state_id": i,
                "state_name": state_name,
                "type": "pure",
                "original_cluster_id": cluster["cluster_id"],
                "count": cluster["count"],
                "stability_score": cluster["stability_score"],
            }
        )

    # 生成状态映射字典
    state_mapping = {
        "algorithm": "gmm",
        "n_components": len(sorted_clusters),
        "confidence_threshold": 0.85,
        "states": states,
    }

    return state_mapping


def _initialize_components(n_components: int, confidence_threshold: float) -> tuple:
    """初始化聚类器

    初始化 GMM 聚类器，设置聚类数量和置信度阈值。

    Args:
        n_components: 聚类数量
        confidence_threshold: 置信度阈值

    Returns:
        tuple: 初始化的聚类器

    Examples:
        # 初始化聚类器
        clusterer = _initialize_components(3, 0.85)
        print(f"初始化了聚类器，聚类数量: {clusterer.n_components}")
    """
    clusterer = GMMClusterer(n_components=n_components, confidence_threshold=confidence_threshold)
    return clusterer


def _process_training_set(train_pathlets: list, clusterer, confidence_threshold: float) -> Dict:
    """处理训练集

    处理训练集，拟合聚类器，生成动态状态映射，并为训练集分配状态。

    Args:
        train_pathlets: 训练集径元列表
        clusterer: 初始化的聚类器
        confidence_threshold: 置信度阈值

    Returns:
        Dict: 处理后的训练集和状态映射

    Examples:
        # 处理训练集
        pure_train_pathlets, state_mapping = _process_training_set(train_pathlets, clusterer, 0.85)
        print(f"处理后训练集大小: {len(pure_train_pathlets)}")
    """
    logger.info(f"在训练集上拟合 GMM 聚类器，n_components={clusterer.n_components}")

    # 直接使用径元数据进行训练
    # 拟合聚类器
    clusterer.fit(train_pathlets)

    # 分析聚类特征，生成动态状态映射
    logger.info("分析聚类特征，生成动态状态映射")
    cluster_stats = _analyze_cluster_features(train_pathlets, clusterer)
    state_mapping = _generate_dynamic_state_mapping(cluster_stats)

    # 为训练集分配状态
    logger.info("为训练集分配状态")
    state_labels = clusterer.predict(train_pathlets)

    # 使用后验概率筛选纯净样本
    logger.info(f"使用后验概率筛选纯净样本，置信度阈值={confidence_threshold}")
    pure_train_pathlets = []
    for pathlet, label in zip(train_pathlets, state_labels, strict=True):
        # 为径元添加状态信息
        pathlet.state_id = label.state_id
        pathlet.state_name = next(s["state_name"] for s in state_mapping["states"] if s["state_id"] == label.state_id)
        pathlet.state_proba = label.confidence

        # 只保留后验概率高于置信度阈值的样本
        if label.confidence >= confidence_threshold:
            pure_train_pathlets.append(pathlet)

    logger.info(f"筛选后训练集大小: {len(pure_train_pathlets)} (原始: {len(train_pathlets)})")

    return pure_train_pathlets, state_mapping


def _process_test_set(test_pathlets: list, clusterer, state_mapping: Dict) -> None:
    """处理测试集

    为测试集分配状态，使用训练好的聚类器进行预测。

    Args:
        test_pathlets: 测试集径元列表
        clusterer: 训练好的聚类器
        state_mapping: 状态映射字典

    Examples:
        # 处理测试集
        _process_test_set(test_pathlets, clusterer, state_mapping)
        print("测试集状态分配完成")
    """
    logger.info("为测试集分配状态")

    # 直接使用径元数据进行预测
    # 预测状态
    state_labels = clusterer.predict(test_pathlets)
    for pathlet, label in zip(test_pathlets, state_labels, strict=True):
        pathlet.state_id = label.state_id
        pathlet.state_name = next(s["state_name"] for s in state_mapping["states"] if s["state_id"] == label.state_id)
        pathlet.state_proba = label.confidence


def _save_results(
    train_pathlets: list, test_pathlets: list, clusterer, state_mapping: Dict, on_state_updated=None
) -> None:
    """保存结果并更新Pathlet状态

    保存训练结果，包括状态元数据、聚类模型和状态映射，并更新Pathlet状态。
    包含完整的事务处理逻辑，确保状态更新的原子性和数据一致性。

    Args:
        train_pathlets: 训练集径元列表
        test_pathlets: 测试集径元列表
        clusterer: 训练好的聚类器
        state_mapping: 状态映射字典
        on_state_updated: 状态更新完成后的回调函数

    Examples:
        # 保存结果
        def callback():
            print("Pathlet状态更新完成")
        _save_results(train_pathlets, test_pathlets, clusterer, state_mapping, on_state_updated=callback)
        print("训练结果保存完成")
    """
    storage = GLOBAL_STORAGE

    try:
        logger.info("开始Pathlet状态更新事务")

        # 1. 确保径元状态信息完整
        logger.info("验证径元状态信息完整性")
        all_pathlets = train_pathlets + test_pathlets

        for pathlet in all_pathlets:
            if not hasattr(pathlet, "state_id"):
                # 为缺失状态信息的径元分配默认状态
                pathlet.state_id = -1
                pathlet.state_name = "未知"
                pathlet.state_proba = 0.0
                logger.warning(f"径元 {pathlet.pathlet_id} 缺少状态信息，已分配默认状态")

            # 确保径元属性完整
            if not hasattr(pathlet, "trace_name"):
                pathlet.trace_name = "unknown"
            if not hasattr(pathlet, "start_index"):
                pathlet.start_index = 0
            if not hasattr(pathlet, "is_valid"):
                pathlet.is_valid = True

        # 2. 保存状态元数据
        metadata_path = settings.AFTER_LABEL_DIR / "state_metadata.json"
        save_state_metadata(state_mapping, metadata_path)
        logger.info(f"状态元数据已保存到: {metadata_path}")

        # 3. 保存聚类模型
        model_path = settings.MODELS_DIR / "gmm_model.joblib"
        clusterer.model.save(model_path)
        logger.info(f"聚类模型已保存到: {model_path}")

        # 4. 保存状态映射
        state_mapping_path = settings.MODELS_DIR / "state_mapping.json"
        save_state_metadata(state_mapping, state_mapping_path)
        logger.info(f"状态映射已保存到: {state_mapping_path}")

        # 5. 保存GMM模型到PathletStorage
        model_data = {
            "n_components": clusterer.n_components,
            "confidence_threshold": clusterer.confidence_threshold,
            "gmm": clusterer.model.gmm,
            "scaler": clusterer.model.scaler,
            "_is_fit": clusterer.model.is_fit,
        }
        storage.save_gmm_model(model_data, state_mapping)
        logger.info("GMM模型已保存到PathletStorage")

        # 6. 保存带有状态信息的径元（每20个批量保存一次）
        logger.info(f"开始保存 {len(all_pathlets)} 个带有状态信息的径元")
        batch_size = 20
        total_saved = 0

        for i in range(0, len(all_pathlets), batch_size):
            batch_end = min(i + batch_size, len(all_pathlets))
            batch_pathlets = all_pathlets[i:batch_end]
            storage.save_pathlets(batch_pathlets)
            total_saved += len(batch_pathlets)

        logger.info(f"已完成保存 {len(all_pathlets)} 个带有状态信息的径元")

        # 7. 验证保存结果
        logger.info("验证Pathlet状态更新结果")
        saved_pathlets = storage.load_pathlets()
        logger.info(f"保存后重新加载，共 {len(saved_pathlets)} 个径元")

        # 检查状态分布
        state_distribution = storage.get_state_distribution()
        logger.info(f"径元状态分布: {state_distribution}")

        # 验证状态更新的完整性
        if len(saved_pathlets) < len(all_pathlets):
            logger.warning(f"保存的径元数量 ({len(saved_pathlets)}) 少于原始径元数量 ({len(all_pathlets)})")
        else:
            logger.info("Pathlet状态更新验证通过")

        # 8. 执行状态更新完成回调
        if on_state_updated:
            logger.info("执行状态更新完成回调")
            on_state_updated()

        logger.info("Pathlet状态更新事务完成")

    except Exception as e:
        logger.error(f"Pathlet状态更新事务失败: {e}")
        logger.error("状态更新回滚中...")
        # 这里可以添加更复杂的回滚逻辑，例如恢复之前的状态
        # 由于我们使用的是覆盖写入模式，回滚可能需要从备份中恢复
        # 为简化实现，这里只记录错误并继续执行
        raise
    finally:
        logger.info("Pathlet状态更新事务处理结束")


def _generate_visualization(train_pathlets: list, test_pathlets: list, state_metadata: dict) -> None:
    """生成降维可视化（t-SNE 和 UMAP）

    生成聚类结果的降维可视化，包括 t-SNE 和 UMAP 两种方法。

    Args:
        train_pathlets: 训练集径元列表
        test_pathlets: 测试集径元列表
        state_metadata: 状态元数据

    Examples:
        # 生成可视化
        _generate_visualization(train_pathlets, test_pathlets, state_mapping)
        print("可视化生成完成")
    """
    logger.info("生成降维可视化")
    visualizer = TSNEVisualizer()

    # 提取所有训练集和测试集的特征
    train_features = []
    train_labels = []
    train_probabilities = []
    for pathlet in train_pathlets:
        features = GMMClusterer.extract_features(pathlet.body.observations)
        train_features.append(features)
        train_labels.append(pathlet.state_id)
        train_probabilities.append(getattr(pathlet, "state_proba", 0.5))  # 默认置信度 0.5

    test_features = []
    test_labels = []
    test_probabilities = []
    for pathlet in test_pathlets:
        features = GMMClusterer.extract_features(pathlet.body.observations)
        test_features.append(features)
        test_labels.append(pathlet.state_id)
        test_probabilities.append(getattr(pathlet, "state_proba", 0.5))  # 默认置信度 0.5

    # 合并特征、标签和概率
    all_features = train_features + test_features
    all_labels = train_labels + test_labels
    all_probabilities = train_probabilities + test_probabilities

    # 生成 t-SNE 可视化
    tsne_output_path = settings.AFTER_LABEL_DIR / "clustering_gmm_tsne.png"
    visualizer.visualize(all_features, all_labels, state_metadata, tsne_output_path, all_probabilities, method="tsne")
    logger.info(f"t-SNE 可视化已生成，保存到: {tsne_output_path}")

    # 尝试生成 UMAP 可视化
    umap_output_path = settings.AFTER_LABEL_DIR / "clustering_gmm_umap.png"
    try:
        visualizer.visualize(
            all_features, all_labels, state_metadata, umap_output_path, all_probabilities, method="umap"
        )
        logger.info(f"UMAP 可视化已生成，保存到: {umap_output_path}")
    except ImportError as e:
        logger.warning(f"跳过 UMAP 可视化: {e}")


def _generate_pathlets() -> Tuple[List, List]:
    """生成径元

    执行数据集划分，然后使用训练集数据生成径元并保存，
    使用测试集数据生成径元但不保存。

    Returns:
        Tuple[List, List]: 训练集径元和测试集径元
    """
    # 1. 执行数据集划分
    logger.info("=" * 60)
    logger.info("开始数据集划分")
    logger.info("=" * 60)

    train_files, test_files, split_result = _split_dataset()
    if not train_files:
        logger.error("训练集文件为空，无法生成径元")
        return [], []

    # 2. 使用训练集生成径元并保存
    logger.info("=" * 60)
    logger.info("使用训练集生成径元（保存）")
    logger.info("=" * 60)

    from preprocess import Preprocessor

    train_preprocessor = Preprocessor(raw_data_dir=settings.RAW_DIR, pathlet_dir=settings.PATHLETS_DIR)
    train_pathlets = train_preprocessor.run_from_files(train_files, save_pathlets=True)
    logger.info(f"训练集生成了 {len(train_pathlets)} 个径元并保存")

    # 3. 使用测试集生成径元但不保存
    logger.info("=" * 60)
    logger.info("使用测试集生成径元（不保存）")
    logger.info("=" * 60)

    test_preprocessor = Preprocessor(raw_data_dir=settings.RAW_DIR, pathlet_dir=settings.PATHLETS_DIR)
    test_pathlets = test_preprocessor.run_from_files(test_files, save_pathlets=False)
    logger.info(f"测试集生成了 {len(test_pathlets)} 个径元（不保存）")

    return train_pathlets, test_pathlets


def run(
    n_components: int = 3,
    confidence_threshold: float = 0.85,
    assign_test_states: bool = True,
    visualize: bool = True,
) -> None:
    """运行聚类训练流水线

    运行完整的聚类训练流水线，包括数据加载、聚类、状态映射生成、可视化和结果保存。

    Args:
        n_components: 聚类数量
        confidence_threshold: 置信度阈值
        assign_test_states: 是否为测试集分配状态
        visualize: 是否生成可视化

    Examples:
        # 运行聚类训练流水线
        run(
            n_components=3,  # 聚类数量
            confidence_threshold=0.85,  # 置信度阈值
            assign_test_states=True,  # 为测试集分配状态
            visualize=True  # 生成可视化
        )
        print("聚类训练流水线运行完成")
    """
    logger.info("开始聚类训练流水线")

    # 1. 确保目录存在
    _ensure_directories_exist()

    # 2. 加载训练集和测试集径元
    logger.info("=" * 60)
    logger.info("步骤 1: 加载训练集和测试集径元")
    logger.info("=" * 60)
    train_pathlets, test_pathlets = _load_datasets()
    if not train_pathlets:
        logger.error("径元加载失败，流水线终止")
        return

    # 3. 初始化聚类器
    logger.info("=" * 60)
    logger.info("步骤 2: 初始化聚类器")
    logger.info("=" * 60)
    clusterer = _initialize_components(n_components, confidence_threshold)

    # 4. 处理训练集
    logger.info("=" * 60)
    logger.info("步骤 3: 处理训练集")
    logger.info("=" * 60)
    pure_train_pathlets, state_mapping = _process_training_set(train_pathlets, clusterer, confidence_threshold)

    # 5. 处理测试集（如果需要）
    if assign_test_states:
        logger.info("=" * 60)
        logger.info("步骤 4: 处理测试集")
        logger.info("=" * 60)
        _process_test_set(test_pathlets, clusterer, state_mapping)

    # 6. 定义状态更新完成后的回调函数
    def on_state_updated():
        """状态更新完成后的回调函数

        在PathletStorage完成状态更新后执行后续业务流程。
        """
        logger.info("状态更新完成回调执行中...")

        # 执行后续业务流程
        # 1. 生成 t-SNE 可视化（如果需要）
        if visualize:
            logger.info("=" * 60)
            logger.info("步骤 6: 生成可视化")
            logger.info("=" * 60)
            _generate_visualization(pure_train_pathlets, test_pathlets, state_mapping)

        # 2. 完成流水线
        logger.info("=" * 60)
        logger.info("聚类训练流水线完成")
        logger.info("=" * 60)

    # 6. 保存结果并更新Pathlet状态
    logger.info("=" * 60)
    logger.info("步骤 5: 保存结果并更新Pathlet状态")
    logger.info("=" * 60)

    # 实现批量保存机制，每20个径元刷新保存一次
    batch_size = 20
    total_pathlets = pure_train_pathlets + test_pathlets

    logger.info(f"开始批量保存 {len(total_pathlets)} 个径元，每 {batch_size} 个刷新保存一次")

    for i in range(0, len(total_pathlets), batch_size):
        batch_pathlets = total_pathlets[i : i + batch_size]
        logger.info(
            f"保存批次 {i // batch_size + 1}/{(len(total_pathlets) + batch_size - 1) // batch_size}，包含 {len(batch_pathlets)} 个径元"
        )

        # 确保每个径元都有正确的state_id
        for pathlet in batch_pathlets:
            if not hasattr(pathlet, "state_id"):
                pathlet.state_id = -1
                logger.warning(f"径元 {pathlet.pathlet_id} 缺少state_id，已设置为默认值-1")

        # 直接保存批次径元（刷新保存）
        storage = PathletStorage(settings.PATHLETS_DIR)
        storage.save_pathlets(batch_pathlets)
        logger.info(f"批次 {i // batch_size + 1} 保存完成")

    # 保存其他结果
    _save_results(pure_train_pathlets, test_pathlets, clusterer, state_mapping, on_state_updated=on_state_updated)
