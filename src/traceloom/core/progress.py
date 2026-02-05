# -*- coding: utf-8 -*-
"""进度管理模块

提供进度跟踪和显示的功能，增强用户体验。
"""

import time
from typing import Any, Callable, Optional

from traceloom.core.logger import logger


class ProgressTracker:
    """进度跟踪器

    用于跟踪长时间运行操作的进度，并提供进度反馈
    """

    def __init__(
        self,
        total: int,
        description: str = "Processing",
        update_interval: float = 0.5,
        callback: Optional[Callable[[int, int, float], None]] = None
    ):
        """初始化进度跟踪器

        Args:
            total: 总任务数
            description: 任务描述
            update_interval: 进度更新间隔（秒）
            callback: 进度更新回调函数，接收当前进度、总任务数和百分比
        """
        self.total = total
        self.description = description
        self.update_interval = update_interval
        self.callback = callback

        self.current = 0
        self.start_time = time.time()
        self.last_update_time = 0
        self.last_progress = 0

    def update(self, increment: int = 1) -> None:
        """更新进度

        Args:
            increment: 进度增量
        """
        self.current += increment
        current_time = time.time()

        # 计算进度百分比
        progress_percent = min(100.0, (self.current / self.total) * 100)

        # 检查是否需要更新
        if (current_time - self.last_update_time >= self.update_interval or
            progress_percent >= 100 or
            int(progress_percent) > int(self.last_progress)):

            # 计算剩余时间
            elapsed_time = current_time - self.start_time
            if progress_percent > 0:
                estimated_total_time = elapsed_time / (progress_percent / 100)
                remaining_time = estimated_total_time - elapsed_time
            else:
                remaining_time = 0

            # 调用回调函数
            if self.callback:
                self.callback(self.current, self.total, progress_percent)
            else:
                # 默认的进度显示
                self._default_callback(self.current, self.total, progress_percent, remaining_time)

            # 更新时间戳和进度
            self.last_update_time = current_time
            self.last_progress = progress_percent

    def _default_callback(
        self,
        current: int,
        total: int,
        progress_percent: float,
        remaining_time: float
    ) -> None:
        """默认的进度回调函数

        Args:
            current: 当前进度
            total: 总任务数
            progress_percent: 进度百分比
            remaining_time: 剩余时间（秒）
        """
        # 构建进度消息
        progress_bar = self._build_progress_bar(progress_percent)
        time_str = self._format_time(remaining_time)

        # 打印进度消息
        message = f"{self.description}: {progress_bar} {progress_percent:.1f}% ({current}/{total}) ETA: {time_str}"

        # 使用logger.info打印进度消息
        logger.info(message)

    def _build_progress_bar(self, progress_percent: float) -> str:
        """构建进度条

        Args:
            progress_percent: 进度百分比

        Returns:
            str: 进度条字符串
        """
        bar_length = 50
        filled_length = int(bar_length * progress_percent / 100)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        return f"[{bar}]"

    def _format_time(self, seconds: float) -> str:
        """格式化时间

        Args:
            seconds: 秒数

        Returns:
            str: 格式化的时间字符串
        """
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{int(minutes)}m {int(seconds)}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{int(hours)}h {int(minutes)}m"

    def finish(self) -> None:
        """完成进度跟踪

        标记任务完成，并显示最终进度
        """
        # 确保进度显示为100%
        self.current = self.total
        self.update(0)

        # 计算总耗时
        total_time = time.time() - self.start_time
        time_str = self._format_time(total_time)

        # 显示完成消息
        message = f"{self.description}: 完成! 总耗时: {time_str}"
        logger.info(message)

    def __enter__(self) -> "ProgressTracker":
        """进入上下文管理器

        Returns:
            ProgressTracker: 进度跟踪器实例
        """
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """退出上下文管理器

        Args:
            exc_type: 异常类型
            exc_val: 异常值
            exc_tb: 异常回溯
        """
        if exc_type is None:
            # 如果没有异常，标记任务完成
            self.finish()
        else:
            # 如果有异常，显示错误消息
            message = f"{self.description}: 出错!"
            logger.error(message)


class ProgressManager:
    """进度管理器

    管理多个进度跟踪器，用于复杂任务的进度跟踪
    """

    def __init__(self):
        """初始化进度管理器
        """
        self.trackers: dict[str, ProgressTracker] = {}

    def add_tracker(
        self,
        name: str,
        total: int,
        description: str = "Processing",
        update_interval: float = 0.5,
        callback: Optional[Callable[[int, int, float], None]] = None
    ) -> ProgressTracker:
        """添加进度跟踪器

        Args:
            name: 跟踪器名称
            total: 总任务数
            description: 任务描述
            update_interval: 进度更新间隔（秒）
            callback: 进度更新回调函数

        Returns:
            ProgressTracker: 进度跟踪器实例
        """
        tracker = ProgressTracker(
            total=total,
            description=description,
            update_interval=update_interval,
            callback=callback
        )
        self.trackers[name] = tracker
        return tracker

    def get_tracker(self, name: str) -> Optional[ProgressTracker]:
        """获取进度跟踪器

        Args:
            name: 跟踪器名称

        Returns:
            Optional[ProgressTracker]: 进度跟踪器实例，如果不存在则返回None
        """
        return self.trackers.get(name)

    def update_tracker(self, name: str, increment: int = 1) -> None:
        """更新指定的进度跟踪器

        Args:
            name: 跟踪器名称
            increment: 进度增量
        """
        tracker = self.get_tracker(name)
        if tracker:
            tracker.update(increment)

    def finish_tracker(self, name: str) -> None:
        """完成指定的进度跟踪器

        Args:
            name: 跟踪器名称
        """
        tracker = self.get_tracker(name)
        if tracker:
            tracker.finish()

    def finish_all(self) -> None:
        """完成所有进度跟踪器
        """
        for name in list(self.trackers.keys()):
            self.finish_tracker(name)

    def clear(self) -> None:
        """清除所有进度跟踪器
        """
        self.trackers.clear()


# 全局进度管理器实例
global_progress_manager = ProgressManager()


def get_progress_manager() -> ProgressManager:
    """获取全局进度管理器

    Returns:
        ProgressManager: 全局进度管理器实例
    """
    return global_progress_manager


def track_progress(
    total: int,
    description: str = "Processing",
    update_interval: float = 0.5,
    callback: Optional[Callable[[int, int, float], None]] = None
) -> ProgressTracker:
    """创建并返回一个进度跟踪器

    Args:
        total: 总任务数
        description: 任务描述
        update_interval: 进度更新间隔（秒）
        callback: 进度更新回调函数

    Returns:
        ProgressTracker: 进度跟踪器实例

    Examples:
        # 使用上下文管理器
        with track_progress(100, "Processing items") as tracker:
            for i in range(100):
                # 处理任务
                time.sleep(0.1)
                # 更新进度
                tracker.update()

        # 不使用上下文管理器
        tracker = track_progress(100, "Processing items")
        for i in range(100):
            # 处理任务
            time.sleep(0.1)
            # 更新进度
            tracker.update()
        # 标记完成
        tracker.finish()
    """
    return ProgressTracker(
        total=total,
        description=description,
        update_interval=update_interval,
        callback=callback
    )
