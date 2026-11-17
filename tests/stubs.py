"""زیرساخت تست: جایگزین‌های PyQt6، OpenCV، MediaPipe و PyAutoGUI تا همهٔ منطق بدون دوربین و صفحه‌نمایش تست شود."""
import importlib.util
import pathlib
import sys
import time
import types
from types import SimpleNamespace as NS

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class Dummy:
    def __init__(self, *a, **k): pass
    def __getattr__(self, n): return Dummy()
    def __call__(self, *a, **k): return Dummy()
    def __lt__(s, o): return False
    def __gt__(s, o): return False
    def __le__(s, o): return False
    def __ge__(s, o): return False
    def __int__(s): return 0
    def __float__(s): return 0.0
    def __index__(s): return 0
    def __iter__(s): return iter([])
    def __len__(s): return 0
    def __bool__(s): return True
    def __str__(s): return ""
    def __invert__(s): return Dummy()
    def __or__(s, o): return Dummy()
    def __and__(s, o): return Dummy()
    def __ror__(s, o): return Dummy()
    def __rand__(s, o): return Dummy()
    def __hash__(s): return id(s)


class Meta(type):
    def __getattr__(cls, n): return Dummy()


def _stub(name):
    m = types.ModuleType(name)
    m.__getattr__ = lambda n: Meta(n, (Dummy,), {})
    sys.modules[name] = m


STATE = {"frames": 120, "hook": None, "delay": 0.004, "engine": None}
ACTS = []
SCENE = {"fn": lambda i: []}
FACE = {"fn": lambda i: None}
COUNT = {"process": 0}

# ---------------- دوربین و OpenCV ----------------
cv2 = types.ModuleType("cv2")
for k, v in dict(CAP_DSHOW=700, CAP_V4L2=200, CAP_PROP_FOURCC=6, CAP_PROP_FRAME_WIDTH=3,
                 CAP_PROP_FRAME_HEIGHT=4, CAP_PROP_BUFFERSIZE=38, COLOR_BGR2RGB=4,
                 COLOR_RGB2LAB=45, COLOR_LAB2RGB=56, INTER_LANCZOS4=4,
                 BORDER_CONSTANT=0, FONT_HERSHEY_SIMPLEX=0).items():
    setattr(cv2, k, v)
cv2.VideoWriter_fourcc = lambda *a: 0
cv2.flip = lambda f, c: f[:, ::-1].copy()
cv2.cvtColor = lambda f, c: f.copy()
cv2.resize = lambda f, sz, interpolation=None: np.zeros((sz[1], sz[0], f.shape[2]), f.dtype)
cv2.copyMakeBorder = lambda f, t, b, l, r, bt, value=None: np.pad(f, ((t, b), (l, r), (0, 0)))
cv2.createCLAHE = lambda **k: NS(apply=lambda x: x)
for n in ("rectangle", "putText", "line", "circle"):
    setattr(cv2, n, lambda *a, **k: None)
OPENED = []


class Cap:
    def __init__(self, *a):
        self.n = 0
        OPENED.append(a)

    def isOpened(self): return True
    def set(self, *a): pass

    def read(self):
        self.n += 1
        eng = STATE["engine"]
        eng.frames = self.n
        if STATE["hook"]:
            STATE["hook"](self.n)
        if self.n >= STATE["frames"]:
            eng._quit = True
        time.sleep(STATE["delay"])
        return True, np.zeros((720, 1280, 3), np.uint8)

    def release(self): pass


cv2.VideoCapture = Cap

# ---------------- pyautogui ----------------
pg = types.ModuleType("pyautogui")
pg.size = lambda: (1920, 1080)
pg.position = lambda: (100, 100)
for n in ("moveTo", "click", "rightClick", "doubleClick", "middleClick", "mouseDown",
          "mouseUp", "scroll", "press", "hotkey", "write", "keyDown", "keyUp"):
    setattr(pg, n, (lambda nm: (lambda *a, **k: ACTS.append((nm,) + a)))(n))
pg.FAILSAFE = True
pg.PAUSE = 0.1

# ---------------- mediapipe ----------------


def _tmpl(pose):
    T = np.zeros((21, 2))
    T[5] = (-20, -80); T[9] = (0, -85); T[13] = (20, -80); T[17] = (40, -70)
    ext = {"palm": (1, 1, 1, 1), "fist": (0, 0, 0, 0), "point": (1, 0, 0, 0)}[pose]
    for (mcp, pip, dip, tip), e in zip([(5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16),
                                        (17, 18, 19, 20)], ext):
        x, y = T[mcp]
        if e:
            T[pip] = (x, y - 40); T[dip] = (x, y - 65); T[tip] = (x, y - 90)
        else:
            T[pip] = (x, y - 30); T[dip] = (x, y - 10); T[tip] = (x, y + 10)
    if pose == "fist":
        T[1] = (-30, -10); T[2] = (-25, -40); T[3] = (-20, -65); T[4] = (-18, -75)
    else:
        T[1] = (-30, -10); T[2] = (-50, -30); T[3] = (-70, -45); T[4] = (-90, -55)
    return T


TM = {p: _tmpl(p) for p in ("palm", "fist", "point")}


