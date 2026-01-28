# -*- coding: utf-8 -*-
"""TraceLoom API v1 端点定义
包含各种 API 路由和处理函数
"""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from traceloom.core.logger import logger
from traceloom.services.weaver_service import WeaverService
from traceloom.storage.task_store import TaskStore

from .schemas import (
    HealthCheckResponse,
    ImpairmentDevice,
    TaskStatusResponse,
    TaskStopResponse,
    WeaveRequest,
    WeaveResponse,
)

router = APIRouter()

# 初始化服务
task_store = TaskStore()
weaver_service = WeaverService(task_store)


@router.get("/health", response_model=HealthCheckResponse, tags=["system"])
def health_check():
    """健康检查端点

    返回服务的健康状态
    """
    return HealthCheckResponse(status="ok", timestamp=datetime.now(), version="1.0.0")


def _generate_task_id(prefix: str) -> str:
    """生成任务唯一标识

    参数:
        prefix: 任务前缀

    返回:
        str: 任务唯一标识
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    return f"{prefix}_{timestamp}"


def _create_task_response(task_id: str, engine: str, status: str, message: str, prefix: str) -> WeaveResponse:
    """创建任务响应

    参数:
        task_id: 任务唯一标识
        engine: 引擎名称
        status: 任务状态
        message: 响应消息
        prefix: 路径前缀

    返回:
        WeaveResponse: 任务响应
    """
    download_url = f"/api/v1/{prefix}/{task_id}/playback"
    return WeaveResponse(
        task_id=task_id,
        engine=engine,
        status=status,
        message=message,
        download_url=download_url,
    )


def _create_status_response(task_info: dict, prefix: str) -> TaskStatusResponse:
    """创建状态响应

    参数:
        task_info: 任务信息
        prefix: 路径前缀

    返回:
        TaskStatusResponse: 状态响应
    """
    impairment_device = ImpairmentDevice(
        host=task_info["host"],
        port=task_info["port"],
        engine_id=task_info["engine_id"],
        path_name=task_info["path_name"],
    )
    download_url = f"/api/v1/{prefix}/{task_info['task_id']}/playback"
    return TaskStatusResponse(
        task_id=task_info["task_id"],
        engine=task_info["engine"],
        status=task_info["status"],
        target_ip=task_info["target_ip"],
        weaving_pattern=task_info["weaving_pattern"],
        impairment_device=impairment_device,
        started_at=task_info["started_at"],
        download_url=download_url,
    )


def _create_stop_response(task_id: str, status: str, message: str, prefix: str) -> TaskStopResponse:
    """创建停止响应

    参数:
        task_id: 任务唯一标识
        status: 任务状态
        message: 响应消息
        prefix: 路径前缀

    返回:
        TaskStopResponse: 停止响应
    """
    download_url = f"/api/v1/{prefix}/{task_id}/playback"
    return TaskStopResponse(
        task_id=task_id,
        status=status,
        message=message,
        download_url=download_url,
    )


@router.post("/weave", response_model=WeaveResponse, tags=["weaver"])
def weave(request: WeaveRequest, background_tasks: BackgroundTasks):
    """自动选择引擎端点

    根据织样自动选择合适的引擎执行织径任务
    """
    try:
        # 生成任务ID
        task_id = _generate_task_id("weave")

        # 创建任务
        task_store.create_task(task_id, request, "auto")

        # 后台执行任务
        background_tasks.add_task(weaver_service.execute_task, task_id, request)

        # 返回响应
        return _create_task_response(
            task_id=task_id,
            engine="auto",
            status="accepted",
            message="网络损伤注入已启动（需手动停止）",
            prefix="weave",
        )
    except Exception as e:
        logger.error(f"执行织径任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"执行织径任务失败: {str(e)}") from e


@router.post("/reweave", response_model=WeaveResponse, tags=["weaver"])
def reweave(request: WeaveRequest, background_tasks: BackgroundTasks):
    """显式指定 Reweaver 端点

    使用 Reweaver 引擎执行织径任务
    """
    try:
        # 生成任务ID
        task_id = _generate_task_id("reweave")

        # 创建任务
        task_store.create_task(task_id, request, "reweaver")

        # 后台执行任务
        background_tasks.add_task(weaver_service.execute_reweave, task_id, request)

        # 返回响应
        return _create_task_response(
            task_id=task_id,
            engine="reweaver",
            status="accepted",
            message="网络损伤注入已启动（需手动停止）",
            prefix="reweave",
        )
    except Exception as e:
        logger.error(f"执行 Reweaver 任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"执行 Reweaver 任务失败: {str(e)}") from e


@router.post("/stitch", response_model=WeaveResponse, tags=["weaver"])
def stitch(request: WeaveRequest, background_tasks: BackgroundTasks):
    """显式指定 Stitcher 端点

    使用 Stitcher 引擎执行织径任务
    """
    try:
        # 生成任务ID
        task_id = _generate_task_id("stitch")

        # 创建任务
        task_store.create_task(task_id, request, "stitcher")

        # 后台执行任务
        background_tasks.add_task(weaver_service.execute_stitch, task_id, request)

        # 返回响应
        return _create_task_response(
            task_id=task_id,
            engine="stitcher",
            status="accepted",
            message="网络损伤注入已启动（需手动停止）",
            prefix="stitch",
        )
    except Exception as e:
        logger.error(f"执行 Stitcher 任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"执行 Stitcher 任务失败: {str(e)}") from e


@router.post("/dream", response_model=WeaveResponse, tags=["weaver"])
def dream(request: WeaveRequest, background_tasks: BackgroundTasks):
    """显式指定 Dreamer 端点

    使用 Dreamer 引擎执行织径任务
    """
    try:
        # 生成任务ID
        task_id = _generate_task_id("dream")

        # 创建任务
        task_store.create_task(task_id, request, "dreamer")

        # 后台执行任务
        background_tasks.add_task(weaver_service.execute_dream, task_id, request)

        # 返回响应
        return _create_task_response(
            task_id=task_id,
            engine="dreamer",
            status="accepted",
            message="网络损伤注入已启动（需手动停止）",
            prefix="dream",
        )
    except Exception as e:
        logger.error(f"执行 Dreamer 任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"执行 Dreamer 任务失败: {str(e)}") from e


@router.get("/weave/{task_id}", response_model=TaskStatusResponse, tags=["weaver"])
def get_weave_status(task_id: str):
    """查询自动选择引擎任务状态

    查询使用自动选择引擎执行的织径任务状态
    """
    task_info = task_store.get_task(task_id)
    if not task_info:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    return _create_status_response(task_info, "weave")


@router.get("/reweave/{task_id}", response_model=TaskStatusResponse, tags=["weaver"])
def get_reweave_status(task_id: str):
    """查询 Reweaver 任务状态

    查询使用 Reweaver 引擎执行的织径任务状态
    """
    task_info = task_store.get_task(task_id)
    if not task_info:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    return _create_status_response(task_info, "reweave")


@router.get("/stitch/{task_id}", response_model=TaskStatusResponse, tags=["weaver"])
def get_stitch_status(task_id: str):
    """查询 Stitcher 任务状态

    查询使用 Stitcher 引擎执行的织径任务状态
    """
    task_info = task_store.get_task(task_id)
    if not task_info:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    return _create_status_response(task_info, "stitch")


@router.get("/dream/{task_id}", response_model=TaskStatusResponse, tags=["weaver"])
def get_dream_status(task_id: str):
    """查询 Dreamer 任务状态

    查询使用 Dreamer 引擎执行的织径任务状态
    """
    task_info = task_store.get_task(task_id)
    if not task_info:
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")
    return _create_status_response(task_info, "dream")


@router.delete("/weave/{task_id}", response_model=TaskStopResponse, tags=["weaver"])
def stop_weave_task(task_id: str):
    """停止自动选择引擎任务

    停止使用自动选择引擎执行的织径任务
    """
    try:
        # 停止任务
        weaver_service.cancel_task(task_id)

        # 返回响应
        return _create_stop_response(
            task_id=task_id,
            status="completed",
            message="仿真已停止，HoloWAN 设备资源已清理",
            prefix="weave",
        )
    except Exception as e:
        logger.error(f"停止任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止任务失败: {str(e)}") from e


@router.delete("/reweave/{task_id}", response_model=TaskStopResponse, tags=["weaver"])
def stop_reweave_task(task_id: str):
    """停止 Reweaver 任务

    停止使用 Reweaver 引擎执行的织径任务
    """
    try:
        # 停止任务
        weaver_service.cancel_task(task_id)

        # 返回响应
        return _create_stop_response(
            task_id=task_id,
            status="completed",
            message="仿真已停止，HoloWAN 设备资源已清理",
            prefix="reweave",
        )
    except Exception as e:
        logger.error(f"停止任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止任务失败: {str(e)}") from e


@router.delete("/stitch/{task_id}", response_model=TaskStopResponse, tags=["weaver"])
def stop_stitch_task(task_id: str):
    """停止 Stitcher 任务

    停止使用 Stitcher 引擎执行的织径任务
    """
    try:
        # 停止任务
        weaver_service.cancel_task(task_id)

        # 返回响应
        return _create_stop_response(
            task_id=task_id,
            status="completed",
            message="仿真已停止，HoloWAN 设备资源已清理",
            prefix="stitch",
        )
    except Exception as e:
        logger.error(f"停止任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止任务失败: {str(e)}") from e


@router.delete("/dream/{task_id}", response_model=TaskStopResponse, tags=["weaver"])
def stop_dream_task(task_id: str):
    """停止 Dreamer 任务

    停止使用 Dreamer 引擎执行的织径任务
    """
    try:
        # 停止任务
        weaver_service.cancel_task(task_id)

        # 返回响应
        return _create_stop_response(
            task_id=task_id,
            status="completed",
            message="仿真已停止，HoloWAN 设备资源已清理",
            prefix="dream",
        )
    except Exception as e:
        logger.error(f"停止任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止任务失败: {str(e)}") from e


@router.get("/weave/{task_id}/playback", tags=["weaver"])
def download_weave_playback(task_id: str):
    """下载自动选择引擎回放文件

    下载使用自动选择引擎执行的织径任务的回放文件
    """
    playback_file_path = weaver_service.get_playback_file_path(task_id)
    if not playback_file_path or not Path(playback_file_path).exists():
        raise HTTPException(status_code=404, detail=f"回放文件不存在")
    return FileResponse(
        path=playback_file_path,
        media_type="text/plain",
        filename=f"{task_id}.txt",
    )


@router.get("/reweave/{task_id}/playback", tags=["weaver"])
def download_reweave_playback(task_id: str):
    """下载 Reweaver 回放文件

    下载使用 Reweaver 引擎执行的织径任务的回放文件
    """
    playback_file_path = weaver_service.get_playback_file_path(task_id)
    if not playback_file_path or not Path(playback_file_path).exists():
        raise HTTPException(status_code=404, detail=f"回放文件不存在")
    return FileResponse(
        path=playback_file_path,
        media_type="text/plain",
        filename=f"{task_id}.txt",
    )


@router.get("/stitch/{task_id}/playback", tags=["weaver"])
def download_stitch_playback(task_id: str):
    """下载 Stitcher 回放文件

    下载使用 Stitcher 引擎执行的织径任务的回放文件
    """
    playback_file_path = weaver_service.get_playback_file_path(task_id)
    if not playback_file_path or not Path(playback_file_path).exists():
        raise HTTPException(status_code=404, detail=f"回放文件不存在")
    return FileResponse(
        path=playback_file_path,
        media_type="text/plain",
        filename=f"{task_id}.txt",
    )


@router.get("/dream/{task_id}/playback", tags=["weaver"])
def download_dream_playback(task_id: str):
    """下载 Dreamer 回放文件

    下载使用 Dreamer 引擎执行的织径任务的回放文件
    """
    playback_file_path = weaver_service.get_playback_file_path(task_id)
    if not playback_file_path or not Path(playback_file_path).exists():
        raise HTTPException(status_code=404, detail=f"回放文件不存在")
    return FileResponse(
        path=playback_file_path,
        media_type="text/plain",
        filename=f"{task_id}.txt",
    )
