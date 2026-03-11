# Implementation Plan

## Services 层封装完善计划

### [Overview]

本计划旨在完善 RSS2Pod 项目的 Services 层架构，将 Pipeline 层中对底层模块的直接调用逐步迁移到 Services 层，根据 `.clinerules/noLogicinCli.md` 规则实现前后端分离。

经过调查发现：
- Feed 模块已完成 Services 层封装
- LLM、TTS、Fever 模块已有基础 Services 层
- Database 模块缺失 Services 层封装
- Pipeline 层仍存在对底层模块的多处直接调用

实施优先级：Database > LLM > TTS > Fever > Orchestrator

---

### [Types]

#### 服务结果类型 (沿用现有 ServiceResult)
```python
@dataclass
class ServiceResult:
    success: bool
    data: Any = None
    error_message: str = None
    metadata: Dict = field(default_factory=dict)
```

#### 数据库服务方法签名
```python
class DatabaseService(BaseService):
    def get_group(self, group_id: str) -> ServiceResult
    def create_group(self, group: Group) -> ServiceResult
    def update_group(self, group: Group) -> ServiceResult
    def delete_group(self, group_id: str) -> ServiceResult
    def add_article(self, article: Article) -> ServiceResult
    def get_articles_by_status(self, status: str, limit: int) -> ServiceResult
    def update_article_status(self, article_id: str, status: str) -> ServiceResult
    def add_episode(self, episode: Episode) -> ServiceResult
    def get_episode(self, episode_id: str) -> ServiceResult
    def get_episodes_by_group(self, group_id: str, limit: int) -> ServiceResult
    def add_source_summary(self, summary: SourceSummary) -> ServiceResult
    def get_stats(self) -> ServiceResult
```

#### LLM 服务增强方法签名
```python
class LLMService(BaseService):
    # 现有方法保持不变
    # 新增方法：
    def get_prompt_manager(self) -> PromptManager
    def get_prompt_template(self, template_type: str, group_id: str, group_overrides: Dict) -> str
```

#### TTS 服务增强方法签名
```python
class TTSService(BaseService):
    # 现有方法保持不变
    # 新增方法：
    def get_adapter(self, config_path: str = None)
    def synthesize_with_speed(self, segments: List[Dict], speed: float, output_dir: str) -> ServiceResult
    def synthesize_segments_advanced(self, segments: List[Dict], config: Dict) -> ServiceResult
```

#### Fever 服务增强方法签名
```python
class FeverService(BaseService):
    # 现有方法保持不变
    # 新增方法：
    def fetch_articles(self, rss_sources: List[str], since_id: str, force: bool, limit: int) -> ServiceResult
    def get_feed_map(self, rss_sources: List[str]) -> ServiceResult
```

---

### [Files]

#### 新建文件
| 文件路径 | 目的 |
|----------|------|
| `rss2pod/services/database_service.py` | 数据库服务封装 |
| `rss2pod/services/pipeline/database_service.py` | Pipeline 专用数据库服务（可选，如果需要更精细控制） |

#### 修改文件
| 文件路径 | 修改内容 |
|----------|----------|
| `rss2pod/services/llm_service.py` | 添加 get_prompt_manager(), get_prompt_template() 方法 |
| `rss2pod/services/tts_service.py` | 添加 get_adapter(), synthesize_with_speed(), synthesize_segments_advanced() 方法 |
| `rss2pod/services/fever_service.py` | 添加 fetch_articles(), get_feed_map() 方法 |
| `rss2pod/services/pipeline/pipeline_orchestrator.py` | 移除直接导入，改为调用 Services 层 |
| `rss2pod/services/pipeline/group_processor.py` | 移除直接导入 database.models，改为使用 Services 层 |

---

### [Functions]

#### 新建函数
| 函数名 | 文件 | 功能 |
|--------|------|------|
| `DatabaseService` 类 | `services/database_service.py` | 数据库服务封装类 |
| `get_database_service()` | `services/__init__.py` | 获取数据库服务实例的便捷函数 |

#### 修改函数
| 函数名 | 文件 | 修改内容 |
|--------|------|----------|
| `PipelineOrchestrator.__init__()` | `pipeline/pipeline_orchestrator.py` | 添加 database_service 属性 |
| `PipelineOrchestrator._fetch_articles()` | `pipeline/pipeline_orchestrator.py` | 改为调用 FeverService.fetch_articles() |
| `PipelineOrchestrator._get_tts_adapter()` | `pipeline/pipeline_orchestrator.py` | 改为调用 TTSService.get_adapter() |
| `PipelineOrchestrator._synthesize_audio()` | `pipeline/pipeline_orchestrator.py` | 改为调用 TTSService 的高级方法 |
| `PipelineOrchestrator._save_episode()` | `pipeline/pipeline_orchestrator.py` | 改为调用 DatabaseService |
| `PipelineOrchestrator._save_source_summary()` | `pipeline/pipeline_orchestrator.py` | 改为调用 DatabaseService |
| `PipelineOrchestrator._update_article_status()` | `pipeline/pipeline_orchestrator.py` | 改为调用 DatabaseService |
| `GroupProcessor.__init__()` | `pipeline/group_processor.py` | 移除直接导入 DatabaseManager |
| `GroupProcessor.process()` | `pipeline/group_processor.py` | 改为使用 DatabaseService |

