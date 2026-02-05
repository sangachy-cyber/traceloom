# -*- coding: utf-8 -*-
"""响应处理工具

统一处理API和函数调用的响应格式化和错误转换
"""

from fastapi import HTTPException
from loguru import logger

from traceloom.core.response import ErrorResponse, WeaveResponse


class ResponseHandler:
    """响应处理器"""
    
    @staticmethod
    def format_success_response(status: str, message: str, **kwargs) -> dict:
        """格式化成功响应
        
        参数:
            status: 响应状态
            message: 响应消息
            **kwargs: 额外的响应数据
            
        返回:
            dict: 格式化后的响应字典
        """
        response = {
            "status": status,
            "message": message,
            **kwargs
        }
        return response
    
    @staticmethod
    def format_error_response(error: Exception, status_code: int = 500) -> ErrorResponse:
        """格式化错误响应
        
        参数:
            error: 异常对象
            status_code: HTTP状态码
            
        返回:
            ErrorResponse: 错误响应对象
        """
        logger.error(f"处理错误: {str(error)}")
        logger.exception("详细错误信息:")
        
        error_response = ErrorResponse(
            status="error",
            message=str(error),
            error_code=str(status_code),
            details={"exception_type": type(error).__name__}
        )
        return error_response
    
    @staticmethod
    def raise_http_exception(error: Exception, status_code: int = 500) -> None:
        """抛出HTTP异常
        
        参数:
            error: 异常对象
            status_code: HTTP状态码
        """
        error_response = ResponseHandler.format_error_response(error, status_code)
        raise HTTPException(status_code=status_code, detail=error_response.model_dump())
    
    @staticmethod
    def create_weave_response(task_id: str, engine: str, status: str, message: str, download_url: str) -> WeaveResponse:
        """创建编织响应
        
        参数:
            task_id: 任务唯一标识
            engine: 使用的引擎
            status: 任务状态
            message: 响应消息
            download_url: 回放文件下载链接
            
        返回:
            WeaveResponse: 编织响应对象
        """
        return WeaveResponse(
            task_id=task_id,
            engine=engine,
            status=status,
            message=message,
            download_url=download_url
        )
