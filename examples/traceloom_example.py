# -*- coding: utf-8 -*-
"""TraceLoom 示例脚本
演示如何使用新的 traceloom API 调用方式
"""

# 从config读取settings对象
import sys
import traceback
from pathlib import Path

from loguru import logger

from traceloom.core.config import settings

# 添加src到Python路径
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


# 配置日志
logger.add(settings.OUTPUT_DIR / "traceloom_example.log", rotation="10 MB", compression="zip", level=settings.LOG_LEVEL)


def main():
    """主函数"""
    logger.info("TraceLoom示例脚本启动")

    # 演示新的API调用方式
    try:
        # 使用 traceloom 别名导入
        import traceloom as tl

        logger.info("=== 重织（reweave）示例 ====")
        # 使用重织功能，从真实HoloWAN文件提取并重组路径
        # 注意：这里使用了一个示例文件路径，实际使用时需要替换为真实文件
        # sample_file = settings.RAW_DIR / "20251203_230356_b6x-playback.txt"
        # tl.reweave(input_file=str(sample_file), output=str(settings.OUTPUT_DIR / "reweave_path.txt"))
        # logger.info(f"重织结果: {reweave_result}")
        # sample = "s2x2 -> s1x57 -> s2x1 -> s1x45 -> s2x1 -> s1x5 -> s2x1 -> s1x124 -> s2x1 -> s1x70 -> s2x1 -> s1x47 -> s2x1 -> s1x4"
        sample = "s2x2 -> s1x2 -> s0x2 > s1x2"

        tl.reweave(input_file=str(" -> ".join([sample] * 100)), output=str(settings.OUTPUT_DIR / "reweave_path.txt"))

        # logger.info("=== 绣织（embroider）示例 ====")
        # # 使用绣织功能，按织样构造质径
        # embroider_result = tl.embroider(
        #     input_pattern="s0x2 -> s2x6", output=str(settings.OUTPUT_DIR / "embroider_path.txt")
        # )
        # logger.info(f"绣织结果: {embroider_result}")
        #
        # logger.info("=== 广织（dream）示例 ====")
        # # 使用广织功能，生成幻径
        # dream_result = tl.dream(input_pattern="s0x2 -> s2x6", output=str(settings.OUTPUT_DIR / "dream_path.txt"))
        # logger.info(f"广织结果: {dream_result}")
        #
        # # 演示使用JSON格式的织样
        # logger.info("=== 使用JSON格式织样的绣织示例 ====")
        # json_pattern = '[{"state": "s0", "duration": 20}, {"state": "s2", "duration": 60}]'
        # json_result = tl.embroider(
        #     input_pattern=json_pattern, output=str(settings.OUTPUT_DIR / "json_pattern_path.txt")
        # )
        # logger.info(f"JSON格式织样绣织结果: {json_result}")

    except NotImplementedError:
        logger.info("功能尚未实现，跳过该操作")
    except Exception:
        logger.error(f"API调用失败: {traceback.format_exc()}", exc_info=True)

    logger.info("TraceLoom示例脚本完成")


if __name__ == "__main__":
    main()
