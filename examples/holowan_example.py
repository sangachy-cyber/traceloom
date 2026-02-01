#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HoloWAN 交互示例脚本

展示如何使用重构后的 HoloWANManager 类执行完整的 HoloWAN 交互流程。
"""

import sys
from pathlib import Path

from loguru import logger

from traceloom.core.config import settings

# 添加 src 到 Python 路径
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# 配置日志
logger.add(settings.OUTPUT_DIR / "holowan_example.log", rotation="10 MB", compression="zip", level=settings.LOG_LEVEL)


def connect_device(holowan_manager):
    """连接 HoloWAN 设备"""
    logger.info("\n1. 连接 HoloWAN 设备...")
    holowan_manager.connect()
    logger.info("✅ HoloWAN 设备连接成功")


def check_playback_file(playback_file_path):
    """检查回放文件是否存在"""
    logger.info("\n2. 检查回放文件...")
    if not playback_file_path.exists():
        logger.warning(f"⚠️  回放文件不存在: {playback_file_path}")
        logger.info("创建示例回放文件...")
        # 创建示例回放文件
        with open(playback_file_path, "w") as f:
            f.write("# 示例回放文件\n")
            f.write("0.0,100,0,100,0\n")
            f.write("1.0,150,0.1,90,0\n")
            f.write("2.0,200,0.2,80,0\n")
            f.write("3.0,150,0.1,90,0\n")
            f.write("4.0,100,0,100,0\n")
        logger.info("✅ 示例回放文件创建成功")


def get_path_id(holowan_manager, path_name):
    """获取路径 ID"""
    logger.info(f"\n3. 获取路径 ID: {path_name}...")
    try:
        path_id = holowan_manager.get_path_id_by_name(path_name)
        logger.info(f"✅ 获取路径 ID 成功: {path_id}")
        return path_id
    except Exception as e:
        logger.error(f"❌ 获取路径 ID 失败: {e}")
        return None


def bind_ip_to_path(holowan_manager, target_ip, path_id):
    """绑定 IP 到路径"""
    logger.info(f"\n4. 绑定 IP: {target_ip} 到路径: {path_id}...")
    try:
        holowan_manager.bind_ip_to_path(target_ip, path_id)
        logger.info("✅ IP 绑定成功")
        return True
    except Exception as e:
        logger.error(f"❌ IP 绑定失败: {e}")
        return False


def upload_and_apply_playback(holowan_manager, playback_file_path, playback_name, path_id):
    """上传并应用回放文件"""
    logger.info("\n5. 上传并应用回放文件...")
    try:
        holowan_manager.upload_and_apply_playback(str(playback_file_path), playback_name, path_id)
        logger.info("✅ 回放文件上传并应用成功")
        return True
    except Exception as e:
        logger.error(f"❌ 回放文件上传并应用失败: {e}")
        return False


def generate_temp_playback_file(output_path):
    """生成临时回放文件

    根据指定内容生成临时回放文件

    Args:
        output_path: 输出文件路径

    Returns:
        Path: 生成的文件路径
    """
    logger.info("\n生成临时回放文件...")

    # 回放文件内容
    playback_content = """HoloWAN Recorder File (www.msytest.com)
 NetworkType: "4G"
