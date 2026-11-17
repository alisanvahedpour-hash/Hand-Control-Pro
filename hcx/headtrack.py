"""کنترل نشانگر با سر و پلک (دسترس‌پذیری) — منطق خالص، بدون وابستگی به دوربین"""
import numpy as np

LEFT_EYE = (33, 160, 158, 133, 153, 144)
RIGHT_EYE = (362, 385, 387, 263, 373, 380)
NOSE, FACE_L, FACE_R = 1, 234, 454


def ear(points):
    """نسبت باز بودن چشم (Eye Aspect Ratio) از ۶ نقطه [p1..p6]"""
    p = [np.asarray(x, float) for x in points]
    return float((np.linalg.norm(p[1] - p[5]) + np.linalg.norm(p[2] - p[4]))
                 / (2 * np.linalg.norm(p[0] - p[3]) + 1e-9))


def face_metrics(landmarks, w, h):
    """از لندمارک‌های FaceMesh: (بینی، پهنای صورت، EAR چپ، EAR راست) به پیکسل"""
    def pt(i):
        return (landmarks[i].x * w, landmarks[i].y * h)
    nose = np.array(pt(NOSE))
    fw = float(np.linalg.norm(np.array(pt(FACE_L)) - np.array(pt(FACE_R))))
    el = ear([pt(i) for i in LEFT_EYE])
    er = ear([pt(i) for i in RIGHT_EYE])
    return nose, fw, el, er


class HeadTracker:
    """سر = مکان‌نما ؛ پلک بلند = کلیک ؛ چشمک چپ = کلیک راست ؛ چشمک راست = دابل‌کلیک"""

    def __init__(self, gain=2.2, ear_thr=0.19, blink_min=0.45, blink_max=1.5):
        self.gain = gain
        self.ear_thr = ear_thr
        self.blink_min = blink_min
        self.blink_max = blink_max
        self.neutral = None
        self.closed_since = {"both": None, "left": None, "right": None}

    def recenter(self):
        self.neutral = None

    def _event(self, name, closed, t):
        """رویداد هنگام باز شدن چشم‌ها اگر مدت بستنش در بازه بود"""
        t0 = self.closed_since[name]
        if closed:
            if t0 is None:
                self.closed_since[name] = t
            return None
        self.closed_since[name] = None
        if t0 is not None and self.blink_min <= t - t0 <= self.blink_max:
            return True
        return None

    def update(self, t, nose, face_w, ear_l, ear_r):
        """برمی‌گرداند ((u, v) در بازهٔ ۰ تا ۱ صفحه، فهرست رویدادها)"""
        nose = np.asarray(nose, float)
        if self.neutral is None:
            self.neutral = nose.copy()
        d = (nose - self.neutral) / max(face_w, 1e-6)
        u = float(np.clip(0.5 + d[0] * self.gain, 0.0, 1.0))
        v = float(np.clip(0.5 + d[1] * self.gain, 0.0, 1.0))
        cl, cr = ear_l < self.ear_thr, ear_r < self.ear_thr
        events = []
        if self._event("both", cl and cr, t):
            events.append("click")
        if self._event("left", cl and not cr, t):
            events.append("right_click")
        if self._event("right", cr and not cl, t):
            events.append("double_click")
        return (u, v), events
