# -*- coding: utf-8 -*-
"""TraceLoom API v1 端点定义
包含各种 API 路由和处理函数
"""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import FileResponse

from traceloom.core.logger import logger
from traceloom.services.weaver_service import WeaverService
from traceloom.storage.pathlet_storage import PathletStorage
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
pathlet_storage = PathletStorage()
weaver_service = WeaverService(task_store, pathlet_storage)


@router.get("/health", response_model=HealthCheckResponse, tags=["system"])
def health_check(request: Request):
    """健康检查端点

    返回服务的健康状态
    """
    timestamp = datetime.now()
    logger.info(
        f"[API] 请求开始 | 路径: {request.url.path} | 方法: {request.method} | 参数: {dict(request.query_params)} | 时间戳: {timestamp}"
    )

    response = HealthCheckResponse(status="ok", timestamp=timestamp, version="1.0.0")

    logger.info(f"[API] 请求完成 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: ok")
    return response


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
def weave(request: Request, weave_request: WeaveRequest, background_tasks: BackgroundTasks):
    """自动选择引擎端点

    根据织样自动选择合适的引擎执行织径任务
    """
    timestamp = datetime.now()
    logger.info(
        f"[API] 请求开始 | 路径: {request.url.path} | 方法: {request.method} | 参数: {weave_request.model_dump()} | 时间戳: {timestamp}"
    )

    try:
        # 生成任务ID
        task_id = _generate_task_id("weave")

        # 创建任务
        task_store.create_task(task_id, weave_request, "auto")

        # 后台执行任务
        background_tasks.add_task(weaver_service.execute_task, task_id, weave_request)

        # 返回响应
        response = _create_task_response(
            task_id=task_id,
            engine="auto",
            status="accepted",
            message="网络损伤注入已启动（需手动停止）",
            prefix="weave",
        )

        logger.info(
            f"[API] 请求完成 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: accepted | 任务ID: {task_id}"
        )
        return response
    except Exception as e:
        logger.error(f"执行织径任务失败: {e}")
        logger.info(
            f"[API] 请求失败 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: error"
        )
        raise HTTPException(status_code=500, detail=f"执行织径任务失败: {str(e)}") from e


@router.post("/reweave", response_model=WeaveResponse, tags=["weaver"])
def reweave(request: Request, weave_request: WeaveRequest, background_tasks: BackgroundTasks):
    """显式指定 Reweave 端点

    使用 Reweave 引擎执行织径任务
    """
    timestamp = datetime.now()
    logger.info(
        f"[API] 请求开始 | 路径: {request.url.path} | 方法: {request.method} | 参数: {weave_request.model_dump()} | 时间戳: {timestamp}"
    )

    try:
        # 生成任务ID
        task_id = _generate_task_id("reweave")

        # 创建任务
        task_store.create_task(task_id, weave_request, "reweaver")

        # 后台执行任务
        background_tasks.add_task(weaver_service.execute_reweave, task_id, weave_request)

        # 返回响应
        response = _create_task_response(
            task_id=task_id,
            engine="reweaver",
            status="accepted",
            message="网络损伤注入已启动（需手动停止）",
            prefix="reweave",
        )

        logger.info(
            f"[API] 请求完成 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: accepted | 任务ID: {task_id}"
        )
        return response
    except Exception as e:
        logger.error(f"执行 Reweaver 任务失败: {e}")
        logger.info(
            f"[API] 请求失败 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: error"
        )
        raise HTTPException(status_code=500, detail=f"执行 Reweaver 任务失败: {str(e)}") from e


@router.post("/stitch", response_model=WeaveResponse, tags=["weaver"])
def stitch(request: Request, weave_request: WeaveRequest, background_tasks: BackgroundTasks):
    """显式指定 Stitch 端点

    使用 Stitch 引擎执行织径任务
    """
    timestamp = datetime.now()
    logger.info(
        f"[API] 请求开始 | 路径: {request.url.path} | 方法: {request.method} | 参数: {weave_request.model_dump()} | 时间戳: {timestamp}"
    )

    try:
        # 生成任务ID
        task_id = _generate_task_id("stitch")

        # 创建任务
        task_store.create_task(task_id, weave_request, "stitcher")

        # 后台执行任务
        background_tasks.add_task(weaver_service.execute_stitch, task_id, weave_request)

        # 返回响应
        response = _create_task_response(
            task_id=task_id,
            engine="stitcher",
            status="accepted",
            message="网络损伤注入已启动（需手动停止）",
            prefix="stitch",
        )

        logger.info(
            f"[API] 请求完成 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: accepted | 任务ID: {task_id}"
        )
        return response
    except Exception as e:
        logger.error(f"执行 Stitcher 任务失败: {e}")
        logger.info(
            f"[API] 请求失败 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: error"
        )
        raise HTTPException(status_code=500, detail=f"执行 Stitcher 任务失败: {str(e)}") from e


