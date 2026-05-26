from __future__ import annotations

import base64
import html
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components

from imagegen.core import (
    CONFIG_PATH,
    OUTPUT_DIR,
    augment_prompt_fields,
    create_client,
    edit_images,
    endpoint_url,
    generate_images,
    load_config,
    normalize_api_base,
    save_config,
    validate_payload,
)
from imagegen.history import (
    HistoryEntry,
    clear_history,
    delete_history_entry,
    get_history_image_path,
    list_history,
    save_to_history,
)

APP_DIR = Path(__file__).resolve().parent.parent
CLIPBOARD_COMPONENT_DIR = APP_DIR / "clipboard_image_component"
clipboard_image = components.declare_component(
    "clipboard_image",
    path=str(CLIPBOARD_COMPONENT_DIR),
)

RATIO_PRESETS: Dict[str, Tuple[int, int]] = {
    "\u81ea\u52a8": (0, 0),
    "1:1": (1024, 1024),
    "1:1 (2K)": (2048, 2048),
    "4:3": (1280, 960),
    "3:4": (960, 1280),
    "16:9": (1536, 864),
    "16:9 (2K)": (2048, 1152),
    "16:9 (4K)": (3840, 2160),
    "9:16": (864, 1536),
    "9:16 (4K)": (2160, 3840),
    "3:2": (1536, 1024),
    "2:3": (1024, 1536),
    "21:9": (1792, 768),
    "\u81ea\u5b9a\u4e49": (1024, 1024),
}

USE_CASES = [
    "",
    "photorealistic-natural",
    "product-mockup",
    "ui-mockup",
    "infographic-diagram",
    "scientific-educational",
    "ads-marketing",
    "productivity-visual",
    "logo-brand",
    "illustration-story",
    "stylized-concept",
    "historical-scene",
]


class ReferenceImage(NamedTuple):
    name: str
    data: bytes


