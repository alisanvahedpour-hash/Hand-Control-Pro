"""اتصال به سرویس‌ها: Home Assistant، MQTT، Hue، OBS و صدای راهنما (TTS).
همه در نخ جدا اجرا می‌شوند تا تشخیص دست متوقف نشود. کلیدهای تنظیمات با set_config داده می‌شوند."""
import json
import platform
import re
import shutil
import subprocess
import threading
import urllib.request

CFG = {}
KEYS = ("ha_url", "ha_token", "mqtt_host", "mqtt_port", "mqtt_user", "mqtt_pass",
        "hue_bridge", "hue_user", "obs_host", "obs_port", "obs_pass")


def set_config(settings):
    CFG.clear()
    for k in KEYS:
        CFG[k] = settings.get(k, "")


def _thread(fn, *a):
    t = threading.Thread(target=fn, args=a, daemon=True)
    t.start()
    return t


def http_json(method, url, body=None, headers=None, timeout=5):
    """درخواست وب؛ پاسخ JSON (یا متن) برمی‌گرداند و خطا را پرتاب می‌کند"""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8", "replace")
    try:
        return json.loads(raw)
    except ValueError:
        return raw


# ---------------- Home Assistant ----------------
def parse_ha(spec):
    """'light.turn_on light.salon {"brightness": 120}' ← (دامنه، سرویس، بدنه)"""
    parts = spec.strip().split(None, 2)
    if not parts or "." not in parts[0]:
        raise ValueError("قالب: دامنه.سرویس [entity_id] [JSON]")
    domain, service = parts[0].split(".", 1)
    body = {}
    rest = parts[1:]
    if rest and not rest[0].startswith("{"):
        body["entity_id"] = rest[0]
        rest = rest[1:]
    if rest:
        body.update(json.loads(" ".join(rest)))
    return domain, service, body


def ha_call(spec):
    def work():
        try:
            domain, service, body = parse_ha(spec)
            url = CFG.get("ha_url", "").rstrip("/") + f"/api/services/{domain}/{service}"
            http_json("POST", url, body,
                      {"Authorization": "Bearer " + CFG.get("ha_token", "")})
        except Exception as e:
            print("Home Assistant:", e)
    return _thread(work)


# ---------------- Philips Hue (پل محلی) ----------------
def hue_state(spec, current_on=None):
    """'3 on' | '3 off' | '3 toggle' | '3 bri:200' ← (شناسهٔ چراغ، بدنهٔ وضعیت)"""
    parts = spec.split()
    if len(parts) < 2:
        raise ValueError("قالب: شمارهٔ-چراغ on|off|toggle|bri:0-254")
    lid, cmd = parts[0], parts[1].lower()
    if cmd == "on":
        return lid, {"on": True}
    if cmd == "off":
        return lid, {"on": False}
    if cmd == "toggle":
        return lid, {"on": not bool(current_on)}
    m = re.fullmatch(r"bri:(\d+)", cmd)
    if m:
        return lid, {"on": True, "bri": max(0, min(254, int(m.group(1))))}
    raise ValueError("دستور Hue نامعتبر")


def hue_light(spec):
    def work():
        try:
            base = f"http://{CFG.get('hue_bridge', '')}/api/{CFG.get('hue_user', '')}/lights/"
            cur = None
            if spec.split()[1:2] == ["toggle"]:
                cur = http_json("GET", base + spec.split()[0])["state"]["on"]
            lid, body = hue_state(spec, cur)
            http_json("PUT", base + lid + "/state", body)
        except Exception as e:
            print("Hue:", e)
    return _thread(work)


# ---------------- MQTT (paho-mqtt اختیاری) ----------------
def mqtt_publish(spec):
    def work():
        try:
            import paho.mqtt.publish as pub
            topic, _, payload = [x.strip() for x in spec.partition("|")]
            auth = None
            if CFG.get("mqtt_user"):
                auth = {"username": CFG["mqtt_user"], "password": CFG.get("mqtt_pass", "")}
            pub.single(topic, payload or "1", hostname=CFG.get("mqtt_host", "localhost"),
                       port=int(CFG.get("mqtt_port") or 1883), auth=auth)
        except ImportError:
            print("MQTT: بسته paho-mqtt نصب نیست (pip install paho-mqtt)")
        except Exception as e:
            print("MQTT:", e)
    return _thread(work)


# ---------------- OBS (obsws-python اختیاری) ----------------
def snake(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def obs_request(spec):
    """'ToggleRecord' | 'StartRecord' | 'SetCurrentProgramScene صحنه۱'"""
    def work():
        try:
            import obsws_python as obs
            cmd, _, arg = spec.strip().partition(" ")
            cl = obs.ReqClient(host=CFG.get("obs_host") or "localhost",
                               port=int(CFG.get("obs_port") or 4455),
                               password=CFG.get("obs_pass", ""), timeout=3)
            fn = getattr(cl, snake(cmd))
            fn(arg.strip()) if arg.strip() else fn()
        except ImportError:
            print("OBS: بسته obsws-python نصب نیست (pip install obsws-python)")
        except Exception as e:
            print("OBS:", e)
    return _thread(work)


# ---------------- صدای راهنما (TTS) ----------------
def speak(text):
    if not text:
        return

    def work():
        try:
            sysname = platform.system()
            if sysname == "Windows":
                safe = text.replace("'", "''")
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "Add-Type -AssemblyName System.Speech; "
                     f"(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{safe}')"],
                    timeout=10, creationflags=0x08000000)
            elif sysname == "Darwin":
                subprocess.run(["say", text], timeout=10)
            else:
                for cmd in (["espeak-ng", text], ["spd-say", text], ["espeak", text]):
                    if shutil.which(cmd[0]):
                        subprocess.run(cmd, timeout=10)
                        break
        except Exception:
            pass
    return _thread(work)
