# API 参考

## 核心数据结构



### 核心数据结构层次

#### BodyObservations

主体观测数据类，存储径元主体部分的网络参数数据，包含100个观测值（约10秒）。

##### 构造函数

```python
BodyObservations(
    observations: List[Observation]  # 观测数据列表，长度为100
)
```

**参数**：
- `observations`: 观测数据列表，长度为100，每个元素为Observation对象

**返回值**：
- `BodyObservations`: 主体观测数据实例

#### TailObservations

融尾观测数据类，存储径元融尾部分的网络参数数据，包含10个观测值（约1秒），用于径元之间的平滑过渡。

##### 构造函数

```python
TailObservations(
    observations: List[Observation]  # 观测数据列表，长度为10
)
```

**参数**：
- `observations`: 观测数据列表，长度为10，每个元素为Observation对象

**返回值**：
- `TailObservations`: 融尾观测数据实例

#### Observation

核心网络观测模型，存储单个时间点的网络参数数据。

##### 构造函数

```python
Observation(
    delay_up: float = 0.0,  # 上行延迟 (ms)
    delay_down: float = 0.0,  # 下行延迟 (ms)
    loss_up: float = 0.0,  # 上行丢包率
    loss_down: float = 0.0,  # 下行丢包率
    bw_up: float = 0.0,  # 上行带宽 (Mbps)
    bw_down: float = 0.0  # 下行带宽 (Mbps)
)
```

**参数**：
- `delay_up`: 上行延迟 (ms)
- `delay_down`: 下行延迟 (ms)
- `loss_up`: 上行丢包率
- `loss_down`: 下行丢包率
- `bw_up`: 上行带宽 (Mbps)
- `bw_down`: 下行带宽 (Mbps)

**返回值**：
- `Observation`: 网络观测数据实例

#### ContextValues

10秒时序序列统计值，从原始10秒上下文数据中提取的统计特征值。

##### 构造函数

```python
ContextValues(
    delay_up_mean: float,
    delay_up_std: float,
    delay_down_mean: float,
    delay_down_std: float,
    loss_up_mean: float,
    loss_up_max: float,
    loss_down_mean: float,
    loss_down_max: float,
    bw_up_mean: float,
    bw_up_max: float,
    bw_down_mean: float,
    bw_down_max: float
)
```

**参数**：
- `delay_up_mean`: 上行时延均值
- `delay_up_std`: 上行时延标准差
- `delay_down_mean`: 下行时延均值
- `delay_down_std`: 下行时延标准差
- `loss_up_mean`: 上行丢包率均值
- `loss_up_max`: 上行丢包率最大值
- `loss_down_mean`: 下行丢包率均值
- `loss_down_max`: 下行丢包率最大值
- `bw_up_mean`: 上行带宽均值
- `bw_up_max`: 上行带宽最大值
- `bw_down_mean`: 下行带宽均值
- `bw_down_max`: 下行带宽最大值

**返回值**：
- `ContextValues`: 10秒时序序列统计值实例

#### RawProfile

原始网络剖面数据类，用于拼接和进一步处理。

##### 构造函数

```python
RawProfile(
    trace_name: str,
    start_index: int,
    ctx_10s: BodyObservations,
    cont_1s: TailObservations,
    ctx_values: ContextValues,
    is_valid: bool = True
)
```

**参数**：
- `trace_name`: 轨迹名称
- `start_index`: 起始索引
- `ctx_10s`: 10秒主体观测数据
- `cont_1s`: 1秒融尾观测数据
- `ctx_values`: 10秒时序序列统计值
- `is_valid`: 是否有效，默认为True

**返回值**：
- `RawProfile`: 原始网络剖面实例

##### 方法

##### `to_dict() -> Dict`

转换为字典格式。

**返回值**：
- `Dict`: 原始网络剖面的字典表示

##### `from_dict(data: Dict) -> RawProfile`

从字典创建原始网络剖面。

**参数**：
- `data`: 包含原始网络剖面数据的字典

**返回值**：
- `RawProfile`: 原始网络剖面实例

##### `to_file(file_path: Path) -> None`

序列化到文件。

**参数**：
- `file_path`: 输出文件路径

##### `from_file(file_path: Path) -> RawProfile`

从文件反序列化。

