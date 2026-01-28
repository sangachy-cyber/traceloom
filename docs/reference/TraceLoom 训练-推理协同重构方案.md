# 🧵 TraceLoom 训练-推理协同重构方案（最终版 · 开发指南）

> **目标**：  
> - ✅ 推理包纯净（`src/traceloom/` 不依赖 `training/`）  
> - ✅ 训练灵活（`training/` 可自由使用 ML 库）  
> - ✅ 共用语义统一（通过 `common/` 强约束）  
> - ✅ 术语精准（训练用功能名，推理用引擎名）

---

## 一、目录结构（必须严格遵守）

```bash
TraceLoom/
│
├── src/
│   └── traceloom/                     # ← 推理核心（将打包进 PyPI）
│       ├── common/                    # ← 共用数据结构与工具（训练+推理共享）
│       │   ├── __init__.py            # 导出所有共用类
│       │   ├── pathlet.py             # Observation, BodyObservations, TailObservations, Pathlet
│       │   ├── features.py            # FeatureExtractor
│       │   └── state.py               # StateLabel, StateNamer（仅加载映射表）
│       │
│       ├── core/
│       │   └── config.py              # OBSERVATION_FIELDS = ("delay_up", "loss_up", ...)
│       │
│       ├── io/
│       │   ├── adapters/
│       │   │   └── holowan_adapter.py # HoloWAN → Observation
│       │   └── observer.py            # Observer.parse_file()
│       │
│       └── weaving/
│           └── engines/
│               ├── Reweaver.py        # 拼接真实径元
│               ├── Stitcher.py        # 缝入受控质径
│               └── Dreamer.py         # 生成幻径
│
├── training/                          # ← 纯训练代码（不进 PyPI，用户本地运行）
│   ├── pathlet/
│   │   ├── PathletBuilder.py          # 构建【径元】（主干100 + 融尾10）
│   │   └── WeavingLawTrainer.py       # 训练【织律】（GMM + 状态命名）
│   │
│   ├── profile/
│   │   └── RawProfile.py              # 加载原始轨迹 → List[Observation]
│   │
│   ├── synthesis/                     # ← 网络参数合成（生成模型训练）
│   │   ├── NetworkDiffusionModel.py   # 扩散模型（含训练逻辑）
│   │   └── NetworkSamplerTrainer.py   # 采样策略训练
│   │
│   ├── embroider/                     # ← 精细插值技术（训练侧）
│   │   ├── NetworkInterpolator.py     # 网络参数插值
│   │   └── PSDConstraint.py           # 功率谱密度约束
│   │
│   └── pipeline/
│       ├── Preprocessor.py            # 原始日志 → 径元库
│       └── ClusteringPipeline.py      # 径元 → 带状态标注的径元
│
├── scripts/                           # ← 用户训练入口（命令行调用）
│   ├── build_pathlets.py
│   ├── train_weaving_law.py
│   └── train_synthesizer.py
│
└── data/                              # 原始数据
```

---

## 二、关键类清单与职责

### 【共用层】`src/traceloom/common/`
| 类 | 文件 | 职责 |
|----|------|------|
| `Observation` | `pathlet.py` | 单点网络快照（6维：`delay_up`, `loss_up`, `bw_up`, `delay_down`, `loss_down`, `bw_down`） |
| `BodyObservations` | `pathlet.py` | 【主干】100个观元 |
| `TailObservations` | `pathlet.py` | 【融尾】10个观元 |
| `Pathlet` | `pathlet.py` | `body: BodyObservations`, `tail: TailObservations`, `state_label: StateLabel` |
| `FeatureExtractor` | `features.py` | 从 `List[Observation]` 提取原始/统计特征 |
| `StateLabel` | `state.py` | `state_id: int`, `confidence: float` |
| `StateNamer` | `state.py` | **轻量版**：加载 `state_mapping.json`，ID ↔ 语义名 |

