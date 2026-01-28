# -*- coding: utf-8 -*-
"""LoomNet Web 服务模块
基于 FastAPI 实现的 RESTful API
"""

from fastapi import FastAPI

from .api.v1 import endpoints

__all__ = ["create_app"]


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例

    示例:
        from traceloom.app import create_app

        app = create_app()

    返回:
        FastAPI: FastAPI 应用实例
    """
    app = FastAPI(
        title="LoomNet API",
        description="织虚（LoomNet）网络仿真 API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 注册路由
    app.include_router(endpoints.router, prefix="/api/v1", tags=["v1"])

    return app
