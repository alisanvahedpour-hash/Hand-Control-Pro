"""ضبط ماکرو (ماوس و صفحه‌کلید) و تبدیل آن به مرحله‌های یک «عمل»"""
import threading
import time

MOD_ORDER = ["ctrl", "alt", "shift", "win"]
_KEYMAP = {"ctrl_l": "ctrl", "ctrl_r": "ctrl", "alt_l": "alt", "alt_r": "alt",
           "alt_gr": "alt", "shift_l": "shift", "shift_r": "shift", "shift": "shift",
           "cmd": "win", "cmd_l": "win", "cmd_r": "win", "caps_lock": "capslock",
           "page_up": "pageup", "page_down": "pagedown"}


def normalize_key(key):
    """نام کلید pynput (یا شبیه آن) ← نام ساده؛ حروف و نمادها همان می‌مانند"""
    ch = getattr(key, "char", None)
    if ch:
        return ch
    name = getattr(key, "name", None) or str(key)
    return _KEYMAP.get(name, name)


def events_to_steps(events, min_wait=0.35):
    """events: لیست دیکشنری‌ها
       {"t":..,"kind":"click","x":..,"y":..,"button":"left"}  یا
       {"t":..,"kind":"key","name":"a","down":True}"""
    steps, text, mods, last_t = [], "", set(), None

    def flush():
        nonlocal text
        if text:
            steps.append({"type": "type_text", "param": text})
            text = ""

    for e in events:
        if last_t is not None and e["t"] - last_t >= min_wait:
            flush()
            ms = int(round((e["t"] - last_t) * 1000 / 50.0) * 50)
            steps.append({"type": "wait", "param": str(ms)})
        last_t = e["t"]
        if e["kind"] == "click":
            flush()
            steps.append({"type": "click_at",
                          "param": f"{int(e['x'])},{int(e['y'])},{e.get('button', 'left')}"})
            continue
        name = e["name"]
        if name in MOD_ORDER:
            mods.add(name) if e["down"] else mods.discard(name)
            continue
        if not e["down"]:
            continue
        if mods - {"shift"}:
            flush()
            combo = [m for m in MOD_ORDER if m in mods] + [name.lower()]
            steps.append({"type": "hotkey", "param": "+".join(combo)})
        elif len(name) == 1:
            text += name.upper() if ("shift" in mods and name.isalpha()) else name
        elif name == "space":
            text += " "
        else:
            flush()
            steps.append({"type": "key", "param": name})
    flush()
    return steps


class MacroRecorder:
    """ضبط با pynput (ویندوز و X11)؛ stop() فهرست رویدادها را برمی‌گرداند"""

    def __init__(self):
        self.events = []
        self._ml = None
        self._kl = None
        self._lock = threading.Lock()

    def start(self):
        from pynput import keyboard, mouse
        t0 = time.time()

        def on_click(x, y, button, pressed):
            if pressed:
                with self._lock:
                    self.events.append({"t": time.time() - t0, "kind": "click",
                                        "x": x, "y": y,
                                        "button": getattr(button, "name", "left")})

        def on_key(down):
            def inner(key):
                with self._lock:
                    self.events.append({"t": time.time() - t0, "kind": "key",
                                        "name": normalize_key(key), "down": down})
            return inner

        self._ml = mouse.Listener(on_click=on_click)
        self._kl = keyboard.Listener(on_press=on_key(True), on_release=on_key(False))
        self._ml.start()
        self._kl.start()

    def stop(self):
        for lst in (self._ml, self._kl):
            if lst is not None:
                lst.stop()
        with self._lock:
            return list(self.events)