**参数**：
- `file_path`: 输入文件路径

**返回值**：
- `RawProfile`: 原始网络剖面实例

#### NormalizedData

归一化后的数据类，存储经过全局标准化处理后的网络剖面数据。

##### 构造函数

```python
NormalizedData(
    ctx_10s: ContextData,     # 归一化后的10秒上下文数据
    cont_1s: ContinuationData  # 归一化后的1秒延续数据
)
```

**参数**：
- `ctx_10s`: 归一化后的10秒上下文数据
- `cont_1s`: 归一化后的1秒延续数据

**返回值**：
- `NormalizedData`: 归一化后的数据实例

#### FeaturesData

提取的特征数据类。

##### 构造函数

```python
FeaturesData(
    features_16d: np.ndarray  # 16维特征向量
)
```

**参数**：
- `features_16d`: 16维特征向量

**返回值**：
- `FeaturesData`: 特征数据实例

#### StateInfo

网络状态信息类。

##### 构造函数

```python
StateInfo(
    state_id: int = -1,
    state_name: str = "",
    is_pure: bool = False,
    state_proba: float = 0.0,
    top2_state_ids: List[int] = field(default_factory=list),
    top2_state_probas: List[float] = field(default_factory=list),
    base_state_id: int = -1
)
```

**参数**：
- `state_id`: 状态ID，默认为-1
- `state_name`: 状态名称，默认为空字符串
- `is_pure`: 是否为纯净状态，默认为False
- `state_proba`: 状态概率，默认为0.0
- `top2_state_ids`: 概率最高的两个基础状态ID，默认为空列表
- `top2_state_probas`: 对应概率，默认为空列表
- `base_state_id`: 主基础状态，默认为-1

**返回值**：
- `StateInfo`: 网络状态信息实例

#### ProcessedProfile

处理后的网络剖面数据类，包含原始数据、归一化数据、特征和状态信息。

##### 构造函数

```python
ProcessedProfile(
    raw_profile: RawProfile,
    normalized: NormalizedData,
    features: FeaturesData,
    state_info: StateInfo
)
```

**参数**：
- `raw_profile`: 关联的原始数据
- `normalized`: 归一化后的数据
- `features`: 提取的特征
- `state_info`: 状态信息

**返回值**：
- `ProcessedProfile`: 处理后的网络剖面实例

#### ProfileSequence

网络剖面序列数据类，用于管理多个相关的网络剖面。

##### 构造函数

```python
ProfileSequence(
    sequence_id: str,
    profiles: List[ProcessedProfile],
    metadata: Optional[Dict] = None
)
```

**参数**：
- `sequence_id`: 序列唯一标识符
- `profiles`: 处理后的网络剖面列表
- `metadata`: 附加元数据，默认为None

**返回值**：
- `ProfileSequence`: 网络剖面序列实例

## 核心接口

### 织径核心函数

TraceLoom 提供了三个核心织径函数，用于生成不同类型的网络路径：

#### reweave(input, output="output.txt")

**重织**：从真实 HoloWAN 文件提取并重组路径（【故径】）。

**参数**：
- `input` (str): 真实 HoloWAN 文件路径
- `output` (str or Path, optional): 输出文件路径，默认为"output.txt"

**返回值**：
- `dict`: 包含路径信息的字典，格式为：
  ```python
  {
      "path_id": str,        # 路径唯一标识符
      "duration_sec": int,   # 路径时长（秒）
      "state_sequence": str  # 状态序列，如 "s0x2 -> s2x6"
  }
  ```

**示例**：
```python
import traceloom as tl

# 从文件重织
result = tl.reweave(
    input="real.txt",
    output="reweave.txt"
)
print(result)
```

#### embroider(input, output="output.txt")

**绣织**：按织样构造高质量路径（【质径】）。

**参数**：
- `input` (str): 织样字符串，支持两种格式：
  - 紧凑文本格式："s0x2 -> s2x6"（状态名x时长倍数，时长倍数×10=实际秒数）
  - JSON格式：'[{"state": "s0", "duration": 20}, {"state": "s2", "duration": 60}]'
- `output` (str or Path, optional): 输出文件路径，默认为"output.txt"

**返回值**：
- `dict`: 包含路径信息的字典，格式同 `reweave` 函数

