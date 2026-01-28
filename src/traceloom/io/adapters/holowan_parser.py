# -*- coding: utf-8 -*-
"""HoloWAN解析器（HoloWANParser）。

从HoloWAN原始文件解析序列观测，返回【观元】列表。
"""

from pathlib import Path
from typing import Dict, List

from traceloom.core.exceptions import ValidationError
from traceloom.core.logger import logger
from traceloom.domain.pathlet import Observation


class HoloWANParser:
    """HoloWAN解析器，从HoloWAN原始文件解析序列观测，返回【观元】列表。

    示例:
        from traceloom.io.adapters.holowan_parser import HoloWANParser

        # 解析原始文件
        observations = HoloWANParser.parse_file("input.txt")

    属性:
        column_names: 6列观测的列名
        expected_columns: 预期的列数
    """

    column_names = ["delay_up", "loss_up", "bw_up", "delay_down", "loss_down", "bw_down"]
    expected_columns = 6

    @classmethod
    def parse_file(cls, file_path: str) -> List[Observation]:
        """从HoloWAN原始文件解析序列观测。

        参数:
            file_path: 原始文件路径

        返回:
            List[Observation]: 解析后的观元列表

        异常:
            FileNotFoundError: 文件不存在
            ValidationError: 文件格式无效
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"原始文件不存在：{file_path}")

        logger.info(f"解析HoloWAN原始文件：{file_path}")

        # 读取文件内容，找到数据部分
        with open(file_path, 'r') as f:
            lines = f.readlines()

        # 找到数据部分的开始位置
        data_start = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            # 数据部分通常在分隔线之后
            if stripped == '------------------------------------------------':
                data_start = i + 1
                break

        # 提取数据行并处理
        data_lines = [line.strip() for line in lines[data_start:] if line.strip()]
        if not data_lines:
            raise ValidationError("HoloWAN文件中未找到数据部分")

        # 解析数据行
        observations = []
        for line in data_lines:
            parts = line.split(',')
            if len(parts) != cls.expected_columns:
                continue  # 跳过格式不正确的行

            try:
                values = [float(p) for p in parts]
                obs = Observation(
                    delay_up=values[0],
                    loss_up=values[1],
                    bw_up=values[2],
                    delay_down=values[3],
                    loss_down=values[4],
                    bw_down=values[5]
                )
                observations.append(obs)
            except (ValueError, IndexError):
                continue  # 跳过解析失败的行

        if not observations:
            raise ValidationError("无法从HoloWAN文件解析出有效数据")

        logger.info(f"解析完成，共 {len(observations)} 个观元")
        return observations

    @classmethod
    def parse_folder(cls, folder_path: str) -> Dict[str, List[Observation]]:
        """解析文件夹中的所有HoloWAN原始文件。

        参数:
            folder_path: 文件夹路径

        返回:
            Dict[str, List[Observation]]: 文件名到观元列表的映射

        异常:
            FileNotFoundError: 文件夹不存在
        """
        folder_path = Path(folder_path)

        if not folder_path.exists():
            raise FileNotFoundError(f"文件夹不存在：{folder_path}")

        logger.info(f"解析文件夹中的HoloWAN原始文件：{folder_path}")

        observations = {}

        # 遍历文件夹中的所有txt文件
        for file_path in folder_path.glob("*.txt"):
            try:
                obs_list = cls.parse_file(file_path)
                observations[file_path.name] = obs_list
                logger.info(f"成功解析文件：{file_path.name}")
            except Exception as e:
                logger.error(f"解析文件失败 {file_path.name}：{e}")
                continue

        logger.info(f"文件夹解析完成，成功解析 {len(observations)} 个文件")

        return observations
