import time

import torch

from ..constants import SIZES, T2I_MODELS
from ..helpers import download_url_to_image_tensor, extract_image_url_from_async, extract_image_url_from_sync, image_tensor_to_base64_list
from ..models import ColorPaletteItem, ContentItem, Message, Text2ImageInput, Text2ImageParameters, Text2ImageRequest
from .base import DashScopeBaseNode


class DashScopeTextToImage(DashScopeBaseNode):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("COMBO", {"default": "wan2.7-image-pro", "options": T2I_MODELS, "tooltip": "Model: wan2.7-image-pro (high quality) or wan2.7-image (fast)"}),
                "prompt": ("STRING", {"default": "", "multiline": True, "tooltip": "Text prompt, Chinese/English, max 5000 characters"}),
                "size": ("COMBO", {"default": "2K", "options": SIZES, "tooltip": "Output resolution: 1K=1024², 2K=2048², 4K=4096²"}),
                "n": ("STRING", {"default": "1", "tooltip": "Number of images: 1-4 for single mode, 1-12 for sequential mode"}),
                "seed": ("STRING", {"default": "0", "tooltip": "Random seed (0=random). Same seed gives similar results but not identical"}),
                "watermark": ("BOOLEAN", {"default": False, "tooltip": "Add 'AI生成' watermark at bottom-right corner"}),
                "enable_sequential": ("BOOLEAN", {"default": False, "tooltip": "Group/sequential generation mode. True = output multiple related images; requires n>1"}),
                "thinking_mode": ("BOOLEAN", {"default": True, "tooltip": "Enhanced reasoning for better quality. Only works when no reference images are provided"}),
            },
            "optional": {
                "reference_images": ("IMAGE", {"tooltip": "Reference images for image-to-image / style reference / image editing (max 9). Connect IMAGE output from Load Image or other nodes"}),
                "color_palette": ("STRING", {"default": "", "multiline": True, "tooltip": "Custom color theme in JSON: [{\"hex\":\"#C2D1E6\",\"ratio\":\"25.00%\"},...]. 3-10 colors, ratios must sum to 100%"}),
                "bbox_list": ("STRING", {"default": "", "multiline": True, "tooltip": "Interactive editing bounding boxes in JSON: [[[x1,y1,x2,y2]],...]. One array per reference image, empty [] for unedited images"}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "generate"
    CATEGORY = "api node/image/DashScope"

    def generate(
        self,
        model: str,
        prompt: str,
        size: str = "2K",
        n: str = "1",
        seed: str = "0",
        watermark: bool = False,
        enable_sequential: bool = False,
        thinking_mode: bool = True,
        reference_images: torch.Tensor | None = None,
        color_palette: str = "",
        bbox_list: str = "",
    ):
        start_ts = time.monotonic()
        model = self._validate_setup(model)
        if not prompt.strip():
            raise ValueError("Prompt must not be empty.")

        n_val = self._parse_int(n)
        seed_val = self._parse_seed(seed)

        content = [ContentItem(text=prompt)]
        if reference_images is not None and reference_images.shape[0] > 0:
            if reference_images.shape[0] > 9:
                raise ValueError(f"Maximum 9 reference images allowed, got {reference_images.shape[0]}.")
            for b64_uri in image_tensor_to_base64_list(reference_images):
                content.append(ContentItem(image=b64_uri))

        body = Text2ImageRequest(
            model=model,
            input=Text2ImageInput(messages=[Message(role="user", content=content)]),
            parameters=Text2ImageParameters(
                size=size,
                n=n_val,
                seed=seed_val if seed_val > 0 else None,
                watermark=watermark,
                enable_sequential=enable_sequential if enable_sequential else None,
                thinking_mode=thinking_mode if not thinking_mode else None,
                color_palette=self._build_color_palette(color_palette),
                bbox_list=self._parse_json(bbox_list),
            ),
        )

        data = self._client.post("/api/v1/services/aigc/multimodal-generation/generation", body)
        url_result = extract_image_url_from_sync(data)
        if not url_result:
            raise Exception("DashScope API returned no image URL.")

        time_str = self._report_done(start_ts)
        return {"ui": {"text": [f"execution_time: {time_str}"]}, "result": (download_url_to_image_tensor(url_result, api_key=self._api_key),)}

    @staticmethod
    def _build_color_palette(raw):
        parsed = DashScopeBaseNode._parse_json(raw)
        if parsed is None:
            return None
        if isinstance(parsed, list):
            items = []
            for entry in parsed:
                if isinstance(entry, dict):
                    items.append(ColorPaletteItem(hex=entry.get("hex", ""), ratio=entry.get("ratio", "")))
            return items if items else None
        return None


class DashScopeTextToImageAsync(DashScopeBaseNode):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("COMBO", {"default": "wan2.7-image-pro", "options": T2I_MODELS, "tooltip": "Model: wan2.7-image-pro (high quality) or wan2.7-image (fast)"}),
                "prompt": ("STRING", {"default": "", "multiline": True, "tooltip": "Text prompt, Chinese/English, max 5000 characters"}),
                "size": ("COMBO", {"default": "2K", "options": SIZES, "tooltip": "Output resolution: 1K=1024², 2K=2048², 4K=4096²"}),
                "n": ("STRING", {"default": "1", "tooltip": "Number of images: 1-4 for single mode, 1-12 for sequential mode"}),
                "seed": ("STRING", {"default": "0", "tooltip": "Random seed (0=random). Same seed gives similar results but not identical"}),
                "watermark": ("BOOLEAN", {"default": False, "tooltip": "Add 'AI生成' watermark at bottom-right corner"}),
                "enable_sequential": ("BOOLEAN", {"default": False, "tooltip": "Group/sequential generation mode. True = output multiple related images"}),
                "thinking_mode": ("BOOLEAN", {"default": True, "tooltip": "Enhanced reasoning for better quality. Only works when no reference images are provided"}),
            },
            "optional": {
                "reference_images": ("IMAGE", {"tooltip": "Reference images for image-to-image / style reference / image editing (max 9). Connect IMAGE output from Load Image or other nodes"}),
                "color_palette": ("STRING", {"default": "", "multiline": True, "tooltip": "Custom color theme in JSON: [{\"hex\":\"#C2D1E6\",\"ratio\":\"25.00%\"},...]. 3-10 colors, ratios must sum to 100%"}),
                "bbox_list": ("STRING", {"default": "", "multiline": True, "tooltip": "Interactive editing bounding boxes in JSON: [[[x1,y1,x2,y2]],...]. One array per reference image"}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "generate"
    CATEGORY = "api node/image/DashScope"

    def generate(
        self,
        model: str,
        prompt: str,
        size: str = "2K",
        n: str = "1",
        seed: str = "0",
        watermark: bool = False,
        enable_sequential: bool = False,
        thinking_mode: bool = True,
        reference_images: torch.Tensor | None = None,
        color_palette: str = "",
        bbox_list: str = "",
    ):
        model = self._validate_setup(model)
        if not prompt.strip():
            raise ValueError("Prompt must not be empty.")

        n_val = self._parse_int(n)
        seed_val = self._parse_seed(seed)

        content = [ContentItem(text=prompt)]
        if reference_images is not None and reference_images.shape[0] > 0:
            if reference_images.shape[0] > 9:
                raise ValueError(f"Maximum 9 reference images allowed, got {reference_images.shape[0]}.")
            for b64_uri in image_tensor_to_base64_list(reference_images):
                content.append(ContentItem(image=b64_uri))

        body = Text2ImageRequest(
            model=model,
            input=Text2ImageInput(messages=[Message(role="user", content=content)]),
            parameters=Text2ImageParameters(
                size=size,
                n=n_val,
                seed=seed_val if seed_val > 0 else None,
                watermark=watermark,
                enable_sequential=enable_sequential if enable_sequential else None,
                thinking_mode=thinking_mode if not thinking_mode else None,
                color_palette=self._build_color_palette(color_palette),
                bbox_list=self._parse_json(bbox_list),
            ),
        )

        task_id = self._client.post_async("/api/v1/services/aigc/image-generation/generation", body)
        start_ts = time.monotonic()
        task_output, time_str = self._client.poll(task_id, poll_interval=3.0, label="image")

        url_result = extract_image_url_from_async({"output": task_output})
        if not url_result:
            raise Exception("DashScope API task succeeded but returned no image URL.")

        elapsed = time.monotonic() - start_ts
        time_str = f"{elapsed:.1f}s"
        self._report_done(start_ts)
        return {"ui": {"text": [f"execution_time: {time_str}"]}, "result": (download_url_to_image_tensor(url_result, api_key=self._api_key),)}

    @staticmethod
    def _build_color_palette(raw):
        return DashScopeTextToImage._build_color_palette(raw)
