# TraceLoom（织径）

🧵 🌐 **TraceLoom（织径）**  
*Weaving programmable paths from real traces.*

🪡 🧷 **以实为丝，以律为梭，织就可编程之径**

---

## 欢迎来到 TraceLoom 文档

TraceLoom 从真实 HoloWAN 测量中提炼网络行为规律（【织律】），并将轨迹解构为可复用的【径元】。通过三种织径模式——重织（重组）、绣织（构造）、广织（生成）——合成高保真虚拟路径，注入 HoloWAN 后可驱动真实 App 产生自然协议行为。

## 文档导航

### 🎯 愿景层
- [为什么需要织虚？](00-philosophy/why-loomsnet.md) - 现网采集瓶颈与解决方案
- [命名与隐喻](00-philosophy/naming-and-metaphor.md) - “织虚”“元”“三重织境”的由来
- [验证哲学](00-philosophy/validation-philosophy.md) - 为什么“闭卷考试”是唯一标准？

### 🏗️ 架构层
- [整体架构](01-architecture/overview.md) - 数据流图与系统概览
- [Playback 底座](01-architecture/the-root.md) - 设计约束与真实数据源
- [【径元】切片逻辑](01-architecture/the-pathlet.md) - GMM 聚类细节与状态切片
- [织径模式](01-architecture/stages/)
  - [重织（重组）](01-architecture/stages/replace.md) - 拼接算法与平滑策略
  - [绣织（构造）](01-architecture/stages/craft.md) - 插值 + PSD 约束数学推导
  - [广织（生成）](01-architecture/stages/explore.md) - Diffusion 模型结构与采样策略
- [评估指标](01-architecture/validation-dimensions.md) - 时延/丢包率/可用带宽 各阶段评估指标定义

### 🛠️ 实现层
- [API 参考](02-implementation/api-reference.md) - 核心接口文档
- [HoloWAN 集成](02-implementation/holowan-integration.md) - 如何导出 .hwan 文件
- [回放文件格式](02-implementation/playback-format.md) - 回放文件格式规范
- [调试指南](02-implementation/debugging-guide.md) - 常见问题与解决方案

### 🚀 演进层
- [架构决策记录](03-evolution/design-decisions.md) - ADR 文档
- [发展路线图](03-evolution/roadmap.md) - 短期/长期计划
- [实验与探索](03-evolution/experiments/)
  - [GAN vs Diffusion](03-evolution/experiments/gan-vs-diffusion.md)
  - [状态标签粒度](03-evolution/experiments/state-label-granularity.md)

---

## 快速入门

要开始使用 TraceLoom，请遵循以下步骤：

1. **安装 TraceLoom**
   ```bash
   uv pip install -e ./third_party/holowan_python_api
   uv pip install -e .
   ```

2. **导入并使用**
   ```python
   import traceloom as tl
   
   # 重织：从文件
   tl.reweave("real.txt", output="reweave.txt")
   
   # 绣织：从织样
   tl.stitch("s0x2 -> s2x6", output="weak.txt")
   
   # 广织：生成幻径
   tl.dream("s0x2 -> s2x6", output="dreamed.txt")
   ```

---

## 核心特性

- **三种织径模式**：重织（重组）、绣织（构造）、广织（生成）
- **基于 GMM 的状态聚类**：自动识别网络状态，生成【织律】
- **扩散模型生成**：创建真实可信的【幻径】
- **HoloWAN 集成**：支持导出 .hwan 文件
- **闭卷验证**：确保生成轨迹的真实性和可靠性

## 项目结构

```
/Users/xiaotuanzi/PycharmProjects/traceloom/
├── .trae/               # Trae AI 配置文件
├── data/                # 数据目录
│   ├── outputs/         # 输出文件
│   └── raw/             # 原始数据
├── docs/                # 项目文档
│   ├── 00-philosophy/   # 愿景层文档
│   ├── 01-architecture/ # 架构层文档
│   ├── 02-implementation/ # 实现层文档
│   ├── 03-evolution/    # 演进层文档
│   ├── reference/       # 参考文档
│   └── index.md         # 文档首页
├── scripts/             # 示例脚本
├── src/                 # 源代码
│   └── traceloom/         # 主源码目录
│       ├── app/         # API 应用
│       ├── core/        # 核心功能
│       ├── io/          # 输入输出
│       ├── pipelines/   # 流水线
│       ├── simcore/     # 仿真核心
│       └── validation/  # 验证模块
├── tests/               # 测试代码
├── third_party/         # 第三方依赖
├── .gitignore           # Git 忽略文件
├── LICENSE              # 许可证
├── Makefile             # Make 配置
├── README.md            # 项目说明
├── install.sh           # 安装脚本
├── mkdocs.yml           # MkDocs 配置
├── pyproject.toml       # 项目配置
└── uv.lock              # uv 依赖锁
```

---

## 联系我们

- 📧 邮箱：traceloom@example.com
- 🔗 GitHub：[https://github.com/traceloom/traceloom](https://github.com/traceloom/traceloom)
- 📖 文档：[https://traceloom.readthedocs.io](https://traceloom.readthedocs.io)