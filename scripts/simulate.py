#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""仿真脚本
调用 pipelines.simulation.run() 执行仿真流程
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Optional

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from training.pathlet.simulation import run

from traceloom.core.logger import setup_logger


def parse_args() -> argparse.Namespace:
    """解析命令行参数

    Returns:
        argparse.Namespace: 解析后的命令行参数
    """
    parser = argparse.ArgumentParser(description="LoomNet 仿真脚本")

    parser.add_argument(
        "--scenario",
        type=str,
        default="splice",
        choices=["splice", "synthesize", "extrapolate"],
        help="仿真场景类型 (默认: %(default)s)",
    )

    parser.add_argument(
        "--output-format", type=str, default="hwan", choices=["hwan", "csv"], help="输出格式 (默认: %(default)s)"
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="日志级别 (默认: %(default)s)",
    )

    return parser.parse_args()


def main() -> None:
    """主函数

    解析命令行参数，初始化日志，执行仿真流程
    """
    # 解析命令行参数
    args = parse_args()

    # 初始化日志
    setup_logger()

    # 准备仿真参数
    params: Optional[Dict] = {
        # 可以根据需要添加默认参数
    }

    # 运行仿真流水线
    run(scenario_type=args.scenario, params=params, output_format=args.output_format)


if __name__ == "__main__":
    main()
