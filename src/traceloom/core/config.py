from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """TraceLoom 配置类

    管理所有配置项，支持通过环境变量覆盖默认值。
    所有配置项均使用 UPPER_SNAKE_CASE 命名规范。

    示例:
        # 默认配置使用
        from traceloom.core.config import settings
        print(settings.DATA_DIR)

        # 通过环境变量覆盖
        # export TRACELOOM_DATA_DIR=/path/to/data
    """

    # ─────────────── 用户可配置项（12项）───────────────

    # 1. 根数据目录（用户最常自定义的位置）
    DATA_DIR: Path = Path("data")
    """根数据目录，可通过环境变量 TRACELOOM_DATA_DIR 覆盖"""

    # 2. 输出目录
    OUTPUT_DIR: Path = DATA_DIR / "outputs"
    """输出目录，用于存储生成的文件和结果"""

    # 3. 径元库路径（支持多版本径元库）
    PATHLETS_DIR: Path = DATA_DIR / "pathlets" / "default"
    """径元库路径，支持多版本径元库"""

    # 4. 模型路径（支持多模型实验）
    MODELS_DIR: Path = DATA_DIR / "models" / "default"
    """模型路径，支持多模型实验"""

    BEFORE_LABEL_DIR: Path = DATA_DIR / "before_labels"
    """.BeforeLabel 目录，用于存储.BeforeLabel 文件"""

    AFTER_LABEL_DIR: Path = DATA_DIR / "after_labels"
    """.AfterLabel 目录，用于存储.AfterLabel 文件"""

    # 5. 径元结构参数
    BODY_SIZE: int = 100
    """【主干】长度，径元的主体部分长度"""

    TAIL_SIZE: int = 10
    """【融尾】长度，径元的融合尾部长度"""

    BODY_STRIDE: int = 100
    """切片步长，径元提取时的步长"""

    # 6. 文件格式
    TRACE_EXT: str = ".txt"
    """轨迹文件扩展名"""

    WEAVING_LAW_FILE: Path = MODELS_DIR / "weaving_law.pkl"
    """编织规则文件路径"""

    PATHLET_PARQUET_FILE: str = "pathlets.parquet"
    """径元存储的 Parquet 文件名"""

    # 7. 观测字段定义（顺序必须与原始数据一致）
    OBSERVATION_FIELDS: tuple[str, ...] = ("delay_up", "loss_up", "bw_up", "delay_down", "loss_down", "bw_down")
    """观测字段定义，顺序必须与原始数据一致"""

    OBSERVATION_DIM: int = len(OBSERVATION_FIELDS)  # = 6
    """观测维度，由观测字段数量决定"""

    # 8. 日志
    LOG_LEVEL: str = "INFO"
    """日志级别"""

    # ─────────────── 动态计算路径（不暴露为配置）───────────────
    @property
    def RAW_DIR(self) -> Path:
        """原始数据目录

        固定为 DATA_DIR / 'raw'，用于存储原始轨迹数据。

        Returns:
            Path: 原始数据目录路径
        """
        return self.DATA_DIR / "raw"

    model_config = ConfigDict(
        env_prefix="TRACELOOM_",
        description="""配置类的配置

        Attributes:
            env_prefix: str = "TRACELOOM_"
                环境变量前缀，用于覆盖配置项
        """,
    )


def get_settings() -> Settings:
    """获取配置实例

    创建并返回全局配置实例。

    Returns:
        Settings: 配置实例
    """
    return Settings()


# 创建全局配置实例
settings = get_settings()
"""全局配置实例，供整个项目使用"""
