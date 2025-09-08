# Text2Video

一个示例级端到端“小课视频”生成流程：从 **主题 / Markdown** 出发，自动完成脚本解析与口语化、句子拆分、批量 TTS、插图提示生成、图像生成、语音与插图合并、视频分段拼装、字幕生成。

> 目前仓库用于演示工程化流水线拆解与可观测性，不追求模型效果最优；欢迎在此基础上换模型 / 加检验 / 迭代策略。

## ✨ 功能特性

- 主题脚本生成（few‑shot）→ `generate_markdown_script`
- Markdown 解析 → 标题+正文结构化
- LLM 口语化改写（可选，可与测试脚本对齐提示词）
- 句子拆分（去标点、兼容括号嵌套）+ TTS 细粒度合成 & 时长缓存
- 插图详细提示词（对齐测试版的结构化 Prompt）
- 图像批量生成（SiliconFlow 图像接口）
- 合并语音 & 插图 → blocks
- 视频分段构建 + 总拼接（ffmpeg）
- 字幕 (JSON + SRT) 输出
- 中间产物全部落盘，便于调试与复用

## 🧱 流程总览

```
Topic / Markdown
	│
	├─(可选) generate_markdown_script 主题扩写
	▼
Markdown 解析 → script_raw.json
	│
	├─(optimize=True) 口语化 → script_optimized.json
	▼
拆句（content 保留 + sentences 新增）→ script_expanded.json
	▼
批量 TTS (缓存/时长/manifest) → speech_manifest.json (+ 音频文件)
	│
	├─插图 prompts (使用未拆句版本) → illustration_prompts.json
	├─图像生成 → illustration_assets.json (+ 本地图片)
	▼
合并 → blocks_merged.json
	▼
视频分段 & 拼接 → 最终 mp4 / segments/*.mp4
	▼
字幕 → subtitles.json / subtitles.srt
```

## 📁 关键产物说明

| 文件 | 说明 |
|------|------|
| `script_raw.json` | Markdown / 输入脚本解析结果（title+content 原文） |
| `script_optimized.json` | 口语化（可选）版本，结构同上 |
| `script_expanded.json` | 每条含 `content` 原文 + `sentences` 拆句列表 |
| `speech/speech_manifest.json` | 每块的 `sentences` / `audio_files` / `durations` / `total_duration` |
| `speech/script_items.json` | 与 `script_expanded.json` 相同内容副本，靠近音频便于调试 |
| `images/illustration_prompts.json` | 结构化插图提示（含示例格式约束生成） |
| `images/illustration_assets.json` | 实际生成图片清单（含本地路径） |
| `blocks_merged.json` | 合并后的区块：图像 + 语音引用 + 文本 |
| `subtitles.json` / `subtitles.srt` | 基于句子与时长生成的字幕数据 |
| `output/speech/*.mp3` | 每句 TTS 片段（唯一命名，含 hash/uuid 可配置） |
| `output/segments/*.mp4` | 每个区块对应的视频片段 |

## 🔧 环境准备

要求：

- Python 3.11+
- 已安装 `ffmpeg` / `ffprobe` 并加入 PATH（Windows 可用 scoop / choco）
- 注册并获取 SiliconFlow / 硅基 API Key（或替换为其他 LLM / TTS / Image Provider）

安装依赖：

```cmd
pip install -r requirements.txt
```

## 🔐 环境变量 (.env 示例)

```env
GUIJI_API_KEY=sk_xxxxxxxxxxxxxxxxx
GUIJI_BASE_URL=https://api.siliconflow.cn/v1
GUIJI_IMAGE_MODEL=Kwai-Kolors/Kolors
GUIJI_CHAT_MODEL=Qwen/Qwen2.5-7B-Instruct
# 可选阿里云 TTS
ALIBABA_CLOUD_AK=xxx
ALIBABA_CLOUD_SK=yyy
```

## ▶️ 运行示例

按主题自动生成脚本并出视频：

```cmd
python main.py --mode topic --topic 边缘计算与云计算的协同 --output output/video_topic.mp4
```

使用内置的简单 Markdown 示例：

```cmd
python main.py --mode markdown --output output/video_markdown.mp4
```

生成后在 `output/` 目录可查看所有中间 JSON / 音频 / 图片 / 视频片段与字幕。

## 🗂️ 目录结构（节选）

```
app/
  core/
	 pipeline.py
	 script_preprocess.py
	 illustration.py
	 video/
  providers/
output/
  script_raw.json
  script_expanded.json
  subtitles.srt
  speech/
	 speech_manifest.json
  images/
	 illustration_prompts.json
	 illustration_assets.json
  segments/
	 segment_*.mp4
tests/
```

## 🤖 提示词对齐策略

已与 `tests/` 中脚本保持一致：

- 口语化：`optimize_script_for_speech` 使用与 `prepare_script_for_recording.py` 相同的系统角色与格式约束。
- 插图提示：`illustration.py` 同步测试版的结构化要素与示例 JSON。

## 🗣️ 句子拆分逻辑

`split_text_for_tts`：

- 依据中文主要标点（，。；？！）与空格分段
- 跳过嵌套括号内部的临时切分（防止括号里被截断）
- 输出去首尾空白的短句，供 TTS 精细控制与字幕对齐

（如需英文 / 多语种更精细切分，可替换为 spaCy / regex 更复杂规则。）

## 🗜️ 缓存与复用

- 音频：`speech_manifest.json` + 时长缓存（避免重复合成 & 减少 ffprobe 开销）
- 文件命名：hash + 可选 uuid 片段，杜绝覆盖；后期可加 `reuse_manifest=False` 强制刷新

## 🎬 视频组装

当前实现：

1. 每个 block 生成独立段视频（背景 / 图片 / 音频叠加）
2. 使用 ffmpeg concat 合成最终成品
3. 字幕 (SRT) 可用于后期再烧录（可扩展自动 burn-in）

## ❓ 常见问题

| 问题 | 说明 / 处理 |
|------|--------------|
| MP3 偶发损坏 | 可能为网络 / 服务端异常，建议加：文件大小校验 + ffprobe 验证 + 重试（TODO） |
| 列表符号残留 | 已在 Markdown 解析阶段补充行首 `-` / `•` 去除（若仍有，扩展正则） |
| 口语化不生效 | 确认 `--mode topic` / `optimize=True`；或检查模型是否支持上下文长度 |
| 插图风格单调 | 可在 prompt 追加全局风格控制字段或引入多轮 refine |

## 🔍 TODO / Roadmap

- [ ] 音频文件完整性校验 & 失败重试机制
- [ ] 更丰富的多段背景模板 / 动态字幕渲染
- [ ] 插图生成并行调度与失败回退
- [ ] 英文 / 多语种混合分句支持
- [ ] 可配置内容审核 / 敏感词过滤钩子
- [ ] Web UI / REST API 封装

## 🧪 测试脚本参考

`tests/` 目录保留了最初分步脚本（如 `md2script.py`, `prepare_script_for_recording.py`, `generate_illustration_prompts.py`），用于对照与回归确认 pipeline 等价性。

## 🔄 自定义与扩展

可以通过替换 Provider：

```python
from app.providers import GuijiTTSProvider, AliyunTTSProvider
tts = AliyunTTSProvider(access_key_id=..., access_key_secret=...)
```

或新增 Image / LLM Provider：实现接口 `LLMProvider.chat(messages, model=None)` 与 `ImageProvider.generate(prompt, ...)` 即可接入。

## 📌 许可证

未声明 License，默认保留所有权利。若需开源再行补充。

---
欢迎提出改进建议或直接提交 PR。
