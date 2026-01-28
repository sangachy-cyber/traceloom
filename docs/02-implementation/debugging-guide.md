# 调试指南

## 概述

本指南旨在帮助开发者和用户解决在使用织虚过程中遇到的常见问题。我们将介绍调试工具、技术和常见问题的解决方案，特别是关于拼接不平滑、状态跳变等典型问题。

## 调试工具与技术

### 1. 日志系统

织虚使用loguru进行日志记录，默认日志级别为INFO。可以通过以下方式调整日志级别：

```python
from traceloom.core import settings
settings.set_config("LOG_LEVEL", "DEBUG")
```

或者通过环境变量：

```bash
export LOG_LEVEL=DEBUG
```

### 2. 可视化工具

- **Matplotlib/Seaborn**：用于绘制网络轨迹图
- **TensorBoard**：用于可视化模型训练过程
- **HoloWAN GUI**：用于预览和验证生成的链路

### 3. 验证工具

```bash
# 验证回放文件
python scripts/validate_playback.py --file data/playback/trace.trace

# 验证生成的链路
python scripts/validate_link.py --file output/link.hwan
```

## 常见问题与解决方案

### 1. 拼接不平滑

#### 问题描述

在【替】或【造】阶段，生成的网络轨迹在拼接处出现明显的不连续性。

#### 可能原因

- 拼接算法参数设置不当
- 平滑策略选择不合适
- 状态间差异过大
- 时间对齐问题

#### 解决方案

1. **调整平滑参数**：
   ```python
   # 增加平滑窗口大小
   link = TraceLoom.craft(
       base="trace.trace",
       target_states=["S0", "S1"],
       smooth_window=2.0  # 调整为2秒
   )
   ```

2. **尝试不同的平滑策略**：
   ```python
   # 使用余弦插值替代线性插值
   link = TraceLoom.craft(
       base="trace.trace",
       target_states=["S0", "S1"],
       smooth_strategy="cosine"  # 可选：linear, cosine, exponential
   )
   ```

3. **增加过渡区域长度**：
   ```python
   # 增加过渡区域长度
   link = TraceLoom.craft(
       base="trace.trace",
       target_states=["S0", "S1"],
       transition_length=2.0  # 调整为2秒
   )
   ```

4. **检查状态间差异**：
   ```python
   # 检查状态S0和S1的差异
   from traceloom.model import GMMModel
   model = GMMModel.load("models/gmm_model.pkl")
   state_s0 = model.get_state("S0")
   state_s1 = model.get_state("S1")
   print(f"S0: {state_s0}")
   print(f"S1: {state_s1}")
   ```

### 2. 状态跳变

#### 问题描述

生成的网络轨迹中出现突兀的状态跳变，不符合预期的状态序列。

#### 可能原因

- 状态标签不准确
- 模型训练不足
- 状态转换矩阵不合理
- 参数设置不当

#### 解决方案

1. **重新训练GMM模型**：
   ```python
   from traceloom.model import GMMModel
   
   model = GMMModel(n_components=5)
   model.fit(data)
   model.save("models/gmm_model.pkl")
   ```

2. **调整状态数量**：
   ```python
   # 增加或减少状态数量
   model = GMMModel(n_components=3)  # 调整为3个状态
   model.fit(data)
   ```

3. **检查状态转换矩阵**：
   ```python
   # 查看状态转换矩阵
   transition_matrix = model.get_transition_matrix()
   print(transition_matrix)
   ```

4. **使用条件采样**：
   ```python
   # 使用条件采样确保状态序列符合预期
   link = TraceLoom.craft(
       base="trace.trace",
       target_states=["S0", "S1"],
       enforce_state_sequence=True  # 强制遵循状态序列
   )
   ```

### 3. 参数范围超出限制

#### 问题描述

生成的轨迹中出现超出合理范围的参数值（如时延>2000ms）。

#### 可能原因

- 模型训练数据包含异常值
- 采样参数设置不当
- 约束条件未生效

#### 解决方案

