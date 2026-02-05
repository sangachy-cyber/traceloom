# -*- coding: utf-8 -*-
"""径元模型管理模块"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

import joblib

from traceloom.core.config import settings
from traceloom.core.logger import logger


class PathletModelManager:
    """径元模型管理器

    负责径元相关模型的读写操作，包括：
    - GMM模型的保存和加载
    - 状态映射的保存和加载
    - 轻量级StateGMM模型的保存和加载
    """

    def __init__(self, model_dir: Optional[Path] = None):
        """初始化径元模型管理器

        Args:
            model_dir: 模型目录路径，默认使用settings中的配置
        """
        self.model_dir = model_dir or settings.PATHLETS_DIR
        self.model_dir.mkdir(exist_ok=True, parents=True)

        # GMM模型文件 - 存储训练好的聚类模型
        self.gmm_model_file = self.model_dir / "gmm_model.joblib"
        # 状态映射文件 - 存储状态ID到状态名称的映射
        self.state_mapping_file = self.model_dir / "state_mapping.json"

    def save_gmm_model(self, model: Any, state_mapping: Dict[str, Any]) -> None:
        """保存GMM模型和状态映射

        Args:
            model: GMM模型对象
            state_mapping: 状态映射字典
        """
        # 保存模型
        joblib.dump(model, self.gmm_model_file)
        logger.debug(f"GMM模型已保存到: {self.gmm_model_file}")

        # 保存状态映射
        with open(self.state_mapping_file, "w", encoding="utf-8") as f:
            json.dump(state_mapping, f, ensure_ascii=False, indent=2)
        logger.debug(f"状态映射已保存到: {self.state_mapping_file}")

    def load_gmm_model(self) -> Optional[Any]:
        """加载GMM模型

        Returns:
            Optional[Any]: 加载的GMM模型对象，如果文件不存在则返回None
        """
        if not self.gmm_model_file.exists():
            logger.warning(f"GMM模型文件不存在: {self.gmm_model_file}")
            return None

        model = joblib.load(self.gmm_model_file)
        logger.debug(f"GMM模型已从: {self.gmm_model_file} 加载")
        return model

    def load_state_mapping(self) -> Optional[Dict[str, Any]]:
        """加载状态映射

        Returns:
            Optional[Dict[str, Any]]: 状态映射字典，如果文件不存在则返回None
        """
        if not self.state_mapping_file.exists():
            logger.warning(f"状态映射文件不存在: {self.state_mapping_file}")
            return None

        with open(self.state_mapping_file, "r", encoding="utf-8") as f:
            state_mapping = json.load(f)
        logger.info(f"状态映射已从: {self.state_mapping_file} 加载")
        return state_mapping

    def save_state_gmm_model(self, model_data: Dict[str, Any]) -> None:
        """保存轻量级StateGMM模型

        Args:
            model_data: 模型数据字典，包含gmm、scaler等组件
        """
        joblib.dump(model_data, self.gmm_model_file)
        logger.info(f"轻量级StateGMM模型已保存到: {self.gmm_model_file}")

    def load_state_gmm_model(self) -> Optional[Dict[str, Any]]:
        """加载轻量级StateGMM模型

        Returns:
            Optional[Dict[str, Any]]: 模型数据字典，如果文件不存在则返回None
        """
        if not self.gmm_model_file.exists():
            logger.warning(f"StateGMM模型文件不存在: {self.gmm_model_file}")
            return None

        model_data = joblib.load(self.gmm_model_file)
        logger.info(f"轻量级StateGMM模型已从: {self.gmm_model_file} 加载")
        return model_data

    def clear_models(self) -> None:
        """清空模型数据
        """
        if self.gmm_model_file.exists():
            self.gmm_model_file.unlink()
            logger.debug(f"已删除GMM模型文件: {self.gmm_model_file}")

        if self.state_mapping_file.exists():
            self.state_mapping_file.unlink()
            logger.debug(f"已删除状态映射文件: {self.state_mapping_file}")
