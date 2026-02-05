# -*- coding: utf-8 -*-
"""TraceLoom API v1 端点定义
包含各种 API 路由和处理函数
"""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import FileResponse

from traceloom.core.logger import logger
from traceloom.core.response_handler import ResponseHandler
from traceloom.services.weaver_service import WeaverService
from traceloom.storage.pathlet_storage import PathletStorage
from traceloom.storage.task_store import TaskStore

from .schemas import (
    HealthCheckResponse,
    HoloWANApplyRequest,
    HoloWANApplyResponse,
    HoloWANBindIPRequest,
    HoloWANBindIPResponse,
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


def _handle_task_execution(
    request: Request, weave_request: WeaveRequest, engine_type: str, background_tasks: BackgroundTasks
):
    """处理任务执行

    参数:
        request: HTTP请求对象
        weave_request: 编织请求对象
        engine_type: 引擎类型
        background_tasks: 后台任务对象

    返回:
        WeaveResponse: 编织响应对象
    """
    timestamp = datetime.now()
    logger.info(
        f"[API] 请求开始 | 路径: {request.url.path} | 方法: {request.method} | 参数: {weave_request.model_dump()} | 时间戳: {timestamp}"
    )

    try:
        # 生成任务ID
        task_id = _generate_task_id(engine_type)

        # 创建任务
        task_store.create_task(task_id, weave_request, engine_type)

        # 根据引擎类型执行任务
        if engine_type == "auto":
            background_tasks.add_task(weaver_service.execute_task, task_id, weave_request)
        elif engine_type == "reweaver":
            background_tasks.add_task(weaver_service.execute_reweave, task_id, weave_request)
        elif engine_type == "stitcher":
            background_tasks.add_task(weaver_service.execute_stitch, task_id, weave_request)
        elif engine_type == "dreamer":
            background_tasks.add_task(weaver_service.execute_dream, task_id, weave_request)

        # 返回响应
        response = _create_task_response(
            task_id=task_id,
            engine=engine_type,
            status="accepted",
            message="网络损伤注入已启动（需手动停止）",
            prefix=engine_type if engine_type != "auto" else "weave",
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
        ResponseHandler.raise_http_exception(e)


def _handle_task_status(request: Request, task_id: str, prefix: str):
    """处理任务状态查询

    参数:
        request: HTTP请求对象
        task_id: 任务唯一标识
        prefix: 路径前缀

    返回:
        TaskStatusResponse: 任务状态响应对象
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

    response = _create_status_response(task_info, prefix)
    logger.info(
        f"[API] 请求完成 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: {task_info['status']} | 任务ID: {task_id}"
    )
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


def _handle_task_stop(request: Request, task_id: str, prefix: str):
    """处理任务停止

    参数:
        request: HTTP请求对象
        task_id: 任务唯一标识
        prefix: 路径前缀

    返回:
        TaskStopResponse: 任务停止响应对象
    """
    timestamp = datetime.now()
    logger.info(
        f"[API] 请求开始 | 路径: {request.url.path} | 方法: {request.method} | 参数: {{'task_id': '{task_id}'}} | 时间戳: {timestamp}"
    )

    try:
        # 取消任务
        result = weaver_service.cancel_task(task_id)

        if result is None:
            # 任务取消成功
            response = _create_stop_response(task_id, "completed", "任务已成功停止", prefix)
            logger.info(
                f"[API] 请求完成 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: completed | 任务ID: {task_id}"
            )
        else:
            # 任务取消失败
            response = _create_stop_response(task_id, "error", result.message, prefix)
            logger.info(
                f"[API] 请求失败 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: error | 任务ID: {task_id}"
            )

        return response
    except Exception as e:
        logger.error(f"停止任务失败: {e}")
        logger.info(
            f"[API] 请求失败 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: error"
        )
        ResponseHandler.raise_http_exception(e)


def _handle_playback_download(request: Request, task_id: str):
    """处理回放文件下载

    参数:
        request: HTTP请求对象
        task_id: 任务唯一标识

    返回:
        FileResponse: 文件响应对象
    """
    timestamp = datetime.now()
    logger.info(
        f"[API] 请求开始 | 路径: {request.url.path} | 方法: {request.method} | 参数: {{'task_id': '{task_id}'}} | 时间戳: {timestamp}"
    )

    try:
        # 获取回放文件路径
        playback_file_path = weaver_service.get_playback_file_path(task_id)

        if not playback_file_path:
            logger.info(
                f"[API] 请求失败 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: not_found"
            )
            raise HTTPException(status_code=404, detail="回放文件不存在")

        # 检查文件是否存在
        file_path = Path(playback_file_path)
        if not file_path.exists():
            logger.info(
                f"[API] 请求失败 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: not_found"
            )
            raise HTTPException(status_code=404, detail="回放文件不存在")

        logger.info(
            f"[API] 请求完成 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: success | 文件: {file_path.name}"
        )
        return FileResponse(path=file_path, filename=file_path.name, media_type="text/plain")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载回放文件失败: {e}")
        logger.info(
            f"[API] 请求失败 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: error"
        )
        ResponseHandler.raise_http_exception(e)


@router.get("/health", response_model=HealthCheckResponse, tags=["system"])
def health_check(request: Request):
    """健康检查端点

    返回服务的健康状态
    """
    timestamp = datetime.now()
    logger.info(
        f"[API] 请求开始 | 路径: {request.url.path} | 方法: {request.method} | 参数: {dict(request.query_params)} | 时间戳: {timestamp}"
    )

    response = HealthCheckResponse(status="ok", timestamp=timestamp.isoformat(), version="1.0.0")

    logger.info(f"[API] 请求完成 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: ok")
    return response


@router.post("/weave", response_model=WeaveResponse, tags=["weaver"])
def weave(request: Request, weave_request: WeaveRequest, background_tasks: BackgroundTasks):
    """自动选择引擎端点

    根据织样自动选择合适的引擎执行织径任务
    """
    return _handle_task_execution(request, weave_request, "auto", background_tasks)


@router.post("/reweave", response_model=WeaveResponse, tags=["weaver"])
def reweave(request: Request, weave_request: WeaveRequest, background_tasks: BackgroundTasks):
    """显式指定 Reweave 端点

    使用 Reweave 引擎执行织径任务
    """
    return _handle_task_execution(request, weave_request, "reweaver", background_tasks)


@router.post("/stitch", response_model=WeaveResponse, tags=["weaver"])
def stitch(request: Request, weave_request: WeaveRequest, background_tasks: BackgroundTasks):
    """显式指定 Stitch 端点

    使用 Stitch 引擎执行织径任务
    """
    return _handle_task_execution(request, weave_request, "stitcher", background_tasks)


@router.post("/dream", response_model=WeaveResponse, tags=["weaver"])
def dream(request: Request, weave_request: WeaveRequest, background_tasks: BackgroundTasks):
    """显式指定 Dream 端点

    使用 Dream 引擎执行织径任务
    """
    return _handle_task_execution(request, weave_request, "dreamer", background_tasks)


@router.get("/weave/{task_id}", response_model=TaskStatusResponse, tags=["weaver"])
def get_weave_status(request: Request, task_id: str):
    """查询自动选择引擎任务状态

    查询使用自动选择引擎执行的织径任务状态
    """
    return _handle_task_status(request, task_id, "weave")


@router.get("/reweave/{task_id}", response_model=TaskStatusResponse, tags=["weaver"])
def get_reweave_status(request: Request, task_id: str):
    """查询 Reweave 任务状态

    查询使用 Reweave 引擎执行的织径任务状态
    """
    return _handle_task_status(request, task_id, "reweave")


@router.get("/stitch/{task_id}", response_model=TaskStatusResponse, tags=["weaver"])
def get_stitch_status(request: Request, task_id: str):
    """查询 Stitch 任务状态

    查询使用 Stitch 引擎执行的织径任务状态
    """
    return _handle_task_status(request, task_id, "stitch")


@router.get("/dream/{task_id}", response_model=TaskStatusResponse, tags=["weaver"])
def get_dream_status(request: Request, task_id: str):
    """查询 Dream 任务状态

    查询使用 Dream 引擎执行的织径任务状态
    """
    return _handle_task_status(request, task_id, "dream")


@router.delete("/weave/{task_id}", response_model=TaskStopResponse, tags=["weaver"])
def stop_weave_task(request: Request, task_id: str):
    """停止自动选择引擎任务

    停止使用自动选择引擎执行的织径任务
    """
    return _handle_task_stop(request, task_id, "weave")


@router.delete("/reweave/{task_id}", response_model=TaskStopResponse, tags=["weaver"])
def stop_reweave_task(request: Request, task_id: str):
    """停止 Reweave 任务

    停止使用 Reweave 引擎执行的织径任务
    """
    return _handle_task_stop(request, task_id, "reweave")


@router.delete("/stitch/{task_id}", response_model=TaskStopResponse, tags=["weaver"])
def stop_stitch_task(request: Request, task_id: str):
    """停止 Stitch 任务

    停止使用 Stitch 引擎执行的织径任务
    """
    return _handle_task_stop(request, task_id, "stitch")


@router.delete("/dream/{task_id}", response_model=TaskStopResponse, tags=["weaver"])
def stop_dream_task(request: Request, task_id: str):
    """停止 Dream 任务

    停止使用 Dream 引擎执行的织径任务
    """
    return _handle_task_stop(request, task_id, "dream")


@router.get("/{engine}/{task_id}/playback", tags=["weaver"])
def download_playback(request: Request, engine: str, task_id: str):
    """下载回放文件

    下载织径任务的回放文件
    """
    return _handle_playback_download(request, task_id)


def _handle_bind_ip(request: Request, bind_request: HoloWANBindIPRequest):
    """处理IP绑定

    参数:
        request: HTTP请求对象
        bind_request: 绑定IP请求对象

    返回:
        HoloWANBindIPResponse: 绑定IP响应对象
    """
    timestamp = datetime.now()
    logger.info(
        f"[API] 请求开始 | 路径: {request.url.path} | 方法: {request.method} | 参数: {bind_request.model_dump()} | 时间戳: {timestamp}"
    )

    try:
        # 绑定IP到路径
        result = weaver_service.bind_ip_to_path(bind_request.target_ip, bind_request.impairment_device)

        response = HoloWANBindIPResponse(status=result["status"], path_id=result["path_id"], message="IP绑定成功")

        logger.info(
            f"[API] 请求完成 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: success | 路径ID: {result['path_id']}"
        )
        return response
    except Exception as e:
        logger.error(f"绑定IP失败: {e}")
        logger.info(
            f"[API] 请求失败 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: error"
        )
        ResponseHandler.raise_http_exception(e)


def _handle_apply_file(request: Request, apply_request: HoloWANApplyRequest):
    """处理文件应用

    参数:
        request: HTTP请求对象
        apply_request: 应用文件请求对象

    返回:
        HoloWANApplyResponse: 应用文件响应对象
    """
    timestamp = datetime.now()
    logger.info(
        f"[API] 请求开始 | 路径: {request.url.path} | 方法: {request.method} | 参数: {apply_request.model_dump()} | 时间戳: {timestamp}"
    )

    try:
        # 应用文件
        result = weaver_service.apply_file(apply_request.file_name, apply_request.impairment_device)

        response = HoloWANApplyResponse(status=result["status"], path_id=result["path_id"], message="文件应用成功")

        logger.info(
            f"[API] 请求完成 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: success | 路径ID: {result['path_id']}"
        )
        return response
    except Exception as e:
        logger.error(f"应用文件失败: {e}")
        logger.info(
            f"[API] 请求失败 | 路径: {request.url.path} | 方法: {request.method} | 时间戳: {timestamp} | 状态: error"
        )
        ResponseHandler.raise_http_exception(e)


@router.post("/holowan/bind-ip", response_model=HoloWANBindIPResponse, tags=["holowan"])
def bind_ip(request: Request, bind_request: HoloWANBindIPRequest):
    """绑定IP到路径

    将指定的IP地址绑定到HoloWAN设备的指定路径
    """
    return _handle_bind_ip(request, bind_request)


@router.post("/holowan/apply", response_model=HoloWANApplyResponse, tags=["holowan"])
def apply_file(request: Request, apply_request: HoloWANApplyRequest):
    """应用文件到设备

    将指定的文件上传并应用到HoloWAN设备
    """
    return _handle_apply_file(request, apply_request)