1. **调整模型训练数据**：
   ```python
   # 过滤训练数据中的异常值
   from traceloom.data import DataPreprocessor
   
   preprocessor = DataPreprocessor()
   filtered_data = preprocessor.filter_outliers(data)
   model.fit(filtered_data)
   ```

2. **调整采样温度**：
   ```python
   # 降低采样温度，减少极端值
   link = TraceLoom.craft(
       base="trace.trace",
       target_states=["S0", "S1"],
       sampling_temperature=0.5  # 降低温度
   )
   ```

3. **启用严格约束**：
   ```python
   # 启用严格的参数范围约束
   link = TraceLoom.craft(
       base="trace.trace",
       target_states=["S0", "S1"],
       strict_constraints=True  # 启用严格约束
   )
   ```

### 4. 模型加载失败

#### 问题描述

无法加载预训练模型。

#### 可能原因

- 模型文件损坏
- 模型版本不兼容
- 依赖库版本不匹配

#### 解决方案

1. **检查模型文件**：
   ```bash
   # 检查模型文件是否存在且完整
   ls -la models/model.pkl
   file models/model.pkl
   ```

2. **重新训练模型**：
   ```python
   # 重新训练模型
   model = GMMModel()
   model.fit(data)
   model.save("models/new_model.pkl")
   ```

3. **检查依赖版本**：
   ```bash
   # 检查依赖库版本
   pip list | grep -E "numpy|scikit-learn|torch"
   ```

### 5. 导出失败

#### 问题描述

无法将生成的链路导出为.hwan格式。

#### 可能原因

- 输出目录不存在
- 权限问题
- 数据格式错误

#### 解决方案

1. **检查输出目录**：
   ```python
   from traceloom.core import settings
   print(f"输出目录: {settings.OUTPUT_DIR}")
   print(f"目录存在: {settings.OUTPUT_DIR.exists()}")
   ```

2. **创建输出目录**：
   ```python
   # 确保输出目录存在
   settings.OUTPUT_DIR.mkdir(exist_ok=True)
   ```

3. **检查数据格式**：
   ```python
   # 验证链路数据
   result = TraceLoom.validate(link)
   print(f"验证结果: {result}")
   ```

## 调试流程

### 1. 复现问题

```python
# 编写最小复现脚本
from traceloom import TraceLoom

# 简化的参数设置
link = TraceLoom.craft(
    base="simple_trace.trace",
    target_states=["S0", "S1"]
)
link.export("holowan")
```

### 2. 收集信息

- 查看日志文件
- 绘制生成的轨迹图
- 检查中间结果

```python
# 绘制轨迹图
link.plot(output_path="debug/trace.png")

# 查看轨迹数据
print(link.data.head())
```

### 3. 定位问题

- 检查特定阶段（【替】/【造】/【拓】）
- 逐步调试，分离问题
- 使用二分法定位问题代码

### 4. 修复问题

- 应用解决方案
- 验证修复效果
- 编写测试用例

## 最佳实践

1. **从简单开始**：先使用简单的配置和数据，逐步增加复杂度
2. **记录实验**：记录每次实验的参数和结果
3. **版本控制**：使用Git跟踪代码和模型的变化
4. **单元测试**：为核心功能编写单元测试
5. **集成测试**：测试端到端的工作流程
6. **文档化**：记录问题和解决方案

## 高级调试技巧

### 1. 断点调试

使用IDE的断点调试功能，逐步执行代码，查看变量值和执行流程。

### 2. 性能分析

```bash
# 使用cProfile分析性能
python -m cProfile -o profile.prof scripts/example.py

# 使用snakeviz可视化性能分析结果
snakeviz profile.prof
```

### 3. 模型解释

```python
# 解释GMM模型
from sklearn.inspection import permutation_importance

result = permutation_importance(model, X, y, n_repeats=10, random_state=42)
print(result.importances_mean)
```

## 总结

调试是使用和开发织虚过程中不可或缺的一部分。通过本指南中介绍的工具、技术和解决方案，您应该能够有效地解决在使用织虚过程中遇到的常见问题。如果您遇到了无法解决的问题，请查看项目的GitHub Issues或提交新的Issue。