**示例**：
```python
import traceloom as tl

# 使用紧凑文本格式织样
result = tl.embroider(
    input="s0x2 -> s2x6",
    output="embroider.txt"
)

# 使用JSON格式织样
json_pattern = '[{"state": "s0", "duration": 20}, {"state": "s2", "duration": 60}]'
result = tl.embroider(
    input=json_pattern,
    output="json_pattern.txt"
)
```

#### dream(input, output="output.txt")

**广织**：生成全新的虚拟路径（【幻径】）。

**参数**：
- `input` (str): 织样字符串，格式同 `embroider` 函数
- `output` (str or Path, optional): 输出文件路径，默认为"output.txt"

**返回值**：
- `dict`: 包含路径信息的字典，格式同 `reweave` 函数

**示例**：
```python
import traceloom as tl

# 生成幻径
result = tl.dream(
    input="s0x2 -> s2x6",
    output="dreamed.txt"
)
```

## 数据处理接口

### NetworkProfileExtractor

网络剖面提取器，负责从DataFrame中提取结构化的RawProfile。

#### 构造函数

```python
NetworkProfileExtractor(
    window_context_size: int = settings.WINDOW_CONTEXT_SIZE,
    window_cont_size: int = settings.WINDOW_CONT_SIZE,
    sliding_step: int = settings.SLIDING_STEP
)
```

**参数**：
- `window_context_size`: 上下文窗口大小（行），默认为100
- `window_cont_size`: 延续窗口大小（行），默认为10
- `sliding_step`: 滑动步长（行），默认为50

**返回值**：
- `NetworkProfileExtractor`: 网络剖面提取器实例

#### 方法

##### `extract(df: pd.DataFrame, trace_name: str) -> List[RawProfile]`

从DataFrame中提取网络剖面。

**参数**：
- `df`: 包含网络数据的DataFrame，必须包含以下列：
  - raw_delay_up, raw_loss_up, raw_bw_up
  - raw_delay_down, raw_loss_down, raw_bw_down
- `trace_name`: 轨迹名称

**返回值**：
- `List[RawProfile]`: 提取的原始网络剖面列表

**示例**：
```python
extractor = NetworkProfileExtractor()
profiles = extractor.extract(df, trace_name="test_trace")
```

##### `scale_profiles(profiles: List[RawProfile], scaler: Any) -> List[RawProfile]`

归一化网络剖面数据。

归一化策略:
- Delay: log(1+x) 变换后使用 StandardScaler 归一化
- Loss: value / 100.0（线性归一化）
- Bandwidth: 保持原始值不变

**参数**：
- `profiles`: 原始网络剖面列表
- `scaler`: 归一化器对象（如sklearn.preprocessing.StandardScaler）

**返回值**：
- `List[RawProfile]`: 归一化后的网络剖面列表

**示例**：
```python
from sklearn.preprocessing import StandardScaler
scaler = StandardScaler()
scaled_profiles = extractor.scale_profiles(profiles, scaler)
```

##### `profiles_to_csv(profiles: List[RawProfile], output_path: Path) -> bool`

将网络剖面列表保存为CSV文件。

**参数**：
- `profiles`: 原始网络剖面列表
- `output_path`: 输出CSV文件路径

**返回值**：
- `bool`: 是否成功保存

**示例**：
```python
extractor.profiles_to_csv(profiles, Path("output.csv"))
```

##### `profiles_from_csv(csv_path: Path) -> List[RawProfile]`

从CSV文件中加载网络剖面。

**参数**：
- `csv_path`: CSV文件路径

**返回值**：
- `List[RawProfile]`: 加载的原始网络剖面列表

**示例**：
```python
profiles = extractor.profiles_from_csv(Path("profiles.csv"))
```

### 特征提取函数

提供网络状态特征提取的独立函数，支持RawProfile和ProcessedProfile。

#### `extract_16d_features(profile: Union[RawProfile, ProcessedProfile]) -> np.ndarray`

从网络剖面中提取16维特征。

**参数**：
- `profile`: 网络剖面实例，支持RawProfile和ProcessedProfile

**返回值**：
- `np.ndarray`: 16维特征向量

**示例**：
```python
from traceloom.simcore.pathlet.features import extract_16d_features
features = extract_16d_features(profile)  # profile可以是RawProfile或ProcessedProfile
```

