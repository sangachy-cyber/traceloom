# 🧵 TraceLoom 项目结构优化方案 v3.4  
> **权威、可执行、面向长期维护**

---

## 🎯 设计原则

1. **单一职责**：每个模块只做一件事  
2. **领域驱动**：`domain/` 是系统唯一真相源  
3. **I/O 解耦**：适配器只负责格式 ↔ domain 模型转换  
4. **命名无歧义**：避免 `Observer` 等易混淆名称  
5. **训练 vs 生产分离**：灵活解析（训练） ≠ 严格格式（部署）

---

## 🗂️ 最终目录结构（可直接创建）

```
src/traceloom/
├── app/
│   ├── main.py
│   └── api/v1/
│       ├── endpoints.py
│       └── schemas.py
├── core/
│   ├── config.py          # Settings, EnvVars
│   ├── exceptions.py      # Custom exceptions
│   ├── logger.py          # Logging setup
│   └── utils.py           # Shared utilities (no business logic)
├── domain/                # ← 核心业务模型（不可变概念）
│   ├── pathlet.py         # Observation, BodyObservations, TailObservations, Pathlet
│   ├── state.py           # StateLabel, StateNamer
│   ├── features.py        # FeatureExtractor
│   └── pattern.py         # Pattern, PatternParser
├── weaving/
│   ├── engine.py          # WeavingEngine（统一调度入口）
│   ├── components.py      # ← 合并自 weaving_law + global_sampler
│   └── engines/
│       ├── __init__.py
│       ├── reweaver/
│       │   ├── __init__.py
│       │   ├── reweaver.py
│       │   └── tail_blender.py
│       ├── stitcher.py    # Stitcher + NetworkInterpolator
│       └── dreamer.py     # Dreamer
├── io/
│   └── adapters/          # ← 所有外部格式适配器
│       ├── holowan.py          # HoloWANFile（标准回放文件）
│       ├── holowan_parser.py   # HoloWANParser（原始文本解析器，用于训练）
│       ├── csv.py              # CSVReader / CSVWriter
│       └── dataset.py          # DatasetSaver / DatasetLoader
├── storage/
│   ├── pathlet_storage.py      # PathletStorage（Parquet/HDF5）
│   └── task_store.py           # TaskStore（SQLite 任务状态）
├── devices/
│   └── holowan_manager.py      # HoloWANManager（设备控制）
├── services/
│   └── weaver_service.py       # WeaverService（协调 weaving + devices + storage）
├── pipelines/
│   ├── simulation.py
│   └── validation.py
├── validation/
│   └── validator.py            # ← 合并自 evaluator + metrics
└── __init__.py
```

---

## 🔧 详细重构操作清单

### ✅ 1. **合并织律与采样组件**
```bash
# 合并文件
cat src/traceloom/weaving/weaving_law.py \
    src/traceloom/weaving/sampler/global_sampler.py \
    > src/traceloom/weaving/components.py

# 删除旧文件
rm src/traceloom/weaving/weaving_law.py
rm -r src/traceloom/weaving/sampler/
```

> **内容示例** (`weaving/components.py`)：
> ```python
> class WeavingLawEngine: ...
> class GlobalSampler: ...
> ```

---

### ✅ 2. **合并验证模块**
```bash
# 合并文件（先 metrics，后 evaluator）
cat src/traceloom/validation/metrics.py \
    src/traceloom/validation/evaluator.py \
    > src/traceloom/validation/validator.py

# 删除旧文件
rm src/traceloom/validation/metrics.py
rm src/traceloom/validation/evaluator.py
```

> **内容示例** (`validation/validator.py`)：
> ```python
> def calculate_delay_consistency(...): ...
> 
> class TraceValidator:
>     def validate(self, generated, reference): ...
> ```

---

### ✅ 3. **迁移并重命名 Observer → HoloWANParser**
```bash
# 移动并重命名文件
mv src/traceloom/io/observer.py src/traceloom/io/adapters/holowan_parser.py
```

