import sys

from loguru import logger


# 配置 loguru 日志
def setup_logger():
    """初始化日志配置

    示例:
        from traceloom.core.logger import setup_logger
        setup_logger()
        logger.info("日志初始化完成")
    """
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> "
            "| <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        ),
        colorize=True,
    )
    logger.add(
        "./tmp/loomnet.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
    )


# 导出 logger
def get_logger():
    """获取日志实例

    示例:
        from traceloom.core.logger import get_logger
        logger = get_logger()
        logger.info("使用日志实例")
    """
    return logger


# 初始化日志
setup_logger()
