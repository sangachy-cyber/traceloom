import os
import sys
from pathlib import Path

from traceloom.core.logger import logger


# 中文字体配置
def get_chinese_font():
    """获取适合当前系统的中文字体

    示例:
        from traceloom.core.utils import get_chinese_font
        font_path = get_chinese_font()
        print(f"使用中文字体: {font_path}")

    返回:
        str: 中文字体路径
    """
    # 系统默认字体映射
    font_map = {
        "darwin": [
            "/System/Library/Fonts/Hiragino Sans GB.ttc",  # macOS 冬青黑体
            "/System/Library/Fonts/STHeiti Medium.ttc",  # macOS 华文黑体
            "/System/Library/Fonts/STHeiti Light.ttc",  # macOS 华文细黑
            "/System/Library/Fonts/PingFang.ttc",  # macOS 苹方（备选）
        ],
        "win32": [
            "C:/Windows/Fonts/simhei.ttf",  # Windows 黑体
            "C:/Windows/Fonts/msyh.ttc",  # Windows 微软雅黑
        ],
        "linux": [
            # 文泉驿系列
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",  # Linux 文泉驿正黑
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # Linux 文泉驿微米黑
            # Noto 系列
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Noto Sans CJK
            "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",  # Noto Serif CJK
            # 文鼎系列
            "/usr/share/fonts/truetype/arphic/ukai.ttc",  # AR PL UKai CN
            "/usr/share/fonts/truetype/arphic/uming.ttc",  # AR PL UMing CN
        ],
    }

    system = sys.platform
    system_fonts = font_map.get(system, [])

    # 首先尝试系统特定的字体列表
    for font_path in system_fonts:
        if os.path.exists(font_path):
            return font_path

    # 尝试通用备选字体
    fallback_fonts = [
        "/Library/Fonts/Arial Unicode.ttf",  # macOS 备选
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",  # macOS 补充字体
    ]

    for fallback in fallback_fonts:
        if os.path.exists(fallback):
            return fallback

    # 最后尝试使用系统fc-list命令查找中文字体
    try:
        import subprocess

        result = subprocess.run(["fc-list", ":lang=zh"], capture_output=True, text=True)
        if result.returncode == 0:
            # 解析fc-list输出，提取第一个字体路径
            for line in result.stdout.split("\n"):
                if line.strip():
                    font_path = line.split(":")[0]
                    if os.path.exists(font_path):
                        return font_path
    except Exception as e:
        logger.warning(f"使用fc-list查找字体失败: {e}")

    return None


def setup_chinese_font():
    """设置Matplotlib的中文字体

    示例:
        from traceloom.core.utils import setup_chinese_font
        setup_chinese_font()
    """

    import matplotlib.font_manager as fm
    import matplotlib.pyplot as plt

    # 首先尝试获取系统中实际存在的字体文件
    font_path = get_chinese_font()

    # 如果找到字体文件，将其添加到fontManager中
    if font_path:
        logger.info(f"找到中文字体文件: {font_path}")
        # 检查是否已添加该字体
        font_names = [f.name for f in fm.fontManager.ttflist]
        font_props = fm.FontProperties(fname=font_path)
        font_name = font_props.get_name()

        if font_name not in font_names:
            fm.fontManager.addfont(font_path)
            logger.info(f"已添加中文字体: {font_name}")
    else:
        # 如果没有找到字体文件，尝试重新扫描系统字体目录
        logger.warning("未找到预定义的中文字体文件，尝试重新扫描系统字体")
        fm.fontManager.ttflist.clear()  # 清空现有字体列表
        fm.fontManager._load_system_fonts()  # 重新加载系统字体

    # 重新获取字体列表
    font_list = [f.name for f in fm.fontManager.ttflist]

    # 尝试多种中文字体名称，按优先级排序
    chinese_fonts = [
        "WenQuanYi Zen Hei",  # 文泉驿正黑
        "WenQuanYi Micro Hei",  # 文泉驿微米黑
        "Noto Sans CJK SC",  # Noto 简体中文
        "Noto Serif CJK SC",  # Noto 衬线简体中文
        "AR PL UKai CN",  # 文鼎楷体
        "AR PL UMing CN",  # 文鼎明体
        "SimHei",  # 黑体
        "Microsoft YaHei",  # 微软雅黑
        "PingFang SC",  # 苹方
        "Hiragino Sans GB",  # macOS 冬青黑体
        "STHeiti",  # macOS 华文黑体
        "Arial Unicode MS",  # Arial Unicode
    ]

    # 选择系统中实际存在的第一个中文字体
    available_font = None
    for font in chinese_fonts:
        if font in font_list:
            available_font = font
            break

    if available_font:
        # 使用字体名称
        plt.rcParams["font.sans-serif"] = [available_font] + [
            "WenQuanYi Zen Hei",
            "WenQuanYi Micro Hei",
            "Noto Sans CJK SC",
            "SimHei",
        ]
        logger.info(f"使用中文字体: {available_font}")
    else:
        # 尝试直接使用字体文件路径
        if font_path:
            plt.rcParams["font.sans-serif"] = [fm.FontProperties(fname=font_path).get_name()]
            logger.info(f"直接使用字体文件: {font_path}")
        else:
            # 如果没有找到中文字体，使用默认字体，但确保负号显示正常
            logger.warning("未找到可用中文字体，使用默认字体")

    # 确保负号显示正常
    plt.rcParams["axes.unicode_minus"] = False
