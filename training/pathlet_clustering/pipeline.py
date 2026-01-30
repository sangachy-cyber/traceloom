from pathlib import Path

import numpy as np
from loguru import logger

from traceloom.core.config import settings
from traceloom.core.exceptions import ValidationError
from traceloom.models.state_gmm import StateGMM
from traceloom.storage.pathlet_storage import PathletStorage


class PathletClusteringPipeline:
    """径元聚类训练流水线

    基于径元的聚类训练流水线，实现以下功能：
    1. 按文件路径划分训练集和测试集
    2. 使用训练集拟合GMM聚类器
    3. 生成动态状态映射
    4. 为训练集和测试集分配状态标签
    5. 生成可视化结果
    6. 保存模型和状态映射
    """

    def __init__(self, n_components=3, test_size=0.2, random_state=42):
        """初始化聚类训练流水线

        Args:
            n_components: GMM聚类器的组件数量
            test_size: 测试集比例
            random_state: 随机种子
        """
        self.n_components = n_components
        self.test_size = test_size
        self.random_state = random_state
        self.storage = PathletStorage()
        self.scaler = None
        self.model = None
        self.state_mapping = None
        self.training_data = None
        self.test_data = None
        self.training_features = None
        self.test_features = None
        self.training_states = None
        self.test_states = None

    def run(self):
        """运行完整的聚类训练流水线"""
        logger.info("开始运行径元聚类训练流水线")

        try:
            self.step1_load_datasets()
            self.step2_fit_model()
            self.step3_save_model()
            self.step4_predict_test_set()
            self.step5_generate_state_mapping()
            self.step6_assign_states()
            self.step7_generate_visualizations()
            self.step8_update_pathlet_states()

            logger.info("径元聚类训练流水线运行完成")
        except Exception as e:
            logger.error(f"流水线运行失败: {e}")
            raise

    def step1_load_datasets(self):
        """加载数据集并按文件路径划分为训练集和测试集"""
        logger.info("加载数据集并按文件路径划分")

        # 加载所有径元数据
        pathlets = self.storage.load_pathlets()

        if len(pathlets) == 0:
            raise ValidationError("没有找到径元数据")

        # 按文件路径分组
        file_groups = {}
        valid_pathlets = []

        for pathlet in pathlets:
            # 检查径元的基本属性
            if not hasattr(pathlet, "body") or not hasattr(pathlet, "tail"):
                raise ValidationError(f"径元 {pathlet.pathlet_id} 缺少必要属性")

            # 检查观测数据
            body_obs_count = len(pathlet.body.observations) if hasattr(pathlet.body, "observations") else 0
            tail_obs_count = len(pathlet.tail.observations) if hasattr(pathlet.tail, "observations") else 0
            total_obs = body_obs_count + tail_obs_count

            if total_obs == 0:
                raise ValidationError(f"径元 {pathlet.pathlet_id} 的观测数据为空")

            valid_pathlets.append(pathlet)
            if pathlet.trace_name not in file_groups:
                file_groups[pathlet.trace_name] = []
            file_groups[pathlet.trace_name].append(pathlet)

        if len(valid_pathlets) == 0:
            raise ValidationError("没有找到有效的径元数据")

        logger.info(f"过滤后有效径元数量: {len(valid_pathlets)}")

        # 随机划分文件路径
        trace_names = list(file_groups.keys())
        np.random.seed(self.random_state)
        np.random.shuffle(trace_names)

        test_size = int(len(trace_names) * self.test_size)
        train_trace_names = set(trace_names[test_size:])

        # 构建训练集和测试集
        self.training_data = []
        self.test_data = []

        for trace_name, pathlet_list in file_groups.items():
            if trace_name in train_trace_names:
                self.training_data.extend(pathlet_list)
            else:
                self.test_data.extend(pathlet_list)

        logger.info(f"训练集大小: {len(self.training_data)}, 测试集大小: {len(self.test_data)}")

    def step2_fit_model(self):
        """使用训练集拟合GMM聚类器"""
        logger.info("使用训练集拟合GMM聚类器")

        # 使用同目录下的 GMMClusterer
        from training.pathlet_clustering.gmm_clusterer import GMMClusterer

        self.clusterer = GMMClusterer(n_components=self.n_components, random_state=self.random_state)
        # GMMClusterer.fit 方法会自动处理特征提取和归一化
        self.clusterer.fit(self.training_data)

        logger.info("GMM聚类器拟合完成")

    def step3_save_model(self):
        """保存聚类模型和状态映射"""
        logger.info("保存聚类模型和状态映射")

        # 创建保存目录
        model_dir = Path(settings.MODELS_DIR)
        model_dir.mkdir(parents=True, exist_ok=True)

        # 使用 clusterer 保存模型
        self.clusterer.save(model_dir)

    def step4_predict_test_set(self):
        """使用保存的模型预测测试集径元状态"""
        logger.info("预测测试集径元状态")

        # 加载训练后的模型
        from traceloom.models.state_gmm import StateGMM

        model_path = Path(settings.MODELS_DIR) / "gmm_model.joblib"
        state_gmm = StateGMM(model_path=model_path)

        # 预测测试集径元状态
        self.test_states = []
        for pathlet in self.test_data:
            # 从主干观测数据中提取特征并预测，与step6_assign_states保持一致
            observations = pathlet.body.observations
            if not observations:
                raise ValidationError(f"径元 {pathlet.pathlet_id} 的观测数据为空")
            # 使用训练后的模型预测
            state_label = state_gmm.predict(observations)
            self.test_states.append(state_label.state_id)

        logger.info("测试集状态预测完成")

    def step5_generate_state_mapping(self):
        """基于训练集聚类结果生成动态状态映射"""
        logger.info("生成动态状态映射")

        # 使用 clusterer 获取训练集聚类结果
        training_labels = self.clusterer.predict(self.training_data)
        training_labels = [label.state_id for label in training_labels]

        # 计算每个聚类的统计信息
        cluster_stats = {}
        for i in range(self.n_components):
            # 使用原始特征计算统计信息
            cluster_features = []
            for j, label in enumerate(training_labels):
                if label == i:
                    # 提取径元的特征
                    pathlet = self.training_data[j]
                    observations = []
                    if hasattr(pathlet.body, "observations"):
                        observations.extend(pathlet.body.observations)
                    if hasattr(pathlet.tail, "observations"):
                        observations.extend(pathlet.tail.observations)
                    features = StateGMM.extract_features(observations)
                    cluster_features.append(features)
            cluster_features = np.array(cluster_features)

            if len(cluster_features) > 0:
                cluster_stats[i] = {
                    "count": len(cluster_features),
                    "mean": np.mean(cluster_features, axis=0),
                    "std": np.std(cluster_features, axis=0),
                }

        # 生成状态映射
        self.state_mapping = {}
        for cluster_id, stats in cluster_stats.items():
            self.state_mapping[cluster_id] = f"state_{cluster_id}_{stats['count']}"

        logger.info(f"生成状态映射: {self.state_mapping}")

    def step6_assign_states(self):
        """为训练集和测试集径元分配状态标签"""
        logger.info("为径元分配状态标签")

        # 加载训练后的模型
        from traceloom.models.state_gmm import StateGMM

        model_path = Path(settings.MODELS_DIR) / "gmm_model.joblib"
        state_gmm = StateGMM(model_path=model_path)

        # 为训练集分配状态
        self.training_states = []
        for pathlet in self.training_data:
            # 从主干观测数据中提取特征并预测
            observations = pathlet.body.observations
            state_label = state_gmm.predict(observations)
            self.training_states.append(state_label.state_id)

        # 为测试集分配状态
        if len(self.test_data) > 0:
            self.test_states = []
            for pathlet in self.test_data:
                # 从主干观测数据中提取特征并预测
                observations = pathlet.body.observations
                state_label = state_gmm.predict(observations)
                self.test_states.append(state_label.state_id)
            logger.info("训练集状态分配完成，测试集状态分配完成")
        else:
            self.test_states = []
            logger.info("训练集状态分配完成，测试集为空跳过")

    def step7_generate_visualizations(self):
        """生成训练集和测试集的可视化"""
        logger.info("生成可视化结果")

        # 创建输出目录
        output_dir = Path(settings.OUTPUT_DIR) / "pathlet_clustering"
        output_dir.mkdir(parents=True, exist_ok=True)

        # 导入 TSNEVisualizer
        from training.pathlet_clustering.visualization import TSNEVisualizer

        visualizer = TSNEVisualizer(random_state=self.random_state)

        # 生成状态映射
        state_metadata = {
            "states": [{"state_id": int(k), "state_name": v, "type": "pure"} for k, v in self.state_mapping.items()]
        }

        # 提取训练集特征用于可视化
        training_features = []
        for pathlet in self.training_data:
            # 提取特征
            observations = []
            if hasattr(pathlet.body, "observations"):
                observations.extend(pathlet.body.observations)
            if hasattr(pathlet.tail, "observations"):
                observations.extend(pathlet.tail.observations)
            if observations:
                features = StateGMM.extract_features(observations)
                training_features.append(features)

        # 对训练集进行降维可视化
        if training_features:
            import numpy as np

            training_features = np.array(training_features)
            # 数据采样以减少内存使用
            sample_size = min(10000, len(training_features))
            if len(training_features) > sample_size:
                indices = np.random.choice(len(training_features), sample_size, replace=False)
                sampled_features = training_features[indices]
                sampled_states = np.array(self.training_states)[indices]
            else:
                sampled_features = training_features
                sampled_states = np.array(self.training_states)

            # 使用 TSNEVisualizer 生成 UMAP 可视化
            visualizer.visualize(
                sampled_features,
                sampled_states,
                state_metadata,
                output_dir / "training_visualization_umap.png",
                method="umap",
            )

            # 使用 TSNEVisualizer 生成 TSNE 可视化
            visualizer.visualize(
                sampled_features,
                sampled_states,
                state_metadata,
                output_dir / "training_visualization_tsne.png",
                method="tsne",
            )

        # 提取测试集特征用于可视化
        test_features = []
        for pathlet in self.test_data:
            # 提取特征
            observations = []
            if hasattr(pathlet.body, "observations"):
                observations.extend(pathlet.body.observations)
            if hasattr(pathlet.tail, "observations"):
                observations.extend(pathlet.tail.observations)
            if observations:
                features = StateGMM.extract_features(observations)
                test_features.append(features)

        # 对测试集进行降维可视化
        if test_features:
            import numpy as np

            test_features = np.array(test_features)
            # 数据采样以减少内存使用
            sample_size = min(10000, len(test_features))
            if len(test_features) > sample_size:
                indices = np.random.choice(len(test_features), sample_size, replace=False)
                sampled_features = test_features[indices]
                sampled_states = np.array(self.test_states)[indices]
            else:
                sampled_features = test_features
                sampled_states = np.array(self.test_states)

            # 使用 TSNEVisualizer 生成 UMAP 可视化
            visualizer.visualize(
                sampled_features,
                sampled_states,
                state_metadata,
                output_dir / "test_visualization_umap.png",
                method="umap",
            )

            # 使用 TSNEVisualizer 生成 TSNE 可视化
            visualizer.visualize(
                sampled_features,
                sampled_states,
                state_metadata,
                output_dir / "test_visualization_tsne.png",
                method="tsne",
            )

    def step8_update_pathlet_states(self):
        """更新径元状态信息并保存"""
        logger.info("更新径元状态信息")

        from traceloom.domain.state import StateLabel

        # 更新训练集径元状态
        for pathlet, state in zip(self.training_data, self.training_states, strict=False):
            # 设置 state_label
            pathlet.state_label = StateLabel(state_id=state)

        # 更新测试集径元状态
        for pathlet, state in zip(self.test_data, self.test_states, strict=False):
            # 设置 state_label
            pathlet.state_label = StateLabel(state_id=state)

        # 保存更新后的径元状态，不更新点数据（点数据为静态数据）
        all_pathlets = self.training_data + self.test_data
        self.storage.save_pathlets(all_pathlets, update_points=False)

        logger.info("径元状态信息更新完成")


if __name__ == "__main__":
    """主函数，运行径元聚类训练流水线"""
    try:
        pipeline = PathletClusteringPipeline()
        pipeline.run()
    except Exception as e:
        logger.error(f"运行失败: {e}")
        raise
