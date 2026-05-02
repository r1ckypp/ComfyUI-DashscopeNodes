import os
import uuid

import torch

from ..constants import (
    COSYVOICE_FORMATS,
    COSYVOICE_MODELS,
    COSYVOICE_SAMPLE_RATES,
    COSYVOICE_VOICES,
    MINIMAX_AUDIO_FORMATS,
    MINIMAX_CLONE_LANGUAGES,
    MINIMAX_CLONE_MODELS,
    MINIMAX_EMOTIONS,
    MINIMAX_SAMPLE_RATES,
    MINIMAX_SPEECH_MODELS,
    QWEN_TTS_LANGUAGES,
    QWEN_TTS_MODELS,
    QWEN_TTS_VOICES,
)
from ..helpers import (
    audio_bytes_to_audio,
    audio_input_to_temp_file,
    download_url_to_audio,
    extract_audio_url_from_response,
)
from ..models import (
    CosyVoiceTTSInput,
    CosyVoiceTTSRequest,
    MiniMaxAudioSetting,
    MiniMaxCloneInput,
    MiniMaxClonePrompt,
    MiniMaxCloneRequest,
    MiniMaxSpeechInput,
    MiniMaxSpeechRequest,
    MiniMaxVoiceSetting,
    QwenTTSInput,
    QwenTTSParameters,
    QwenTTSRequest,
)
from .base import DashScopeBaseNode


class DashScopeQwenTTS(DashScopeBaseNode):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("COMBO", {"default": "qwen3-tts-flash", "options": QWEN_TTS_MODELS, "tooltip": "Qwen TTS model"}),
                "text": ("STRING", {"default": "", "multiline": True, "tooltip": "Text to synthesize. Max 512 tokens for qwen-tts, 600 chars for qwen3-tts series"}),
                "voice": ("COMBO", {"default": "Cherry", "options": QWEN_TTS_VOICES, "tooltip": "Voice / speaker name"}),
                "language_type": ("COMBO", {"default": "Auto", "options": QWEN_TTS_LANGUAGES, "tooltip": "Language hint. 'Auto' lets the model detect automatically"}),
            },
            "optional": {
                "instructions": ("STRING", {"default": "", "multiline": True, "tooltip": "Instruction for speech style control (max 1600 tokens). Only works with qwen3-tts-instruct-flash"}),
                "optimize_instructions": ("BOOLEAN", {"default": False, "tooltip": "Let the model optimize the instructions. Only works with qwen3-tts-instruct-flash"}),
            },
        }

    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio",)
    FUNCTION = "generate"
    CATEGORY = "api node/audio/DashScope"

    def generate(
        self,
        model: str,
        text: str,
        voice: str = "Cherry",
        language_type: str = "Auto",
        instructions: str = "",
        optimize_instructions: bool = False,
    ):
        model = self._validate_setup(model)
        if not text.strip():
            raise ValueError("Text must not be empty.")

        text_clean = text.strip()
        voice_clean = self._extract_str(voice)
        language_clean = self._extract_str(language_type)
        instructions_clean = self._extract_str(instructions) if instructions else None

        params = QwenTTSParameters(voice=voice_clean)
        if language_clean and language_clean != "Auto":
            params.language_type = language_clean
        if instructions_clean:
            params.instructions = instructions_clean
        if optimize_instructions:
            params.optimize_instructions = True

        body = QwenTTSRequest(model=model, input=QwenTTSInput(text=text_clean), parameters=params)
        data = self._client.post("/api/v1/services/aigc/multimodal-generation/generation", body)

        code = data.get("code", "")
        if code:
            raise Exception(f"DashScope API error: [{code}] {data.get('message', '')}")

        audio_url = extract_audio_url_from_response(data)
        if not audio_url:
            raise Exception("DashScope Qwen TTS returned no audio URL.")

        audio_dict = download_url_to_audio(audio_url, api_key=self._api_key)
        return {"ui": {"text": (audio_url,)}, "result": (audio_dict,)}


