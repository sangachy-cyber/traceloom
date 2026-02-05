# -*- coding: utf-8 -*-
"""编织服务模块

实现织径任务的执行逻辑，协调编织引擎、HoloWAN 适配器和设备管理
"""

import os
import time
from pathlib import Path
from typing import Optional

from loguru import logger

from traceloom.app.api.v1.schemas import WeaveRequest
from traceloom.core.interfaces import IWeaverService
from traceloom.core.response import ErrorResponse, WeaveResponse
from traceloom.core.response_handler import ResponseHandler
from traceloom.devices import HoloWAN
from traceloom.domain.pattern import PatternParser
from traceloom.io.adapters._holowan import HoloWANTrace
from traceloom.storage.pathlet_storage import PathletStorage
from traceloom.storage.task_store import TaskStore
from traceloom.weaving.engines import select_engine
from traceloom.weaving.sampler.global_sampler import GlobalSampler

# 导入 _get_weaving_engine 函数
from traceloom import _get_weaving_engine


class WeaverService(IWeaverService):
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

    def __init__(self, task_store: TaskStore, pathlet_storage: PathletStorage = None):
        """初始化编织服务

        参数:
            task_store: 任务存储实例
            pathlet_storage: 径元存储实例，若为 None 则创建默认实例
        """
        logger.info("初始化 WeaverService 开始")
        self.task_store = task_store
        # 初始化径元存储
        self.pathlet_storage = pathlet_storage or PathletStorage()
        # 初始化全局采样器
        self.sampler = GlobalSampler(self.pathlet_storage)
        logger.info("全局采样器初始化完成")
        # 初始化回放文件存储目录
        self.playback_dir = Path("tmp/playback")
        logger.debug(f"回放文件存储目录: {self.playback_dir}")
        self.playback_dir.mkdir(parents=True, exist_ok=True)
        logger.info("初始化 WeaverService 完成")
        # 初始化HoloWAN设备链接池
        self.holowan_manager_map = {}

    def _generate_holowan_content(self, weaving_pattern: str) -> str:
        """生成HoloWAN文件内容

        参数:
            weaving_pattern: 织样语法

        返回:
            str: HoloWAN文件内容
        """
        logger.info("生成HoloWAN文件内容开始")
        logger.debug(f"织样语法: {weaving_pattern}")

        # 使用 WeavingEngine 进行织径操作
        result = _get_weaving_engine().weave(weaving_pattern, mode="stitch")

        # 直接获取 HoloWANTrace 对象
        holowan_trace = result["trace"]

        # 创建一个临时文件路径
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            temp_file_path = f.name

        try:
            # 调用 dump 方法写入临时文件
            holowan_trace.dump(temp_file_path)
            logger.debug("HoloWAN 回放内容生成完成")

            # 读取临时文件内容
            with open(temp_file_path, "r") as f:
                holowan_content = f.read()
        finally:
            # 清理临时文件
            import os

            os.unlink(temp_file_path)

        logger.info("生成HoloWAN文件内容完成")
        return holowan_content

    def save_holowan_file(self, content: str, file_name: str) -> None:
        """保存HoloWAN文件

        参数:
            content: 文件内容
            file_name: 文件名
        """
        logger.info(f"保存HoloWAN文件开始，文件名: {file_name}")
        playback_file_path = self.playback_dir / file_name
        with open(playback_file_path, "w") as f:
            f.write(content)
        logger.info(f"回放文件保存成功: {playback_file_path}")

    def bind_ip_to_path(self, target_ip: str, device) -> dict:
        """绑定IP到路径

        参数:
            target_ip: 目标IP
            device: 设备信息

        返回:
            dict: 绑定结果
        """
        logger.info(f"绑定IP到路径开始，IP: {target_ip}")
        logger.debug(
            f"设备信息: host={device.host}, port={device.port}, engine_id={device.engine_id}, path_name={device.path_name}"
        )

        # 连接设备
        manager = self.holowan_manager_map.get(device.host, None)
        if manager is None:
            manager = HoloWAN(device.host, device.port, device.engine_id)
            self.holowan_manager_map[device.host] = manager

        manager.connect()
        logger.info("设备连接成功")

        # 获取 Path ID
        logger.info("获取 Path ID")
        path_id = manager.get_path_id_by_name(device.path_name)
        logger.info(f"获取 Path ID 成功: {path_id}")

        # 绑定 IP
        logger.info(f"绑定 IP: {target_ip} 到路径: {path_id}")
        manager.bind_ip_to_path(target_ip, path_id)
        logger.info("IP 绑定成功")

        logger.info("绑定IP到路径完成")
        return {"status": "success", "path_id": path_id}

    def apply_file(self, file_name: str, device) -> dict:
        """上传并应用文件到设备

        参数:
            file_name: 文件名
            device: 设备信息

        返回:
            dict: 应用结果
        """
        logger.info(f"上传并应用文件开始，文件名: {file_name}")
        logger.debug(
            f"设备信息: host={device.host}, port={device.port}, engine_id={device.engine_id}, path_name={device.path_name}"
        )

        # 获取文件路径
        playback_file_path = self.playback_dir / file_name
        if not playback_file_path.exists():
            raise FileNotFoundError(f"文件不存在: {playback_file_path}")

        # 连接设备
        manager = self.holowan_manager_map.get(device.host, None)
        if manager is None:
            manager = HoloWAN(device.host, device.port, device.engine_id)
            self.holowan_manager_map[device.host] = manager

        manager.connect()
        logger.info("设备连接成功")

        # 获取 Path ID
        logger.info("获取 Path ID")
        path_id = manager.get_path_id_by_name(device.path_name)
        logger.info(f"获取 Path ID 成功: {path_id}")

        # 上传并应用
        logger.info("上传并应用回放文件")
        manager.upload_and_apply_playback(playback_file_path.as_posix(), file_name, path_id)
        logger.info("回放文件上传并应用成功")
        # 短暂延迟，确保仿真启动
        time.sleep(1)

        logger.info("上传并应用文件完成")
        return {"status": "success", "path_id": path_id}

    def execute_task(self, task_id: str, request: WeaveRequest) -> Optional[WeaveResponse]:
        """执行织径任务

        参数:
            task_id: 任务唯一标识
            request: 编织请求对象

        返回:
            WeaveResponse: 编织响应对象
        """
        logger.info(f"执行织径任务开始，task_id: {task_id}")
        logger.debug(f"请求参数: target_ip={request.target_ip}, weaving_pattern={request.weaving_pattern}")
        logger.debug(
            f"设备信息: host={request.impairment_device.host}, port={request.impairment_device.port}, engine_id={request.impairment_device.engine_id}"
        )

        try:
            # 1. 生成HoloWAN文件内容
            logger.info("步骤 1: 生成HoloWAN文件内容")
            holowan_content = self._generate_holowan_content(request.weaving_pattern)

            # 2. 保存回放文件到服务端（用于下载）
            logger.info("步骤 2: 保存回放文件到服务端")
            playback_file_name = f"{task_id}.txt"
            self.save_holowan_file(holowan_content, playback_file_name)
            playback_file_path = self.playback_dir / playback_file_name
            # 更新任务的回放文件路径
            self.task_store.update_playback_file(task_id, str(playback_file_path))

            # 3. 任务基本信息已在create_task时保存
            logger.debug("任务基本信息已在创建时保存")

            # 4. 绑定IP到路径
            logger.info("步骤 3: 绑定IP到路径")
            self.task_store.update_status(task_id, "binding_flow")
            logger.debug("更新任务状态为: binding_flow")
            self.bind_ip_to_path(request.target_ip, request.impairment_device)

            # 5. 上传并应用文件
            logger.info("步骤 4: 上传并应用回放文件")
            self.task_store.update_status(task_id, "uploading_profile")
            logger.debug("更新任务状态为: uploading_profile")
            self.apply_file(playback_file_name, request.impairment_device)

            # 6. 更新任务状态为 running，并记录开始时间
            logger.info("步骤 5: 更新任务状态为 running")
            self.task_store.update_status(task_id, "running")
            logger.debug("更新任务状态为: running")
            self.task_store.update_started_at(task_id)
            logger.info("任务开始时间记录成功")

            # 7. 仿真持续运行，不再自动结束
            # 注意：生产环境中可以在这里设置一个后台任务，定期检查任务状态

            logger.info(f"织径任务执行完成，task_id: {task_id}")

            # 创建并返回响应
            download_url = f"/api/v1/weave/{task_id}/playback"
            return ResponseHandler.create_weave_response(
                task_id=task_id,
                engine="auto",
                status="accepted",
                message="网络损伤注入已启动（需手动停止）",
                download_url=download_url,
            )

        except Exception as e:
            logger.error(f"执行织径任务失败，task_id: {task_id}, 错误: {str(e)}")
            logger.exception("详细错误信息:")
            self.task_store.update_status(task_id, "failed", error=str(e))
            logger.debug(f"更新任务状态为: failed, 错误信息: {str(e)}")
            return None

    def execute_reweave(self, task_id: str, request: WeaveRequest) -> Optional[WeaveResponse]:
        """执行 Reweaver 织径任务

        参数:
            task_id: 任务唯一标识
            request: 编织请求对象

        返回:
            WeaveResponse: 编织响应对象
        """
        logger.info(f"执行 Reweaver 织径任务开始，task_id: {task_id}")
        # 暂时复用 execute_task 方法
        response = self.execute_task(task_id, request)
        logger.info(f"执行 Reweaver 织径任务完成，task_id: {task_id}")
        return response

    def execute_stitch(self, task_id: str, request: WeaveRequest) -> Optional[WeaveResponse]:
        """执行 Stitcher 织径任务

        参数:
            task_id: 任务唯一标识
            request: 编织请求对象

        返回:
            WeaveResponse: 编织响应对象
        """
        logger.info(f"执行 Stitcher 织径任务开始，task_id: {task_id}")
        # 暂时复用 execute_task 方法
        response = self.execute_task(task_id, request)
        logger.info(f"执行 Stitcher 织径任务完成，task_id: {task_id}")
        return response

    def execute_dream(self, task_id: str, request: WeaveRequest) -> Optional[WeaveResponse]:
        """执行 Dreamer 织径任务

        参数:
            task_id: 任务唯一标识
            request: 编织请求对象

        返回:
            WeaveResponse: 编织响应对象
        """
        logger.info(f"执行 Dreamer 织径任务开始，task_id: {task_id}")
        # 暂时复用 execute_task 方法
        response = self.execute_task(task_id, request)
        logger.info(f"执行 Dreamer 织径任务完成，task_id: {task_id}")
        return response

    def get_playback_file_path(self, task_id: str) -> Optional[str]:
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

    def cleanup_expired_files(self) -> None:
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

    def cancel_task(self, task_id: str) -> Optional[ErrorResponse]:
        """取消任务

        参数:
            task_id: 任务唯一标识

        返回:
            ErrorResponse: 错误响应对象，无错误时返回None
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
            playback_name = f"{task_id}.txt"
            logger.debug(f"清理参数: target_ip={target_ip}, playback_name={playback_name}, path_id={path_id}")
            manager.cleanup(target_ip, playback_name, path_id)
            logger.info("资源清理成功")

            # 更新状态
            logger.info("步骤 5: 更新任务状态")
            self.task_store.update_status(task_id, "completed", error="任务被用户取消")
            logger.info("任务状态更新为: completed, 错误信息: 任务被用户取消")

            logger.info(f"取消任务完成，task_id: {task_id}")
            return None

        except Exception as e:
            logger.error(f"取消任务失败，task_id: {task_id}, 错误: {str(e)}")
            logger.exception("详细错误信息:")
            self.task_store.update_status(task_id, "failed", error=f"取消任务失败: {str(e)}")
            logger.debug(f"更新任务状态为: failed, 错误信息: 取消任务失败: {str(e)}")
            return ResponseHandler.format_error_response(e)
