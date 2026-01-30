# -*- coding: utf-8 -*-
"""TraceLoom Web 服务主入口
用于启动 Uvicorn 服务器
"""

import uvicorn

from traceloom.app import create_app

# 先初始化日志
from traceloom.core.logger import logger, setup_logger

setup_logger()

app = create_app()

if __name__ == "__main__":
    """启动 Uvicorn 服务器

    示例:
        python -m traceloom.app.main
    """
    logger.info("启动 TraceLoom Web 服务...")
    uvicorn.run("traceloom.app.main:app", host="0.0.0.0", port=8000, reload=False, log_level="debug")
