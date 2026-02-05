# -*- coding: utf-8 -*-
"""并行处理模块测试

测试ParallelProcessor类的功能
"""

import time

import pytest

from traceloom.core.parallel import ParallelProcessor, parallel_map, parallel_process


def test_parallel_process_basic():
    """测试基本的并行处理功能
    """
    processor = ParallelProcessor()
    items = [1, 2, 3, 4, 5]
    results = processor.process(items, lambda x: x * 2)
    assert results == [2, 4, 6, 8, 10]


def test_parallel_process_batch():
    """测试批处理功能
    """
    processor = ParallelProcessor()
    items = [1, 2, 3, 4, 5]

    def batch_func(batch):
        return [item * 2 for item in batch]

    results = processor.process(items, batch_func, batch_size=2)
    # 结果应该是展平的
    assert sorted(results) == [2, 4, 6, 8, 10]


def test_parallel_process_with_progress():
    """测试带进度回调的并行处理
    """
    processor = ParallelProcessor()
    items = [1, 2, 3, 4, 5]
    progress_calls = []

    def progress_func(done, total):
        progress_calls.append((done, total))

    results = processor.process(items, lambda x: x * 2, progress_callback=progress_func)
    assert results == [2, 4, 6, 8, 10]
    # 应该至少有一次进度更新
    assert len(progress_calls) > 0
    # 最后一次调用应该是完成状态
    assert progress_calls[-1] == (5, 5)


def test_parallel_map():
    """测试并行映射功能
    """
    processor = ParallelProcessor()
    items = range(5)
    results = list(processor.map(lambda x: x * 2, items))
    assert results == [0, 2, 4, 6, 8]


def test_parallel_map_with_batch():
    """测试带批处理的并行映射功能
    """
    processor = ParallelProcessor()
    items = range(5)

    def batch_func(batch):
        return [item * 2 for item in batch]

    results = list(processor.map(batch_func, items, batch_size=2))
    # 结果应该是展平的
    assert sorted(results) == [0, 2, 4, 6, 8]


def test_parallel_process_with_exception():
    """测试并行处理中的异常处理
    """
    processor = ParallelProcessor()
    items = [1, 2, 3, 4, 5]

    def error_func(x):
        if x == 3:
            raise ValueError("Test error")
        return x * 2

    results = processor.process(items, error_func)
    # 出错的项目应该返回None
    assert results[0] == 2
    assert results[1] == 4
    assert results[2] is None
    assert results[3] == 8
    assert results[4] == 10


def test_convenience_functions():
    """测试便捷函数
    """
    # 测试parallel_process
    items = [1, 2, 3, 4, 5]
    results = parallel_process(items, lambda x: x * 2)
    assert results == [2, 4, 6, 8, 10]

    # 测试parallel_map
    items = range(5)
    map_results = list(parallel_map(lambda x: x * 2, items))
    assert map_results == [0, 2, 4, 6, 8]


def test_performance():
    """测试性能
    """
    processor = ParallelProcessor()
    items = list(range(100))

    start_time = time.time()
    results = processor.process(items, lambda x: time.sleep(0.01) or x * 2)
    parallel_time = time.time() - start_time

    # 串行处理
    start_time = time.time()
    serial_results = [x * 2 for x in items]
    serial_time = time.time() - start_time

    # 并行处理应该比串行处理快
    assert parallel_time < serial_time * 0.8  # 至少快20%
    assert results == serial_results


if __name__ == "__main__":
    pytest.main([__file__])
