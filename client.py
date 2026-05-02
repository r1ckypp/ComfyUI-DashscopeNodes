import os
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .constants import (
    DASHSCOPE_BASE_URL,
    DASHSCOPE_IMAGE_URL,
    DASHSCOPE_SYNC_PATH,
    DASHSCOPE_TASK_PATH,
    DASHSCOPE_UPLOAD_PATH,
)
from .exceptions import ProcessingInterrupted


class DashScopeClient:
    """Unified HTTP client for DashScope APIs with error handling, async polling, and OSS upload."""

    def __init__(self, api_key: str):
        self._api_key = api_key

    # ── session ─────────────────────────────────────────────────

    def _build_session(self, retries=3, backoff_factor=1.0):
        session = requests.Session()
        retry_strategy = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist={408, 429, 500, 502, 503, 504},
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _headers(self, **extra):
        h = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        h.update(extra)
        return h

    @staticmethod
    def _parse_error(resp):
        try:
            body = resp.json()
        except Exception:
            return f"HTTP {resp.status_code}: {resp.text[:300]}"
        code = body.get("code", "")
        msg = body.get("message", "")
        return f"DashScope API error ({resp.status_code}): [{code}] {msg}"

    # ── sync POST ───────────────────────────────────────────────

    def post(self, path: str, body, **extra_headers) -> dict:
        url = f"{DASHSCOPE_BASE_URL}{path}"
        with self._build_session() as session:
            resp = session.post(
                url,
                json=body.model_dump(exclude_none=True),
                headers=self._headers(**extra_headers),
                timeout=120,
            )
            if resp.status_code >= 400:
                raise Exception(self._parse_error(resp))
            return resp.json()

    # ── async POST ──────────────────────────────────────────────

    def post_async(self, path: str, body, **extra_headers) -> str:
        data = self.post(path, body, **{"X-DashScope-Async": "enable", **extra_headers})
        output = data.get("output")
        if not output or not output.get("task_id"):
            raise Exception(
                f"DashScope API did not return a task ID: [{data.get('code')}] {data.get('message')}"
            )
        return output["task_id"]

    # ── poll ────────────────────────────────────────────────────

    def poll(self, task_id: str, poll_interval: float = 15.0, label: str = "task"):
        """Poll an async task. Returns (output_dict, elapsed_time_str)."""
        from comfy.model_management import processing_interrupted

        from server import PromptServer

        start_ts = time.monotonic()
        poll_url = f"{DASHSCOPE_BASE_URL}{DASHSCOPE_TASK_PATH}/{task_id}"
        poll_headers = {"Authorization": f"Bearer {self._api_key}"}

        while True:
            with self._build_session() as session:
                resp = session.get(poll_url, headers=poll_headers, timeout=30)
                if resp.status_code >= 400:
                    raise Exception(self._parse_error(resp))
                status_data = resp.json()

            task_output = status_data.get("output") or {}
            if task_output.get("code"):
                raise Exception(f"DashScope API error: [{task_output['code']}] {task_output.get('message', '')}")
            if status_data.get("code"):
                raise Exception(f"DashScope API error: [{status_data['code']}] {status_data.get('message', '')}")

            task_status = task_output.get("task_status")
            if task_status == "SUCCEEDED":
                elapsed = time.monotonic() - start_ts
                time_str = f"{elapsed:.1f}s"
                PromptServer.instance.send_sync(
                    "progress",
                    {
                        "value": 1, "max": 1,
                        "prompt_id": PromptServer.instance.last_prompt_id or "",
                        "node": "",
                        "text": f"Done in {time_str}",
                    },
                )
                return task_output, time_str

            if task_status in ("FAILED", "CANCELED"):
                code = task_output.get("code") or ""
                msg = task_output.get("message") or ""
                raise Exception(f"DashScope task {task_status}: [{code}] {msg}")

            if task_status == "UNKNOWN":
                raise Exception("DashScope task ID expired or unknown (24h TTL). Re-queue to get a new task.")

            if processing_interrupted():
                raise ProcessingInterrupted("Task cancelled")

            PromptServer.instance.send_sync(
                "progress",
                {
                    "value": 1, "max": 1,
                    "prompt_id": PromptServer.instance.last_prompt_id or "",
                    "node": "",
                    "text": f"Generating {label}\nElapsed: {int(time.monotonic() - start_ts)}s",
                },
            )

            self._sleep_with_interrupt(poll_interval)

    @staticmethod
    def _sleep_with_interrupt(seconds: float, *, check_interval: float = 1.0):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            from comfy.model_management import processing_interrupted
            if processing_interrupted():
                raise ProcessingInterrupted("Task cancelled")
            time.sleep(min(check_interval, max(0, end - time.monotonic())))

    # ── upload ──────────────────────────────────────────────────

    def upload(self, file_data: bytes, filename: str, model: str, content_type: str) -> str:
        """Upload a file to DashScope OSS. Returns oss:// URL."""
        policy = self._get_upload_policy(model)

        key = f"{policy['upload_dir']}/{filename}"
        upload_host = policy["upload_host"]
        files = {
            "OSSAccessKeyId": (None, policy["oss_access_key_id"]),
            "Signature": (None, policy["signature"]),
            "policy": (None, policy["policy"]),
            "x-oss-object-acl": (None, policy["x_oss_object_acl"]),
            "x-oss-forbid-overwrite": (None, policy["x_oss_forbid_overwrite"]),
            "key": (None, key),
            "success_action_status": (None, "200"),
            "file": (filename, file_data, content_type),
        }
        with self._build_session(retries=1) as session:
            resp = session.post(upload_host, files=files, timeout=60)
            if resp.status_code >= 400:
                raise Exception(f"DashScope OSS upload error ({resp.status_code}): {resp.text}")

        return f"oss://{key}"

    def _get_upload_policy(self, model: str) -> dict:
        url = f"{DASHSCOPE_IMAGE_URL}{DASHSCOPE_UPLOAD_PATH}"
        params = {"action": "getPolicy", "model": model}
        with self._build_session() as session:
            resp = session.get(url, headers=self._headers(), params=params, timeout=30)
            if resp.status_code >= 400:
                raise Exception(self._parse_error(resp))
            data = resp.json()
        policy = data.get("data")
        if not policy:
            raise Exception(f"DashScope did not return upload policy data: {data}")
        return policy

    # ── download ────────────────────────────────────────────────

    def download(self, url: str, timeout: int = 120) -> bytes:
        resp = requests.get(url, headers={"Authorization": f"Bearer {self._api_key}"}, timeout=timeout)
        resp.raise_for_status()
        return resp.content
