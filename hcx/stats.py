"""آمار استفاده و یادآور استراحت"""
import json
import threading
from datetime import date, timedelta
from pathlib import Path


class UsageStats:
    def __init__(self, path=None):
        self.path = Path(path) if path else None
        self.lock = threading.Lock()
        self.days = {}
        self.cont_active = 0.0
        self._idle = 0.0
        self.load()

    def _day(self, key=None):
        k = key or date.today().isoformat()
        return self.days.setdefault(k, {"gestures": {}, "actions": {}, "active_s": 0.0})

    def gesture(self, key):
        with self.lock:
            g = self._day()["gestures"]
            g[key] = g.get(key, 0) + 1

    def action(self, key):
        with self.lock:
            a = self._day()["actions"]
            a[key] = a.get(key, 0) + 1

    def tick(self, active, dt):
        """هر فریم صدا زده می‌شود؛ active یعنی دست دیده می‌شود"""
        dt = min(max(dt, 0.0), 0.5)
        with self.lock:
            if active:
                self._day()["active_s"] += dt
                self.cont_active += dt
                self._idle = 0.0
            else:
                self._idle += dt
                if self._idle > 60:          # یک دقیقه بدون دست = استراحت حساب می‌شود
                    self.cont_active = 0.0

    def break_due(self, minutes):
        with self.lock:
            if minutes and minutes > 0 and self.cont_active >= minutes * 60:
                self.cont_active = 0.0
                return True
        return False

    def top(self, kind, n=8, days=1):
        agg = {}
        with self.lock:
            for i in range(days):
                k = (date.today() - timedelta(days=i)).isoformat()
                for name, c in self.days.get(k, {}).get(kind, {}).items():
                    agg[name] = agg.get(name, 0) + c
        return sorted(agg.items(), key=lambda kv: -kv[1])[:n]

    def minutes_by_day(self, n=7):
        out = []
        with self.lock:
            for i in range(n - 1, -1, -1):
                d = date.today() - timedelta(days=i)
                out.append((d.isoformat(),
                            round(self.days.get(d.isoformat(), {}).get("active_s", 0.0) / 60, 1)))
        return out

    def save(self):
        if not self.path:
            return
        try:
            with self.lock:
                keep = sorted(self.days)[-90:]
                data = {k: self.days[k] for k in keep}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def load(self):
        try:
            if self.path and self.path.exists():
                self.days = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            self.days = {}
