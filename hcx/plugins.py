"""افزونه‌ها: هر فایل .py در پوشهٔ plugins می‌تواند عمل و رویداد اضافه کند.
هشدار: افزونه‌ها کد دلخواه اجرا می‌کنند؛ فقط افزونهٔ مورد اعتماد بگذارید."""
import importlib.util
from pathlib import Path

EXAMPLE = '''# -*- coding: utf-8 -*-
"""افزونهٔ نمونه — این فایل را ویرایش کنید یا کپی بگیرید"""
PLUGIN_NAME = "نمونه"

# (کلید، برچسب، نوع پارامتر: None یا "text")
ACTIONS = [
    ("hello", "چاپ سلام در کنسول", None),
    ("echo", "چاپ متن دلخواه", "text"),
]


def run(action, param):
    if action == "hello":
        print("سلام از افزونه!")
    elif action == "echo":
        print("افزونه:", param)


def on_event(name, data):
    """name مثل 'gesture' و data نام ژست؛ اختیاری"""
    pass
'''


class PluginManager:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.mods, self.errors, self.actions = {}, [], []

    def write_example(self):
        self.folder.mkdir(parents=True, exist_ok=True)
        p = self.folder / "example_plugin.py"
        if not p.exists():
            p.write_text(EXAMPLE, encoding="utf-8")
        return p

    def load(self):
        self.mods, self.errors, self.actions = {}, [], []
        if not self.folder.is_dir():
            return
        for f in sorted(self.folder.glob("*.py")):
            try:
                spec = importlib.util.spec_from_file_location(f"hc_plugin_{f.stem}", f)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                name = getattr(mod, "PLUGIN_NAME", f.stem)
                for a in getattr(mod, "ACTIONS", []):
                    kind = a[2] if len(a) > 2 else None
                    self.actions.append((f"plugin:{f.stem}:{a[0]}", f"{name} › {a[1]}", kind))
                self.mods[f.stem] = mod
            except Exception as e:
                self.errors.append(f"{f.name}: {e}")

    def run(self, key, param=""):
        try:
            _, stem, action = key.split(":", 2)
            self.mods[stem].run(action, param)
        except Exception as e:
            print("افزونه:", e)

    def notify(self, event, data=None):
        for mod in self.mods.values():
            fn = getattr(mod, "on_event", None)
            if fn:
                try:
                    fn(event, data)
                except Exception as e:
                    print("افزونه:", e)
