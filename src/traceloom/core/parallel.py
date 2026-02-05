# -*- coding: utf-8 -*-
"""并行处理工具模块

提供并行处理的功能，充分利用多核CPU资源，提高处理速度。
"""

import concurrent.futures
from typing import Any, Callable, Iterator, List, Optional, TypeVar

from traceloom.core.logger import logger

T = TypeVar('T')


class ParallelProcessor:
    """并行处理器

    提供并行处理的功能，支持以下特性：
    - 自动根据CPU核心数调整线程池大小
    - 支持分批处理大任务
    - 支持异常处理
    - 支持进度回调
    """

    def __init__(self, max_workers: Optional[int] = None):
        """初始化并行处理器

        Args:
            max_workers: 最大工作线程数，默认使用CPU核心数
        """
        self.max_workers = max_workers

    def process(
        self,
        items: List[T],
        func: Callable[[T], Any],
        batch_size: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Any]:
        """并行处理列表中的项目

        Args:
            items: 要处理的项目列表
            func: 处理函数，接收一个项目并返回处理结果
            batch_size: 批处理大小，默认不使用批处理
            progress_callback: 进度回调函数，接收已处理的项目数和总项目数

        Returns:
            List[Any]: 处理结果列表

        Examples:
            # 基本用法
            processor = ParallelProcessor()
            results = processor.process(
                [1, 2, 3, 4, 5],
                lambda x: x * 2
            )
            print(results)  # [2, 4, 6, 8, 10]

            # 使用批处理
            def batch_func(batch):
                return [item * 2 for item in batch]
            results = processor.process(
                [1, 2, 3, 4, 5],
                batch_func,
                batch_size=2
            )
            print(results)  # [2, 4, 6, 8, 10]

            # 使用进度回调
            def progress_func(done, total):
                print(f"Progress: {done}/{total}")
            results = processor.process(
                [1, 2, 3, 4, 5],
                lambda x: x * 2,
                progress_callback=progress_func
            )
        """
        if not items:
            return []

        total_items = len(items)
        results = []

        # 如果指定了批处理大小，使用批处理
        if batch_size and batch_size > 0:
            # 分批次处理
            batches = self._create_batches(items, batch_size)
            batch_results = self._process_batches(batches, func, progress_callback, total_items)
            # 展平结果
            for batch_result in batch_results:
                if isinstance(batch_result, list):
                    results.extend(batch_result)
                else:
                    results.append(batch_result)
        else:
            # 单个项目处理
            results = self._process_items(items, func, progress_callback)

        return results

    def _create_batches(self, items: List[T], batch_size: int) -> List[List[T]]:
        """创建批处理列表

        Args:
            items: 要处理的项目列表
            batch_size: 批处理大小

        Returns:
            List[List[T]]: 批处理列表
        """
        batches = []
        for i in range(0, len(items), batch_size):
            batches.append(items[i:i+batch_size])
        return batches

    def _process_items(
        self,
        items: List[T],
        func: Callable[[T], Any],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[Any]:
        """并行处理单个项目

        Args:
            items: 要处理的项目列表
            func: 处理函数
            progress_callback: 进度回调函数

        Returns:
            List[Any]: 处理结果列表
        """
        results = []
        total_items = len(items)
        processed = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_item = {
                executor.submit(func, item): item
                for item in items
            }

            # 处理结果
            for future in concurrent.futures.as_completed(future_to_item):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as exc:
                    logger.error(f"处理项目时出错: {exc}")
                    # 出错时添加None作为结果
                    results.append(None)
                finally:
                    processed += 1
                    # 调用进度回调
                    if progress_callback:
                        progress_callback(processed, total_items)

        return results

    def _process_batches(
        self,
        batches: List[List[T]],
        func: Callable[[List[T]], Any],
        progress_callback: Optional[Callable[[int, int], None]] = None,
        total_items: Optional[int] = None
    ) -> List[Any]:
        """并行处理批处理

        Args:
            batches: 批处理列表
            func: 处理函数
            progress_callback: 进度回调函数
            total_items: 总项目数，用于进度计算

        Returns:
            List[Any]: 处理结果列表
        """
        results = []
        total_batches = len(batches)
        processed_batches = 0
        processed_items = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_batch = {
                executor.submit(func, batch): batch
                for batch in batches
            }

            # 处理结果
            for future in concurrent.futures.as_completed(future_to_batch):
                batch = future_to_batch[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as exc:
                    logger.error(f"处理批处理时出错: {exc}")
                    # 出错时添加None作为结果
                    results.append(None)
                finally:
                    processed_batches += 1
                    processed_items += len(batch)
                    # 调用进度回调
                    if progress_callback and total_items:
                        progress_callback(processed_items, total_items)
                    elif progress_callback:
                        progress_callback(processed_batches, total_batches)

        return results

    def map(
        self,
        func: Callable[[T], Any],
        items: Iterator[T],
        batch_size: Optional[int] = None
    ) -> Iterator[Any]:
        """并行映射函数到迭代器

        Args:
            func: 映射函数
            items: 输入迭代器
            batch_size: 批处理大小，默认不使用批处理

        Returns:
            Iterator[Any]: 输出迭代器

        Examples:
            # 基本用法
            processor = ParallelProcessor()
            results = processor.map(
                lambda x: x * 2,
                range(10)
            )
            print(list(results))  # [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]
        """
        # 将迭代器转换为列表
        items_list = list(items)
        # 处理项目
        results = self.process(items_list, func, batch_size)
        # 转换回迭代器
        return iter(results)


# 全局并行处理器实例
parallel_processor = ParallelProcessor()


def parallel_process(
    items: List[T],
    func: Callable[[T], Any],
    batch_size: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[Any]:
    """并行处理列表中的项目

    便捷函数，使用全局并行处理器实例

    Args:
        items: 要处理的项目列表
        func: 处理函数
        batch_size: 批处理大小
        progress_callback: 进度回调函数

    Returns:
        List[Any]: 处理结果列表
    """
    return parallel_processor.process(items, func, batch_size, progress_callback)


def parallel_map(
    func: Callable[[T], Any],
    items: Iterator[T],
    batch_size: Optional[int] = None
) -> Iterator[Any]:
    """并行映射函数到迭代器

    便捷函数，使用全局并行处理器实例

    Args:
        func: 映射函数
        items: 输入迭代器
        batch_size: 批处理大小

    Returns:
        Iterator[Any]: 输出迭代器
    """
    return parallel_processor.map(func, items, batch_size)
