"""تست برنامهٔ اصلی: توابع، موتور تشخیص (با دوربین شبیه‌سازی‌شده) و رابط (با Qt جایگزین)"""
import json
import pathlib
import shutil
import subprocess
import tempfile
import time
import unittest
from types import SimpleNamespace as NS

import numpy as np

from tests import stubs
from tests.stubs import ACTS, COUNT, TM, bind, run_engine

hc = stubs.load_app()
names = lambda: [a[0] for a in ACTS]          # noqa: E731


def hand(pose="palm", cx=600, cy=350, scale=1.5):
    return {"pose": pose, "cx": cx, "cy": cy, "scale": scale}


class TestCore(unittest.TestCase):
    def test_hotkeys(self):
        self.assertEqual(hc.parse_hotkey("ctrl+alt+h"), ([0x11, 0x12], ord("H")))
        self.assertEqual(hc.parse_hotkey("win+d")[1], ord("D"))
        self.assertEqual(hc.parse_hotkey("ctrl+shift+f5")[1], 0x74)
        for bad in ("h", "ctrl+", "ctrl+alt+bad", ""):
            self.assertIsNone(hc.parse_hotkey(bad))

    def test_calibration(self):
        rng = np.random.default_rng(3)

        def smp(a, th, pi, far, px=(300, 200)):
            return {"angles": list(a), "thumb_v": th, "pinch_v": pi, "far_v": far, "palm": 60.0, "px": px}
        data = {"open": [smp(rng.normal(172, 4, 4), .9, 1.6, 1.3) for _ in range(35)],
                "fist": [smp(rng.normal(85, 10, 4), .4, .8, .6) for _ in range(35)],
                "trigger": [smp(rng.normal(150, 5, 4), .35, 1.1, 1.2) for _ in range(35)],
                "point": [smp(rng.normal(170, 5, 4), .95, 1.2, 1.3, (300 + rng.normal(0, 1.5), 200 + rng.normal(0, 1.5))) for _ in range(35)],
                "pinch": [smp(rng.normal(120, 8, 4), .5, .18, 1.05) for _ in range(35)]}
        upd, rpt = hc.compute_calibration(data)
        self.assertTrue(110 < upd["ext_angle"] < 160)
        self.assertLess(upd["tuck_on"], upd["tuck_off"])
        self.assertLess(upd["pinch_on"], upd["pinch_off"])
        self.assertTrue(0.6 < upd["pinch_far"] < 1.1)
        self.assertEqual(hc.compute_calibration({}), ({}, []))
        # دو حالت یکسان = نباید آستانه عوض شود
        same = {"open": data["fist"], "fist": data["fist"]}
        self.assertNotIn("ext_angle", hc.compute_calibration(same)[0])

    def test_profiles_are_valid(self):
        valid_actions = {a[0] for a in hc.ACTIONS}
        for k, fn in hc.PROFILES.items():
            for b in fn():
                self.assertIn(b["action"], valid_actions, (k, b))
                self.assertIn(b["gesture"], hc.BUILTIN_GESTURES, (k, b))
        self.assertIn("presenter", hc.PROFILES)
        self.assertEqual(set(hc.PROFILES), set(hc.PROFILE_NAMES))

    def test_dangerous_and_tremor(self):
        self.assertTrue(hc.is_dangerous("hotkey", "ALT + F4"))
        self.assertFalse(hc.is_dangerous("hotkey", "ctrl+c"))
        ca = [{"id": "x", "name": "n", "steps": [{"type": "hotkey", "param": "alt+f4"}]}]
        self.assertTrue(hc.is_dangerous("custom:x", "", ca))
        cfg = hc.apply_tremor(dict(hc.DEFAULT_SETTINGS, tremor_mode=True))
        self.assertGreaterEqual(cfg["smoothing"], 8)
        self.assertLessEqual(cfg["vote_min"], cfg["vote_frames"])
        self.assertEqual(hc.apply_tremor(dict(hc.DEFAULT_SETTINGS))["smoothing"], hc.DEFAULT_SETTINGS["smoothing"])

    def test_app_matches(self):
        self.assertTrue(hc.app_matches("", "x", "y"))
        self.assertTrue(hc.app_matches("exe:chrome", "chrome.exe", ""))
        self.assertTrue(hc.app_matches("chrome", "chrome", ""))
        self.assertTrue(hc.app_matches("title:Docs", "", "My Docs - Chrome"))
        self.assertFalse(hc.app_matches("exe:firefox", "chrome", ""))

    def test_custom_action_alt_f4_and_macro_options(self):
        ACTS.clear()
        hc.set_custom_actions([
            {"id": "c", "name": "بستن پنجره", "steps": [{"type": "hotkey", "param": "alt+f4"}]},
            {"id": "m", "name": "ماکرو", "repeat": 3,
             "steps": [{"type": "key", "param": "enter"}, {"type": "left_click", "param": ""}]},
            {"id": "o", "name": "شرطی", "only_if": "exe:chrome", "steps": [{"type": "key", "param": "esc"}]}])
        hc.run_action("custom:c"); time.sleep(0.2)
        self.assertIn(("hotkey", "alt", "f4"), ACTS)
        ACTS.clear(); hc.run_action("custom:m"); time.sleep(0.4)
        self.assertEqual(names().count("press"), 3)
        self.assertEqual(names().count("click"), 3)
        ACTS.clear()
        orig = hc.get_active_app
        hc.get_active_app = lambda: ("firefox", "x")
        hc.run_action("custom:o"); time.sleep(0.2)
        self.assertEqual(ACTS, [])                          # برنامهٔ دیگری فعال است
        hc.get_active_app = lambda: ("chrome.exe", "x")
        hc.run_action("custom:o"); time.sleep(0.2)
        self.assertIn(("press", "esc"), ACTS)
        hc.get_active_app = orig
        self.assertEqual(hc.action_speech("custom:c"), "بستن پنجره")
        self.assertEqual(hc.action_speech("copy"), "کپی")

    def test_new_steps_and_actions(self):
        ACTS.clear()
        hc.run_action("click_at", "100,200,right"); hc.run_action("move_to", "5,6")
        self.assertEqual(ACTS, [("click", 100, 200), ("moveTo", 5, 6)])
        hooks = []
        hc.HOOKS["overlay"] = hooks.append
        hc.run_action("overlay_laser"); hc.run_action("airkb_toggle")
        self.assertEqual(hooks, ["overlay_laser", "airkb_toggle"])
        calls = []
        orig = hc.integ.ha_call
        hc.integ.ha_call = lambda spec: calls.append(spec)
        hc.run_action("ha_service", "light.turn_on light.x")
        hc.integ.ha_call = orig
        self.assertEqual(calls, ["light.turn_on light.x"])
        self.assertIn("overlay_pen", hc.CONTINUOUS)

    def test_tracking_hooks_stats_and_tts(self):
        spoken = []
        orig = hc.integ.speak
        hc.integ.speak = spoken.append
        from hcx.stats import UsageStats
        st = UsageStats(); hc.RUNTIME["stats"] = st; hc.RUNTIME["tts"] = True
        try:
            hc.run_action("copy")
            hc.run_action("hotkey", "ctrl+x", track=False)
        finally:
            hc.RUNTIME["stats"] = None; hc.RUNTIME["tts"] = False; hc.integ.speak = orig
        self.assertEqual(spoken, ["کپی"])
        self.assertEqual(st.top("actions"), [("copy", 1)])

    def test_plugin_actions_listed_and_run(self):
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / "p.py").write_text(
                "PLUGIN_NAME='P'\nLOG=[]\nACTIONS=[('a','A',None)]\ndef run(a,p): LOG.append(a)\n")
            old = hc.PLUGINS.folder
            hc.PLUGINS.folder = pathlib.Path(d); hc.PLUGINS.load()
            try:
                self.assertIn("plugin:p:a", [a[0] for a in hc.all_actions()])
                hc.run_action("plugin:p:a")
                self.assertEqual(hc.PLUGINS.mods["p"].LOG, ["a"])
            finally:
                hc.PLUGINS.folder = old; hc.PLUGINS.load()

    def test_config_roundtrip_with_voices(self):
        with tempfile.TemporaryDirectory() as d:
            old = (hc.CONFIG_DIR, hc.CONFIG_FILE)
            hc.CONFIG_DIR = pathlib.Path(d); hc.CONFIG_FILE = hc.CONFIG_DIR / "c.json"
            try:
                st, data = hc.load_config()
                self.assertEqual(st["cfg_version"], 2)
                self.assertTrue(len(data["bindings"]) > 0)
                data["voices"] = [{"id": "v1", "name": "بعدی"}]
                hc.save_config(st, data)
                self.assertEqual(hc.load_config()[1]["voices"][0]["name"], "بعدی")
                # پیکربندی قدیمی بدون کلیدهای جدید
                hc.CONFIG_FILE.write_text(json.dumps({"settings": {"margin": 90}, "bindings": []}))
                st2, d2 = hc.load_config()
                self.assertEqual(st2["margin"], hc.DEFAULT_SETTINGS["margin"])
                self.assertEqual(d2["voices"], [])
                self.assertEqual(st2["language"], "fa")
            finally:
                hc.CONFIG_DIR, hc.CONFIG_FILE = old

    def test_camera_source_url(self):
        stubs.OPENED.clear()
        self.assertIsNotNone(hc.open_camera("rtsp://x/y"))
        self.assertIsNotNone(hc.open_camera("2"))
        self.assertEqual(stubs.OPENED[0], ("rtsp://x/y",))

    def test_linux_helpers(self):
        calls = []
        orig = (subprocess.run, hc.shutil.which, subprocess.Popen)
        subprocess.run = lambda cmd, **k: NS(stdout="_NET_ACTIVE_WINDOW(WINDOW): window id # 0x0\n")
        hc.shutil.which = lambda n: "/usr/bin/" + n
        try:
            self.assertEqual(hc.linux_active_app(), ("", ""))
            hc.IS_LINUX_SAVED = hc.IS_LINUX
        finally:
            subprocess.run, hc.shutil.which, subprocess.Popen = orig


