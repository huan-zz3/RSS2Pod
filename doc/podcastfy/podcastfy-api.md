# Podcastfy API 架构文档

## 概述

Podcastfy 是一个开源的播客生成服务，利用生成式 AI 将多模态内容（文本、图像、网站、YouTube 视频、PDF）转换为引人入胜的多语言音频对话。

### 核心功能

- **多模态输入支持**: 网站、YouTube 视频、PDF 文档、图像、原始文本
- **多 LLM 后端**: Google Gemini、OpenAI GPT、Anthropic Claude、本地 Llamafile
- **多 TTS 提供者**: OpenAI、ElevenLabs、Microsoft Edge、Google Gemini（单/多说话人）
- **多语言支持**: 英语、法语、葡萄牙语等
- **长短格式**: 支持短视频（2-5 分钟）和长视频（30+ 分钟）播客

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Podcastfy 系统架构                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │   内容提取    │ ──→ │   内容生成    │ ──→ │   语音合成    │    │
│  │  Extractor   │     │   Generator  │     │     TTS      │    │
│  └──────────────┘     └──────────────┘     └──────────────┘    │
│         │                    │                    │             │
│         ▼                    ▼                    ▼             │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐    │
│  │ - Website    │     │ - LLM Backend│     │ - OpenAI     │    │
│  │ - YouTube    │     │ - Prompts    │     │ - ElevenLabs │    │
│  │ - PDF        │     │ - Strategies │     │ - Edge       │    │
│  │ - Images     │     │ - Longform   │     │ - Gemini     │    │
│  └──────────────┘     └──────────────┘     └──────────────┘    │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                          API 层 (FastAPI)                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  POST /generate  │  GET /audio/{filename}  │  GET /health │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 项目结构

```
thirdparty/podcastfy/
├── podcastfy/
│   ├── __init__.py
│   ├── client.py                 # Python 客户端 API
│   ├── content_generator.py      # LLM 内容生成器
│   ├── text_to_speech.py         # TTS 转换引擎
│   ├── config.yaml               # 主配置文件
│   ├── conversation_config.yaml  # 对话配置
│   │
│   ├── api/
│   │   └── fast_app.py           # FastAPI REST 服务
│   │
│   ├── content_parser/           # 内容解析模块
│   │   ├── __init__.py
│   │   ├── content_extractor.py  # 内容提取器（统一入口）
│   │   ├── website_extractor.py  # 网站内容提取
│   │   ├── youtube_transcriber.py# YouTube 字幕提取
│   │   └── pdf_extractor.py      # PDF 内容提取
│   │
│   ├── tts/                      # TTS 提供者模块
│   │   ├── __init__.py
│   │   ├── base.py               # TTS 抽象基类
│   │   ├── factory.py            # TTS 工厂类
│   │   └── providers/
│   │       ├── __init__.py
│   │       ├── openai.py         # OpenAI TTS
│   │       ├── elevenlabs.py     # ElevenLabs TTS
│   │       ├── edge.py           # Microsoft Edge TTS
│   │       ├── gemini.py         # Google Gemini TTS
│   │       └── geminimulti.py    # Google Gemini Multi-Speaker TTS
│   │
│   └── utils/
│       ├── config.py             # 配置加载
│       ├── config_conversation.py# 对话配置
│       └── logger.py             # 日志配置
│
├── tests/                        # 测试套件
├── usage/                        # 使用文档
└── docs/                         # Sphinx 文档
```

---

## REST API 端点

### 基础信息

| 属性 | 值 |
|------|-----|
| **基础 URL** | `http://localhost:8000` |
| **API 类型** | RESTful JSON |
| **认证方式** | API Keys（通过请求体传递） |
| **内容类型** | `application/json` |

---

### POST /generate

生成播客音频的主要端点。

#### 请求参数

```json
{
  "generate_podcast": true,
  "google_key": "YOUR_GEMINI_API_KEY",
  "openai_key": "YOUR_OPENAI_API_KEY",
  "elevenlabs_key": "YOUR_ELEVENLABS_API_KEY",
  "urls": ["https://example.com/article"],
  "name": "Podcast Name",
  "tagline": "Your podcast tagline",
  "creativity": 0.7,
  "conversation_style": ["engaging", "informative", "storytelling"],
  "roles_person1": "main summarizer",
  "roles_person2": "main inquisitor",
  "dialogue_structure": ["Introduction", "Summary", "Call to Action"],
  "tts_model": "openai",
  "is_long_form": false,
  "engagement_techniques": ["questions", "examples", "analogies", "humor"],
  "user_instructions": "Focus on storytelling",
  "output_language": "English",
  "voices": {
    "question": "voice_id_1",
    "answer": "voice_id_2"
  }
}
```