def inject_style() -> None:
    st.markdown(
        """
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

          :root {
            --app-bg: #f8f9fc;
            --panel: #ffffff;
            --ink: #0b0f1a;
            --ink-secondary: #1e293b;
            --muted: #64748b;
            --muted-light: #94a3b8;
            --line: #e2e8f0;
            --line-light: #f1f5f9;
            --accent: #6366f1;
            --accent-hover: #4f46e5;
            --accent-light: rgba(99, 102, 241, 0.08);
            --accent-gradient: linear-gradient(135deg, #6366f1, #8b5cf6);
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.03);
            --shadow-md: 0 4px 16px rgba(0,0,0,0.06), 0 2px 8px rgba(0,0,0,0.04);
            --shadow-lg: 0 8px 32px rgba(0,0,0,0.08), 0 4px 16px rgba(0,0,0,0.04);
            --radius: 12px;
            --radius-lg: 16px;
            --radius-xl: 20px;
            --font: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
          }

          * { font-family: var(--font); }

          .stApp {
            background: linear-gradient(160deg, #f8f9fc 0%, #f1f3f9 40%, #f8f9fc 100%);
          }

          .stApp > header { display: none; }

          .block-container {
            max-width: 1280px;
            padding: 1.5rem 2rem 3rem;
          }

          [data-testid="stSidebar"] {
            background: rgba(255,255,255,0.85);
            border-right: 1px solid var(--line);
            backdrop-filter: blur(24px);
            padding: 1.5rem 0.5rem;
          }

          [data-testid="stSidebar"] > div:first-child {
            padding-top: 0;
          }

          [data-testid="stSidebar"] h2 {
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            color: var(--muted-light);
            margin: 1.25rem 0 0.5rem;
            padding: 0 0.75rem;
          }

          [data-testid="stSidebar"] h3 {
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--ink-secondary);
            margin: 0.75rem 0 0.25rem;
            padding: 0 0.75rem;
          }

          [data-testid="stSidebar"] .stTextInput input,
          [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {
            font-size: 0.8125rem;
          }

          [data-testid="stSidebar"] .stNumberInput input {
            font-size: 0.8125rem;
          }

          [data-testid="stSidebar"] [data-testid="baseButton-secondary"] {
            font-size: 0.8125rem;
          }

          [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
            font-size: 0.75rem;
            color: var(--muted);
          }

          .hero {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: var(--radius-xl);
            box-shadow: var(--shadow-md);
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1.75rem;
            padding: 1.5rem 2rem;
            position: relative;
            overflow: hidden;
          }

          .hero::before {
            content: '';
            position: absolute;
            inset: 0;
            background: var(--accent-gradient);
            opacity: 0.04;
            border-radius: inherit;
          }

          .hero-left { position: relative; z-index: 1; }

          .hero h1 {
            font-size: clamp(1.5rem, 3vw, 2rem);
            font-weight: 800;
            letter-spacing: -0.02em;
            color: var(--ink);
            margin: 0;
            line-height: 1.25;
          }

          .hero h1 span {
            background: var(--accent-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
          }

          .hero p {
            color: var(--muted);
            font-size: 0.875rem;
            margin: 0.25rem 0 0;
            line-height: 1.5;
          }

          .hero-right {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            flex-shrink: 0;
          }

          .status-chip {
            background: var(--accent-light);
            border: 1px solid rgba(99,102,241,0.15);
            border-radius: 999px;
            color: var(--accent);
            font-size: 0.75rem;
            font-weight: 600;
            padding: 0.4rem 0.9rem;
            white-space: nowrap;
          }

          .status-dot {
            display: inline-block;
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: var(--success);
            margin-right: 0.35rem;
            vertical-align: middle;
            animation: pulse-dot 2s ease-in-out infinite;
          }

          @keyframes pulse-dot {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
          }

          .sidebar-logo {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            padding: 0.25rem 0.75rem 0.5rem;
            margin-bottom: 0.5rem;
          }

          .sidebar-logo svg {
            width: 28px;
            height: 28px;
          }

          .sidebar-logo span {
            font-size: 1.1rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            color: var(--ink);
          }

          .sidebar-logo span small {
            font-size: 0.65rem;
            font-weight: 500;
            color: var(--muted-light);
            letter-spacing: 0;
          }

          [data-testid="stTabs"] {
            margin-top: 0.25rem;
          }

          [data-testid="stTabs"] [role="tablist"] {
            background: var(--line-light);
            border-radius: var(--radius);
            border: 1px solid var(--line);
            gap: 2px;
            padding: 3px;
          }

          [data-testid="stTabs"] button[role="tab"] {
            border: none;
            border-radius: calc(var(--radius) - 3px);
            font-size: 0.8125rem;
            font-weight: 600;
            color: var(--muted);
            padding: 0.45rem 1rem;
            transition: all 0.2s ease;
          }

          [data-testid="stTabs"] button[role="tab"]:hover {
            color: var(--ink-secondary);
            background: rgba(255,255,255,0.6);
          }

          [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            background: var(--panel);
            color: var(--ink);
            box-shadow: var(--shadow-sm);
          }

          [data-testid="stTextArea"] textarea,
          [data-testid="stTextInput"] input,
          [data-testid="stNumberInput"] input,
          [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            border-radius: var(--radius);
            border: 1.5px solid var(--line);
            font-size: 0.875rem;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
          }

          [data-testid="stTextArea"] textarea:focus,
          [data-testid="stTextInput"] input:focus,
          [data-testid="stNumberInput"] input:focus,
          [data-testid="stSelectbox"] div[data-baseweb="select"] > div:focus-within {
            border-color: var(--accent);
            box-shadow: 0 0 0 3px var(--accent-light);
          }

          .stButton button,
          .stDownloadButton button {
            border-radius: var(--radius);
            font-weight: 600;
            font-size: 0.875rem;
            height: 2.5rem;
            transition: all 0.2s ease;
          }

          .stButton button[kind="primary"] {
            background: var(--accent-gradient);
            color: #fff;
            border: none;
            box-shadow: 0 4px 14px rgba(99,102,241,0.3);
            height: 2.75rem;
            font-weight: 700;
            font-size: 0.9375rem;
          }

          .stButton button[kind="primary"]:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 20px rgba(99,102,241,0.4);
          }

          .stButton button[kind="primary"]:active {
            transform: translateY(0);
          }

          .stButton button[kind="primary"]:disabled {
            opacity: 0.5;
            box-shadow: none;
          }

          [data-testid="baseButton-secondary"] {
            border: 1.5px solid var(--line) !important;
          }

          [data-testid="stExpander"] {
            border: 1px solid var(--line);
            border-radius: var(--radius);
            background: var(--panel);
            margin: 0.75rem 0;
          }

          [data-testid="stExpander"] summary {
            font-weight: 600;
            font-size: 0.8125rem;
            color: var(--ink-secondary);
            padding: 0.6rem 1rem;
          }

          [data-testid="stExpander"] [data-testid="stExpanderContent"] {
            padding: 0 1rem 1rem;
          }

          .section-title {
            font-size: 1rem;
            font-weight: 700;
            color: var(--ink);
            margin: 0 0 0.25rem;
          }

          .section-subtitle {
            font-size: 0.8125rem;
            color: var(--muted);
            margin: 0 0 1rem;
            line-height: 1.5;
          }

          .uploaded-pill {
            background: var(--accent-light);
            border: 1px solid rgba(99,102,241,0.12);
            border-radius: 999px;
            color: var(--accent);
            display: inline-block;
            font-size: 0.75rem;
            font-weight: 500;
            margin: 0.25rem 0.4rem 0.25rem 0;
            padding: 0.3rem 0.7rem;
          }

          .history-card {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: var(--radius-lg);
            padding: 1.25rem;
            margin-bottom: 1rem;
            box-shadow: var(--shadow-sm);
            transition: box-shadow 0.2s ease;
          }

          .history-card:hover {
            box-shadow: var(--shadow-md);
          }

          .history-meta {
            color: var(--muted);
            font-size: 0.75rem;
          }

          .history-mode-badge {
            display: inline-block;
            background: var(--accent-light);
            border-radius: 6px;
            color: var(--accent);
            font-size: 0.6875rem;
            font-weight: 600;
            padding: 0.2rem 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.03em;
          }

          .history-prompt {
            color: var(--ink-secondary);
            font-size: 0.875rem;
            margin-top: 0.35rem;
            line-height: 1.5;
          }

          .stAlert {
            border-radius: var(--radius);
            border: none;
          }

          [data-testid="stAlert"] {
            border-radius: var(--radius);
            padding: 0.75rem 1rem;
          }

          .stAlert > div:first-child {
            font-size: 0.8125rem;
          }

          [data-testid="stImage"] {
            border-radius: var(--radius);
            overflow: hidden;
            box-shadow: var(--shadow-sm);
          }

          [data-testid="stImage"] img {
            border-radius: var(--radius);
            transition: transform 0.3s ease;
          }

          [data-testid="stImage"]:hover img {
            transform: scale(1.02);
          }

          .stDownloadButton button {
            background: var(--panel);
            border: 1.5px solid var(--line);
            font-size: 0.8125rem;
            height: 2.25rem;
          }

          .stDownloadButton button:hover {
            border-color: var(--accent);
            color: var(--accent);
            background: var(--accent-light);
          }

          hr {
            border-color: var(--line) !important;
            margin: 1.25rem 0 !important;
          }

          [data-testid="stProgress"] {
            border-radius: 999px;
            overflow: hidden;
          }

          [data-testid="stProgress"] > div {
            background: var(--accent-gradient) !important;
          }

          [data-testid="stInfo"] {
            background: var(--accent-light);
            color: var(--accent);
          }

          [data-testid="stNotification"] {
            border-radius: var(--radius);
          }

          .stCheckbox label {
            font-size: 0.8125rem;
            font-weight: 500;
          }

          .stCheckbox [data-baseweb="checkbox"] span {
            background-color: var(--accent) !important;
            border-color: var(--accent) !important;
          }

          [data-testid="stFileUploader"] section {
            border: 1.5px dashed var(--line);
            border-radius: var(--radius);
            padding: 0.75rem;
            background: var(--line-light);
            transition: border-color 0.2s ease, background 0.2s ease;
          }

          [data-testid="stFileUploader"] section:hover {
            border-color: var(--accent);
            background: var(--accent-light);
          }

          [data-testid="stFileUploader"] button {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: var(--radius);
            font-size: 0.8125rem;
          }

          .st-emotion-cache-1q7spjk {
            border-radius: var(--radius);
          }

          div[data-testid="column"] {
            gap: 0.75rem;
          }

          @media (max-width: 768px) {
            .hero {
              flex-direction: column;
              align-items: flex-start;
              padding: 1.25rem;
            }
            .hero-right { margin-top: 0.5rem; }
            .block-container { padding: 1rem; }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def data_url_to_reference(payload: Dict[str, Any]) -> Optional[ReferenceImage]:
    data_url = str(payload.get("dataUrl", ""))
    if "," not in data_url:
        return None
    header, encoded = data_url.split(",", 1)
    if not header.startswith("data:image/"):
        return None
    try:
        raw = base64.b64decode(encoded)
    except Exception:
        return None
    name = str(payload.get("name") or "clipboard-image.png")
    return ReferenceImage(name=name, data=raw)


def pasted_payload_to_references(payload: Optional[Dict[str, Any]]) -> List[ReferenceImage]:
    if not payload:
        return []
    if isinstance(payload.get("images"), list):
        references: List[ReferenceImage] = []
        for item in payload["images"]:
            if isinstance(item, dict):
                reference = data_url_to_reference(item)
                if reference is not None:
                    references.append(reference)
        return references

    data_url = str(payload.get("dataUrl", ""))
    if "," not in data_url:
        return []
    header, encoded = data_url.split(",", 1)
    if not header.startswith("data:image/"):
        return []
    try:
        raw = base64.b64decode(encoded)
    except Exception:
        return []
    name = str(payload.get("name") or "clipboard-image.png")
    return [ReferenceImage(name=name, data=raw)]


def _selectbox_index(options: List[Any], value: Any, default: int = 0) -> int:
    try:
        return options.index(value)
    except ValueError:
        return default


def _config_optional_select_value(config: Dict[str, str], key: str, default_label: str) -> str:
    value = config.get(key)
    return default_label if value in (None, "") else value


def make_size_selector(config: Dict[str, str]) -> str:
    saved_size = config.get("size", "")
    preset_options = list(RATIO_PRESETS.keys())
    preset_by_size = {f"{width}x{height}": label for label, (width, height) in RATIO_PRESETS.items()}
    preset = "\u81ea\u52a8" if saved_size == "auto" else preset_by_size.get(saved_size, "\u81ea\u5b9a\u4e49" if saved_size else "1:1")

    preset = st.sidebar.selectbox(
        "\u6bd4\u4f8b",
        preset_options,
        index=_selectbox_index(preset_options, preset),
    )
    default_width, default_height = RATIO_PRESETS[preset]

    if preset == "\u81ea\u52a8":
        st.sidebar.caption("\u5c3a\u5bf8\uff1aauto")
        return "auto"

    if preset == "\u81ea\u5b9a\u4e49":
        if "x" in saved_size:
            saved_width, saved_height = saved_size.lower().split("x", 1)
            if saved_width.isdigit() and saved_height.isdigit():
                default_width = min(3840, max(256, int(saved_width)))
                default_height = min(3840, max(256, int(saved_height)))
        col_w, col_h = st.sidebar.columns(2)
        with col_w:
            width = st.number_input("\u5bbd\u5ea6", min_value=256, max_value=3840, value=default_width, step=16)
        with col_h:
            height = st.number_input("\u9ad8\u5ea6", min_value=256, max_value=3840, value=default_height, step=16)
        width = int(round(width / 16) * 16)
        height = int(round(height / 16) * 16)
        st.sidebar.caption(f"\u5df2\u81ea\u52a8\u5bf9\u9f50\u4e3a 16 \u7684\u500d\u6570\uff1a{width}x{height}")
        return f"{width}x{height}"

    st.sidebar.caption(f"\u5c3a\u5bf8\uff1a{default_width}x{default_height}")
    return f"{default_width}x{default_height}"


def _provider_names(config: Dict[str, Any]) -> List[str]:
    providers = config.get("providers", [])
    if not isinstance(providers, list):
        return ["Default"]
    names = [str(provider.get("name") or "Default") for provider in providers if isinstance(provider, dict)]
    return names or ["Default"]


def _provider_by_name(config: Dict[str, Any], name: str) -> Dict[str, Any]:
    providers = config.get("providers", [])
    if isinstance(providers, list):
        for provider in providers:
            if isinstance(provider, dict) and str(provider.get("name") or "Default") == name:
                return provider
    return {
        "name": name or "Default",
        "base_url": os.getenv("OPENAI_BASE_URL", ""),
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "models": [os.getenv("IMAGE_GEN_MODEL", "gpt-image-2")],
        "active_model": os.getenv("IMAGE_GEN_MODEL", "gpt-image-2"),
    }


def _parse_models(value: str, fallback: str) -> List[str]:
    models: List[str] = []
    for line in value.replace(",", "\n").splitlines():
        model = line.strip()
        if model and model not in models:
            models.append(model)
    fallback = fallback.strip()
    if fallback and fallback not in models:
        models.insert(0, fallback)
    return models or ["gpt-image-2"]


def _upsert_provider(config: Dict[str, Any], provider: Dict[str, Any]) -> List[Dict[str, Any]]:
    providers = config.get("providers", [])
    if not isinstance(providers, list):
        providers = []
    updated: List[Dict[str, Any]] = []
    seen = False
    for existing in providers:
        if not isinstance(existing, dict):
            continue
        existing_name = str(existing.get("name") or "Default")
        if existing_name == provider["name"]:
            updated.append(provider)
            seen = True
        else:
            updated.append(dict(existing))
    if not seen:
        updated.append(provider)
    return updated


def connection_panel(config: Dict[str, Any]) -> Dict[str, Any]:
    st.sidebar.header("\u8fde\u63a5")
    provider_names = _provider_names(config)
    active_provider = str(config.get("active_provider") or provider_names[0])
    provider_name = st.sidebar.selectbox(
        "Provider",
        provider_names,
        index=_selectbox_index(provider_names, active_provider),
        key="provider-selector",
    )
    add_new_provider = st.sidebar.checkbox("Add New Provider", value=False)
    provider = _provider_by_name(config, provider_name)
    if add_new_provider:
        provider = {
            "name": "",
            "base_url": "",
            "api_key": "",
            "models": [os.getenv("IMAGE_GEN_MODEL", "gpt-image-2")],
            "active_model": os.getenv("IMAGE_GEN_MODEL", "gpt-image-2"),
        }
    new_provider_name = st.sidebar.text_input(
        "Provider Name",
        value=str(provider.get("name") or ("New Provider" if add_new_provider else provider_name)),
        help="\u4fee\u6539\u540e\u70b9 Save Settings \u4f1a\u4fdd\u5b58\u4e3a\u8fd9\u4e2a Provider\u3002",
    ).strip() or provider_name
    base_url = st.sidebar.text_input(
        "Base URL",
        value=str(provider.get("base_url") or os.getenv("OPENAI_BASE_URL", "")),
        placeholder="https://api.openai.com/v1",
    )
    api_key = st.sidebar.text_input(
        "API Key",
        value=str(provider.get("api_key") or os.getenv("OPENAI_API_KEY", "")),
        type="password",
    )
    provider_models = provider.get("models", [])
    if not isinstance(provider_models, list):
        provider_models = []
    active_model = str(provider.get("active_model") or provider.get("model") or config.get("model") or "gpt-image-2")
    models = [str(model).strip() for model in provider_models if str(model).strip()]
    if active_model and active_model not in models:
        models.insert(0, active_model)
    models = models or ["gpt-image-2"]
    model = st.sidebar.selectbox(
        "\u6a21\u578b",
        models,
        index=_selectbox_index(models, active_model),
    )
    models_text = st.sidebar.text_area(
        "Provider Models",
        value="\n".join(models),
        height=88,
        help="\u6bcf\u884c\u4e00\u4e2a\u6a21\u578b\uff0c\u4e5f\u652f\u6301\u9017\u53f7\u5206\u9694\u3002\u70b9 Save Settings \u540e\u8bb0\u4f4f\u3002",
    )
    models = _parse_models(models_text, model)
    if model not in models:
        models.insert(0, model)
    current_provider = {
        "name": new_provider_name,
        "base_url": normalize_api_base(base_url),
        "api_key": api_key.strip(),
        "models": models,
        "active_model": model,
    }
    providers = _upsert_provider(config, current_provider)

    st.sidebar.header("\u8f93\u51fa")
    size = make_size_selector(config)
    quality_options = ["medium", "low", "high", "auto"]
    format_options = ["png", "jpeg", "webp"]
    background_options = ["\u9ed8\u8ba4", "opaque", "transparent", "auto"]
    moderation_options = ["\u9ed8\u8ba4", "auto", "low"]
    quality = st.sidebar.selectbox(
        "\u8d28\u91cf",
        quality_options,
        index=_selectbox_index(quality_options, config.get("quality", "medium")),
    )
    output_format = st.sidebar.selectbox(
        "\u683c\u5f0f",
        format_options,
        index=_selectbox_index(format_options, config.get("output_format", "png")),
    )
    try:
        saved_n = int(config.get("n", "1"))
    except ValueError:
        saved_n = 1
    n = st.sidebar.number_input("\u6570\u91cf", min_value=1, max_value=10, value=min(10, max(1, saved_n)), step=1)
    background = st.sidebar.selectbox(
        "\u80cc\u666f",
        background_options,
        index=_selectbox_index(background_options, _config_optional_select_value(config, "background", "\u9ed8\u8ba4")),
    )
    moderation = st.sidebar.selectbox(
        "\u5ba1\u6838",
        moderation_options,
        index=_selectbox_index(moderation_options, _config_optional_select_value(config, "moderation", "\u9ed8\u8ba4")),
    )
    if background == "transparent" and output_format == "jpeg":
        st.sidebar.caption("\u900f\u660e\u80cc\u666f\u9700\u8981 alpha \u901a\u9053\uff0c\u5df2\u81ea\u52a8\u6539\u4e3a PNG \u8f93\u51fa\u3002")
        output_format = "png"

    return {
        "base_url": normalize_api_base(base_url),
        "api_key": api_key.strip(),
        "model": model.strip(),
        "active_provider": new_provider_name,
        "providers": providers,
        "size": size,
        "quality": quality,
        "output_format": output_format,
        "n": int(n),
        "background": None if background == "\u9ed8\u8ba4" else background,
        "moderation": None if moderation == "\u9ed8\u8ba4" else moderation,
    }


def effective_output_format(settings: Dict[str, Any]) -> str:
    if settings.get("background") == "transparent" and settings.get("output_format") == "jpeg":
        return "png"
    return str(settings.get("output_format", "png"))


def prompt_panel(key_prefix: str) -> Tuple[str, Dict[str, Optional[str]], bool]:
    prompt = st.text_area(
        "\u63d0\u793a\u8bcd",
        height=160,
        placeholder="\u63cf\u8ff0\u4f60\u60f3\u751f\u6210\u6216\u7f16\u8f91\u7684\u56fe\u7247...",
        key=f"{key_prefix}-prompt",
    )
    with st.expander("\u7ed3\u6784\u5316\u63d0\u793a\u8bcd", expanded=False):
        col_a, col_b = st.columns(2)
        with col_a:
            use_case = st.selectbox("\u7528\u9014", USE_CASES, index=0, key=f"{key_prefix}-use-case")
            subject = st.text_input("\u4e3b\u4f53", key=f"{key_prefix}-subject")
            style = st.text_input("\u98ce\u683c/\u5a92\u4ecb", key=f"{key_prefix}-style")
            palette = st.text_input("\u8272\u5f69", key=f"{key_prefix}-palette")
            constraints = st.text_area("\u7ea6\u675f", height=80, key=f"{key_prefix}-constraints")
        with col_b:
            scene = st.text_input("\u573a\u666f/\u80cc\u666f", key=f"{key_prefix}-scene")
            composition = st.text_input("\u6784\u56fe", key=f"{key_prefix}-composition")
            lighting = st.text_input("\u5149\u7ebf/\u6c1b\u56f4", key=f"{key_prefix}-lighting")
            text = st.text_input("\u753b\u9762\u6587\u5b57", key=f"{key_prefix}-text")
            negative = st.text_area("\u907f\u514d", height=80, key=f"{key_prefix}-negative")

    augment = st.checkbox("\u542f\u7528\u63d0\u793a\u8bcd\u589e\u5f3a", value=True, key=f"{key_prefix}-augment")
    fields = {
        "use_case": use_case or None,
        "scene": scene or None,
        "subject": subject or None,
        "style": style or None,
        "composition": composition or None,
        "lighting": lighting or None,
        "palette": palette or None,
        "materials": None,
        "text": text or None,
        "constraints": constraints or None,
        "negative": negative or None,
    }
    return prompt.strip(), fields, augment


def render_gallery(images: List[bytes], output_format: str) -> None:
    if not images:
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ext = "jpg" if output_format == "jpeg" else output_format
    cols = st.columns(min(3, len(images)))
    for index, image_bytes in enumerate(images, start=1):
        with cols[(index - 1) % len(cols)]:
            st.image(image_bytes, width='stretch')
            filename = f"image_{index}.{ext}"
            st.download_button(
                "\u4e0b\u8f7d\u56fe\u7247",
                data=image_bytes,
                file_name=filename,
                mime=f"image/{output_format}",
                key=f"download-{index}-{len(images)}",
            )


def render_reference_picker(key_prefix: str) -> List[ReferenceImage]:
    st.markdown('<p class="section-title">\u53c2\u8003\u56fe\u7247</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-subtitle">\u652f\u6301\u666e\u901a\u4e0a\u4f20\uff0c\u4e5f\u652f\u6301\u590d\u5236\u56fe\u7247\u540e\u76f4\u63a5 Ctrl+V \u7c98\u8d34\uff0c\u53ef\u540c\u65f6\u4e0a\u4f20\u591a\u5f20\u3002</p>',
        unsafe_allow_html=True,
    )

    uploaded_files = st.file_uploader(
        "\u4e0a\u4f20\u53c2\u8003\u56fe\u7247",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
        key=f"{key_prefix}-uploader",
    )

    pasted_payload = clipboard_image(key=f"{key_prefix}-clipboard")
    references = pasted_payload_to_references(pasted_payload)

    if uploaded_files:
        for f in uploaded_files:
            references.append(ReferenceImage(name=f.name, data=f.read()))

    if references:
        st.markdown(
            "".join(
                f'<span class="uploaded-pill">{index}. {html.escape(ref.name)}</span>'
                for index, ref in enumerate(references, start=1)
            ),
            unsafe_allow_html=True,
        )
        preview_cols = st.columns(min(4, len(references)))
        for index, ref in enumerate(references):
            with preview_cols[index % len(preview_cols)]:
                st.image(ref.data, width='stretch')
    return references


def check_api_key(settings: Dict[str, Any]) -> bool:
    if not settings["api_key"] and not os.getenv("OPENAI_API_KEY"):
        st.error("\u8bf7\u586b\u5199 API Key\uff0c\u6216\u8bbe\u7fbd OPENAI_API_KEY \u73af\u5883\u53d8\u91cf\u3002")
        return False
    return True


def tab_generate(settings: Dict[str, Any], config: Dict[str, str]) -> None:
    prompt, fields, augment = prompt_panel("generate")
    final_prompt = augment_prompt_fields(augment, prompt, fields) if prompt else ""
    with st.expander("\u6700\u7ec8\u8bf7\u6c42\u63d0\u793a\u8bcd", expanded=False):
        st.code(final_prompt or "\u8bf7\u8f93\u5165\u63d0\u793a\u8bcd", language="text")

    if st.button("\u751f\u6210\u56fe\u7247", type="primary", disabled=not prompt):
        if not check_api_key(settings):
            return
        payload = {
            "model": settings["model"],
            "prompt": final_prompt,
            "n": settings["n"],
            "size": settings["size"],
            "quality": settings["quality"],
            "output_format": settings["output_format"],
            "background": settings.get("background"),
            "moderation": settings.get("moderation"),
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        error = validate_payload(payload)
        if error:
            st.error(error)
            return
        with st.spinner("\u6b63\u5728\u751f\u6210\u56fe\u7247..."):
            try:
                images, transport = generate_images(settings, final_prompt)
            except Exception as exc:
                st.error(f"\u751f\u6210\u5931\u8d25\uff1a{exc}")
                return
        st.caption(f"\u8fde\u63a5\u65b9\u5f0f\uff1a{transport}")
        output_format = effective_output_format(settings)
        render_gallery(images, output_format)

        save_to_history(
            mode="generate",
            prompt=prompt,
            augmented_prompt=final_prompt,
            settings=settings,
            image_bytes_list=images,
            output_format=output_format,
        )


def tab_edit(settings: Dict[str, Any], config: Dict[str, str]) -> None:
    references = render_reference_picker("edit")
    edit_prompt, edit_fields, edit_augment = prompt_panel("edit")
    final_edit_prompt = augment_prompt_fields(edit_augment, edit_prompt, edit_fields) if edit_prompt else ""
    with st.expander("\u6700\u7ec8\u7f16\u8f91\u63d0\u793a\u8bcd", expanded=False):
        st.code(final_edit_prompt or "\u8bf7\u8f93\u5165\u7f16\u8f91\u63d0\u793a\u8bcd", language="text")

    can_edit = bool(edit_prompt) and bool(references)
    if st.button("\u7f16\u8f91\u56fe\u7247", type="primary", disabled=not can_edit):
        if not check_api_key(settings):
            return
        temp_paths: List[Path] = []
        try:
            for ref in references:
                suffix = Path(ref.name).suffix or ".png"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                    handle.write(ref.data)
                    temp_paths.append(Path(handle.name))

            with st.spinner("\u6b63\u5728\u7f16\u8f91\u56fe\u7247..."):
                try:
                    images, transport = edit_images(settings, final_edit_prompt, temp_paths)
                except Exception as exc:
                    st.error(f"\u7f16\u8f91\u5931\u8d25\uff1a{exc}")
                    return
            st.caption(f"\u8fde\u63a5\u65b9\u5f0f\uff1a{transport}")
            output_format = effective_output_format(settings)
            render_gallery(images, output_format)

            ref_names = [ref.name for ref in references]
            save_to_history(
                mode="edit",
                prompt=edit_prompt,
                augmented_prompt=final_edit_prompt,
                settings=settings,
                image_bytes_list=images,
                output_format=output_format,
                references=ref_names,
            )
        finally:
            for path in temp_paths:
                try:
                    path.unlink(missing_ok=True)
                except Exception:
                    pass


def tab_batch(settings: Dict[str, Any], config: Dict[str, str]) -> None:
    st.markdown('<p class="section-title">\u6279\u91cf\u751f\u6210</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="section-subtitle">\u6bcf\u884c\u4e00\u4e2a\u63d0\u793a\u8bcd\uff0c\u5c06\u4f9d\u6b21\u751f\u6210\u591a\u5f20\u56fe\u7247\u3002</p>',
        unsafe_allow_html=True,
    )

    batch_text = st.text_area(
        "\u63d0\u793a\u8bcd\u5217\u8868\uff08\u6bcf\u884c\u4e00\u4e2a\uff09",
        height=200,
        placeholder="\u4e00\u53ea\u5728\u6708\u5149\u4e0b\u6563\u6b65\u7684\u732b\n\u7e41\u661f\u70b9\u7f00\u7684\u591c\u7a7a\n\u672a\u6765\u57ce\u5e02\u7684\u9e1f\u77b0\u56fe\n...",
        key="batch-prompts",
    )

    prompts = [line.strip() for line in batch_text.strip().splitlines() if line.strip()] if batch_text else []
    if prompts:
        st.caption(f"\u5171 {len(prompts)} \u4e2a\u63d0\u793a\u8bcd")

    batch_augment = st.checkbox("\u542f\u7528\u63d0\u793a\u8bcd\u589e\u5f3a", value=True, key="batch-augment")

    if st.button("\u5f00\u59cb\u6279\u91cf\u751f\u6210", type="primary", disabled=not prompts):
        if not check_api_key(settings):
            return

        progress_bar = st.progress(0)
        status_text = st.empty()
        all_results = []

        for idx, raw_prompt in enumerate(prompts):
            final_prompt = raw_prompt
            if batch_augment:
                final_prompt = augment_prompt_fields(True, raw_prompt, {})

            payload = {
                "model": settings["model"],
                "prompt": final_prompt,
                "n": settings["n"],
                "size": settings["size"],
                "quality": settings["quality"],
                "output_format": settings["output_format"],
                "background": settings.get("background"),
                "moderation": settings.get("moderation"),
            }
            payload = {k: v for k, v in payload.items() if v is not None}
            error = validate_payload(payload)
            if error:
                st.error(f"\u7b2c {idx + 1} \u4e2a\u63d0\u793a\u8bcd\u9a8c\u8bc1\u5931\u8d25\uff1a{error}")
                continue

            status_text.text(f"\u6b63\u5728\u751f\u6210\u7b2c {idx + 1}/{len(prompts)} \u4e2a...\n{raw_prompt[:80]}")
            progress_bar.progress((idx) / len(prompts))

            try:
                images, transport = generate_images(settings, final_prompt)
                all_results.append((raw_prompt, images, transport))

                output_format = effective_output_format(settings)
                save_to_history(
                    mode="batch",
                    prompt=raw_prompt,
                    augmented_prompt=final_prompt,
                    settings=settings,
                    image_bytes_list=images,
                    output_format=output_format,
                )
            except Exception as exc:
                st.error(f"\u7b2c {idx + 1} \u4e2a\u63d0\u793a\u8bcd\u751f\u6210\u5931\u8d25\uff1a{exc}")
                all_results.append((raw_prompt, None, str(exc)))

        progress_bar.progress(1.0)
        status_text.text("\u6279\u91cf\u751f\u6210\u5b8c\u6210\uff01")

        if all_results:
            st.divider()
            for idx, (raw_prompt, images, transport) in enumerate(all_results, start=1):
                st.subheader(f"#{idx}: {raw_prompt[:60]}")
                if images is None:
                    st.error(f"\u751f\u6210\u5931\u8d25: {transport}")
                else:
                    st.caption(f"\u8fde\u63a5\u65b9\u5f0f\uff1a{transport}")
                    render_gallery(images, effective_output_format(settings))


def tab_history(settings: Dict[str, Any]) -> None:
    st.markdown('<p class="section-title">\u5386\u53f2\u8bb0\u5f55</p>', unsafe_allow_html=True)

    entries = list_history(limit=200)

    if not entries:
        st.info("\u8fd8\u6ca1\u6709\u751f\u6210\u8bb0\u5f55\u3002\u5f00\u59cb\u751f\u6210\u56fe\u7247\u540e\uff0c\u5386\u53f2\u8bb0\u5f55\u4f1a\u81ea\u52a8\u4fdd\u5b58\u3002")
        return

    filter_col1, filter_col2, filter_col3 = st.columns([1, 2, 1])
    with filter_col1:
        mode_filter = st.selectbox(
            "\u6a21\u5f0f",
            ["\u5168\u90e8", "generate", "edit", "batch"],
            key="history-mode-filter",
        )
    with filter_col2:
        search_query = st.text_input("\u641c\u7d22\u63d0\u793a\u8bcd", placeholder="\u8f93\u5165\u5173\u952e\u8bcd\u8fc7\u6ee4...", key="history-search")
    with filter_col3:
        st.write("")
        if st.button("\u6e05\u7a7a\u5386\u53f2", width='stretch', type="secondary"):
            count = clear_history()
            st.success(f"\u5df2\u6e05\u9664 {count} \u6761\u8bb0\u5f55")
            st.rerun()

    filtered = entries
    if mode_filter != "\u5168\u90e8":
        filtered = [e for e in filtered if e.mode == mode_filter]
    if search_query:
        filtered = [e for e in filtered if search_query.lower() in e.prompt.lower()]

    mode_label = {"generate": "\u751f\u6210", "edit": "\u7f16\u8f91", "batch": "\u6279\u91cf"}

    for entry in filtered:
        st.markdown('<div class="history-card">', unsafe_allow_html=True)
        label = mode_label.get(entry.mode, entry.mode)
        col_info, col_del = st.columns([6, 1])
        with col_info:
            st.markdown(
                f"<span class='history-mode-badge'>{label}</span>"
                f" &nbsp; <span class='history-meta'>#{entry.id} &middot; {entry.created_at}</span>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div class='history-prompt'>{html.escape(entry.prompt[:150])}</div>",
                unsafe_allow_html=True,
            )
        with col_del:
            if st.button("\u2716", key=f"del-{entry.id}"):
                delete_history_entry(entry.id)
                st.rerun()

        image_dir = get_history_image_path(entry.id, "")
        if entry.image_files:
            img_cols = st.columns(min(3, len(entry.image_files)))
            for idx, img_file in enumerate(entry.image_files):
                img_path = image_dir / img_file if isinstance(image_dir, Path) else Path(str(image_dir)) / img_file
                if img_path.exists():
                    with img_cols[idx % len(img_cols)]:
                        st.image(str(img_path), width='stretch')
                        with open(str(img_path), "rb") as f:
                            st.download_button(
                                "\u4e0b\u8f7d",
                                data=f.read(),
                                file_name=img_file,
                                mime=f"image/{entry.settings.get('output_format', 'png')}",
                                key=f"hdl-{entry.id}-{img_file}",
                            )
        st.markdown('</div>', unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(page_title="ImageGen", page_icon="\U0001f3a8", layout="wide")
    inject_style()

    config = load_config()

    st.sidebar.markdown(
        """
        <div class="sidebar-logo">
          <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="32" height="32" rx="8" fill="url(#glogo)"/>
            <path d="M16 6c-2 0-3.5 1.5-3.5 3.5 0 1.2.6 2.3 1.5 2.9v2.1l-4 2.3v-4.4a3.5 3.5 0 10-2 0v6.2l6 3.5V24a3.5 3.5 0 102 0v-1.9l4-2.3v-4.4a3.5 3.5 0 001.5-2.9C19.5 7.5 18 6 16 6z" fill="#fff"/>
            <defs><linearGradient id="glogo" x1="0" y1="0" x2="32" y2="32"><stop stop-color="#6366f1"/><stop offset="1" stop-color="#8b5cf6"/></linearGradient></defs>
          </svg>
          <span>ImageGen <small>v0.1</small></span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    settings = connection_panel(config)

    st.sidebar.divider()
    if st.sidebar.button("Save Settings", width='stretch'):
        save_config(settings)
        st.sidebar.success("Settings saved! Will load on next launch.")
    st.sidebar.caption(f"Output: {OUTPUT_DIR}")

    st.markdown(
        """
        <div class="hero">
          <div class="hero-left">
            <h1>Image<span>Gen</span></h1>
            <p>Local image generation console \u2014 create, edit, and batch-generate with any OpenAI-compatible API.</p>
          </div>
          <div class="hero-right">
            <div class="status-chip"><span class="status-dot"></span>API Connected</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_generate_tab, tab_edit_tab, tab_batch_tab, tab_history_tab = st.tabs(
        ["\u751f\u6210", "\u56fe\u751f\u56fe", "\u6279\u91cf", "\u5386\u53f2"]
    )

    with tab_generate_tab:
        tab_generate(settings, config)

    with tab_edit_tab:
        tab_edit(settings, config)

    with tab_batch_tab:
        tab_batch(settings, config)

    with tab_history_tab:
        tab_history(settings)


if __name__ == "__main__":
    main()
