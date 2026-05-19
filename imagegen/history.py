from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

HISTORY_DIR = Path(__file__).resolve().parent.parent / "output" / "history"


class HistoryEntry:
    def __init__(
        self,
        id: str,
        mode: str,
        prompt: str,
        augmented_prompt: str,
        settings: Dict[str, Any],
        image_files: List[str],
        created_at: str,
        references: Optional[List[str]] = None,
    ):
        self.id = id
        self.mode = mode
        self.prompt = prompt
        self.augmented_prompt = augmented_prompt
        self.settings = settings
        self.image_files = image_files
        self.created_at = created_at
        self.references = references or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "mode": self.mode,
            "prompt": self.prompt,
            "augmented_prompt": self.augmented_prompt,
            "settings": self.settings,
            "image_files": self.image_files,
            "created_at": self.created_at,
            "references": self.references,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HistoryEntry":
        return cls(
            id=data["id"],
            mode=data["mode"],
            prompt=data["prompt"],
            augmented_prompt=data.get("augmented_prompt", data["prompt"]),
            settings=data.get("settings", {}),
            image_files=data.get("image_files", []),
            created_at=data.get("created_at", ""),
            references=data.get("references", []),
        )


def _ensure_history_dir() -> Path:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    return HISTORY_DIR


def save_to_history(
    mode: str,
    prompt: str,
    augmented_prompt: str,
    settings: Dict[str, Any],
    image_bytes_list: List[bytes],
    output_format: str,
    references: Optional[List[str]] = None,
) -> HistoryEntry:
    history_dir = _ensure_history_dir()
    timestamp = datetime.now()
    entry_id = timestamp.strftime("%Y%m%d_%H%M%S_%f")
    entry_dir = history_dir / entry_id
    entry_dir.mkdir(parents=True, exist_ok=True)

    ext = "jpg" if output_format == "jpeg" else output_format
    image_files: List[str] = []
    for idx, image_bytes in enumerate(image_bytes_list, start=1):
        filename = f"image_{idx}.{ext}"
        (entry_dir / filename).write_bytes(image_bytes)
        image_files.append(filename)

    entry = HistoryEntry(
        id=entry_id,
        mode=mode,
        prompt=prompt,
        augmented_prompt=augmented_prompt,
        settings=settings,
        image_files=image_files,
        created_at=timestamp.isoformat(),
        references=references or [],
    )

    meta_path = entry_dir / "meta.json"
    meta_path.write_text(json.dumps(entry.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    return entry


def list_history(limit: int = 100) -> List[HistoryEntry]:
    history_dir = _ensure_history_dir()
    entries: List[HistoryEntry] = []
    if not history_dir.exists():
        return entries

    for entry_dir in sorted(history_dir.iterdir(), reverse=True):
        if not entry_dir.is_dir():
            continue
        meta_path = entry_dir / "meta.json"
        if not meta_path.exists():
            continue
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            entries.append(HistoryEntry.from_dict(data))
            if len(entries) >= limit:
                break
        except Exception:
            continue
    return entries


def get_history_entry(entry_id: str) -> Optional[HistoryEntry]:
    entry_dir = HISTORY_DIR / entry_id
    meta_path = entry_dir / "meta.json"
    if not meta_path.exists():
        return None
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        return HistoryEntry.from_dict(data)
    except Exception:
        return None


def get_history_image_path(entry_id: str, filename: str) -> Path:
    return HISTORY_DIR / entry_id / filename


def delete_history_entry(entry_id: str) -> bool:
    entry_dir = HISTORY_DIR / entry_id
    if not entry_dir.exists():
        return False
    import shutil
    shutil.rmtree(entry_dir)
    return True


def clear_history() -> int:
    history_dir = _ensure_history_dir()
    count = 0
    for entry_dir in list(history_dir.iterdir()):
        if entry_dir.is_dir() and (entry_dir / "meta.json").exists():
            import shutil
            shutil.rmtree(entry_dir)
            count += 1
    return count