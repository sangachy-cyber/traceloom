# -*- coding: utf-8 -*-
"""编织服务模块

实现织径任务的执行逻辑，协调编织引擎、HoloWAN 适配器和设备管理
"""

import tempfile
import time
from pathlib import Path

from traceloom.app.api.v1.schemas import WeaveRequest
from traceloom.devices.holowan_manager import HoloWANManager
from traceloom.domain.pattern import PatternParser
from traceloom.io.adapters.holowan import HoloWANTrace
from traceloom.storage.task_store import TaskStore
from traceloom.weaving.engines import select_engine


class WeaverService:
    """编织服务类，执行织径任务

    示例:
        from traceloom.services.weaver_service import WeaverService
        from traceloom.storage.task_store import TaskStore
        from traceloom.app.api.v1.schemas import WeaveRequest

        # 创建任务存储实例
        task_store = TaskStore()

        # 创建编织服务实例
        weaver_service = WeaverService(task_store)

        # 执行任务
        task_id = "task_123"
        request = WeaveRequest(...)
        weaver_service.execute_task(task_id, request)
    """

    def __init__(self, task_store: TaskStore):
        """初始化编织服务

        参数:
            task_store: 任务存储实例
        """
        self.task_store = task_store
        # 初始化回放文件存储目录
        self.playback_dir = Path("tmp/playback")
        self.playback_dir.mkdir(parents=True, exist_ok=True)

    def execute_task(self, task_id: str, request: WeaveRequest):
        """执行织径任务

        参数:
            task_id: 任务唯一标识
            request: 编织请求对象
        """
        try:
            # 1. 解析织样 & 选择引擎
            pattern = PatternParser.parse(request.weaving_pattern)
            engine = select_engine(pattern)  # 返回 Reweaver/Stitcher/Dreamer
            observations = engine.weave(pattern)

            # 2. 转为 HoloWAN 文件
            holowan_trace = HoloWANTrace()
            # 转换观测数据为数据点
            holowan_trace.data_points = [holowan_trace._observation_to_data_point(obs) for obs in observations]
            # 生成严格格式的 HoloWAN 回放内容
            holowan_content = holowan_trace.dump()

            # 3. 保存回放文件到服务端（用于下载）
            playback_file_name = f"{task_id}.txt"
            playback_file_path = self.playback_dir / playback_file_name
            with open(playback_file_path, "w") as f:
                f.write(holowan_content)
            # 更新任务的回放文件路径
            self.task_store.update_playback_file(task_id, str(playback_file_path))

            # 4. 创建临时文件用于上传到 HoloWAN
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(holowan_content)
                file_path = f.name
            playback_name = f"weaver_{task_id}.txt"

            # 5. 连接设备
            dev = request.impairment_device
            manager = HoloWANManager(dev.host, dev.port, dev.engine_id)
            self.task_store.update_status(task_id, "connecting_device")
            manager.connect()
            self.task_store.update_status(task_id, "finding_path")

            # 6. 获取 Path ID
            path_id = manager.get_path_id_by_name(dev.path_name)
            self.task_store.update_status(task_id, "binding_flow")

            # 7. 绑定 IP
            manager.bind_ip_to_path(request.target_ip, path_id)
            self.task_store.update_status(task_id, "uploading_profile")

            # 8. 上传并应用
            manager.upload_and_apply_playback(file_path, playback_name, path_id)
            # 短暂延迟，确保仿真启动
            time.sleep(1)

            # 9. 更新任务状态为 running，并记录开始时间
            self.task_store.update_status(task_id, "running")
            self.task_store.update_started_at(task_id)

            # 10. 仿真持续运行，不再自动结束
            # 注意：生产环境中可以在这里设置一个后台任务，定期检查任务状态

        except Exception as e:
            self.task_store.update_status(task_id, "failed", error=str(e))

    def execute_reweave(self, task_id: str, request: WeaveRequest):
        """执行 Reweaver 织径任务

        参数:
            task_id: 任务唯一标识
            request: 编织请求对象
        """
        # 这里应该实现 Reweaver 引擎的具体逻辑
        # 暂时复用 execute_task 方法
        self.execute_task(task_id, request)

    def execute_stitch(self, task_id: str, request: WeaveRequest):
        """执行 Stitcher 织径任务

        参数:
            task_id: 任务唯一标识
            request: 编织请求对象
        """
        # 这里应该实现 Stitcher 引擎的具体逻辑
        # 暂时复用 execute_task 方法
        self.execute_task(task_id, request)

    def execute_dream(self, task_id: str, request: WeaveRequest):
        """执行 Dreamer 织径任务

        参数:
            task_id: 任务唯一标识
            request: 编织请求对象
        """
        # 这里应该实现 Dreamer 引擎的具体逻辑
        # 暂时复用 execute_task 方法
        self.execute_task(task_id, request)

    def get_playback_file_path(self, task_id: str):
        """获取任务的回放文件路径

        参数:
            task_id: 任务唯一标识

        返回:
            str: 回放文件路径，如果不存在返回 None
        """
        task_info = self.task_store.get_task(task_id)
        if not task_info:
            return None
        return task_info.get("playback_file_path")

    def cleanup_expired_files(self):
        """清理过期的回放文件

        删除超过 24 小时的回放文件
        """
        current_time = time.time()
        for file_path in self.playback_dir.glob("*.txt"):
            if file_path.is_file():
                file_mtime = file_path.stat().st_mtime
                if current_time - file_mtime > 24 * 60 * 60:  # 24 小时
                    try:
                        file_path.unlink()
                    except Exception:
                        # 记录错误但继续执行
                        pass

    def cancel_task(self, task_id: str):
        """取消任务

        参数:
            task_id: 任务唯一标识
        """
        try:
            # 从任务存储中获取任务信息
            task_info = self.task_store.get_task(task_id)
            if not task_info:
                raise ValueError(f"任务 {task_id} 不存在")

            # 连接设备
            host = task_info["host"]
            port = task_info["port"]
            engine_id = task_info["engine_id"]
            path_name = task_info["path_name"]
            target_ip = task_info["target_ip"]

            manager = HoloWANManager(host, port, engine_id)
            manager.connect()

            # 获取 Path ID
            path_id = manager.get_path_id_by_name(path_name)

            # 清理
            playback_name = f"weaver_{task_id}.txt"
            manager.cleanup(target_ip, playback_name, path_id)

            # 更新状态
            self.task_store.update_status(task_id, "completed", error="任务被用户取消")
        except Exception as e:
            self.task_store.update_status(task_id, "failed", error=f"取消任务失败: {str(e)}")
