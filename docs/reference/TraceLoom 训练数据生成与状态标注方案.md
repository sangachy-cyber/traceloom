# 🧩 TraceLoom 训练数据生成与状态标注方案  
> **版本**：v2.0 · 2026年1月  
> **目标**：将原始 HoloWAN 日志转换为结构化的 `NetworkProfile` 序列（含 10s 上下文 + 1s 真实延续），支持后续聚类标注、模型训练与仿真验证。  
> **关键升级**：成对窗口提取、CSV 可读格式、端到端流水线、无缝对接状态聚类。

---

## 一、核心目标

| 原始目标 | **增强后目标** |
|--------|--------------|
| 生成训练/测试 Parquet | → **生成 train/test CSV（含 10s+1s 成对结构）** |
| 单文件滑动窗口 | → **保留，但强制要求后续有 1s（10行）延续** |
| `is_valid` 软删除 | → **保留，并作为聚类输入过滤条件** |
| `state_id=0` 预留 | → **扩展为 6 类语义 ID（纯净+混合）** |
| 路径分层 | → **完全适配 `pipelines/` + `simcore/pathlet/` 架构** |

---

## 二、输入规范

- **目录**：`data/raw/`
- **文件**：多个 `.txt` 文件（如 `campus.txt`, `lab.txt`）
- **格式**：每行六列空格/制表符分隔：
  ```
  delay_up loss_up bw_up delay_down loss_down bw_down
  ```
- **前提**：无预处理，直接使用原始日志

---

## 三、输出规范

### 3.1 文件路径（CSV 格式）

| 数据集 | 路径 |
|--------|------|
| 训练集 | `data/before_label/train.csv` |
| 测试集 | `data/before_label/test.csv` |
| 全局归一化器 | `data/before_label/global_scaler.joblib` |

> ✅ **全部使用 CSV**，便于人工检查 10s+1s 对齐

---

### 3.2 每行字段（共 1323 列）

| 字段前缀 | 含义 | 长度 | 示例 |
|----------|------|------|------|
| `trace_name` | 来源文件名 | 1 | `"campus"` |
| `start_index` | context 起始行索引 | 1 | `0` |
| `ctx_raw_*` | **上下文原始值**（10s） | 12 × 100 | `ctx_raw_delay_up_0 ... ctx_raw_bw_down_99` |
| `ctx_norm_*` | **上下文归一化值** | 12 × 100 | `ctx_norm_delay_up_0 ...` |
| `cont_raw_*` | **延续原始值**（1s） | 12 × 10 | `cont_raw_delay_up_0 ... cont_raw_bw_down_9` |
| `cont_norm_*` | **延续归一化值** | 12 × 10 | `cont_norm_delay_up_0 ...` |
| `is_valid` | 是否通过清洗规则 | 1 | `True` |
| `state_id` | **网络状态 ID**（初始为 -1，聚类后更新） | 1 | `-1` → `3` |
| `state_name` | **状态名称**（聚类后填充） | 1 | `"jittery/abnormal"` |

> 🔸 **总列数** = `2 + 12*100*2 + 12*10*2 + 1 + 2 = 2 + 2400 + 240 + 3 = 2645`  
> 🔸 **初始生成时**：`state_id = -1`, `state_name = ""`（由聚类模块填充）

---

## 四、核心逻辑

### 4.1 窗口生成规则（成对提取）

| 参数 | 值 | 说明 |
|------|-----|------|
| Context 长度 | 100 行 | ≈10 秒历史 |
| Continuation 长度 | 10 行 | ≈1 秒真实未来 |
| 步长 | 50 行 | 50% 重叠 |
| 作用域 | 单文件内 | 不跨文件 |
| 尾部处理 | 若 `start + 110 > file_length` → 跳过 | 必须同时满足 context + continuation |

> 💡 **每个窗口天然包含“已知”与“真实答案”**，支撑监督学习与验证

---

### 4.2 清洗与 `is_valid` 判定

对 **context 或 continuation** 中的 `raw_delay` 检查：

| 条件 | 结果 |
|------|------|
| 存在 `raw_delay > 2000` (ms) | `is_valid = False` |
| 上行或下行存在 **连续 ≥10 个相等延迟** | `is_valid = False` |

