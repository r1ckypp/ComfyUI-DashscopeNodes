from __future__ import annotations

import base64

import numpy as np
from pydantic import BaseModel, Field


# ── Text-to-Image ──────────────────────────────────────────────────

class ContentItem(BaseModel):
    text: str | None = Field(None)
    image: str | None = Field(None)


class Message(BaseModel):
    role: str = Field(default="user")
    content: list[ContentItem] = Field(...)


class Text2ImageInput(BaseModel):
    messages: list[Message] = Field(...)


class ColorPaletteItem(BaseModel):
    hex: str = Field(...)
    ratio: str = Field(...)


class Text2ImageParameters(BaseModel):
    size: str | None = Field(None)
    n: int | None = Field(None)
    seed: int | None = Field(None)
    watermark: bool | None = Field(None)
    enable_sequential: bool | None = Field(None)
    thinking_mode: bool | None = Field(None)
    color_palette: list[ColorPaletteItem] | None = Field(None)
    bbox_list: list[list[list[int]]] | None = Field(None)


class Text2ImageRequest(BaseModel):
    model: str = Field(...)
    input: Text2ImageInput = Field(...)
    parameters: Text2ImageParameters = Field(default_factory=Text2ImageParameters)


# ── Response models ─────────────────────────────────────────────────

class OutputContent(BaseModel):
    image: str | None = Field(None)
    text: str | None = Field(None)
    type: str | None = Field(None)


class OutputMessage(BaseModel):
    role: str | None = Field(None)
    content: list[OutputContent] | None = Field(None)


class Choice(BaseModel):
    finish_reason: str | None = Field(None)
    message: OutputMessage | None = Field(None)


class SyncResponseOutput(BaseModel):
    choices: list[Choice] | None = Field(None)
    finished: bool | None = Field(None)


class SyncResponse(BaseModel):
    output: SyncResponseOutput | None = Field(None)
    request_id: str | None = Field(None)
    code: str | None = Field(None)
    message: str | None = Field(None)


class TaskCreateOutput(BaseModel):
    task_id: str | None = Field(None)
    task_status: str | None = Field(None)


class TaskCreateResponse(BaseModel):
    output: TaskCreateOutput | None = Field(None)
    request_id: str | None = Field(None)
    code: str | None = Field(None)
    message: str | None = Field(None)


class TaskQueryOutput(SyncResponseOutput):
    task_id: str | None = Field(None)
    task_status: str | None = Field(None)
    code: str | None = Field(None)
    message: str | None = Field(None)


class TaskQueryResponse(BaseModel):
    output: TaskQueryOutput | None = Field(None)
    request_id: str | None = Field(None)
    code: str | None = Field(None)
    message: str | None = Field(None)


# ── Video generation ────────────────────────────────────────────────

class MediaItem(BaseModel):
    type: str = Field(...)
    url: str = Field(...)


class VideoGenerationInput(BaseModel):
    prompt: str = Field(...)
    media: list[MediaItem] | None = Field(None)


class VideoGenerationParameters(BaseModel):
    resolution: str | None = Field(None)
    ratio: str | None = Field(None)
    duration: int | None = Field(None)
    watermark: bool | None = Field(None)
    seed: int | None = Field(None)


class I2VParameters(BaseModel):
    resolution: str | None = Field(None)
    duration: int | None = Field(None)
    watermark: bool | None = Field(None)
    seed: int | None = Field(None)


class VideoGenerationRequest(BaseModel):
    model: str = Field(...)
    input: VideoGenerationInput = Field(...)
    parameters: VideoGenerationParameters = Field(default_factory=VideoGenerationParameters)


class I2VRequest(BaseModel):
    model: str = Field(...)
    input: VideoGenerationInput = Field(...)
    parameters: I2VParameters = Field(default_factory=I2VParameters)


class VideoQueryOutput(BaseModel):
    task_id: str | None = Field(None)
    task_status: str | None = Field(None)
    code: str | None = Field(None)
    message: str | None = Field(None)
    submit_time: str | None = Field(None)
    scheduled_time: str | None = Field(None)
    end_time: str | None = Field(None)
    video_url: str | None = Field(None)
    orig_prompt: str | None = Field(None)


class VideoEditParameters(BaseModel):
    resolution: str | None = Field(None)
    watermark: bool | None = Field(None)
    audio_setting: str | None = Field(None)
    seed: int | None = Field(None)


class VideoEditRequest(BaseModel):
    model: str = Field(...)
    input: VideoGenerationInput = Field(...)
    parameters: VideoEditParameters = Field(default_factory=VideoEditParameters)


class VideoQueryUsage(BaseModel):
    duration: int | None = Field(None)
    input_video_duration: int | None = Field(None)
    output_video_duration: int | None = Field(None)
    video_count: int | None = Field(None)
    SR: int | None = Field(None)
    ratio: str | None = Field(None)


class VideoQueryResponse(BaseModel):
    output: VideoQueryOutput | None = Field(None)
    request_id: str | None = Field(None)
    code: str | None = Field(None)
    message: str | None = Field(None)
    usage: VideoQueryUsage | None = Field(None)