class DashScopeMiniMaxSpeech(DashScopeBaseNode):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("COMBO", {"default": "MiniMax/speech-2.8-hd", "options": MINIMAX_SPEECH_MODELS, "tooltip": "MiniMax speech model"}),
                "text": ("STRING", {"default": "", "multiline": True, "tooltip": "Text to synthesize (max ~10000 chars). >3000 chars recommended with streaming"}),
                "voice_id": ("STRING", {"default": "", "tooltip": "Voice ID. Use a cloned voice_id or a default system voice"}),
                "speed": ("FLOAT", {"default": 1.0, "min": 0.5, "max": 2.0, "step": 0.1, "tooltip": "Speech speed"}),
                "vol": ("FLOAT", {"default": 1.0, "min": 0.01, "max": 10.0, "step": 0.1, "tooltip": "Volume"}),
                "pitch": ("INT", {"default": 0, "min": -12, "max": 12, "step": 1, "tooltip": "Pitch shift in semitones"}),
                "format": ("COMBO", {"default": "mp3", "options": MINIMAX_AUDIO_FORMATS, "tooltip": "Output audio format"}),
                "sample_rate": ("COMBO", {"default": "32000", "options": [str(r) for r in MINIMAX_SAMPLE_RATES], "tooltip": "Audio sample rate in Hz"}),
                "output_format": ("COMBO", {"default": "url", "options": ["url", "hex"], "tooltip": "'url' returns a downloadable link; 'hex' returns raw hex-encoded data"}),
            },
            "optional": {
                "emotion": ("COMBO", {"default": "none", "options": MINIMAX_EMOTIONS, "tooltip": "Emotional tone. Only supported by speech-2.8-hd and speech-02-hd"}),
                "language_boost": ("STRING", {"default": "", "tooltip": "Boost recognition for specific language/dialect. Leave empty for auto. Example: Chinese, English, auto"}),
                "aigc_watermark": ("BOOLEAN", {"default": False, "tooltip": "Embed AIGC watermark in audio (non-streaming only)"}),
            },
        }

    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio",)
    FUNCTION = "generate"
    CATEGORY = "api node/audio/DashScope"

    def generate(
        self,
        model: str,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        vol: float = 1.0,
        pitch: int = 0,
        format: str = "mp3",
        sample_rate: str = "32000",
        output_format: str = "url",
        emotion: str = "none",
        language_boost: str = "",
        aigc_watermark: bool = False,
    ):
        model = self._validate_setup(model)
        if not text.strip():
            raise ValueError("Text must not be empty.")
        if not voice_id.strip():
            raise ValueError("voice_id is required.")

        sample_rate_int = int(sample_rate)

        voice_setting = MiniMaxVoiceSetting(voice_id=voice_id.strip())
        if speed != 1.0:
            voice_setting.speed = speed
        if vol != 1.0:
            voice_setting.vol = vol
        if pitch != 0:
            voice_setting.pitch = pitch
        if emotion and emotion != "none":
            voice_setting.emotion = emotion

        audio_setting = MiniMaxAudioSetting(format=format)
        if sample_rate_int != 32000:
            audio_setting.sample_rate = sample_rate_int

        speech_input = MiniMaxSpeechInput(
            text=text.strip(),
            voice_setting=voice_setting,
            audio_setting=audio_setting,
            output_format=output_format,
        )
        if language_boost.strip():
            speech_input.language_boost = language_boost.strip()
        if aigc_watermark:
            speech_input.aigc_watermark = True

        body = MiniMaxSpeechRequest(model=model, input=speech_input)
        data = self._client.post("/api/v1/services/aigc/multimodal-generation/generation", body)

        output = data.get("output") or {}
        base_resp = output.get("base_resp") or {}
        if base_resp.get("status_code", 0) != 0:
            raise Exception(f"MiniMax API error: [{base_resp.get('status_code')}] {base_resp.get('status_msg', '')}")

        if output_format == "url":
            audio_url = output.get("demo_audio") or ""
            if not audio_url:
                data_block = output.get("data") or {}
                audio_url = data_block.get("audio", "")
            if audio_url and (audio_url.startswith("http://") or audio_url.startswith("https://")):
                audio_dict = download_url_to_audio(audio_url, api_key=self._api_key)
                return {"ui": {"text": (audio_url,)}, "result": (audio_dict,)}
            raise Exception("MiniMax API returned no audio URL in 'url' output_format.")

        hex_audio = None
        data_block = output.get("data") or {}
        if data_block.get("audio"):
            hex_audio = data_block["audio"]

        if not hex_audio:
            raise Exception("MiniMax API returned no audio data.")

        audio_dict = audio_bytes_to_audio(bytes.fromhex(hex_audio), hint_suffix=f".{format}")
        return {"ui": {"text": (hex_audio[:64] + "...",), "result": (audio_dict,)}}


