# DashScope Nodes for ComfyUI

阿里云 DashScope API 的 ComfyUI 自定义节点，覆盖文生图、视频生成、视频/图像理解、语音合成与声音克隆。

## 可用节点（14 个）

### 图像
| 节点名称 | 功能 | 类别 |
|---------|------|------|
| DashScope Text to Image | 文生图（同步），支持参考图、色彩调色板、区域编辑 | `api node/image/DashScope` |
| DashScope Text to Image (Async) | 文生图（异步），适合大批量生成 | `api node/image/DashScope` |

### 视频
| 节点名称 | 功能 | 类别 |
|---------|------|------|
| DashScope HappyHorse Text to Video | 文生视频 | `api node/video/DashScope` |
| DashScope HappyHorse Image to Video (First Frame) | 首帧图生视频 | `api node/video/DashScope` |
| DashScope HappyHorse Reference to Video | 多参考图生视频 | `api node/video/DashScope` |
| DashScope HappyHorse Video Edit | 视频编辑 | `api node/video/DashScope` |

### 理解（Qwen Omni）
| 节点名称 | 功能 | 类别 |
|---------|------|------|
| DashScope Qwen Omni - Image Understanding | 图像理解，支持语音输出 | `api node/image/DashScope` |
| DashScope Qwen Omni - Video Understanding | 视频理解，支持语音输出 | `api node/video/DashScope` |

### 语音合成（TTS）
| 节点名称 | 功能 | 类别 |
|---------|------|------|
| DashScope Qwen TTS | Qwen 文本转语音 | `api node/audio/DashScope` |
| DashScope MiniMax Speech Synthesis | MiniMax 语音合成（支持情感/音调/速度控制） | `api node/audio/DashScope` |
| DashScope MiniMax Voice Clone | MiniMax 声音克隆 | `api node/audio/DashScope` |
| DashScope CosyVoice TTS | CosyVoice 文本转语音（支持 SSML） | `api node/audio/DashScope` |

### 上传
| 节点名称 | 功能 | 类别 |
|---------|------|------|
| DashScope File Upload (to OSS) | 上传图片/视频到 DashScope OSS，生成 `oss://` URL | `api node/upload/DashScope` |
| DashScope Audio Upload (to OSS) | 上传音频到 DashScope OSS，生成 `oss://` URL | `api node/upload/DashScope` |

## 安装

1. 克隆到 ComfyUI 的 `custom_nodes` 目录：

```bash
cd ComfyUI/custom_nodes
git clone <repo-url> dashscope_nodes
```

2. 安装依赖：

```bash
cd dashscope_nodes
pip install -r requirements.txt
```

## 配置 API Key