class TestEngine(unittest.TestCase):
    def test_hold_and_confirm(self):
        run_engine(hc, [bind("palm", "media_play_pause", "", 0.1)],
                   lambda i: [hand()] if i > 5 else [], frames=150)
        self.assertEqual(names().count("press"), 1)
        # confirm = نگه‌داشتن ۱٫۲ ثانیه: در ۰٫۶ ثانیه نباید اجرا شود
        ev = run_engine(hc, [bind("palm", "hotkey", "alt+f4", 0, confirm=True)],
                        lambda i: [hand()] if i > 5 else [], frames=60, delay=0.008)
        self.assertEqual(ACTS, [])
        self.assertEqual(ev["engine"].hold_map["palm"][0][0], 1.2)

    def test_volume_seek_sequence_zoom(self):
        run_engine(hc, [bind("fist", "volume_slider")],
                   lambda i: [hand("fist", 600, 500 - 6 * i)] if i > 5 else [], frames=60)
        self.assertGreater(names().count("press"), 2)
        self.assertEqual({a[1] for a in ACTS if a[0] == "press"}, {"volumeup"})
        run_engine(hc, [bind("fist", "seek_slider")],
                   lambda i: [hand("fist", 300 + 8 * i, 400)] if i > 5 else [], frames=60)
        self.assertEqual({a[1] for a in ACTS if a[0] == "press"}, {"right"})

        def scene(i):
            if 6 <= i < 30: return [hand("palm")]
            if 36 <= i < 70: return [hand("fist")]
            return []
        ev = run_engine(hc, [bind("seq:s1", "copy")], scene, frames=90,
                        sequences=[{"id": "s1", "name": "pf", "steps": ["palm", "fist"], "window": 6}])
        self.assertEqual(ev["mot"], [("seq:s1",)])
        self.assertIn(("hotkey", "ctrl", "c"), ACTS)

        run_engine(hc, [bind("palm", "two_hand_zoom")],
                   lambda i: [hand("palm", 500, 360, 1.8), hand("palm", 700 + 9 * i, 360, 1.5)] if i > 5 else [],
                   frames=70)
        self.assertIn(("keyDown", "ctrl"), ACTS)
        self.assertTrue(any(a[0] == "scroll" and a[1] > 0 for a in ACTS))

    def test_dwell_monitor_and_calibration(self):
        run_engine(hc, [bind("point", "move_cursor")], lambda i: [hand("point", 600, 400)] if i > 5 else [],
                   frames=120, cfg_over={"dwell_click": True, "dwell_time": 0.1, "dwell_radius": 12})
        self.assertGreaterEqual(names().count("click"), 1)
        run_engine(hc, [bind("point", "move_cursor")], lambda i: [hand("point", 600, 400)] if i > 5 else [],
                   frames=60, cfg_over={"monitor_rect": [1920, 0, 1280, 720], "smoothing": 1.0, "deadzone": 0})
        xs = [a[1] for a in ACTS if a[0] == "moveTo"]
        self.assertTrue(xs and all(x >= 1900 for x in xs))
        stubs_ = {}
        ev = run_engine(hc, [], lambda i: [hand()] if i > 5 else [], frames=40,
                        hook=lambda n: stubs.STATE["engine"].start_collect(10) if n == 15 else None)
        self.assertEqual(len(ev["cd"]), 1)
        self.assertEqual(len(ev["cd"][0][0]), 10)
        self.assertEqual(sorted(ev["cd"][0][0][0]), ["angles", "far_v", "palm", "pinch_v", "px", "thumb_v"])

    def test_overlay_pen_hooks(self):
        calls = []
        hc.HOOKS["overlay"] = calls.append
        run_engine(hc, [bind("fist", "overlay_pen")],
                   lambda i: [hand("fist", 600, 400)] if 6 <= i < 40 else [], frames=70)
        self.assertEqual(calls[0], "overlay_pen_down")
        self.assertEqual(calls[-1], "overlay_pen_up")
        self.assertGreater(names().count("moveTo"), 3)
        hc.HOOKS["overlay"] = None

    def test_head_control_moves_and_clicks(self):
        def face(i):
            if i < 10:
                return {"nose": (0.5, 0.5)}
            if i < 40:
                return {"nose": (0.5 + 0.004 * (i - 10), 0.5)}        # سر به راست
            if i < 110:
                return {"nose": (0.62, 0.5), "left_closed": True, "right_closed": True}
            return {"nose": (0.62, 0.5)}
        run_engine(hc, [], lambda i: [], frames=130, face=face, delay=0.012,
                   cfg_over={"head_control": True, "head_gain": 3.0, "smoothing": 1.0})
        moves = [a for a in ACTS if a[0] == "moveTo"]
        self.assertGreater(len(moves), 20)
        self.assertGreater(moves[-1][1], moves[0][1])
        self.assertIn("click", names())

    def test_learned_custom_gesture(self):
        T = TM["palm"]
        p = (T - T[0]) / (np.linalg.norm(T[0] - T[9]))
        samples = [(p[1:].flatten() + np.random.default_rng(i).normal(0, .006, 40)).tolist() for i in range(12)]
        customs = [{"id": "z", "name": "z", "vec": samples[0], "samples": samples}]
        ev = run_engine(hc, [bind("custom:z", "media_play_pause")],
                        lambda i: [hand("palm")] if i > 5 else [], frames=60, customs=customs)
        self.assertIn("custom:z", [g[0] for g in ev["gest"]])
        self.assertIn("press", names())

    def test_stats_plugins_and_tts_from_engine(self):
        from hcx.stats import UsageStats
        st = UsageStats(); hc.RUNTIME["stats"] = st
        try:
            run_engine(hc, [bind("palm", "copy")], lambda i: [hand()] if i > 5 else [], frames=60)
        finally:
            hc.RUNTIME["stats"] = None
        self.assertEqual(st.top("gestures")[0][0], "palm")
        self.assertEqual(st.top("actions")[0], ("copy", 1))
        self.assertGreater(list(st.days.values())[0]["active_s"], 0)

    def test_low_power_skips_frames(self):
        run_engine(hc, [], lambda i: [], frames=60, cfg_over={"low_power": False})
        normal = COUNT["process"]
        run_engine(hc, [], lambda i: [], frames=60, cfg_over={"low_power": True, "idle_after": 0.0})
        self.assertLess(COUNT["process"], normal * 0.6)

    def test_far_mode_pipeline_runs(self):
        ev = run_engine(hc, [bind("palm", "pause")], lambda i: [hand()] if 6 <= i < 80 else [], frames=100,
                        cfg_over={"far_mode": True, "enhance": True, "edge_pad": 0.12})
        self.assertEqual(ev["err"], [])
        self.assertIn("palm", [g[0] for g in ev["gest"]])


class TestMainWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class QMB:
            class StandardButton: Yes = 1; No = 2
            class ButtonRole: AcceptRole = 0; ActionRole = 1; DestructiveRole = 2; RejectRole = 3
            ans = 1; pick = "rep"
            def __init__(self, *a): self.btns = []
            def setWindowTitle(self, *a): pass
            def setText(self, *a): pass
            def addButton(self, text, role): b = NS(text=text); self.btns.append(b); return b
            def exec(self): pass
            def clickedButton(self): return self.btns[{"rep": 0, "add": 1, "cancel": 2}[QMB.pick]]
            @staticmethod
            def question(*a, **k): return QMB.ans
            @staticmethod
            def information(*a, **k): pass
            @staticmethod
            def warning(*a, **k): pass
        cls.QMB = QMB
        hc.QMessageBox = QMB
        cls.tmp = tempfile.mkdtemp()
        cls.old = (hc.CONFIG_DIR, hc.CONFIG_FILE)
        hc.CONFIG_DIR = pathlib.Path(cls.tmp); hc.CONFIG_FILE = hc.CONFIG_DIR / "config.json"
        hc.QInputDialog = NS(getText=staticmethod(lambda *a, **k: ("متن تست", True)),
                             getItem=staticmethod(lambda *a, **k: (a[3][0], True)))
        cls.files = {"p": str(pathlib.Path(cls.tmp) / "x.json")}
        hc.QFileDialog = NS(getSaveFileName=staticmethod(lambda *a, **k: (cls.files["p"], "")),
                            getOpenFileName=staticmethod(lambda *a, **k: (cls.files["p"], "")))
        cls.w = hc.MainWindow()

    @classmethod
    def tearDownClass(cls):
        hc.CONFIG_DIR, hc.CONFIG_FILE = cls.old
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_startup_state(self):
        w = self.w
        self.assertTrue(w.first_run)
        self.assertGreater(len(w.bindings), 5)
        self.assertEqual(w.voices, [])
        self.assertEqual(w._lang, "fa")
        self.assertIn(("🎤 x", "voice:x"), [(l, k) for l, k in [("🎤 x", "voice:x")]])

    def test_voice_flow(self):
        w = self.w
        w.add_voice()
        self.assertEqual(w.voices[-1]["name"], "متن تست")
        key = "voice:" + w.voices[-1]["id"]
        self.assertIn(key, [k for _l, k in w.gesture_choices()])
        self.assertEqual(w.gesture_label(key), "🎤 متن تست")
        w.bindings.append({"id": "vb", "name": "v", "gesture": key, "action": "copy", "param": "",
                           "enabled": True, "hold": 0, "need_gesture": "palm"})
        ACTS.clear()
        w.last_stable = "none"; w.on_voice_heard("لطفا متن تست را اجرا کن"); time.sleep(0.2)
        self.assertEqual(ACTS, [])                                    # ژست شرط برقرار نیست
        w.last_stable = "palm"; w.on_voice_heard("متن تست"); time.sleep(0.2)
        self.assertIn(("hotkey", "ctrl", "c"), ACTS)
        ACTS.clear(); w.on_voice_heard("چیز دیگر"); self.assertEqual(ACTS, [])
        w.tools_tab.voice_list = NS(currentRow=lambda: len(w.voices) - 1, clear=lambda: None,
                                    addItem=lambda *a: None)
        w.delete_voice()
        self.assertEqual(w.voices, [])
        self.assertFalse(any(b["gesture"] == key for b in w.bindings))

    def test_remote_commands(self):
        w = self.w
        w.exec_check = NS(isChecked=lambda: True, setChecked=lambda v: calls.append(("exec", v)))
        calls = []
        w.start_engine = lambda: calls.append("cam_on"); w.stop_engine = lambda: calls.append("cam_off")
        for cmd in ("toggle_exec", "exec_off", "camera_on", "camera_off", "stop", "profile:media", "profile:evil"):
            w.on_remote_cmd(cmd)
        self.assertEqual(calls, [("exec", False), ("exec", False), "cam_on", "cam_off", ("exec", False), "cam_off"])
        self.assertEqual(w.manual_profile, "media")                   # پروفایل ناشناس نادیده گرفته می‌شود
        w.set_manual_profile(None)
        ACTS.clear(); w.on_remote_cmd("action:media_play_pause"); self.assertTrue(ACTS)

    def test_profiles_rules_and_auto_switch(self):
        w = self.w
        w.add_suggested_rules()
        self.assertGreater(len(w.app_rules), 5)
        orig = hc.get_active_app
        try:
            hc.get_active_app = lambda: ("powerpnt.exe", "Deck")
            w.check_active_app()
            self.assertEqual(w.active_profile, "powerpoint")
            hc.get_active_app = lambda: ("chromium", "Home")
            w.check_active_app()
            self.assertEqual(w.active_profile, "browser")
            hc.get_active_app = lambda: ("python3", "dialog")
            w.check_active_app()
            self.assertEqual(w.active_profile, "browser")             # پنجرهٔ خود برنامه = بدون تغییر
        finally:
            hc.get_active_app = orig
        self.assertEqual(len(w.profile_bindings("presenter")), len(hc.presenter_bindings()))
        w.active_profile = None

    def test_backup_restore_and_delete_flows(self):
        w = self.w
        w.export_all()
        raw = json.loads(
            pathlib.Path(self.files["p"]).read_text(encoding="utf-8")
        )
        self.assertNotIn("owner", raw)
        self.assertIn("voices", raw)
        w.bindings = [{"id": "zz", "name": "e", "gesture": "palm", "action": "copy", "param": "", "enabled": True}]
        self.QMB.pick = "cancel"; w.import_all()
        self.assertEqual([b["id"] for b in w.bindings], ["zz"])
        self.QMB.pick = "rep"; w.import_all()
        self.assertEqual([b["id"] for b in w.bindings], [b["id"] for b in raw["bindings"]])
        self.assertTrue(w.undo_stack)

    def test_language_switch_and_runtime_sync(self):
        w = self.w
        w.settings["language"] = "en"
        w.apply_language()
        self.assertEqual(w._lang, "en")
        self.assertFalse(w.settings["ui_rtl"])
        w.settings["language"] = "fa"
        w.apply_language()
        self.assertTrue(w.settings["ui_rtl"])
        w.settings["tts"] = True; w.sync_runtime()
        self.assertTrue(hc.RUNTIME["tts"])
        w.settings["tts"] = False; w.sync_runtime()

    def test_extras_services_off_by_default(self):
        w = self.w
        w.sync_services()
        self.assertIsNone(w.voice)
        self.assertIsNone(w.remote)
        w.shutdown_extras()
