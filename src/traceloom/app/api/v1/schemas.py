# -*- coding: utf-8 -*-
"""TraceLoom API v1 数据模型
定义 API 请求和响应的数据结构
"""


from typing import Optional

from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    """健康检查响应模型"""

    status: str = Field(..., description="服务状态")
    timestamp: str = Field(..., description="检查时间")
    version: str = Field(..., description="API 版本")


class ImpairmentDevice(BaseModel):
    """损伤设备模型"""

    host: str = Field(..., description="HoloWAN 设备 IP")
    port: int = Field(..., description="Web API 端口")
    engine_id: int = Field(..., description="引擎 ID")
    path_name: str = Field(..., description="虚拟链路名")


class WeaveRequest(BaseModel):
    """编织请求模型"""

    target_ip: str = Field(..., description="目标流量 IP")
    weaving_pattern: str = Field(..., description="织样语法")
    impairment_device: ImpairmentDevice = Field(..., description="损伤设备信息")


class WeaveResponse(BaseModel):
    """编织响应模型"""

    task_id: str = Field(..., description="任务唯一标识")
    engine: str = Field(..., description="实际使用的引擎")
    status: str = Field(..., description="任务状态")
    message: str = Field(..., description="响应消息")
    download_url: str = Field(..., description="回放文件下载链接")


class TaskStatusResponse(BaseModel):
    """任务状态响应模型"""

    task_id: str = Field(..., description="任务唯一标识")
    engine: str = Field(..., description="使用的引擎")
    status: str = Field(..., description="任务状态")
    target_ip: str = Field(..., description="目标流量 IP")
    weaving_pattern: str = Field(..., description="织样语法")
    impairment_device: ImpairmentDevice = Field(..., description="损伤设备信息")
    started_at: Optional[str] = Field(None, description="开始时间")
    download_url: str = Field(..., description="回放文件下载链接")


class TaskStopResponse(BaseModel):
    """任务停止响应模型"""

    task_id: str = Field(..., description="任务唯一标识")
    status: str = Field(..., description="任务状态")
    message: str = Field(..., description="响应消息")
    download_url: str = Field(..., description="回放文件下载链接")


class ErrorResponse(BaseModel):
    """错误响应模型"""

    detail: str = Field(..., description="错误详情")


class HoloWANBindIPRequest(BaseModel):
    """绑定IP请求模型"""

    target_ip: str = Field(..., description="目标流量 IP")
    impairment_device: ImpairmentDevice = Field(..., description="损伤设备信息")


class HoloWANBindIPResponse(BaseModel):
    """绑定IP响应模型"""

    status: str = Field(..., description="操作状态")
    path_id: int = Field(..., description="绑定的路径 ID")
    message: str = Field(..., description="响应消息")


class HoloWANApplyRequest(BaseModel):
    """应用文件请求模型"""

    file_name: str = Field(..., description="文件名")
    impairment_device: ImpairmentDevice = Field(..., description="损伤设备信息")


class HoloWANApplyResponse(BaseModel):
    """应用文件响应模型"""

    status: str = Field(..., description="操作状态")
    path_id: int = Field(..., description="应用的路径 ID")
    message: str = Field(..., description="响应消息")