#### `extract_features_batch(profiles: List[Union[RawProfile, ProcessedProfile]]) -> np.ndarray`

批量从网络剖面中提取16维特征。

**参数**：
- `profiles`: 网络剖面列表，支持RawProfile和ProcessedProfile

**返回值**：
- `np.ndarray`: 特征矩阵，形状为 (n_samples, 16)

**示例**：
```python
from traceloom.simcore.pathlet.features import extract_features_batch
features = extract_features_batch(profiles)  # profiles可以包含RawProfile或ProcessedProfile
```

### DataReader 类

#### DataReader.read()

读取网络轨迹数据。

**参数**：
- `file_path` (str): 轨迹文件路径

**返回值**：
- `pd.DataFrame`: 读取的数据

**示例**：
```python
from traceloom.data import DataReader

reader = DataReader()
data = reader.read("xichen_apartment.trace")
```

#### DataReader.read_directory()

读取目录下所有轨迹文件。

**参数**：
- `directory_path` (str): 目录路径
- `pattern` (str, optional): 文件匹配模式，默认为"*.trace"

**返回值**：
- `list`: 读取的数据列表

**示例**：
```python
data_list = reader.read_directory("data/traces")
```

### DataPreprocessor 类

#### DataPreprocessor.preprocess()

预处理网络轨迹数据。

**参数**：
- `data` (pd.DataFrame): 原始数据

**返回值**：
- `pd.DataFrame`: 预处理后的数据

**示例**：
```python
from traceloom.data import DataPreprocessor

preprocessor = DataPreprocessor()
processed_data = preprocessor.preprocess(data)
```

#### DataPreprocessor.segment()

分段网络轨迹数据。

**参数**：
- `data` (pd.DataFrame): 原始数据
- `segment_length` (int, optional): 分段长度（秒），默认为10

**返回值**：
- `list`: 分段后的数据列表

**示例**：
```python
segments = preprocessor.segment(data, segment_length=10)
```

## 模型接口

### GMMClusterer

GMM聚类器，用于对网络状态进行无监督聚类。

#### 构造函数

```python
GMMClusterer(
    n_components: int = 3,
    confidence_threshold: float = 0.85,
    random_state: int = 42
)
```

**参数**：
- `n_components`: 聚类数量，默认为3
- `confidence_threshold`: 纯净态置信度阈值，默认为0.85
- `random_state`: 随机种子，默认为42

**返回值**：
- `GMMClusterer`: GMM聚类器实例

#### 方法

##### `fit(profiles: List[Union[RawProfile, ProcessedProfile]]) -> None`

拟合GMM模型。

**参数**：
- `profiles`: 网络剖面列表，用于训练模型，支持RawProfile和ProcessedProfile

**返回值**：
- `None`

**示例**：
```python
clusterer = GMMClusterer(n_components=3)
clusterer.fit(train_profiles)  # train_profiles可以是RawProfile或ProcessedProfile列表
```

##### `predict(profiles: List[Union[RawProfile, ProcessedProfile]]) -> List[int]`

预测网络剖面所属的聚类。

**参数**：
- `profiles`: 网络剖面列表，用于预测，支持RawProfile和ProcessedProfile

**返回值**：
- `List[int]`: 每个剖面所属的聚类索引

**示例**：
```python
clusters = clusterer.predict(test_profiles)  # test_profiles可以是RawProfile或ProcessedProfile列表
```

##### `predict_proba(profiles: List[Union[RawProfile, ProcessedProfile]]) -> List[List[float]]`

预测网络剖面属于每个聚类的概率。

**参数**：
- `profiles`: 网络剖面列表，用于预测，支持RawProfile和ProcessedProfile

**返回值**：
- `List[List[float]]`: 每个剖面属于每个聚类的概率

**示例**：
```python
probabilities = clusterer.predict_proba(test_profiles)  # test_profiles可以是RawProfile或ProcessedProfile列表
```

##### `save(path: Path) -> None`

保存聚类模型。

**参数**：
- `path`: 保存路径

**返回值**：
- `None`

**示例**：
```python
clusterer.save(Path("gmm_model.joblib"))
```

##### `load(path: Path) -> GMMClusterer`

加载聚类模型。

**参数**：
- `path`: 模型路径