# ── Qwen TTS ────────────────────────────────────────────────────────

class QwenTTSInput(BaseModel):
    text: str = Field(...)


class QwenTTSParameters(BaseModel):
    voice: str = Field(...)
    language_type: str | None = Field(None)
    instructions: str | None = Field(None)
    optimize_instructions: bool | None = Field(None)


class QwenTTSRequest(BaseModel):
    model: str = Field(...)
    input: QwenTTSInput = Field(...)
    parameters: QwenTTSParameters = Field(default_factory=lambda: QwenTTSParameters(voice="Cherry"))


# ── MiniMax Speech ──────────────────────────────────────────────────

class MiniMaxVoiceSetting(BaseModel):
    voice_id: str = Field(...)
    speed: float | None = Field(None)
    vol: float | None = Field(None)
    pitch: int | None = Field(None)
    emotion: str | None = Field(None)
    text_normalization: bool | None = Field(None)
    latex_read: bool | None = Field(None)


class MiniMaxAudioSetting(BaseModel):
    sample_rate: int | None = Field(None)
    bitrate: int | None = Field(None)
    format: str | None = Field(None)
    channel: int | None = Field(None)


class MiniMaxSpeechInput(BaseModel):
    text: str = Field(...)
    voice_setting: MiniMaxVoiceSetting = Field(...)
    audio_setting: MiniMaxAudioSetting | None = Field(None)
    language_boost: str | None = Field(None)
    output_format: str | None = Field(None)
    aigc_watermark: bool | None = Field(None)
    subtitle_enable: bool | None = Field(None)


class MiniMaxSpeechRequest(BaseModel):
    model: str = Field(...)
    input: MiniMaxSpeechInput = Field(...)


# ── MiniMax Voice Clone ─────────────────────────────────────────────

class MiniMaxClonePrompt(BaseModel):
    prompt_audio: str | None = Field(None)
    prompt_text: str | None = Field(None)


class MiniMaxCloneInput(BaseModel):
    action: str = Field(default="voice_clone")
    audio_url: str = Field(...)
    text: str = Field(...)
    voice_id: str = Field(...)
    clone_prompt: MiniMaxClonePrompt | None = Field(None)
    language_boost: str | None = Field(None)
    need_noise_reduction: bool | None = Field(None)
    need_volume_normalization: bool | None = Field(None)
    aigc_watermark: bool | None = Field(None)


class MiniMaxCloneRequest(BaseModel):
    model: str = Field(...)
    input: MiniMaxCloneInput = Field(...)


# ── CosyVoice TTS ───────────────────────────────────────────────────

class CosyVoiceTTSInput(BaseModel):
    text: str = Field(...)
    voice: str = Field(...)
    format: str | None = Field(None)
    sample_rate: int | None = Field(None)
    volume: int | None = Field(None)
    rate: float | None = Field(None)
    pitch: float | None = Field(None)
    enable_ssml: bool | None = Field(None)
    seed: int | None = Field(None)
    language_hints: list[str] | None = Field(None)
    instruction: str | None = Field(None)
    enable_aigc_tag: bool | None = Field(None)
    enable_markdown_filter: bool | None = Field(None)


class CosyVoiceTTSRequest(BaseModel):
    model: str = Field(...)
    input: CosyVoiceTTSInput = Field(...)


# ── Qwen Omni ───────────────────────────────────────────────────────

def call_qwen_omni(
    api_key: str,
    model: str,
    content_parts: list[dict],
    modalities: list[str],
    voice: str,
    extra_body: dict | None = None,
) -> tuple[str, dict]:
    from openai import OpenAI

    import torch

    client = OpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    kwargs = dict(
        model=model,
        messages=[{"role": "user", "content": content_parts}],
        stream=True,
        stream_options={"include_usage": True},
        modalities=modalities,
    )
    if "audio" in modalities:
        kwargs["audio"] = {"voice": voice, "format": "wav"}
    if extra_body:
        kwargs["extra_body"] = extra_body

    completion = client.chat.completions.create(**kwargs)

    text_parts = []
    audio_base64 = ""

    for chunk in completion:
        if chunk.choices:
            delta = chunk.choices[0].delta
            if hasattr(delta, "content") and delta.content:
                text_parts.append(delta.content)
            if hasattr(delta, "audio") and delta.audio:
                data = delta.audio
                if isinstance(data, dict):
                    audio_base64 += data.get("data", "")
                elif hasattr(data, "data"):
                    audio_base64 += data.data

    text = "".join(text_parts).strip()
    if not text:
        text = "Qwen Omni returned an empty response."

    if audio_base64:
        wav_bytes = base64.b64decode(audio_base64)
        audio_np = np.frombuffer(wav_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        waveform = torch.from_numpy(audio_np).unsqueeze(0).unsqueeze(0)
        audio_dict = {"waveform": waveform, "sample_rate": 24000}
    else:
        waveform = torch.zeros(1, 1, 1)
        audio_dict = {"waveform": waveform, "sample_rate": 24000}

    return text, audio_dict
