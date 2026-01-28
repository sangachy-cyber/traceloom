# TraceLoom Weaver Service 在线织径方案设计

> **目标**：提供灵活、明确、可审计的网络织径仿真控制服务，支持自动或手动选择编织引擎，并通过 HoloWAN 损伤仪执行持续注入。

---

## 一、核心设计原则

| 原则 | 说明 |
|------|------|
| 🔧 **双模式引擎选择** | 支持 **自动选择**（`/weave`）和 **显式指定**（`/reweave`, `/stitch`, `/dream`） |
| 🧭 **URL 区分资源** | 不同引擎使用独立路径，符合 REST 资源模型 |
| 📏 **用户完全控制设备** | 必须提供 `engine_id` 和 **已存在的** `path_name` |
| ⏳ **仿真持续运行** | 启动后**不会自动结束**，必须调用 `DELETE` 停止 |
| 🧹 **停止即清理** | 强制从 HoloWAN 删除回放文件和流规则 |
| 💾 **支持归档** | 所有任务提供 `/playback` 下载接口（保留 24 小时） |
| 🚫 **无虚假数据** | **不返回** `current_observation`（因 HoloWAN 无法实时读取） |

---

## 二、API 端点汇总表

| 功能 | 自动选择 | Reweaver | Stitcher | Dreamer |
|------|--------|----------|----------|--------|
| **启动任务** | `POST /weave` | `POST /reweave` | `POST /stitch` | `POST /dream` |
| **查询状态** | `GET /weave/{id}` | `GET /reweave/{id}` | `GET /stitch/{id}` | `GET /dream/{id}` |
| **停止任务** | `DELETE /weave/{id}` | `DELETE /reweave/{id}` | `DELETE /stitch/{id}` | `DELETE /dream/{id}` |
| **下载回放文件** | `GET /weave/{id}/playback` | `GET /reweave/{id}/playback` | `GET /stitch/{id}/playback` | `GET /dream/{id}/playback` |
| **引擎选择逻辑** | 根据 `weaving_pattern` 自动路由 | 固定使用 `Reweaver` | 固定使用 `Stitcher` | 固定使用 `Dreamer` |
| **适用场景** | 快速实验、脚本调用 | 基于真实 trace 重织 | 多 trace 拼接 | 完全生成式损伤 |

> 🔑 **所有端点共享相同请求体结构和响应格式（除引擎字段外）**

---

## 三、通用数据结构

### 1. `ImpairmentDevice`（必填）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `host` | string | ✅ | HoloWAN 设备 IP（如 `"160.100.15.195"`） |
| `port` | integer | ✅ | Web API 端口（通常 `8080`） |
| `engine_id` | integer | ✅ | 引擎 ID（1 ~ N） |
| `path_name` | string | ✅ | **必须已在 HoloWAN GUI 中创建** 的虚拟链路名 |

> ⚠️ 若 `path_name` 不存在 → 返回 `400 Bad Request`

---

### 2. 任务状态枚举（`status` 字段）

| 状态 | 说明 |
|------|------|
| `accepted` | 请求已接收 |
| `connecting_device` | 正在连接 HoloWAN |
| `finding_path` | 查找 `path_name` |
| `binding_flow` | 绑定 `target_ip` 到 Path |
| `uploading_profile` | 上传 `.txt` 回放文件 |
| `running` | **仿真已启动，持续运行中**（需手动停止） |
| `stopping` | 用户请求停止，正在清理 |
| `completed` | 已成功停止并清理 |
| `failed` | 执行过程中出错 |

> 📌 **`running` 是持久状态，不会自动变为 `completed`**

---

## 四、详细 API 规范

### 1. 启动织径任务

#### 路径与方法
| 入口类型 | HTTP 方法 + 路径 |
|--------|----------------|
| 自动选择 | `POST /api/v1/weave` |
| Reweaver | `POST /api/v1/reweave` |
| Stitcher | `POST /api/v1/stitch` |
| Dreamer | `POST /api/v1/dream` |

#### 请求体（所有入口相同）
```json
{
  "target_ip": "10.10.10.10",
  "weaving_pattern": "s0x2 -> s9x1",
  "impairment_device": {
    "host": "160.100.15.195",
    "port": 8080,
    "engine_id": 1,
    "path_name": "MyLink"
  }
}
```

| 字段 | 说明 |
|------|------|
| `target_ip` | 目标流量 IP（需在 HoloWAN 监控范围内） |
| `weaving_pattern` | 织样语法（如 `"s0x3"` 或 `"s0->s1x2"`） |
| `impairment_device` | 见上文定义 |

> 💡 **自动选择入口**：服务内部根据 `weaving_pattern` 语法规则路由到对应引擎  
> 💡 **显式入口**：忽略 pattern 语义，强制使用指定引擎

#### 成功响应（202 Accepted）
```json
{
  "task_id": "weave_a1b2c3",        // 自动入口前缀为 "weave_"
  "engine": "reweaver",             // 实际使用的引擎（自动入口会推断）
  "status": "running",
  "message": "网络损伤注入已启动（需手动停止）",
  "download_url": "/api/v1/weave/weave_a1b2c3/playback"
}
```

