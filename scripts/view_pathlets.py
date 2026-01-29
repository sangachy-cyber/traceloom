#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查看径元内容的脚本

用于查看生成的径元数据，包括数量、状态分布和具体径元信息
"""

from traceloom.core.logger import logger
from traceloom.storage.pathlet_storage import PathletStorage


def view_pathlets():
    """查看径元内容"""
    # 初始化PathletStorage
    storage = PathletStorage()

    # 获取径元数量
    pathlet_count = storage.get_pathlet_count()
    logger.info(f"径元总数: {pathlet_count}")

    if pathlet_count == 0:
        logger.warning("没有找到径元数据")
        return

    # 获取状态分布
    state_distribution = storage.get_state_distribution()
    logger.info(f"状态分布: {state_distribution}")

    # 加载所有径元
    pathlets = storage.load_pathlets()
    logger.info(f"成功加载 {len(pathlets)} 个径元")

    # 查看前5个径元的详细信息
    logger.info("\n前5个径元的详细信息:")
    for i, pathlet in enumerate(pathlets[:5]):
        logger.info(f"\n径元 {i + 1}:")
        logger.info(f"  ID: {pathlet.pathlet_id}")
        logger.info(f"  主体观测数据数量: {len(pathlet.body.observations)}")
        logger.info(f"  融尾观测数据数量: {len(pathlet.tail.observations)}")

        # 获取原始数据
        raw_data = storage.get_raw_profile(pathlet.pathlet_id)
        if raw_data:
            logger.info(f"  来源轨迹: {raw_data['trace_name']}")
            logger.info(f"  起始索引: {raw_data['start_index']}")
            logger.info(f"  是否有效: {raw_data['is_valid']}")

            # 查看统计信息
            ctx_values = raw_data["ctx_values"]
            logger.info("  统计信息:")
            logger.info(f"    上行延迟均值: {ctx_values.delay_up_mean:.2f} ms")
            logger.info(f"    下行延迟均值: {ctx_values.delay_down_mean:.2f} ms")
            logger.info(f"    上行丢包率均值: {ctx_values.loss_up_mean * 100:.2f}% ({ctx_values.loss_up_mean:.4f})")
            logger.info(f"    上行丢包率最大值: {ctx_values.loss_up_max * 100:.2f}% ({ctx_values.loss_up_max:.4f})")
            logger.info(f"    下行丢包率均值: {ctx_values.loss_down_mean * 100:.2f}% ({ctx_values.loss_down_mean:.4f})")
            logger.info(f"    下行丢包率最大值: {ctx_values.loss_down_max * 100:.2f}% ({ctx_values.loss_down_max:.4f})")
            logger.info(f"    上行带宽均值: {ctx_values.bw_up_mean:.2f} Mbps")
            logger.info(f"    上行带宽最大值: {ctx_values.bw_up_max:.2f} Mbps")
            logger.info(f"    下行带宽均值: {ctx_values.bw_down_mean:.2f} Mbps")
            logger.info(f"    下行带宽最大值: {ctx_values.bw_down_max:.2f} Mbps")


if __name__ == "__main__":
    view_pathlets()
