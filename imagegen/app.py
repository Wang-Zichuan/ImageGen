from __future__ import annotations

import base64
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components

from imagegen.core import (
    OUTPUT_DIR,
    augment_prompt_fields,
    create_client,
    edit_images,
    endpoint_url,
    generate_images,
    load_config,
    normalize_api_base,
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
    "1:1": (1024, 1024),
    "4:3": (1280, 960),
    "3:4": (960, 1280),
    "16:9": (1536, 864),
    "9:16": (864, 1536),
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
          :root {
            --app-bg: #f6f7fb;
            --panel: #ffffff;
            --ink: #101828;
            --muted: #667085;
            --line: #e4e7ec;
            --accent: #ef4444;
            --accent-2: #0ea5e9;
          }

          .stApp {
            background:
              radial-gradient(circle at 18% 0%, rgba(239, 68, 68, 0.10), transparent 28rem),
              radial-gradient(circle at 90% 10%, rgba(14, 165, 233, 0.10), transparent 30rem),
              var(--app-bg);
          }

          [data-testid="stSidebar"] {
            background: rgba(255, 255, 255, 0.82);
            border-right: 1px solid rgba(228, 231, 236, 0.9);
            backdrop-filter: blur(18px);
          }

          [data-testid="stSidebar"] h2,
          [data-testid="stSidebar"] h3 {
            letter-spacing: 0;
          }

          .block-container {
            max-width: 1180px;
            padding-top: 3rem;
          }

          .hero {
            align-items: end;
            display: flex;
            gap: 20px;
            justify-content: space-between;
            margin-bottom: 22px;
          }

          .hero h1 {
            color: var(--ink);
            font-size: clamp(34px, 5vw, 58px);
            letter-spacing: 0;
            line-height: 1;
            margin: 0;
          }

          .hero p {
            color: var(--muted);
            font-size: 15px;
            margin: 10px 0 0;
          }

          .status-chip {
            background: #101828;
            border-radius: 999px;
            color: #fff;
            font-size: 13px;
            font-weight: 650;
            padding: 10px 14px;
            white-space: nowrap;
          }

          [data-testid="stTabs"] [role="tablist"] {
            border-bottom: 1px solid var(--line);
            gap: 10px;
          }

          [data-testid="stTabs"] button[role="tab"] {
            border-radius: 12px 12px 0 0;
            font-weight: 650;
            padding: 12px 18px;
          }

          [data-testid="stTextArea"] textarea,
          [data-testid="stTextInput"] input,
          [data-testid="stNumberInput"] input,
          [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            border-radius: 14px;
          }

          .stButton button,
          .stDownloadButton button {
            border-radius: 14px;
            font-weight: 700;
            min-height: 44px;
          }

          .stButton button[kind="primary"] {
            background: linear-gradient(135deg, var(--accent), #fb7185);
            border: 0;
            box-shadow: 0 12px 28px rgba(239, 68, 68, 0.22);
          }

          .section-card {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 18px;
          }

          .section-title {
            color: var(--ink);
            font-size: 17px;
            font-weight: 750;
            margin: 0 0 6px;
          }

          .section-subtitle {
            color: var(--muted);
            font-size: 13px;
            margin: 0 0 14px;
          }

          .uploaded-pill {
            background: #f9fafb;
            border: 1px solid var(--line);
            border-radius: 999px;
            color: #344054;
            display: inline-block;
            font-size: 12px;
            margin: 4px 6px 4px 0;
            padding: 7px 10px;
          }

          .history-card {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 16px;
            margin-bottom: 12px;
          }

          .history-meta {
            color: var(--muted);
            font-size: 12px;
          }

          .history-prompt {
            color: var(--ink);
            font-size: 14px;
            margin-top: 4px;
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


def make_size_selector() -> str:
    preset = st.sidebar.selectbox("\u6bd4\u4f8b", list(RATIO_PRESETS.keys()), index=0)
    default_width, default_height = RATIO_PRESETS[preset]

    if preset == "\u81ea\u5b9a\u4e49":
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


def connection_panel(config: Dict[str, str]) -> Dict[str, Any]:
    st.sidebar.header("\u8fde\u63a5")
    base_url = st.sidebar.text_input(
        "Base URL",
        value=config.get("base_url") or os.getenv("OPENAI_BASE_URL", ""),
        placeholder="https://api.openai.com/v1",
    )
    api_key = st.sidebar.text_input(
        "API Key",
        value=config.get("api_key") or os.getenv("OPENAI_API_KEY", ""),
        type="password",
    )
    model = st.sidebar.text_input(
        "\u6a21\u578b",
        value=config.get("model") or os.getenv("IMAGE_GEN_MODEL", "gpt-image-2"),
    )

    st.sidebar.header("\u8f93\u51fa")
    size = make_size_selector()
    quality = st.sidebar.selectbox(
        "\u8d28\u91cf",
        ["medium", "low", "high", "auto"],
        index=["medium", "low", "high", "auto"].index(config.get("quality", "medium"))
        if config.get("quality", "medium") in {"medium", "low", "high", "auto"}
        else 0,
    )
    output_format = st.sidebar.selectbox("\u683c\u5f0f", ["png", "jpeg", "webp"], index=0)
    n = st.sidebar.number_input("\u6570\u91cf", min_value=1, max_value=10, value=1, step=1)
    background = st.sidebar.selectbox("\u80cc\u666f", ["\u9ed8\u8ba4", "opaque", "transparent", "auto"], index=0)
    moderation = st.sidebar.selectbox("\u5ba1\u6838", ["\u9ed8\u8ba4", "auto", "low"], index=0)

    return {
        "base_url": normalize_api_base(base_url),
        "api_key": api_key.strip(),
        "model": model.strip(),
        "size": size,
        "quality": quality,
        "output_format": output_format,
        "n": int(n),
        "background": None if background == "\u9ed8\u8ba4" else background,
        "moderation": None if moderation == "\u9ed8\u8ba4" else moderation,
    }


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
            st.image(image_bytes, use_container_width=True)
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
                f'<span class="uploaded-pill">{index}. {ref.name}</span>'
                for index, ref in enumerate(references, start=1)
            ),
            unsafe_allow_html=True,
        )
        preview_cols = st.columns(min(4, len(references)))
        for index, ref in enumerate(references):
            with preview_cols[index % len(preview_cols)]:
                st.image(ref.data, use_container_width=True)
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
        render_gallery(images, settings["output_format"])

        save_to_history(
            mode="generate",
            prompt=prompt,
            augmented_prompt=final_prompt,
            settings=settings,
            image_bytes_list=images,
            output_format=settings["output_format"],
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
            render_gallery(images, settings["output_format"])

            ref_names = [ref.name for ref in references]
            save_to_history(
                mode="edit",
                prompt=edit_prompt,
                augmented_prompt=final_edit_prompt,
                settings=settings,
                image_bytes_list=images,
                output_format=settings["output_format"],
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

                save_to_history(
                    mode="batch",
                    prompt=raw_prompt,
                    augmented_prompt=final_prompt,
                    settings=settings,
                    image_bytes_list=images,
                    output_format=settings["output_format"],
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
                    render_gallery(images, settings["output_format"])


def tab_history(settings: Dict[str, Any]) -> None:
    st.markdown('<p class="section-title">\u751f\u6210\u5386\u53f2</p>', unsafe_allow_html=True)

    entries = list_history(limit=200)

    if not entries:
        st.info("\u8fd8\u6ca1\u6709\u751f\u6210\u8bb0\u5f55\u3002\u5f00\u59cb\u751f\u6210\u56fe\u7247\u540e\uff0c\u5386\u53f2\u8bb0\u5f55\u4f1a\u81ea\u52a8\u4fdd\u5b58\u3002")
        return

    col_mode = st.columns([1, 3, 1])
    with col_mode[0]:
        mode_filter = st.selectbox(
            "\u7b5b\u9009\u6a21\u5f0f",
            ["\u5168\u90e8", "generate", "edit", "batch"],
            key="history-mode-filter",
        )

    search_query = st.text_input("\u641c\u7d22\u63d0\u793a\u8bcd", key="history-search")
    clear_col1, clear_col2 = st.columns([1, 5])
    with clear_col1:
        if st.button("\u6e05\u7a7a\u5386\u53f2", type="secondary"):
            count = clear_history()
            st.success(f"\u5df2\u6e05\u9664 {count} \u6761\u5386\u53f2\u8bb0\u5f55")
            st.rerun()

    filtered = entries
    if mode_filter != "\u5168\u90e8":
        filtered = [e for e in filtered if e.mode == mode_filter]
    if search_query:
        filtered = [e for e in filtered if search_query.lower() in e.prompt.lower()]

    mode_label = {"generate": "\u751f\u6210", "edit": "\u7f16\u8f91", "batch": "\u6279\u91cf"}

    for entry in filtered:
        with st.container():
            label = mode_label.get(entry.mode, entry.mode)
            col_info, col_del = st.columns([6, 1])
            with col_info:
                st.markdown(
                    f"**#{entry.id}** &nbsp; `[{label}]` &nbsp; <span class='history-meta'>{entry.created_at}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"<div class='history-prompt'>{entry.prompt[:120]}</div>", unsafe_allow_html=True)
            with col_del:
                if st.button("\u2716", key=f"del-{entry.id}"):
                    delete_history_entry(entry.id)
                    st.rerun()

            image_dir = get_history_image_path(entry.id, "")
            for img_file in entry.image_files:
                img_path = image_dir / img_file if isinstance(image_dir, Path) else Path(str(image_dir)) / img_file
                if img_path.exists():
                    st.image(str(img_path), use_container_width=True)
                    with open(str(img_path), "rb") as f:
                        st.download_button(
                            "\u4e0b\u8f7d",
                            data=f.read(),
                            file_name=img_file,
                            mime=f"image/{entry.settings.get('output_format', 'png')}",
                            key=f"hdl-{entry.id}-{img_file}",
                        )
            st.divider()


def main() -> None:
    st.set_page_config(page_title="ImageGen", page_icon="\U0001f3a8", layout="wide")
    inject_style()

    config = load_config()
    settings = connection_panel(config)

    st.markdown(
        """
        <div class="hero">
          <div>
            <h1>ImageGen</h1>
            <p>\u4e00\u4e2a\u9762\u5411\u521b\u4f5c\u548c\u53c2\u8003\u56fe\u7f16\u8f91\u7684\u672c\u5730\u56fe\u7247\u751f\u6210\u63a7\u5236\u53f0\u3002</p>
          </div>
          <div class="status-chip">OpenAI-compatible API</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_generate_tab, tab_edit_tab, tab_batch_tab, tab_history_tab = st.tabs(
        ["\u751f\u6210", "\u7f16\u8f91\uff08\u56fe\u751f\u56fe\uff09", "\u6279\u91cf\u751f\u6210", "\u5386\u53f2\u8bb0\u5f55"]
    )

    with tab_generate_tab:
        tab_generate(settings, config)

    with tab_edit_tab:
        tab_edit(settings, config)

    with tab_batch_tab:
        tab_batch(settings, config)

    with tab_history_tab:
        tab_history(settings)

    st.sidebar.divider()
    st.sidebar.caption(f"\u8f93\u51fa\u76ee\u5f55\uff1a{OUTPUT_DIR}")


if __name__ == "__main__":
    main()