# ImageGen

基于 OpenAI 兼容 API 的本地图片生成控制台。通过简洁的 Streamlit 界面，支持文生图、图生图和批量生成。

## 功能

- **文生图** — 从文本描述生成图片，支持结构化提示词增强
- **图生图** — 上传参考图片进行编辑，支持多图上传和剪贴板粘贴
- **批量生成** — 一次性从多个提示词生成多张图片
- **生成历史** — 浏览、搜索和下载所有已生成的图片
- **灵活设置** — 自定义模型、尺寸比例、质量、格式、背景和审核控制
- **API 兼容** — 支持任何 OpenAI 兼容接口（OpenAI、Azure、本地代理等）
- **自动回退** — SDK 失败时自动回退到 curl（处理 Windows 下的 SSL 问题）

## 快速开始

### Windows

1. **克隆并安装**
   ```batch
   git clone https://github.com/Wang-Zichuan/ImageGen.git
   cd ImageGen
   setup.bat
   ```

2. **配置** — 编辑 `config.json`，填入你的 API 信息：
   ```json
   {
     "base_url": "https://api.openai.com/v1",
     "api_key": "sk-...",
     "model": "gpt-image-2-reverse",
     "size": "1024x1024",
     "quality": "medium"
   }
   ```

3. **启动**
   ```batch
   start.bat
   ```

### 手动安装

```bash
# 安装 uv（如未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh   # Linux/macOS
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# 安装依赖并构建项目
uv sync
uv pip install -e .

# 配置
cp config.example.json config.json
# 编辑 config.json 填入你的 API Key

# 启动
uv run streamlit run imagegen/app.py --server.port 8502
```

## 配置项

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `base_url` | API 接口地址 | `https://api.openai.com/v1` |
| `api_key` | 你的 API 密钥 | *（必填）* |
| `model` | 模型名称 | `gpt-image-2` |
| `size` | 默认图片尺寸 | `1024x1024` |
| `quality` | 图片质量（low/medium/high/auto） | `medium` |

也可通过环境变量 `OPENAI_BASE_URL` 和 `OPENAI_API_KEY` 配置，优先级高于 `config.json`。

## 项目结构

```
ImageGen/
├── imagegen/                   # Python 核心包
│   ├── core.py                 # API 客户端和图片生成逻辑
│   ├── app.py                  # Streamlit Web 界面
│   ├── history.py              # 生成历史管理
│   └── __init__.py
├── clipboard_image_component/  # 浏览器粘贴组件
│   └── index.html
├── assets/                     # 项目资源文件
│   ├── imagegen-small.svg
│   └── imagegen.png
├── .github/                    # GitHub Issue/PR 模板
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
├── config.example.json         # 配置模板
├── pyproject.toml              # 项目元数据和依赖
├── setup.bat                   # 一键环境安装（Windows）
├── start.bat                   # 一键启动（Windows）
├── uv.lock                     # 锁定依赖版本
└── LICENSE                     # MIT 许可证
```

## 技术栈

- [Streamlit](https://streamlit.io/) — Web UI 框架
- [OpenAI Python SDK](https://github.com/openai/openai-python) — API 客户端
- [Pillow](https://python-pillow.org/) — 图片处理
- [uv](https://docs.astral.sh/uv/) — Python 包管理

## 许可证

[MIT](LICENSE)
