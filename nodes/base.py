import json
import os
import time

from server import PromptServer

from ..client import DashScopeClient


class DashScopeBaseNode:
    """Shared base for DashScope ComfyUI nodes — validation, progress, client access."""

    _cached_api_key: str | None = None

    @property
    def _api_key(self) -> str:
        if self._cached_api_key is None:
            self._cached_api_key = os.environ.get("DASHSCOPE_API_KEY", "")
        return self._cached_api_key

    @property
    def _client(self) -> DashScopeClient:
        if not hasattr(self, "_cached_client"):
            self._cached_client = DashScopeClient(self._api_key)
        return self._cached_client

    @staticmethod
    def _extract_str(value):
        if isinstance(value, list):
            return str(value[0]).strip() if value else ""
        return str(value).strip() if value else ""

    def _validate_setup(self, model: str) -> str:
        model = self._extract_str(model)
        if not self._api_key:
            raise ValueError("DashScope API Key is required. Get one from https://bailian.console.aliyun.com/")
        if not model:
            raise ValueError("Model name is required.")
        return model

    def _report_done(self, start_ts: float) -> str:
        time_str = f"{time.monotonic() - start_ts:.1f}s"
        PromptServer.instance.send_sync(
            "progress",
            {
                "value": 1,
                "max": 1,
                "prompt_id": PromptServer.instance.last_prompt_id or "",
                "node": "",
                "text": f"Done in {time_str}",
            },
        )
        return time_str

    @staticmethod
    def _parse_int(raw, default=1):
        if raw is None:
            return default
        if isinstance(raw, (int, float)):
            return int(raw)
        try:
            return int(raw)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _parse_seed(raw):
        if raw is None:
            return 0
        if isinstance(raw, (int, float)):
            return int(raw)
        try:
            return int(raw)
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _parse_json(raw, default=None):
        if raw is None:
            return default
        if isinstance(raw, (list, dict)):
            return raw
        if isinstance(raw, str):
            s = raw.strip()
            if not s:
                return default
            try:
                return json.loads(s)
            except (json.JSONDecodeError):
                return default
        return default
