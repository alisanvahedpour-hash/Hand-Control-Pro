"""کنترل از گوشی: یک صفحهٔ وب کوچک روی شبکهٔ محلی با PIN"""
import json
import re
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

SAFE_ACTIONS = ["media_play_pause", "media_next", "media_prev", "volume_up",
                "volume_down", "volume_mute", "ppt_next", "ppt_prev", "ppt_start",
                "ppt_start_current", "ppt_end", "ppt_black", "show_desktop",
                "alt_tab", "left_click", "right_click"]
CMD_RE = re.compile(r"^(toggle_exec|exec_on|exec_off|camera_on|camera_off|stop|"
                    r"profile:[A-Za-z0-9_:]+|action:[a-z_0-9]+)$")

PAGE = """<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hand Control Pro</title><style>
body{margin:0;background:#0e1118;color:#e8ebf4;font-family:system-ui,Tahoma,sans-serif}
h1{font-size:18px;padding:14px;margin:0;background:#1b2132}
#st{padding:8px 14px;color:#8d96ad;font-size:13px}
.g{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;padding:12px}
button{padding:16px 8px;font-size:15px;border:0;border-radius:12px;background:#26304f;color:#e8ebf4}
button:active{background:#6d8bff;color:#0b0f1a}.d{background:#4a1f2a}</style></head><body>
<h1>🖐️ Hand Control Pro</h1><div id="st">...</div><div class="g">__BUTTONS__</div>
<script>
const pin=new URLSearchParams(location.search).get('pin')||'';
async function c(cmd){try{const r=await fetch('/api/cmd',{method:'POST',body:JSON.stringify({cmd:cmd,pin:pin})});
document.getElementById('st').textContent=r.ok?'✓ '+cmd:'✗ خطا ('+r.status+')'}catch(e){document.getElementById('st').textContent='✗ ارتباط قطع است'}}
async function s(){try{const r=await fetch('/api/status?pin='+pin);const j=await r.json();
document.getElementById('st').textContent='دوربین: '+(j.camera?'روشن':'خاموش')+' · دستورها: '+(j.exec?'فعال':'متوقف')+' · پروفایل: '+j.profile}catch(e){}}
setInterval(s,3000);s();
</script></body></html>"""

BUTTONS = [("⏯ پخش/توقف", "action:media_play_pause"), ("🔇 بی‌صدا", "action:volume_mute"),
           ("🔉 صدا -", "action:volume_down"), ("🔊 صدا +", "action:volume_up"),
           ("⏮ قبلی", "action:media_prev"), ("⏭ بعدی", "action:media_next"),
           ("◀ اسلاید قبل", "action:ppt_prev"), ("اسلاید بعد ▶", "action:ppt_next"),
           ("▶ شروع نمایش", "action:ppt_start"), ("⏹ پایان نمایش", "action:ppt_end"),
           ("⬛ صفحهٔ سیاه", "action:ppt_black"), ("🖥 دسکتاپ", "action:show_desktop"),
           ("⏸ مکث/ادامه", "toggle_exec"), ("🛑 توقف اضطراری", "stop")]


def new_pin():
    return "".join(secrets.choice("0123456789") for _ in range(6))


def render_page():
    btns = "".join(
        f'<button class="{"d" if c == "stop" else ""}" onclick="c(\'{c}\')">{t}</button>'
        for t, c in BUTTONS)
    return PAGE.replace("__BUTTONS__", btns)


class RemoteServer:
    """on_command(cmd)->bool ؛ get_status()->dict  (در نخ سرور صدا زده می‌شوند)"""

    def __init__(self, host, port, pin, on_command, get_status):
        self.host, self.port, self.pin = host, int(port), str(pin)
        self.on_command, self.get_status = on_command, get_status
        self.httpd = None
        self.thread = None
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code, body, ctype="application/json"):
                data = body.encode("utf-8") if isinstance(body, str) else body
                self.send_response(code)
                self.send_header("Content-Type", ctype + "; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _pin_ok(self, pin):
                return secrets.compare_digest(str(pin or ""), outer.pin)

            def do_GET(self):
                u = urlparse(self.path)
                q = parse_qs(u.query)
                if u.path == "/":
                    if not self._pin_ok((q.get("pin") or [""])[0]):
                        return self._send(403, "<h3 dir=rtl>PIN را در آدرس بنویسید: ?pin=123456</h3>",
                                          "text/html")
                    return self._send(200, render_page(), "text/html")
                if u.path == "/api/status":
                    if not self._pin_ok((q.get("pin") or [""])[0]):
                        return self._send(403, '{"error":"pin"}')
                    return self._send(200, json.dumps(outer.get_status(), ensure_ascii=False))
                self._send(404, '{"error":"not found"}')

            def do_POST(self):
                if self.path != "/api/cmd":
                    return self._send(404, '{"error":"not found"}')
                try:
                    n = min(int(self.headers.get("Content-Length", 0)), 2000)
                    j = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
                except Exception:
                    return self._send(400, '{"error":"bad json"}')
                if not self._pin_ok(j.get("pin")):
                    return self._send(403, '{"error":"pin"}')
                cmd = str(j.get("cmd", ""))
                if not CMD_RE.match(cmd):
                    return self._send(400, '{"error":"cmd"}')
                if cmd.startswith("action:") and cmd[7:] not in SAFE_ACTIONS:
                    return self._send(400, '{"error":"action not allowed"}')
                ok = bool(outer.on_command(cmd))
                self._send(200 if ok else 400, json.dumps({"ok": ok}))

        self._handler = H

    def start(self):
        self.httpd = ThreadingHTTPServer((self.host, self.port), self._handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
