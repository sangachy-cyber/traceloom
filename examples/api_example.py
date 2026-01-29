# -*- coding: utf-8 -*-
"""TraceLoom API 示例脚本
演示如何通过 HTTP 请求调用 TraceLoom 的 API 接口，实现完整的织径任务流程。
"""

import sys
import time
from pathlib import Path
from typing import Any, Dict

# 检查 requests 库是否安装
try:
    import requests
except ImportError:
    print("错误: requests 库未安装，请先运行 'uv add requests' 或 'pip install requests' 安装")
    sys.exit(1)

from loguru import logger

from traceloom.core.config import settings

# 添加src到Python路径
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# 配置日志
logger.add(settings.OUTPUT_DIR / "api_example.log", rotation="10 MB", compression="zip", level=settings.LOG_LEVEL)

# API 基础 URL
API_BASE_URL = "http://localhost:8000/api/v1"


def health_check() -> Dict[str, Any]:
    """健康检查

    验证 API 服务是否正常运行

    Returns:
        Dict[str, Any]: 健康检查响应
    """
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"健康检查失败: {e}")
        raise


def create_task(engine: str, target_ip: str, weaving_pattern: str, impairment_device: Dict[str, Any]) -> Dict[str, Any]:
    """创建织径任务

    使用指定引擎创建织径任务

    Args:
        engine: 引擎名称，可选值："weave", "reweave", "stitch", "dream"
        target_ip: 目标流量 IP
        weaving_pattern: 织样语法
        impairment_device: 损伤设备信息

    Returns:
        Dict[str, Any]: 创建任务的响应
    """
    try:
        data = {"target_ip": target_ip, "weaving_pattern": weaving_pattern, "impairment_device": impairment_device}
        response = requests.post(f"{API_BASE_URL}/{engine}", json=data)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"创建任务失败: {e}")
        raise


def get_task_status(engine: str, task_id: str) -> Dict[str, Any]:
    """查询任务状态

    查询指定任务的执行状态

    Args:
        engine: 引擎名称，可选值："weave", "reweave", "stitch", "dream"
        task_id: 任务唯一标识

    Returns:
        Dict[str, Any]: 任务状态响应
    """
    try:
        response = requests.get(f"{API_BASE_URL}/{engine}/{task_id}")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"查询任务状态失败: {e}")
        raise


def stop_task(engine: str, task_id: str) -> Dict[str, Any]:
    """停止任务

    停止正在执行的任务

    Args:
        engine: 引擎名称，可选值："weave", "reweave", "stitch", "dream"
        task_id: 任务唯一标识

    Returns:
        Dict[str, Any]: 停止任务的响应
    """
    try:
        # 先检查任务状态，只有 running 状态才需要停止
        task_status = get_task_status(engine, task_id)
        if task_status.get("status") != "running":
            logger.info(f"任务状态为 {task_status.get('status')}，不需要停止")
            return {
                "task_id": task_id,
                "status": task_status.get("status"),
                "message": f"任务状态为 {task_status.get('status')}，不需要停止"
            }
        
        response = requests.delete(f"{API_BASE_URL}/{engine}/{task_id}")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"停止任务失败: {e}")
        raise


def download_playback(engine: str, task_id: str, output_path: Path) -> Path:
    """下载回放文件

    下载任务生成的回放文件

    Args:
        engine: 引擎名称，可选值："weave", "reweave", "stitch", "dream"
        task_id: 任务唯一标识
        output_path: 下载文件的保存路径

    Returns:
        Path: 下载文件的完整路径
    """
    try:
        response = requests.get(f"{API_BASE_URL}/{engine}/{task_id}/playback")
        response.raise_for_status()

        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 保存文件
        with open(output_path, "wb") as f:
            f.write(response.content)

        return output_path
    except requests.RequestException as e:
        logger.error(f"下载回放文件失败: {e}")
        raise


def main():
    """主函数

    演示完整的 API 调用流程
    """
    logger.info("TraceLoom API 示例脚本启动")

    # 1. 健康检查
    logger.info("=== 健康检查 ===")
    try:
        health_result = health_check()
        logger.info(f"健康检查结果: {health_result}")
        print(f"健康检查结果: {health_result}")
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        print(f"健康检查失败: {e}")
        return

    # 2. 准备测试数据
    target_ip = "192.168.1.100"
    weaving_pattern = "s0x2 -> s2x6"
    impairment_device = {"host": "160.100.15.195", "port": 8080, "engine_id": 1, "path_name": "LoomPath"}

    # 3. 创建任务（使用 reweave 引擎）
    logger.info("=== 创建织径任务 ===")
    try:
        task_response = create_task(
            engine="reweave", target_ip=target_ip, weaving_pattern=weaving_pattern, impairment_device=impairment_device
        )
        logger.info(f"创建任务结果: {task_response}")
        print(f"创建任务结果: {task_response}")

        task_id = task_response["task_id"]
        engine = "reweave"  # 与创建任务时使用的引擎一致
    except Exception as e:
        logger.error(f"创建任务失败: {e}")
        print(f"创建任务失败: {e}")
        return

    # 4. 查询任务状态
    logger.info("=== 查询任务状态 ===")
    try:
        # 等待几秒后查询状态
        time.sleep(2)
        status_response = get_task_status(engine, task_id)
        logger.info(f"任务状态: {status_response}")
        print(f"任务状态: {status_response}")
    except Exception as e:
        logger.error(f"查询任务状态失败: {e}")
        print(f"查询任务状态失败: {e}")

    # 5. 停止任务
    logger.info("=== 停止任务 ===")
    try:
        stop_response = stop_task(engine, task_id)
        logger.info(f"停止任务结果: {stop_response}")
        print(f"停止任务结果: {stop_response}")
    except Exception as e:
        logger.error(f"停止任务失败: {e}")
        print(f"停止任务失败: {e}")

    # 6. 下载回放文件
    logger.info("=== 下载回放文件 ===")
    try:
        output_file = settings.OUTPUT_DIR / f"{task_id}_playback.txt"
        downloaded_file = download_playback(engine, task_id, output_file)
        logger.info(f"回放文件下载成功: {downloaded_file}")
        print(f"回放文件下载成功: {downloaded_file}")
    except Exception as e:
        logger.error(f"下载回放文件失败: {e}")
        print(f"下载回放文件失败: {e}")

    # 7. 演示使用其他引擎
    logger.info("=== 演示使用其他引擎 ===")
    engines = ["weave", "stitch", "dream"]

    for test_engine in engines:
        try:
            logger.info(f"使用 {test_engine} 引擎创建任务")
            test_task_response = create_task(
                engine=test_engine,
                target_ip=target_ip,
                weaving_pattern=weaving_pattern,
                impairment_device=impairment_device,
            )
            logger.info(f"{test_engine} 引擎创建任务结果: {test_task_response}")

            # 停止测试任务
            test_task_id = test_task_response["task_id"]
            stop_task(test_engine, test_task_id)
            logger.info(f"{test_engine} 引擎任务已停止")
        except Exception as e:
            logger.error(f"使用 {test_engine} 引擎失败: {e}")

    logger.info("TraceLoom API 示例脚本完成")
    print("TraceLoom API 示例脚本完成")


if __name__ == "__main__":
    main()