> 🔍 未违反任一条件 → `is_valid = True`  
> 📌 **窗口始终保存**，仅通过 `is_valid` 实现“软删除”

---

### 4.3 训练/测试划分策略

- 所有 `.txt` 文件按字母序排序
- **最后一个文件** → 测试集
- **其余所有文件** → 训练集

✅ 模拟“历史数据训练，新场景测试”的真实部署逻辑

---

## 五、归一化策略

- **Delay**：`log(1 + x)` + `StandardScaler`（全局共享）
- **Loss**：`value / 100.0`（线性缩放）
- **Bandwidth**：保持原始值不变
- **Scalers**：保存为 `global_scaler.joblib`，供反变换使用

> 🔸 归一化在 **整个训练集上拟合**，测试集仅 transform

---

## 六、模块实现路径（适配 TraceLoom 架构）

| 功能 | 路径 | 职责 |
|------|------|------|
| HoloWAN 解析 | `src/traceloom/io/holowan.py` | `.txt` → DataFrame |
| Profile 提取 | `src/traceloom/simcore/pathlet/extractor.py` | 滑动窗口 + 清洗 + 归一化 → `List[NetworkProfile]` |
| CSV 保存 | `src/traceloom/io/csv_io.py` | `List[NetworkProfile]` → `.csv` |
| **训练数据流水线** | `src/traceloom/pipelines/preprocessing.py` | **编排全过程** |
| CLI 入口 | `scripts/preprocess.py` | 调用 pipeline |

> 🔸 **不再有独立 `generate_training_dataset.py`**，统一由 `pipelines/preprocessing.py` 处理

---

## 七、使用方式

```bash
# 生成训练/测试 CSV
uv run python scripts/preprocess.py

# 输出日志示例
[INFO] Found 3 files in data/raw/
[INFO] Train traces: [campus, lab], Test trace: wan_trace
[INFO] Generated 120 profiles from campus.txt (95 valid)
[INFO] Generated 80 profiles from lab.txt (70 valid)
[INFO] Generated 60 profiles from wan_trace.txt (50 valid)
[INFO] Saved train.csv (165 samples), test.csv (50 samples)
```

---

## 八、与聚类模块的衔接

1. **预处理阶段**：生成 `train.csv` / `test.csv`，`state_id = -1`
2. **聚类阶段**：
   - 加载 `train.csv`，过滤 `is_valid=True`
   - 提取 `ctx_raw_*` → 16D 特征
   - GMM 聚类 → 分配 `state_id` / `state_name`
   - 保存 `train_with_state.csv`
3. **下游使用**：
   - 【替】：按 `state_id` 拼接 profiles
   - 【造】/【拓】：以 `state_id` 为条件生成新轨迹

> ✅ **数据流闭环**：原始日志 → 可标注元 → 语义状态 → 仿真生成

---

## 九、设计优势总结

| 优势 | 说明 |
|------|------|
| **概念精准** | “元” = 10s context + 1s continuation |
| **可读性强** | 中间数据用 CSV，非 Parquet |
| **验证友好** | continuation 提供真实 ground truth |
| **灵活筛选** | `is_valid` 支持动态调整可用集 |
| **标注就绪** | 预留 `state_id` 字段，无缝对接聚类 |
| **场景真实** | 按文件划分，避免数据泄露 |
| **工程规范** | 符合 `pipelines/` + `simcore/` 分层架构 |

---

## 附：目录结构快照（相关部分）

```text
src/traceloom/
├── io/
│   ├── holowan.py      # 解析 .txt
│   └── csv_io.py       # 读写 CSV
├── simcore/pathlet/
│   ├── profile.py      # NetworkProfile 定义
│   └── extractor.py    # 窗口提取 + 清洗 + 归一化
├── pipelines/
│   └── preprocessing.py # 端到端流水线
scripts/
└── preprocess.py       # CLI 入口
```

---

这份方案彻底打通了 **从原始日志到语义状态** 的全链路，既保留了你原有设计的严谨性（软删除、单文件滑动、全局 scaler），又全面拥抱 TraceLoom 的新范式（`NetworkProfile`、`pipelines/`、t-SNE 聚类）。

> **织虚之始，在于元；元之精，在于态。**