## ✅ TraceLoom 聚类模块最终目录结构

```
project_root/
│
├── src/traceloom/                     # ← 纯运行时代码（无 matplotlib / 无训练逻辑）
│   ├── app/
│   ├── core/
│   ├── domain/                        # ← 领域模型（不可变）
│   │   ├── pathlet.py                 # Observation, Pathlet(state_id: int)
│   │   ├── state.py                   # StateLabel, StateNamer（可选）
│   │   └── pattern.py                 # Pattern, PatternParser
│   │
│   ├── models/                        # ← 新增！仅存放轻量级运行时模型
│   │   └── state_gmm.py               # StateGMMModel（加载 + 预测）
│   │
│   ├── weaving/
│   │   ├── engine.py                  # WeavingEngine（可调用 StateGMMModel）
│   │   └── engines/                   # Reweaver, Stitcher, Dreamer
│   │
│   ├── io/adapters/                   # I/O 适配器
│   │   ├── holowan.py                 # HoloWANFile（部署格式）
│   │   └── holowan_parser.py          # HoloWANParser（训练解析 → List[Observation]）
│   │
│   ├── storage/
│   │   ├── pathlet_storage.py         # 保存/加载 Pathlet（Parquet） + GMM 模型
│   │   └── task_store.py              # SQLite 任务状态
│   │
│   ├── devices/
│   │   └── holowan_manager.py         # 设备控制
│   │
│   ├── services/
│   │   └── weaver_service.py          # 协调服务
│   │
│   └── pipelines/                     # 运行时管道（simulation/validation）
│       ├── simulation.py
│       └── validation.py
│
└── training/                          # ← 所有训练/聚类/可视化逻辑
    └── pathlet_clustering/            # ← 聚类专用子模块
        ├── __init__.py
        ├── config.py                  # n_components, random_state 等
        ├── data_loader.py             # RawDataLoader（统一加载原始数据）
        ├── gmm_clusterer.py           # GMMClusterer（训练 + 特征提取）
        ├── pathlet_builder.py         # PathletBuilder（构建带 state_id 的径元）
        ├── visualization.py           # TSNEVisualizer / PCAPlotter（含 matplotlib）
        └── pipeline.py                # 端到端流程：load → cluster → build → save → visualize
```

---

## 🔧 **关键文件变更清单**

| 操作 | 源位置 | 目标位置 | 说明 |
|------|--------|----------|------|
| ✅ **新增** | — | `src/traceloom/models/state_gmm.py` | 轻量 GMM 推理模型（含 `_to_features`） |
| ✅ **新增** | — | `training/pathlet_clustering/` | 聚类训练专属目录 |
| ✅ **移动 + 重命名** | `weaving_law_trainer.py` | `training/pathlet_clustering/gmm_clusterer.py` | 聚类训练核心 |
| ✅ **移动 + 合并** | 多个 `NetworkProfileExtractor` | `training/pathlet_clustering/data_loader.py` | 统一数据加载 |
| ✅ **移动** | `pathlet_builder.py` | `training/pathlet_clustering/pathlet_builder.py` | 构建带标签径元 |
| ✅ **移动** | 可视化代码（如 `TSNEVisualizer`） | `training/pathlet_clustering/visualization.py` | 彻底移出 `src/` |
| ✅ **删除** | `src/traceloom/domain/features.py`（若存在） | — | 不再需要全局 FeatureExtractor |
| ✅ **保留但简化** | `domain/pathlet.py` | — | 仅定义 `Pathlet` 结构（含 `state_id: int`） |
| ✅ **增强** | `storage/pathlet_storage.py` | — | 支持 `save_gmm_model()` / `load_gmm_model()` |

---

## 📦 **依赖关系约束（必须遵守）**

- ✅ `training/` **可以** 导入 `src/traceloom/`  
  （例如：`from traceloom.domain.pathlet import Observation`）

- ❌ `src/traceloom/` **绝不可以** 导入 `training/`  
  （保证推理环境纯净）

- ✅ `models/state_gmm.py` **只依赖**：
  - `numpy`
  - `joblib`
  - `sklearn.mixture.GaussianMixture`
  - `traceloom.domain.pathlet.Observation`

- ❌ `src/` 中**禁止出现**：
  - `matplotlib`, `seaborn`, `plotly`
  - `sklearn` 除 `GaussianMixture` 外的其他模块（如 `TSNE`）

---

## 🔄 **数据流与职责分工**

| 阶段 | 组件 | 职责 |
|------|------|------|
| **训练** | `training/pathlet_clustering/pipeline.py` | 端到端聚类流程 |
| | `gmm_clusterer.py` | 训练 GMM，提取聚类专用特征 |
| | `pathlet_builder.py` | 生成 `Pathlet(state_id=...)` |
| | `visualization.py` | 生成 t-SNE/PCA 图（仅训练时） |
| **持久化** | `storage/pathlet_storage.py` | 保存：• `all_pathlets.parquet`（含 `state_id`）• `state_gmm.joblib`（GMM 模型） |
| **推理** | `models/state_gmm.py` | 加载 GMM，对新观测预测 `state_id` |
| | `weaving/engine.py` | 使用固化径元 + 动态 GMM 预测 |

