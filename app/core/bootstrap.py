"""应用启动引导：统一加载 .env / config.yaml，并注入 provider 配置。

供 `main.py` 与 `streamlit.app.py` 导入使用，避免重复实现环境加载逻辑。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any


def init_env_and_providers() -> Dict[str, Any]:
    """加载 .env，优先读取根目录的 config.yaml（如果存在），将未设置的项写入环境变量（不覆盖已存在的），
    并调用 provider_factory.configure_providers 注入 key/base_url 等。

    返回解析后的配置字典（以 config.yaml 的内容为主，结合环境变量）。
    """
    # 先加载 .env
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        # python-dotenv 未安装 的情况下略过（大多数环境会已有环境变量）
        pass

    # 尝试加载 config.yaml
    root = Path(__file__).resolve().parent.parent.parent
    cfg_path = root / "config.yaml"
    yaml_data: Dict[str, Any] = {}
    if cfg_path.exists():
        try:
            import yaml

            yaml_data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        except Exception:
            yaml_data = {}

    # 将 yaml 中的键写入环境变量（仅在未设置时写入，避免覆盖系统环境）
    for k, v in list(yaml_data.items()):
        if v is None:
            continue
        # 布尔值转换为 '1'/'0' 以兼容现有代码中以字符串判断的逻辑
        if isinstance(v, bool):
            sval = "1" if v else "0"
        else:
            sval = str(v)
        os.environ.setdefault(k, sval)

    # 决定注入 provider 的值（优先 yaml，其次环境变量）
    api_key = yaml_data.get("GUIJI_API_KEY") or os.getenv("GUIJI_API_KEY")
    base_url = yaml_data.get("GUIJI_BASE_URL") or os.getenv("GUIJI_BASE_URL")
    image_base = yaml_data.get("GUIJI_IMAGE_BASE_URL") or os.getenv("GUIJI_IMAGE_BASE_URL") or "https://api.siliconflow.cn/v1/images/generations"

    # 注入 provider 工厂默认
    try:
        from app.core.provider_factory import configure_providers

        configure_providers(api_key=api_key, base_url=base_url, image_base=image_base)
    except Exception:
        # 若 provider_factory 导入失败（例如在测试环境），不要阻塞，只返回配置
        pass

    # 返回合并配置，方便上层显示/调试
    merged = {**yaml_data}
    merged.setdefault("GUIJI_API_KEY", api_key)
    merged.setdefault("GUIJI_BASE_URL", base_url)
    merged.setdefault("GUIJI_IMAGE_BASE_URL", image_base)
    return merged


__all__ = ["init_env_and_providers"]
