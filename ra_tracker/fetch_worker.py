import logging
from datetime import date

import requests
from PyQt6.QtCore import QObject, pyqtSignal

from .api import RAClient
from . import cache as cache_mgr

log = logging.getLogger(__name__)


class FetchWorker(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, client: RAClient, username: str):
        super().__init__()
        self.client = client
        self.username = username

    def run(self):
        try:
            cached = cache_mgr.load_achievements(self.username)
            if cached is not None:
                log.info("Using achievement cache for %s", self.username)
                self.finished.emit(cached)
                return

            today = date.today().isoformat()
            data = self.client.get_achievements_between(self.username, "2000-01-01", today)
            data.sort(key=lambda a: (
                a.get("GameTitle", a.get("gameTitle", "")),
                a.get("Date", a.get("date", "")),
            ))
            cache_mgr.save_achievements(self.username, data)
            badge_names = list({
                a.get("BadgeName", a.get("badgeName", ""))
                for a in data if a.get("BadgeName", a.get("badgeName", ""))
            })
            if badge_names:
                RAClient.preload_badges(badge_names)
            self.finished.emit(data)
        except requests.RequestException as e:
            self.error.emit(f"Could not connect to RetroAchievements API.\n\n{e}")
        except Exception as e:
            self.error.emit(f"Failed to fetch achievements:\n{e}")
