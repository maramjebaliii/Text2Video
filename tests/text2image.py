import requests
import os
import time
from urllib.parse import urlparse, unquote
from collections import deque
import threading


class ImageGenerator:
    """图像生成器类，支持 IPM（images per minute）速率限制并将生成的第一张图片下载到本地。

    使用示例：
        g = ImageGenerator(api_key, ipm=2)
        path = g.generate_and_save(prompt)
    """

    def __init__(
        self,
        api_key: str,
        model: str = "Kwai-Kolors/Kolors",
        base_url: str = "https://api.siliconflow.cn/v1/images/generations",
        ipm: int = 2,
        output_dir: str = "output_images",
        timeout: int = 30,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.ipm = max(1, int(ipm))
        self.output_dir = output_dir
        self.timeout = timeout

        # deque 用于记录一分钟内的调用时间戳
        self._calls = deque()
        self._lock = threading.Lock()

    def _wait_for_slot(self):
        """如果一分钟内调用已达 ipm，等待至有可用槽位为止。"""
        with self._lock:
            now = time.time()
            # 清理 60 秒之前的时间戳
            while self._calls and now - self._calls[0] >= 60:
                self._calls.popleft()

            if len(self._calls) < self.ipm:
                # 还有槽位，记录当前调用时间戳并返回
                self._calls.append(now)
                return

            # 已满，计算需等待时间
            earliest = self._calls[0]
            wait = 60 - (now - earliest)

        # 在锁外睡眠，避免阻塞其他线程的检查
        if wait > 0:
            time.sleep(wait)

        # 递归/循环直到能加入
        return self._wait_for_slot()

    def _extract_first_image_url(self, resp_json: dict) -> str:
        img_url = None
        if isinstance(resp_json, dict):
            if resp_json.get("images") and isinstance(resp_json["images"], list):
                img_url = resp_json["images"][0].get("url")
            if not img_url and resp_json.get("data") and isinstance(resp_json["data"], list):
                img_url = resp_json["data"][0].get("url")
            if not img_url:
                for v in resp_json.values():
                    if isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict) and item.get("url"):
                                img_url = item.get("url")
                                break
                    if img_url:
                        break

        if not img_url:
            raise ValueError("未能在响应中找到图片 URL，响应内容: " + str(resp_json))

        return img_url

    def _download_image(self, img_url: str) -> str:
        os.makedirs(self.output_dir, exist_ok=True)
        path = urlparse(img_url).path
        unquoted_path = unquote(path)
        filename = os.path.basename(unquoted_path)
        if not filename:
            filename = f"image_{int(time.time())}.png"

        file_path = os.path.join(self.output_dir, filename)
        r = requests.get(img_url, timeout=60)
        r.raise_for_status()
        with open(file_path, "wb") as f:
            f.write(r.content)
        return os.path.abspath(file_path)

    def generate_and_save(
        self,
        prompt: str,
        batch_size: int = 1,
        image_size: str = "1024x1024",
        num_inference_steps: int = 20,
        guidance_scale: float = 7.5,
    ) -> str:
        """生成图片并保存第一张，返回本地绝对路径。该方法会受 IPM 限制控制。

        可能抛出的异常：requests.HTTPError、ValueError 等。
        """
        # 等待可用的调用槽位（速率控制）
        self._wait_for_slot()

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

        resp = requests.post(self.base_url, headers=headers, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        resp_json = resp.json()

        img_url = self._extract_first_image_url(resp_json)
        return self._download_image(img_url)


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    API_KEY = os.getenv("GUIJI_KEY")

    gen = ImageGenerator(api_key=API_KEY, ipm=2, output_dir="output_images")

    try:
        # 示例：连续调用两次，IPM=2 会限制每分钟不超过 2 次
        p1 = gen.generate_and_save(prompt="一幅美丽的风景画，画中有山脉和河流，采用吉卜力工作室的风格")
        print("已保存图片到：", p1)
        p2 = gen.generate_and_save(prompt="同一主题的另一幅构图，黄昏光线，柔和色彩")
        print("已保存图片到：", p2)
    except Exception as e:
        print("保存图片失败：", e)