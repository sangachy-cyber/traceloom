# -*- coding: utf-8 -*-
"""径元缓存管理模块"""

import time
from collections import OrderedDict
from typing import Any, Dict, Optional

import pandas as pd

from traceloom.core.logger import logger


class LRUCache:
    """LRU缓存实现

    使用OrderedDict实现LRU缓存，支持自动淘汰最久未使用的项
    """

    def __init__(self, capacity: int):
        """初始化LRU缓存

        Args:
            capacity: 缓存容量
        """
        self.capacity = capacity
        self.cache = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存项

        Args:
            key: 缓存键

        Returns:
            Optional[Any]: 缓存值，如果不存在则返回None
        """
        if key not in self.cache:
            return None
        # 将访问的项移到末尾，表示最近使用
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: str, value: Any) -> None:
        """添加缓存项

        Args:
            key: 缓存键
            value: 缓存值
        """
        if key in self.cache:
            # 如果键已存在，先删除旧值
            del self.cache[key]
        elif len(self.cache) >= self.capacity:
            # 如果缓存已满，删除最久未使用的项
            self.cache.popitem(last=False)
        # 添加新项到末尾
        self.cache[key] = value

    def clear(self) -> None:
        """清空缓存
        """
        self.cache.clear()

    def __len__(self) -> int:
        """获取缓存大小

        Returns:
            int: 缓存大小
        """
        return len(self.cache)


class PathletCacheManager:
    """径元缓存管理器

    负责径元数据的缓存管理，包括：
    - 主数据缓存
    - 点数据缓存
    - 基于LRU的缓存淘汰机制
    - 缓存过期时间管理
    """

    def __init__(self, cache_size_limit: int = 100000, cache_expiry_seconds: int = 300):
        """初始化径元缓存管理器

        Args:
            cache_size_limit: 缓存大小限制（行数）
            cache_expiry_seconds: 缓存过期时间（秒）
        """
        # 缓存配置
        self._cache_size_limit = cache_size_limit
        self._cache_expiry_seconds = cache_expiry_seconds

        # 使用LRU缓存
        self._main_data_cache = LRUCache(capacity=10)  # 主数据缓存，按查询条件缓存
        self._points_cache = LRUCache(capacity=5)    # 点数据缓存，按trace_name缓存

        # 缓存时间戳
        self._cache_timestamp: Dict[str, float] = {}

        # 点数据加载标记
        self._points_loaded: bool = False

    def get_main_data(self, key: str) -> Optional[pd.DataFrame]:
        """获取主数据缓存

        Args:
            key: 缓存键，通常是查询条件的字符串表示

        Returns:
            Optional[pd.DataFrame]: 缓存的主数据，如果不存在或已过期则返回None
        """
        # 检查缓存是否存在且未过期
        if self._is_cache_valid(key):
            data = self._main_data_cache.get(key)
            if data is not None:
                # 更新缓存时间戳
                self._update_cache_timestamp(key)
                logger.debug(f"从缓存加载主数据，键: {key}")
            return data
        return None

    def set_main_data(self, key: str, data: pd.DataFrame) -> None:
        """设置主数据缓存

        Args:
            key: 缓存键
            data: 要缓存的主数据
        """
        # 检查数据大小是否超过限制
        if len(data) <= self._cache_size_limit:
            self._main_data_cache.put(key, data)
            self._update_cache_timestamp(key)
            logger.debug(f"主数据已缓存，键: {key}, 行数: {len(data)}")
        else:
            logger.debug(f"主数据超过缓存大小限制，未缓存，行数: {len(data)}")

    def get_points_data(self, key: str) -> Optional[pd.DataFrame]:
        """获取点数据缓存

        Args:
            key: 缓存键，通常是trace_name的字符串表示

        Returns:
            Optional[pd.DataFrame]: 缓存的点数据，如果不存在或已过期则返回None
        """
        # 检查缓存是否存在且未过期
        if self._is_cache_valid(key):
            data = self._points_cache.get(key)
            if data is not None:
                # 更新缓存时间戳
                self._update_cache_timestamp(key)
                logger.debug(f"从缓存加载点数据，键: {key}")
            return data
        return None

    def set_points_data(self, key: str, data: pd.DataFrame) -> None:
        """设置点数据缓存

        Args:
            key: 缓存键
            data: 要缓存的点数据
        """
        # 检查数据大小是否超过限制
        if len(data) <= self._cache_size_limit:
            self._points_cache.put(key, data)
            self._update_cache_timestamp(key)
            logger.debug(f"点数据已缓存，键: {key}, 行数: {len(data)}")
        else:
            logger.debug(f"点数据超过缓存大小限制，未缓存，行数: {len(data)}")

    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效

        Args:
            cache_key: 缓存键

        Returns:
            bool: 缓存是否有效
        """
        if cache_key not in self._cache_timestamp:
            return False

        current_time = time.time()
        return current_time - self._cache_timestamp[cache_key] < self._cache_expiry_seconds

    def _update_cache_timestamp(self, cache_key: str) -> None:
        """更新缓存时间戳

        Args:
            cache_key: 缓存键
        """
        self._cache_timestamp[cache_key] = time.time()

    def clear_cache(self) -> None:
        """清空所有缓存
        """
        self._main_data_cache.clear()
        self._points_cache.clear()
        self._cache_timestamp.clear()
        self._points_loaded = False
        logger.debug("所有缓存已清空")

    def set_points_loaded(self, loaded: bool) -> None:
        """设置点数据加载标记

        Args:
            loaded: 是否已加载
        """
        self._points_loaded = loaded

    def is_points_loaded(self) -> bool:
        """获取点数据加载标记

        Returns:
            bool: 是否已加载
        """
        return self._points_loaded

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息

        Returns:
            Dict[str, Any]: 缓存统计信息
        """
        return {
            "main_data_cache_size": len(self._main_data_cache),
            "points_cache_size": len(self._points_cache),
            "cache_size_limit": self._cache_size_limit,
            "cache_expiry_seconds": self._cache_expiry_seconds
        }
