"""Client for the RetroAchievements web API.

Wraps the documented REST endpoints (see https://retroachievements.org/API)
and provides helpers to load badges/box-art images, backed by an in-memory
cache and the on-disk cache in :mod:`ra_tracker.cache`.
"""

import logging
import concurrent.futures
import requests
from datetime import datetime
from typing import Any
from io import BytesIO
from PIL import Image

from . import cache as cache_mgr

log = logging.getLogger(__name__)

# Public RetroAchievements endpoints.
BASE_URL = "https://retroachievements.org/API"
BADGE_URL = "https://retroachievements.org/Badge"
COVER_URL = "https://retroachievements.org"


class RAClient:
    """Minimal wrapper around the RetroAchievements HTTP API.

    Every request sends the API key in the ``y`` query parameter. Instances
    share a ``requests.Session`` to reuse the underlying TCP connection.
    """

    # Shared process-wide badge cache so already-downloaded images are not
    # re-fetched or re-decoded across widgets.
    _badge_cache: dict[str, Image.Image] = {}

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._session = requests.Session()

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> list | dict:
        """Perform a GET request to the given API endpoint.

        The API key is injected as the ``y`` parameter automatically. The key
        is stripped from log output on purpose to avoid leaking credentials
        into the logs.
        """
        params = params or {}
        params["y"] = self.api_key
        url = f"{BASE_URL}/{endpoint}"
        log.info("GET %s params=%s", endpoint, {k: v for k, v in params.items() if k != "y"})
        resp = self._session.get(url, params=params, timeout=30)
        log.info("Resposta HTTP %s %s: %s", endpoint, resp.status_code, resp.reason)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            log.info("Retornou %d conquistas", len(data))
        else:
            # Truncate dict payloads so a huge game response does not flood the log.
            log.info("Resposta (dict): %s", str(data)[:200])
        return data

    # -- User data endpoints -------------------------------------------------

    def get_user_summary(self, username: str) -> dict:
        """Return the profile summary for ``username`` (used to validate the login)."""
        log.info("get_user_summary: username=%s", username)
        return self._get("API_GetUserSummary.php", {"u": username})

    def get_recent_achievements(self, username: str, minutes: int = 60) -> list[dict]:
        """Return achievements earned by ``username`` within the last ``minutes``."""
        log.info("get_recent_achievements: username=%s minutes=%d", username, minutes)
        return self._get("API_GetUserRecentAchievements.php", {"u": username, "m": minutes})

    def get_achievements_on_day(self, username: str, date: str) -> list[dict]:
        """Return achievements earned by ``username`` on a single ``YYYY-MM-DD`` date."""
        log.info("get_achievements_on_day: username=%s date=%s", username, date)
        return self._get("API_GetAchievementsEarnedOnDay.php", {"u": username, "d": date})

    def get_achievements_between(self, username: str, start: str, end: str) -> list[dict]:
        """Return achievements earned by ``username`` between two ``YYYY-MM-DD`` dates.

        The API expects Unix timestamps for the ``f``/``t`` parameters, so the
        ISO dates are converted before sending the request.
        """
        log.info("get_achievements_between: username=%s start=%s end=%s", username, start, end)
        from datetime import datetime
        f_ts = int(datetime.strptime(start, "%Y-%m-%d").timestamp())
        t_ts = int(datetime.strptime(end, "%Y-%m-%d").timestamp())
        return self._get(
            "API_GetAchievementsEarnedBetween.php",
            {"u": username, "f": f_ts, "t": t_ts},
        )

    # -- Game data endpoints -------------------------------------------------

    def get_game_extended(self, game_id: int) -> dict:
        """Return extended metadata (publisher, developer, achievements...) for a game."""
        log.info("get_game_extended: game_id=%d", game_id)
        return self._get("API_GetGameExtended.php", {"i": game_id})

    # -- Image helpers -------------------------------------------------------

    @staticmethod
    def load_image(image_path: str) -> Image.Image | None:
        """Fetch a game cover from the site, converting it to RGBA.

        Returns ``None`` on any network/decoding failure so callers can hide
        the image instead of crashing.
        """
        if not image_path:
            return None
        url = f"{COVER_URL}{image_path}"
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            return Image.open(BytesIO(resp.content)).convert("RGBA")
        except Exception:
            return None

    @staticmethod
    def badge_url(badge_name: str) -> str:
        """Return the full URL pointing to an achievement badge PNG."""
        url = f"{BADGE_URL}/{badge_name}.png"
        log.debug("badge_url: %s", url)
        return url

    @staticmethod
    def load_badge(badge_name: str) -> Image.Image | None:
        """Load a badge by name with a three-tier lookup: memory, disk, network.

        On a network hit the image is stored both in memory (for this process)
        and on disk (for future runs).
        """
        if not badge_name:
            return None
        # 1) Already fetched during this session?
        if badge_name in RAClient._badge_cache:
            return RAClient._badge_cache[badge_name]
        # 2) Cached on disk from a previous session?
        cached = cache_mgr.load_badge(badge_name)
        if cached is not None:
            RAClient._badge_cache[badge_name] = cached
            return cached
        # 3) Download from the site and persist it.
        url = RAClient.badge_url(badge_name)
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            img = Image.open(BytesIO(resp.content)).convert("RGBA")
            RAClient._badge_cache[badge_name] = img
            cache_mgr.save_badge(badge_name, img)
            return img
        except Exception:
            return None

    @staticmethod
    def preload_badges(badge_names: list[str]):
        """Download all badges that are not yet cached, in parallel.

        Fetches happen on worker threads (12 at a time) so scrolling through
        the achievement list stays smooth instead of blocking on each badge.
        """
        missing = [b for b in badge_names if b and b not in RAClient._badge_cache]
        if not missing:
            return
        log.info("Pré-carregando %d badges em paralelo...", len(missing))
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
            list(ex.map(RAClient.load_badge, missing))
        log.info("Pré-carregamento concluído.")

    @staticmethod
    def parse_date(date_str: str) -> datetime:
        """Parse an achievement timestamp into a :class:`datetime`."""
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
