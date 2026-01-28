# -*- coding: utf-8 -*-
"""TraceLoom API v1 数据模型
定义 API 请求和响应的数据结构
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class NetworkProfileBase(BaseModel):
    """网络剖面基础模型"""

    rtt: float = Field(..., ge=0, le=2000, description="往返时延（毫秒）")
    loss_rate: float = Field(..., ge=-1.0, le=101.0, description="丢包率")
    bandwidth: float = Field(..., ge=0, description="可用带宽（Mbps）")


class NetworkProfileCreate(NetworkProfileBase):
    """创建网络剖面请求模型"""

    profile_id: Optional[str] = Field(None, description="剖面唯一标识符")
    metadata: Optional[Dict] = Field(None, description="附加元数据")


class NetworkProfileResponse(NetworkProfileBase):
    """网络剖面响应模型"""

    profile_id: str = Field(..., description="剖面唯一标识符")
    timestamp: datetime = Field(..., description="剖面生成时间")
    metadata: Optional[Dict] = Field(None, description="附加元数据")

    model_config = ConfigDict(from_attributes=True)


class ProfileSequenceCreate(BaseModel):
    """创建剖面序列请求模型"""

    profiles: List[NetworkProfileCreate] = Field(..., description="网络剖面列表")
    sequence_id: Optional[str] = Field(None, description="序列唯一标识符")
    metadata: Optional[Dict] = Field(None, description="附加元数据")


class ProfileSequenceResponse(BaseModel):
    """剖面序列响应模型"""

    sequence_id: str = Field(..., description="序列唯一标识符")
    profiles: List[NetworkProfileResponse] = Field(..., description="网络剖面列表")
    metadata: Optional[Dict] = Field(None, description="附加元数据")

    model_config = ConfigDict(from_attributes=True)


class ScenarioConfigBase(BaseModel):
    """场景配置基础模型"""

    scenario_type: str = Field(..., description="场景类型，可选 'reweave', 'embroider', 'dream'")
    params: Optional[Dict] = Field(None, description="场景参数")


class ScenarioConfigCreate(ScenarioConfigBase):
    """创建场景配置请求模型"""

    profiles: Optional[List[NetworkProfileCreate]] = Field(None, description="输入的网络剖面列表")


class GenerateRequest(BaseModel):
    """生成网络参数序列请求模型"""

    config: ScenarioConfigCreate = Field(..., description="场景配置")


class GenerateResponse(BaseModel):
    """生成网络参数序列响应模型"""

    profiles: List[NetworkProfileResponse] = Field(..., description="生成的网络剖面列表")
    message: str = Field(..., description="响应消息")
    scenario_type: str = Field(..., description="场景类型")


class MetricsResponse(BaseModel):
    """网络参数指标响应模型"""

    avg_rtt: float = Field(..., description="平均 RTT")
    max_rtt: float = Field(..., description="最大 RTT")
    min_rtt: float = Field(..., description="最小 RTT")
    avg_loss_rate: float = Field(..., description="平均丢包率")
    avg_bandwidth: float = Field(..., description="平均带宽")
    duration: float = Field(..., description="序列持续时间（秒）")


class FileExportRequest(BaseModel):
    """文件导出请求模型"""

    profile_ids: List[str] = Field(..., description="要导出的剖面 ID 列表")
    format: str = Field(..., description="导出格式，可选 'hwan', 'csv', 'json'")


class FileExportResponse(BaseModel):
    """文件导出响应模型"""

    file_url: str = Field(..., description="导出文件的 URL")
    file_name: str = Field(..., description="导出文件的名称")
    message: str = Field(..., description="响应消息")


class HealthCheckResponse(BaseModel):
    """健康检查响应模型"""

    status: str = Field(..., description="服务状态")
    timestamp: datetime = Field(..., description="检查时间")
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
