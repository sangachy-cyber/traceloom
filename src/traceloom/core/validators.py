# -*- coding: utf-8 -*-
"""输入验证模块

提供API输入验证的功能，防止注入攻击和非法输入。
"""

import re
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator

from traceloom.core.exceptions import ValidationError as TraceLoomValidationError


class BaseValidator:
    """基础验证器

    提供通用的输入验证方法
    """

    @staticmethod
    def validate_pathlet_id(pathlet_id: str) -> bool:
        """验证径元ID

        Args:
            pathlet_id: 径元ID

        Returns:
            bool: 是否有效
        """
        # 径元ID应该由字母、数字、下划线组成
        pattern = r'^[a-zA-Z0-9_]+$'
        return bool(re.match(pattern, pathlet_id))

    @staticmethod
    def validate_trace_name(trace_name: str) -> bool:
        """验证轨迹名称

        Args:
            trace_name: 轨迹名称

        Returns:
            bool: 是否有效
        """
        # 轨迹名称应该由字母、数字、下划线、连字符组成
        pattern = r'^[a-zA-Z0-9_-]+$'
        return bool(re.match(pattern, trace_name))

    @staticmethod
    def validate_state_id(state_id: int) -> bool:
        """验证状态ID

        Args:
            state_id: 状态ID

        Returns:
            bool: 是否有效
        """
        # 状态ID应该是非负整数
        return isinstance(state_id, int) and state_id >= -1

    @staticmethod
    def validate_delay(delay: float) -> bool:
        """验证时延值

        Args:
            delay: 时延值（毫秒）

        Returns:
            bool: 是否有效
        """
        # 时延应该是非负浮点数，且不超过2000毫秒
        return isinstance(delay, (int, float)) and 0 <= delay <= 2000

    @staticmethod
    def validate_loss(loss: float) -> bool:
        """验证丢包率

        Args:
            loss: 丢包率

        Returns:
            bool: 是否有效
        """
        # 丢包率应该在-0.01到1.01之间
        return isinstance(loss, (int, float)) and -0.01 <= loss <= 1.01

    @staticmethod
    def validate_bandwidth(bw: float) -> bool:
        """验证带宽

        Args:
            bw: 带宽（Mbps）

        Returns:
            bool: 是否有效
        """
        # 带宽应该是非负浮点数
        return isinstance(bw, (int, float)) and bw >= 0

    @staticmethod
    def validate_dataset(dataset: str) -> bool:
        """验证数据集划分

        Args:
            dataset: 数据集划分（train/test/val）

        Returns:
            bool: 是否有效
        """
        # 数据集划分应该是train、test或val
        valid_datasets = ['train', 'test', 'val']
        return dataset in valid_datasets


