# 🧵 TraceLoom（织径）  
> **从真实轨迹中，织就 App 信以为真的网络之径** 🪡

> **观元见真，径元造实**  
> **织律识态，织样定序**  
> **重织复现，广织推演，绣织精修**

> 以【径元】为丝，以【织律】为梭，织可编程之径  
> 不生成流量 —— 而是生成 **App 信以为真的网络路径**。

TraceLoom 从真实 HoloWAN 测量中提炼网络行为规律（【织律】），并将轨迹解构为可复用的【径元】。通过三种织径模式——**重织**（重组）、**绣织**（构造）、**广织**（生成）——合成高保真虚拟路径，注入 HoloWAN 后可驱动真实 App 产生自然协议行为。

✅ 破解 QoE 数据三大瓶颈：**成本高、覆盖窄、样本稀疏**。

---

## 🎭 三重织径 · 三重境界

| 模式 | 口诀 | 核心能力 |
|------|------|--------|
| **重织**`reweave` | **以真复真** | 将真实轨迹解构为【径元】丝线，依新【织样】重编，重现多样化【故径】- 所有片段均来自真实观测- 支持任意编辑织样（如 `s0x2 -> s2x3`）- 拼接采用 **【融尾】技术**：动态对齐 + Hermite 插值，保障六维物理连续性 |
| **绣织**`stitch` | **于真饰真** | 在关键位置精工调控，绣织一段高丢包、低带宽的【质径】- 按需拉伸特定状态（如持续弱网60秒）- 插值算法：Hermite 平滑 + PSD 约束，确保合理性 |
| **广织**`dream` | **依律生新** | 挥洒算法想象力，广织千万条未历之【幻径】- 基于生成模型（如 Diffusion）- 在【织律】约束下探索极端场景- 采样策略确保符合物理边界与协议响应 |

> **重织以复现 · 绣织以控因 · 广织以探界**

---

## 🔁 智能输入 · 一参通三态

所有模式仅需一个 `input` 参数，系统自动识别类型：

- **HoloWAN 文件路径或内容**  
  （字符串以 `.txt` 结尾，或包含多行数字）
- **织样字符串**  
  （如 `"s0x2 -> s2x6"`，含 `->`）
- **StateSequence 对象**  
  （程序化构建）

### 示例
```python
tl.reweave("real.txt")               # 文件 → 重织
tl.stitch("s0x2 -> s2x6")        # 字符串 → 绣织
tl.dream(my_state_seq)              # 对象 → 广织
```

> **判断优先级**：对象 > 文件路径 > 织样字符串。若歧义，优先视为文件。

---

## 📤 输出规范

- 标准 HoloWAN `.txt` 文件（6 列，10 Hz）
- 自带【织样】注释（便于溯源）：
  ```txt
  # TraceLoom v1.0 | Mode: reweave
  # State Sequence: s0x2 -> s2x6
  # Duration: 80 sec
  32.5,0.0,18.7,30.1,0.0,20.3
  ...
  ```
- **时长精确**：每 `sxK` 对应 `K × 10` 秒

---

## 🌐 API 调用（远程织径）

```bash
# 重织：上传真实轨迹
curl -X POST https://traceloom.local/api/v1/weave \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "reweave",
    "input": "UEsDBBQACAgIAF..."   # base64 HoloWAN content
  }'

# 广织：基于织样生成幻径
curl -X POST https://traceloom.local/api/v1/weave \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "dream",
    "input": "s0x2 -> s2x6"
  }'
```

**返回**：
```json
{
  "path_id": "tl_20260126_xyz",
  "download_url": "/api/v1/paths/tl_20260126_xyz/download",
  "state_sequence": "s0x2 -> s2x6",
  "duration_sec": 80
}
```

> **支持模式**：`reweave`（重织）、`stitch`（绣织）、`dream`（广织）

---

## 🧵 核心术语体系

| 中文 | 英文 | 说明 |
|------|------|------|
| 【观元】 | `Observation` | **瞬时快照**：单点 `(rtt, loss, bw)`，感知网络之原子 |
| 【径元】 | `Pathlet` | **11秒丝线**：10秒【主干】 + 1秒【融尾】，编织之基本单元 |
| 【主干】 | `Body` | **状态主体**：前 10 秒（100 个【观元】），代表该状态的典型行为 |
| 【融尾】 | `Tail Blend` | **融合尾段**：后 1 秒（10 个【观元】），用于拼接时平滑过渡，通过动态对齐与 Hermite 插值实现六维连续 |
| 【织律】 | `WeavingLaw` | **状态之规**：GMM模型，赋予 `s0/s2` 等语义 |
| 【织样】 | `Pattern` | **编织图样**：如 `"s0x2 -> s2x3"`，指令序列 |
| 【织机】 | `Weaver` | **生成之器**：未来模块，依律生新径 |

> **十秒主干立其形，一秒融尾续其脉**  
> **【观元】见真，【径元】造实**  
> **【织律】识万象，【织机】生万径**

---

## 💻 快速开始

### 安装
```bash
uv pip install -e ./third_party/holowan_python_api
uv pip install -e .
```

### 使用
```python
import traceloom as tl

# 重织：从文件
tl.reweave("real.txt", output_file="reweave.txt")

# 绣织：从织样
tl.stitch("s0x2 -> s2x6", output_file="weak.txt")

# 广织：生成幻径
tl.dream("s0x2 -> s2x6", output_file="dreamed.txt")
```

> **函数签名**：`func(input, output_file="output.txt")`  
> **返回**：`{"path_id": "...", "duration_sec": 80, "state_sequence": "s0x2 -> s2x6"}`

---

> 🧵 **TraceLoom（织径）：三元织虚实，万径入真模**  
> **观元见真，径元造实；织律识态，织样定序**  
> 你并非在模拟网络——而是在**织一条 App 信以为真的路**。