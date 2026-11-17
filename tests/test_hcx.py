"""تست ماژول‌های hcx (منطق خالص)"""
import http.server
import json
import socketserver
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path

import numpy as np

from tests import stubs

stubs.load_app()          # PyQt6 جایگزین را برای hcx.overlay آماده می‌کند
from hcx import (headtrack, i18n, integrations, learn, macro, overlay, plugins, remote,  # noqa: E402
                 stats, updater, voice)


def rot(v, deg):
    return learn._rot(v, deg)


def pose_vec(T, noise=0.0, seed=0):
    p = (T - T[0]) / (np.linalg.norm(T[0] - T[9]) + 1e-9)
    v = p[1:].flatten()
    return v + np.random.default_rng(seed).normal(0, noise, v.shape)


class TestLearn(unittest.TestCase):
    def setUp(self):
        self.P = {k: stubs.TM[k] for k in ("palm", "fist", "point")}
        samples = {k: [pose_vec(T, 0.008, i) for i in range(14)] for k, T in self.P.items()}
        self.model = learn.PoseModel().fit(samples)

    def test_classifies_each_pose(self):
        for k, T in self.P.items():
            lab, r = self.model.predict(pose_vec(T, 0.01, 99))
            self.assertEqual(lab, k)
            self.assertLess(r, 1.0)

    def test_rejects_unknown_pose(self):
        weird = np.random.default_rng(1).normal(0, 0.8, 40)
        self.assertIsNone(self.model.predict(weird)[0])

    def test_tolerates_small_rotation(self):
        v = rot(pose_vec(self.P["fist"], 0.005, 5), 8)
        self.assertEqual(self.model.predict(v)[0], "fist")

    def test_threshold_bounds(self):
        V = np.array([pose_vec(self.P["palm"], 0.02, i) for i in range(10)])
        t = learn.PoseModel.threshold(V)
        self.assertTrue(0.12 <= t <= 0.35)
        self.assertEqual(learn.PoseModel.threshold(V[:2]), 0.25)


class TestHead(unittest.TestCase):
    def test_ear_open_vs_closed(self):
        op = headtrack.ear([(0, 0), (0.3, -0.6), (0.7, -0.6), (1, 0), (0.7, 0.6), (0.3, 0.6)])
        cl = headtrack.ear([(0, 0), (0.3, -0.05), (0.7, -0.05), (1, 0), (0.7, 0.05), (0.3, 0.05)])
        self.assertGreater(op, 0.5)
        self.assertLess(cl, 0.19)

    def test_cursor_follows_nose(self):
        h = headtrack.HeadTracker(gain=2.0)
        (u0, v0), _ = h.update(0.0, (500, 300), 200, 0.4, 0.4)
        (u1, v1), _ = h.update(0.1, (540, 300), 200, 0.4, 0.4)
        self.assertAlmostEqual(u0, 0.5, places=2)
        self.assertGreater(u1, u0)
        self.assertAlmostEqual(v1, 0.5, places=2)
        h.recenter()
        (u2, _), _ = h.update(0.2, (540, 300), 200, 0.4, 0.4)
        self.assertAlmostEqual(u2, 0.5, places=2)

    def _blink(self, left, right, dur):
        h = headtrack.HeadTracker()
        h.update(0, (0, 0), 100, 0.4, 0.4)
        h.update(0.1, (0, 0), 100, left, right)
        _, ev = h.update(0.1 + dur, (0, 0), 100, 0.4, 0.4)
        return ev

    def test_long_blink_clicks_short_does_not(self):
        self.assertEqual(self._blink(0.05, 0.05, 0.7), ["click"])
        self.assertEqual(self._blink(0.05, 0.05, 0.15), [])
        self.assertEqual(self._blink(0.05, 0.05, 3.0), [])        # بستن طولانی = نادیده

    def test_winks(self):
        self.assertEqual(self._blink(0.05, 0.4, 0.7), ["right_click"])
        self.assertEqual(self._blink(0.4, 0.05, 0.7), ["double_click"])


