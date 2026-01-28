# HoloWAN 集成



## HoloWAN管理器

### 概述

重构后的HoloWANManager类封装了与HoloWAN设备的交互逻辑，提供简洁的API用于管理HoloWAN引擎、分类规则和回放文件。该类实现了资源的自动管理和清理，简化了HoloWAN交互流程。

### 配置

在`src/traceloom/core/config.py`中可以配置HoloWAN连接信息：

```python
# HoloWAN配置
HOLOWAN_IP: str = "160.100.15.195"  # HoloWAN服务器IP地址
HOLOWAN_PORT: str = "8080"  # HoloWAN服务器端口
```

### 主要功能

HoloWANManager类提供了以下核心功能：

1. **引擎管理**：初始化引擎连接，更新引擎状态
2. **路径管理**：查找指定名称的虚拟链路
3. **规则管理**：创建、应用和移除分类规则
4. **回放管理**：上传、应用、释放和删除回放文件
5. **资源清理**：自动清理资源，确保系统状态一致性

### 使用示例

以下是使用HoloWANManager类执行完整HoloWAN交互流程的示例：

```python
from traceloom.io.holowan import HoloWANManager

# 初始化HoloWAN管理器（引擎ID由使用者传入）
holowan_manager = HoloWANManager(engine_id=1)

# 设置分类规则
if holowan_manager.setup_rules("TraceLoom", "10.10.10.10"):
    print("✅ 分类规则设置成功")

# 应用回放文件
if holowan_manager.apply_playback("../output/holowan/sim_task_20260122_103424_udw81q.txt"):
    print("✅ 回放文件应用成功")

# 执行业务逻辑
# TODO: 添加您的业务逻辑

# 清理资源
holowan_manager.cleanup("10.10.10.10", "sim_task_20260122_103424_udw81q.txt")
```

### 方法说明

#### 初始化

```python
def __init__(self, engine_id: int):
    """
    初始化HoloWAN管理器
    
    Args:
        engine_id: HoloWAN引擎ID
    """
```

#### 设置分类规则

```python
def setup_rules(self, path_name: str, target_ip: str, label_prefix: str = "AutoGen") -> bool:
    """
    设置分类规则
    
    Args:
        path_name: 路径名称
        target_ip: 目标IP地址
        label_prefix: 规则标签前缀，默认为"AutoGen"
    
    Returns:
        bool: 设置是否成功
    """
```

#### 应用回放文件

```python
def apply_playback(self, playback_file_path: str) -> bool:
    """
    应用回放文件
    
    Args:
        playback_file_path: 本地回放文件路径
    
    Returns:
        bool: 应用是否成功
    """
```

#### 清理资源

```python
def cleanup(self, target_ip: str, playback_name: str, label_prefix: str = "AutoGen") -> bool:
    """
    清理资源
    
    Args:
        target_ip: 目标IP地址
        playback_name: 回放文件名称
        label_prefix: 规则标签前缀，默认为"AutoGen"
    
    Returns:
        bool: 清理是否成功
    """
```

## 总结

织虚与HoloWAN的集成实现了网络轨迹生成与虚拟网络模拟的无缝衔接。通过将织虚生成的高保真网络轨迹导出为.hwan格式，可以在HoloWAN上创建可编程的虚拟网络链路，用于测试和验证网络应用在各种网络条件下的表现。

重构后的HoloWANManager类进一步简化了与HoloWAN的交互，提供了更加简洁和可靠的API，便于开发者快速集成HoloWAN功能到自己的应用中。