test_name: "Xicen (12-03 23:03:56)"
Destination: "172.30.153.236:8081"
Start Time: 2025-12-03 23:03:56
End Time: 2025-12-04 00:04:00
Interval(sec): 0.1
Packet Size(byte): 300
Enable Reordering: True
Contents: Delay1(ms),Loss1(%),Bandwidth1(Mbps),Delay2(ms),Loss2(%),Bandwidth2(Mbps)
Switch: 1,1,1,1,1,1
------------------------------------------------
134.572000,0.000000,0.025600,134.487167,0.000000,0.051200
146.251500,0.000000,0.000000,148.487000,0.000000,0.051200
215.487500,0.000000,0.025600,215.762250,0.000000,0.076800
228.668250,0.000000,0.025600,237.027667,0.000000,0.051200
218.970000,0.000000,0.025600,232.197750,0.000000,0.051200
212.542000,0.000000,0.000000,211.996000,0.000000,0.076800
172.930500,0.000000,0.025600,172.811833,0.000000,0.051200
134.730000,0.000000,0.025600,134.388250,0.000000,0.051200
93.994500,0.000000,0.025600,98.168750,0.000000,0.076800
38.640250,0.000000,0.051200,56.623000,0.000000,0.051200
18.050500,0.000000,0.128000,18.101750,0.000000,0.076800
13.651000,0.000000,0.051200,13.395000,0.000000,0.051200
18.952500,0.000000,0.025600,17.235500,0.000000,0.051200
16.440000,0.000000,0.025600,16.414750,0.000000,0.076800
19.643000,0.000000,0.025600,29.708333,0.000000,0.051200
18.828000,0.000000,0.025600,19.198750,0.000000,0.051200
25.362500,0.000000,0.025600,25.082250,0.000000,0.076800
13.243500,0.000000,0.051200,13.280000,0.000000,0.051200
17.396500,0.000000,0.025600,13.046500,0.000000,0.051200
"""

    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 写入文件
    with open(output_path, "w") as f:
        f.write(playback_content)

    logger.info(f"✅ 临时回放文件生成成功: {output_path}")

    return output_path


def execute_business_logic():
    """执行业务逻辑"""
    logger.info("\n6. 执行业务逻辑...")
    # 这里可以添加业务逻辑，比如进行网络测试等
    logger.info("   示例业务逻辑: 模拟网络测试...")
    # 模拟业务逻辑执行时间
    import time
    time.sleep(3)
    logger.info("✅ 业务逻辑执行完成")


def cleanup_resources(holowan_manager, target_ip, playback_name, path_id):
    """清理资源"""
    logger.info("\n7. 清理资源...")
    try:
        holowan_manager.cleanup(target_ip, playback_name, path_id)
        logger.info("✅ 资源清理成功")
        return True
    except Exception as e:
        logger.error(f"❌ 资源清理失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("HoloWAN 交互示例脚本启动")

    # 配置参数
    engine_id = 1
    target_ip = "19.13.169.52"
    path_name = "LoomNet"
    # 临时回放文件路径
    temp_dir = Path(__file__).parent.parent / "data" / 'outputs'
    playback_file_path = temp_dir / "reweave_path.txt"

    # 获取回放文件名称
    playback_name = playback_file_path.name

    # 生成临时回放文件
    generate_temp_playback_file(playback_file_path)

    # 初始化 HoloWAN 管理器
    try:
        from traceloom.devices import HoloWAN

        holowan_manager = HoloWAN(host="160.100.15.195", port="8080", engine_id=engine_id)
        logger.info("HoloWAN 管理器初始化成功")
    except ImportError as e:
        logger.error(f"导入 HoloWANManager 失败: {e}")
        return
    except Exception as e:
        logger.error(f"初始化 HoloWAN 管理器失败: {e}")
        return

    path_id = None
    try:
        # 1. 连接设备
        connect_device(holowan_manager)

        # 2. 检查回放文件
        check_playback_file(playback_file_path)

        # 3. 获取路径 ID
        path_id = get_path_id(holowan_manager, path_name)
        if path_id is None:
            return

        # 4. 绑定 IP 到路径
        if not bind_ip_to_path(holowan_manager, target_ip, path_id):
            return

        # # 5. 上传并应用回放文件
        # if not upload_and_apply_playback(holowan_manager, playback_file_path, playback_name, path_id):
        #     return
        #
        # # 6. 执行业务逻辑
        # execute_business_logic()
        #
        # # 7. 清理资源
        # cleanup_resources(holowan_manager, target_ip, playback_name, path_id)

        logger.info("完整流程执行成功")
        logger.info("\n🎉 完整流程执行成功！")

    except Exception as e:
        logger.error(f"\n❌ 执行过程中发生错误: {e}")
        # 确保资源被清理
        try:
            if path_id is not None:
                holowan_manager.cleanup(target_ip, playback_name, path_id)
                logger.info("错误后资源清理成功")
            else:
                logger.info("未获取到 path_id，跳过资源清理")
        except Exception as cleanup_error:
            logger.error(f"错误后资源清理失败: {cleanup_error}")
    finally:
        logger.info("HoloWAN 交互示例脚本完成")


if __name__ == "__main__":
    main()