class PathletValidator(BaseValidator):
    """径元验证器

    专门用于验证径元相关的输入
    """

    @staticmethod
    def validate_pathlet_data(pathlet_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证径元数据

        Args:
            pathlet_data: 径元数据

        Returns:
            Dict[str, Any]: 验证后的数据

        Raises:
            TraceLoomValidationError: 如果验证失败
        """
        # 验证径元ID
        if 'pathlet_id' in pathlet_data:
            pathlet_id = pathlet_data['pathlet_id']
            if not BaseValidator.validate_pathlet_id(pathlet_id):
                raise TraceLoomValidationError(f"无效的径元ID: {pathlet_id}")

        # 验证轨迹名称
        if 'trace_name' in pathlet_data:
            trace_name = pathlet_data['trace_name']
            if not BaseValidator.validate_trace_name(trace_name):
                raise TraceLoomValidationError(f"无效的轨迹名称: {trace_name}")

        # 验证起始索引
        if 'start_index' in pathlet_data:
            start_index = pathlet_data['start_index']
            if not isinstance(start_index, int) or start_index < 0:
                raise TraceLoomValidationError(f"无效的起始索引: {start_index}")

        # 验证数据集划分
        if 'dataset' in pathlet_data:
            dataset = pathlet_data['dataset']
            if not BaseValidator.validate_dataset(dataset):
                raise TraceLoomValidationError(f"无效的数据集划分: {dataset}")

        return pathlet_data


class PatternValidator(BaseValidator):
    """织样验证器

    专门用于验证织样相关的输入
    """

    @staticmethod
    def validate_pattern_string(pattern_string: str) -> bool:
        """验证织样字符串

        Args:
            pattern_string: 织样字符串，如 "s0x2 -> s1x3"

        Returns:
            bool: 是否有效
        """
        # 织样字符串应该符合特定格式
        pattern = r'^([a-zA-Z0-9]+x\d+\s*->\s*)*[a-zA-Z0-9]+x\d+$'
        return bool(re.match(pattern, pattern_string))

    @staticmethod
    def validate_state_duration(state_duration: tuple) -> bool:
        """验证状态-持续时间对

        Args:
            state_duration: 状态-持续时间对，如 ("s0", 2)

        Returns:
            bool: 是否有效
        """
        if len(state_duration) != 2:
            return False

        state_name, duration = state_duration

        # 验证状态名称
        state_pattern = r'^[a-zA-Z0-9]+$'
        if not re.match(state_pattern, state_name):
            return False

        # 验证持续时间
        if not isinstance(duration, (int, float)) or duration <= 0:
            return False

        return True


class APIValidator:
    """API输入验证器

    专门用于验证API输入
    """

    @staticmethod
    def validate_api_input(input_data: Any, expected_type: type) -> bool:
        """验证API输入类型

        Args:
            input_data: API输入数据
            expected_type: 期望的类型

        Returns:
            bool: 是否有效
        """
        return isinstance(input_data, expected_type)

    @staticmethod
    def validate_query_params(query_params: Dict[str, Any], required_params: List[str]) -> bool:
        """验证查询参数

        Args:
            query_params: 查询参数字典
            required_params: 必需的参数列表

        Returns:
            bool: 是否有效
        """
        # 检查所有必需参数是否存在
        for param in required_params:
            if param not in query_params:
                return False
        return True


# Pydantic模型

class PathletCreate(BaseModel):
    """创建径元的请求模型
    """
    pathlet_id: str = Field(..., description="径元ID")
    trace_name: str = Field(..., description="轨迹名称")
    start_index: int = Field(..., ge=0, description="起始索引")
    dataset: str = Field(..., description="数据集划分")

    @validator('pathlet_id')
    def validate_pathlet_id(cls, v):
        if not BaseValidator.validate_pathlet_id(v):
            raise ValueError('无效的径元ID')
        return v

    @validator('trace_name')
    def validate_trace_name(cls, v):
        if not BaseValidator.validate_trace_name(v):
            raise ValueError('无效的轨迹名称')
        return v

    @validator('dataset')
    def validate_dataset(cls, v):
        if not BaseValidator.validate_dataset(v):
            raise ValueError('无效的数据集划分')
        return v


class WeaveRequest(BaseModel):
    """织径请求模型
    """
    input_data: Union[str, List[Dict[str, Any]]] = Field(..., description="输入数据")
    mode: str = Field(..., description="织径模式")

    @validator('mode')
    def validate_mode(cls, v):
        valid_modes = ['reweave', 'stitch', 'dream']
        if v not in valid_modes:
            raise ValueError('无效的织径模式')
        return v


class PathletQuery(BaseModel):
    """径元查询模型
    """
    state_id: Optional[int] = Field(None, description="状态ID")
    is_valid: Optional[bool] = Field(None, description="是否有效")
    dataset: Optional[str] = Field(None, description="数据集划分")
    batch_size: Optional[int] = Field(None, ge=1, description="批处理大小")

    @validator('state_id')
    def validate_state_id(cls, v):
        if v is not None and not BaseValidator.validate_state_id(v):
            raise ValueError('无效的状态ID')
        return v

    @validator('dataset')
    def validate_dataset(cls, v):
        if v is not None and not BaseValidator.validate_dataset(v):
            raise ValueError('无效的数据集划分')
        return v


def validate_input(data: Any, validator_class: Optional[type] = None, **kwargs) -> Any:
    """通用输入验证函数

    Args:
        data: 要验证的数据
        validator_class: 验证器类
        **kwargs: 额外的验证参数

    Returns:
        Any: 验证后的数据

    Raises:
        TraceLoomValidationError: 如果验证失败
    """
    if validator_class is None:
        return data

    try:
        # 检查validator_class是否有validate方法
        if hasattr(validator_class, 'validate'):
            return validator_class.validate(data, **kwargs)
        else:
            return data
    except Exception as e:
        raise TraceLoomValidationError(f"输入验证失败: {str(e)}") from e
