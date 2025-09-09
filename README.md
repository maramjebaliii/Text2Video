# Text2Video

从主题或 Markdown 自动生成讲解视频的端到端小工具：调用 LLM 生成/优化脚本，批量 TTS 合成语音，生成插画图片，自动合并字幕面板与音频为片段并用 ffmpeg 拼接为最终 MP4。支持 FastAPI 与本地 Streamlit Web UI。
![](https://oss-liuchengtu.hudunsoft.com/userimg/f8/f8475483bb81d8e07ee71a388b6ee3ee.png)
![](https://oss-liuchengtu.hudunsoft.com/userimg/47/47202368777bb4124d11400d8cac1fd0.png)

## 功能亮点

- 输入两种来源：
  - Topic → 自动生成 Markdown → 生成视频
  - Markdown → 直接生成视频
- 全流程持久化产物：脚本(JSON)、语音清单、插画提示与图片、字幕 JSON/SRT、合并后的 blocks、最终视频
- Provider 可插拔：LLM、TTS、图片生成均通过抽象接口注入

## 环境要求

- Python 3.11+
- FFmpeg 已安装并可在 PATH 中被找到（pydub/ffmpeg 调用需要）
  - Windows 可到 [FFmpeg Builds](https://www.gyan.dev/ffmpeg/builds/) 下载解压，将 `bin` 目录加入系统 PATH

## 安装

使用 pip（推荐在虚拟环境内）：

```cmd
python -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip
pip install .
```

可选：若你使用 uv 包管理器，则在仓库根目录运行：

```cmd
uv sync
```

## 准备配置（.env）

在项目根目录创建 `.env` 文件，至少配置必需的 API Key：

```ini
# 必填：用于 LLM / TTS / Image（硅基流动）
GUIJI_API_KEY=你的_API_Key
GUIJI_BASE_URL=https://api.siliconflow.cn/v1
GUIJI_CHAT_MODEL=Qwen/Qwen2.5-7B-Instruct
GUIJI_IMAGE_MODEL=Kwai-Kolors/Kolors
GUIJI_TTS_MODEL=FunAudioLLM/CosyVoice2-0.5B

```

## 运行方式

你可以选择运行 API 或本地 Web UI（或同时）。

### 方式 A：启动 FastAPI 服务

```cmd
python main.py
```

默认监听 `http://127.0.0.1:8000`（开发模式可热重载）。

也可使用 uvicorn：

```cmd
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 方式 B：启动 Streamlit Web UI

```cmd
streamlit run streamlit.app.py
```

浏览器会自动打开一个包含两个 Tab 的简易界面：

- Markdown → 视频：输入或上传 Markdown，一键生成
- Topic → 视频：填写主题与参数，先生成 Markdown，再生成视频

UI 会将输出固定到 `output/webui/`（除非你覆盖 RUN_ID）。

## API 使用

服务启动后可直接调用：

1. POST `/video/from-topic`（返回 JSON，含输出路径与 blocks 数量）

```cmd
curl -X POST "http://127.0.0.1:8000/video/from-topic" ^
 -H "Content-Type: application/json" ^
 -d "{\"topic\":\"边缘计算与云计算的协同\",\"language\":\"zh\",\"max_sections\":5}"
```

响应示例：

```json
{ "output_path": "c:/.../output/<run_id>/final_video.mp4", "blocks_count": 12 }
```

2. POST `/video/from-markdown`（直接返回 MP4 文件流）

```cmd
curl -X POST "http://127.0.0.1:8000/video/from-markdown" ^
 -H "Content-Type: application/json" ^
 -d "{\"markdown\":\"# 标题\\n内容...\"}" ^
 -o result.mp4
```

可选 body 字段 `output`：指定输出目录或文件名（相对路径会拼到本次运行的 `output/<run_id>/` 下）。

## 输出与中间产物

所有产物默认写入 `output/<run_id>/`：

- `script_raw.json` / `script_optimized.json` / `script_expanded.json`
- `speech/`：
  - `speech_manifest.json`（可复用，避免重复 TTS）
  - `duration_cache.json`（探测到的音频时长缓存）
- `images/`：
  - `illustration_prompts.json`（插画提示）
  - `illustration_assets.json`（生成图片的本地路径等）
- `blocks_merged.json`：合并后的语音+图片块
- `subtitles.json` / `subtitles.srt`
- `segments/`：临时视频片段与资源
- `final_video.mp4`：最终视频

说明：`RUN_ID` 不指定时会随机生成短 UUID 用于隔离；Web UI 默认将其固定为 `webui`。

## 工作原理

整体流程是：从主题或 Markdown 开始，先用 LLM 生成/口语化优化脚本并按语音粒度切分句子；随后批量合成 TTS 音频并缓存探测到的时长，同时用 LLM 产出插画提示并通过图片模型生成配图；将语音与图片按顺序合并为 blocks 并计算字幕时间轴（JSON/SRT）；最后为每个标题/句子渲染字幕面板叠加到背景图、与对应音频合成片段，使用 ffmpeg concat 拼接成 MP4 输出，过程中会把脚本、清单、图片与中间结果全部持久化，便于复用与调试。

## 项目结构

```text
app/
 core/            # 配置、流水线、插画、合并、视频装配
 providers/       # LLM / TTS / Image Provider 实现
 routers/         # FastAPI 路由
 services/        # 业务服务封装（供路由使用）
main.py            # FastAPI 入口
streamlit.app.py   # Web UI 入口
pyproject.toml     # 依赖与元数据
output/            # 运行产物（按 run_id 隔离）
```
