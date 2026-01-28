### 🧵 TraceLoom（织径）引擎架构规范（V2.2）  
> **以【径元】为丝，以【织律】为梭，织就可编程之径**  
> **核心思想**：将真实网络轨迹解构为状态驱动的【径元】序列，通过三大织造模式（重织 / 绣织 / 广织），实现从回放 → 编辑 → 创生的全谱系虚拟链路合成。

---

## 一、核心术语统一

| 中文 | 英文 | 说明 |
|------|------|------|
| 【观元】 | `Observation` | **瞬时快照**：单点 `(rtt, loss, bw)`，感知网络之原子 |
| 【主干】 | `Body` | **状态主体**：【径元】前 10 秒（100 个【观元】），代表典型行为 |
| 【融尾】 | `Tail Blend` | **融合尾段**：【径元】后 1 秒（10 个【观元】），用于拼接平滑过渡 |
| 【径元】 | `Pathlet` | **11秒丝线**：10秒【主干】 + 1秒【融尾】，编织之基本单元 |
| 【织律】 | `WeavingLaw` | GMM模型，定义网络状态语义（如 `s0`, `s2`） |
| 【织样】 | `Pattern` | 编排指令，如 `"s0x2 -> s2x3"`，指导编织的图样 |
| 【织机】 | `Weaver` | 生成模型，未来生成全新合理路径，受【织律】约束 |

> **【观元】看世界，【径元】造世界**  
> **【织律】识万象，【织机】生万径**  
> **十秒主干立其形，一秒融尾续其脉**

---

## 二、关键模块命名与职责

| 模块中文名 | 模块英文名 | 职责 |
|-----------|-----------|------|
| **观元采集器** | `Observer` | 从 HoloWAN 原始文件解析出 6 列观测，存为【观元】 |
| **径元构造器** | `Pathletizer` | 将连续【观元】按 110 行（11 秒）切片，构建【径元】（含主干+融尾） |
| **织律引擎** | `WeavingLaw Engine` | 加载 GMM 模型，提供 `predict_state()` 和 `state_name_to_id()` 接口 |
| **织样解析器** | `PatternParser` | 统一处理三种输入（文件/字符串/JSON），输出标准化 `Pattern` 对象 |
| **全局采样器** | `GlobalSampler` | 根据 `(state_id, duration)` 从全局库采样【径元】ID 序列 |
| **融尾拼接器** | `TailBlender` | 执行【径元】间 1 秒动态对齐 + Hermite 插值，保障六维连续 |
| **重织引擎** | `Reweaver` | 调度真实【径元】重组，实现高保真回放 |
| **绣织引擎** | `Stitcher` | 在轨迹中精准缝入受控【质径】，支持因果实验 |
| **广织引擎** | `Dreamer` | 基于生成模型合成符合【织律】的【幻径】 |
| **织径总控** | `WeavingEngine` | 统一调度 `Reweaver`/`Stitcher`/`Dreamer`，完成主流程 |
| **HoloWAN 适配器** | `HoloWANAdapter` | 负责输入解析与输出格式化（header + 6 列数据） |

> 🔹 所有模式共用底层：`pathlets.parquet` + `observations.parquet` + `WeavingLaw`  
> 🔹 所有模式共用拼接引擎：**融尾拼接器**（动态对齐 + Hermite 插值 + 频谱保真）

---

## 三、数据结构

### 3.1 径元元数据表：`pathlets.parquet`
| 字段 | 类型 | 说明 |
|------|------|------|
| `pathlet_id` | `int64` | 全局唯一 ID |
| `state_id` | `int32` | 对应【织律】中的状态 |
| `source_file` | `string` | 来自 `raw/weak/*.txt` |
| `start_index` | `int64` | 原始文件起始行（指向【主干】首行） |
| `has_tail` | `bool` | 是否包含有效【融尾】（默认 true） |

### 3.2 观测点表：`observations.parquet`
| 字段 | 类型 | 说明 |
|------|------|------|
| `pathlet_id` | `int64` | 外键 |
| `sample_index` | `int32` | `0–109`（`0–99` = 【主干】，`100–109` = 【融尾】） |
| `rtt1, loss1, bw1, rtt2, loss2, bw2` | `float32` | 6 维网络指标（不分上下行） |

> ✅ 文件位置：`data/pathlets/default/`

---

## 四、三大织造模式

| 模式 | 引擎 | 核心逻辑 |
|------|------|--------|
| **重织（Reweave）** | `Reweaver` | 拼接算法：**融尾拼接器**执行导数对齐 + 频谱补纹 |
| **绣织（Stitch）** | `Stitcher` | 插值算法：在【主干】基础上拉伸，末端生成新【融尾】 |
| **广织（Dream）** | `Dreamer` | 生成模型输出完整【径元】（含合成【主干】与【融尾】） |

> **重织以复现 · 绣织以控因 · 广织以探界**

---

## 五、智能输入处理
所有模式仅需一个 `input` 参数，系统自动识别类型：

```python
def parse_pattern(input) -> Pattern:
    if isinstance(input, Pattern):
        return input  # 直接返回 Pattern 对象
    elif is_holowan_file(input):
        return extract_pattern_from_trace(input)  # → 重织
    elif is_string_like(input) and ".txt" in input:
        return extract_pattern_from_trace(input)  # → 重织
    elif is_string_like(input) and "->" in input:
        return Pattern.from_string(input)         # → 绣织/广织
    elif is_string_like(input):
        return Pattern.from_string(input)         # → 绣织/广织
```

**输出**：统一为 `Pattern(sequence: List[(state_id, duration_sec)])`

**判断优先级**：对象 > 文件路径 > 织样字符串。若歧义，优先视为文件。

