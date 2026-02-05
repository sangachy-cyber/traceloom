# -*- coding: utf-8 -*-
"""引擎基类，定义统一的接口和公共方法"""

from typing import List

from traceloom.core.logger import logger
from traceloom.domain.pathlet import Observation
from traceloom.io.adapters._holowan import HoloWANTrace


class BaseEngine:
    """引擎基类，定义统一的接口和公共方法"""
    
    def weave(self, pattern, sampler):
        """织径方法，与其他引擎保持一致的接口
        
        参数:
            pattern: 织样对象
            sampler: 全局采样器实例，用于采样径元
            
        返回:
            HoloWANTrace: 生成的 HoloWANTrace 对象
        """
        # 从织样序列生成观测数据
        observations = []
        
        try:
            # 使用采样器根据织样序列采样径元
            state_duration_sequence = [(state, duration) for state, duration in pattern.sequence]
            pathlets = sampler.sample_pathlets(state_duration_sequence)
            logger.info(f"成功采样 {len(pathlets)} 个径元")
            
            # 从径元生成观测数据
            observations = self._generate_observations_from_pathlets(pathlets)
        except Exception as e:
            logger.error(f"织径操作失败: {e}")
            # 如果采样失败，使用模拟数据作为 fallback
            observations = self._generate_fallback_observations(pattern.sequence)
        
        logger.info(f"成功生成 {len(observations)} 个观测数据")
        
        # 从观测数据创建 HoloWANTrace 对象
        return HoloWANTrace.from_observations(observations)
    
    def _generate_observations_from_pathlets(self, pathlets):
        """从径元生成观测数据
        
        参数:
            pathlets: 径元列表
            
        返回:
            List[Observation]: 观测数据列表
        """
        observations = []
        
        for pathlet in pathlets:
            # 获取主体观测数据
            if hasattr(pathlet, "body") and hasattr(pathlet.body, "observations"):
                for obs in pathlet.body.observations:
                    observations.append(obs)
            else:
                # 如果径元结构不符合预期，使用默认值
                logger.warning(f"径元结构不符合预期: {pathlet}")
                # 为每个径元生成默认观测数据（10秒，100个样本）
                from traceloom.domain.pathlet import Observation
                for _ in range(100):
                    observations.append(Observation(
                        delay_up=50.0, loss_up=0.01, bw_up=50.0,
                        delay_down=50.0, loss_down=0.01, bw_down=50.0
                    ))
        
        return observations
    
    def _generate_fallback_observations(self, sequence):
        """生成 fallback 观测数据
        
        参数:
            sequence: 状态持续时间序列
            
        返回:
            List[Observation]: 观测数据列表
        """
        observations = []
        from traceloom.domain.pathlet import Observation
        
        for _state, duration in sequence:
            for _ in range(duration * 10):  # 10 Hz 采样率
                observations.append(Observation(
                    delay_up=50.0, loss_up=0.01, bw_up=50.0,
                    delay_down=50.0, loss_down=0.01, bw_down=50.0
                ))
        
        return observations