class TestStats(unittest.TestCase):
    def test_counts_and_break(self):
        s = stats.UsageStats()
        for _ in range(3):
            s.gesture("palm")
        s.gesture("fist"); s.action("copy")
        self.assertEqual(s.top("gestures")[0], ("palm", 3))
        self.assertEqual(s.top("actions"), [("copy", 1)])
        for _ in range(130):
            s.tick(True, 0.5)
        self.assertTrue(s.break_due(1))
        self.assertFalse(s.break_due(1))                  # بعد از اعلام صفر می‌شود
        self.assertFalse(s.break_due(0))
        self.assertGreater(s.minutes_by_day(7)[-1][1], 1.0)

    def test_idle_resets_continuous(self):
        s = stats.UsageStats()
        s.tick(True, 0.5); s.cont_active = 600
        for _ in range(130):
            s.tick(False, 0.5)
        self.assertEqual(s.cont_active, 0.0)

    def test_save_load(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"
            s = stats.UsageStats(p); s.gesture("palm"); s.save()
            self.assertEqual(stats.UsageStats(p).top("gestures"), [("palm", 1)])
            p.write_text("not json")
            self.assertEqual(stats.UsageStats(p).days, {})


class FakeKey:
    def __init__(self, char=None, name=None): self.char, self.name = char, name


class TestMacro(unittest.TestCase):
    def ev(self, t, name, down=True): return {"t": t, "kind": "key", "name": name, "down": down}

    def test_typing_collapses_to_text(self):
        evs = []
        for i, ch in enumerate("Hi there"):
            evs += [self.ev(i * 0.05, "space" if ch == " " else ch.lower()),
                    self.ev(i * 0.05 + 0.02, "space" if ch == " " else ch.lower(), False)]
        evs.insert(0, self.ev(-0.01, "shift")); evs.insert(2, self.ev(0.04, "shift", False))
        steps = macro.events_to_steps(evs)
        self.assertEqual(steps, [{"type": "type_text", "param": "Hi there"}])

    def test_hotkey_click_wait_special(self):
        evs = [self.ev(0, "ctrl"), self.ev(0.05, "c"), self.ev(0.1, "c", False), self.ev(0.12, "ctrl", False),
               {"t": 1.0, "kind": "click", "x": 10, "y": 20, "button": "left"},
               self.ev(1.1, "enter"), self.ev(1.15, "enter", False)]
        steps = macro.events_to_steps(evs)
        self.assertEqual([s["type"] for s in steps], ["hotkey", "wait", "click_at", "key"])
        self.assertEqual(steps[0]["param"], "ctrl+c")
        self.assertEqual(steps[2]["param"], "10,20,left")
        self.assertEqual(steps[3]["param"], "enter")
        self.assertEqual(int(steps[1]["param"]) % 50, 0)

    def test_modifier_order_and_normalize(self):
        evs = [self.ev(0, "win"), self.ev(0.01, "shift"), self.ev(0.02, "ctrl"), self.ev(0.03, "s")]
        self.assertEqual(macro.events_to_steps(evs)[0]["param"], "ctrl+shift+win+s")
        self.assertEqual(macro.normalize_key(FakeKey(char="a")), "a")
        self.assertEqual(macro.normalize_key(FakeKey(name="ctrl_l")), "ctrl")
        self.assertEqual(macro.normalize_key(FakeKey(name="cmd")), "win")
        self.assertEqual(macro.normalize_key(FakeKey(name="page_down")), "pagedown")


class _Srv:
    def __init__(self, handler):
        self.httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown(); self.httpd.server_close()


class TestIntegrations(unittest.TestCase):
    def test_parse_ha(self):
        self.assertEqual(integrations.parse_ha("light.turn_on light.salon"),
                         ("light", "turn_on", {"entity_id": "light.salon"}))
        d, s, b = integrations.parse_ha('light.turn_on light.salon {"brightness": 120}')
        self.assertEqual(b, {"entity_id": "light.salon", "brightness": 120})
        self.assertEqual(integrations.parse_ha('script.go {"a": 1}')[2], {"a": 1})
        with self.assertRaises(ValueError):
            integrations.parse_ha("bad")

    def test_hue_state(self):
        self.assertEqual(integrations.hue_state("3 on"), ("3", {"on": True}))
        self.assertEqual(integrations.hue_state("3 toggle", True), ("3", {"on": False}))
        self.assertEqual(integrations.hue_state("2 bri:999")[1]["bri"], 254)
        with self.assertRaises(ValueError):
            integrations.hue_state("3 explode")

    def test_snake(self):
        self.assertEqual(integrations.snake("ToggleRecord"), "toggle_record")
        self.assertEqual(integrations.snake("SetCurrentProgramScene"), "set_current_program_scene")

    def test_ha_and_hue_requests(self):
        got = []

        class H(http.server.BaseHTTPRequestHandler):
            def _r(self, body=b"{}"):
                self.send_response(200); self.end_headers(); self.wfile.write(body)

            def do_POST(self):
                n = int(self.headers.get("Content-Length", 0))
                got.append(("POST", self.path, self.rfile.read(n).decode(), self.headers.get("Authorization")))
                self._r()

            def do_PUT(self):
                n = int(self.headers.get("Content-Length", 0))
                got.append(("PUT", self.path, self.rfile.read(n).decode()))
                self._r()

            def do_GET(self):
                got.append(("GET", self.path)); self._r(b'{"state": {"on": true}}')

            def log_message(self, *a): pass

        srv = _Srv(H)
        try:
            integrations.set_config({"ha_url": f"http://127.0.0.1:{srv.port}", "ha_token": "TOK",
                                     "hue_bridge": f"127.0.0.1:{srv.port}", "hue_user": "USR"})
            integrations.ha_call("light.turn_on light.salon").join(3)
            integrations.hue_light("7 toggle").join(3)
        finally:
            srv.close()
        self.assertEqual(got[0][:2], ("POST", "/api/services/light/turn_on"))
        self.assertEqual(json.loads(got[0][2]), {"entity_id": "light.salon"})
        self.assertEqual(got[0][3], "Bearer TOK")
        self.assertEqual(got[1], ("GET", "/api/USR/lights/7"))
        self.assertEqual(got[2][:2], ("PUT", "/api/USR/lights/7/state"))
        self.assertEqual(json.loads(got[2][2]), {"on": False})   # روشن بود ← خاموش

    def test_optional_libs_fail_gracefully(self):
        integrations.set_config({})
        integrations.mqtt_publish("t | x").join(3)
        integrations.obs_request("ToggleRecord").join(3)
        integrations.ha_call("bad").join(3)          # خطا چاپ می‌شود، پرتاب نمی‌شود


class TestRemote(unittest.TestCase):
    def setUp(self):
        self.cmds = []
        self.srv = remote.RemoteServer("127.0.0.1", 0, "123456",
                                       lambda c: (self.cmds.append(c), True)[1],
                                       lambda: {"camera": True, "exec": True, "profile": "x"})
        self.srv.start()
        self.base = f"http://127.0.0.1:{self.srv.port}"

    def tearDown(self):
        self.srv.stop()

    def get(self, path):
        try:
            with urllib.request.urlopen(self.base + path, timeout=3) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()

    def post(self, body):
        req = urllib.request.Request(self.base + "/api/cmd", data=json.dumps(body).encode(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=3) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code

    def test_pin_protection(self):
        self.assertEqual(self.get("/")[0], 403)
        self.assertEqual(self.get("/?pin=000000")[0], 403)
        code, html = self.get("/?pin=123456")
        self.assertEqual(code, 200)
        self.assertIn("اسلاید بعد", html)
        self.assertEqual(self.get("/api/status?pin=bad")[0], 403)
        self.assertEqual(json.loads(self.get("/api/status?pin=123456")[1])["camera"], True)

    def test_commands(self):
        self.assertEqual(self.post({"cmd": "toggle_exec", "pin": "123456"}), 200)
        self.assertEqual(self.post({"cmd": "action:ppt_next", "pin": "123456"}), 200)
        self.assertEqual(self.post({"cmd": "profile:user:ab12", "pin": "123456"}), 200)
        self.assertEqual(self.cmds, ["toggle_exec", "action:ppt_next", "profile:user:ab12"])
        self.assertEqual(self.post({"cmd": "toggle_exec", "pin": "nope"}), 403)
        self.assertEqual(self.post({"cmd": "rm -rf /", "pin": "123456"}), 400)
        self.assertEqual(self.post({"cmd": "action:run_command", "pin": "123456"}), 400)   # فهرست ایمن
        self.assertEqual(len(self.cmds), 3)

    def test_pin_generator(self):
        p = remote.new_pin()
        self.assertEqual(len(p), 6)
        self.assertTrue(p.isdigit())


class TestUpdater(unittest.TestCase):
    def test_versions(self):
        self.assertGreater(updater.parse_version("4.10"), updater.parse_version("4.9"))
        self.assertEqual(updater.parse_version("v3.1.0-beta"), (3, 1, 0))

    def test_check(self):
        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200); self.end_headers()
                self.wfile.write(json.dumps({"version": "9.9", "url": "http://x", "notes": "n"}).encode())

            def log_message(self, *a): pass
        srv = _Srv(H)
        try:
            url = f"http://127.0.0.1:{srv.port}/v.json"
            self.assertEqual(updater.check(url, "4.0")["version"], "9.9")
            self.assertIsNone(updater.check(url, "9.9"))
        finally:
            srv.close()


class TestPlugins(unittest.TestCase):
    def test_load_run_notify_errors(self):
        with tempfile.TemporaryDirectory() as d:
            pm = plugins.PluginManager(d)
            pm.write_example()
            (Path(d) / "broken.py").write_text("raise RuntimeError('boom')")
            (Path(d) / "mine.py").write_text(
                "PLUGIN_NAME='Mine'\nLOG=[]\nACTIONS=[('go','Go','text')]\n"
                "def run(a,p): LOG.append((a,p))\ndef on_event(n,d): LOG.append((n,d))\n")
            pm.load()
            keys = [k for k, _l, _t in pm.actions]
            self.assertIn("plugin:example_plugin:hello", keys)
            self.assertIn("plugin:mine:go", keys)
            self.assertEqual(len(pm.errors), 1)
            pm.run("plugin:mine:go", "x")
            pm.notify("gesture", "palm")
            self.assertEqual(pm.mods["mine"].LOG, [("go", "x"), ("gesture", "palm")])
            pm.run("plugin:missing:x")                       # بدون پرتاب خطا


class TestVoice(unittest.TestCase):
    def test_normalize_and_match(self):
        self.assertEqual(voice.normalize_phrase("اسلايد  بعدي!"), "اسلاید بعدی")
        phrases = ["اسلاید بعدی", "Next Slide", "صدا بیشتر"]
        self.assertEqual(voice.match_phrase("اسلايد بعدي", phrases), "اسلاید بعدی")
        self.assertEqual(voice.match_phrase("please next slide now", phrases), "Next Slide")
        self.assertIsNone(voice.match_phrase("چیز دیگر", phrases))
        self.assertIsNone(voice.match_phrase("", phrases))
        self.assertEqual(json.loads(voice.build_grammar(phrases))[-1], "[unk]")


class TestOverlay(unittest.TestCase):
    def test_state_commands(self):
        s = overlay.OverlayState()
        self.assertFalse(s.active())
        s.command("laser"); self.assertTrue(s.laser and s.active())
        s.command("draw"); s.command("pen_down")
        for i in range(5):
            s.feed(i * 10, 5)
        s.command("pen_up"); s.feed(100, 100)
        s.command("pen_down"); s.feed(0, 0); s.feed(1, 1)
        self.assertEqual(len(s.strokes), 2)                      # دو خط جدا
        self.assertEqual(len(s.strokes[0]["pts"]), 5)
        s.command("color"); self.assertEqual(s.color, overlay.OverlayState.COLORS[1])
        s.command("clear"); self.assertEqual(s.strokes, [])
        s.command("draw"); self.assertFalse(s.pen)               # با خاموش شدن نقاشی قلم بالا می‌رود
        s.command("pen_down"); s.feed(5, 5)
        self.assertEqual(s.strokes, [])                          # وقتی نقاشی خاموش است چیزی ثبت نمی‌شود
        s.command("timer"); self.assertRegex(s.timer_text(), r"^\d\d:\d\d$")
        s.command("timer"); self.assertEqual(s.timer_text(), "")

    def test_keyboard_layouts(self):
        for rows in (overlay.KB_EN, overlay.KB_FA):
            flat = [k for r in rows for k in r]
            self.assertIn("Space", flat); self.assertIn("⌫", flat); self.assertIn("Enter", flat)
            self.assertGreater(len(flat), 30)
        self.assertEqual(sorted(k for k in overlay.KB_EN[1]), sorted("qwertyuiop"))
        self.assertEqual(overlay.key_output("a", True), ("char", "A"))
        self.assertEqual(overlay.key_output("ض", True), ("char", "ض"))
        self.assertEqual(overlay.key_output("Shift"), ("special", "Shift"))


class TestI18n(unittest.TestCase):
    def test_translate_and_dictionary(self):
        i18n.set_language("en")
        self.assertEqual(i18n.tr("➕ جدید"), "➕ New")
        self.assertEqual(i18n.tr("متن ناشناخته"), "متن ناشناخته")
        i18n.set_language("fa")
        self.assertEqual(i18n.tr("➕ جدید"), "➕ جدید")
        self.assertEqual(i18n.load_dictionary("zz"), {})

    def test_dictionary_keys_exist_in_app(self):
        src = (stubs.ROOT / "hand_control_pro.py").read_text(encoding="utf-8")
        missing = [k for k in i18n.EN if k not in src and k.replace("\n", "\\n") not in src]
        self.assertLessEqual(len(missing), 6, missing)            # فقط چند متن تب‌های تازه

    def test_translate_tree_needs_widgets(self):
        class W:
            pass
        self.assertEqual(i18n.translate_tree(W(), {}), 0)
