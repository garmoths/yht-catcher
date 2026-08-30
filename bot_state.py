import json
import os
import tempfile
import time


class BotState:
    """Bildirim ve hata durumunu küçük, taşınabilir bir JSON dosyasında tutar."""

    def __init__(self, path):
        self.path = path
        self.data = {"notifications": {}, "error_streak": 0, "error_alerted": False}
        self._load()

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as state_file:
                loaded = json.load(state_file)
            if isinstance(loaded, dict):
                self.data.update(loaded)
        except (OSError, ValueError, TypeError):
            pass

    def save(self):
        directory = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(directory, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(prefix=".bot-state-", dir=directory, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as state_file:
                json.dump(self.data, state_file, ensure_ascii=False, indent=2)
            os.replace(temp_path, self.path)
        except Exception:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    def can_notify(self, key, cooldown_seconds, now=None):
        now = time.time() if now is None else now
        last_sent = float(self.data["notifications"].get(key, 0))
        return now - last_sent >= cooldown_seconds

    def mark_notified(self, key, now=None):
        self.data["notifications"][key] = time.time() if now is None else now
        self.save()

    def record_error(self):
        self.data["error_streak"] = int(self.data.get("error_streak", 0)) + 1
        self.save()
        return self.data["error_streak"]

    def mark_error_alerted(self):
        self.data["error_alerted"] = True
        self.save()

    def record_success(self):
        recovered = bool(self.data.get("error_alerted"))
        self.data["error_streak"] = 0
        self.data["error_alerted"] = False
        self.save()
        return recovered

    @property
    def error_alerted(self):
        return bool(self.data.get("error_alerted"))
