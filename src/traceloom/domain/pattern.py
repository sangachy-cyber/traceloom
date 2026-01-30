# -*- coding: utf-8 -*-
"""织样（Pattern）模块

统一解析和管理织样，支持多种格式输入
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from loguru import logger

from traceloom.core.exceptions import ValidationError


class Pattern:
    """织样类，统一表示和解析织样

    示例:
        # 从字符串创建
        pattern1 = Pattern.from_string("s0x2 -> s2x6")

        # 从JSON列表创建
        pattern2 = Pattern.from_json([{"state": "s0", "duration": 20}, {"state": "s2", "duration": 60}])

        # 访问内部序列
        sequence = pattern1.sequence  # [("s0", 20), ("s2", 60)]

        # 转换回字符串
        str_pattern = pattern1.to_string()  # "s0x2 -> s2x6"

    属性
        sequence: 标准化的状态序列，格式为List[Tuple[str, int]]（状态名 + 持续时间秒）
    """

    def __init__(self, sequence: List[Tuple[str, int]]):
        """初始化织样

        参数:
            sequence: 状态序列，格式为List[Tuple[str, int]]

        异常:
            ValueError: 当序列中的状态名或持续时间不合法时
        """
        self.sequence = self._validate(sequence)

    @classmethod
    def from_string(cls, s: str) -> "Pattern":
        """从字符串创建织样

        支持的格式
            - "s0x2 -> s2x6"：s0 持续 20 秒，然后 s2 持续 60 秒

        参数:
            s: 织样字符串

        返回:
            Pattern: 解析后的织样对象

        异常:
            ValueError: 当字符串格式不合法时
        """
        parts = [part.strip() for part in s.split("->")]
        seq = []
        for part in parts:
            match = re.match(r"s(\d+)x(\d+)", part)
            if not match:
                raise ValueError(f"无效的织样段: {part}")
            state_id, mult = match.groups()
            state = f"s{state_id}"
            duration_sec = int(mult) * 10  # sxK 即K×10秒
            seq.append((state, duration_sec))
        return cls(seq)

    @classmethod
    def from_json(cls, data: List[Dict[str, Any]]) -> "Pattern":
        """从JSON列表创建织样

        支持的格式
            - [{"state": "s0", "duration": 20}, {"state": "s2", "duration": 60}]

        参数:
            data: JSON格式的织样数据

        返回:
            Pattern: 解析后的织样对象

        异常:
            ValueError: 当JSON格式不合法时
        """
        seq = []
        for item in data:
            if not isinstance(item, dict):
                raise ValueError(f"织样项必须是字典: {item}")
            if "state" not in item or "duration" not in item:
                raise ValueError(f"织样项必须包含'state'和'duration': {item}")
            state = item["state"]
            duration = int(item["duration"])
            seq.append((state, duration))
        return cls(seq)

    @classmethod
    def from_state_list(cls, states: List[int]) -> "Pattern":
        """从状态列表创建织样

        支持的格式
            - [0, 1, 2, 3, 0, 0, 0, 0, 1, 1]: 连续相同状态会被合并

        参数:
            states: 状态ID列表

        返回:
            Pattern: 解析后的织样对象

        异常:
            ValueError: 当状态列表为空或包含无效状态时
        """
        if not states:
            raise ValueError("状态列表不能为空")

        # 合并连续相同状态
        merged_states = []
        current_state = states[0]
        count = 1

        for state in states[1:]:
            if state == current_state:
                count += 1
            else:
                merged_states.append((current_state, count))
                current_state = state
                count = 1

        # 添加最后一组状态
        merged_states.append((current_state, count))

        # 转换为Pattern序列格式
        seq = []
        for state_id, duration_count in merged_states:
            # 验证状态ID
            if not isinstance(state_id, int) or state_id < 0:
                raise ValueError(f"无效的状态ID: {state_id}")
            # 转换为状态名格式 "s{state_id}"
            state = f"s{state_id}"
            # 计算持续时间（秒），默认每个状态持续10秒
            duration_sec = duration_count * 10
            seq.append((state, duration_sec))

        return cls(seq)

    @staticmethod
    def _validate(seq: List[Tuple[str, int]]) -> List[Tuple[str, int]]:
        """验证状态序列的合法性

        参数:
            seq: 状态序列

        返回:
            List[Tuple[str, int]]: 验证通过的序列

        异常:
            ValueError: 当序列中的状态名或持续时间不合法时
        """
        for state, dur in seq:
            if not re.match(r"s\d+", state):
                raise ValueError(f"无效的状态名: {state}")
            if dur <= 0:
                raise ValueError(f"持续时间必须为正数 {dur}")
        return seq

    def to_string(self) -> str:
        """转换为字符串格式

        返回:
            str: 字符串格式的织样，如 "s0x2 -> s2x6"
        """
        parts = []
        for state, dur_sec in self.sequence:
            k = dur_sec // 10
            parts.append(f"{state}x{k}")
        return " -> ".join(parts)

    def to_json(self) -> List[Dict[str, Any]]:
        """转换为JSON格式

        返回:
            List[Dict[str, Any]]: JSON格式的织样
        """
        return [{"state": state, "duration": duration} for state, duration in self.sequence]

    def __repr__(self) -> str:
        """返回织样的字符串表示

        返回:
            str: 织样的字符串表示
        """
        return f"Pattern({self.to_string()})"

    def __eq__(self, other: object) -> bool:
        """比较两个织样是否相等

        参数:
            other: 另一个织样对象

        返回:
            bool: 如果两个织样相等则返回True，否则返回False
        """
        if not isinstance(other, Pattern):
            return False
        return self.sequence == other.sequence

    def __len__(self) -> int:
        """返回织样中的状态数量

        返回:
            int: 状态数量
        """
        return len(self.sequence)


class PatternParser:
    """织样解析器，统一处理各种输入格式

    示例:
        from traceloom.weaving.pattern_parser import PatternParser

        # 从文件路径创建
        pattern1 = PatternParser.parse("pattern.txt")

        # 从织样字符串创建
        pattern2 = PatternParser.parse("s0x2 -> s2x3")

        # 从JSON列表创建
        pattern3 = PatternParser.parse([{"state": "s0", "duration": 20}, {"state": "s2", "duration": 30}])

        # 从Pattern对象创建（直接返回）
        pattern4 = PatternParser.parse(pattern1)
    """

    @staticmethod
    def parse(input_data: Union[str, List[Dict[str, Any]], List[int], Pattern, Path]) -> Pattern:
        """统一解析输入数据，返回标准化Pattern对象

        参数:
            input_data: 输入数据，可以是文件路径、织样字符串、JSON列表、状态ID列表或Pattern对象

        返回:
            Pattern: 标准化的Pattern对象

        异常:
            ValidationError: 输入格式无效
            FileNotFoundError: 指定的文件不存在
        """
        # 如果已经是Pattern对象，直接返回
        if isinstance(input_data, Pattern):
            return input_data

        # 处理Path对象或字符串路径
        if isinstance(input_data, Path) or (isinstance(input_data, str) and Path(input_data).exists()):
            file_path = Path(input_data)
            return PatternParser._from_file(file_path)

        # 处理字符串
        if isinstance(input_data, str):
            return PatternParser._from_string(input_data)

        # 处理字典
        if isinstance(input_data, list):
            return PatternParser._from_state_list(input_data)

        # 处理JSON列表
        if isinstance(input_data, list):
            # 检查是否为状态ID列表
            if input_data and isinstance(input_data[0], int):
                try:
                    return Pattern.from_state_list(input_data)
                except ValueError as e:
                    raise ValidationError(f"状态列表解析失败：{e}") from e
            # 否则视为JSON列表
            return PatternParser._from_json(input_data)

        # 不支持的输入类型
        raise ValidationError(f"不支持的输入类型：{type(input_data).__name__}")

    @staticmethod
    def _from_file(file_path: Path) -> Pattern:
        """从文件创建织样

        参数:
            file_path: 文件路径

        返回:
            Pattern: 解析后的Pattern对象

        异常:
            FileNotFoundError: 文件不存在
            ValidationError: 文件内容格式无效
        """
        if not file_path.exists():
            raise FileNotFoundError(f"指定的文件不存在：{file_path}")

        # 读取文件内容
        with open(file_path, "r") as f:
            content = f.read().strip()

        # 尝试解析为字符串格式
        try:
            return Pattern.from_string(content)
        except ValueError as e:
            raise ValidationError(f"文件内容解析失败：{e}") from e

    @staticmethod
    def _from_string(s: str) -> Pattern:
        """从字符串创建织样

        参数:
            s: 织样字符串，可以是文本格式或JSON格式

        返回:
            Pattern: 解析后的Pattern对象

        异常:
            ValidationError: 字符串格式无效
        """
        # 尝试解析为JSON格式
        if s.strip().startswith("[") and s.strip().endswith("]"):
            try:
                json_data = json.loads(s)
                if isinstance(json_data, list):
                    return PatternParser._from_json(json_data)
            except json.JSONDecodeError:
                # JSON解析失败，继续尝试文本格式
                pass

        # 尝试解析为文本格式
        try:
            return Pattern.from_string(s)
        except ValueError as e:
            raise ValidationError(f"字符串解析失败：{e}") from e

    @staticmethod
    def _from_json(data: List[Dict[str, Any]]) -> Pattern:
        """从JSON列表创建织样

        参数:
            data: JSON列表

        返回:
            Pattern: 解析后的Pattern对象

        异常:
            ValidationError: JSON格式无效
        """
        try:
            return Pattern.from_json(data)
        except ValueError as e:
            raise ValidationError(f"JSON解析失败：{e}") from e

    @staticmethod
    def _from_state_list(data: List[int]) -> Pattern:
        try:
            return Pattern.from_state_list(data)
        except ValueError as e:
            raise ValidationError(f"List解析失败：{e}") from e
