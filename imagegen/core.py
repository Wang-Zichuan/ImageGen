from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import tempfile
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI


APP_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = APP_DIR / "config.json"
OUTPUT_DIR = APP_DIR / "output"

DEFAULT_MODEL = "gpt-image-2"
DEFAULT_SIZE = "auto"
DEFAULT_QUALITY = "medium"

ALLOWED_LEGACY_SIZES = {"1024x1024", "1536x1024", "1024x1536", "auto"}
ALLOWED_QUALITIES = {"low", "medium", "high", "auto"}
ALLOWED_BACKGROUNDS = {"transparent", "opaque", "auto", None}

GPT_IMAGE_2_MAX_EDGE = 3840
GPT_IMAGE_2_MIN_PIXELS = 655_360
GPT_IMAGE_2_MAX_PIXELS = 8_294_400
GPT_IMAGE_2_MAX_RATIO = 3.0


def load_config() -> Dict[str, str]:
    if not CONFIG_PATH.exists():
        return {}
    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {str(k): str(v) for k, v in raw.items() if v is not None}


def save_config(settings: Dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "base_url": settings.get("base_url", ""),
        "api_key": settings.get("api_key", ""),
        "model": settings.get("model", "gpt-image-2"),
        "size": settings.get("size", "1024x1024"),
        "quality": settings.get("quality", "medium"),
    }
    CONFIG_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def normalize_api_base(base_url: str) -> str:
    return base_url.strip().rstrip("/")


def create_client(base_url: Optional[str] = None, api_key: Optional[str] = None) -> OpenAI:
    for env_var in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        val = os.environ.get(env_var)
        if val and not os.path.exists(val):
            del os.environ[env_var]
    kwargs: Dict[str, Any] = {}
    if base_url:
        kwargs["base_url"] = base_url
    if api_key:
        kwargs["api_key"] = api_key
    return OpenAI(**kwargs)


def endpoint_url(base_url: str, path: str) -> str:
    base = (base_url or "https://api.openai.com/v1").rstrip("/")
    return urllib.parse.urljoin(base + "/", path.lstrip("/"))


def extract_image_bytes(item: Any) -> bytes:
    if item.b64_json:
        return base64.b64decode(item.b64_json)
    if item.url:
        return download_url_with_curl(item.url)
    raise RuntimeError("API response has no image data.")


def download_url_with_curl(url: str) -> bytes:
    with tempfile.NamedTemporaryFile(delete=False) as response_file:
        response_path = Path(response_file.name)
    try:
        completed = subprocess.run(
            ["curl.exe", "-sS", "-L", url, "-o", str(response_path)],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "Failed to download image URL")
        return response_path.read_bytes()
    finally:
        response_path.unlink(missing_ok=True)


def should_retry_with_curl(exc: Exception) -> bool:
    text = f"{exc.__class__.__name__}: {exc}"
    markers = [
        "Connection error",
        "ConnectError",
        "EOF occurred in violation of protocol",
        "SSL connection could not be established",
    ]
    return any(marker.lower() in text.lower() for marker in markers)


def curl_json_request(url: str, payload: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as payload_file:
        json.dump(payload, payload_file, ensure_ascii=False)
        payload_path = Path(payload_file.name)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as response_file:
        response_path = Path(response_file.name)
    try:
        command = [
            "curl.exe", "-sS", "-X", "POST", url,
            "-H", f"Authorization: Bearer {api_key}",
            "-H", "Content-Type: application/json",
            "--data-binary", f"@{payload_path}",
            "-o", str(response_path), "-w", "%{http_code}",
        ]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=180)
        body = response_path.read_text(encoding="utf-8", errors="replace")
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "curl request failed")
        status_code = int((completed.stdout or "0").strip() or "0")
        if status_code >= 400:
            raise RuntimeError(format_api_error(status_code, body))
        return json.loads(body)
    finally:
        payload_path.unlink(missing_ok=True)
        response_path.unlink(missing_ok=True)


def curl_multipart_request(
    url: str,
    payload: Dict[str, Any],
    image_paths: List[Path],
    api_key: str,
) -> Dict[str, Any]:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as response_file:
        response_path = Path(response_file.name)
    command = [
        "curl.exe", "-sS", "-X", "POST", url,
        "-H", f"Authorization: Bearer {api_key}",
    ]
    for key, value in payload.items():
        if value is not None:
            command.extend(["-F", f"{key}={value}"])
    for path in image_paths:
        command.extend(["-F", f"image=@{path}"])
    command.extend(["-o", str(response_path), "-w", "%{http_code}"])
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=180)
        body = response_path.read_text(encoding="utf-8", errors="replace")
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "curl request failed")
        status_code = int((completed.stdout or "0").strip() or "0")
        if status_code >= 400:
            raise RuntimeError(format_api_error(status_code, body))
        return json.loads(body)
    finally:
        response_path.unlink(missing_ok=True)


def format_api_error(status_code: int, body: str) -> str:
    try:
        parsed = json.loads(body)
        message = parsed.get("error", {}).get("message") or parsed.get("message") or body
    except Exception:
        message = body
    return f"API request failed with HTTP {status_code}: {message}"


