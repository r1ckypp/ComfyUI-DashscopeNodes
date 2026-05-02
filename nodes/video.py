import os
import uuid
from io import BytesIO

import torch

from ..constants import (
    I2V_MODELS,
    R2V_MODELS,
    RATIOS,
    RESOLUTIONS,
    T2V_MODELS,
    UPLOAD_MODELS,
    VED_MODELS,
)
from ..helpers import download_url_to_video_path, image_tensor_to_base64_list
from ..models import (
    I2VParameters,
    I2VRequest,
    MediaItem,
    VideoEditParameters,
    VideoEditRequest,
    VideoGenerationInput,
    VideoGenerationParameters,
    VideoGenerationRequest,
)
from .base import DashScopeBaseNode


class DashScopeFileUpload(DashScopeBaseNode):
    """Upload image(s) to DashScope temporary OSS and return oss:// URLs."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("COMBO", {"default": "happyhorse-1.0-i2v", "options": UPLOAD_MODELS, "tooltip": "Target model — must match the model you will use the URL with"}),
            },
            "optional": {
                "image": ("IMAGE", {"tooltip": "Primary image to upload. Connect IMAGE output from Load Image or other nodes"}),
                "image_1": ("IMAGE", {"tooltip": "Alias for image, for backward compatibility"}),
                "image_2": ("IMAGE", {"tooltip": "Optional additional image"}),
                "image_3": ("IMAGE", {"tooltip": "Optional additional image"}),
                "image_4": ("IMAGE", {"tooltip": "Optional additional image"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("reference_images",)
    FUNCTION = "upload"
    CATEGORY = "api node/upload/DashScope"

    def upload(self, model: str, image=None, image_1=None, image_2=None, image_3=None, image_4=None):
        model = self._validate_setup(model)
        images = [img for img in (image, image_1, image_2, image_3, image_4) if img is not None]
        if not images:
            raise ValueError("At least one image is required.")

        if len(images) == 1 and images[0].shape[0] == 1:
            url = self._upload_tensor(images[0], model)
        else:
            target_h, target_w = images[0].shape[1], images[0].shape[2]
            resized = []
            for img in images:
                if img.shape[1] != target_h or img.shape[2] != target_w:
                    img = img.permute(0, 3, 1, 2)
                    img = torch.nn.functional.interpolate(img, size=(target_h, target_w), mode="bilinear", align_corners=False)
                    img = img.permute(0, 2, 3, 1)
                resized.append(img)
            combined = torch.cat(resized, dim=0)
            url = self._upload_batch(combined, model)
        return {"ui": {"text": (url,)}, "result": (url,)}

    def _upload_tensor(self, image_tensor, model: str) -> str:
        import numpy as np
        from PIL import Image

        img = image_tensor[0].cpu().numpy()
        img = (img * 255).clip(0, 255).astype(np.uint8)
        pil_img = Image.fromarray(img, mode="RGB")
        buf = BytesIO()
        pil_img.save(buf, format="PNG")
        buf.seek(0)
        filename = f"comfyui_{uuid.uuid4().hex[:8]}.png"
        return self._client.upload(buf.read(), filename, model, "image/png")

    def _upload_batch(self, image_tensor, model: str) -> str:
        urls = []
        for i in range(image_tensor.shape[0]):
            single = image_tensor[i:i + 1]
            url = self._upload_tensor(single, model)
            urls.append(url)
        return "\n".join(urls)


class DashScopeHappyHorseTextToVideo(DashScopeBaseNode):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("COMBO", {"default": "happyhorse-1.0-t2v", "options": T2V_MODELS, "tooltip": "Model for text-to-video generation"}),
                "prompt": ("STRING", {"default": "", "multiline": True, "tooltip": "Text prompt describing the desired video content"}),
                "resolution": ("COMBO", {"default": "1080P", "options": RESOLUTIONS, "tooltip": "Output video resolution"}),
                "ratio": ("COMBO", {"default": "16:9", "options": RATIOS, "tooltip": "Output video aspect ratio"}),
                "duration": ("INT", {"default": 5, "min": 3, "max": 15, "step": 1, "tooltip": "Video duration in seconds (3-15)"}),
                "watermark": ("BOOLEAN", {"default": True, "tooltip": "Add watermark to output video"}),
                "seed": ("STRING", {"default": "0", "tooltip": "Random seed (0=random)"}),
            }
        }

    RETURN_TYPES = ("VIDEO",)
    RETURN_NAMES = ("video",)
    FUNCTION = "generate"
    CATEGORY = "api node/video/DashScope"
    OUTPUT_NODE = True

    def generate(
        self,
        model: str,
        prompt: str,
        resolution: str = "1080P",
        ratio: str = "16:9",
        duration: int = 5,
        watermark: bool = True,
        seed: str = "0",
    ):
        model = self._validate_setup(model)
        if not prompt.strip():
            raise ValueError("Prompt must not be empty.")

        seed_val = self._parse_seed(seed)

        body = VideoGenerationRequest(
            model=model,
            input=VideoGenerationInput(prompt=prompt),
            parameters=VideoGenerationParameters(
                resolution=resolution,
                ratio=ratio,
                duration=duration,
                watermark=watermark,
                seed=seed_val if seed_val > 0 else None,
            ),
        )

        task_id = self._client.post_async("/api/v1/services/aigc/video-generation/video-synthesis", body)
        task_output, time_str = self._client.poll(task_id, poll_interval=15.0, label="video")
        video_url = task_output.get("video_url")
        if not video_url:
            raise Exception("DashScope API task succeeded but returned no video URL.")
        video_path = download_url_to_video_path(video_url, api_key=self._api_key)
        return {"ui": {"text": [f"execution_time: {time_str}"]}, "result": (VideoFromFile(video_path),)}


class DashScopeHappyHorseImageToVideo(DashScopeBaseNode):
    RETURN_TYPES = ("VIDEO",)
    RETURN_NAMES = ("video",)
    FUNCTION = "generate"
    CATEGORY = "api node/video/DashScope"
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("COMBO", {"default": "happyhorse-1.0-i2v", "options": I2V_MODELS, "tooltip": "Model for image-to-video generation"}),
                "prompt": ("STRING", {"default": "", "multiline": True, "tooltip": "Text prompt describing the desired video content"}),
                "first_frame": ("STRING", {"default": "", "multiline": True, "tooltip": "oss:// URL to the first frame image. Use DashScopeFileUpload node to get the URL"}),
                "resolution": ("COMBO", {"default": "1080P", "options": RESOLUTIONS, "tooltip": "Output video resolution"}),
                "duration": ("INT", {"default": 5, "min": 3, "max": 15, "step": 1, "tooltip": "Video duration in seconds (3-15)"}),
                "watermark": ("BOOLEAN", {"default": True, "tooltip": "Add watermark to output video"}),
                "seed": ("STRING", {"default": "0", "tooltip": "Random seed (0=random)"}),
            }
        }

    def generate(
        self,
        model: str,
        prompt: str,
        first_frame: str,
        resolution: str = "1080P",
        duration: int = 5,
        watermark: bool = True,
        seed: str = "0",
    ):
        model = self._validate_setup(model)
        first_frame = self._extract_str(first_frame)
        if not first_frame:
            raise ValueError("First frame image URL is required.")

        seed_val = self._parse_seed(seed)
        media = [MediaItem(type="first_frame", url=first_frame)]

        body = I2VRequest(
            model=model,
            input=VideoGenerationInput(prompt=prompt, media=media),
            parameters=I2VParameters(
                resolution=resolution,
                duration=duration,
                watermark=watermark,
                seed=seed_val if seed_val > 0 else None,
            ),
        )

        extra = {"X-DashScope-OssResourceResolve": "enable"} if first_frame.startswith("oss://") else {}
        task_id = self._client.post_async("/api/v1/services/aigc/video-generation/video-synthesis", body, **extra)
        task_output, time_str = self._client.poll(task_id, poll_interval=15.0, label="image-to-video")
        video_url = task_output.get("video_url")
        if not video_url:
            raise Exception("DashScope API task succeeded but returned no video URL.")
        video_path = download_url_to_video_path(video_url, api_key=self._api_key)
        return {"ui": {"text": [f"execution_time: {time_str}"]}, "result": (VideoFromFile(video_path),)}


class DashScopeHappyHorseReferenceToVideo(DashScopeBaseNode):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("COMBO", {"default": "happyhorse-1.0-r2v", "options": R2V_MODELS, "tooltip": "Model for reference-to-video generation"}),
                "prompt": ("STRING", {"default": "", "multiline": True, "tooltip": "Text prompt describing the desired video content"}),
                "reference_images": ("STRING", {"default": "", "multiline": True, "tooltip": "oss:// URLs to reference images, one per line (max 9). Use DashScopeFileUpload node to get URLs"}),
                "resolution": ("COMBO", {"default": "1080P", "options": RESOLUTIONS, "tooltip": "Output video resolution"}),
                "ratio": ("COMBO", {"default": "16:9", "options": RATIOS, "tooltip": "Output video aspect ratio"}),
                "duration": ("INT", {"default": 5, "min": 3, "max": 15, "step": 1, "tooltip": "Video duration in seconds (3-15)"}),
                "watermark": ("BOOLEAN", {"default": True, "tooltip": "Add watermark to output video"}),
                "seed": ("STRING", {"default": "0", "tooltip": "Random seed (0=random)"}),
            }
        }

    RETURN_TYPES = ("VIDEO",)
    RETURN_NAMES = ("video",)
    FUNCTION = "generate"
    CATEGORY = "api node/video/DashScope"
    OUTPUT_NODE = True

    def generate(
        self,
        model: str,
        prompt: str,
        reference_images: str,
        resolution: str = "1080P",
        ratio: str = "16:9",
        duration: int = 5,
        watermark: bool = True,
        seed: str = "0",
    ):
        model = self._validate_setup(model)
        reference_images = self._extract_str(reference_images)
        if not reference_images:
            raise ValueError("At least one reference image URL is required.")

        urls = [u.strip() for u in reference_images.split("\n") if u.strip()]
        if not urls:
            raise ValueError("At least one reference image URL is required.")
        if len(urls) > 9:
            raise ValueError(f"Maximum 9 reference images allowed, got {len(urls)}.")

        seed_val = self._parse_seed(seed)
        media = [MediaItem(type="reference_image", url=u) for u in urls]

        body = VideoGenerationRequest(
            model=model,
            input=VideoGenerationInput(prompt=prompt, media=media),
            parameters=VideoGenerationParameters(
                resolution=resolution,
                ratio=ratio,
                duration=duration,
                watermark=watermark,
                seed=seed_val if seed_val > 0 else None,
            ),
        )

        extra = {"X-DashScope-OssResourceResolve": "enable"} if any(u.startswith("oss://") for u in urls) else {}
        task_id = self._client.post_async("/api/v1/services/aigc/video-generation/video-synthesis", body, **extra)
        task_output, time_str = self._client.poll(task_id, poll_interval=15.0, label="reference-to-video")
        video_url = task_output.get("video_url")
        if not video_url:
            raise Exception("DashScope API task succeeded but returned no video URL.")
        video_path = download_url_to_video_path(video_url, api_key=self._api_key)
        return {"ui": {"text": [f"execution_time: {time_str}"]}, "result": (VideoFromFile(video_path),)}


class DashScopeHappyHorseVideoEdit(DashScopeBaseNode):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("COMBO", {"default": "happyhorse-1.0-video-edit", "options": VED_MODELS, "tooltip": "Model for video editing"}),
                "prompt": ("STRING", {"default": "", "multiline": True, "tooltip": "Edit instruction describing the desired changes to the input video"}),
                "video": ("STRING", {"default": "", "multiline": True, "tooltip": "oss:// URL to the source video. Use DashScopeFileUpload node or dashscope oss.upload CLI to get the URL"}),
                "resolution": ("COMBO", {"default": "1080P", "options": RESOLUTIONS, "tooltip": "Output video resolution"}),
                "watermark": ("BOOLEAN", {"default": True, "tooltip": "Add watermark to output video"}),
                "audio_setting": ("COMBO", {"default": "auto", "options": ["auto", "origin"], "tooltip": "Audio setting: auto (AI-generated) or origin (keep original audio)"}),
                "seed": ("STRING", {"default": "0", "tooltip": "Random seed (0=random)"}),
            },
            "optional": {
                "reference_images": ("STRING", {"default": "", "multiline": True, "tooltip": "oss:// URLs to reference images, one per line (max 5). Use DashScopeFileUpload node to get URLs"}),
            },
        }

    RETURN_TYPES = ("VIDEO",)
    RETURN_NAMES = ("video",)
    FUNCTION = "generate"
    CATEGORY = "api node/video/DashScope"
    OUTPUT_NODE = True

    def generate(
        self,
        model: str,
        prompt: str,
        video: str,
        resolution: str = "1080P",
        watermark: bool = True,
        audio_setting: str = "auto",
        seed: str = "0",
        reference_images: str = "",
    ):
        model = self._validate_setup(model)
        video = self._extract_str(video)
        reference_images = self._extract_str(reference_images) if reference_images else ""
        if not video:
            raise ValueError("Video URL is required.")

        media = [MediaItem(type="video", url=video)]
        all_urls = [video]

        if reference_images:
            ref_urls = [u.strip() for u in reference_images.split("\n") if u.strip()]
            if len(ref_urls) > 5:
                raise ValueError(f"Maximum 5 reference images allowed, got {len(ref_urls)}.")
            for u in ref_urls:
                media.append(MediaItem(type="reference_image", url=u))
            all_urls.extend(ref_urls)

        seed_val = self._parse_seed(seed)

        body = VideoEditRequest(
            model=model,
            input=VideoGenerationInput(prompt=prompt, media=media),
            parameters=VideoEditParameters(
                resolution=resolution,
                watermark=watermark,
                audio_setting=audio_setting,
                seed=seed_val if seed_val > 0 else None,
            ),
        )

        extra = {"X-DashScope-OssResourceResolve": "enable"} if any(u.startswith("oss://") for u in all_urls) else {}
        task_id = self._client.post_async("/api/v1/services/aigc/video-generation/video-synthesis", body, **extra)
        task_output, time_str = self._client.poll(task_id, poll_interval=15.0, label="video-edit")
        video_url = task_output.get("video_url")
        if not video_url:
            raise Exception("DashScope API task succeeded but returned no video URL.")
        video_path = download_url_to_video_path(video_url, api_key=self._api_key)
        return {"ui": {"text": [f"execution_time: {time_str}"]}, "result": (VideoFromFile(video_path),)}


# import at bottom to avoid circular import with nodes __init__.py
from comfy_api.latest._input_impl.video_types import VideoFromFile