@router.post("/dream", response_model=WeaveResponse, tags=["weaver"])
def dream(request: Request, weave_request: WeaveRequest, background_tasks: BackgroundTasks):
    """显式指定 Dream 端点

    使用 Dream 引擎执行织径任务
    """
    timestamp = datetime.now()
    logger.info(
        f"[API] 请求开始 | 路径: {request.url.path} | 方法: {request.method} | 参数: {weave_request.model_dump()} | 时间戳: {timestamp}"
    )

    try:
        # 生成任务ID
        task_id = _generate_task_id("dream")

        # 创建任务
        task_store.create_task(task_id, weave_request, "dreamer")

        # 后台执行任务
        background_tasks.add_task(weaver_service.execute_dream, task_id, weave_request)

        # 返回响应
        response = _create_task_response(
            task_id=task_id,
            engine="dreamer",
            status="accepted",
            message="网络损伤注入已启动（需手动停止）",
            prefix="dream",
        )

        logger.info(
            f"[API] 请求完成 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: accepted | 任务ID: {task_id}"
        )
        return response
    except Exception as e:
        logger.error(f"执行 Dreamer 任务失败: {e}")
        logger.info(
            f"[API] 请求失败 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: error"
        )
        raise HTTPException(status_code=500, detail=f"执行 Dreamer 任务失败: {str(e)}") from e


@router.get("/weave/{task_id}", response_model=TaskStatusResponse, tags=["weaver"])
def get_weave_status(request: Request, task_id: str):
    """查询自动选择引擎任务状态

    查询使用自动选择引擎执行的织径任务状态
    """
    timestamp = datetime.now()
    logger.info(
        f"[API] 请求开始 | 路径: {request.url.path} | 方法: {request.method} | 参数: {{'task_id': '{task_id}'}} | 时间戳: {timestamp}"
    )

    task_info = task_store.get_task(task_id)
    if not task_info:
        logger.info(
            f"[API] 请求失败 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: not_found"
        )
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    response = _create_status_response(task_info, "weave")
    logger.info(
        f"[API] 请求完成 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: {task_info['status']} | 任务ID: {task_id}"
    )
    return response


@router.get("/reweave/{task_id}", response_model=TaskStatusResponse, tags=["weaver"])
def get_reweave_status(request: Request, task_id: str):
    """查询 Reweave 任务状态

    查询使用 Reweave 引擎执行的织径任务状态
    """
    timestamp = datetime.now()
    logger.info(
        f"[API] 请求开始 | 路径: {request.url.path} | 方法: {request.method} | 参数: {{'task_id': '{task_id}'}} | 时间戳: {timestamp}"
    )

    task_info = task_store.get_task(task_id)
    if not task_info:
        logger.info(
            f"[API] 请求失败 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: not_found"
        )
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    response = _create_status_response(task_info, "reweave")
    logger.info(
        f"[API] 请求完成 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: {task_info['status']} | 任务ID: {task_id}"
    )
    return response


@router.get("/stitch/{task_id}", response_model=TaskStatusResponse, tags=["weaver"])
def get_stitch_status(request: Request, task_id: str):
    """查询 Stitch 任务状态

    查询使用 Stitch 引擎执行的织径任务状态
    """
    timestamp = datetime.now()
    logger.info(
        f"[API] 请求开始 | 路径: {request.url.path} | 方法: {request.method} | 参数: {{'task_id': '{task_id}'}} | 时间戳: {timestamp}"
    )

    task_info = task_store.get_task(task_id)
    if not task_info:
        logger.info(
            f"[API] 请求失败 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: not_found"
        )
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    response = _create_status_response(task_info, "stitch")
    logger.info(
        f"[API] 请求完成 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: {task_info['status']} | 任务ID: {task_id}"
    )
    return response