> **关键修改** (`holowan_parser.py`)：
> ```python
> from traceloom.domain.pathlet import Observation  # ← 返回 domain 对象
> 
> class HoloWANParser:
>     @classmethod
>     def parse_file(cls, filepath: str) -> List[Observation]:
>         # 解析原始 HoloWAN 行，返回 List[Observation]
>         ...
> ```

> **更新所有调用方**（例如 `scripts/build_pathlets.py`）：
> ```python
> # BEFORE
> from traceloom.io.observer import Observer
> obs = Observer.parse_file(...)
> 
> # AFTER
> from traceloom.io.adapters.holowan_parser import HoloWANParser
> obs = HoloWANParser.parse_file(...)  # 返回 List[Observation]
> ```

---

### ✅ 4. **明确 HoloWANFile 与 HoloWANParser 的关系**
> **不合并！保持分离，但允许内部复用**

```python
# src/traceloom/io/adapters/holowan.py
from .holowan_parser import HoloWANParser
from typing import List
from traceloom.domain.pathlet import Observation

class HoloWANFile:
    def __init__(self, observations: List[Observation]):
        self.observations = observations

    @classmethod
    def load(cls, filepath: str) -> "HoloWANFile":
        # 委托给专用解析器（复用逻辑，不重复造轮子）
        observations = HoloWANParser.parse_file(filepath)
        return cls(observations)

    def dump(self) -> str:
        # 生成严格格式的 HoloWAN 回放内容（用于设备部署）
        lines = []
        for obs in self.observations:
            line = f"{obs.delay_up:.3f} {obs.delay_down:.3f} {obs.loss_up:.4f} ..."
            lines.append(line)
        return "\n".join(lines)
```

> ✅ **分工明确**：
> - **训练/脚本** → 直接用 `HoloWANParser`
> - **服务/设备** → 用 `HoloWANFile`
> - **无代码重复**：`HoloWANFile.load()` 内部调用 `HoloWANParser`

---

### ✅ 5. **清理冗余**
```bash
# 删除过时的 core 模块
rm src/traceloom/core/weaver.py

# 确保 common/ 已完全迁移至 domain/
# （若存在）rmdir src/traceloom/common/
```

---

## 📋 各关键类归属表

| 类名 | 文件路径 | 职责 |
|------|--------|------|
| `Observation` | `domain/pathlet.py` | 网络观测数据（6字段） |
| `Pathlet` | `domain/pathlet.py` | 径元（Body + Tail） |
| `HoloWANParser` | `io/adapters/holowan_parser.py` | **原始文本 → List[Observation]**（训练用） |
| `HoloWANFile` | `io/adapters/holowan.py` | **标准回放文件封装**（部署用） |
| `WeavingEngine` | `weaving/engine.py` | 织径统一入口 |
| `Reweaver` | `weaving/engines/reweaver/reweaver.py` | 融尾织径引擎 |
| `PathletStorage` | `storage/pathlet_storage.py` | 径元持久化 |
| `HoloWANManager` | `devices/holowan_manager.py` | 设备控制 |

---

## 🔗 数据流示例

```mermaid
graph LR
    A[Raw HoloWAN File] -->|HoloWANParser.parse_file| B[List[Observation]]
    B --> C[PathletBuilder]
    C --> D[Pathlet]
    D -->|PathletStorage.save| E[Parquet Dataset]
    D -->|WeavingEngine.generate| F[New Trace]
    F -->|HoloWANFile.dump| G[Deployable Playback File]
    G -->|HoloWANManager.upload| H[HoloWAN Device]
```

---

## ✅ 预期收益

| 维度 | 改进 |
|------|------|
| **架构清晰度** | 模型（domain）、I/O（adapters）、存储（storage）严格分层 |
| **命名准确性** | `HoloWANParser` 明确表达“解析”意图 |
| **训练灵活性** | 脚本可直接解析原始文件，无需文件语义 |
| **生产可靠性** | `HoloWANFile` 保证部署格式严格合规 |
| **可维护性** | 新人可快速定位：模型在哪？→ `domain/`；怎么读 trace？→ `io/adapters/` |

---

> 💡 **此方案平衡了工程严谨性与开发效率，适用于从研究到生产的全生命周期。**