---

## ✅ **预期收益**

| 维度 | 改进 |
|------|------|
| **架构清晰** | 训练 vs 推理严格分离 |
| **特征自治** | 每个模型管理自己的特征（未来扩展无忧） |
| **推理轻量** | `src/` 无重型依赖，启动快 |
| **一致性保障** | 通过测试 + 注释确保训练/推理特征一致 |
| **可维护性** | 新人一眼看懂：聚类在哪？→ `training/pathlet_clustering/` |

---

> 🎯 **执行口诀**：  
> **“训练归 training，模型进 models，特征各自管，src 保纯净”**


太好了！你提供了**非常清晰、专业且工程化的聚类特征方案**（16 维，基于原始值，含 log 变换和条件丢包等）。现在我们将其**无缝整合进最终架构**，并明确归属。

---

## ✅ 最终结论：**聚类特征提取逻辑应内聚于聚类任务，但需在训练/推理两端同步**

> **不再使用 6 维原始值，而是你定义的 16 维高级统计特征**  
> **特征计算基于 `raw_*` 字段，窗口内独立，抗长尾**

---

## 🗂️ 特征提取代码存放位置（权威版）

### 1. **训练侧（Training Side）**
```python
# training/pathlet_clustering/feature_extractor.py

import numpy as np
from typing import Dict, List

def extract_features_from_window(window: Dict[str, List[float]]) -> np.ndarray:
    """
    从单个 100 点窗口提取 16 维聚类特征（基于 raw_* 字段）
    
    Args:
        window: {
            "raw_delay_up": [d1, d2, ..., d100],
            "raw_loss_up": [l1, l2, ..., l100],
            "raw_delay_down": [...],
            "raw_loss_down": [...]
        }
    
    Returns:
        np.ndarray of shape (16,) → [up_8d + down_8d]
    """
    def _extract_direction(delay_seq: List[float], loss_seq: List[float]) -> List[float]:
        delay = np.array(delay_seq)
        loss = np.array(loss_seq)
        
        # Step 1: log transform
        delay_log = np.log(delay + 1)
        
        # Step 2: delay features (4)
        delay_mean = float(np.mean(delay_log))
        delay_std = float(np.std(delay_log, ddof=1))
        delay_p95 = float(np.percentile(delay_log, 95))
        delay_max = float(np.max(delay_log))
        
        # Step 3: loss features (4)
        has_loss = 1.0 if np.any(loss > 0) else 0.0
        cond_loss_mean = float(np.mean(loss[loss > 0])) if np.any(loss > 0) else 0.0
        loss_ratio = float(np.sum(loss > 0) / len(loss))
        loss_mean = float(np.mean(loss))
        
        return [
            delay_mean, delay_std, delay_p95, delay_max,
            has_loss, cond_loss_mean, loss_ratio, loss_mean
        ]
    
    up_feat = _extract_direction(window["raw_delay_up"], window["raw_loss_up"])
    down_feat = _extract_direction(window["raw_delay_down"], window["raw_loss_down"])
    
    return np.array(up_feat + down_feat, dtype=np.float32)
```

### 2. **推理侧（Inference Side）**
```python
# src/traceloom/models/clustering_features.py  ← 新增！

import numpy as np
from typing import List
from traceloom.domain.pathlet import Observation

def extract_features_for_gmm(observations: List[Observation]) -> np.ndarray:
    """
    将 100 个 Observations 转为 16 维特征向量（与训练侧完全一致）
    注意：使用 .raw_delay_up 等字段（假设 Observation 存储了 raw 值）
    """
    # 提取序列
    raw_delay_up = [o.raw_delay_up for o in observations]
    raw_loss_up = [o.raw_loss_up for o in observations]
    raw_delay_down = [o.raw_delay_down for o in observations]
    raw_loss_down = [o.raw_loss_down for o in observations]
    
    window = {
        "raw_delay_up": raw_delay_up,
        "raw_loss_up": raw_loss_up,
        "raw_delay_down": raw_delay_down,
        "raw_loss_down": raw_loss_down
    }
    
    from training.pathlet_clustering.feature_extractor import extract_features_from_window
    # ⚠️ 问题：src 不能依赖 training！
```

> ❌ **冲突出现**：`src/` 不能导入 `training/`

---

## 🔧 正确解法：**复制特征逻辑到推理侧（接受合理重复）**

