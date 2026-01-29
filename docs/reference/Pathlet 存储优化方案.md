当然！以下是完整的、可直接用于工程落地的 **《Pathlet 存储系统设计规范 v1.0》**，涵盖命名、数据模型、存储格式、生成逻辑与使用约定。

---

# 📘 Pathlet 存储系统设计规范  
**版本：1.0**  
**最后更新：2026年1月29日**  
**适用系统：HoloWAN 轨迹分析平台**

---

## 1. 设计原则

| 原则 | 说明 |
|------|------|
| **去重优先** | 利用滑动窗口重叠特性，观测点仅存一次 |
| **职责分离** | 对外清单 vs 内部元数据 vs 原始数据池 |
| **主键自描述** | `pathlet_id` 必须包含足够上下文，无需查表即可理解 |
| **写一次，读多处** | 所有 Pathlet（含无效）均持久化，用 `is_valid` 控制使用 |
| **Parquet 优化** | 充分利用列式存储、字典编码、分区与压缩 |

---

## 2. 核心概念定义

| 术语 | 定义 |
|------|------|
| **Observation** | 单时刻网络状态，含 6 个指标：`delay_up`, `loss_up`, `bw_up`, `delay_down`, `loss_down`, `bw_down` |
| **Pathlet** | 110 个连续 Observations 的逻辑单元：- **Body**: 前 100 点（用于建模）- **Tail**: 后 10 点（用于预测/验证） |
| **Trace** | 原始 HoloWAN 轨迹文件（如 `campus_2025.txt`） |
| **Sliding Window** | 步长 50、窗口 110 的滑动切片策略 |

---

## 3. 存储文件规范

系统生成以下三个 Parquet 文件，**必须共存**：

### 3.1 `pathlets.parquet` —— **对外清单（External Manifest）**

> 🎯 用途：供外部程序（标注工具、调度器、轻量分析）快速列出可用 Pathlet。

| 字段 | 类型 | 必填 | 约束 | 示例 |
|------|------|------|------|------|
| `pathlet_id` | string | ✅ | 符合 `PathletID` 格式（见 §4） | `"campus_00001250"` |
| `state_id` | int32 | ✅ | `-1` = 未标记；≥0 = 自定义状态 | `-1`, `0`, `1` |
| `source_file` | string | ✅ | 原始轨迹文件名（含扩展名） | `"campus_2025.txt"` |
| `start_index` | int32 | ✅ | ≥0 | `1250` |

> 🔒 **不变性**：此文件仅包含已成功写入 `pathlets_meta.parquet` 的 Pathlet。

---

### 3.2 `pathlets_meta.parquet` —— **内部元数据（Internal Metadata）**

> 🎯 用途：内部系统管理 Pathlet 生命周期、有效性、来源。

| 字段 | 类型 | 必填 | 约束 | 示例 |
|------|------|------|------|------|
| `pathlet_id` | string | ✅ | 同 `pathlets.parquet` | `"campus_00001250"` |
| `is_valid` | boolean | ✅ | 是否通过质量过滤 | `true` |
| `state_id` | int32 | ✅ | 同 `pathlets.parquet` | `-1` |
| `trace_name` | string | ✅ | 逻辑轨迹名（不含路径/扩展名） | `"campus"` |
| `start_index` | int32 | ✅ | 同 `pathlets.parquet` | `1250` |

> ⚠️ **同步要求**：`state_id` 变更时，必须同步更新 `pathlets.parquet`。

---

### 3.3 `pathlets_points.parquet` —— **去重观测池（Deduplicated Observations）**

> 🎯 用途：唯一存储所有观测点，支持高效重建任意 Pathlet。

| 字段 | 类型 | 必填 | 约束 | 示例 |
|------|------|------|------|------|
| `trace_name` | string | ✅ | 同 `pathlets_meta.trace_name` | `"campus"` |
| `trace_index` | int32 | ✅ | ≥0，在轨迹中全局唯一 | `1250` |
| `containing_pathlet_ids` | list\ | ✅ | 非空，元素为合法 `pathlet_id` | `["campus_00001200", "campus_00001250"]` |
| `delay_up` | float32 | ✅ | ≥0 | `45.2` |
| `loss_up` | float32 | ✅ | ∈ [0, 1] | `0.01` |
| `bw_up` | float32 | ✅ | ≥0 | `98.7` |
| `delay_down` | float32 | ✅ | ≥0 | `38.1` |
| `loss_down` | float32 | ✅ | ∈ [0, 1] | `0.0` |
| `bw_down` | float32 | ✅ | ≥0 | `102.4` |

> 📌 **物理存储要求**：
> - **分区字段**：`trace_name`
> - **排序字段**：每个分区内按 `trace_index` 升序
> - **压缩**：ZSTD
> - **编码**：`trace_name` 和 `containing_pathlet_ids` 启用字典编码

