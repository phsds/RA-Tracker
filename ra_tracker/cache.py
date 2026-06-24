import json
import os
import logging
from pathlib import Path
from io import BytesIO
from PIL import Image

log = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"


def _ensure_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _achievements_path(username: str) -> Path:
    return CACHE_DIR / f"achievements_{username}.json"


def _badge_path(badge_name: str) -> Path:
    return CACHE_DIR / f"badge_{badge_name}.png"


def _game_path(game_id: int) -> Path:
    return CACHE_DIR / f"game_{game_id}.json"


def save_achievements(username: str, data: list[dict]):
    _ensure_dir()
    path = _achievements_path(username)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        log.info("Cache de conquistas salvo (%d registros)", len(data))
    except Exception as e:
        log.warning("Erro ao salvar cache de conquistas: %s", e)


def load_achievements(username: str) -> list[dict] | None:
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
    _ensure_dir()
    path = _badge_path(badge_name)
    try:
        img.save(path, format="PNG")
    except Exception as e:
        log.warning("Erro ao salvar badge em cache: %s", e)


def load_badge(badge_name: str) -> Image.Image | None:
    path = _badge_path(badge_name)
    if not path.exists():
        return None
    try:
        return Image.open(path).convert("RGBA")
    except Exception:
        return None


def save_game_data(game_id: int, data: dict):
    _ensure_dir()
    path = _game_path(game_id)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception as e:
        log.warning("Erro ao salvar cache do jogo %d: %s", game_id, e)


def load_game_data(game_id: int) -> dict | None:
    path = _game_path(game_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def clear_cache():
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