**示例**：
```python
traceloom.reweave("real.txt")          # 文件 → 重织
Traceloom.dream("s0x2 -> s2x6")       # 织样 → 广织
Traceloom.stitch(my_pattern_obj)    # 对象 → 绣织
```

---

## 六、织径引擎 = 模块协同

```python
def weave(pattern: Pattern, mode: str, output_file: str):
    # 1. 织样解析器 → Pattern
    pattern = PatternParser.parse(input)
    
    # 2. 织律引擎 → state_id 映射
    state_seq = [WeavingLaw.state_name_to_id(s) for s in pattern.states]
    
    # 3. 调度对应引擎
    if mode == "reweave":
        trace_6d = Reweaver.weave(pattern)
    elif mode == "stitch":
        trace_6d = Stitcher.stitch(pattern)
    elif mode == "dream":
        trace_6d = Dreamer.dream(pattern)
    
    # 4. HoloWAN 适配器 → 写入文件
    HoloWANAdapter.write(trace_6d, output_file, pattern)
```

---

## 七、部署与数据流

### 7.1 目录结构
```
TraceLoom/
│
├── src/
│   └── traceloom/                     # 核心推理包（纯运行时，无训练依赖）
│       ├── core/                      # 🧰 通用基础设施
│       │   ├── __init__.py
│       │   ├── config.py              # 配置加载（读取 configs/）
│       │   └── utils.py               # 通用工具函数
│       │
│       ├── io/                        # 💾 输入输出适配
│       │   ├── __init__.py
│       │   ├── holowan_adapter.py     # HoloWAN 格式转换（str ↔ ndarray）
│       │   └── observer.py            # 观元采集器（解析原始文件）
│       │
│       ├── weaving/                   # ⚙️ 织径业务核心（原 simcore/）
│       │   ├── __init__.py
│       │   ├── engines/               # 三大织造引擎
│       │   │   ├── __init__.py
│       │   │   ├── weaving_engine.py  # WeavingEngine（总控）
│       │   │   ├── reweaver.py        # Reweaver（重织引擎）
│       │   │   ├── stitcher.py        # Stitcher（绣织引擎）
│       │   │   └── dreamer.py         # Dreamer（广织引擎）
│       │   │
│       │   ├── sampler/               # 采样逻辑
│       │   │   ├── __init__.py
│       │   │   └── global_sampler.py  # GlobalSampler（从 Parquet 采样）
│       │   │
│       │   ├── reweave/               # 重织专用模块
│       │   │   ├── __init__.py
│       │   │   └── tail_blender.py    # TailBlender（融尾拼接器）
│       │   │
│       │   ├── pattern.py             # Pattern 数据结构
│       │   ├── pattern_parser.py      # PatternParser（输入解析）
│       │   └── weaving_law.py         # WeavingLawEngine（加载 .pkl 模型）
│       │
│       └── weaver.py                  # 🪡 统一入口：reweave/stitch/dream
│
│
├── training/                          # 🏗️ 模型训练与预处理（不在 pip 包中）
│   ├── common/                        # 通用训练工具
│   │   ├── __init__.py
│   │   ├── pathlet_builder.py         # 【径元】构建核心（切片 + 存 Parquet）
│   │   ├── dataset.py                 # 训练数据集加载
│   │   └── metrics.py                 # 评估指标
│   │
│   ├── weaving_law/                   # 织律训练（GMM）
│   │   ├── __init__.py
│   │   └── train_gmm.py
│   │
│   └── weaver_model/                  # 织机训练（生成模型）
│       ├── __init__.py
│       └── train_diffusion.py
│
│
├── scripts/                           # 🛠️ 辅助脚本
│   ├── __init__.py
│   ├── build_pathlets.py              # 构建径元库入口（调用 pathlet_builder）
│   └── validate_install.py            # 安装后验证脚本
│
│
├── data/                              # 🗃️ 共享数据目录
│   ├── raw/                           # 原始 HoloWAN 文件（.txt）
│   ├── pathlets/                      # 【径元】知识库（预处理输出）
│   │   └── default/
│   │       ├── pathlets.parquet       # 径元元数据（含 state_id, source_file）
│   │       └── observations.parquet   # 观元数据（sample_index: 0-99=主干, 100-109=融尾）
│   │
│   └── models/                        # 模型产物
│       └── default/
│           ├── weaving_law.pkl        # 【织律】（GMM）
│           └── weaver_model.pth       # 【织机】（生成模型）
│
│
├── configs/                           # ⚙️ 配置模板
│   └── default.yaml                   # 默认配置（data_dir, model_dir, log_level...）
│
│
├── tests/                             # 🧪 单元测试
│   ├── __init__.py
│   ├── test_weaver.py
│   ├── test_holowan_adapter.py
│   └── ...
│
│
├── docs/                              # 📚 文档
│   └── ...
│
├── .gitignore
├── pyproject.toml                     # 核心包依赖（torch/tensorflow 在 dev 环境）
├── README.md                          # 项目说明（含四言口诀、三重织径）
└── LICENSE
```

### 7.2 数据流（更新）
```
[raw/weak/*.txt]
     ↓
【观元采集器】→ (N,6) 观元流
     ↓
【径元构造器】→ 切分为 110 行片段（100 主干 + 10 融尾）
     ↓
[pathlets.parquet + observations.parquet] ← 存于 data/pathlets/default/
[weaving_law.pkl] ← 存于 data/models/default/
     ↓
Web API / CLI → 【织样解析器】→ 【织径总控】→ 调度 Reweaver/Stitcher/Dreamer → data/outputs/*.txt
```

---

> 🧵 **设计哲学**：  
> **观元为始，径元为用；主干载态，融尾无痕**。  
> TraceLoom 不模拟网络——它**织一条 App 信以为真的路**。