从 [阿里云百炼平台](https://bailian.console.aliyun.com/) 获取 DashScope API Key，设置环境变量：

```bash
export DASHSCOPE_API_KEY="your-api-key-here"
```

## 模型说明

### 文生图

| 模型 | 说明 |
|------|------|
| `wan2.7-image-pro` | 高质量模式 |
| `wan2.7-image` | 快速模式 |

输出分辨率: 1K (1024²), 2K (2048²), 4K (4096²)

### 视频生成

| 模型 | 用途 |
|------|------|
| `happyhorse-1.0-t2v` | 文生视频 |
| `happyhorse-1.0-i2v` | 图生视频（首帧） |
| `happyhorse-1.0-r2v` | 参考图生视频 |
| `happyhorse-1.0-video-edit` | 视频编辑 |

输出分辨率: 720P, 1080P · 宽高比: 16:9, 9:16, 1:1, 4:3, 3:4 · 时长: 3-15 秒

### 理解（Qwen Omni）

| 模型 | 说明 |
|------|------|
| `qwen3.5-omni-plus` | 全能模型，支持长视频（≤1h） |
| `qwen3-omni-flash` | 快速模型，适合短视频（≤150s） |

### 语音合成

**Qwen TTS**: `qwen3-tts-flash`, `qwen3-tts-instruct-flash`, `qwen-tts`

**MiniMax Speech**: `MiniMax/speech-2.8-hd`, `MiniMax/speech-02-hd`, `MiniMax/speech-2.8-turbo`, `MiniMax/speech-02-turbo`

**CosyVoice**: `cosyvoice-v3.5-plus`, `cosyvoice-v3.5-flash`, `cosyvoice-v3-plus`, `cosyvoice-v3-flash`, `cosyvoice-v2`

## 节点详解

### DashScope Text to Image / (Async)

| 参数 | 类型 | 说明 |
|------|------|------|
| `prompt` | STRING | 文本提示词，中英文均可，最长 5000 字符 |
| `size` | COMBO | 输出分辨率: 1K / 2K / 4K |
| `n` | STRING | 生成数量: 普通 1-4，连续 1-12 |
| `seed` | STRING | 随机种子（0=随机） |
| `watermark` | BOOLEAN | 右下角"AI生成"水印 |
| `enable_sequential` | BOOLEAN | 开启连续/组图模式 |
| `thinking_mode` | BOOLEAN | 增强推理（无参考图时可用） |

可选: `reference_images` (IMAGE, 最多 9 张), `color_palette` (JSON), `bbox_list` (JSON)

色彩调色板示例:
```json
[{"hex":"#C2D1E6","ratio":"25.00%"},{"hex":"#FFB5C2","ratio":"25.00%"},{"hex":"#D4E5C2","ratio":"25.00%"},{"hex":"#FFF5C2","ratio":"25.00%"}]
```
> 3-10 种颜色，占比总和必须为 100%。

### HappyHorse 视频系列

**Text to Video** — 文本生成视频。**Image to Video** — 首帧图片 + 文本生成视频。**Reference to Video** — 多张参考图（最多 9 张）+ 文本生成视频。**Video Edit** — 编辑输入视频，可选参考图（最多 5 张）。`audio_setting`: `auto`（AI 生成）/ `origin`（保留原音频）。

> 所有视频节点需要 `oss://` URL 作为媒体输入，使用 **DashScope File Upload** 节点上传获取。

### Qwen Omni 理解系列

**Image Understanding**: 输入图片 + 提示词 → 文本 + 可选语音。`output_mode`: `text_only` / `text_and_audio`。`voice`: Bella / Tina。

**Video Understanding**: 输入视频（≤10MB base64）+ 提示词 → 文本 + 可选语音。`max_pixels` 控制开销: 230400（快）/ 921600（标准）/ 2073600（精细）。支持可选 `system_prompt` 和 `image`（混合模态）。

### TTS / 语音合成

**DashScope Qwen TTS**: 文本转语音，支持多语言。可选 `instructions` 控制风格（qwen3-tts-instruct-flash）。

**DashScope MiniMax Speech**: 高表现力语音合成，支持 `speed`/`pitch`/`vol` 控制、`emotion` 情感（happy/sad/angry 等）、`output_format`: `url`（下载链接）或 `hex`（十六进制数据）。

**DashScope MiniMax Voice Clone**: 上传音频样本 → 克隆声音。需要 `voice_id`（8-256 字符，全局唯一）。可选 `prompt_audio` + `prompt_text` 提升相似度。

**DashScope CosyVoice TTS**: 文本转语音，支持 SSML、`rate`/`pitch` 控制、AIGC 水印。

### 上传节点

**DashScope File Upload**: 上传图片（最多 5 张）→ 输出 `oss://` URL，供视频节点使用。

**DashScope Audio Upload**: 上传音频（AUDIO 输入或文件路径）→ 输出 `oss://` URL，供声音克隆使用。

## 文件结构

```
dashscope_nodes/
├── __init__.py          # 节点注册与映射
├── constants.py         # URL 路径、模型列表、选项常量
├── models.py            # Pydantic 请求/响应模型 + Qwen Omni 调用
├── client.py            # DashScopeClient — 统一 HTTP/轮询/上传
├── helpers.py           # 数据格式转换工具
├── exceptions.py        # 自定义异常
├── api.py               # 向后兼容重导出（指向 models.py）
└── nodes/
    ├── __init__.py      # 节点类导出
    ├── base.py          # DashScopeBaseNode — 共享校验/进度/客户端
    ├── image.py         # TextToImage + TextToImageAsync
    ├── video.py         # HappyHorse 系列 + FileUpload
    ├── audio.py         # QwenTTS + MiniMaxSpeech + MiniMaxClone + CosyVoice + AudioUpload
    └── omni.py          # QwenOmniVideo + QwenOmniImage
```

### 架构说明

- **`DashScopeBaseNode`** (`nodes/base.py`) — 节点基类，提供 API Key 校验、模型名解析、进度上报、客户端访问，所有 14 个节点继承此类。
- **`DashScopeClient`** (`client.py`) — 统一 HTTP 客户端，封装请求/响应错误处理、异步任务轮询、OSS 上传策略获取与文件上传。
- **添加新节点**: 在 `nodes/` 下创建文件 → 继承 `DashScopeBaseNode` → 定义 `INPUT_TYPES` / `RETURN_TYPES` → 调用 `self._client.post(...)` 即可。
