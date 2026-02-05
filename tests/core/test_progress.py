# -*- coding: utf-8 -*-
"""进度管理模块测试

测试progress模块的功能
"""

import pytest

from traceloom.core.progress import ProgressManager, ProgressTracker, get_progress_manager, track_progress


def test_progress_tracker_basic():
    """测试基本的进度跟踪功能
    """
    tracker = ProgressTracker(total=5, description="Test Task")
    for _i in range(5):
        tracker.update()
    tracker.finish()
    # 测试应该正常完成，没有异常
    assert True


def test_progress_tracker_with_callback():
    """测试带回调函数的进度跟踪
    """
    progress_calls = []

    def callback(current, total, percent):
        progress_calls.append((current, total, percent))

    tracker = ProgressTracker(
        total=5,
        description="Test Task",
        callback=callback
    )

    for _i in range(5):
        tracker.update()
    tracker.finish()

    # 应该至少有一次回调
    assert len(progress_calls) > 0
    # 最后一次回调应该是完成状态
    assert progress_calls[-1][0] == 5
    assert progress_calls[-1][1] == 5
    assert progress_calls[-1][2] >= 100


def test_progress_tracker_context_manager():
    """测试使用上下文管理器的进度跟踪
    """
    progress_calls = []

    def callback(current, total, percent):
        progress_calls.append((current, total, percent))

    with ProgressTracker(
        total=5,
        description="Test Task",
        callback=callback
    ) as tracker:
        for _i in range(5):
            tracker.update()

    # 应该至少有一次回调
    assert len(progress_calls) > 0
    # 最后一次回调应该是完成状态
    assert progress_calls[-1][0] == 5
    assert progress_calls[-1][1] == 5


def test_progress_manager():
    """测试进度管理器
    """
    manager = ProgressManager()

    # 添加跟踪器
    tracker1 = manager.add_tracker(
        name="task1",
        total=3,
        description="Task 1"
    )

    tracker2 = manager.add_tracker(
        name="task2",
        total=2,
        description="Task 2"
    )

    # 更新进度
    tracker1.update()
    tracker2.update()

    # 获取跟踪器
    retrieved_tracker = manager.get_tracker("task1")
    assert retrieved_tracker is tracker1

    # 完成所有任务
    manager.finish_all()

    # 清除所有跟踪器
    manager.clear()
    assert len(manager.trackers) == 0


def test_get_progress_manager():
    """测试获取全局进度管理器
    """
    manager1 = get_progress_manager()
    manager2 = get_progress_manager()
    # 应该返回同一个实例
    assert manager1 is manager2


def test_track_progress_function():
    """测试track_progress函数
    """
    progress_calls = []

    def callback(current, total, percent):
        progress_calls.append((current, total, percent))

    # 使用函数创建跟踪器
    tracker = track_progress(
        total=3,
        description="Test Task",
        callback=callback
    )

    for _i in range(3):
        tracker.update()
    tracker.finish()

    # 应该至少有一次回调
    assert len(progress_calls) > 0


def test_track_progress_context_manager():
    """测试使用上下文管理器的track_progress函数
    """
    progress_calls = []

    def callback(current, total, percent):
        progress_calls.append((current, total, percent))

    with track_progress(
        total=3,
        description="Test Task",
        callback=callback
    ) as tracker:
        for _i in range(3):
            tracker.update()

    # 应该至少有一次回调
    assert len(progress_calls) > 0
    # 最后一次回调应该是完成状态
    assert progress_calls[-1][0] == 3
    assert progress_calls[-1][1] == 3


if __name__ == "__main__":
    pytest.main([__file__])