@router.get("/dream/{task_id}", response_model=TaskStatusResponse, tags=["weaver"])
def get_dream_status(request: Request, task_id: str):
    """查询 Dream 任务状态

    查询使用 Dream 引擎执行的织径任务状态
    """
    timestamp = datetime.now()
    logger.info(
        f"[API] 请求开始 | 路径: {request.url.path} | 方法: {request.method} | 参数: {{'task_id': '{task_id}'}} | 时间戳: {timestamp}"
    )

    task_info = task_store.get_task(task_id)
    if not task_info:
        logger.info(
            f"[API] 请求失败 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: not_found"
        )
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    response = _create_status_response(task_info, "dream")
    logger.info(
        f"[API] 请求完成 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: {task_info['status']} | 任务ID: {task_id}"
    )
    return response


@router.delete("/weave/{task_id}", response_model=TaskStopResponse, tags=["weaver"])
def stop_weave_task(request: Request, task_id: str):
    """停止自动选择引擎任务

    停止使用自动选择引擎执行的织径任务
    """
    timestamp = datetime.now()
    logger.info(
        f"[API] 请求开始 | 路径: {request.url.path} | 方法: {request.method} | 参数: {{'task_id': '{task_id}'}} | 时间戳: {timestamp}"
    )

    try:
        # 停止任务
        weaver_service.cancel_task(task_id)

        # 返回响应
        response = _create_stop_response(
            task_id=task_id,
            status="completed",
            message="仿真已停止，HoloWAN 设备资源已清理",
            prefix="weave",
        )

        logger.info(
            f"[API] 请求完成 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: completed | 任务ID: {task_id}"
        )
        return response
    except Exception as e:
        logger.error(f"停止任务失败: {e}")
        logger.info(
            f"[API] 请求失败 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: error"
        )
        raise HTTPException(status_code=500, detail=f"停止任务失败: {str(e)}") from e


@router.delete("/reweave/{task_id}", response_model=TaskStopResponse, tags=["weaver"])
def stop_reweave_task(request: Request, task_id: str):
    """停止 Reweave 任务

    停止使用 Reweave 引擎执行的织径任务
    """
    timestamp = datetime.now()
    logger.info(
        f"[API] 请求开始 | 路径: {request.url.path} | 方法: {request.method} | 参数: {{'task_id': '{task_id}'}} | 时间戳: {timestamp}"
    )

    try:
        # 停止任务
        weaver_service.cancel_task(task_id)

        # 返回响应
        response = _create_stop_response(
            task_id=task_id,
            status="completed",
            message="仿真已停止，HoloWAN 设备资源已清理",
            prefix="reweave",
        )

        logger.info(
            f"[API] 请求完成 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: completed | 任务ID: {task_id}"
        )
        return response
    except Exception as e:
        logger.error(f"停止任务失败: {e}")
        logger.info(
            f"[API] 请求失败 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: error"
        )
        raise HTTPException(status_code=500, detail=f"停止任务失败: {str(e)}") from e


@router.delete("/stitch/{task_id}", response_model=TaskStopResponse, tags=["weaver"])
def stop_stitch_task(request: Request, task_id: str):
    """停止 Stitch 任务

    停止使用 Stitch 引擎执行的织径任务
    """
    timestamp = datetime.now()
    logger.info(
        f"[API] 请求开始 | 路径: {request.url.path} | 方法: {request.method} | 参数: {{'task_id': '{task_id}'}} | 时间戳: {timestamp}"
    )

    try:
        # 停止任务
        weaver_service.cancel_task(task_id)

        # 返回响应
        response = _create_stop_response(
            task_id=task_id,
            status="completed",
            message="仿真已停止，HoloWAN 设备资源已清理",
            prefix="stitch",
        )

        logger.info(
            f"[API] 请求完成 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: completed | 任务ID: {task_id}"
        )
        return response
    except Exception as e:
        logger.error(f"停止任务失败: {e}")
        logger.info(
            f"[API] 请求失败 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: error"
        )
        raise HTTPException(status_code=500, detail=f"停止任务失败: {str(e)}") from e


