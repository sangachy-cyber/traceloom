# -*- coding: utf-8 -*-
"""公共接口定义

定义项目中的服务接口和抽象基类
"""

from abc import ABC, abstractmethod
from typing import Optional

from traceloom.app.api.v1.schemas import WeaveRequest
from traceloom.core.response import ErrorResponse, WeaveResponse


class IWeaverService(ABC):
    """编织服务接口"""
    
    @abstractmethod
    def execute_task(self, task_id: str, request: WeaveRequest) -> Optional[WeaveResponse]:
        """执行织径任务
        
        参数:
            task_id: 任务唯一标识
            request: 编织请求对象
            
        返回:
            WeaveResponse: 编织响应对象
        """
        pass
    
    @abstractmethod
    def execute_reweave(self, task_id: str, request: WeaveRequest) -> Optional[WeaveResponse]:
        """执行Reweaver织径任务
        
        参数:
            task_id: 任务唯一标识
            request: 编织请求对象
            
        返回:
            WeaveResponse: 编织响应对象
        """
        pass
    
    @abstractmethod
    def execute_stitch(self, task_id: str, request: WeaveRequest) -> Optional[WeaveResponse]:
        """执行Stitch织径任务
        
        参数:
            task_id: 任务唯一标识
            request: 编织请求对象
            
        返回:
            WeaveResponse: 编织响应对象
        """
        pass
    
    @abstractmethod
    def execute_dream(self, task_id: str, request: WeaveRequest) -> Optional[WeaveResponse]:
        """执行Dream织径任务
        
        参数:
            task_id: 任务唯一标识
            request: 编织请求对象
            
        返回:
            WeaveResponse: 编织响应对象
        """
        pass
    
    @abstractmethod
    def cancel_task(self, task_id: str) -> Optional[ErrorResponse]:
        """取消任务
        
        参数:
            task_id: 任务唯一标识
            
        返回:
            ErrorResponse: 错误响应对象，无错误时返回None
        """
        pass
    
    @abstractmethod
    def get_playback_file_path(self, task_id: str) -> Optional[str]:
        """获取任务的回放文件路径
        
        参数:
            task_id: 任务唯一标识
            
        返回:
            str: 回放文件路径，如果不存在返回None
        """
        pass
    
    @abstractmethod
    def cleanup_expired_files(self) -> None:
        """清理过期的回放文件
        """
        pass
