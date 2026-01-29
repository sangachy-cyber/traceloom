# -*- coding: utf-8 -*-
"""原始轨迹片段

加载原始轨迹数据，转换为观测数据列表，用于径元提取和轨迹分析。

示例:
    # 创建原始轨迹片段
    from traceloom.domain.raw_trace import RawTraceSegment
    import pandas as pd

    # 创建示例 DataFrame
    df = pd.DataFrame({
        'delay_up': [10.0] * 120,
        'delay_down': [8.0] * 120,
        'loss_up': [0.01] * 120,
        'loss_down': [0.005] * 120,
        'bw_up': [50.0] * 120,
        'bw_down': [100.0] * 120
    })

    # 从 DataFrame 创建原始轨迹片段
    segment = RawTraceSegment.from_dataframe(
        df=df,
        trace_name="test_trace",
        start_index=0,
        length=110
    )

    # 获取主体和融尾观测数据
    body_obs = segment.get_body_observations()
    tail_obs = segment.get_tail_observations()

    # 检查是否有效
    print(f"轨迹片段是否有效: {segment.is_valid}")
"""

from traceloom.domain.pathlet import PathletMeta

# 向后兼容的别名
RawTraceSegment = PathletMeta
