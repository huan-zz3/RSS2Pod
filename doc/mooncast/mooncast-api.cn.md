# MoonCast API 文档

## 概述

MoonCast 是一个高质量的零样本（zero-shot）播客生成系统，可将文本文稿转换为自然流畅的多说话人音频。本文档描述了将 MoonCast 集成到您的应用程序中的完整 API。

## 目录

1. [系统架构](#系统架构)
2. [安装与设置](#安装与设置)
3. [核心 API](#核心-api)
   - [分词器 API](#分词器-api)
   - [音频分词器 API](#音频分词器-api)
   - [音频逆分词器 API](#音频逆分词器-api)
   - [推理模型 API](#推理模型-api)
4. [数据格式](#数据格式)
5. [文稿生成](#文稿生成)
6. [示例](#示例)

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      MoonCast 流水线                            │
├─────────────────────────────────────────────────────────────────┤
│  文本文稿 → 分词器 → LLM → 语义令牌 → 逆分词器 → 音频
│                              ↑                                    │
│                    (音频分词器用于参考)                           │
└─────────────────────────────────────────────────────────────────┘
```

**组件：**
- **分词器（Tokenizer）**：将文本转换为 BPE（Byte Pair Encoding，字节对编码）令牌 ID
- **音频分词器（Audio Tokenizer）**：从参考音频中提取语义令牌（W2V-BERT 2.0 + RepCodec）
- **文本到语义 LLM（Text-to-Semantic LLM）**：从文本提示生成语义令牌
- **音频逆分词器（Audio Detokenizer）**：将语义令牌转换回音频（Flow Matching + BigVGAN）

---

## 安装与设置

### 环境要求

```bash
conda create -n mooncast -y python=3.10
conda activate mooncast
pip install -r requirements.txt 
pip install flash-attn --no-build-isolation
pip install huggingface_hub
pip install gradio==5.22.0
```

### 下载预训练权重

```python
from huggingface_hub import snapshot_download
snapshot_download(repo_id="jzq11111/mooncast", local_dir='./resources/')
```

### 所需资源结构

```
resources/
├── tokenizer/
│   └── 160k.model          # SentencePiece 分词器模型
├── audio_tokenizer/
│   ├── stats.pt            # 特征归一化统计信息
│   └── model.safetensors   # RepCodec 语义编解码模型
├── audio_detokenizer/
│   ├── config.yaml         # Flow Matching 模型配置
│   └── model.pt            # Flow Matching 模型权重
├── vocoder/
│   ├── config.json         # BigVGAN 声码器配置
│   └── model.pt            # BigVGAN 声码器权重
└── text2semantic/          # 文本到语义 LLM
```

---

## 核心 API

### 分词器 API

#### `get_tokenizer_and_extra_tokens()`

初始化并返回分词器及特殊令牌。

**返回值：**
- `tokenizer` (SPieceTokenizer): SentencePiece 分词器实例
- `extra_tokens` (ExtraTokens): 包含特殊令牌 ID 的数据类

**ExtraTokens 字段：**
| 字段 | 类型 | 描述 |
|-------|------|-------------|
| `msg_end` | int | 消息结束令牌 ID |
| `user_msg_start` | int | 用户消息开始令牌 ID |
| `assistant_msg_start` | int | 助手消息开始令牌 ID |
| `name_end` | int | 名称/说话人 ID 令牌结束 |
| `media_begin` | int | 媒体内容开始令牌 ID |
| `media_content` | int | 媒体内容标记令牌 ID |
| `media_end` | int | 媒体内容结束令牌 ID |
| `pad` | int | 填充令牌 ID |

**示例：**
```python
from modules.tokenizer.tokenizer import get_tokenizer_and_extra_tokens

tokenizer, extra_tokens = get_tokenizer_and_extra_tokens()
print(f"消息结束令牌 ID: {extra_tokens.msg_end}")
```

---

#### `SPieceTokenizer.encode(text, bos=False, eos=False)`

将文本编码为令牌 ID。

**参数：**
| 参数 | 类型 | 默认值 | 描述 |
|-----------|------|---------|-------------|
| `text` | str | - | 要编码的输入文本 |
| `bos` | bool | False | 是否在开头添加序列开始令牌 |
| `eos` | bool | False | 是否在末尾添加序列结束令牌 |

**返回值：**
- `list[int]`: 令牌 ID 列表

**示例：**
```python
text = "你好，这是测试文本。"
token_ids = tokenizer.encode(text)
print(f"令牌 ID: {token_ids}")
```

---

#### `SPieceTokenizer.decode(token_ids, skip_special_tokens=False)`

将令牌 ID 解码回文本。

**参数：**
| 参数 | 类型 | 默认值 | 描述 |
|-----------|------|---------|-------------|
| `token_ids` | int 或 list[int] | - | 令牌 ID 或令牌 ID 列表 |
| `skip_special_tokens` | bool | False | 是否跳过特殊令牌（不支持） |

**返回值：**
- `str`: 解码后的文本

**示例：**
```python
token_ids = [100, 200, 300, 400]
text = tokenizer.decode(token_ids)
print(f"解码文本：{text}")
```

---

### 音频分词器 API

#### `get_audio_tokenizer()`

初始化并返回音频分词器（W2V-BERT 2.0 + RepCodec）。

**返回值：**
- `AudioTokenizer`: 音频分词器实例

**配置：**
| 键 | 值 | 描述 |
|-----|-------|-------------|
| `device` | 'cuda' 或 'cpu' | 运行模型的设备 |
| `feat_stats` | path | 特征统计文件路径 |
| `wav2vec_ckpt` | 'facebook/w2v-bert-2.0' | W2V-BERT 模型检查点 |
| `semantic_codec_ckpt` | path | RepCodec 模型检查点 |

**示例：**
```python
from modules.audio_tokenizer.audio_tokenizer import get_audio_tokenizer

audio_tokenizer = get_audio_tokenizer()
```

---

#### `AudioTokenizer.tokenize(speech)`

从音频波形中提取语义令牌。

**参数：**
| 参数 | 类型 | 描述 |
|-----------|------|-------------|
| `speech` | torch.Tensor | 音频波形，形状 `[B, N]`，采样率 16kHz |

**返回值：**
- `torch.Tensor`: 语义令牌，形状 `[B, N_tokens]`

**示例：**
```python
import torch
import librosa

# 以 16kHz 加载音频
waveform, sr = librosa.load("audio.wav", sr=16000)
waveform = torch.tensor(waveform).unsqueeze(0)  # 添加批次维度

# 提取语义令牌
semantic_tokens = audio_tokenizer.tokenize(waveform)
print(f"语义令牌形状：{semantic_tokens.shape}")
```

---

### 音频逆分词器 API

#### `get_audio_detokenizer()`

初始化并返回音频逆分词器（Flow Matching + BigVGAN）。

**返回值：**
- `PrefixStreamingFlowMatchingDetokenizer`: 音频逆分词器实例

**配置：**
| 参数 | 值 | 描述 |
|-----------|-------|-------------|
| `vocoder_config` | path | BigVGAN 配置文件路径 |
| `vocoder_ckpt` | path | BigVGAN 检查点路径 |
| `fm_config` | path | Flow Matching 配置路径 |
| `fm_ckpt` | path | Flow Matching 检查点路径 |
| `max_prompt_chunk` | 10 | 最大提示块大小（10 * 3 = 30 秒） |
| `look_ahead_tokens` | 12 | 用于平滑的前视令牌数量 |

**示例：**
```python
from modules.audio_detokenizer.audio_detokenizer import get_audio_detokenizer

detokenizer = get_audio_detokenizer()
```

---

#### `detokenize(detokenizer, tokens, ref_wav, ref_tokens)`

将语义令牌转换为音频，使用参考音频提供音色。

**参数：**
| 参数 | 类型 | 描述 |
|-----------|------|-------------|
| `detokenizer` | PrefixStreamingFlowMatchingDetokenizer | 逆分词器实例 |
| `tokens` | torch.Tensor | 语义令牌，形状 `[B, N]` |
| `ref_wav` | torch.Tensor | 用于音色的参考波形，形状 `[B, N]`，24kHz |
| `ref_tokens` | torch.Tensor | 参考语义令牌，形状 `[B, N]` |

**返回值：**
- `torch.Tensor`: 生成的音频波形，形状 `[B, N]`，24kHz

**示例：**
```python
from modules.audio_detokenizer.audio_detokenizer import detokenize

# tokens: 要解码的语义令牌
# ref_wav: 用于音色的参考音频
# ref_tokens: 参考语义令牌
generated_audio = detokenize(detokenizer, tokens, ref_wav, ref_tokens)
```

---

#### `detokenize_streaming(detokenizer, tokens, ref_wav, ref_tokens)`

流式地将语义令牌转换为音频，使用参考音频。

**参数：**
| 参数 | 类型 | 描述 |
|-----------|------|-------------|
| `detokenizer` | PrefixStreamingFlowMatchingDetokenizer | 逆分词器实例 |
| `tokens` | torch.Tensor | 语义令牌，形状 `[B, N]` |
| `ref_wav` | torch.Tensor | 用于音色的参考波形 |
| `ref_tokens` | torch.Tensor | 参考语义令牌 |

**产出：**
- `torch.Tensor`: 音频块，形状 `[B, N_chunk]`，24kHz

**示例：**
```python
from modules.audio_detokenizer.audio_detokenizer import detokenize_streaming

for audio_chunk in detokenize_streaming(detokenizer, tokens, ref_wav, ref_tokens):
    # 实时处理每个音频块
    pass
```

---

#### `detokenize_noref(detokenizer, tokens)`

将语义令牌转换为音频，不使用参考音频。

**参数：**
| 参数 | 类型 | 描述 |
|-----------|------|-------------|
| `detokenizer` | PrefixStreamingFlowMatchingDetokenizer | 逆分词器实例 |
| `tokens` | torch.Tensor | 语义令牌，形状 `[B, N]` |

**返回值：**
- `torch.Tensor`: 生成的音频波形，形状 `[B, N]`，24kHz

**示例：**
```python
from modules.audio_detokenizer.audio_detokenizer import detokenize_noref

generated_audio = detokenize_noref(detokenizer, tokens)
```

---

#### `detokenize_noref_streaming(detokenizer, tokens)`

流式地将语义令牌转换为音频，不使用参考音频。

**参数：**
| 参数 | 类型 | 描述 |
|-----------|------|-------------|
| `detokenizer` | PrefixStreamingFlowMatchingDetokenizer | 逆分词器实例 |
| `tokens` | torch.Tensor | 语义令牌，形状 `[B, N]` |

**产出：**
- `torch.Tensor`: 音频块，形状 `[B, N_chunk]`，24kHz

---

### 推理模型 API

#### `Model.__init__()`

初始化 MoonCast 推理模型及所有组件。

**加载：**
- 文本分词器和特殊令牌
- 音频分词器（W2V-BERT 2.0 + RepCodec）
- 音频逆分词器（Flow Matching + BigVGAN）
- 文本到语义 LLM

**示例：**
```python
from inference import Model

model = Model()
model.generate_config.max_new_tokens = 50 * 50  # 每轮最多 50 秒
```

---

#### `Model.inference(js, streaming=False)`

用于播客生成的主要推理方法。

**参数：**
| 参数 | 类型 | 默认值 | 描述 |
|-----------|------|---------|-------------|
| `js` | dict | - | 输入 JSON，包含对话和可选的 role_mapping |
| `streaming` | bool | False | 是否流式输出音频 |

**返回值：**
- 如果 `streaming=False`: `str` - Base64 编码的 MP3 音频数据
- 如果 `streaming=True`: 生成器，产出 base64 编码的 MP3 块

**输入 JSON 格式（带提示）：**
```json
{
    "role_mapping": {
        "0": {
            "ref_audio": "path/to/role0_audio.wav",
            "ref_text": "角色 0 的参考文本"
        },
        "1": {
            "ref_audio": "path/to/role1_audio.wav",
            "ref_text": "角色 1 的参考文本"
        }
    },
    "dialogue": [
        {
            "role": "0",
            "text": "角色 0 要说的文本"
        },
        {
            "role": "1",
            "text": "角色 1 要说的文本"
        }
    ]
}
```

**输入 JSON 格式（不带提示）：**
```json
{
    "dialogue": [
        {
            "role": "0",
            "text": "角色 0 要说的文本"
        },
        {
            "role": "1",
            "text": "角色 1 要说的文本"
        }
    ]
}
```

**示例：**
```python
# 非流式推理
input_json = {
    "role_mapping": {
        "0": {"ref_audio": "./zh_prompt0.wav", "ref_text": "参考文本"},
        "1": {"ref_audio": "./zh_prompt1.wav", "ref_text": "参考文本"}
    },
    "dialogue": [
        {"role": "0", "text": "第一轮对话"},
        {"role": "1", "text": "第二轮对话"}
    ]
}

audio_b64 = model.inference(input_json)

# 流式推理
for chunk_b64 in model.inference(input_json, streaming=True):
    audio_chunk = base64.b64decode(chunk_b64)
    # 处理音频块
```

---

#### `Model.infer_with_prompt(js)`

使用参考音频提示进行推理，用于声音克隆。

**参数：**
| 参数 | 类型 | 描述 |
|-----------|------|-------------|
| `js` | dict | 包含 role_mapping 和 dialogue 的输入 JSON |

**返回值：**
- `str`: Base64 编码的 MP3 音频数据

**示例：**
```python
input_json = {
    "role_mapping": {
        "0": {"ref_audio": "./prompt0.wav", "ref_text": "参考文本 0"},
        "1": {"ref_audio": "./prompt1.wav", "ref_text": "参考文本 1"}
    },
    "dialogue": [
        {"role": "0", "text": "你好，这是说话人 0"},
        {"role": "1", "text": "嗨，这是说话人 1"}
    ]
}

audio_b64 = model.infer_with_prompt(input_json)
```

---

#### `Model.infer_with_prompt_streaming(js)`

使用参考音频提示进行流式推理。

**参数：**
| 参数 | 类型 | 描述 |
|-----------|------|-------------|
| `js` | dict | 包含 role_mapping 和 dialogue 的输入 JSON |

**产出：**
- `str`: Base64 编码的 MP3 音频块

---

#### `Model.infer_without_prompt(js)`

不使用参考音频提示进行推理（使用默认声音）。

**参数：**
| 参数 | 类型 | 描述 |
|-----------|------|-------------|
| `js` | dict | 仅包含 dialogue 的输入 JSON |

**返回值：**
- `str`: Base64 编码的 MP3 音频数据

**示例：**
```python
input_json = {
    "dialogue": [
        {"role": "0", "text": "你好，这是说话人 0"},
        {"role": "1", "text": "嗨，这是说话人 1"}
    ]
}

audio_b64 = model.infer_without_prompt(input_json)
```

---

#### `Model.infer_without_prompt_streaming(js)`

不使用参考音频提示进行流式推理。

**参数：**
| 参数 | 类型 | 描述 |
|-----------|------|-------------|
| `js` | dict | 仅包含 dialogue 的输入 JSON |

**产出：**
- `str`: Base64 编码的 MP3 音频块

---

## 数据格式

### 对话 JSON 格式

```json
{
    "role_mapping": {
        "<role id>": {
            "ref_audio": "<音频文件路径>",
            "ref_text": "<ASR 对齐的参考文本>"
        }
    },
    "dialogue": [
        {
            "role": "<角色 id>",
            "text": "<要朗读的文本>"
        }
    ]
}
```

**字段：**
| 字段 | 类型 | 必需 | 描述 |
|-------|------|----------|-------------|
| `role_mapping` | dict | 否 | 将角色 ID 映射到参考音频和文本 |
| `role_mapping.<role_id>.ref_audio` | str | 是（如果存在 role_mapping） | 参考音频文件路径 |
| `role_mapping.<role_id>.ref_text` | str | 是（如果存在 role_mapping） | 用于 ASR 对齐的参考文本 |
| `dialogue` | list | 是 | 对话轮次列表 |
| `dialogue[].role` | str | 是 | 角色 ID（"0" 或 "1"） |
| `dialogue[].text` | str | 是 | 要朗读的文本 |

**约束：**
- 角色必须交替（0, 1, 0, 1, ...）
- 每轮最多 50 秒音频
- 参考音频应为清晰的语音样本

### 音频格式规范

| 格式 | 采样率 | 声道 | 编码 |
|--------|-------------|----------|----------|
| 输入（参考） | 24kHz / 16kHz | 单声道 | WAV/MP3 |
| 输出（生成） | 24kHz | 单声道 | MP3 (base64) |

---

## 文稿生成

MoonCast 包含用于从文档生成播客文稿的 LLM 提示。

### INPUT2BRIEF 提示

位于 `zh_llmprompt_script_gen.py`（中文）和 `en_llmprompt_script_gen.py`（英文）。

**目的：** 将输入文档总结为结构化的摘要。

**结构：**
1. **标题和作者** - 文档元数据和主题
2. **摘要** - 什么、为什么、如何以及结果
3. **主题和概念** - 3W 原则（What, Why, How）
4. **关键引用** - 论点、证据、推理
5. **结论** - 亮点和未来方向

### BRIEF2SCRIPT 提示

**目的：** 将摘要转换为播客文稿。

**输出格式：**
```json
[
    {"speaker": "1", "text": "主持人在这里说话"},
    {"speaker": "2", "text": "嘉宾回应"}
]
```

**要求：**
- 对话风格，包含填充词
- 仅使用逗号、句号、问号（无感叹号、省略号、括号、引号）
- 说话人 1 = 主持人，说话人 2 = 嘉宾
- 最多 3000 字，最多 60 轮
- 每个主题至少讨论 4 轮

---

## 示例

### 完整推理示例

```python
from inference import Model
import base64
import io
from pydub import AudioSegment

# 初始化模型
model = Model()
model.generate_config.max_new_tokens = 50 * 50  # 每轮最多 50 秒

# 准备输入
input_json = {
    "role_mapping": {
        "0": {
            "ref_audio": "./zh_prompt0.wav",
            "ref_text": "可以每天都骑并且可能会让你爱上骑车。"
        },
        "1": {
            "ref_audio": "./zh_prompt1.wav",
            "ref_text": "他最后就能让同样食材炒出来的菜味道大大提升。"
        }
    },
    "dialogue": [
        {
            "role": "0",
            "text": "我觉得啊，就是经历了这么多年的经验，补剂的作用就是九分的努力，十分的补剂。"
        },
        {
            "role": "1",
            "text": "对，其实很多时候心理作用是非常重要的。"
        },
        {
            "role": "0",
            "text": "其实心理作用只要能实现你的预期目的就可以了。"
        }
    ]
}

# 非流式推理
audio_b64 = model.inference(input_json)
with open("output.mp3", "wb") as f:
    f.write(base64.b64decode(audio_b64))

# 流式推理
audio = AudioSegment.empty()
for chunk_b64 in model.inference(input_json, streaming=True):
    audio_chunk = AudioSegment.from_file(io.BytesIO(base64.b64decode(chunk_b64)), format="mp3")
    audio += audio_chunk
audio.export("output_stream.mp3", format="mp3")
```

### Gradio Web 界面

```python
# app.py 部署
CUDA_VISIBLE_DEVICES=0 python app.py
```

Gradio 界面提供：
- 角色 0 和角色 1 的提示音频上传
- 每个角色的参考文本输入
- JSON 对话输入
- 流式音频输出
- 双语界面（中文/英文）

---

## 错误处理

### 常见错误

| 错误 | 原因 | 解决方案 |
|-------|-------|----------|
| 角色验证失败 | 角色未交替 | 确保对话交替 0, 1, 0, 1... |
| 音频加载失败 | 无效的音频路径 | 检查文件路径是否正确 |
| OOM (显存不足) | GPU 显存耗尽 | 减小小批次大小或使用流式模式 |
| 令牌限制超出 | 文本过长 | 拆分为多轮（每轮最多 50 秒） |

---

## 许可证

MoonCast 根据 MIT 许可证发布。详细信息请参阅 LICENSE 文件。

## 免责声明

本项目仅供**研究用途**。强烈鼓励用户负责任地使用本项目及其生成的音频。作者不对本项目的任何 misuse 或 abuse 负责。