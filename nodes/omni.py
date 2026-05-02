import torch

from ..constants import OMNI_MODELS
from ..helpers import tensor_to_base64_png, video_to_base64
from ..models import call_qwen_omni
from .base import DashScopeBaseNode


class DashScopeQwenOmniVideo(DashScopeBaseNode):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video": ("VIDEO", {"tooltip": "The video to analyse. Connect from a LoadVideo node or provide a file path."}),
                "prompt": ("STRING", {"default": "请详细描述这个视频的内容", "multiline": True, "tooltip": "What should the model do with this video?"}),
                "model": (OMNI_MODELS, {"default": "qwen3.5-omni-plus", "tooltip": "Qwen3.5-Omni for long videos (≤1h); Qwen3-Omni-Flash for short clips (≤150s)."}),
                "output_mode": (["text_only", "text_and_audio"], {"default": "text_only", "tooltip": "'text_only' returns text. 'text_and_audio' also outputs speech audio."}),
                "voice": (["Bella", "Tina"], {"default": "Tina", "tooltip": "Voice for audio output."}),
                "max_pixels": ("INT", {"default": 921600, "min": 230400, "max": 2073600, "step": 100, "tooltip": "Lower values = lower cost & faster. 230400: quick, 921600: standard, 2073600: fine."}),
            },
            "optional": {
                "image": ("IMAGE", {"tooltip": "Optional extra image for mixed-modal analysis."}),
                "system_prompt": ("STRING", {"default": "", "multiline": True, "tooltip": "Optional system-level instructions."}),
            },
        }

    RETURN_TYPES = ("STRING", "AUDIO")
    RETURN_NAMES = ("text_response", "audio")
    FUNCTION = "generate"
    CATEGORY = "api node/video/DashScope"
    OUTPUT_NODE = True

    def generate(
        self,
        video,
        prompt: str,
        model: str,
        output_mode: str = "text_only",
        voice: str = "Tina",
        max_pixels: int = 921600,
        image: torch.Tensor | None = None,
        system_prompt: str = "",
    ):
        if not self._api_key:
            raise ValueError("DashScope API Key is required. Get one from https://bailian.console.aliyun.com/")

        if isinstance(max_pixels, str):
            try:
                max_pixels = int(max_pixels)
            except ValueError:
                max_pixels = 921600

        content_parts: list[dict] = []
        data_uri = video_to_base64(video)
        content_parts.append({"type": "video_url", "video_url": {"url": data_uri}})

        if image is not None:
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": tensor_to_base64_png(image)},
            })

        content_parts.append({"type": "text", "text": prompt})

        modalities = ["text", "audio"] if output_mode == "text_and_audio" else ["text"]
        extra_body = {"max_pixels": max_pixels} if max_pixels else {}

        text, audio_dict = call_qwen_omni(
            api_key=self._api_key, model=model,
            content_parts=content_parts,
            modalities=modalities, voice=voice,
            extra_body=extra_body,
        )
        return {"ui": {"text": [text]}, "result": (text, audio_dict)}


class DashScopeQwenOmniImage(DashScopeBaseNode):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE", {"tooltip": "The image to analyse."}),
                "prompt": ("STRING", {"default": "请详细描述这张图片的内容", "multiline": True, "tooltip": "What should the model do with this image?"}),
                "model": (OMNI_MODELS, {"default": "qwen3.5-omni-plus", "tooltip": "Model to use."}),
                "output_mode": (["text_only", "text_and_audio"], {"default": "text_only", "tooltip": "Output text only, or text with spoken audio."}),
                "voice": (["Bella", "Tina"], {"default": "Tina", "tooltip": "Voice for audio output."}),
            },
            "optional": {
                "system_prompt": ("STRING", {"default": "", "multiline": True, "tooltip": "Optional system-level instructions."}),
            },
        }

    RETURN_TYPES = ("STRING", "AUDIO")
    RETURN_NAMES = ("text_response", "audio")
    FUNCTION = "generate"
    CATEGORY = "api node/image/DashScope"
    OUTPUT_NODE = True

    def generate(
        self,
        image: torch.Tensor,
        prompt: str,
        model: str,
        output_mode: str = "text_only",
        voice: str = "Tina",
        system_prompt: str = "",
    ):
        if not self._api_key:
            raise ValueError("DashScope API Key is required. Get one from https://bailian.console.aliyun.com/")

        content_parts = [
            {"type": "image_url", "image_url": {"url": tensor_to_base64_png(image)}},
            {"type": "text", "text": prompt},
        ]
        modalities = ["text", "audio"] if output_mode == "text_and_audio" else ["text"]

        text, audio_dict = call_qwen_omni(
            api_key=self._api_key, model=model,
            content_parts=content_parts,
            modalities=modalities, voice=voice,
        )
        return {"ui": {"text": [text]}, "result": (text, audio_dict)}
