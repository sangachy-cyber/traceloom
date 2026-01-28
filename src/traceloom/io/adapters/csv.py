# -*- coding: utf-8 -*-
"""CSV 输入输出模块。

用于读写 processed/ 目录下的 CSV 文件。
"""

from pathlib import Path
from typing import Dict

import pandas as pd

from traceloom.core.logger import logger


class CSVIO:
    """CSV 输入输出器。

    示例:
        from traceloom.io.csv_io import CSVIO

        # 初始化CSVIO
        csv_io = CSVIO()

        # 读取 CSV 文件
        df = csv_io.read(Path("processed/trace_001.csv"))

        # 写入 CSV 文件
        csv_io.write(df, Path("processed/trace_002.csv"))

    属性:
        delimiter: CSV 分隔符
        encoding: 文件编码
    """

    def __init__(self, delimiter: str = ",", encoding: str = "utf-8"):
        """初始化CSVIO。

        参数:
            delimiter: CSV 分隔符
            encoding: 文件编码
        """
        self.delimiter = delimiter
        self.encoding = encoding

    def read(self, file_path: Path) -> pd.DataFrame:
        """读取 CSV 文件。

        参数:
            file_path: CSV 文件路径

        返回:
            pd.DataFrame: 读取的数据

        异常:
            FileNotFoundError: 文件不存在时抛出
            ValueError: 文件格式错误时抛出
        """
        if not file_path.exists():
            logger.error(f"CSV 文件不存在: {file_path}")
            raise FileNotFoundError(f"CSV 文件不存在: {file_path}")

        try:
            logger.info(f"读取 CSV 文件: {file_path}")
            df = pd.read_csv(file_path, delimiter=self.delimiter, encoding=self.encoding)
            logger.info(f"成功读取 CSV 文件，共 {len(df)} 行数据")
            return df
        except pd.errors.ParserError as e:
            logger.error(f"CSV 文件格式错误: {e}")
            raise ValueError(f"CSV 文件格式错误: {e}") from e

    def write(self, df: pd.DataFrame, file_path: Path) -> bool:
        """写入 CSV 文件。

        参数:
            df: 要写入的数据
            file_path: CSV 文件路径

        返回:
            bool: 是否成功写入
        """
        try:
            logger.info(f"写入 CSV 文件: {file_path}")
            df.to_csv(file_path, index=False, delimiter=self.delimiter, encoding=self.encoding)
            logger.info(f"成功写入 CSV 文件，共 {len(df)} 行数据")
            return True
        except Exception as e:
            logger.error(f"写入 CSV 文件失败: {e}")
            return False

    def read_traces(self, dir_path: Path) -> Dict[str, pd.DataFrame]:
        """读取目录下所有CSV 文件。

        参数:
            dir_path: 目录路径

        返回:
            Dict[str, pd.DataFrame]: 文件名到 DataFrame 的映射
        """
        traces = {}

        for file_path in dir_path.glob("*.csv"):
            trace_name = file_path.stem
            df = self.read(file_path)
            traces[trace_name] = df

        return traces

    def write_traces(self, traces: Dict[str, pd.DataFrame], dir_path: Path) -> bool:
        """写入多个轨迹到CSV 文件。

        参数:
            traces: 文件名到 DataFrame 的映射
            dir_path: 目录路径

        返回:
            bool: 是否成功写入
        """
        success = True

        # 确保目录存在
        dir_path.mkdir(parents=True, exist_ok=True)

        for trace_name, df in traces.items():
            file_path = dir_path / f"{trace_name}.csv"
            if not self.write(df, file_path):
                success = False

        return success

    def write_dataframe(self, df: pd.DataFrame, file_path: Path) -> bool:
        """写入 DataFrame 到 CSV 文件。

        参数:
            df: 要写入的数据
            file_path: CSV 文件路径

        返回:
            bool: 是否成功写入
        """
        return self.write(df, file_path)

    def read_dataframe(self, file_path: Path) -> pd.DataFrame:
        """从 CSV 文件读取 DataFrame。

        参数:
            file_path: CSV 文件路径

        返回:
            pd.DataFrame: 读取的数据
        """
        return self.read(file_path)
