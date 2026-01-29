# -*- coding: utf-8 -*-
"""【重织】阶段（reweaver）实现类。
用于拼接网络剖面序列，实现平滑过渡效果。
"""

from typing import Dict, List, Tuple, Union

import numpy as np

from traceloom.core.exceptions import SplicingError
from traceloom.core.logger import logger
from traceloom.domain.pathlet import BodyObservations, Observation, Pathlet
from traceloom.storage.pathlet_storage import PathletStatistics




class ProfileSequence:
    """剖面序列"""

    def __init__(self, sequence_id, profiles, metadata=None):
        self.sequence_id = sequence_id
        self.profiles = profiles
        self.metadata = metadata or {}


class Reweaver:
    """网络剖面重织器。
    用于拼接网络剖面序列，实现平滑过渡效果。

    示例:
        from traceloom.weaving.reweave.reweaver import Reweaver
        from training.common.profile import Pathlet, ContextData, ContinuationData
        from datetime import datetime

        # 准备两个网络剖面序列
        seq1 = [
            Pathlet(
                profile_id=f"p1_{i}",
                timestamp=datetime.now() + timedelta(seconds=i),
                context_data=ContextData(
                    delay_up=[100.0]*100, loss_up=[0.01]*100, bw_up=[10.0]*100,
                    delay_down=[100.0]*100, loss_down=[0.01]*100, bw_down=[10.0]*100
                ),
                continuation_data=ContinuationData(
                    delay_up=[100.0]*10, loss_up=[0.01]*10, bw_up=[10.0]*10,
                    delay_down=[100.0]*10, loss_down=[0.01]*10, bw_down=[10.0]*10
                )
            )
            for i in range(10)
        ]

        seq2 = [
            Pathlet(
                profile_id=f"p2_{i}",
                timestamp=datetime.now() + timedelta(seconds=10+i),
                context_data=ContextData(
                    delay_up=[200.0]*100, loss_up=[0.05]*100, bw_up=[5.0]*100,
                    delay_down=[200.0]*100, loss_down=[0.05]*100, bw_down=[5.0]*100
                ),
                continuation_data=ContinuationData(
                    delay_up=[200.0]*10, loss_up=[0.05]*10, bw_up=[5.0]*10,
                    delay_down=[200.0]*10, loss_down=[0.05]*10, bw_down=[5.0]*10
                )
            )
            for i in range(10)
        ]

        # 初始化重织器
        reweaver = Reweaver()

        # 拼接序列
        reweaved_seq = reweaver.splice(seq1, seq2)

    属性:
        transition_duration: 过渡持续时间（秒）
        transition_steps: 过渡步数
    """

    def __init__(self, transition_duration: float = 1.0, transition_steps: int = 10):
        """初始化网络剖面重织器。

        参数:
            transition_duration: 过渡持续时间（秒）
            transition_steps: 过渡步数
        """
        self.transition_duration = transition_duration
        self.transition_steps = transition_steps

    def _linear_interpolate(self, start: float, end: float, step: int) -> float:
        """线性插值计算过渡值

        参数:
            start: 起始值
            end: 结束值
            step: 当前步数，范围0到transition_steps

        返回:
            float: 插值结果
        """
        return start + (end - start) * (step / self.transition_steps)

    def _find_optimal_offset(self, profile_a: Pathlet, profile_b: Pathlet) -> int:
        """查找最佳切入点t*，实现动态对齐（安全偏移量）

        参数:
            profile_a: 前一个网络剖面
            profile_b: 后一个网络剖面

        返回:
            int: 最佳切入点t*，范围0到10
        """
        # 使用A的Tail（100-109）与B的前1秒（0-10）搜索最佳切入点
        # 计算A的Tail的平均斜率
        a_tail_delay_up = np.array(profile_a.cont_1s.delay_up)
        a_tail_loss_up = np.array(profile_a.cont_1s.loss_up)
        a_tail_bw_up = np.array(profile_a.cont_1s.bw_up)

        # 计算A的Tail的斜率
        a_delay_slope = np.diff(a_tail_delay_up).mean()
        a_loss_slope = np.diff(a_tail_loss_up).mean()
        a_bw_slope = np.diff(a_tail_bw_up).mean()

        best_offset = 0
        min_cost = float("inf")

        # 在B的前1秒（sample_index 0-10）搜索最佳切入点
        for t_star in range(0, 11):
            # 提取B的对应片段（10个点）
            # B的前10点（t_star到t_star+9）
            b_start_delay = profile_b.ctx_10s.delay_up[t_star : t_star + 10]
            b_start_loss = profile_b.ctx_10s.loss_up[t_star : t_star + 10]
            b_start_bw = profile_b.ctx_10s.bw_up[t_star : t_star + 10]

            # 计算B的对应片段的斜率
            b_delay_slope = np.diff(b_start_delay).mean()
            b_loss_slope = np.diff(b_start_loss).mean()
            b_bw_slope = np.diff(b_start_bw).mean()

            # 计算斜率差异成本
            delay_cost = abs(a_delay_slope - b_delay_slope)
            loss_cost = abs(a_loss_slope - b_loss_slope)
            bw_cost = abs(a_bw_slope - b_bw_slope)

            # 总成成本（可根据权重调整）
            total_cost = delay_cost + loss_cost + bw_cost

            if total_cost < min_cost:
                min_cost = total_cost
                best_offset = t_star

        return best_offset

    def _hermite_interpolate(self, a_tail: np.ndarray, b_head: np.ndarray, length: int = 10) -> np.ndarray:
        """使用Hermite插值生成过渡段

        参数:
            a_tail: A的Tail部分（10个点）
            b_head: B的Head部分（10个点）
            length: 过渡段长度（默认10个点）

        返回:
            np.ndarray: 插值后的过渡段
        """
        # Hermite插值需要起始点（A的Tail的最后一个点）、终点（B的Head的第一个点）及其导数
        # 计算A的Tail的最后一个点及其导数
        a_end = a_tail[-1]
        a_deriv = np.diff(a_tail).mean()

        # 计算B的Head的第一个点及其导数
        b_start = b_head[0]
        b_deriv = np.diff(b_head).mean()

        # 生成插值点
        x = np.linspace(0, 1, length)

        # Hermite基函数
        h00 = 2 * x**3 - 3 * x**2 + 1
        h10 = x**3 - 2 * x**2 + x
        h01 = -2 * x**3 + 3 * x**2
        h11 = x**3 - x**2

        # 生成插值结果
        interpolated = h00 * a_end + h10 * a_deriv + h01 * b_start + h11 * b_deriv

        return interpolated

    def _extract_profile_segment(self, profile: Pathlet, start_offset: int) -> Tuple[BodyObservations, PathletStatistics]:
        """从profile中提取从start_offset开始的100个点作为新的上下文数据

        参数:
            profile: 原始网络剖面
            start_offset: 起始偏移量，范围0-10

        返回:
            Tuple[ContextData, ContextValues]: 新的上下文数据和统计值
        """
        # 提取从start_offset开始的100个点
        end_offset = start_offset + 100

        # 提取各个参数的片段
        delay_up = profile.ctx_10s.delay_up[start_offset:end_offset]
        loss_up = profile.ctx_10s.loss_up[start_offset:end_offset]
        bw_up = profile.ctx_10s.bw_up[start_offset:end_offset]
        delay_down = profile.ctx_10s.delay_down[start_offset:end_offset]
        loss_down = profile.ctx_10s.loss_down[start_offset:end_offset]
        bw_down = profile.ctx_10s.bw_down[start_offset:end_offset]

        # 计算新的ContextValues
        ctx_values = PathletStatistics(
            delay_up_mean=np.mean(delay_up),
            delay_up_std=np.std(delay_up),
            delay_down_mean=np.mean(delay_down),
            delay_down_std=np.std(delay_down),
            loss_up_mean=np.mean(loss_up),
            loss_up_max=np.max(loss_up),
            loss_down_mean=np.mean(loss_down),
            loss_down_max=np.max(loss_down),
            bw_up_mean=np.mean(bw_up),
            bw_up_max=np.max(bw_up),
            bw_down_mean=np.mean(bw_down),
            bw_down_max=np.max(bw_down),
        )

        # 创建新的BodyObservations
        observations = []
        for i in range(len(delay_up)):
            obs = Observation(
                delay_up=delay_up[i],
                loss_up=loss_up[i],
                bw_up=bw_up[i],
                delay_down=delay_down[i],
                loss_down=loss_down[i],
                bw_down=bw_down[i]
            )
            observations.append(obs)
        body = BodyObservations(observations=observations)

        return body, ctx_values

    def _generate_psd_noise(self, original_data: np.ndarray, length: int) -> np.ndarray:
        """生成符合原PSD的高频噪声，保留Jitter

        参数:
            original_data: 原始数据
            length: 噪声长度

        返回:
            np.ndarray: 符合原PSD的高频噪声
        """
        # 使用FFT计算原始数据的PSD
        fft_vals = np.fft.fft(original_data)
        psd = np.abs(fft_vals) ** 2
        frequencies = np.fft.fftfreq(len(original_data))

        # 生成随机相位
        phase = np.random.rand(len(frequencies)) * 2 * np.pi

        # 生成符合原PSD的随机噪声
        noise_fft = np.sqrt(psd) * np.exp(1j * phase)
        noise = np.fft.ifft(noise_fft).real

        # 调整噪声长度
        if len(noise) < length:
            # 如果噪声长度不足，循环填充
            noise = np.tile(noise, length // len(noise) + 1)[:length]
        elif len(noise) > length:
            # 如果噪声长度过长，截断
            noise = noise[:length]

        # 归一化噪声，使其方差与原始数据的Jitter一致
        original_jitter = np.std(np.diff(original_data))
        noise_jitter = np.std(np.diff(noise))
        if noise_jitter > 0:
            noise = noise * (original_jitter / noise_jitter)

        return noise

    def _apply_psd_noise(self, profile: Pathlet) -> Pathlet:
        """应用PSD噪声到网络剖面，保留Jitter

        参数:
            profile: 原始网络剖面

        返回:
            Pathlet: 应用了PSD噪声的网络剖面
        """
        # 提取原始数据
        original_delay_up = np.array(profile.ctx_10s.delay_up)
        original_loss_up = np.array(profile.ctx_10s.loss_up)
        original_bw_up = np.array(profile.ctx_10s.bw_up)
        original_delay_down = np.array(profile.ctx_10s.delay_down)
        original_loss_down = np.array(profile.ctx_10s.loss_down)
        original_bw_down = np.array(profile.ctx_10s.bw_down)

        # 生成符合原PSD的高频噪声
        delay_noise_up = self._generate_psd_noise(original_delay_up, len(original_delay_up))
        loss_noise_up = self._generate_psd_noise(original_loss_up, len(original_loss_up))
        bw_noise_up = self._generate_psd_noise(original_bw_up, len(original_bw_up))
        delay_noise_down = self._generate_psd_noise(original_delay_down, len(original_delay_down))
        loss_noise_down = self._generate_psd_noise(original_loss_down, len(original_loss_down))
        bw_noise_down = self._generate_psd_noise(original_bw_down, len(original_bw_down))

        # 应用噪声，保留原始趋势
        new_delay_up = original_delay_up + delay_noise_up
        new_loss_up = original_loss_up + loss_noise_up
        new_bw_up = original_bw_up + bw_noise_up
        new_delay_down = original_delay_down + delay_noise_down
        new_loss_down = original_loss_down + loss_noise_down
        new_bw_down = original_bw_down + bw_noise_down

        # 确保参数在合理范围内
        new_loss_up = np.clip(new_loss_up, 0.0, 1.0)
        new_loss_down = np.clip(new_loss_down, 0.0, 1.0)
        new_bw_up = np.clip(new_bw_up, 0.0, None)
        new_bw_down = np.clip(new_bw_down, 0.0, None)

        # 更新ContextData
        new_ctx_10s = ContextData(
            delay_up=new_delay_up.tolist(),
            loss_up=new_loss_up.tolist(),
            bw_up=new_bw_up.tolist(),
            delay_down=new_delay_down.tolist(),
            loss_down=new_loss_down.tolist(),
            bw_down=new_bw_down.tolist(),
        )

        # 更新PathletStatistics
        new_ctx_values = PathletStatistics(
            delay_up_mean=np.mean(new_delay_up),
            delay_up_std=np.std(new_delay_up),
            delay_down_mean=np.mean(new_delay_down),
            delay_down_std=np.std(new_delay_down),
            loss_up_mean=np.mean(new_loss_up),
            loss_up_max=np.max(new_loss_up),
            loss_down_mean=np.mean(new_loss_down),
            loss_down_max=np.max(new_loss_down),
            bw_up_mean=np.mean(new_bw_up),
            bw_up_max=np.max(new_bw_up),
            bw_down_mean=np.mean(new_bw_down),
            bw_down_max=np.max(new_bw_down),
        )

        # 创建新的Pathlet
        new_profile = Pathlet(
            trace_name=profile.trace_name,
            start_index=profile.start_index,
            ctx_10s=new_ctx_10s,
            cont_1s=profile.cont_1s,
            ctx_values=new_ctx_values,
            is_valid=profile.is_valid,
        )

        return new_profile

    def _validate_profile(self, profile: Union[Dict, Pathlet]) -> None:
        """验证网络剖面参数

        参数:
            profile: 网络剖面（字典或Pathlet对象）

        异常:
            ValueError: 参数无效时抛出
        """
        # 简化验证，只检查基本结构
        if isinstance(profile, dict):
            # 处理字典类型的输入
            if profile.get("ctx_10s") is None or profile.get("cont_1s") is None:
                raise ValueError("网络剖面缺少必要数据")
            # 检查上下文数据长度
            if len(profile["ctx_10s"].delay_up) != 100:
                raise ValueError(f"上下文数据长度无效 {len(profile['ctx_10s'].delay_up)}")
            if len(profile["cont_1s"].delay_up) != 10:
                raise ValueError(f"延续数据长度无效: {len(profile['cont_1s'].delay_up)}")
        else:
            # 处理Pathlet对象类型的输入
            if profile.ctx_10s is None or profile.cont_1s is None:
                raise ValueError("网络剖面缺少必要数据")
            # 检查上下文数据长度
            if len(profile.ctx_10s.delay_up) != 100:
                raise ValueError(f"上下文数据长度无效 {len(profile.ctx_10s.delay_up)}")
            if len(profile.cont_1s.delay_up) != 10:
                raise ValueError(f"延续数据长度无效: {len(profile.cont_1s.delay_up)}")

    def blend_tails(
        self, profile1: Union[Dict, Pathlet], profile2: Union[Dict, Pathlet]
    ) -> Tuple[List[float], List[float], List[float], List[float], List[float], List[float]]:
        """融合两个网络剖面的尾部

        参数:
            profile1: 第一个网络剖面（字典或Pathlet对象）
            profile2: 第二个网络剖面（字典或Pathlet对象）

        返回:
            Tuple[List[float], List[float], List[float], List[float], List[float], List[float]]: 融合后的六维数据
        """
        # 从第一个剖面获取尾部数据
        tail1 = profile1["cont_1s"] if isinstance(profile1, dict) else profile1.cont_1s

        # 从第二个剖面获取头部数据
        head2 = profile2["ctx_10s"] if isinstance(profile2, dict) else profile2.ctx_10s

        # 执行Hermite插值
        delay_up_blended = self._hermite_interpolation(tail1.delay_up, head2.delay_up[: self.transition_steps])
        loss_up_blended = self._hermite_interpolation(tail1.loss_up, head2.loss_up[: self.transition_steps])
        bw_up_blended = self._hermite_interpolation(tail1.bw_up, head2.bw_up[: self.transition_steps])
        delay_down_blended = self._hermite_interpolation(tail1.delay_down, head2.delay_down[: self.transition_steps])
        loss_down_blended = self._hermite_interpolation(tail1.loss_down, head2.loss_down[: self.transition_steps])
        bw_down_blended = self._hermite_interpolation(tail1.bw_down, head2.bw_down[: self.transition_steps])

        return (
            delay_up_blended,
            loss_up_blended,
            bw_up_blended,
            delay_down_blended,
            loss_down_blended,
            bw_down_blended,
        )

    def _hermite_interpolation(self, tail_data: List[float], head_data: List[float]) -> List[float]:
        """执行Hermite插值

        参数:
            tail_data: 第一个剖面的尾部数据
            head_data: 第二个剖面的头部数据

        返回:
            List[float]: 插值后的数据
        """
        # 确保数据长度一致
        if len(tail_data) != len(head_data):
            logger.warning(f"数据长度不一致，tail_data: {len(tail_data)}, head_data: {len(head_data)}")
            min_len = min(len(tail_data), len(head_data))
            tail_data = tail_data[:min_len]
            head_data = head_data[:min_len]

        # 计算导数
        tail_deriv = self._calculate_derivative(tail_data)
        head_deriv = self._calculate_derivative(head_data)

        # 执行Hermite插值
        blended = []
        for i in range(len(tail_data)):
            t = i / len(tail_data)
            h00 = (1 + 2 * t) * (1 - t) ** 2
            h10 = t * (1 - t) ** 2
            h01 = t**2 * (3 - 2 * t)
            h11 = t**2 * (t - 1)
            blended_value = h00 * tail_data[i] + h10 * tail_deriv[i] + h01 * head_data[i] + h11 * head_deriv[i]
            blended.append(blended_value)

        return blended

    def _calculate_derivative(self, data: List[float]) -> List[float]:
        """计算数据的导数

        参数:
            data: 输入数据

        返回:
            List[float]: 导数数据
        """
        if len(data) < 2:
            return [0.0] * len(data)

        derivatives = []
        for i in range(len(data)):
            if i == 0:
                derivatives.append(data[1] - data[0])
            elif i == len(data) - 1:
                derivatives.append(data[-1] - data[-2])
            else:
                derivatives.append((data[i + 1] - data[i - 1]) / 2)

        return derivatives

    def validate_blend(
        self, blended_data: Tuple[List[float], List[float], List[float], List[float], List[float], List[float]]
    ) -> bool:
        """验证融合结果的有效性

        参数:
            blended_data: 融合后的六维数据

        返回:
            bool: 是否有效
        """
        for data in blended_data:
            for value in data:
                if not isinstance(value, (int, float)) or np.isnan(value) or np.isinf(value):
                    logger.warning(f"融合结果包含无效值: {value}")
                    return False

        return True

    def _generate_transition_profiles(
        self, start_profile: Union[Dict, Pathlet], end_profile: Union[Dict, Pathlet]
    ) -> List[Union[Dict, Pathlet]]:
        """生成过渡网络剖面

        参数:
            start_profile: 起始网络剖面（字典或Pathlet对象）
            end_profile: 结束网络剖面（字典或Pathlet对象）

        返回:
            List[Union[Dict, Pathlet]]: 过渡网络剖面列表
        """
        transition_profiles = []

        # 获取起始和结束剖面的数据
        if isinstance(start_profile, dict):
            start_ctx_10s = start_profile.get("ctx_10s")
            start_trace_name = start_profile.get("trace_name", "unknown")
            start_index = start_profile.get("start_index", 0)
        else:
            start_ctx_10s = start_profile.ctx_10s
            start_trace_name = getattr(start_profile, "trace_name", "unknown")
            start_index = getattr(start_profile, "start_index", 0)

        if isinstance(end_profile, dict):
            end_ctx_10s = end_profile.get("ctx_10s")
            end_trace_name = end_profile.get("trace_name", "unknown")
        else:
            end_ctx_10s = end_profile.ctx_10s
            end_trace_name = getattr(end_profile, "trace_name", "unknown")

        # 使用平均延迟作为代表值进行插值
        start_rtt = sum(start_ctx_10s.delay_up) / len(start_ctx_10s.delay_up)
        end_rtt = sum(end_ctx_10s.delay_up) / len(end_ctx_10s.delay_up)
        start_loss = sum(start_ctx_10s.loss_up) / len(start_ctx_10s.loss_up)
        end_loss = sum(end_ctx_10s.loss_up) / len(end_ctx_10s.loss_up)
        start_bw = sum(start_ctx_10s.bw_up) / len(start_ctx_10s.bw_up)
        end_bw = sum(end_ctx_10s.bw_up) / len(end_ctx_10s.bw_up)

        for step in range(1, self.transition_steps + 1):
            # 线性插值各参数
            rtt = self._linear_interpolate(start_rtt, end_rtt, step)
            loss_rate = self._linear_interpolate(start_loss, end_loss, step)
            bandwidth = self._linear_interpolate(start_bw, end_bw, step)

            # 创建过渡剖面
            transition_profile = {
                "trace_name": f"transition_{start_trace_name}_to_{end_trace_name}",
                "start_index": start_index + step,
                "ctx_10s": ContextData(
                    delay_up=[rtt] * 100,
                    loss_up=[loss_rate] * 100,
                    bw_up=[bandwidth] * 100,
                    delay_down=[rtt] * 100,
                    loss_down=[loss_rate] * 100,
                    bw_down=[bandwidth] * 100,
                ),
                "cont_1s": ContinuationData(
                    delay_up=[rtt] * 10,
                    loss_up=[loss_rate] * 10,
                    bw_up=[bandwidth] * 10,
                    delay_down=[rtt] * 10,
                    loss_down=[loss_rate] * 10,
                    bw_down=[bandwidth] * 10,
                ),
                "ctx_values": PathletStatistics(
                    delay_up_mean=rtt,
                    delay_up_std=0.0,
                    delay_down_mean=rtt,
                    delay_down_std=0.0,
                    loss_up_mean=loss_rate,
                    loss_up_max=loss_rate,
                    loss_down_mean=loss_rate,
                    loss_down_max=loss_rate,
                    bw_up_mean=bandwidth,
                    bw_up_max=bandwidth,
                    bw_down_mean=bandwidth,
                    bw_down_max=bandwidth,
                ),
            }

            # 验证剖面
            self._validate_profile(transition_profile)

            transition_profiles.append(transition_profile)

        return transition_profiles

    def splice(
        self, profile_list1: List[Union[Dict, Pathlet]], profile_list2: List[Union[Dict, Pathlet]]
    ) -> List[Union[Dict, Pathlet]]:
        """拼接两个网络剖面序列，实现动态对齐和Hermite插值

        示例:
            spliced_seq = splicer.splice(seq1, seq2)

        参数:
            profile_list1: 第一个网络剖面序列（字典或Pathlet对象列表）
            profile_list2: 第二个网络剖面序列（字典或Pathlet对象列表）

        返回:
            List[Union[Dict, Pathlet]]: 拼接后的网络剖面序列
        """
        if not profile_list1 or not profile_list2:
            raise ValueError("输入的网络剖面序列不能为空")

        # 验证所有剖面
        for profile in profile_list1 + profile_list2:
            self._validate_profile(profile)

        # 实现拼接容错：最多重试3次
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                # 生成过渡段
                profile_a = profile_list1[-1]
                profile_b = profile_list2[0]
                # 使用内部方法生成过渡段
                transition_profiles = self._generate_transition_profiles(profile_a, profile_b)
                logger.info(f"生成 {len(transition_profiles)} 个过渡段剖面")

                # 构建最终拼接结果
                spliced_profiles = []

                # 添加第一个序列的所有剖面
                spliced_profiles.extend(profile_list1)

                # 添加过渡段
                spliced_profiles.extend(transition_profiles)

                # 添加第二个序列的所有剖面
                spliced_profiles.extend(profile_list2)

                logger.info("成功拼接两个网络剖面序列")
                return spliced_profiles
            except Exception as e:
                retry_count += 1
                logger.warning(f"拼接失败，重试第 {retry_count} 次：{e}")

        # 如果所有重试都失败，抛出异常
        raise SplicingError(f"拼接失败，已重试 {max_retries} 次")

    def splice_sequences(self, sequences: List[List[Pathlet]]) -> List[Pathlet]:
        """拼接多个网络剖面序列

        示例:
            from traceloom.weaving.reweave.reweaver import Reweaver
            from training.common.profile import Pathlet, ContextData, ContinuationData
            from datetime import datetime

            # 准备三个网络剖面序列
            seq1 = [
                Pathlet(
                    profile_id=f"p1_{i}",
                    timestamp=datetime.now() + timedelta(seconds=i),
                    context_data=ContextData(
                        delay_up=[100.0]*100, loss_up=[0.01]*100, bw_up=[10.0]*100,
                        delay_down=[100.0]*100, loss_down=[0.01]*100, bw_down=[10.0]*100
                    ),
                    continuation_data=ContinuationData(
                        delay_up=[100.0]*10, loss_up=[0.01]*10, bw_up=[10.0]*10,
                        delay_down=[100.0]*10, loss_down=[0.01]*10, bw_down=[10.0]*10
                    )
                )
                for i in range(10)
            ]

            seq2 = [
                Pathlet(
                    profile_id=f"p2_{i}",
                    timestamp=datetime.now() + timedelta(seconds=10+i),
                    context_data=ContextData(
                        delay_up=[200.0]*100, loss_up=[0.05]*100, bw_up=[5.0]*100,
                        delay_down=[200.0]*100, loss_down=[0.05]*100, bw_down=[5.0]*100
                    ),
                    continuation_data=ContinuationData(
                        delay_up=[200.0]*10, loss_up=[0.05]*10, bw_up=[5.0]*10,
                        delay_down=[200.0]*10, loss_down=[0.05]*10, bw_down=[5.0]*10
                    )
                )
                for i in range(10)
            ]

            seq3 = [
                Pathlet(
                    profile_id=f"p3_{i}",
                    timestamp=datetime.now() + timedelta(seconds=20+i),
                    context_data=ContextData(
                        delay_up=[50.0]*100, loss_up=[0.001]*100, bw_up=[20.0]*100,
                        delay_down=[50.0]*100, loss_down=[0.001]*100, bw_down=[20.0]*100
                    ),
                    continuation_data=ContinuationData(
                        delay_up=[50.0]*10, loss_up=[0.001]*10, bw_up=[20.0]*10,
                        delay_down=[50.0]*10, loss_down=[0.001]*10, bw_down=[20.0]*10
                    )
                )
                for i in range(10)
            ]

            splicer = NetworkSplicer()
            spliced_seq = splicer.splice_sequences([seq1, seq2, seq3])

            splicer = NetworkSplicer()
            sequences = [seq1, seq2, seq3]
            spliced_seq = splicer.splice_sequences(sequences)

        参数:
            sequences: 网络剖面序列列表

        返回:
            List[Pathlet]: 拼接后的网络剖面序列
        """
        if not sequences:
            raise ValueError("输入的网络剖面序列列表不能为空")

        if len(sequences) == 1:
            return sequences[0].copy()

        # 初始化拼接结果为第一个序列
        spliced_result = sequences[0].copy()

        # 依次拼接后续序列
        for i in range(1, len(sequences)):
            spliced_result = self.splice(spliced_result, sequences[i])

        return spliced_result

    def splice_profile_sequences(self, sequences: List[ProfileSequence]) -> ProfileSequence:
        """拼接多个 ProfileSequence 对象

        示例:
            from traceloom.weaving.reweave.reweaver import Reweaver

            reweaver = Reweaver()
            sequences = [seq1, seq2, seq3]  # 都是 ProfileSequence 对象
            reweaved_seq = reweaver.splice_profile_sequences(sequences)

        参数:
            sequences: ProfileSequence 对象列表

        返回:
            ProfileSequence: 拼接后的 ProfileSequence 对象
        """
        if not sequences:
            raise ValueError("输入的 ProfileSequence 列表不能为空")

        # 提取所有网络剖面
        all_profiles = []
        for seq in sequences:
            all_profiles.extend(seq.profiles)

        # 拼接剖面
        spliced_profiles = self.splice_sequences([seq.profiles for seq in sequences])

        # 创建新的 ProfileSequence
        return ProfileSequence(
            sequence_id=f"spliced_{'_'.join(seq.sequence_id for seq in sequences)}",
            profiles=spliced_profiles,
            metadata={
                "spliced_sequences": [seq.sequence_id for seq in sequences],
                "transition_duration": self.transition_duration,
                "transition_steps": self.transition_steps,
            },
        )

    def generate_trace(self, pathlet_sequence: List[Pathlet], pathlet_storage: any) -> List[List[float]]:
        """生成合成轨迹

        根据径元序列生成6列HoloWAN格式的合成轨迹数据

        示例:
            from traceloom.weaving.reweave.reweaver import Reweaver
            from traceloom.io.pathlet_storage import PathletStorage

            pathlet_storage = PathletStorage()
            pathlet_sequence = [Pathlet(...), Pathlet(...)]
            reweaver = Reweaver()
            trace_data = reweaver.generate_trace(pathlet_sequence, pathlet_storage)

        参数:
            pathlet_sequence: 径元序列
            pathlet_storage: 径元存储实例

        返回:
            合成轨迹数据（6列）
        """
        if not pathlet_sequence:
            raise ValueError("输入的径元序列不能为空")

        logger.info(f"开始生成合成轨迹，共包含{len(pathlet_sequence)} 个径元")

        # 从径元存储中获取每个径元的详细数据
        all_profiles = self._get_profiles_from_storage(pathlet_sequence, pathlet_storage)

        if not all_profiles:
            # 如果无法获取任何径元数据，直接退出
            logger.error("无法获取任何径元的详细数据，无法生成合成轨迹")
            raise ValueError("无法获取任何径元的详细数据，无法生成合成轨迹")

        # 使用现有的拼接功能生成合成轨迹
        if len(all_profiles) == 1:
            trace_data = self._generate_trace_from_single_profile(all_profiles[0])
        else:
            # 拼接多个径元
            spliced_profiles = self._splice_multiple_profiles(all_profiles)
            trace_data = self._generate_trace_from_profiles(spliced_profiles)

        logger.info(f"成功生成合成轨迹，共包含 {len(trace_data)} 个采样点")
        return trace_data

    def _get_profiles_from_storage(self, pathlet_sequence: List[Pathlet], pathlet_storage: any) -> List:
        """从径元存储中获取每个径元的详细数据"""
        all_profiles = []
        for pathlet_info in pathlet_sequence:
            profile = pathlet_storage.get_raw_profile(pathlet_info.pathlet_id)
            if profile:
                all_profiles.append(profile)
            else:
                logger.warning(f"未找到径元{pathlet_info.pathlet_id} 的数据，跳过")
        return all_profiles

    def _generate_default_trace(self, pathlet_sequence: List[Pathlet]) -> List[List[float]]:
        """生成默认的合成轨迹数据"""
        logger.warning("无法获取任何径元的详细数据，生成默认合成轨迹")
        default_trace = []
        for pathlet_info in pathlet_sequence:
            # 为每个径元生成100个采样点
            for _i in range(100):
                # 默认值：[时间戳, 延迟, 抖动, 丢包率, 带宽, 其他]
                # 时间戳从0开始，每100ms一个点
                # 延迟根据状态ID设置不同的值
                base_delay = pathlet_info.state_id * 100  # 每个状态增加100ms延迟
                timestamp = len(default_trace) * 0.1
                delay = base_delay + 50  # 基础延迟 + 50ms
                jitter = 10  # 固定抖动10ms
                loss_rate = 0.01  # 固定丢包率1%
                bandwidth = 1000  # 固定带宽1000Mbps
                other = 0.0  # 其他值
                default_trace.append([timestamp, delay, jitter, loss_rate, bandwidth, other])
        return default_trace

    def _generate_trace_from_single_profile(self, profile: Union[Dict, Pathlet]) -> List[List[float]]:
        """从单个径元生成轨迹数据"""
        trace_data = []
        # 获取上下文数据
        ctx_10s = profile.get("ctx_10s") if isinstance(profile, dict) else profile.ctx_10s

        for i in range(100):
            trace_data.append(
                [
                    ctx_10s.delay_up[i],
                    ctx_10s.loss_up[i],
                    ctx_10s.bw_up[i],
                    ctx_10s.delay_down[i],
                    ctx_10s.loss_down[i],
                    ctx_10s.bw_down[i],
                ]
            )
        return trace_data

    def _splice_multiple_profiles(self, all_profiles: List) -> List:
        """拼接多个径元"""
        if len(all_profiles) == 1:
            return all_profiles

        # 去重，避免重复拼接相同的径元
        unique_profiles = []
        seen_profile_ids = set()
        for profile in all_profiles:
            # 使用trace_name作为唯一标识
            profile_id = (
                profile.get("trace_name")
                if isinstance(profile, dict)
                else getattr(profile, "trace_name", str(id(profile)))
            )
            if profile_id not in seen_profile_ids:
                seen_profile_ids.add(profile_id)
                unique_profiles.append(profile)

        if len(unique_profiles) == 1:
            return unique_profiles

        # 初始化拼接结果为第一个径元
        spliced_profiles = [unique_profiles[0]]

        # 依次拼接后续径元
        for i in range(1, len(unique_profiles)):
            # 只拼接当前径元和前一个径元，不包括之前的过渡段
            profile_a = spliced_profiles[-1]
            profile_b = unique_profiles[i]
            # 生成过渡段
            transition_profiles = self._generate_transition_profiles(profile_a, profile_b)
            # 添加过渡段
            spliced_profiles.extend(transition_profiles)
            # 添加当前径元
            spliced_profiles.append(profile_b)

        return spliced_profiles

    def _generate_trace_from_profiles(self, profiles: List[Union[Dict, Pathlet]]) -> List[List[float]]:
        """从多个径元生成轨迹数据"""
        trace_data = []
        for profile in profiles:
            # 获取上下文数据
            ctx_10s = profile.get("ctx_10s") if isinstance(profile, dict) else profile.ctx_10s

            for i in range(100):
                trace_data.append(
                    [
                        ctx_10s.delay_up[i],
                        ctx_10s.loss_up[i],
                        ctx_10s.bw_up[i],
                        ctx_10s.delay_down[i],
                        ctx_10s.loss_down[i],
                        ctx_10s.bw_down[i],
                    ]
                )
        return trace_data