def response_json_to_images(response: Dict[str, Any]) -> List[bytes]:
    images: List[bytes] = []
    for item in response.get("data", []):
        if item.get("b64_json"):
            images.append(base64.b64decode(item["b64_json"]))
            continue
        if item.get("url"):
            images.append(download_url_with_curl(item["url"]))
            continue
        raise RuntimeError("API response has no image data.")
    return images


def augment_prompt_fields(augment: bool, prompt: str, fields: Dict[str, Optional[str]]) -> str:
    if not augment:
        return prompt
    sections: List[str] = []
    if fields.get("use_case"):
        sections.append(f"Use case: {fields['use_case']}")
    sections.append(f"Primary request: {prompt}")
    if fields.get("scene"):
        sections.append(f"Scene/background: {fields['scene']}")
    if fields.get("subject"):
        sections.append(f"Subject: {fields['subject']}")
    if fields.get("style"):
        sections.append(f"Style/medium: {fields['style']}")
    if fields.get("composition"):
        sections.append(f"Composition/framing: {fields['composition']}")
    if fields.get("lighting"):
        sections.append(f"Lighting/mood: {fields['lighting']}")
    if fields.get("palette"):
        sections.append(f"Color palette: {fields['palette']}")
    if fields.get("materials"):
        sections.append(f"Materials/textures: {fields['materials']}")
    if fields.get("text"):
        sections.append(f"Text (verbatim): \"{fields['text']}\"")
    if fields.get("constraints"):
        sections.append(f"Constraints: {fields['constraints']}")
    if fields.get("negative"):
        sections.append(f"Avoid: {fields['negative']}")
    return "\n".join(sections)


def validate_payload(payload: Dict[str, Any]) -> Optional[str]:
    try:
        model = str(payload.get("model", DEFAULT_MODEL))
        if not model:
            return "model must not be empty."
        n = int(payload.get("n", 1))
        if n < 1 or n > 10:
            return "n must be between 1 and 10"
        size = str(payload.get("size", DEFAULT_SIZE))
        quality = str(payload.get("quality", DEFAULT_QUALITY))
        background = payload.get("background")
        if quality not in ALLOWED_QUALITIES:
            return "quality must be one of low, medium, high, or auto."
        if background not in ALLOWED_BACKGROUNDS:
            return "background must be one of transparent, opaque, or auto."
        if background == "transparent" and payload.get("output_format") not in (None, "png", "webp"):
            return "transparent background requires output-format png or webp."
        if model == "gpt-image-2" and background == "transparent":
            return "transparent backgrounds are not supported in gpt-image-2."
    except Exception as exc:
        return str(exc)
    return None


def generate_images(
    settings: Dict[str, Any],
    prompt: str,
) -> Tuple[List[bytes], str]:
    client = create_client(
        base_url=settings.get("base_url") or None,
        api_key=settings.get("api_key") or None,
    )
    payload = {
        "model": settings["model"],
        "prompt": prompt,
        "n": settings["n"],
        "size": settings["size"],
        "quality": settings["quality"],
        "output_format": settings["output_format"],
        "background": settings.get("background"),
        "moderation": settings.get("moderation"),
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    try:
        result = client.images.generate(**payload)
        return [extract_image_bytes(item) for item in result.data], "OpenAI SDK"
    except Exception as exc:
        if not should_retry_with_curl(exc):
            raise
        response = curl_json_request(
            endpoint_url(settings["base_url"], "/images/generations"),
            payload,
            settings.get("api_key") or os.getenv("OPENAI_API_KEY", ""),
        )
        return response_json_to_images(response), "curl fallback"


def edit_images(
    settings: Dict[str, Any],
    prompt: str,
    image_paths: List[Path],
) -> Tuple[List[bytes], str]:
    client = create_client(
        base_url=settings.get("base_url") or None,
        api_key=settings.get("api_key") or None,
    )
    with _open_files(image_paths) as image_files:
        payload = {
            "model": settings["model"],
            "prompt": prompt,
            "image": image_files if len(image_files) > 1 else image_files[0],
            "n": settings["n"],
            "size": settings["size"],
            "quality": settings["quality"],
            "output_format": settings["output_format"],
            "background": settings.get("background"),
            "moderation": settings.get("moderation"),
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        try:
            result = client.images.edit(**payload)
            return [extract_image_bytes(item) for item in result.data], "OpenAI SDK"
        except Exception as exc:
            if not should_retry_with_curl(exc):
                raise
            curl_payload = dict(payload)
            curl_payload.pop("image", None)
            response = curl_multipart_request(
                endpoint_url(settings["base_url"], "/images/edits"),
                curl_payload,
                image_paths,
                settings.get("api_key") or os.getenv("OPENAI_API_KEY", ""),
            )
            return response_json_to_images(response), "curl fallback"


class _FileBundle:
    def __init__(self, paths: List[Path]):
        self._paths = paths
        self._handles: List[Any] = []

    def __enter__(self):
        self._handles = [p.open("rb") for p in self._paths]
        return self._handles

    def __exit__(self, exc_type, exc, tb):
        for handle in self._handles:
            try:
                handle.close()
            except Exception:
                pass
        return False


def _open_files(paths: List[Path]):
    return _FileBundle(paths)