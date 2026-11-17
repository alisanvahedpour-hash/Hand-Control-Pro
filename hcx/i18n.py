# -*- coding: utf-8 -*-
"""زبان رابط: فارسی (پیش‌فرض)، انگلیسی (داخلی) و هر زبان دیگر با فایل JSON.

روش: متن‌های فارسی با یک دیکشنری «متن فارسی ← ترجمه» عوض می‌شوند.
برای زبان دیگر (مثل عربی): از تب ابزارها «استخراج متن‌ها برای ترجمه» را بزنید،
ترجمه را در  ~/.hand_control/lang/<کد>.json  بگذارید (مثلاً ar.json) و زبان را انتخاب کنید.
متن‌هایی که ترجمه ندارند فارسی می‌مانند.
"""
import json
from pathlib import Path

EN = {
    # ---- هدر، تب‌ها، کلیدهای اصلی ----
    "کنترل کامپیوتر با ژست دست": "Control your computer with hand gestures",
    "ژست‌ها و دستورها": "Gestures & commands", "عمل‌های من": "My actions",
    "ژست‌های من": "My gestures", "ژست‌های آماده": "Built-in gestures",
    "پروفایل‌ها و برنامه‌ها": "Profiles & apps", "ظاهر": "Appearance", "رفتار": "Behavior",
    "تنظیمات": "Settings", "قفل روی دست من": "Owner-hand lock", "ابزارهای ویژه": "Special tools",
    "▶  شروع دوربین": "▶  Start camera", "⏹  توقف دوربین": "⏹  Stop camera",
    "اجرای دستورها (کنترل واقعی کامپیوتر)": "Run commands (real computer control)",
    "ژست فعلی: —": "Current gesture: —", "ℹ️ درباره": "ℹ️ About", "🎯 کالیبراسیون": "🎯 Calibration",
    "🏋️ تمرین": "🏋️ Practice", "📷 دوربین: خاموش": "📷 Camera: off", "📷 دوربین: روشن": "📷 Camera: on",
    "🔒 قفل: خاموش": "🔒 Lock: off", "🔒 قفل: دستی ثبت نشده": "🔒 Lock: no hand enrolled",
    "🔒 قفل: کف دست باز را نشان دهید": "🔒 Lock: show an open palm", "🔒 قفل: ✅ دست شما": "🔒 Lock: ✅ your hand",
    "📌 پروفایل: فعلی": "📌 Profile: current", "پیش‌نمایش خاموش است": "Preview is off",
    "تغییر تم تیره / روشن": "Toggle dark / light theme", "دربارهٔ برنامه (F1)": "About (F1)",
    # ---- جدول و دکمه‌های ژست ----
    "فعال": "Enabled", "نام": "Name", "ژست": "Gesture", "عمل": "Action", "پارامتر": "Parameter",
    "➕ جدید": "➕ New", "✏️ ویرایش": "✏️ Edit", "📄 تکرار": "📄 Duplicate", "🗑️ حذف": "🗑️ Delete",
    "↩ بازگردانی": "↩ Undo", "بارگذاری پروفایل": "Load profile", "حذف همه": "Delete all",
    "هنوز هیچ ژستی تعریف نشده است.\nبا «➕ جدید» یک ژست بسازید یا از پایین یک پروفایل بارگذاری کنید.":
        "No gestures defined yet.\nCreate one with “➕ New” or load a profile below.",
    "ذخیره": "Save", "انصراف": "Cancel", "تأیید": "OK", "بستن": "Close", "حذف": "Delete",
    "ویرایش": "Edit", "جدید": "New", "تغییر نام": "Rename", "آزمایش": "Test",
    "▶ آزمایش عمل": "▶ Test action", "ویرایش ژست": "Edit gesture", "ژست جدید": "New gesture",
    "نام:": "Name:", "ژست:": "Gesture:", "عمل:": "Action:", "پارامتر:": "Parameter:", "فعال ": "Enabled ",
    "نگه‌داشتن ژست:": "Hold gesture:", "فوری (بدون نگه‌داشتن)": "Instant (no hold)",
    "➕ ژست ثابت": "➕ Static gesture", "🌀 ژست متحرک": "🌀 Motion gesture", "➕ عمل جدید": "➕ New action",
    "انتخاب برنامه…": "Choose program…", "ضبط میانبر:": "Record shortcut:",
    "ژست تکراری": "Duplicate gesture", "خوش آمدید": "Welcome",
    "با پیش‌فرض‌ها": "With defaults", "از صفر": "From scratch", "از صفر کامل": "Completely from scratch",
    # ---- پروفایل‌ها ----
    "پیش‌فرض (ماوس)": "Default (mouse)", "ارائهٔ پاورپوینت 📽️": "PowerPoint presentation 📽️",
    "مرورگر 🌐": "Browser 🌐", "پخش‌کننده / رسانه 🎵": "Media player 🎵", "خالی (از صفر)": "Empty (from scratch)",
    "پروفایل‌های من:": "My profiles:", "💾 ذخیرهٔ ژست‌های فعلی": "💾 Save current gestures",
    "📥 بارگذاری": "📥 Load", "📤 خروجی پروفایل": "📤 Export profile", "📥 وارد کردن پروفایل": "📥 Import profile",
    "➕ قانون جدید": "➕ New rule", "✨ قانون‌های پیشنهادی": "✨ Suggested rules",
    "📦 پشتیبان‌گیری کامل": "📦 Full backup", "♻️ بازیابی از پشتیبان": "♻️ Restore from backup",
    "تغییر خودکار پروفایل بر اساس برنامهٔ فعال (فقط ویندوز)": "Switch profile automatically by active app (Windows/X11)",
    "تطبیق": "Match", "پروفایل": "Profile", "قانون برنامه": "App rule", "تطبیق با:": "Match by:",
    "مقدار:": "Value:", "پروفایل:": "Profile:", "نام پروفایل:": "Profile name:",
    "خودکار (بر اساس برنامهٔ فعال)": "Automatic (by active app)", "نمایش / پنهان کردن پنجره": "Show / hide window",
    "شروع / توقف دوربین": "Start / stop camera", "اجرای دستورها": "Run commands", "درباره": "About", "خروج": "Quit",
    # ---- عمل‌ها ----
    "نام عمل:": "Action name:", "➕ مرحله": "➕ Step", "افزودن نمونهٔ آماده": "Add a ready-made example",
    "مرحلهٔ عمل": "Action step", "نوع مرحله:": "Step type:", "مقدار": "Value",
    "ماوس": "Mouse", "سیستم": "System", "صفحه‌کلید": "Keyboard", "مدیا": "Media", "پیوسته": "Continuous",
    "پاورپوینت": "PowerPoint", "بدون عمل": "No action",
    "حرکت نشانگر ماوس": "Move mouse pointer", "نگه‌داشتن و کشیدن (Drag)": "Hold & drag",
    "اسکرول (دست را بالا/پایین ببرید)": "Scroll (move hand up/down)", "توقف (هیچ کاری نکن)": "Pause (do nothing)",
    "کلیک چپ": "Left click", "کلیک راست": "Right click", "دابل کلیک": "Double click", "کلیک وسط": "Middle click",
    "باز کردن برنامه": "Open program", "باز کردن وب‌سایت": "Open website", "اجرای دستور (Command)": "Run command",
    "نمایش دسکتاپ": "Show desktop", "تعویض پنجره (Alt+Tab)": "Switch window (Alt+Tab)",
    "نمای وظایف (Win+Tab)": "Task view (Win+Tab)", "اسکرین‌شات": "Screenshot",
    "میانبر صفحه‌کلید": "Keyboard shortcut", "تایپ متن": "Type text", "کپی (Ctrl+C)": "Copy (Ctrl+C)",
    "پیست (Ctrl+V)": "Paste (Ctrl+V)", "بازگشت (Ctrl+Z)": "Undo (Ctrl+Z)",
    "پخش / توقف مدیا": "Play / pause media", "آهنگ بعدی": "Next track", "آهنگ قبلی": "Previous track",
    "افزایش صدا": "Volume up", "کاهش صدا": "Volume down", "قطع / وصل صدا": "Mute / unmute",
    "کنترل صدا با بالا/پایین بردن دست": "Volume by moving hand up/down",
    "جلو/عقب ویدیو با حرکت افقی دست": "Seek video by moving hand sideways",
    "زوم با دو دست (Ctrl+اسکرول)": "Zoom with two hands (Ctrl+scroll)",
    "اسلاید بعدی": "Next slide", "اسلاید قبلی": "Previous slide", "پایان نمایش (Esc)": "End show (Esc)",
    "صفحهٔ سیاه (B)": "Black screen (B)", "صفحهٔ سفید (W)": "White screen (W)", "قلم (Ctrl+P)": "Pen (Ctrl+P)",
    "لیزر (Ctrl+L)": "Laser (Ctrl+L)", "پاک‌کن (Ctrl+E)": "Eraser (Ctrl+E)",
    "نشانگر عادی (Ctrl+A)": "Normal pointer (Ctrl+A)", "پاک کردن همهٔ نوشته‌ها (E)": "Clear all ink (E)",
    "شروع نمایش از ابتدا (F5)": "Start show from beginning (F5)",
    "شروع نمایش از اسلاید فعلی (Shift+F5)": "Start from current slide (Shift+F5)",
    "اولین اسلاید (Home)": "First slide (Home)", "آخرین اسلاید (End)": "Last slide (End)",
    "رفتن به اسلاید شمارهٔ …": "Go to slide number …", "نمایش همهٔ اسلایدها (Ctrl+S)": "Show all slides (Ctrl+S)",
    "نمای ارائه‌دهنده (Alt+F5)": "Presenter view (Alt+F5)",
    # ---- ژست‌های آماده ----
    "☝️ اشاره (شست باز)": "☝️ Point (thumb out)", "👉 ماشه (شست بسته)": "👉 Trigger (thumb in)",
    "✌️ دو انگشت": "✌️ Two fingers", "🖖 سه انگشت": "🖖 Three fingers", "🤚 چهار انگشت (شست بسته)": "🤚 Four fingers (thumb in)",
    "🖐️ کف دست باز": "🖐️ Open palm", "✊ مشت": "✊ Fist", "👍 شست بالا": "👍 Thumbs up",
    "🤏 نیشگون": "🤏 Pinch", "👌 اوکی": "👌 OK", "🤟 راک": "🤟 Rock", "🤙 تماس": "🤙 Call",
    "👈 کشیدن دست به چپ": "👈 Swipe left", "👉 کشیدن دست به راست": "👉 Swipe right",
    "👆 کشیدن دست به بالا": "👆 Swipe up", "👇 کشیدن دست به پایین": "👇 Swipe down",
    "نمایش": "Show", "طرز انجام": "How to", "🗑️ حذف همهٔ ژست‌های آماده": "🗑️ Remove all built-in gestures",
    "↩ بازگردانی همه": "↩ Restore all",
    # ---- ژست‌های من ----
    "⭐ ژست ثابت": "⭐ Static gesture", "🌀 ژست متحرک ": "🌀 Motion gesture ", "🔗 ترتیب": "🔗 Sequence",
    "✏️ ویرایش ترتیب": "✏️ Edit sequence", "ژست‌های ثابت (حالت دست):": "Static gestures (hand pose):",
    "ژست‌های متحرک (حرکت دست):": "Motion gestures (hand movement):", "ترتیب ژست‌ها:": "Gesture sequences:",
    "ضبط ژست جدید": "Record new gesture", "ضبط ژست متحرک": "Record motion gesture",
    "نام ژست:": "Gesture name:", "شروع ضبط": "Start recording", "شروع نمونه ۱": "Start sample 1",
    "حالت دست:": "Hand pose:", "با هر حالت دست": "With any hand pose",
    # ---- ظاهر ----
    "🎨 ظاهر برنامه": "🎨 Appearance", "تم:": "Theme:", "تیره": "Dark", "روشن": "Light",
    "نیمه‌شب (مشکی کامل)": "Midnight (pure black)", "رنگ اصلی:": "Accent color:", "رنگ فعلی:": "Current color:",
    "انتخاب رنگ…": "Choose color…", "اندازهٔ نوشته:": "Font size:", "گردی گوشه‌ها:": "Corner radius:",
    "تراکم:": "Density:", "راحت": "Comfortable", "فشرده": "Compact",
    "چیدمان راست‌به‌چپ (فارسی)": "Right-to-left layout", "همیشه روی بقیهٔ پنجره‌ها": "Always on top",
    "بازگشت ظاهر به پیش‌فرض": "Reset appearance",
    "نمایش پیش‌نمایش دوربین (خاموش کردن مصرف CPU را کم می‌کند)": "Show camera preview (turning off saves CPU)",
    # ---- رفتار ----
    "🚀 شروع و پنهان‌سازی": "🚀 Startup & hiding", "اجرای خودکار همراه روشن شدن ویندوز": "Start automatically when the computer starts",
    "شروع به‌صورت پنهان (فقط آیکون کنار ساعت)": "Start hidden (tray icon only)",
    "روشن کردن خودکار دوربین هنگام شروع": "Turn the camera on at startup",
    "با بستن پنجره، به کنار ساعت برود (خروج از منوی آیکون)": "Closing the window minimizes to tray (quit from tray menu)",
    "⌨️ میانبر سراسری (فقط ویندوز)": "⌨️ Global hotkeys", "مکث / ادامهٔ اجرای دستورها:": "Pause / resume commands:",
    "توقف اضطراری (خاموش کردن دوربین):": "Emergency stop (camera off):", "🖥️ مانیتور": "🖥️ Monitor",
    "نشانگر روی:": "Pointer on:", "مانیتور اصلی": "Primary monitor", "همهٔ مانیتورها (یکپارچه)": "All monitors (combined)",
    "🎚️ کنترل پیوسته و دو دست": "🎚️ Continuous & two-hand control",
    "⏱️ کلیک با مکث (بدون حرکت شست)": "⏱️ Dwell click (no thumb movement)",
    "وقتی نشانگر ثابت ماند، خودش کلیک کند": "Click automatically when the pointer rests",
    "مدت ثابت ماندن (ثانیه):": "Rest time (seconds):", "حداکثر لرزش مجاز (پیکسل):": "Max allowed jitter (px):",
    "🔔 بازخورد": "🔔 Feedback",
    # ---- تنظیمات ----
    "📷 دوربین و تشخیص از فاصله": "📷 Camera & long-distance detection", "شمارهٔ دوربین": "Camera index",
    "حساسیت تشخیص (کمتر = دست دورتر را هم می‌بیند)": "Detection sensitivity (lower = sees farther hands)",
    "کیفیت تصویر دوربین:": "Camera quality:", "640×480 — سریع": "640×480 — fast",
    "1280×720 — پیشنهادی برای فاصله": "1280×720 — recommended for distance", "1920×1080 — دورترین، سنگین‌تر": "1920×1080 — farthest, heavier",
    "دقت جستجوی دست در کل تصویر:": "Whole-frame hand search level:", "عادی — سریع": "Normal — fast",
    "دور — پیشنهادی": "Far — recommended", "خیلی دور — دقیق‌تر ولی کندتر هنگام جستجو": "Very far — more precise but slower while searching",
    "بهبود خودکار نور و کنتراست (برای نور کم)": "Auto-enhance light & contrast (low light)",
    "🔍 جستجوی دوربین‌های موجود": "🔍 Find available cameras",
    "🖱️ حرکت، کلیک و ژست‌ها": "🖱️ Movement, clicks & gestures", "نقطهٔ کنترل نشانگر:": "Pointer control point:",
    "ریشهٔ انگشت اشاره (پایدارتر)": "Index base (more stable)", "مفصل میانی اشاره": "Index middle joint",
    "نوک انگشت اشاره (حساس‌تر)": "Index tip (more sensitive)", "نمایش اسکلت دست روی تصویر": "Show hand skeleton on video",
    "🌀 ژست‌های متحرک (حرکت دست)": "🌀 Motion gestures (hand movement)",
    "⚙️ پیشرفته (فقط در صورت اشتباه تشخیص دادن)": "⚙️ Advanced (only if detection is wrong)",
    "بازگشت تنظیمات به پیش‌فرض": "Reset settings",
    "نرمی حرکت نشانگر (بیشتر = نرم‌تر)": "Pointer smoothing (higher = smoother)",
    "ناحیهٔ مرده (پیکسل)": "Dead zone (px)", "هموارسازی دست (کمتر = نرم‌تر)": "Hand smoothing (lower = smoother)",
    "فاصلهٔ بین کلیک‌ها (ثانیه)": "Time between clicks (s)", "فاصلهٔ بین دستورها (ثانیه)": "Time between commands (s)",
    "سرعت اسکرول": "Scroll speed", "تعداد فریم رأی‌گیری ژست": "Gesture voting frames", "حداقل رأی لازم": "Minimum votes",
    "برگشت نشانگر هنگام کلیک (فریم)": "Pointer rewind on click (frames)",
    "حساسیت ژست سفارشی (کمتر = سخت‌گیرتر)": "Custom gesture sensitivity (lower = stricter)",
    # ---- قفل روی دست ----
    "فقط دست من را دنبال کن": "Follow only my hand", "✋ ثبت دست من": "✋ Enroll my hand", "حذف ثبت": "Remove enrollment",
    "وضعیت ثبت:": "Enrollment:", "وضعیت لحظه‌ای:": "Status:", "✅ دست شما ثبت شده است": "✅ Your hand is enrolled",
    "❌ هنوز دستی ثبت نشده": "❌ No hand enrolled yet", "دست مجاز:": "Allowed hand:", "هر دو دست": "Both hands",
    "فقط دست راست": "Right hand only", "فقط دست چپ": "Left hand only",
    "قفل خاموش است": "Lock is off", "قفل شد ✅ — دست شما دنبال می‌شود": "Locked ✅ — following your hand",
    # ---- درباره و کالیبراسیون ----
    "📂 باز کردن پوشهٔ تنظیمات": "📂 Open settings folder", "📋 کپی اطلاعات سیستم": "📋 Copy system info",
    "✅ کپی شد": "✅ Copied", "کالیبراسیون ژست‌ها": "Gesture calibration", "✅ اعمال تنظیمات": "✅ Apply settings",
    "شروع": "Start", "حالت تمرین": "Practice mode", "شروع تمرین": "Start practice", "تمرین دوباره": "Practice again",
    "ژست": "Gesture", "نتیجه": "Result", "زمان": "Time", "اشتباه با": "Confused with",
    "در انتظار تصویر دوربین…": "Waiting for camera image…", "تمام شد 🎉": "Done 🎉",
    "ذخیره‌شد": "Saved", "خطا": "Error", "پشتیبان‌گیری": "Backup", "بازیابی": "Restore",
}