**返回值**：
- `GMMClusterer`: 加载的聚类器实例

**示例**：
```python
clusterer = GMMClusterer.load(Path("gmm_model.joblib"))
```

##### `fit_predict(profiles: List[Union[RawProfile, ProcessedProfile]]) -> Tuple[List[int], List[List[float]]]`

拟合模型并预测聚类和概率。

**参数**：
- `profiles`: 网络剖面列表，支持RawProfile和ProcessedProfile

**返回值**：
- `Tuple[List[int], List[List[float]]]`: 聚类结果和概率

**示例**：
```python
clusters, probabilities = clusterer.fit_predict(profiles)  # profiles可以是RawProfile或ProcessedProfile列表
```

### GMMModel 类

#### GMMModel.fit()

训练GMM模型。

**参数**：
- `data` (pd.DataFrame): 训练数据
- `n_components` (int, optional): 聚类数量，默认为5

**返回值**：
- `None`

**示例**：
```python
from traceloom.model import GMMModel

model = GMMModel(n_components=5)
model.fit(data)
```

#### GMMModel.predict()

预测网络状态。

**参数**：
- `data` (pd.DataFrame): 输入数据

**返回值**：
- `np.ndarray`: 预测的状态标签

**示例**：
```python
states = model.predict(data)
```

### StateNamer

状态命名与ID映射器，负责为网络状态生成有意义的名称和唯一ID。

#### 构造函数

```python
StateNamer()
```

**返回值**：
- `StateNamer`: 状态命名器实例

#### 方法

##### `assign_state(probabilities: List[float], confidence_threshold: float) -> Dict`

分配状态信息，包括状态ID、名称、是否为纯净态等。

**参数**：
- `probabilities`: 每个基础状态的概率列表
- `confidence_threshold`: 置信度阈值

**返回值**：
- `Dict`: 包含状态信息的字典，格式：
  ```python
  {
      "state_id": int,
      "state_name": str,
      "is_pure": bool,
      "state_proba": float,
      "top2_state_ids": List[int],
      "top2_state_probas": List[float],
      "base_state_id": int,
  }
  ```

**示例**：
```python
namer = StateNamer()
state_info = namer.assign_state([0.92, 0.05, 0.03], confidence_threshold=0.85)
```

##### `get_state_name(top_state_ids: List[int]) -> str`

获取状态名称。

**参数**：
- `top_state_ids`: 概率最高的状态ID列表

**返回值**：
- `str`: 状态名称

**示例**：
```python
state_name = namer.get_state_name([0])  # 返回 "stable"
mixed_name = namer.get_state_name([1, 2])  # 返回 "jittery/abnormal"
```

##### `get_state_id(top_state_ids: List[int]) -> int`

获取状态ID。

**参数**：
- `top_state_ids`: 概率最高的状态ID列表

**返回值**：
- `int`: 唯一的状态ID

**示例**：
```python
state_id = namer.get_state_id([0])  # 返回 0
mixed_id = namer.get_state_id([1, 2])  # 返回 3
```

##### `get_state_metadata() -> Dict`

获取状态元数据。

**返回值**：
- `Dict`: 状态元数据，包含所有状态的详细信息

**示例**：
```python
state_metadata = namer.get_state_metadata()
```

### TSNEVisualizer

t-SNE可视化器，用于生成网络状态的t-SNE可视化图。

#### 构造函数

```python
TSNEVisualizer(
    perplexity: int = 20,
    early_exaggeration: float = 10.0,
    learning_rate: float = 200.0,
    random_state: int = 42,
    max_iter: int = 1000
)
```

**参数**：
- `perplexity`: t-SNE perplexity参数，默认为20
- `early_exaggeration`: t-SNE early_exaggeration参数，默认为10.0
- `learning_rate`: t-SNE learning_rate参数，默认为200.0
- `random_state`: 随机种子，默认为42
- `max_iter`: t-SNE最大迭代次数，默认为1000

**返回值**：
- `TSNEVisualizer`: t-SNE可视化器实例

#### 方法

##### `_extract_features(self, profiles: List[Union[RawProfile, ProcessedProfile]]) -> np.ndarray`

从网络剖面列表中提取特征。

**参数**：
- `profiles`: 网络剖面列表，支持RawProfile和ProcessedProfile

