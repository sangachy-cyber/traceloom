# -*- coding: utf-8 -*-
"""统一响应类体系

定义项目中所有API和函数调用的统一返回结构
"""

from datetime import datetime
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field


T = TypeVar('T')


class BaseResponse(BaseModel):
    """基础响应类"""
    
    status: str = Field(..., description="响应状态")
    message: str = Field(..., description="响应消息")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")


class DataResponse(BaseResponse, Generic[T]):
    """带数据的响应类"""
    
    data: Optional[T] = Field(None, description="响应数据")


class ErrorResponse(BaseResponse):
    """错误响应类"""
    
    error_code: Optional[str] = Field(None, description="错误码")
    details: Optional[Any] = Field(None, description="错误详情")


class TaskResponse(BaseResponse):
    """任务响应基类"""
    
    task_id: str = Field(..., description="任务唯一标识")
    engine: str = Field(..., description="使用的引擎")


class WeaveResponse(TaskResponse):
    """编织响应类"""
    
    download_url: str = Field(..., description="回放文件下载链接")


class TaskStatusResponse(TaskResponse):
    """任务状态响应类"""
    
    target_ip: str = Field(..., description="目标流量IP")
    weaving_pattern: str = Field(..., description="织样语法")
    host: str = Field(..., description="HoloWAN设备IP")
    port: int = Field(..., description="Web API端口")
    engine_id: int = Field(..., description="引擎ID")
    path_name: str = Field(..., description="虚拟链路名")
    started_at: Optional[str] = Field(None, description="开始时间")
    download_url: str = Field(..., description="回放文件下载链接")


class TaskStopResponse(TaskResponse):
    """任务停止响应类"""
    
    download_url: str = Field(..., description="回放文件下载链接")


class HealthCheckResponse(BaseResponse):
    """健康检查响应类"""
    
    version: str = Field(..., description="API版本")