class DashScopeMiniMaxVoiceClone(DashScopeBaseNode):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("COMBO", {"default": "MiniMax/speech-2.8-hd", "options": MINIMAX_CLONE_MODELS, "tooltip": "Model for voice cloning"}),
                "audio_url": ("STRING", {"default": "", "multiline": True, "tooltip": "URL to source audio file to clone (mp3/m4a/wav, 10s~5min, ≤20MB). Use DashScopeFileUpload node to upload and get the URL"}),
                "text": ("STRING", {"default": "", "multiline": True, "tooltip": "Demo text to synthesize with the cloned voice (max 1000 chars)"}),
                "voice_id": ("STRING", {"default": "", "tooltip": "Custom cloned voice ID. 8-256 chars, start with a letter, allowed: letters/digits/-/_. Must be globally unique"}),
            },
            "optional": {
                "language_boost": ("COMBO", {"default": "auto", "options": MINIMAX_CLONE_LANGUAGES, "tooltip": "Boost recognition for specific language/dialect"}),
                "need_noise_reduction": ("BOOLEAN", {"default": False, "tooltip": "Apply noise reduction to source audio"}),
                "need_volume_normalization": ("BOOLEAN", {"default": False, "tooltip": "Normalize volume of source audio"}),
                "prompt_audio": ("STRING", {"default": "", "multiline": True, "tooltip": "Optional: URL to a prompt audio (mp3/m4a/wav, <8s, ≤20MB) for better voice similarity"}),
                "prompt_text": ("STRING", {"default": "", "multiline": True, "tooltip": "Text matching the prompt audio. Must match the audio content exactly"}),
            },
        }

    RETURN_TYPES = ("AUDIO", "STRING")
    RETURN_NAMES = ("audio", "voice_id")
    FUNCTION = "generate"
    CATEGORY = "api node/audio/DashScope"

    def generate(
        self,
        model: str,
        audio_url: str,
        text: str,
        voice_id: str,
        language_boost: str = "auto",
        need_noise_reduction: bool = False,
        need_volume_normalization: bool = False,
        prompt_audio: str = "",
        prompt_text: str = "",
    ):
        model = self._validate_setup(model)
        audio_url_clean = self._extract_str(audio_url)
        voice_id_clean = self._extract_str(voice_id)
        if not audio_url_clean:
            raise ValueError("Source audio URL is required.")
        if not text.strip():
            raise ValueError("Demo text is required.")
        if not voice_id_clean:
            raise ValueError("voice_id is required.")

        clone_input = MiniMaxCloneInput(
            audio_url=audio_url_clean,
            text=text.strip(),
            voice_id=voice_id_clean,
        )

        if language_boost and language_boost != "auto":
            clone_input.language_boost = language_boost
        if need_noise_reduction:
            clone_input.need_noise_reduction = True
        if need_volume_normalization:
            clone_input.need_volume_normalization = True

        prompt_audio_clean = self._extract_str(prompt_audio) if prompt_audio else ""
        prompt_text_clean = self._extract_str(prompt_text) if prompt_text else ""
        if prompt_audio_clean and prompt_text_clean:
            clone_input.clone_prompt = MiniMaxClonePrompt(
                prompt_audio=prompt_audio_clean,
                prompt_text=prompt_text_clean,
            )

        body = MiniMaxCloneRequest(model=model, input=clone_input)

        extra = {"X-DashScope-OssResourceResolve": "enable"} if audio_url_clean.startswith("oss://") else {}
        extra["Content-Type"] = "application/json; charset=utf-8"
        data = self._client.post("/api/v1/services/aigc/multimodal-generation/generation", body, **extra)

        output = data.get("output") or {}
        base_resp = output.get("base_resp") or {}
        if base_resp.get("status_code", 0) != 0:
            raise Exception(f"MiniMax voice clone error: [{base_resp.get('status_code')}] {base_resp.get('status_msg', '')}")

        if output.get("input_sensitive"):
            sensitive_type = output.get("input_sensitive_type", "")
            raise Exception(f"Source audio flagged by content moderation (type={sensitive_type}). Use a different audio file.")

        demo_audio_url = output.get("demo_audio") or ""
        if not demo_audio_url:
            raise Exception("MiniMax voice clone returned no demo audio URL.")

        audio_dict = download_url_to_audio(demo_audio_url, api_key=self._api_key)
        return {"ui": {"text": (demo_audio_url, voice_id_clean)}, "result": (audio_dict, voice_id_clean)}


