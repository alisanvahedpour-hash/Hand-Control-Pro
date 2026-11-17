"""یادگیری ژست‌های ثابت از نمونه‌های خود کاربر (کم‌نمونه، بدون نیاز به کتابخانهٔ سنگین).

روش: نزدیک‌ترین‌همسایه با افزایش داده (چرخش و تغییر اندازهٔ کوچک) و آستانهٔ
خودکار برای هر ژست که از پراکندگی نمونه‌های همان ژست محاسبه می‌شود.
"""
import numpy as np


def _rot(vec, deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    p = np.asarray(vec, float).reshape(-1, 2)
    return (p @ np.array([[c, -s], [s, c]]).T).reshape(-1)


def _dists(A, b):
    d = (A - b).reshape(len(A), -1, 2)
    return np.linalg.norm(d, axis=2).mean(axis=1)


class PoseModel:
    def __init__(self):
        self.classes = {}

    @staticmethod
    def threshold(V):
        """آستانهٔ تشخیص یک ژست از پراکندگی نمونه‌هایش"""
        if len(V) < 4:
            return 0.25
        ds = np.array([_dists(np.delete(V, i, axis=0), V[i]).min()
                       for i in range(len(V))])
        return float(np.clip(ds.mean() + 3 * ds.std() + 0.04, 0.12, 0.35))

    def fit(self, samples, seed=0):
        """samples: {برچسب: [بردار ژست، ...]}"""
        rng = np.random.default_rng(seed)
        self.classes = {}
        for label, vecs in samples.items():
            V = np.asarray(vecs, float)
            if V.ndim == 1:
                V = V[None]
            if len(V) == 0:
                continue
            aug = [V]
            for deg in (-12, -6, 6, 12):
                aug.append(np.stack([_rot(v, deg) for v in V]))
            for _ in range(2):
                aug.append(V * rng.uniform(0.94, 1.06, (len(V), 1))
                           + rng.normal(0, 0.01, V.shape))
            self.classes[label] = {"X": np.concatenate(aug),
                                   "thr": self.threshold(V)}
        return self

    def predict(self, vec):
        """(برچسب یا None، نسبت فاصله به آستانه) — نسبت کمتر از ۱ = قبول"""
        vec = np.asarray(vec, float)
        best, best_r = None, 9.0
        for label, c in self.classes.items():
            r = float(np.sort(_dists(c["X"], vec))[:3].mean() / c["thr"])
            if r < 1.0 and r < best_r:
                best, best_r = label, r
        return best, best_r