class Hands:
    def __init__(self, static_image_mode=False, **k): self.static = static_image_mode

    def process(self, img):
        COUNT["process"] += 1
        h, w = img.shape[:2]
        hands = SCENE["fn"](STATE["engine"].frames)
        if not hands:
            return NS(multi_hand_landmarks=None, multi_hand_world_landmarks=None, multi_handedness=None)
        L, W, H = [], [], []
        for hd in hands:
            T = TM[hd["pose"]] * hd.get("scale", 1.5) + np.array([hd["cx"], hd["cy"]])
            L.append(NS(landmark=[NS(x=T[j, 0] / w, y=T[j, 1] / h, z=0) for j in range(21)]))
            W.append(NS(landmark=[NS(x=TM[hd["pose"]][j, 0] / 1000, y=TM[hd["pose"]][j, 1] / 1000, z=0)
                                  for j in range(21)]))
            H.append(NS(classification=[NS(label="Right")]))
        return NS(multi_hand_landmarks=L, multi_hand_world_landmarks=W, multi_handedness=H)

    def close(self): pass


class FaceMesh:
    def __init__(self, **k): pass

    def process(self, img):
        f = FACE["fn"](STATE["engine"].frames)
        if f is None:
            return NS(multi_face_landmarks=None)
        lm = [NS(x=0.5, y=0.5, z=0) for _ in range(468)]
        lm[1] = NS(x=f["nose"][0], y=f["nose"][1], z=0)
        lm[234] = NS(x=0.35, y=0.5, z=0); lm[454] = NS(x=0.65, y=0.5, z=0)
        for idx, (cx, closed) in ((( 33, 160, 158, 133, 153, 144), (0.42, f.get("left_closed"))),
                                  ((362, 385, 387, 263, 373, 380), (0.58, f.get("right_closed")))):
            v = 0.002 if closed else 0.012
            p1, p2, p3, p4, p5, p6 = idx
            lm[p1] = NS(x=cx - 0.03, y=0.45, z=0); lm[p4] = NS(x=cx + 0.03, y=0.45, z=0)
            lm[p2] = NS(x=cx - 0.01, y=0.45 - v, z=0); lm[p6] = NS(x=cx - 0.01, y=0.45 + v, z=0)
            lm[p3] = NS(x=cx + 0.01, y=0.45 - v, z=0); lm[p5] = NS(x=cx + 0.01, y=0.45 + v, z=0)
        return NS(multi_face_landmarks=[NS(landmark=lm)])

    def close(self): pass


mp = types.ModuleType("mediapipe")
mp.solutions = NS(hands=NS(Hands=Hands, HAND_CONNECTIONS=[(0, 1), (1, 2)]),
                  face_mesh=NS(FaceMesh=FaceMesh))
mp.__version__ = "0.10.21"

_loaded = {}


def load_app():
    """برنامهٔ اصلی را با جایگزین‌ها بارگذاری می‌کند (یک بار)"""
    if "hc" in _loaded:
        return _loaded["hc"]
    for n in ("PyQt6", "PyQt6.QtCore", "PyQt6.QtGui", "PyQt6.QtWidgets"):
        _stub(n)
    sys.modules["cv2"], sys.modules["pyautogui"], sys.modules["mediapipe"] = cv2, pg, mp
    spec = importlib.util.spec_from_file_location("hand_control_pro", ROOT / "hand_control_pro.py")
    hc = importlib.util.module_from_spec(spec)
    sys.modules["hand_control_pro"] = hc
    spec.loader.exec_module(hc)
    hc.QImage = Dummy()
    _loaded["hc"] = hc
    return hc


class Sig:
    def __init__(self, store=None): self.store = store
    def emit(self, *a):
        if self.store is not None:
            self.store.append(a)
    def connect(self, *a): pass


def bind(g, a, p="", hold=0, **extra):
    d = {"id": f"{g}{a}{hold}", "name": g, "gesture": g, "action": a, "param": p,
         "enabled": True, "hold": hold}
    d.update(extra)
    return d


def run_engine(hc, bindings, scene, frames=120, cfg_over=None, sequences=None, hook=None,
               customs=None, face=None, delay=0.004, motions=None):
    ACTS.clear()
    COUNT["process"] = 0
    STATE.update(frames=frames, hook=hook, delay=delay)
    SCENE["fn"] = scene
    FACE["fn"] = face or (lambda i: None)
    cfg = dict(hc.DEFAULT_SETTINGS, far_mode=False, enhance=False, edge_pad=0.0, vote_frames=3,
               vote_min=2, swipe_cooldown=99, low_power=False)
    cfg.update(cfg_over or {})
    eng = hc.Engine()
    eng.frames = 0
    STATE["engine"] = eng
    eng.update_config(cfg, bindings, customs or [], None, motions or [], [], sequences)
    ev = {"gest": [], "mot": [], "err": [], "cd": [], "cp": []}
    eng.gesture_changed = Sig(ev["gest"]); eng.motion_detected = Sig(ev["mot"])
    eng.error = Sig(ev["err"]); eng.stats = Sig(); eng.frame_ready = Sig(); eng.lock_status = Sig()
    eng.collect_done = Sig(ev["cd"]); eng.collect_progress = Sig(ev["cp"])
    eng._loop()
    ev["engine"] = eng
    return ev
