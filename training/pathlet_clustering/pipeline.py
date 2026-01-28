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

from pathlib import Path
from typing import Dict, List

from traceloom.core.config import settings
from traceloom.core.logger import logger
from traceloom.domain.pathlet import Pathlet
from traceloom.domain.raw_trace import RawTraceSegment as RawProfile
from traceloom.storage.pathlet_storage import PathletStorage
from training.pathlet_clustering.data_loader import DataLoader
from training.pathlet_clustering.gmm_clusterer import GMMClusterer
from training.pathlet_clustering.visualization import TSNEVisualizer


def load_profiles_from_csv(file_path: Path) -> List[RawProfile]:
    """从 CSV 文件加载网络剖面

    从指定的 CSV 文件中加载网络剖面数据，转换为 RawProfile 对象列表。

    Args:
        file_path: CSV 文件路径

    Returns:
        List[RawProfile]: 网络剖面列表

    Examples:
        # 从 CSV 文件加载网络剖面
        profiles = load_profiles_from_csv(Path("train.csv"))
        print(f"加载了 {len(profiles)} 个网络剖面")
    """
    loader = DataLoader()
    return loader.load_from_csv(file_path)


def save_profiles_to_csv(profiles: List[RawProfile], file_path: Path) -> None:
    """将网络剖面保存为 CSV 文件

    将网络剖面列表保存为 CSV 文件，方便后续加载和分析。

    Args:
        profiles: 网络剖面列表
        file_path: 输出 CSV 文件路径

    Examples:
        # 将网络剖面保存为 CSV 文件
        save_profiles_to_csv(profiles, Path("train.csv"))
        print("网络剖面已保存到 train.csv")
    """
    loader = DataLoader()
    loader.profiles_to_csv(profiles, file_path)


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

    从 before_label/ 目录加载训练集和测试集，如果文件不存在则尝试从径元数据生成。

    Returns:
        tuple: (train_profiles, test_profiles)，训练集和测试集的网络剖面列表

    Examples:
        # 加载训练集和测试集
        train_profiles, test_profiles = _load_datasets()
        print(f"训练集大小: {len(train_profiles)}, 测试集大小: {len(test_profiles)}")
    """
    train_csv_path = settings.BEFORE_LABEL_DIR / "train_scaled.csv"
    test_csv_path = settings.BEFORE_LABEL_DIR / "test_scaled.csv"

    if not train_csv_path.exists():
        # 尝试使用旧命名作为备选
        train_csv_path = settings.BEFORE_LABEL_DIR / "train.csv"
        if not train_csv_path.exists():
            logger.error(f"训练集文件不存在: {train_csv_path}")
            logger.info("尝试从径元数据生成训练集和测试集...")
            # 从径元数据生成训练集和测试集
            return _generate_datasets_from_pathlets()

    if not test_csv_path.exists():
        # 尝试使用旧命名作为备选
        test_csv_path = settings.BEFORE_LABEL_DIR / "test.csv"
        if not test_csv_path.exists():
            logger.error(f"测试集文件不存在: {test_csv_path}")
            logger.info("尝试从径元数据生成训练集和测试集...")
            # 从径元数据生成训练集和测试集
            return _generate_datasets_from_pathlets()

    train_profiles = load_profiles_from_csv(train_csv_path)
    test_profiles = load_profiles_from_csv(test_csv_path)
    return train_profiles, test_profiles


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
    ctx_data = raw_data['ctx_10s']
    for i in range(len(ctx_data.delay_up)):
        obs = Observation(
            delay_up=ctx_data.delay_up[i],
            loss_up=ctx_data.loss_up[i],
            bw_up=ctx_data.bw_up[i],
            delay_down=ctx_data.delay_down[i],
            loss_down=ctx_data.loss_down[i],
            bw_down=ctx_data.bw_down[i]
        )
        observations.append(obs)

    # 添加 cont_1s 的观测数据（10个）
    cont_data = raw_data['cont_1s']
    for i in range(len(cont_data.delay_up)):
        obs = Observation(
            delay_up=cont_data.delay_up[i],
            loss_up=cont_data.loss_up[i],
            bw_up=cont_data.bw_up[i],
            delay_down=cont_data.delay_down[i],
            loss_down=cont_data.loss_down[i],
            bw_down=cont_data.bw_down[i]
        )
        observations.append(obs)

    # 创建 RawProfile 对象
    profile = RawProfile(
        trace_name=raw_data['trace_name'],
        start_index=raw_data['start_index'],
        observations=observations,
        is_valid=raw_data['is_valid']
    )
    return profile


def _generate_datasets_from_pathlets() -> tuple:
    """从径元数据生成训练集和测试集

    从径元库中加载径元数据，生成训练集和测试集（80% 训练，20% 测试）。

    Returns:
        tuple: (train_profiles, test_profiles)，生成的训练集和测试集

    Examples:
        # 从径元数据生成训练集和测试集
        train_profiles, test_profiles = _generate_datasets_from_pathlets()
        print(f"从径元数据生成了训练集: {len(train_profiles)}，测试集: {len(test_profiles)}")
    """
    from traceloom.storage.pathlet_storage import PathletStorage

    storage = PathletStorage(settings.PATHLETS_DIR)
    pathlets = storage.load_pathlets()

    if not pathlets:
        logger.error("没有可用的径元数据")
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
        profile = _pathlet_to_profile(pathlet, storage)
        if profile:
            train_profiles.append(profile)

    # 生成测试集
    test_profiles = []
    for pathlet in test_pathlets:
        profile = _pathlet_to_profile(pathlet, storage)
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

            cluster_stats.append({
                'cluster_id': i,
                'count': count,
                'delay_mean': delay_mean,
                'loss_mean': loss_mean,
                'stability_score': stability_score,
                'mean_features': mean_features.tolist(),
                'std_features': std_features.tolist()
            })
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
    sorted_clusters = sorted(cluster_stats, key=lambda x: x['stability_score'], reverse=True)

    # 定义状态名称
    state_names = ['稳定', '抖动', '异常']
    if len(sorted_clusters) > 3:
        state_names.extend([f'状态_{i}' for i in range(3, len(sorted_clusters))])

    # 生成状态映射
    states = []
    for i, cluster in enumerate(sorted_clusters):
        state_name = state_names[i] if i < len(state_names) else f'状态_{i}'
        states.append({
            'state_id': i,
            'state_name': state_name,
            'type': 'pure',
            'original_cluster_id': cluster['cluster_id'],
            'count': cluster['count'],
            'stability_score': cluster['stability_score']
        })

    # 生成状态映射字典
    state_mapping = {
        'algorithm': 'gmm',
        'n_components': len(sorted_clusters),
        'confidence_threshold': 0.85,
        'states': states
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


def _process_training_set(train_profiles: list, clusterer, confidence_threshold: float) -> Dict:
    """处理训练集

    处理训练集，拟合聚类器，生成动态状态映射，并为训练集分配状态。

    Args:
        train_profiles: 训练集网络剖面列表
        clusterer: 初始化的聚类器
        confidence_threshold: 置信度阈值

    Returns:
        Dict: 处理后的训练集和状态映射

    Examples:
        # 处理训练集
        pure_train_profiles, state_mapping = _process_training_set(train_profiles, clusterer, 0.85)
        print(f"处理后训练集大小: {len(pure_train_profiles)}")
    """
    logger.info(f"在训练集上拟合 GMM 聚类器，n_components={clusterer.n_components}")

    # 转换 RawProfile 为 Pathlet 用于训练
    pathlets = []
    for profile in train_profiles:
        # 创建简单的 Pathlet 对象，只包含必要的观测数据
        from traceloom.domain.pathlet import BodyObservations, TailObservations
        body_obs = profile.observations[:100]  # 假设前100个是主体
        tail_obs = profile.observations[100:]  # 假设后10个是融尾

        pathlet = Pathlet(
            pathlet_id=f"{profile.trace_name}_{profile.start_index}",
            body=BodyObservations(observations=body_obs),
            tail=TailObservations(observations=tail_obs)
        )
        pathlets.append(pathlet)

    # 拟合聚类器
    clusterer.fit(pathlets)

    # 分析聚类特征，生成动态状态映射
    logger.info("分析聚类特征，生成动态状态映射")
    cluster_stats = _analyze_cluster_features(train_profiles, clusterer)
    state_mapping = _generate_dynamic_state_mapping(cluster_stats)

    # 为训练集分配状态
    logger.info("为训练集分配状态")
    state_labels = clusterer.predict(pathlets)

    # 使用后验概率筛选纯净样本
    logger.info(f"使用后验概率筛选纯净样本，置信度阈值={confidence_threshold}")
    pure_train_profiles = []
    for profile, label in zip(train_profiles, state_labels, strict=True):
        profile.state_id = label.state_id
        profile.state_name = next(s['state_name'] for s in state_mapping['states'] if s['state_id'] == label.state_id)
        profile.state_proba = label.confidence

        # 只保留后验概率高于置信度阈值的样本
        if label.confidence >= confidence_threshold:
            pure_train_profiles.append(profile)

    logger.info(f"筛选后训练集大小: {len(pure_train_profiles)} (原始: {len(train_profiles)})")

    return pure_train_profiles, state_mapping


def _process_test_set(test_profiles: list, clusterer, state_mapping: Dict) -> None:
    """处理测试集

    为测试集分配状态，使用训练好的聚类器进行预测。

    Args:
        test_profiles: 测试集网络剖面列表
        clusterer: 训练好的聚类器
        state_mapping: 状态映射字典

    Examples:
        # 处理测试集
        _process_test_set(test_profiles, clusterer, state_mapping)
        print("测试集状态分配完成")
    """
    logger.info("为测试集分配状态")

    # 转换 RawProfile 为 Pathlet 用于预测
    pathlets = []
    for profile in test_profiles:
        from traceloom.domain.pathlet import BodyObservations, TailObservations
        body_obs = profile.observations[:100]  # 假设前100个是主体
        tail_obs = profile.observations[100:]  # 假设后10个是融尾

        pathlet = Pathlet(
            pathlet_id=f"{profile.trace_name}_{profile.start_index}",
            body=BodyObservations(observations=body_obs),
            tail=TailObservations(observations=tail_obs)
        )
        pathlets.append(pathlet)

    # 预测状态
    state_labels = clusterer.predict(pathlets)
    for profile, label in zip(test_profiles, state_labels, strict=True):
        profile.state_id = label.state_id
        profile.state_name = next(s['state_name'] for s in state_mapping['states'] if s['state_id'] == label.state_id)
        profile.state_proba = label.confidence


def _save_results(train_profiles: list, test_profiles: list, clusterer, state_mapping: Dict) -> None:
    """保存结果

    保存训练结果，包括状态元数据、训练集、测试集、聚类模型和状态映射。

    Args:
        train_profiles: 训练集网络剖面列表
        test_profiles: 测试集网络剖面列表
        clusterer: 训练好的聚类器
        state_mapping: 状态映射字典

    Examples:
        # 保存结果
        _save_results(train_profiles, test_profiles, clusterer, state_mapping)
        print("训练结果保存完成")
    """

    # 保存状态元数据
    metadata_path = settings.AFTER_LABEL_DIR / "state_metadata.json"
    save_state_metadata(state_mapping, metadata_path)

    # 保存训练集和测试集
    train_output_path = settings.AFTER_LABEL_DIR / "train.csv"
    test_output_path = settings.AFTER_LABEL_DIR / "test.csv"

    save_profiles_to_csv(train_profiles, train_output_path)
    save_profiles_to_csv(test_profiles, test_output_path)

    # 保存聚类模型
    model_path = settings.MODELS_DIR / "gmm_model.joblib"
    clusterer.model.save(model_path)
    logger.info(f"聚类模型已保存到: {model_path}")

    # 保存状态映射
    state_mapping_path = settings.MODELS_DIR / "state_mapping.json"
    save_state_metadata(state_mapping, state_mapping_path)
    logger.info(f"状态映射已保存到: {state_mapping_path}")

    # 保存到 PathletStorage
    storage = PathletStorage(settings.PATHLETS_DIR)
    # 创建 model_data 字典
    model_data = {
        "n_components": clusterer.n_components,
        "confidence_threshold": clusterer.confidence_threshold,
        "gmm": clusterer.model.gmm,
        "scaler": clusterer.model.scaler,
        "_is_fit": clusterer.model.is_fit,
    }
    storage.save_gmm_model(model_data, state_mapping)


def _generate_visualization(train_profiles: list, test_profiles: list, state_metadata: dict) -> None:
    """生成降维可视化（t-SNE 和 UMAP）

    生成聚类结果的降维可视化，包括 t-SNE 和 UMAP 两种方法。

    Args:
        train_profiles: 训练集网络剖面列表
        test_profiles: 测试集网络剖面列表
        state_metadata: 状态元数据

    Examples:
        # 生成可视化
        _generate_visualization(train_profiles, test_profiles, state_mapping)
        print("可视化生成完成")
    """
    logger.info("生成降维可视化")
    visualizer = TSNEVisualizer()

    # 提取所有训练集和测试集的特征
    train_features = []
    train_labels = []
    train_probabilities = []
    for profile in train_profiles:
        features = GMMClusterer.extract_features(profile.observations)
        train_features.append(features)
        train_labels.append(profile.state_id)
        train_probabilities.append(getattr(profile, 'state_proba', 0.5))  # 默认置信度 0.5

    test_features = []
    test_labels = []
    test_probabilities = []
    for profile in test_profiles:
        features = GMMClusterer.extract_features(profile.observations)
        test_features.append(features)
        test_labels.append(profile.state_id)
        test_probabilities.append(getattr(profile, 'state_proba', 0.5))  # 默认置信度 0.5

    # 合并特征、标签和概率
    all_features = train_features + test_features
    all_labels = train_labels + test_labels
    all_probabilities = train_probabilities + test_probabilities

    # 生成 t-SNE 可视化
    tsne_output_path = settings.AFTER_LABEL_DIR / "clustering_gmm_tsne.png"
    visualizer.visualize(all_features, all_labels, state_metadata, tsne_output_path, all_probabilities, method='tsne')
    logger.info(f"t-SNE 可视化已生成，保存到: {tsne_output_path}")

    # 尝试生成 UMAP 可视化
    umap_output_path = settings.AFTER_LABEL_DIR / "clustering_gmm_umap.png"
    try:
        visualizer.visualize(all_features, all_labels, state_metadata, umap_output_path, all_probabilities, method='umap')
        logger.info(f"UMAP 可视化已生成，保存到: {umap_output_path}")
    except ImportError as e:
        logger.warning(f"跳过 UMAP 可视化: {e}")


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

    # 2. 加载训练集和测试集
    train_profiles, test_profiles = _load_datasets()
    if train_profiles is None or test_profiles is None:
        return

    # 3. 初始化聚类器
    clusterer = _initialize_components(n_components, confidence_threshold)

    # 4. 处理训练集
    pure_train_profiles, state_mapping = _process_training_set(train_profiles, clusterer, confidence_threshold)

    # 5. 处理测试集（如果需要）
    if assign_test_states:
        _process_test_set(test_profiles, clusterer, state_mapping)

    # 6. 保存结果
    _save_results(pure_train_profiles, test_profiles, clusterer, state_mapping)

    # 7. 生成 t-SNE 可视化（如果需要）
    if visualize:
        _generate_visualization(pure_train_profiles, test_profiles, state_mapping)

    logger.info("聚类训练流水线完成")