#### 参数详解

| 参数 | 类型 | 必填 | 默认值 | 描述 |
|------|------|------|--------|------|
| `generate_podcast` | boolean | 否 | true | 是否生成音频（false 仅生成转录） |
| `google_key` | string | 条件 | - | Google Gemini API Key |
| `openai_key` | string | 条件 | - | OpenAI API Key |
| `elevenlabs_key` | string | 条件 | - | ElevenLabs API Key |
| `urls` | array | 条件 | [] | 要处理的 URL 列表 |
| `name` | string | 否 | "PODCASTFY" | 播客名称 |
| `tagline` | string | 否 | "YOUR PERSONAL GenAI PODCAST" | 播客标语 |
| `creativity` | float | 否 | 0.7 | 创意程度 (0-1) |
| `conversation_style` | array | 否 | ["engaging"] | 对话风格标签 |
| `roles_person1` | string | 否 | "main summarizer" | 说话人 1 角色 |
| `roles_person2` | string | 否 | "questioner" | 说话人 2 角色 |
| `dialogue_structure` | array | 否 | ["Introduction", "Content", "Conclusion"] | 对话结构 |
| `tts_model` | string | 否 | "openai" | TTS 模型选择 |
| `is_long_form` | boolean | 否 | false | 是否生成长格式内容 |
| `engagement_techniques` | array | 否 | [] | 互动技巧列表 |
| `user_instructions` | string | 否 | "" | 用户自定义指令 |
| `output_language` | string | 否 | "English" | 输出语言 |
| `voices` | object | 否 | 使用默认 | 自定义声音配置 |

#### TTS 模型选项

| 值 | 提供者 | 描述 |
|-----|--------|------|
| `openai` | OpenAI | 默认选项，高质量语音 |
| `elevenlabs` | ElevenLabs | 逼真的人声 |
| `edge` | Microsoft Edge | 免费 TTS 选项 |
| `gemini` | Google | Google 单说话人模型 |
| `geminimulti` | Google | Google 多说话人模型（推荐） |

#### 响应

**成功响应 (200 OK):**

```json
{
  "audioUrl": "/audio/podcast_abc123def456.mp3"
}
```

**错误响应 (500 Internal Server Error):**

```json
{
  "detail": "错误描述信息"
}
```

---

### GET /audio/{filename}

获取生成的音频文件。

#### 路径参数

| 参数 | 类型 | 描述 |
|------|------|------|
| `filename` | string | 音频文件名（如：`podcast_abc123.mp3`） |

#### 响应

- **内容类型**: `audio/mpeg`
- **格式**: MP3
- **比特率**: 320kbps

---

### GET /health

健康检查端点。

#### 响应

```json
{
  "status": "healthy"
}
```

---

## Python 客户端 API

### 核心函数：`generate_podcast()`

```python
from podcastfy.client import generate_podcast

audio_file = generate_podcast(
    urls=["https://example.com/article"],
    tts_model="geminimulti",
    conversation_config=custom_config,
    longform=False
)
```

### 函数签名

```python
def generate_podcast(
    urls: Optional[List[str]] = None,
    url_file: Optional[str] = None,
    transcript_file: Optional[str] = None,
    tts_model: Optional[str] = None,
    transcript_only: bool = False,
    config: Optional[Dict[str, Any]] = None,
    conversation_config: Optional[Dict[str, Any]] = None,
    image_paths: Optional[List[str]] = None,
    is_local: bool = False,
    text: Optional[str] = None,
    llm_model_name: Optional[str] = None,
    api_key_label: Optional[str] = None,
    topic: Optional[str] = None,
    longform: bool = False,
) -> Optional[str]
```

### 参数详解

