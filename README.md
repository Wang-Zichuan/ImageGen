# ImageGen

A local image generation console powered by any OpenAI-compatible API. Generate, edit, and batch-create images through a clean Streamlit interface.

## Features

- **Text to Image** — Generate images from text prompts with structured prompt augmentation
- **Image to Image** — Edit existing images with reference images (supports multi-image upload & clipboard paste)
- **Batch Generation** — Generate multiple images from a list of prompts in one go
- **Generation History** — Browse, search, and download all previously generated images
- **Flexible Settings** — Custom model, size ratios, quality, format, background, and moderation controls
- **API Compatible** — Works with any OpenAI-compatible endpoint (OpenAI, Azure, local proxies, etc.)
- **Automatic Fallback** — Falls back to curl when the SDK fails (handles SSL issues on Windows)

## Quick Start

### Windows

1. **Clone & Setup**
   ```batch
   git clone https://github.com/<your-username>/imagegen.git
   cd imagegen
   setup.bat
   ```

2. **Configure** — Edit `config.json` and fill in your API key:
   ```json
   {
     "base_url": "https://api.openai.com/v1",
     "api_key": "sk-...",
     "model": "gpt-image-2",
     "size": "1024x1024",
     "quality": "medium"
   }
   ```

3. **Launch**
   ```batch
   start.bat
   ```

### Manual Setup

```bash
# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh   # Linux/macOS
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows

# Setup
uv sync

# Configure
cp config.example.json config.json
# Edit config.json with your API key

# Run
uv run streamlit run imagegen/app.py --server.port 8502
```

## Configuration

| Field      | Description                          | Default                  |
|------------|--------------------------------------|--------------------------|
| `base_url` | API endpoint                         | `https://api.openai.com/v1` |
| `api_key`  | Your API key                         | *(required)*             |
| `model`    | Model name                           | `gpt-image-2`           |
| `size`     | Default image size                   | `1024x1024`             |
| `quality`  | Image quality (`low/medium/high/auto`) | `medium`              |

You can also set environment variables `OPENAI_BASE_URL` and `OPENAI_API_KEY` instead of `config.json`.

## Screenshots

> *(Add screenshots here after first run)*

## Project Structure

```
imagegen/
├── imagegen/                   # Python package
│   ├── core.py                 # API client and image generation logic
│   ├── app.py                  # Streamlit web interface
│   ├── history.py              # Generation history management
│   └── __init__.py
├── clipboard_image_component/  # Browser paste component
│   └── index.html
├── references/                 # Prompting guides and API docs
├── config.example.json         # Configuration template
├── pyproject.toml              # Project metadata and dependencies
├── setup.bat                   # One-click environment setup (Windows)
├── start.bat                   # One-click launch (Windows)
└── uv.lock                     # Locked dependencies
```

## Tech Stack

- [Streamlit](https://streamlit.io/) — Web UI
- [OpenAI Python SDK](https://github.com/openai/openai-python) — API client
- [Pillow](https://python-pillow.org/) — Image processing
- [uv](https://docs.astral.sh/uv/) — Package management

## License

[MIT](LICENSE)