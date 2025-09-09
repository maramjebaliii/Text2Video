"""SiliconFlow 图像生成 Provider（含速率限制与下载首图）。"""
from __future__ import annotations

import os
import time
import threading
from collections import deque
from urllib.parse import urlparse, unquote
import requests
from uuid import uuid4

__all__ = ["SiliconFlowImageProvider"]


class SiliconFlowImageProvider:
    """SiliconFlow 图片生成封装。"""

    def __init__(
        self,
        api_key: str,
        model: str = "Kwai-Kolors/Kolors",
        base_url: str = "https://api.siliconflow.cn/v1/images/generations",
        ipm: int = 2,
        output_dir: str = "output_images",
        timeout: int = 60,
    ) -> None:
        """初始化参数与速率控制。"""
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.ipm = max(1, int(ipm))
        self.output_dir = output_dir
        self.timeout = timeout
        self._calls: deque[float] = deque()
        self._lock = threading.Lock()

    def _wait_slot(self) -> None:
        """简单 IPM 速率限制。"""
        with self._lock:
            now = time.time()
            while self._calls and now - self._calls[0] >= 60:
                self._calls.popleft()
            if len(self._calls) < self.ipm:
                self._calls.append(now)
                return
            earliest = self._calls[0]
            wait = 60 - (now - earliest)
        if wait > 0:
            time.sleep(wait)
        self._wait_slot()

    def _extract_first_url(self, data: dict) -> str:
        """提取首个图片 URL。"""
        url = None
        if isinstance(data, dict):
            images = data.get("images")
            if isinstance(images, list) and images:
                url = images[0].get("url")
            if not url:
                d = data.get("data")
                if isinstance(d, list) and d:
                    url = d[0].get("url")
            if not url:
                for v in data.values():
                    if isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict) and item.get("url"):
                                url = item["url"]
                                break
                        if url:
                            break
        if not url:
            raise ValueError("未找到图片 URL")
        return url

    def _download(self, url: str) -> str:
        """下载图片并返回绝对路径。"""
        os.makedirs(self.output_dir, exist_ok=True)
        path = urlparse(url).path
        base = os.path.basename(unquote(path)) or f"image_{int(time.time())}.png"
        stem, ext = os.path.splitext(base)
        if not ext:
            ext = ".png"
        # 追加短 UUID，避免同名覆盖（并发/重复 URL 的情况下）
        name = f"{stem}_{uuid4().hex[:8]}{ext}"
        file_path = os.path.join(self.output_dir, name)
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        with open(file_path, "wb") as f:
            f.write(resp.content)
        return os.path.abspath(file_path)

    def generate(
        self,
        prompt: str,
        *,
        batch_size: int = 1,
        image_size: str = "1024x1024",
        num_inference_steps: int = 20,
        guidance_scale: float = 7.5,
    ) -> str:
        """生成图片并返回本地路径。"""
        self._wait_slot()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "prompt": prompt,
            "image_size": image_size,
            "batch_size": batch_size,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
        }
        r = requests.post(self.base_url, headers=headers, json=payload, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        url = self._extract_first_url(data)
        return self._download(url)