| 参数 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `urls` | List[str] | None | 要处理的 URL 列表 |
| `url_file` | str | None | 包含 URL 的文件路径（每行一个） |
| `transcript_file` | str | None | 现有转录文件路径 |
| `tts_model` | str | "openai" | TTS 模型选择 |
| `transcript_only` | bool | False | 仅生成转录，不生成音频 |
| `config` | Dict | None | 用户配置字典 |
| `conversation_config` | Dict | None | 对话配置字典 |
| `image_paths` | List[str] | None | 图像文件路径列表 |
| `is_local` | bool | False | 使用本地 LLM |
| `text` | str | None | 原始文本输入 |
| `llm_model_name` | str | None | LLM 模型名称 |
| `api_key_label` | str | None | API Key 环境变量名 |
| `topic` | str | None | 生成播客的主题 |
| `longform` | bool | False | 生成长格式内容 |

### 返回值

- **成功**: 生成的音频文件路径（字符串）
- **transcript_only=True**: 转录文件路径（字符串）

---

## 内容提取器 (ContentExtractor)

### 类结构

```python
class ContentExtractor:
    def __init__(self)
    def is_url(self, source: str) -> bool
    def extract_content(self, source: str) -> str
    def generate_topic_content(self, topic: str) -> str
```

### 支持的输入类型

| 类型 | 检测方式 | 提取器 |
|------|----------|--------|
| **PDF** | `.pdf` 扩展名 | `PDFExtractor` |
| **YouTube** | URL 包含 youtube 模式 | `YouTubeTranscriber` |
| **网站** | 有效 URL | `WebsiteExtractor` |
| **主题** | 文本输入 | Gemini Google Search |

### 使用示例

```python
from podcastfy.content_parser.content_extractor import ContentExtractor

extractor = ContentExtractor()

# 提取网站内容
content = extractor.extract_content("https://example.com")

# 提取 YouTube 字幕
transcript = extractor.extract_content("https://youtube.com/watch?v=xxx")

# 提取 PDF 内容
pdf_content = extractor.extract_content("./document.pdf")

# 基于主题生成内容
topic_content = extractor.generate_topic_content("AI in Healthcare")
```

---

## 内容生成器 (ContentGenerator)

### 类结构

```python
class ContentGenerator:
    def __init__(
        self,
        is_local: bool = False,
        model_name: str = "gemini-2.5-flash",
        api_key_label: str = "GEMINI_API_KEY",
        conversation_config: Optional[Dict[str, Any]] = None
    )
    
    def generate_qa_content(
        self,
        input_texts: str = "",
        image_file_paths: List[str] = [],
        output_filepath: Optional[str] = None,
        longform: bool = False
    ) -> str
```

### LLM 后端支持

```python
class LLMBackend:
    """支持多种 LLM 后端"""
    
    # Google Gemini
    ChatGoogleGenerativeAI
    
    # OpenAI / Anthropic / 其他 (通过 LiteLLM)
    ChatLiteLLM
    
    # 本地模型 (通过 Llamafile)
    Llamafile
```

### 内容生成策略

| 策略 | 描述 | 适用场景 |
|------|------|----------|
| `StandardContentStrategy` | 标准长度内容生成 | 短文本、URL、图像 |
| `LongFormContentStrategy` | 长格式内容生成 | 书籍、长文档 |

### 长格式生成技术

使用 **"Content Chunking with Contextual Linking"** 技术：

1. 将输入内容分块
2. 为每个块生成对话
3. 维护上下文链接确保连贯性
4. 拼接所有部分

```python
# 长格式配置参数
config = {
    "max_num_chunks": 7,    # 最大分块数
    "min_chunk_size": 600   # 最小块大小（字符）
}
```

---

## 语音合成 (TextToSpeech)

### 类结构

```python
class TextToSpeech:
    def __init__(
        self,
        model: str = "openai",
        api_key: Optional[str] = None,
        conversation_config: Optional[Dict[str, Any]] = None
    )
    
    def convert_to_speech(self, text: str, output_file: str) -> None
```

### TTS 工厂模式

```python
class TTSProviderFactory:
    _providers = {
        'elevenlabs': ElevenLabsTTS,
        'openai': OpenAITTS,
        'edge': EdgeTTS,
        'gemini': GeminiTTS,
        'geminimulti': GeminiMultiTTS
    }
```

### TTS 提供者基类

```python
class TTSProvider(ABC):
    @abstractmethod
    def generate_audio(self, text: str, voice: str, model: str, voice2: str) -> bytes
    
    def get_supported_tags(self) -> List[str]
    def validate_parameters(self, text: str, voice: str, model: str) -> None
    def split_qa(self, input_text: str, ending_message: str, tags: List[str]) -> List[Tuple[str, str]]
    def clean_tss_markup(self, input_text: str, tags: List[str]) -> str
```