**返回值**：
- `np.ndarray`: 特征矩阵，形状为 (n_samples, 16)

##### `_plot_tsne(self, tsne_results: np.ndarray, profiles: List[ProcessedProfile], state_metadata: Dict, title: str, output_path: Optional[Path], with_annotations: bool = False) -> None`

绘制t-SNE图。

**参数**：
- `tsne_results`: t-SNE降维后的特征向量
- `profiles`: 处理后的网络剖面列表（ProcessedProfile）
- `state_metadata`: 状态元数据，包含状态ID、名称、颜色等信息
- `title`: 图表标题
- `output_path`: 输出路径
- `with_annotations`: 是否添加注释，默认为False

##### `visualize(profiles: List[ProcessedProfile], state_metadata: Dict, output_path: Optional[Path] = None, title: str = "网络状态 t-SNE 可视化") -> np.ndarray`

生成t-SNE可视化图。

**参数**：
- `profiles`: 处理后的网络剖面列表（ProcessedProfile）
- `state_metadata`: 状态元数据，包含状态ID、名称、颜色等信息
- `output_path`: 输出路径，默认为None
- `title`: 图表标题，默认为"网络状态 t-SNE 可视化"

**返回值**：
- `np.ndarray`: t-SNE降维后的特征向量

**示例**：
```python
visualizer = TSNEVisualizer()
tsne_results = visualizer.visualize(
    profiles, 
    state_metadata, 
    Path("tsne_output.png"),
    title="网络状态 t-SNE 可视化"
)
```

### DiffusionModel 类

#### DiffusionModel.load()

加载预训练的Diffusion模型。

**参数**：
- `model_path` (str): 模型文件路径

**返回值**：
- `None`

**示例**：
```python
from traceloom.model import DiffusionModel

model = DiffusionModel()
model.load("models/diffusion_model.pt")
```

#### DiffusionModel.sample()

生成网络轨迹样本。

**参数**：
- `num_samples` (int, optional): 生成样本数量，默认为1
- `cond` (dict, optional): 条件采样参数

**返回值**：
- `list`: 生成的轨迹样本列表

**示例**：
```python
samples = model.sample(num_samples=3)
```

## 配置接口

### Settings 类

#### settings.get_config()

获取配置值。

**参数**：
- `key` (str): 配置键名

**返回值**：
- `Any`: 配置值

**示例**：
```python
from traceloom.core import settings

rtt_max = settings.get_config("DELAY_MAX")
```

#### settings.set_config()

设置配置值（运行时）。

**参数**：
- `key` (str): 配置键名
- `value` (Any): 配置值

**返回值**：
- `None`

**示例**：
```python
settings.set_config("LOG_LEVEL", "DEBUG")
```

## 异常接口

### TraceLoomBaseException

所有自定义异常的父类。

### ConfigError

配置错误，当配置文件读取或解析失败时抛出。

### DataError

数据错误，当数据格式、范围或内容不符合要求时抛出。

### ValidationError

验证错误，当参数或数据验证失败时抛出。

### NetworkParameterError

网络参数错误，当网络参数超出允许范围时抛出。

### TraceGenerationError

轨迹生成错误，当生成网络轨迹失败时抛出。

## 示例用法

### 完整示例

```python
import traceloom as tl

# 重织：从真实HoloWAN文件提取并重组路径
reweave_result = tl.reweave(
    input="data/raw/20251203_230356_b6x-playback.txt",
    output="reweave_path.txt"
)
print("Reweave result:", reweave_result)

# 绣织：按织样构造质径
embroider_result = tl.embroider(
    input="s0x2 -> s2x6",
    output="embroider_path.txt"
)
print("Embroider result:", embroider_result)

# 广织：生成幻径
dream_result = tl.dream(
    input="s0x2 -> s2x6",
    output="dream_path.txt"
)
print("Dream result:", dream_result)
```

## 最佳实践

1. **使用上下文管理器**：对于大型模型和数据集，使用上下文管理器确保资源正确释放
2. **处理异常**：捕获并处理可能的异常，提高代码的健壮性
3. **验证输入**：在调用API前验证输入参数，确保其符合要求
4. **使用配置**：通过配置接口获取和设置配置值，避免硬编码
5. **记录日志**：使用loguru记录关键操作，便于调试和监控