### 修改推理侧实现：
```python
# src/traceloom/models/clustering_features.py

import numpy as np
from typing import List
from traceloom.domain.pathlet import Observation

def _extract_direction_features(delay_seq: List[float], loss_seq: List[float]) -> List[float]:
    """内部工具函数（与 training/pathlet_clustering/feature_extractor.py 完全一致）"""
    delay = np.array(delay_seq)
    loss = np.array(loss_seq)
    
    delay_log = np.log(delay + 1)
    delay_mean = float(np.mean(delay_log))
    delay_std = float(np.std(delay_log, ddof=1))
    delay_p95 = float(np.percentile(delay_log, 95))
    delay_max = float(np.max(delay_log))
    
    has_loss = 1.0 if np.any(loss > 0) else 0.0
    cond_loss_mean = float(np.mean(loss[loss > 0])) if np.any(loss > 0) else 0.0
    loss_ratio = float(np.sum(loss > 0) / len(loss))
    loss_mean = float(np.mean(loss))
    
    return [
        delay_mean, delay_std, delay_p95, delay_max,
        has_loss, cond_loss_mean, loss_ratio, loss_mean
    ]

def extract_features_for_gmm(observations: List[Observation]) -> np.ndarray:
    """
    ⚠️ 必须与 training/pathlet_clustering/feature_extractor.py 保持完全一致！
    """
    raw_delay_up = [o.raw_delay_up for o in observations]
    raw_loss_up = [o.raw_loss_up for o in observations]
    raw_delay_down = [o.raw_delay_down for o in observations]
    raw_loss_down = [o.raw_loss_down for o in observations]
    
    up_feat = _extract_direction_features(raw_delay_up, raw_loss_up)
    down_feat = _extract_direction_features(raw_delay_down, raw_loss_down)
    
    return np.array(up_feat + down_feat, dtype=np.float32)
```

> ✅ **关键**：两处 `_extract_direction_features` 函数**代码完全相同**

---

## 🔁 更新 GMM 模型使用新特征

### 训练侧：
```python
# training/pathlet_clustering/gmm_clusterer.py
from .feature_extractor import extract_features_from_window

class GMMClusterer:
    def fit_from_windows(self, windows: List[Dict]) -> Self:
        X = np.array([extract_features_from_window(w) for w in windows])
        # 可选：应用 RobustScaler（保存 scaler 供推理用）
        self.scaler = RobustScaler()
        X_scaled = self.scaler.fit_transform(X)
        self.gmm.fit(X_scaled)
        return self
```

### 推理侧：
```python
# src/traceloom/models/state_gmm.py
from .clustering_features import extract_features_for_gmm
from sklearn.preprocessing import RobustScaler  # 如果用了 scaler

class StateGMMModel:
    def __init__(self, gmm: GaussianMixture, scaler: Optional[RobustScaler] = None):
        self.gmm = gmm
        self.scaler = scaler
    
    def predict_state(self, observations: List[Observation]) -> int:
        feat = extract_features_for_gmm(observations)  # (16,)
        if self.scaler:
            feat = self.scaler.transform(feat.reshape(1, -1))
        return int(self.gmm.predict(feat.reshape(1, -1))[0])
```

> 💡 **注意**：如果训练时用了 `RobustScaler`，必须一并保存并在推理时加载

---

## 📦 目录结构最终确认（含特征）

```
src/traceloom/
├── domain/
│   └── pathlet.py          # Observation 需包含 raw_delay_up, raw_loss_up 等字段
├── models/
│   ├── state_gmm.py        # StateGMMModel（调用 clustering_features）
│   └── clustering_features.py  # ← 新增！16维特征提取（推理侧）
└── ...

training/pathlet_clustering/
├── feature_extractor.py    # ← 新增！16维特征提取（训练侧）
├── gmm_clusterer.py        # 使用 feature_extractor
└── ...
```

---

## 🔒 一致性保障：单元测试

```python
# tests/test_clustering_feature_consistency.py

def test_16d_feature_consistency():
    # 构造测试窗口
    window = {
        "raw_delay_up": [50.0] * 99 + [200.0],
        "raw_loss_up": [0.0] * 99 + [0.1],
        "raw_delay_down": [40.0] * 100,
        "raw_loss_down": [0.0] * 100
    }
    
    # 训练侧
    from training.pathlet_clustering.feature_extractor import extract_features_from_window
    X_train = extract_features_from_window(window)
    
    # 推理侧（模拟 Observation 列表）
    from traceloom.domain.pathlet import Observation
    obs_list = [
        Observation(
            raw_delay_up=d_up, raw_loss_up=l_up,
            raw_delay_down=d_down, raw_loss_down=l_down,
            # ... 其他字段
        )
        for d_up, l_up, d_down, l_down in zip(
            window["raw_delay_up"], window["raw_loss_up"],
            window["raw_delay_down"], window["raw_loss_down"]
        )
    ]
    from traceloom.models.clustering_features import extract_features_for_gmm
    X_infer = extract_features_for_gmm(obs_list)
    
    np.testing.assert_array_equal(X_train, X_infer)
```

---

## ✅ 总结：你的 16 维特征方案已完整落地

| 要素 | 实现 |
|------|------|
| **特征维度** | 16 维（上下行各 8 维） |
| **输入** | `raw_delay_*`, `raw_loss_*`（物理单位） |
| **关键处理** | `log(delay+1)`, 条件丢包均值, 二值丢包指示 |
| **训练侧位置** | `training/pathlet_clustering/feature_extractor.py` |
| **推理侧位置** | `src/traceloom/models/clustering_features.py` |
| **一致性保障** | 单元测试 + 显式注释 |
| **归一化建议** | 训练时用 `RobustScaler`，并保存用于推理 |

> 🎯 **现在你可以放心训练 GMM，并在推理时对新轨迹准确分配状态！**