### 支持的 SSML 标签

| 标签 | 描述 |
|------|------|
| `<lang>` | 语言指定 |
| `<p>` | 段落 |
| `<phoneme>` | 音标 |
| `<s>` | 句子 |
| `<sub>` | 替换文本 |

---

## 数据流图

### 完整播客生成流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        播客生成完整流程                                  │
└─────────────────────────────────────────────────────────────────────────┘

1. 输入阶段
   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
   │  URLs   │  │  PDFs   │  │ YouTube │  │  Images │  │  Text   │
   └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘
        │            │            │            │            │
        └────────────┴────────────┴────────────┴────────────┘
                              │
                              ▼
2. 内容提取 (ContentExtractor)
   ┌─────────────────────────────────────────────────────────────┐
   │  • 检测源类型                                                 │
   │  • 提取文本内容                                               │
   │  • 处理多模态输入（图像）                                     │
   │  • 合并所有内容                                               │
   └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
3. 内容生成 (ContentGenerator)
   ┌─────────────────────────────────────────────────────────────┐
   │  • 选择 LLM 后端（Gemini/OpenAI/Local）                       │
   │  • 构建提示模板                                               │
   │  • 生成 Q&A 对话格式转录                                      │
   │  • 长格式：分块处理 + 上下文链接                               │
   │  • 清理输出（移除无效标记）                                   │
   └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
4. 语音合成 (TextToSpeech)
   ┌─────────────────────────────────────────────────────────────┐
   │  • 选择 TTS 提供者（OpenAI/ElevenLabs/Edge/Gemini）           │
   │  • 分割 Q&A 对                                                │
   │  • 为每个说话人生成音频                                       │
   │  • 合并音频片段                                               │
   │  • 导出 MP3 (320kbps)                                        │
   └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
5. 输出
   ┌─────────────────────────────────────────────────────────────┐
   │  • 音频文件：data/audio/podcast_*.mp3                        │
   │  • 转录文件：data/transcripts/transcript_*.txt               │
   └─────────────────────────────────────────────────────────────┘
```

---

## 配置系统

### 主配置文件 (config.yaml)

```yaml
main:
  default_tts_model: openai
  default_llm_model: gemini-2.5-flash

content_generator:
  llm_model: gemini-2.5-flash
  max_output_tokens: 8192
  prompt_template: podcastfy/prompt_v1
  prompt_commit: abc123

content_extractor:
  youtube_url_patterns:
    - youtube.com
    - youtu.be

text_to_speech:
  default_tts_model: openai
  audio_format: mp3
  output_directories:
    audio: data/audio
    transcripts: data/transcripts
  openai:
    model: tts-1
    default_voices:
      question: alloy
      answer: echo
  elevenlabs:
    model: eleven_monolingual_v1
    default_voices:
      question: Rachel
      answer: Adam
  edge:
    default_voices:
      question: en-US-AndrewNeural
      answer: en-US-AriaNeural
  gemini:
    model: tts-default
    default_voices:
      question: Aoede
      answer: Kore
  geminimulti:
    model: en-US-Studio-MultiSpeaker
    default_voices:
      question: S
      answer: R
```

### 对话配置 (conversation_config.yaml)

```yaml
creativity: 0.7
conversation_style:
  - engaging
  - informative
roles_person1: main summarizer
roles_person2: questioner
dialogue_structure:
  - Introduction
  - Main Content
  - Conclusion
podcast_name: PODCASTFY
podcast_tagline: YOUR PERSONAL GenAI PODCAST
output_language: English
engagement_techniques:
  - Rhetorical Questions
  - Analogies
  - Humor
user_instructions: ""
max_num_chunks: 7
min_chunk_size: 600
```

---

## 使用示例

### 基础用法

```python
from podcastfy.client import generate_podcast

# 从单个 URL 生成播客
audio_file = generate_podcast(
    urls=["https://en.wikipedia.org/wiki/Podcast"]
)
```

### 自定义配置

```python
# 自定义对话配置
custom_config = {
    'conversation_style': ['Engaging', 'Fast-paced', 'Educational'],
    'roles_person1': 'Interviewer',
    'roles_person2': 'Subject matter expert',
    'dialogue_structure': ['Topic Introduction', 'Discussion', 'Q&A', 'Conclusion'],
    'podcast_name': 'Tech Talk',
    'podcast_tagline': 'The future of technology',
    'output_language': 'English',
    'creativity': 0.75
}