def lang_dir():
    return Path.home() / ".hand_control" / "lang"


def load_dictionary(code):
    """دیکشنری زبان: 'fa' = بدون ترجمه، 'en' = داخلی، بقیه از فایل JSON"""
    if code in ("fa", "", None):
        return {}
    if code == "en":
        return dict(EN)
    p = lang_dir() / f"{code}.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


_STATE = {"dict": {}}


def set_language(code):
    _STATE["dict"] = load_dictionary(code)


def tr(text):
    """ترجمهٔ یک متن (اگر ترجمه نداشت همان متن برمی‌گردد)"""
    return _STATE["dict"].get(text, text)


def translate_tree(root, dictionary=None):
    """همهٔ متن‌های ویجت‌های زیرمجموعهٔ root را ترجمه می‌کند"""
    from PyQt6.QtWidgets import (QAbstractButton, QComboBox, QGroupBox, QLabel,
                                 QLineEdit, QTableWidget, QTabWidget, QWidget)
    d = _STATE["dict"] if dictionary is None else dictionary
    if not d:
        return 0
    n = 0

    def t(s):
        nonlocal n
        r = d.get(s)
        if r is not None and r != s:
            n += 1
            return r
        return s

    widgets = [root] + list(root.findChildren(QWidget))
    for w in widgets:
        if isinstance(w, (QLabel, QAbstractButton)):
            w.setText(t(w.text()))
        if isinstance(w, QGroupBox):
            w.setTitle(t(w.title()))
        if isinstance(w, QTabWidget):
            for i in range(w.count()):
                w.setTabText(i, t(w.tabText(i)))
        if isinstance(w, QTableWidget):
            for c in range(w.columnCount()):
                it = w.horizontalHeaderItem(c)
                if it is not None:
                    it.setText(t(it.text()))
        if isinstance(w, QComboBox):
            for i in range(w.count()):
                w.setItemText(i, t(w.itemText(i)))
        if isinstance(w, QLineEdit):
            w.setPlaceholderText(t(w.placeholderText()))
        tip = w.toolTip()
        if tip:
            w.setToolTip(t(tip))
    if hasattr(root, "windowTitle"):
        root.setWindowTitle(t(root.windowTitle()))
    return n


def collect_strings(root):
    """همهٔ متن‌های فارسی ویجت‌ها برای ساختن فایل ترجمه (کلید = متن فارسی، مقدار = خالی)"""
    from PyQt6.QtWidgets import (QAbstractButton, QComboBox, QGroupBox, QLabel,
                                 QTabWidget, QWidget)
    import re
    found = {}
    fa = re.compile(r"[\u0600-\u06FF]")

    def add(s):
        if s and fa.search(s):
            found.setdefault(s, "")

    for w in [root] + list(root.findChildren(QWidget)):
        if isinstance(w, (QLabel, QAbstractButton)):
            add(w.text())
        if isinstance(w, QGroupBox):
            add(w.title())
        if isinstance(w, QTabWidget):
            for i in range(w.count()):
                add(w.tabText(i))
        if isinstance(w, QComboBox):
            for i in range(w.count()):
                add(w.itemText(i))
        add(w.toolTip())
    for k, v in EN.items():
        found.pop(k, None) if v else None
    return found
