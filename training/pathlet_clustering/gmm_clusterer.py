# -*- coding: utf-8 -*-
"""GMM 聚类器

训练 GMM 模型，生成状态映射表，使用 StateGMM 进行模型管理。

示例:
    from training.pathlet_clustering.gmm_clusterer import GMMClusterer
    from traceloom.domain.pathlet import Pathlet, BodyObservations, TailObservations
    from traceloom.domain.pathlet import Observation

    # 创建径元数据
    observations = [Observation(delay_up=10, loss_up=0, bw_up=100, delay_down=10, loss_down=0, bw_down=100) for _ in range(10)]
    body = BodyObservations(observations=observations)
    tail = TailObservations(observations=observations[:2])
    pathlet = Pathlet(pathlet_id="test", body=body, tail=tail)

    # 初始化聚类器
    clusterer = GMMClusterer(n_components=3, confidence_threshold=0.85)

    # 拟合模型
    clusterer.fit([pathlet])

    # 预测状态
    labels = clusterer.predict([pathlet])
    print(f"预测状态: {labels[0].state_id}, 置信度: {labels[0].confidence}")

    # 保存模型
    from pathlib import Path
    clusterer.save(Path("./models"))

    # 加载模型
    loaded_clusterer = GMMClusterer.load(Path("./models/gmm_model.joblib"))
    print(f"加载的模型是否已拟合: {loaded_clusterer.is_fit}")
"""

from pathlib import Path
from typing import List

from traceloom.core.logger import logger
from traceloom.domain.pathlet import Pathlet
from traceloom.domain.state import StateLabel
from traceloom.models.state_gmm import StateGMM


class GMMClusterer:
    """GMM 聚类器

    训练 GMM 模型，生成状态映射表，使用 StateGMM 进行模型管理。
    """

    def __init__(self, n_components: int = 3, confidence_threshold: float = 0.85, random_state: int = 42):
        """初始化 GMM 聚类器

        Args:
            n_components: 聚类数量
            confidence_threshold: 置信度阈值
            random_state: 随机种子

        Examples:
            # 初始化聚类器
            clusterer = GMMClusterer(n_components=3, confidence_threshold=0.85)
            print(f"聚类器初始化完成，聚类数量: {clusterer.n_components}")
        """
        self.n_components = n_components
        self.confidence_threshold = confidence_threshold
        self.random_state = random_state
        self.model = StateGMM(
            n_components=n_components, confidence_threshold=confidence_threshold, random_state=random_state
        )

    @staticmethod
    def extract_features(observations):
        """提取观测数据的特征

        调用 StateGMM 的特征提取方法。

        Args:
            observations: 观测数据列表

        Returns:
            特征向量

        Examples:
            # 提取特征
            from traceloom.domain.pathlet import Observation
            observations = [Observation(delay_up=10, loss_up=0, bw_up=100, delay_down=10, loss_down=0, bw_down=100)]
            features = GMMClusterer.extract_features(observations)
            print(f"提取的特征维度: {len(features)}")
        """
        return StateGMM.extract_features(observations)

    def fit(self, pathlets: List[Pathlet]) -> None:
        """拟合 GMM 模型

        Args:
            pathlets: 径元列表

        Examples:
            # 拟合模型
            clusterer.fit([pathlet1, pathlet2])
            print(f"模型拟合完成，是否已拟合: {clusterer.is_fit}")
        """
        self.model.fit(pathlets)

    def predict(self, pathlets: List[Pathlet]) -> List[StateLabel]:
        """预测径元的状态

        Args:
            pathlets: 径元列表

        Returns:
            List[StateLabel]: 状态标签列表

        Raises:
            ValueError: 模型尚未拟合时抛出

        Examples:
            # 预测状态
            labels = clusterer.predict([pathlet])
            for i, label in enumerate(labels):
                print(f"径元 {i} 状态: {label.state_id}, 置信度: {label.confidence}")
        """
        if not self.model.is_fit:
            raise ValueError("模型尚未拟合，请先调用 fit 方法")

        # 预测每个径元的状态
        state_labels = []
        for pathlet in pathlets:
            # 从主干观测数据中提取特征并预测
            observations = pathlet.body.observations
            state_label = self.model.predict(observations)
            state_labels.append(state_label)

        return state_labels

    def save(self, output_dir: Path) -> None:
        """保存模型

        只保存 GMM 模型和 Scaler，不生成状态映射。
        状态映射的生成和持久化由 pipeline.py 负责。

        Args:
            output_dir: 输出目录

        Raises:
            ValueError: 模型尚未拟合时抛出

        Examples:
            # 保存模型
            from pathlib import Path
            clusterer.save(Path("./models"))
            print("模型保存完成")
        """
        if not self.model.is_fit:
            raise ValueError("模型尚未拟合，请先调用 fit 方法")

        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存模型
        model_path = output_dir / "gmm_model.joblib"
        self.model.save(model_path)

        logger.info(f"GMM 模型保存到: {model_path}")

    @classmethod
    def load(cls, model_path: Path) -> "GMMClusterer":
        """加载模型

        Args:
            model_path: 模型路径

        Returns:
            GMMClusterer: 加载的 GMM 聚类器实例

        Examples:
            # 加载模型
            from pathlib import Path
            loaded_clusterer = GMMClusterer.load(Path("./models/gmm_model.joblib"))
            print(f"模型加载完成，聚类数量: {loaded_clusterer.n_components}")
        """
        # 创建 StateGMM 实例并加载模型
        state_gmm = StateGMM(model_path=model_path)

        # 创建 GMMClusterer 实例
        clusterer = cls(
            n_components=state_gmm.n_components,
            confidence_threshold=state_gmm.confidence_threshold,
            random_state=state_gmm.random_state,
        )
        clusterer.model = state_gmm

        logger.info(f"GMM 模型从 {model_path} 加载完成")
        return clusterer

    @property
    def is_fit(self) -> bool:
        """模型是否已经拟合

        Returns:
            bool: 模型是否已经拟合

        Examples:
            # 检查模型是否已拟合
            if clusterer.is_fit:
                print("模型已拟合，可以进行预测")
            else:
                print("模型尚未拟合，请先调用 fit 方法")
        """
        return self.model.is_fit