#### 待移除的直接导入 (迁移完成后)
```python
# 从 pipeline_orchestrator.py 移除:
from database.models import DatabaseManager, Group, Article, SourceSummary
from llm.prompt_manager import get_prompt_manager, PromptManager
from tts.adapter import get_adapter_from_tts_config
from tts.audio_speed import AudioSpeedProcessor
from tts.audio_assembler import AudioAssembler, AudioRole, AssemblyConfig
from fetcher.fever_client import FeverClient, FeverCredentials
from database.models import Episode

# 从 group_processor.py 移除:
from database.models import DatabaseManager, Group
from fetcher.fever_cache import FeverCacheManager
from fetcher.fever_client import FeverClient, FeverCredentials
from database.models import DatabaseManager
```

---

### [Classes]

#### 新建类
| 类名 | 文件 | 说明 |
|------|------|------|
| `DatabaseService` | `services/database_service.py` | 继承 BaseService，封装所有数据库 CRUD 操作 |

#### 修改类
| 类名 | 文件 | 修改内容 |
|------|------|----------|
| `LLMService` | `services/llm_service.py` | 添加 prompt_manager 相关方法 |
| `TTSService` | `services/tts_service.py` | 添加 adapter 和高级合成方法 |
| `FeverService` | `services/fever_service.py` | 添加文章获取方法 |
| `PipelineOrchestrator` | `pipeline/pipeline_orchestrator.py` | 使用 Services 层替代直接导入 |
| `GroupProcessor` | `pipeline/group_processor.py` | 使用 Services 层替代直接导入 |

---

### [Dependencies]

#### 现有依赖（保持不变）
- `database.models` - 现有数据库模型
- `llm.llm_client` - LLM 客户端
- `llm.prompt_manager` - Prompt 管理器
- `llm.group_aggregator` - 组级聚合器
- `tts.siliconflow_provider` - TTS 提供商
- `tts.adapter` - TTS 适配器
- `tts.audio_assembler` - 音频组装器
- `tts.audio_speed` - 音频调速
- `fetcher.fever_client` - Fever API 客户端
- `fetcher.fever_cache` - Fever 缓存管理器
- `feed.feed_manager` - Feed 管理器
- `orchestrator.state_manager` - 状态管理器

#### 无需新增依赖

---

### [Testing]

#### 测试策略
1. **单元测试**：为每个新服务方法编写单元测试
2. **集成测试**：使用现有 Pipeline 进行端到端测试
3. **回归测试**：确保现有功能不受影响

#### 测试文件位置
- `rss2pod/tests/test_database_service.py` (新建)
- `rss2pod/tests/test_llm_service.py` (扩展)
- `rss2pod/tests/test_tts_service.py` (扩展)
- `rss2pod/tests/test_fever_service.py` (扩展)

#### 验证方法
1. 运行现有 Pipeline 测试
2. 检查 CLI 命令是否正常工作
3. 验证 RSS Feed 生成是否正确

---

### [Implementation Order]

#### 阶段 1：DatabaseService 创建（高优先级）
1. [ ] 创建 `services/database_service.py`，定义 DatabaseService 类
2. [ ] 实现基本的 CRUD 方法
3. [ ] 在 `services/__init__.py` 中导出
4. [ ] 测试基本功能

#### 阶段 2：LLMService 增强（中优先级）
5. [ ] 在 LLMService 中添加 `get_prompt_manager()` 方法
6. [ ] 添加 `get_prompt_template()` 方法
7. [ ] 更新 Pipeline 中的调用

#### 阶段 3：TTSService 增强（中优先级）
8. [ ] 在 TTSService 中添加 `get_adapter()` 方法
9. [ ] 添加 `synthesize_with_speed()` 方法
10. [ ] 添加 `synthesize_segments_advanced()` 方法
11. [ ] 更新 Pipeline 中的调用

#### 阶段 4：FeverService 增强（中优先级）
12. [ ] 在 FeverService 中添加 `fetch_articles()` 方法
13. [ ] 添加 `get_feed_map()` 方法
14. [ ] 更新 Pipeline 中的调用

#### 阶段 5：Pipeline 重构（整合）
15. [ ] 更新 `pipeline_orchestrator.py` 使用 Services 层
16. [ ] 更新 `group_processor.py` 使用 Services 层
17. [ ] 移除不再需要的直接导入
18. [ ] 全面测试和验证

#### 阶段 6：清理和文档（低优先级）
19. [ ] 更新相关文档
20. [ ] 添加单元测试

---

### 实施注意事项

1. **向后兼容**：保持现有接口不变，新方法作为增强
2. **逐步迁移**：每个阶段完成后进行测试验证
3. **错误处理**：确保 Services 层有完善的错误处理
4. **日志记录**：保持现有的日志级别和格式
5. **配置管理**：Services 层通过 BaseService 继承配置管理能力
