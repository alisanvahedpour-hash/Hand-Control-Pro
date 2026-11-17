"""دستور صوتی آفلاین با Vosk (اختیاری). مدل را از alphacephei.com/vosk/models دانلود کنید."""
import json
import queue
import re
import threading

try:
    from PyQt6.QtCore import QThread, pyqtSignal
except Exception:                      # برای تست بدون Qt
    QThread = object

    def pyqtSignal(*a):
        return None


_FIX = str.maketrans({"ي": "ی", "ك": "ک", "ۀ": "ه", "ة": "ه", "‌": " ", "أ": "ا", "إ": "ا"})


def normalize_phrase(text):
    """یکسان‌سازی حروف فارسی/عربی، حذف فاصله‌های اضافه و کوچک‌کردن حروف لاتین"""
    t = (text or "").translate(_FIX).lower()
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def match_phrase(heard, phrases):
    """بهترین عبارت ثبت‌شده که با آنچه شنیده شد برابر است یا در آن آمده؛ وگرنه None"""
    h = normalize_phrase(heard)
    if not h:
        return None
    norm = {normalize_phrase(p): p for p in phrases if normalize_phrase(p)}
    if h in norm:
        return norm[h]
    for n in sorted(norm, key=len, reverse=True):
        if re.search(rf"(^| ){re.escape(n)}( |$)", h):
            return norm[n]
    return None


def build_grammar(phrases):
    return json.dumps([normalize_phrase(p) for p in phrases if p] + ["[unk]"],
                      ensure_ascii=False)


class VoiceListener(QThread):
    heard = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, model_path, phrases):
        super().__init__()
        self.model_path = model_path
        self.phrases = list(phrases)
        self._quit = False

    def stop(self):
        self._quit = True
        self.wait(2000)

    def run(self):
        try:
            import sounddevice as sd
            from vosk import KaldiRecognizer, Model
        except ImportError:
            self.status.emit("نصب نیست: pip install vosk sounddevice")
            return
        try:
            model = Model(self.model_path)
        except Exception as e:
            self.status.emit(f"مدل بارگذاری نشد: {e}")
            return
        rec = KaldiRecognizer(model, 16000, build_grammar(self.phrases))
        q = queue.Queue()
        try:
            with sd.RawInputStream(samplerate=16000, blocksize=4000, dtype="int16",
                                   channels=1, callback=lambda d, f, t, s: q.put(bytes(d))):
                self.status.emit("در حال گوش دادن…")
                while not self._quit:
                    try:
                        data = q.get(timeout=0.3)
                    except queue.Empty:
                        continue
                    if rec.AcceptWaveform(data):
                        text = json.loads(rec.Result()).get("text", "")
                        if text and text != "[unk]":
                            self.heard.emit(text)
        except Exception as e:
            self.status.emit(f"میکروفون: {e}")