@router.delete("/dream/{task_id}", response_model=TaskStopResponse, tags=["weaver"])
def stop_dream_task(request: Request, task_id: str):
    """停止 Dream 任务

    停止使用 Dream 引擎执行的织径任务
    """
    timestamp = datetime.now()
    logger.info(
        f"[API] 请求开始 | 路径: {request.url.path} | 方法: {request.method} | 参数: {{'task_id': '{task_id}'}} | 时间戳: {timestamp}"
    )

    try:
        # 停止任务
        weaver_service.cancel_task(task_id)

        # 返回响应
        response = _create_stop_response(
            task_id=task_id,
            status="completed",
            message="仿真已停止，HoloWAN 设备资源已清理",
            prefix="dream",
        )

        logger.info(
            f"[API] 请求完成 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: completed | 任务ID: {task_id}"
        )
        return response
    except Exception as e:
        logger.error(f"停止任务失败: {e}")
        logger.info(
            f"[API] 请求失败 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: error"
        )
        raise HTTPException(status_code=500, detail=f"停止任务失败: {str(e)}") from e


@router.get("/weave/{task_id}/playback", tags=["weaver"])
def download_weave_playback(request: Request, task_id: str):
    """下载自动选择引擎回放文件

    下载使用自动选择引擎执行的织径任务的回放文件
    """
    timestamp = datetime.now()
    logger.info(
        f"[API] 请求开始 | 路径: {request.url.path} | 方法: {request.method} | 参数: {{'task_id': '{task_id}'}} | 时间戳: {timestamp}"
    )

    playback_file_path = weaver_service.get_playback_file_path(task_id)
    if not playback_file_path or not Path(playback_file_path).exists():
        logger.info(
            f"[API] 请求失败 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: not_found"
        )
        raise HTTPException(status_code=404, detail="回放文件不存在")

    logger.info(
        f"[API] 请求完成 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: success | 任务ID: {task_id}"
    )
    return FileResponse(
        path=playback_file_path,
        media_type="text/plain",
        filename=f"{task_id}.txt",
    )


@router.get("/reweave/{task_id}/playback", tags=["weaver"])
def download_reweave_playback(request: Request, task_id: str):
    """下载 Reweave 回放文件

    下载使用 Reweave 引擎执行的织径任务的回放文件
    """
    timestamp = datetime.now()
    logger.info(
        f"[API] 请求开始 | 路径: {request.url.path} | 方法: {request.method} | 参数: {{'task_id': '{task_id}'}} | 时间戳: {timestamp}"
    )

    playback_file_path = weaver_service.get_playback_file_path(task_id)
    if not playback_file_path or not Path(playback_file_path).exists():
        logger.info(
            f"[API] 请求失败 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: not_found"
        )
        raise HTTPException(status_code=404, detail="回放文件不存在")

    logger.info(
        f"[API] 请求完成 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: success | 任务ID: {task_id}"
    )
    return FileResponse(
        path=playback_file_path,
        media_type="text/plain",
        filename=f"{task_id}.txt",
    )


@router.get("/stitch/{task_id}/playback", tags=["weaver"])
def download_stitch_playback(request: Request, task_id: str):
    """下载 Stitch 回放文件

    下载使用 Stitch 引擎执行的织径任务的回放文件
    """
    timestamp = datetime.now()
    logger.info(
        f"[API] 请求开始 | 路径: {request.url.path} | 方法: {request.method} | 参数: {{'task_id': '{task_id}'}} | 时间戳: {timestamp}"
    )

    playback_file_path = weaver_service.get_playback_file_path(task_id)
    if not playback_file_path or not Path(playback_file_path).exists():
        logger.info(
            f"[API] 请求失败 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: not_found"
        )
        raise HTTPException(status_code=404, detail="回放文件不存在")

    logger.info(
        f"[API] 请求完成 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: success | 任务ID: {task_id}"
    )
    return FileResponse(
        path=playback_file_path,
        media_type="text/plain",
        filename=f"{task_id}.txt",
    )


@router.get("/dream/{task_id}/playback", tags=["weaver"])
def download_dream_playback(request: Request, task_id: str):
    """下载 Dream 回放文件

    下载使用 Dream 引擎执行的织径任务的回放文件
    """
    timestamp = datetime.now()
    logger.info(
        f"[API] 请求开始 | 路径: {request.url.path} | 方法: {request.method} | 参数: {{'task_id': '{task_id}'}} | 时间戳: {timestamp}"
    )

    playback_file_path = weaver_service.get_playback_file_path(task_id)
    if not playback_file_path or not Path(playback_file_path).exists():
        logger.info(
            f"[API] 请求失败 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: not_found"
        )
        raise HTTPException(status_code=404, detail="回放文件不存在")

    logger.info(
        f"[API] 请求完成 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: success | 任务ID: {task_id}"
    )
    return FileResponse(
        path=playback_file_path,
        media_type="text/plain",
        filename=f"{task_id}.txt",
    )
