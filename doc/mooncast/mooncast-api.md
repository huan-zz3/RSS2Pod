# MoonCast API Documentation

## Overview

MoonCast is a high-quality zero-shot podcast generation system that converts text scripts into natural-sounding multi-speaker audio. This document describes the complete API for integrating MoonCast into your applications.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Installation and Setup](#installation-and-setup)
3. [Core APIs](#core-apis)
   - [Tokenizer API](#tokenizer-api)
   - [Audio Tokenizer API](#audio-tokenizer-api)
   - [Audio Detokenizer API](#audio-detokenizer-api)
   - [Inference Model API](#inference-model-api)
4. [Data Formats](#data-formats)
5. [Script Generation](#script-generation)
6. [Examples](#examples)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      MoonCast Pipeline                          │
├─────────────────────────────────────────────────────────────────┤
│  Text Script → Tokenizer → LLM → Semantic Tokens → Detokenizer → Audio
│                              ↑                                    │
│                    (Audio Tokenizer for reference)               │
└─────────────────────────────────────────────────────────────────┘
```

**Components:**
- **Tokenizer**: Converts text to BPE (Byte Pair Encoding) token IDs
- **Audio Tokenizer**: Extracts semantic tokens from reference audio (W2V-BERT 2.0 + RepCodec)
- **Text-to-Semantic LLM**: Generates semantic tokens from text prompts
- **Audio Detokenizer**: Converts semantic tokens back to audio (Flow Matching + BigVGAN)

---

## Installation and Setup

### Environment Requirements

```bash
conda create -n mooncast -y python=3.10
conda activate mooncast
pip install -r requirements.txt 
pip install flash-attn --no-build-isolation
pip install huggingface_hub
pip install gradio==5.22.0
```

### Download Pretrained Weights

```python
from huggingface_hub import snapshot_download
snapshot_download(repo_id="jzq11111/mooncast", local_dir='./resources/')
```

### Required Resources Structure

```
resources/
├── tokenizer/
│   └── 160k.model          # SentencePiece tokenizer model
├── audio_tokenizer/
│   ├── stats.pt            # Feature normalization statistics
│   └── model.safetensors   # RepCodec semantic codec model
├── audio_detokenizer/
│   ├── config.yaml         # Flow matching model config
│   └── model.pt            # Flow matching model weights
├── vocoder/
│   ├── config.json         # BigVGAN vocoder config
│   └── model.pt            # BigVGAN vocoder weights
└── text2semantic/          # Text-to-semantic LLM
```

---

## Core APIs

### Tokenizer API

#### `get_tokenizer_and_extra_tokens()`

Initialize and return the tokenizer with special tokens.

**Returns:**
- `tokenizer` (SPieceTokenizer): SentencePiece tokenizer instance
- `extra_tokens` (ExtraTokens): Dataclass containing special token IDs

**ExtraTokens Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `msg_end` | int | Message end token ID |
| `user_msg_start` | int | User message start token ID |
| `assistant_msg_start` | int | Assistant message start token ID |
| `name_end` | int | Name/end of speaker ID token |
| `media_begin` | int | Media content begin token ID |
| `media_content` | int | Media content marker token ID |
| `media_end` | int | Media content end token ID |
| `pad` | int | Padding token ID |

**Example:**
```python
from modules.tokenizer.tokenizer import get_tokenizer_and_extra_tokens

tokenizer, extra_tokens = get_tokenizer_and_extra_tokens()
print(f"Message end token ID: {extra_tokens.msg_end}")
```

---

#### `SPieceTokenizer.encode(text, bos=False, eos=False)`

Encode text into token IDs.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text` | str | - | Input text to encode |
| `bos` | bool | False | Whether to prepend beginning-of-sequence token |
| `eos` | bool | False | Whether to append end-of-sequence token |

**Returns:**
- `list[int]`: List of token IDs

**Example:**
```python
text = "你好，这是测试文本。"
token_ids = tokenizer.encode(text)
print(f"Token IDs: {token_ids}")
```

---

#### `SPieceTokenizer.decode(token_ids, skip_special_tokens=False)`

Decode token IDs back to text.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `token_ids` | int or list[int] | - | Token ID or list of token IDs |
| `skip_special_tokens` | bool | False | Whether to skip special tokens (not supported) |

**Returns:**
- `str`: Decoded text

**Example:**
```python
token_ids = [100, 200, 300, 400]
text = tokenizer.decode(token_ids)
print(f"Decoded text: {text}")
```

---

### Audio Tokenizer API

#### `get_audio_tokenizer()`

Initialize and return the audio tokenizer (W2V-BERT 2.0 + RepCodec).

**Returns:**
- `AudioTokenizer`: Audio tokenizer instance

**Configuration:**
| Key | Value | Description |
|-----|-------|-------------|
| `device` | 'cuda' or 'cpu' | Device to run the model on |
| `feat_stats` | path | Path to feature statistics file |
| `wav2vec_ckpt` | 'facebook/w2v-bert-2.0' | W2V-BERT model checkpoint |
| `semantic_codec_ckpt` | path | RepCodec model checkpoint |

**Example:**
```python
from modules.audio_tokenizer.audio_tokenizer import get_audio_tokenizer

audio_tokenizer = get_audio_tokenizer()
```

---

#### `AudioTokenizer.tokenize(speech)`

Extract semantic tokens from audio waveform.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `speech` | torch.Tensor | Audio waveform, shape `[B, N]`, sample rate 16kHz |

**Returns:**
- `torch.Tensor`: Semantic tokens, shape `[B, N_tokens]`

**Example:**
```python
import torch
import librosa

# Load audio at 16kHz
waveform, sr = librosa.load("audio.wav", sr=16000)
waveform = torch.tensor(waveform).unsqueeze(0)  # Add batch dimension

# Extract semantic tokens
semantic_tokens = audio_tokenizer.tokenize(waveform)
print(f"Semantic tokens shape: {semantic_tokens.shape}")
```

---

### Audio Detokenizer API

#### `get_audio_detokenizer()`

Initialize and return the audio detokenizer (Flow Matching + BigVGAN).

**Returns:**
- `PrefixStreamingFlowMatchingDetokenizer`: Audio detokenizer instance

**Configuration:**
| Parameter | Value | Description |
|-----------|-------|-------------|
| `vocoder_config` | path | BigVGAN config file path |
| `vocoder_ckpt` | path | BigVGAN checkpoint path |
| `fm_config` | path | Flow matching config path |
| `fm_ckpt` | path | Flow matching checkpoint path |
| `max_prompt_chunk` | 10 | Maximum prompt chunk size (10 * 3 = 30s) |
| `look_ahead_tokens` | 12 | Number of tokens to look ahead for smoothing |

**Example:**
```python
from modules.audio_detokenizer.audio_detokenizer import get_audio_detokenizer

detokenizer = get_audio_detokenizer()
```

---

#### `detokenize(detokenizer, tokens, ref_wav, ref_tokens)`

Convert semantic tokens to audio with reference audio for timbre.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `detokenizer` | PrefixStreamingFlowMatchingDetokenizer | Detokenizer instance |
| `tokens` | torch.Tensor | Semantic tokens, shape `[B, N]` |
| `ref_wav` | torch.Tensor | Reference waveform for timbre, shape `[B, N]`, 24kHz |
| `ref_tokens` | torch.Tensor | Reference semantic tokens, shape `[B, N]` |

**Returns:**
- `torch.Tensor`: Generated audio waveform, shape `[B, N]`, 24kHz

**Example:**
```python
from modules.audio_detokenizer.audio_detokenizer import detokenize

# tokens: semantic tokens to decode
# ref_wav: reference audio for timbre
# ref_tokens: reference semantic tokens
generated_audio = detokenize(detokenizer, tokens, ref_wav, ref_tokens)
```

---

#### `detokenize_streaming(detokenizer, tokens, ref_wav, ref_tokens)`

Stream semantic tokens to audio with reference audio.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `detokenizer` | PrefixStreamingFlowMatchingDetokenizer | Detokenizer instance |
| `tokens` | torch.Tensor | Semantic tokens, shape `[B, N]` |
| `ref_wav` | torch.Tensor | Reference waveform for timbre |
| `ref_tokens` | torch.Tensor | Reference semantic tokens |

**Yields:**
- `torch.Tensor`: Audio chunks, shape `[B, N_chunk]`, 24kHz

**Example:**
```python
from modules.audio_detokenizer.audio_detokenizer import detokenize_streaming

for audio_chunk in detokenize_streaming(detokenizer, tokens, ref_wav, ref_tokens):
    # Process each audio chunk in real-time
    pass
```

---

#### `detokenize_noref(detokenizer, tokens)`

Convert semantic tokens to audio without reference audio.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `detokenizer` | PrefixStreamingFlowMatchingDetokenizer | Detokenizer instance |
| `tokens` | torch.Tensor | Semantic tokens, shape `[B, N]` |

**Returns:**
- `torch.Tensor`: Generated audio waveform, shape `[B, N]`, 24kHz

**Example:**
```python
from modules.audio_detokenizer.audio_detokenizer import detokenize_noref

generated_audio = detokenize_noref(detokenizer, tokens)
```

---

#### `detokenize_noref_streaming(detokenizer, tokens)`

Stream semantic tokens to audio without reference audio.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `detokenizer` | PrefixStreamingFlowMatchingDetokenizer | Detokenizer instance |
| `tokens` | torch.Tensor | Semantic tokens, shape `[B, N]` |

**Yields:**
- `torch.Tensor`: Audio chunks, shape `[B, N_chunk]`, 24kHz

---

### Inference Model API

#### `Model.__init__()`

Initialize the MoonCast inference model with all components.

**Loads:**
- Text tokenizer and special tokens
- Audio tokenizer (W2V-BERT 2.0 + RepCodec)
- Audio detokenizer (Flow Matching + BigVGAN)
- Text-to-semantic LLM

**Example:**
```python
from inference import Model

model = Model()
model.generate_config.max_new_tokens = 50 * 50  # Max 50 seconds per turn
```

---

#### `Model.inference(js, streaming=False)`

Main inference method for podcast generation.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `js` | dict | - | Input JSON containing dialogue and optional role_mapping |
| `streaming` | bool | False | Whether to stream audio output |

**Returns:**
- If `streaming=False`: `str` - Base64-encoded MP3 audio data
- If `streaming=True`: Generator yielding base64-encoded MP3 chunks

**Input JSON Format (with prompt):**
```json
{
    "role_mapping": {
        "0": {
            "ref_audio": "path/to/role0_audio.wav",
            "ref_text": "Reference text for role 0"
        },
        "1": {
            "ref_audio": "path/to/role1_audio.wav",
            "ref_text": "Reference text for role 1"
        }
    },
    "dialogue": [
        {
            "role": "0",
            "text": "Text for role 0 to speak"
        },
        {
            "role": "1",
            "text": "Text for role 1 to speak"
        }
    ]
}
```

**Input JSON Format (without prompt):**
```json
{
    "dialogue": [
        {
            "role": "0",
            "text": "Text for role 0 to speak"
        },
        {
            "role": "1",
            "text": "Text for role 1 to speak"
        }
    ]
}
```

**Example:**
```python
# Non-streaming inference
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

# Streaming inference
for chunk_b64 in model.inference(input_json, streaming=True):
    audio_chunk = base64.b64decode(chunk_b64)
    # Process audio chunk
```

---

#### `Model.infer_with_prompt(js)`

Inference with reference audio prompts for voice cloning.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `js` | dict | Input JSON with role_mapping and dialogue |

**Returns:**
- `str`: Base64-encoded MP3 audio data

**Example:**
```python
input_json = {
    "role_mapping": {
        "0": {"ref_audio": "./prompt0.wav", "ref_text": "Reference text 0"},
        "1": {"ref_audio": "./prompt1.wav", "ref_text": "Reference text 1"}
    },
    "dialogue": [
        {"role": "0", "text": "Hello, this is speaker 0"},
        {"role": "1", "text": "Hi, this is speaker 1"}
    ]
}

audio_b64 = model.infer_with_prompt(input_json)
```

---

#### `Model.infer_with_prompt_streaming(js)`

Streaming inference with reference audio prompts.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `js` | dict | Input JSON with role_mapping and dialogue |

**Yields:**
- `str`: Base64-encoded MP3 audio chunks

---

#### `Model.infer_without_prompt(js)`

Inference without reference audio prompts (uses default voice).

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `js` | dict | Input JSON with dialogue only |

**Returns:**
- `str`: Base64-encoded MP3 audio data

**Example:**
```python
input_json = {
    "dialogue": [
        {"role": "0", "text": "Hello, this is speaker 0"},
        {"role": "1", "text": "Hi, this is speaker 1"}
    ]
}

audio_b64 = model.infer_without_prompt(input_json)
```

---

#### `Model.infer_without_prompt_streaming(js)`

Streaming inference without reference audio prompts.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `js` | dict | Input JSON with dialogue only |

**Yields:**
- `str`: Base64-encoded MP3 audio chunks

---

## Data Formats

### Dialogue JSON Format

```json
{
    "role_mapping": {
        "<role_id>": {
            "ref_audio": "<path_to_audio_file>",
            "ref_text": "<reference_text_for_asr>"
        }
    },
    "dialogue": [
        {
            "role": "<role_id>",
            "text": "<text_to_speak>"
        }
    ]
}
```

**Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `role_mapping` | dict | No | Maps role IDs to reference audio and text |
| `role_mapping.<role_id>.ref_audio` | str | Yes (if role_mapping exists) | Path to reference audio file |
| `role_mapping.<role_id>.ref_text` | str | Yes (if role_mapping exists) | Reference text for ASR alignment |
| `dialogue` | list | Yes | List of dialogue turns |
| `dialogue[].role` | str | Yes | Role ID ("0" or "1") |
| `dialogue[].text` | str | Yes | Text to be spoken |

**Constraints:**
- Roles must alternate (0, 1, 0, 1, ...)
- Each turn max 50 seconds of audio
- Reference audio should be clear speech samples

### Audio Format Specifications

| Format | Sample Rate | Channels | Encoding |
|--------|-------------|----------|----------|
| Input (reference) | 24kHz / 16kHz | Mono | WAV/MP3 |
| Output (generated) | 24kHz | Mono | MP3 (base64) |

---

## Script Generation

MoonCast includes LLM prompts for generating podcast scripts from documents.

### INPUT2BRIEF Prompt

Located in `zh_llmprompt_script_gen.py` (Chinese) and `en_llmprompt_script_gen.py` (English).

**Purpose:** Summarize input document into a structured brief.

**Structure:**
1. **Title and Author** - Document metadata and theme
2. **Abstract** - What, why, how, and results
3. **Main Themes and Concepts** - 3W principle (What, Why, How)
4. **Key Citations** - Argument, Evidence, Reasoning
5. **Conclusion** - Highlights and future directions

### BRIEF2SCRIPT Prompt

**Purpose:** Convert summary brief into podcast script.

**Output Format:**
```json
[
    {"speaker": "1", "text": "Host speaks here"},
    {"speaker": "2", "text": "Guest responds"}
]
```

**Requirements:**
- Conversational style with filler words
- Only commas, periods, question marks (no exclamation, ellipsis, parentheses, quotes)
- Speaker 1 = Host, Speaker 2 = Guest
- Max 3000 words, max 60 turns
- Each topic discussed for at least 4 turns

---

## Examples

### Complete Inference Example

```python
from inference import Model
import base64
import io
from pydub import AudioSegment

# Initialize model
model = Model()
model.generate_config.max_new_tokens = 50 * 50  # Max 50s per turn

# Prepare input
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

# Non-streaming inference
audio_b64 = model.inference(input_json)
with open("output.mp3", "wb") as f:
    f.write(base64.b64decode(audio_b64))

# Streaming inference
audio = AudioSegment.empty()
for chunk_b64 in model.inference(input_json, streaming=True):
    audio_chunk = AudioSegment.from_file(io.BytesIO(base64.b64decode(chunk_b64)), format="mp3")
    audio += audio_chunk
audio.export("output_stream.mp3", format="mp3")
```

### Gradio Web Interface

```python
# app.py deployment
CUDA_VISIBLE_DEVICES=0 python app.py
```

The Gradio interface provides:
- Role 0 and Role 1 prompt audio upload
- Reference text input for each role
- JSON dialogue input
- Streaming audio output
- Bilingual UI (Chinese/English)

---

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Role validation failed | Roles not alternating | Ensure dialogue alternates 0, 1, 0, 1... |
| Audio loading failed | Invalid audio path | Check file paths are correct |
| OOM (Out of Memory) | GPU memory exhausted | Reduce batch size or use streaming mode |
| Token limit exceeded | Text too long | Split into multiple turns (max 50s each) |

---

## License

MoonCast is released under the MIT License. See LICENSE file for details.

## Disclaimer

This project is intended for **research purposes only**. Users are strongly encouraged to use this project and its generated audio responsibly. The authors are not responsible for any misuse or abuse of this project.