| 字段 | 说明 |
|------|------|
| `task_id` | 全局唯一 ID，带前缀标识来源（`weave_`, `reweave_`, `stitch_`, `dream_`） |
| `engine` | 实际使用的引擎名称（`reweaver` / `stitcher` / `dreamer`） |
| `download_url` | 回放文件下载链接（24 小时有效） |

---

### 2. 查询任务状态

#### 路径与方法
| 入口类型 | HTTP 方法 + 路径 |
|--------|----------------|
| 自动选择 | `GET /api/v1/weave/{task_id}` |
| Reweaver | `GET /api/v1/reweave/{task_id}` |
| Stitcher | `GET /api/v1/stitch/{task_id}` |
| Dreamer | `GET /api/v1/dream/{task_id}` |

> 🔒 **必须使用与启动时相同的路径前缀查询**

#### 成功响应（200 OK）
```json
{
  "task_id": "weave_a1b2c3",
  "engine": "reweaver",
  "status": "running",
  "target_ip": "10.10.10.10",
  "weaving_pattern": "s0x2 -> s9x1",
  "impairment_device": {
    "host": "160.100.15.195",
    "port": 8080,
    "engine_id": 1,
    "path_name": "MyLink"
  },
  "started_at": "2026-01-27T10:30:00Z",
  "download_url": "/api/v1/weave/weave_a1b2c3/playback"
}
```

> ❌ **已移除 `current_observation` 字段**（因不可获取）

---

### 3. 停止织径任务

#### 路径与方法
| 入口类型 | HTTP 方法 + 路径 |
|--------|----------------|
| 自动选择 | `DELETE /api/v1/weave/{task_id}` |
| Reweaver | `DELETE /api/v1/reweave/{task_id}` |
| Stitcher | `DELETE /api/v1/stitch/{task_id}` |
| Dreamer | `DELETE /api/v1/dream/{task_id}` |

#### 后台操作（必须执行）
1. 调用 `playback.release_playback_file(engine_id, path_id)` → **从 HoloWAN 删除回放文件**
2. 删除 Port1/Port2 上的 `AutoGenFor_{target_ip}` 流分类规则
3. 更新任务状态为 `completed`
4. **不清除服务端归档文件**

#### 成功响应（202 Accepted）
```json
{
  "task_id": "weave_a1b2c3",
  "status": "completed",
  "message": "仿真已停止，HoloWAN 设备资源已清理",
  "download_url": "/api/v1/weave/weave_a1b2c3/playback"
}
```

> ✅ 即使任务已停止，`download_url` 在 24 小时内仍有效

---

### 4. 下载回放文件（归档）

#### 路径与方法
| 入口类型 | HTTP 方法 + 路径 |
|--------|----------------|
| 自动选择 | `GET /api/v1/weave/{task_id}/playback` |
| Reweaver | `GET /api/v1/reweave/{task_id}/playback` |
| Stitcher | `GET /api/v1/stitch/{task_id}/playback` |
| Dreamer | `GET /api/v1/dream/{task_id}/playback` |

#### 响应
- **HTTP 状态**: `200 OK`
- **Content-Type**: `text/plain`
- **Body**: HoloWAN 回放文件内容（纯文本，UTF-8）

#### 生命周期
- 服务端生成后保存至临时目录
- **TTL = 24 小时**，过期自动删除
- 删除策略：后台定时任务每日清理

---

## 五、自动选择引擎逻辑（仅 `/weave` 使用）

服务内部根据 `weaving_pattern` 语法自动路由：

| Pattern 特征 | 选择引擎 |
|-------------|--------|
| 包含 `->` 且基于单 trace 重放 | `Reweaver` |
| 包含多个 trace 标识（如 `t0`, `t1`） | `Stitcher` |
| 完全由参数生成（如 `gaussian(delay=50, loss=0.1)`） | `Dreamer` |

> ⚠️ 若无法识别 → 返回 `400 Bad Request: Unsupported weaving pattern`

---

## 六、错误响应统一格式

| 状态码 | 响应体示例 | 触发条件 |
|--------|-----------|--------|
| `400` | `{"detail": "impairment_device.path_name is required"}` | 缺少必填字段 |
| `400` | `{"detail": "Path 'MyLink' not found on HoloWAN device"}` | Path 不存在 |
| `400` | `{"detail": "Unsupported weaving pattern for auto-selection"}` | 自动入口无法识别 pattern |
| `404` | `{"detail": "Task weave_xxx not found"}` | 任务 ID 不存在或路径不匹配 |
| `500` | `{"detail": "Failed to connect to 160.100.15.195:8080"}` | 设备连接失败 |

---

## 七、用户使用建议

| 场景 | 推荐入口 |
|------|--------|
| 快速测试，不确定用哪个引擎 | `POST /weave`（自动选择） |
| 明确使用重织（基于 trace） | `POST /reweave` |
| 拼接多条 trace | `POST /stitch` |
| 生成理想化损伤序列 | `POST /dream` |
| 需要长期运行实验 | 任一入口 + 记录 `task_id`，结束时务必 `DELETE` |

---

## 八、部署与维护

- **Base URL**: `http://<host>:8000/api/v1`
- **认证**: 无（假设部署在可信内网）
- **存储**: SQLite（轻量级任务状态持久化）
- **文件清理**: 后台任务每日凌晨清理超过 24 小时的回放文件

---