class DashScopeCosyVoiceTTS(DashScopeBaseNode):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("COMBO", {"default": "cosyvoice-v3.5-flash", "options": COSYVOICE_MODELS, "tooltip": "CosyVoice model"}),
                "text": ("STRING", {"default": "", "multiline": True, "tooltip": "Text to synthesize. Support SSML when enable_ssml is on"}),
                "voice": ("COMBO", {"default": "longxiaochun", "options": COSYVOICE_VOICES, "tooltip": "Voice / speaker name"}),
                "format": ("COMBO", {"default": "mp3", "options": COSYVOICE_FORMATS, "tooltip": "Output audio format"}),
                "sample_rate": ("COMBO", {"default": "22050", "options": [str(r) for r in COSYVOICE_SAMPLE_RATES], "tooltip": "Audio sample rate in Hz"}),
                "volume": ("INT", {"default": 50, "min": 0, "max": 100, "step": 1, "tooltip": "Volume (0-100)"}),
                "rate": ("FLOAT", {"default": 1.0, "min": 0.5, "max": 2.0, "step": 0.05, "tooltip": "Speech speed"}),
                "pitch": ("FLOAT", {"default": 1.0, "min": 0.5, "max": 2.0, "step": 0.05, "tooltip": "Pitch adjustment"}),
            },
            "optional": {
                "enable_ssml": ("BOOLEAN", {"default": False, "tooltip": "Enable SSML parsing in the input text"}),
                "instruction": ("STRING", {"default": "", "multiline": True, "tooltip": "Control emotion/dialect/style (max 100 chars). Supports differ by model"}),
                "enable_aigc_tag": ("BOOLEAN", {"default": False, "tooltip": "Embed AIGC watermark. Only v2/v3-flash/v3-plus support this"}),
            },
        }

    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio",)
    FUNCTION = "generate"
    CATEGORY = "api node/audio/DashScope"

    def generate(
        self,
        model: str,
        text: str,
        voice: str = "longxiaochun",
        format: str = "mp3",
        sample_rate: str = "22050",
        volume: int = 50,
        rate: float = 1.0,
        pitch: float = 1.0,
        enable_ssml: bool = False,
        instruction: str = "",
        enable_aigc_tag: bool = False,
    ):
        model = self._validate_setup(model)
        if not text.strip():
            raise ValueError("Text must not be empty.")

        sample_rate_int = int(sample_rate)
        voice_clean = self._extract_str(voice)
        instruction_clean = self._extract_str(instruction) if instruction else None

        tts_input = CosyVoiceTTSInput(
            text=text.strip(),
            voice=voice_clean,
            format=format,
            sample_rate=sample_rate_int,
            volume=volume,
            rate=rate,
            pitch=pitch,
        )
        if enable_ssml:
            tts_input.enable_ssml = True
        if instruction_clean:
            tts_input.instruction = instruction_clean
        if enable_aigc_tag:
            tts_input.enable_aigc_tag = True

        body = CosyVoiceTTSRequest(model=model, input=tts_input)
        data = self._client.post("/api/v1/services/audio/tts/SpeechSynthesizer", body)

        code = data.get("code", "")
        if code:
            raise Exception(f"DashScope API error: [{code}] {data.get('message', '')}")

        audio_url = extract_audio_url_from_response(data)
        if not audio_url:
            raise Exception("CosyVoice TTS returned no audio URL.")

        audio_dict = download_url_to_audio(audio_url, api_key=self._api_key)
        return {"ui": {"text": (audio_url,)}, "result": (audio_dict,)}


class DashScopeAudioUpload(DashScopeBaseNode):
    """Upload audio to DashScope temporary OSS and return oss:// URL."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("COMBO", {"default": "MiniMax/speech-2.8-hd", "options": MINIMAX_CLONE_MODELS, "tooltip": "Target model — must match the model you will use the URL with"}),
            },
            "optional": {
                "audio": ("AUDIO", {"tooltip": "Audio to upload. Connect AUDIO output from Load Audio or other nodes"}),
                "file_path": ("STRING", {"default": "", "multiline": True, "tooltip": "Path to audio file to upload. Use this OR the audio input"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("audio_url",)
    FUNCTION = "upload"
    CATEGORY = "api node/upload/DashScope"

    def upload(self, model: str, audio=None, file_path: str = ""):
        model = self._validate_setup(model)

        if audio is not None:
            tmp_path = audio_input_to_temp_file(audio)
            try:
                url = self._upload_file(tmp_path, model)
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        elif file_path and self._extract_str(file_path):
            path = self._extract_str(file_path)
            if not os.path.exists(path):
                raise ValueError(f"Audio file not found: {path}")
            url = self._upload_file(path, model)
        else:
            raise ValueError("Provide either an AUDIO input or a file_path to the audio file.")

        return {"ui": {"text": (url,)}, "result": (url,)}

    def _upload_file(self, file_path: str, model: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        mime_map = {
            ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4",
            ".flac": "audio/flac", ".ogg": "audio/ogg", ".opus": "audio/opus",
        }
        content_type = mime_map.get(ext, "audio/mpeg")
        filename = f"comfyui_{uuid.uuid4().hex[:8]}{ext}"

        with open(file_path, "rb") as f:
            return self._client.upload(f.read(), filename, model, content_type)