> 🔒 **约束**：`common/` 中不得 import `training/` 或 `torch/sklearn`

---

### 【训练层】`training/`
| 类 | 文件 | 职责 |
|----|------|------|
| `PathletBuilder` | `pathlet/PathletBuilder.py` | 切片轨迹 → 径元 |
| `WeavingLawTrainer` | `pathlet/WeavingLawTrainer.py` | 训练 GMM，生成 `state_mapping.json` |
| `NetworkDiffusionModel` | `synthesis/NetworkDiffusionModel.py` | 完整扩散模型（含训练循环） |
| `NetworkInterpolator` | `embroider/NetworkInterpolator.py` | 实现插值算法（含 PSD 约束） |
| `Preprocessor` | `pipeline/Preprocessor.py` | 聚合流程：日志 → 径元库 |

> ✅ **允许**：使用 `torch`, `sklearn`, `matplotlib`

---

### 【推理层】`src/traceloom/weaving/engines/`
| 类 | 文件 | 职责 |
|----|------|------|
| `Reweaver` | `Reweaver.py` | 拼接真实径元（调用 `common/`） |
| `Stitcher` | `Stitcher.py` | 缝入质径（调用轻量插值函数） |
| `Dreamer` | `Dreamer.py` | 生成幻径（加载 `.pth` 权重，**不依赖 `NetworkDiffusionModel`**） |

> 🔒 **禁止**：import `training/` 任何模块

---

## 三、核心解耦机制

| 功能 | 训练侧输出 | 推理侧输入 | 通信方式 |
|------|-----------|-----------|--------|
| 【织律】 | `weaving_law.pkl`（GMM权重 + `state_mapping.json`） | `Reweaver` 加载 | 文件序列化 |
| 生成模型 | `synthesizer.pth`（`state_dict`） | `Dreamer` 加载 | PyTorch 权重 |
| 状态映射 | `state_mapping.json` | `StateNamer` 加载 | JSON 文件 |

> ✅ **所有跨阶段通信通过文件，而非代码依赖**

---

## 四、开发 checklist（按顺序执行）

### 阶段 1：建立共用核心
- [ ] 创建 `src/traceloom/common/pathlet.py`，定义：
  ```python
  Observation, BodyObservations, TailObservations, Pathlet
  ```
- [ ] 创建 `src/traceloom/common/features.py`，实现 `FeatureExtractor`
- [ ] 更新 `core/config.py`：`OBSERVATION_FIELDS = ("delay_up", "loss_up", ...)`

### 阶段 2：迁移训练代码
- [ ] 将原 `training/common/` 拆解到新子目录
- [ ] 重命名类为 PascalCase（如 `PathletBuilder`）
- [ ] 确保所有训练类 import `traceloom.common`

### 阶段 3：解耦推理引擎
- [ ] 重写 `Dreamer.py`：内部定义轻量模型，加载 `.pth`
- [ ] 重写 `Reweaver.py`：加载 `weaving_law.pkl` + `state_mapping.json`
- [ ] 移除所有 `from training import ...`

### 阶段 4：验证
- [ ] `pip install -e .` 后，`tl reweave real.txt` 正常运行
- [ ] `python scripts/train_weaving_law.py` 正常训练
- [ ] 所有单元测试通过

---

## 五、命名规范（强制）

| 场景 | 规则 |
|------|------|
| **类名** | PascalCase（`PathletBuilder`, `Dreamer`） |
| **字段名** | snake_case（`delay_up`, `state_id`） |
| **训练目录** | 功能名（`synthesis`, `embroider`） |
| **推理引擎** | 引擎名（`Dreamer`, `Stitcher`, `Reweaver`） |
| **特征名** | 必须基于 `OBSERVATION_FIELDS`（如 `mean_delay_up`） |

---

> 🧵 **观元为始，主干载态，融尾续脉，径元成丝**  
> **织律识态，织样编序，三重织径，虚实无痕**