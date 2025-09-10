# Text2Video

![](https://oss-liuchengtu.hudunsoft.com/userimg/e7/e7297caa019b5634cebf47b9b3789d5b.png)

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
下面使用的key来自硅基流动，你可以去<https://cloud.siliconflow.cn/i/FcjKykMn获取，或者![硅基流动>](<https://cloud.siliconflow.cn/i/FcjKykMn)，>

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

## 使用 Docker 运行

镜像内已预装 ffmpeg 与中文字体，支持 API 和 Streamlit 两种模式。

### 构建镜像（可选传入国内镜像源）

```cmd
docker build -t text2video .
```

可选（使用阿里云源）：

```cmd
docker build -t text2video ^
  --build-arg PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple ^
  --build-arg PIP_EXTRA_INDEX_URL=https://pypi.org/simple ^
  .
```

### 运行（API 模式，<http://localhost:8000>）

```cmd
docker run --rm -it ^
  -p 8000:8000 ^
  -e RUN_MODE=api ^
  --env-file .env ^
  -v "%CD%\output":/app/output ^
  text2video
```

### 运行（UI 模式，<http://localhost:8501>）

```cmd
docker run --rm -it ^
  -p 8501:8501 ^
  -e RUN_MODE=ui ^
  --env-file .env ^
  -v "%CD%\output":/app/output ^
  text2video
```

### 使用 docker-compose（同时提供 api/ui 服务）

```cmd
docker compose up -d --build
```

- API: <http://localhost:8000>
- UI:  <http://localhost:8501>

日志查看：

```cmd
docker compose logs -f api
docker compose logs -f ui
```

提示与常见问题：

- 需要 `.env` 中提供 GUIJI_API_KEY 等参数；compose 已将 `.env` 作为文件挂载到容器并通过 `environment` 注入。

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

1. POST `/video/from-markdown`（直接返回 MP4 文件流）

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

## 技术介绍

### 提示词介绍

下面的提示词是用来生成插画的。

```python
def generate_illustration_prompts(script_json: str, llm: LLMProvider, model: str | None = None) -> list[dict]:
    """调用 LLM 生成插图提示 JSON 数组。"""
    system_message = (
        "您是一位插图提示生成专家，专注于为微课程生成详细的插图提示。"
    )
    prompt = f"""
### 任务
生成关于 {script_json} 的插图。返回仅包含多个插图详细信息的 JSON 数组。
### 插图描述要素:
- **主题:** 中心概念。
- **描述:** 详细叙述重点元素、情感和氛围。
- **场景:** 特定环境（如自然、城市、太空），包括颜色、光线和情绪。
- **对象:** 主要主题和特征（如人、动物、物体）。
- **动作:** 对象的动态（如飞行、跳跃、闲逛）。
- **风格:** 艺术技巧（如抽象、超现实主义、水彩、矢量）。
- **细节:** 其他特定信息（如纹理、背景元素）。
### 生成的提示结构:
描述, 场景, 包含对象, 动作. 以风格呈现, 强调细节。
### 输出格式要求
\```json
[
    {{
        "illustration_id": 1,
        "title": "阳光明媚的日子",
        "description": "一幅富有创意的数字艺术作品，描绘了一只由埃菲尔铁塔构建的长颈鹿。"
    }},
    {{
        "illustration_id": 2,
        "title": "繁星之夜",
        "description": "一幅黑暗幻想肖像，呈现了一匹马奔跑在风暴中，背景火焰般的景观。"
    }}
]
\```

输出格式为JSON。不包含任何额外的文字、解释或评论。
"""
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt},
    ]
    raw = llm.chat(messages, model=model)  # 允许 provider 内部忽略 model
    raw = raw.strip()
    if raw.startswith("```json"):
        raw = raw[len("```json"):].strip()
    if raw.endswith("```"):
        raw = raw[:-3].strip()
    try:
        data = json.loads(raw)
    except Exception as e:
        raise ValueError(f"插图提示解析失败: {raw[:200]} ... -> {e}") from e
    return data

```

下面是脚本口语化处理的提示词。

```python

def optimize_script_for_speech(script_items: list[dict[str, str]], llm: LLMProvider) -> list[dict[str, str]]:
    """调用 LLM 对 content 口语化。"""
    system_message = "您是录音稿专家。"
    prompt = f"""处理以下 JSON 中的 content 字段，并将内容转换为适合录音的纯文本形式。
返回处理后的 JSON，不要任何额外的说明。内容格式要求：
1. 对于英文的专有术语缩写，替换为全称。
2. 去除星号、井号等 Markdown 格式。
3. 去除换行符和段落分隔。
4. 对于复杂的长难句，使用中文句号分割，便于口语表达。
content 中的内容使用于发言使用。
下面的内容是待处理的 JSON：
{json.dumps(script_items, ensure_ascii=False)}

输出格式为 JSON。不包含任何额外的文字、解释或评论。
非常重要：请严格返回可被 json.loads() 解析的 JSON。注意事项：
- 使用英文逗号分隔数组中的对象，数组元素之间不能缺少逗号。
- 字符串必须使用双引号。
- 不要在 JSON 外添加任何说明性文字或代码块说明（例如 ```json ```）。
下面给出一个合法输出示例（仅供格式参考）：
[
    {{"title": "云计算简介", "content": "云计算是一种通过互联网按需提供计算资源，例如服务器、存储、数据库、网络和软件。它使企业可以更灵活地扩展资源并降低基础设施成本。"}},
    {{"title": "什么是云计算", "content": "云计算将传统本地部署的计算资源迁移到远程数据中心，由云服务提供商管理和维护。用户可以根据需要申请或释放资源，而无需关心底层硬件的运维。"}}
]
"""
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt},
    ]
    raw = llm.chat(messages)
    raw = raw.strip()
    if raw.startswith("```"):
        # 去掉 ```json 包装
        raw = re.sub(r'^```json', '', raw)
        raw = raw.removeprefix('```').strip('`')
    try:
        data = json.loads(raw)
    except Exception as e:  # 容错：如果模型返回非纯 JSON
        raise ValueError(f"LLM 返回内容解析失败: {raw[:200]} ... -> {e}") from e
    return data