audio_file = generate_podcast(
    urls=["https://example.com/article"],
    conversation_config=custom_config,
    tts_model="geminimulti"
)
```

### 长格式播客

```python
# 生成长格式播客（20-30+ 分钟）
audio_file = generate_podcast(
    urls=["https://www.gutenberg.org/book/148"],  # 本杰明·富兰克林自传
    longform=True,
    tts_model="geminimulti"
)
```

### 从图像生成

```python
# 从图像生成播客
image_paths = [
    "https://example.com/image1.jpg",
    "https://example.com/image2.jpg"
]

audio_file = generate_podcast(
    image_paths=image_paths,
    tts_model="geminimulti"
)
```

### 仅生成转录

```python
# 仅生成转录文件
transcript_file = generate_podcast(
    urls=["https://example.com/article"],
    transcript_only=True
)

# 读取转录
with open(transcript_file, 'r') as f:
    content = f.read()
```

### 使用本地 LLM

```python
# 使用本地 Llamafile 模型
audio_file = generate_podcast(
    urls=["https://example.com"],
    is_local=True
)
```

### 多语言支持

```python
# 生成法语播客
config = {
    'output_language': 'French'
}

audio_file = generate_podcast(
    urls=["https://example.fr/article"],
    conversation_config=config,
    tts_model="elevenlabs"  # 推荐使用 ElevenLabs 用于非英语
)
```

---

## API 请求示例（cURL）

### 生成播客

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://en.wikipedia.org/wiki/Podcast"],
    "google_key": "YOUR_GEMINI_KEY",
    "openai_key": "YOUR_OPENAI_KEY",
    "tts_model": "openai",
    "name": "My Podcast",
    "creativity": 0.7
  }'
```

### 获取音频文件

```bash
curl -O http://localhost:8000/audio/podcast_abc123.mp3
```

### 健康检查

```bash
curl http://localhost:8000/health
```

---

## Docker 部署

### 构建镜像

```bash
# 生产镜像
docker build -f Dockerfile -t podcastfy:latest .

# API 镜像
docker build -f Dockerfile_api -t podcastfy-api:latest .

# 开发镜像
docker build -f Dockerfile.dev -t podcastfy-dev:latest .
```

### 运行容器

```bash
# 运行 API 服务
docker run -p 8000:8000 \
  -e GOOGLE_API_KEY=your_key \
  -e OPENAI_API_KEY=your_key \
  podcastfy-api:latest
```

### Docker Compose

```yaml
version: '3.8'

services:
  podcastfy:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    ports:
      - "8000:8000"
```

---

## 错误处理

### 常见错误

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `Invalid API Key` | API Key 无效或缺失 | 检查环境变量配置 |
| `No input provided` | 未提供输入源 | 提供 URL、文本或图像 |
| `Transcript format invalid` | 转录格式不正确 | 确保使用 `<Person1>`/`<Person2>` 标签 |
| `TTS generation failed` | TTS API 调用失败 | 检查 TTS 配置和网络 |

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

---

## 性能优化建议

1. **使用 Gemini Multi-Speaker TTS** - 最自然的多人对话效果
2. **长内容使用分块处理** - 避免 LLM 输出限制
3. **缓存转录文件** - 避免重复生成
4. **批量处理 URL** - 一次处理多个 URL 提高效率

---

## 相关资源

- **GitHub**: https://github.com/souzatharsis/podcastfy
- **PyPI**: https://pypi.org/project/podcastfy/
- **文档**: https://podcastfy.readthedocs.io/
- **HuggingFace Demo**: https://huggingface.co/spaces/thatupiso/Podcastfy.ai_demo

---

## 版本历史

| 版本 | 日期 | 主要更新 |
|------|------|----------|
| 0.4.3 | 2024-11 | Google Multi-Speaker TTS 支持 |
| 0.3.6 | 2024-11 | 长格式播客生成支持 |
| 0.3.3 | 2024-11 | REST API (FastAPI) 部署 |
| 0.2.3 | 2024-10 | Edge TTS、本地 LLM 支持 |
| 0.2.0 | 2024-10 | 对话配置参数化、LangChain 集成 |

---

*文档最后更新：2024 年 11 月*