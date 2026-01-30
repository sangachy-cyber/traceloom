# -*- coding: utf-8 -*-
"""编织服务模块

实现织径任务的执行逻辑，协调编织引擎、HoloWAN 适配器和设备管理
"""

import tempfile
import time
from pathlib import Path

from loguru import logger

from traceloom.app.api.v1.schemas import WeaveRequest
from traceloom.devices import HoloWAN
from traceloom.domain.pattern import PatternParser
from traceloom.io.adapters._holowan import HoloWANTrace
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
        logger.info("初始化 WeaverService 开始")
        self.task_store = task_store
        # 初始化回放文件存储目录
        self.playback_dir = Path("tmp/playback")
        logger.debug(f"回放文件存储目录: {self.playback_dir}")
        self.playback_dir.mkdir(parents=True, exist_ok=True)
        logger.info("初始化 WeaverService 完成")

    def execute_task(self, task_id: str, request: WeaveRequest):
        """执行织径任务

        参数:
            task_id: 任务唯一标识
            request: 编织请求对象
        """
        logger.info(f"执行织径任务开始，task_id: {task_id}")
        logger.debug(f"请求参数: target_ip={request.target_ip}, weaving_pattern={request.weaving_pattern}")
        logger.debug(
            f"设备信息: host={request.impairment_device.host}, port={request.impairment_device.port}, engine_id={request.impairment_device.engine_id}"
        )

        try:
            # 1. 解析织样 & 选择引擎
            logger.info("步骤 1: 解析织样和选择引擎")
            pattern = PatternParser.parse(request.weaving_pattern)
            engine = select_engine(pattern)  # 返回 Reweaver/Stitcher/Dreamer
            logger.info(f"选择的引擎类型: {type(engine).__name__}")
            observations = engine.weave(pattern)
            logger.debug(f"生成的观测数据数量: {len(observations)}")

            # 2. 转为 HoloWAN 文件
            logger.info("步骤 2: 转换为 HoloWAN 文件")
            holowan_trace = HoloWANTrace()
            # 转换观测数据为数据点
            holowan_trace.data_points = [holowan_trace._observation_to_data_point(obs) for obs in observations]
            logger.info(f"数据点数量: {len(holowan_trace.data_points)}")
            # 生成严格格式的 HoloWAN 回放内容
            holowan_content = holowan_trace.dump()
            logger.debug("HoloWAN 回放内容生成完成")

            # 3. 保存回放文件到服务端（用于下载）
            logger.info("步骤 3: 保存回放文件到服务端")
            playback_file_name = f"{task_id}.txt"
            playback_file_path = self.playback_dir / playback_file_name
            with open(playback_file_path, "w") as f:
                f.write(holowan_content)
            # 更新任务的回放文件路径
            self.task_store.update_playback_file(task_id, str(playback_file_path))
            logger.info(f"回放文件保存成功: {playback_file_path}")

            # 4. 创建临时文件用于上传到 HoloWAN
            logger.info("步骤 4: 创建临时文件用于上传到 HoloWAN")
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                f.write(holowan_content)
                file_path = f.name
            playback_name = f"weaver_{task_id}.txt"
            logger.info(f"临时文件创建成功: {file_path}")
            logger.debug(f"回放文件名: {playback_name}")

            # 5. 连接设备
            logger.info("步骤 5: 连接设备")
            dev = request.impairment_device
            logger.info(f"连接设备: {dev.host}:{dev.port}, engine_id={dev.engine_id}")
            manager = HoloWAN(dev.host, dev.port, dev.engine_id)
            self.task_store.update_status(task_id, "connecting_device")
            logger.debug("更新任务状态为: connecting_device")
            manager.connect()
            logger.info("设备连接成功")
            self.task_store.update_status(task_id, "finding_path")
            logger.debug("更新任务状态为: finding_path")

            # 6. 获取 Path ID
            logger.info("步骤 6: 获取 Path ID")
            logger.debug(f"路径名称: {dev.path_name}")
            path_id = manager.get_path_id_by_name(dev.path_name)
            logger.info(f"获取 Path ID 成功: {path_id}")
            self.task_store.update_status(task_id, "binding_flow")
            logger.debug("更新任务状态为: binding_flow")

            # 7. 绑定 IP
            logger.info("步骤 7: 绑定 IP 到路径")
            logger.debug(f"绑定 IP: {request.target_ip} 到路径: {path_id}")
            manager.bind_ip_to_path(request.target_ip, path_id)
            logger.info("IP 绑定成功")
            self.task_store.update_status(task_id, "uploading_profile")
            logger.debug("更新任务状态为: uploading_profile")

            # 8. 上传并应用
            logger.info("步骤 8: 上传并应用回放文件")
            logger.debug(f"上传文件: {file_path}, 回放名称: {playback_name}, 路径 ID: {path_id}")
            manager.upload_and_apply_playback(file_path, playback_name, path_id)
            logger.info("回放文件上传并应用成功")
            # 短暂延迟，确保仿真启动
            time.sleep(1)

            # 9. 更新任务状态为 running，并记录开始时间
            logger.info("步骤 9: 更新任务状态为 running")
            self.task_store.update_status(task_id, "running")
            logger.debug("更新任务状态为: running")
            self.task_store.update_started_at(task_id)
            logger.info("任务开始时间记录成功")

            # 10. 仿真持续运行，不再自动结束
            # 注意：生产环境中可以在这里设置一个后台任务，定期检查任务状态

            logger.info(f"织径任务执行完成，task_id: {task_id}")

        except Exception as e:
            logger.error(f"执行织径任务失败，task_id: {task_id}, 错误: {str(e)}")
            logger.exception("详细错误信息:")
            self.task_store.update_status(task_id, "failed", error=str(e))
            logger.debug(f"更新任务状态为: failed, 错误信息: {str(e)}")

    def execute_reweave(self, task_id: str, request: WeaveRequest):
        """执行 Reweaver 织径任务

        参数:
            task_id: 任务唯一标识
            request: 编织请求对象
        """
        logger.info(f"执行 Reweaver 织径任务开始，task_id: {task_id}")
        # 这里应该实现 Reweaver 引擎的具体逻辑
        # 暂时复用 execute_task 方法
        self.execute_task(task_id, request)
        logger.info(f"执行 Reweaver 织径任务完成，task_id: {task_id}")

    def execute_stitch(self, task_id: str, request: WeaveRequest):
        """执行 Stitcher 织径任务

        参数:
            task_id: 任务唯一标识
            request: 编织请求对象
        """
        logger.info(f"执行 Stitcher 织径任务开始，task_id: {task_id}")
        # 这里应该实现 Stitcher 引擎的具体逻辑
        # 暂时复用 execute_task 方法
        self.execute_task(task_id, request)
        logger.info(f"执行 Stitcher 织径任务完成，task_id: {task_id}")

    def execute_dream(self, task_id: str, request: WeaveRequest):
        """执行 Dreamer 织径任务

        参数:
            task_id: 任务唯一标识
            request: 编织请求对象
        """
        logger.info(f"执行 Dreamer 织径任务开始，task_id: {task_id}")
        # 这里应该实现 Dreamer 引擎的具体逻辑
        # 暂时复用 execute_task 方法
        self.execute_task(task_id, request)
        logger.info(f"执行 Dreamer 织径任务完成，task_id: {task_id}")

    def get_playback_file_path(self, task_id: str):
        """获取任务的回放文件路径

        参数:
            task_id: 任务唯一标识

        返回:
            str: 回放文件路径，如果不存在返回 None
        """
        logger.info(f"获取任务回放文件路径，task_id: {task_id}")
        task_info = self.task_store.get_task(task_id)
        if not task_info:
            logger.warning(f"任务 {task_id} 不存在")
            return None
        playback_file_path = task_info.get("playback_file_path")
        logger.info(f"获取到回放文件路径: {playback_file_path}")
        return playback_file_path

    def cleanup_expired_files(self):
        """清理过期的回放文件

        删除超过 24 小时的回放文件
        """
        logger.info("开始清理过期的回放文件")
        logger.debug(f"回放文件存储目录: {self.playback_dir}")

        current_time = time.time()
        expired_threshold = 24 * 60 * 60  # 24 小时
        cleaned_count = 0
        error_count = 0

        for file_path in self.playback_dir.glob("*.txt"):
            if file_path.is_file():
                file_mtime = file_path.stat().st_mtime
                if current_time - file_mtime > expired_threshold:
                    try:
                        logger.debug(f"清理过期文件: {file_path}")
                        file_path.unlink()
                        cleaned_count += 1
                    except Exception as e:
                        logger.error(f"清理文件失败: {file_path}, 错误: {str(e)}")
                        error_count += 1
                        # 记录错误但继续执行
                        pass

        logger.info(f"清理过期文件完成，清理文件数量: {cleaned_count}, 错误数量: {error_count}")

    def cancel_task(self, task_id: str):
        """取消任务

        参数:
            task_id: 任务唯一标识
        """
        logger.info(f"取消任务开始，task_id: {task_id}")

        try:
            # 从任务存储中获取任务信息
            logger.info("步骤 1: 获取任务信息")
            task_info = self.task_store.get_task(task_id)
            if not task_info:
                raise ValueError(f"任务 {task_id} 不存在")
            logger.info(
                f"获取到任务信息: host={task_info.get('host')}, port={task_info.get('port')}, engine_id={task_info.get('engine_id')}"
            )

            # 连接设备
            logger.info("步骤 2: 连接设备")
            host = task_info["host"]
            port = task_info["port"]
            engine_id = task_info["engine_id"]
            path_name = task_info["path_name"]
            target_ip = task_info["target_ip"]

            logger.info(f"连接设备: host={host}, port={port}, engine_id={engine_id}")
            manager = HoloWAN(host, port, engine_id)
            manager.connect()
            logger.info("设备连接成功")

            # 获取 Path ID
            logger.info("步骤 3: 获取 Path ID")
            logger.debug(f"路径名称: {path_name}")
            path_id = manager.get_path_id_by_name(path_name)
            logger.info(f"获取 Path ID 成功: {path_id}")

            # 清理
            logger.info("步骤 4: 清理资源")
            playback_name = f"weaver_{task_id}.txt"
            logger.debug(f"清理参数: target_ip={target_ip}, playback_name={playback_name}, path_id={path_id}")
            manager.cleanup(target_ip, playback_name, path_id)
            logger.info("资源清理成功")

            # 更新状态
            logger.info("步骤 5: 更新任务状态")
            self.task_store.update_status(task_id, "completed", error="任务被用户取消")
            logger.info(f"任务状态更新为: completed, 错误信息: 任务被用户取消")

            logger.info(f"取消任务完成，task_id: {task_id}")

        except Exception as e:
            logger.error(f"取消任务失败，task_id: {task_id}, 错误: {str(e)}")
            logger.exception("详细错误信息:")
            self.task_store.update_status(task_id, "failed", error=f"取消任务失败: {str(e)}")
            logger.debug(f"更新任务状态为: failed, 错误信息: 取消任务失败: {str(e)}")
