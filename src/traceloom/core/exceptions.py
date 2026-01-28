# -*- coding: utf-8 -*-
"""LoomNet自定义异常类定义
所有异常集中于此定义
"""


class LoomNetBaseException(Exception):
    """LoomNet基础异常类
    所有自定义异常的父类
    """

    pass


class ConfigError(LoomNetBaseException):
    """配置错误
    当配置文件读取或解析失败时抛出
    """

    pass


class DataError(LoomNetBaseException):
    """数据错误
    当数据格式、范围或内容不符合要求时抛出
    """

    pass


class ValidationError(LoomNetBaseException):
    """验证错误
    当参数或数据验证失败时抛出
    """

    pass


class NetworkParameterError(LoomNetBaseException):
    """网络参数错误
    当网络参数超出允许范围时抛出
    """

    pass


class TraceGenerationError(LoomNetBaseException):
    """轨迹生成错误
    当生成网络轨迹失败时抛出
    """

    pass


class ExportError(LoomNetBaseException):
    """导出错误
    当导出数据或结果失败时抛出
    """

    pass


class FileOperationError(LoomNetBaseException):
    """文件操作错误
    当文件读写操作失败时抛出
    """

    pass


class ModuleNotFoundError(LoomNetBaseException):
    """模块未找到错误
    当请求的模块不存在时抛出
    """

    pass


class InvalidStateError(LoomNetBaseException):
    """无效状态错误
    当状态转换或状态使用无效时抛出
    """

    pass


class StateMappingError(LoomNetBaseException):
    """状态映射错误
    当状态名无法映射为ID时抛出
    """

    pass


class PathletSamplingError(LoomNetBaseException):
    """径元采样错误
    当无法采样到足够径元时抛出
    """

    pass


class SplicingError(LoomNetBaseException):
    """拼接错误
    当径元拼接失败时抛出
    """

    pass