---

## 4. Pathlet ID 规范

### 4.1 格式
```
{TRACE_KEY}_{START_INDEX:08d}
```

- `TRACE_KEY`：安全化的逻辑轨迹名（仅含 `[a-zA-Z0-9_.-]`）
- `START_INDEX`：8 位零填充十进制整数

### 4.2 生成规则（Python）
```python
import re

def make_pathlet_id(trace_name: str, start_index: int) -> str:
    if start_index < 0:
        raise ValueError("start_index must be non-negative")
    # 移除非安全字符，保留字母、数字、下划线、点、连字符
    safe_key = re.sub(r"[^a-zA-Z0-9_.-]", "_", trace_name.strip())
    if not safe_key:
        raise ValueError("trace_name is empty after sanitization")
    return f"{safe_key}_{start_index:08d}"
```

### 4.3 解析规则
```python
def parse_pathlet_id(pathlet_id: str) -> tuple[str, int]:
    parts = pathlet_id.rsplit("_", 1)
    if len(parts) != 2 or not parts[1].isdigit():
        raise ValueError(f"Invalid pathlet_id format: {pathlet_id}")
    trace_key, idx_str = parts
    return trace_key, int(idx_str)
```

> ✅ **保证**：`make_pathlet_id(trace, idx) → parse → (trace, idx)`

---

## 5. 写入流程规范

### 5.1 生成阶段
对每条轨迹 `T`，执行滑动窗口（步长=50，窗口=110）：
1. 对每个起始位置 `i`，提取 110 点片段 `S`
2. 验证 `S[0:100]` 是否有效 → 得到 `(is_valid, reason)`
3. 生成：
   - `pathlet_id = make_pathlet_id(T.name, i)`
   - `meta = {pathlet_id, is_valid, state_id=-1, trace_name=T.name, start_index=i}`
   - 将 `S` 中每个观测点关联到 `pathlet_id`

### 5.2 写入阶段
1. **写 `pathlets_points.parquet`**：
   - 按 `trace_name` 分区
   - 每个分区内按 `trace_index` 排序
   - 合并相同 `(trace_name, trace_index)` 的 `containing_pathlet_ids`
2. **写 `pathlets_meta.parquet`**：全量覆盖或追加
3. **生成 `pathlets.parquet`**：
   ```python
   external_df = meta_df[["pathlet_id", "state_id", "trace_name", "start_index"]]
   external_df.rename(columns={"trace_name": "source_file"}).to_parquet(...)
   ```

---

## 6. 读取与使用规范

### 6.1 外部程序（只读清单）
```python
df = pd.read_parquet("pathlets.parquet")
active_pathlets = df[df["state_id"] != -1]
```

### 6.2 内部程序（重建完整 Pathlet）
```python
def load_pathlet(pathlet_id: str, meta_df, points_dataset) -> Pathlet:
    meta = meta_df.set_index("pathlet_id").loc[pathlet_id]
    points = points_dataset.to_table(filter=[
        ("trace_name", "=", meta["trace_name"]),
        ("trace_index", ">=", meta["start_index"]),
        ("trace_index", "<=", meta["start_index"] + 109)
    ]).to_pandas().sort_values("trace_index")
    
    # 构造 Observation 列表...
    return Pathlet(...)
```

> 🔑 **性能依赖**：`points_dataset` 必须基于分区+排序的 Parquet。

---

## 7. 版本与兼容性

- **向后兼容**：新增字段可选，旧程序忽略
- **不兼容变更**：修改字段类型/删除字段需升级版本号
- **Schema 演化**：使用 PyArrow Schema Evolution 机制

---

## 8. 附录：典型目录结构

```
/pathlet_storage/
├── pathlets.parquet                 # 对外清单
├── pathlets_meta.parquet            # 内部元数据
└── pathlets_points.parquet/         # 分区目录
    ├── trace=campus/
    │   └── part-00000-xxx.parquet
    ├── trace=lab/
    │   └── part-00000-yyy.parquet
    └── ...
```

---

> ✅ **本规范确保系统在存储效率、查询性能、可维护性之间达到最优平衡。**

感谢上传代码！结合你之前的说明和这两个文件，我现在**完全理解了你的架构**。

关键澄清：

> ✅ **`HoloWANRawTraceSegment` ≈ 你的 `PathletMeta`（但更重）**  
> 它不仅包含元数据（`trace_name`, `start_index`），还**内嵌了完整的 110 个 `Observation`**！

而你当前的 `PathletStorage.save_pathlets()` 接口是：
```python
def save_pathlets(
    self, 
    pathlets: List[Pathlet], 
    raw_trace_segment_map: Dict[str, HoloWANRawTraceSegment]
)
```