```

下面是脚本生成的部分提示词。

```python

_FEW_SHOT_EXAMPLE =  """
## 云计算简介

云计算是一种通过互联网按需提供计算资源（例如服务器、存储、数据库、网络和软件）的方法。
它使企业可以更灵活地扩展资源并降低基础设施成本。

## 什么是云计算？

云计算将传统本地部署的计算资源迁移到远程数据中心，由云服务提供商管理和维护。
用户可以根据需要申请或释放资源，而无需关心底层硬件的运维。

## 云计算的主要类型

- 公有云：由第三方云服务提供商向多个租户提供服务。
- 私有云：为单个组织专属使用，通常部署在防火墙后面。
- 混合云：结合公有云与私有云的优势，支持在不同环境之间迁移工作负载。

## 云计算的优点

- 弹性伸缩：根据负载动态调整资源，避免资源浪费。
- 成本优化：按需付费，减少初始投资和运维成本。
- 高可用性：多可用区和灾备方案提升业务连续性。

了解这些基本概念后，你就可以开始评估云服务提供商并设计适合自己业务的云架构了。
"""

_SYSTEM_INSTRUCTION = """
你是一个专业的视频脚本撰写助手, 需要基于给定的主题或要点, 生成结构化的 Markdown 内容。
要求:
1) 偏教程风格, 面向初学者;
2) 使用若干 ## 二级标题拆分要点; 
3) 语言自然、口语化、利于后续 TTS 配音;
4) 避免过长段落, 每段 1-3 句; 
5) 不要添加额外的解释性前后缀。
"""

```
