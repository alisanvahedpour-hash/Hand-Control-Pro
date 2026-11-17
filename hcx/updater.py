"""بررسی نسخهٔ جدید: یک آدرس JSON مثل {"version": "4.1", "url": "...", "notes": "..."}"""
import json
import re
import urllib.request


def parse_version(v):
    return tuple(int(x) for x in re.findall(r"\d+", str(v))[:4]) or (0,)


def check(url, current, timeout=5):
    """اگر نسخهٔ جدیدتر بود دیکشنری نسخه، وگرنه None؛ خطا پرتاب می‌شود"""
    with urllib.request.urlopen(url, timeout=timeout) as r:
        info = json.loads(r.read().decode("utf-8"))
    return info if parse_version(info.get("version", "0")) > parse_version(current) else None