这意味着：
- `pathlets[i].pathlet_id` → 对应 `raw_trace_segment_map[pathlet_id]`
- 后者提供了**完整观测数据 + 元信息**

---

## 🔍 当前实现 vs 你描述的三文件目标

| 文件 | 当前是否生成 | 如何生成 |
|------|------------|--------|
| `pathlets_meta.parquet` | ✅ 是 | 来自 `pathlets` + `raw_trace_segment_map` 的元信息 |
| `pathlets_points.parquet` | ✅ 是 | 扁平化 `raw_trace_segment_map` 中的 110 点 |
| `pathlets.parquet` | ❌ **否** | 你的代码中**没有生成这个对外清单文件**！ |

> 🚨 **关键发现**：  
> 你**描述了** `pathlets.parquet`（对外清单），但**当前代码并未写入它**。  
> 你只写了 `pathlets_meta.parquet` 和 `pathlets_points.parquet`。

---

## ✅ 重构建议：在现有代码基础上增量支持 `pathlets.parquet`

### 步骤 1：明确 `pathlets.parquet` 的内容来源

它应是 `pathlets_meta.parquet` 的**投影（projection）**：
```python
# 从 metadata_df 生成 external_df
external_df = metadata_df[[
    "pathlet_id",
    "state_id",          # 来自 Pathlet.state_label 或 -1
    "trace_name",        # 改名为 source_file
    "start_index"
]].copy()
external_df.rename(columns={"trace_name": "source_file"}, inplace=True)
```

### 步骤 2：修改 `save_pathlets` 以同时写入三文件

在你现有的 `_write_metadata(metadata_df)` 之后，增加：

```python
# 新增：写入对外清单
self._write_external_manifest(metadata_df)
```

并实现：

```python
def _write_external_manifest(self, metadata_df: pd.DataFrame) -> None:
    """写入对外清单 pathlets.parquet"""
    external_df = metadata_df[[
        "pathlet_id",
        "state_id",
        "trace_name",
        "start_index"
    ]].copy()
    external_df.rename(columns={"trace_name": "source_file"}, inplace=True)
    
    table = pa.Table.from_pandas(external_df)
    pq.write_table(table, self.pathlet_dir / "pathlets.parquet", compression="ZSTD")
    logger.info(f"写入对外清单到 {self.pathlet_dir / 'pathlets.parquet'}")
```

### 步骤 3：确保 `state_id` 正确提取

在你现有的 `_extract_metadata` 中：
```python
state_id = pathlet.state_label.state_id if pathlet.state_label else -1
```
→ 这已正确，`metadata_df` 包含 `state_id`，可直接用于 `external_df`。

---

## 🔧 针对你代码的具体 patch 建议

### 在 `PathletStorage.save_pathlets` 中：

```python
# ... 你现有的代码 ...
metadata_df, points_df = self.storage_adapter.pathlets_to_storage(pathlets, raw_trace_segment_map)

# 写入内部文件
self._write_metadata(metadata_df)
self._write_points(points_df)

# 👇 新增：写入对外清单
self._write_external_manifest(metadata_df)  # <-- 新增这一行
```

### 新增方法 `_write_external_manifest`：

```python
def _write_external_manifest(self, metadata_df: pd.DataFrame) -> None:
    """写入对外清单 pathlets.parquet"""
    if metadata_df.empty:
        logger.warning("无数据可写入对外清单")
        return
        
    external_df = metadata_df[[
        "pathlet_id",
        "state_id",
        "trace_name",
        "start_index"
    ]].copy()
    external_df.rename(columns={"trace_name": "source_file"}, inplace=True)
    
    logger.info(f"写入对外清单到 {self.pathlet_dir / 'pathlets.parquet'}")
    table = pa.Table.from_pandas(external_df)
    pq.write_table(table, self.pathlet_dir / "pathlets.parquet", compression="ZSTD")
    logger.info(f"成功写入 {len(external_df)} 条对外清单记录")
```

---

## ✅ 最终效果

运行 `save_pathlets()` 后，将生成三个文件：

1. `pathlets_meta.parquet` —— 内部元数据（含 `is_valid`, `state_id`）
2. `pathlets_points.parquet` —— 去重观测池
3. `pathlets.parquet` —— **新增！对外清单（`pathlet_id`, `state_id`, `source_file`, `start_index`）**

完全符合你设计的三文件架构！

---

## 📌 注意事项

- **`is_valid` 字段**：你当前代码中假设所有 Pathlet 有效（`is_valid=True`）。如需支持无效样本，需在 `HoloWANRawTraceSegment` 或 `Pathlet` 中传递有效性标志。
- **`source_file` vs `trace_name`**：你代码中用的是 `trace_name`（来自 `HoloWANRawTraceSegment.trace_name`），对外改为 `source_file` 更清晰。
- **同步性**：每次 `save_pathlets` 都全量覆盖三文件，保证一致性。

---