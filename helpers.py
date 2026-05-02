"""Data conversion helpers — tensor/audio/video downloads and format conversions."""

import base64
import os
import uuid
from io import BytesIO

import numpy as np
import requests
import torch
from PIL import Image

from folder_paths import get_output_directory


def download_url_to_image_tensor(url: str, *, api_key: str = "", timeout: int = 120) -> torch.Tensor:
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    img = Image.open(BytesIO(resp.content)).convert("RGB")
    img_np = np.array(img).astype(np.float32) / 255.0
    return torch.from_numpy(img_np).unsqueeze(0)


def download_url_to_video_path(video_url: str, *, api_key: str = "", timeout: int = 300) -> str:
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    resp = requests.get(video_url, headers=headers, timeout=timeout, stream=True)
    resp.raise_for_status()

    output_dir = get_output_directory()
    filename = f"dashscope_video_{uuid.uuid4().hex[:8]}.mp4"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)
    return filepath


def extract_image_url_from_sync(response) -> str | None:
    choices = (response.get("output") and response["output"].get("choices")) or []
    for choice in choices:
        if choice.get("message") and choice["message"].get("content"):
            for item in choice["message"]["content"]:
                if item.get("image"):
                    return item["image"]
    return None


def extract_image_url_from_async(response) -> str | None:
    choices = (response.get("output") and response["output"].get("choices")) or []
    for choice in choices:
        if choice.get("message") and choice["message"].get("content"):
            for item in choice["message"]["content"]:
                if item.get("image"):
                    return item["image"]
    return None


def tensor_to_base64_png(image_tensor) -> str:
    img = image_tensor[0].cpu().numpy()
    img = (img * 255).clip(0, 255).astype(np.uint8)
    pil_img = Image.fromarray(img, mode="RGB")
    buf = BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)
    b64_str = base64.b64encode(buf.read()).decode("utf-8")
    return f"data:image/png;base64,{b64_str}"


def video_to_base64(video_input) -> str:
    import os as _os
    import tempfile

    MAX_BASE64_SIZE = 10 * 1024 * 1024

    if hasattr(video_input, "save_to"):
        from comfy_api.latest import Types

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            video_input.save_to(
                tmp_path,
                format=Types.VideoContainer.MP4,
                codec=Types.VideoCodec.H264,
            )
            with open(tmp_path, "rb") as f:
                data = f.read()
        finally:
            try:
                _os.unlink(tmp_path)
            except OSError:
                pass
    elif isinstance(video_input, str):
        with open(video_input, "rb") as f:
            data = f.read()
    else:
        raise ValueError(f"Unsupported video input type: {type(video_input)}")

    if len(data) > MAX_BASE64_SIZE:
        size_mb = len(data) / (1024 * 1024)
        raise ValueError(
            f"Encoded video is {size_mb:.1f}MB, exceeds the 10MB base64 limit. "
            "Consider trimming the video or using a shorter clip."
        )
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:video/mp4;base64,{b64}"


def image_tensor_to_base64_list(image_tensor: torch.Tensor) -> list[str]:
    results: list[str] = []
    for i in range(image_tensor.shape[0]):
        img_np = (image_tensor[i].cpu().numpy() * 255).astype(np.uint8)
        img = Image.fromarray(img_np, mode="RGB")
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=90)
        results.append("data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii"))
    return results


# ── audio helpers ───────────────────────────────────────────────────

def audio_input_to_temp_file(audio_data: dict) -> str:
    import tempfile

    waveform = audio_data["waveform"]
    sample_rate = audio_data["sample_rate"]
    if waveform.dim() == 3:
        waveform = waveform[0]
    waveform = waveform.cpu()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        import torchaudio
    except ImportError:
        raise ImportError("torchaudio is required for AUDIO input: pip install torchaudio")
    torchaudio.save(tmp_path, waveform, sample_rate)
    return tmp_path


def extract_audio_url_from_response(data: dict) -> str | None:
    output = data.get("output") or {}
    audio = output.get("audio") or {}
    return audio.get("url") or None


def audio_bytes_to_audio(audio_bytes: bytes, hint_suffix: str = ".wav") -> dict:
    import tempfile

    import torchaudio

    suffix = hint_suffix if hint_suffix.startswith(".") else f".{hint_suffix}"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        waveform, sample_rate = torchaudio.load(tmp_path)
        return {"waveform": waveform.unsqueeze(0), "sample_rate": sample_rate}
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def download_url_to_audio(url: str, *, api_key: str = "", timeout: int = 120) -> dict:
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return audio_bytes_to_audio(resp.content)
