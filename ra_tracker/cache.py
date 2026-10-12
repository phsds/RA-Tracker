"""On-disk cache for achievements, badges and game metadata.

Files live under ``~/.ra_tracker/cache/`` so the app can satisfy repeat
requests without hitting the RetroAchievements API. Each save/load pair is
defensive: IO errors are logged and swallowed rather than crashing the UI.
"""

import json
import os
import logging
from pathlib import Path
from io import BytesIO
from PIL import Image

log = logging.getLogger(__name__)

# Root folder where every cached object is stored.
CACHE_DIR = Path.home() / ".ra_tracker" / "cache"


def _ensure_dir():
    """Create the cache directory (and any parents) if it does not exist yet."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _achievements_path(username: str) -> Path:
    """Path of the JSON file holding one user's achievements."""
    return CACHE_DIR / f"achievements_{username}.json"


def _badge_path(badge_name: str) -> Path:
    """Path of the PNG file holding one achievement badge."""
    return CACHE_DIR / f"badge_{badge_name}.png"


def _game_path(game_id: int) -> Path:
    """Path of the JSON file holding one game's extended metadata."""
    return CACHE_DIR / f"game_{game_id}.json"


def save_achievements(username: str, data: list[dict]):
    """Persist ``data`` (list of earned achievements) for ``username``."""
    _ensure_dir()
    path = _achievements_path(username)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        log.info("Cache de conquistas salvo (%d registros)", len(data))
    except Exception as e:
        log.warning("Erro ao salvar cache de conquistas: %s", e)


def load_achievements(username: str) -> list[dict] | None:
    """Return cached achievements for ``username`` or ``None`` if not cached."""
    path = _achievements_path(username)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        log.info("Cache de conquistas carregado (%d registros)", len(data))
        return data
    except Exception as e:
        log.warning("Erro ao ler cache de conquistas: %s", e)
        return None


def save_badge(badge_name: str, img: Image.Image):
    """Persist a badge image as a PNG file on disk."""
    _ensure_dir()
    path = _badge_path(badge_name)
    try:
        img.save(path, format="PNG")
    except Exception as e:
        log.warning("Erro ao salvar badge em cache: %s", e)


def load_badge(badge_name: str) -> Image.Image | None:
    """Load a cached badge image, or ``None`` if missing/corrupt."""
    path = _badge_path(badge_name)
    if not path.exists():
        return None
    try:
        return Image.open(path).convert("RGBA")
    except Exception:
        return None


def save_game_data(game_id: int, data: dict):
    """Persist a game's extended metadata as JSON."""
    _ensure_dir()
    path = _game_path(game_id)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        log.warning("Erro ao salvar cache do jogo %d: %s", game_id, e)


def load_game_data(game_id: int) -> dict | None:
    """Return cached game metadata for ``game_id`` or ``None`` if not cached."""
    path = _game_path(game_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def clear_cache():
    """Delete every file inside the cache directory.

    Returns the number of removed files so the UI can report the result.
    """
    if not CACHE_DIR.exists():
        return
    count = 0
    for f in CACHE_DIR.iterdir():
        if f.is_file():
            try:
                f.unlink()
                count += 1
            except Exception as e:
                log.warning("Erro ao remover %s: %s", f.name, e)
    if count:
        log.info("Cache limpo: %d arquivo(s) removido(s)", count)
    return count
