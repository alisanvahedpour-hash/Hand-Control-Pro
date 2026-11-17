# -*- coding: utf-8 -*-
"""
Hand Control Pro - کنترل کامپیوتر با ژست دست (PyQt6)

قابلیت‌ها:
  - جدول ژست‌ها: جدید / ویرایش / حذف / تکرار / فعال و غیرفعال
  - ثبت ژست سفارشی با دوربین (خودتان ژست دلخواه را یاد بدهید)
  - عمل‌ها: ماوس، باز کردن برنامه، باز کردن سایت، میانبر صفحه‌کلید،
    تایپ متن، اجرای دستور، مدیا، دسکتاپ، اسکرین‌شات و ...
  - تنظیمات زنده (نرمی، حساسیت، دوربین و ...) و ذخیرهٔ خودکار
  - میانبرهای پاورپوینت + ژست کشیدن دست (Swipe) برای اسلاید بعدی/قبلی
  - قفل روی دست شما: وقتی چند نفر جلوی دوربین‌اند فقط دست ثبت‌شدهٔ شما دنبال می‌شود

نصب:
  pip install PyQt6 opencv-python mediapipe==0.10.21 pyautogui numpy
  (روی پایتون 3.12 با: pip install numpy==1.26.4 mediapipe==0.10.21 pyautogui PyQt6)

اجرا:
  python hand_control_pro.py
"""

import copy
import json
import math
import pathlib
import random
import os
import re
import shutil
import platform
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from collections import Counter, deque
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
import pyautogui
from PyQt6.QtCore import (QEvent, QObject, QPointF, QRectF, Qt, QThread, QTimer,
                          pyqtSignal)
from PyQt6.QtGui import (QBrush, QColor, QFont, QGuiApplication, QIcon, QImage,
                         QKeySequence, QLinearGradient, QPainter, QPen,
                         QPixmap, QShortcut)
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog,
    QColorDialog, QFrame, QGridLayout, QMenu, QScrollArea, QSystemTrayIcon,
    QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QInputDialog, QKeySequenceEdit, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QProgressBar, QPushButton, QSpinBox, QTableWidget, QTableWidgetItem,
    QTabWidget, QVBoxLayout, QWidget,
)

from hcx import headtrack as hhead
from hcx import i18n
from hcx import integrations as integ
from hcx import learn as hlearn
from hcx import macro as hmacro
from hcx import overlay as ovl
from hcx import remote as hremote
from hcx import updater as hupdate
from hcx import voice as hvoice
from hcx.plugins import PluginManager
from hcx.stats import UsageStats

IS_WIN = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"
if IS_LINUX:
    # OpenCV مسیر افزونه‌های Qt خودش را تنظیم می‌کند و با PyQt6 تداخل دارد
    for _k in ("QT_QPA_PLATFORM_PLUGIN_PATH", "QT_QPA_FONTDIR"):
        os.environ.pop(_k, None)

FRAME_W, FRAME_H = 640, 480
APP_NAME = "Hand Control Pro"
APP_VERSION = "4.0"
CONFIG_DIR = Path.home() / ".hand_control"
CONFIG_FILE = CONFIG_DIR / "config.json"
HOOKS = {"overlay": None}                      # توابعی که رابط کاربری برای ابزار ارائه می‌گذارد
RUNTIME = {"tts": False, "stats": None}        # وضعیت‌های لحظه‌ای مشترک با موتور
PLUGINS = PluginManager(CONFIG_DIR / "plugins")

# ============================ تنظیمات پیش‌فرض ============================
DEFAULT_SETTINGS = {
    "camera_index": 1,
    "cfg_version": 2,
    "margin": 24,
    "edge_pad": 0.12,
    "scan_level": 1,
    "enhance": True,
    "pinch_far": 0.9,
    "sound": False,
    "close_to_tray": False,
    "autostart": False,
    "start_minimized": False,
    "auto_start_camera": False,
    "hotkey_toggle": "ctrl+alt+h",
    "hotkey_stop": "ctrl+alt+q",
    "auto_profile": True,
    "monitor": 0,
    "monitor_rect": None,
    "slider_step": 10,
    "zoom_step": 16,
    "dwell_click": False,
    "dwell_time": 1.0,
    "dwell_radius": 12,
    "language": "fa",
    "head_control": False,
    "head_gain": 2.2,
    "tremor_mode": False,
    "low_power": True,
    "idle_after": 6.0,
    "fatigue_minutes": 20,
    "tts": False,
    "voice_enabled": False,
    "voice_model": "",
    "ha_url": "",
    "ha_token": "",
    "mqtt_host": "",
    "mqtt_port": 1883,
    "mqtt_user": "",
    "mqtt_pass": "",
    "hue_bridge": "",
    "hue_user": "",
    "obs_host": "localhost",
    "obs_port": 4455,
    "obs_pass": "",
    "remote_enabled": False,
    "remote_port": 8765,
    "remote_pin": "",
    "camera_source": "",
    "update_url": "",
    "airkb_scale": 1.0,
    "pointer_landmark": 5,
    "smoothing": 4.0,
    "deadzone": 3,
    "landmark_alpha": 0.55,
    "click_cooldown": 0.35,
    "action_cooldown": 1.5,
    "scroll_speed": 3.0,
    "custom_threshold": 0.25,
    "vote_frames": 5,
    "vote_min": 3,
    "click_rewind": 4,
    "show_landmarks": True,
    "accent": "#6d8bff",
    "font_size": 10,
    "radius": 12,
    "density": "comfortable",
    "ui_rtl": True,
    "show_preview": True,
    "always_on_top": False,
    "motion_start_speed": 1.5,
    "motion_still_time": 0.25,
    "motion_threshold": 0.30,
    "motion_max_time": 2.5,
    "motion_min_len": 1.0,
    "far_mode": True,
    "cam_width": 1280,
    "detect_conf": 0.55,
    "theme": "dark",
    "owner_lock": False,
    "owner_threshold": 0.15,
    "hand_side": "any",
    "min_hand_size": 0,
    "lock_timeout": 1.5,
    "swipe_distance": 0.30,
    "swipe_window": 0.45,
    "swipe_cooldown": 0.9,
    "ext_angle": 150,
    "tuck_on": 0.55,
    "tuck_off": 0.75,
    "pinch_on": 0.30,
    "pinch_off": 0.42,
}

# (کلید، برچسب، نوع، حداقل، حداکثر، گام)
SETTINGS_SPEC = [
    ("smoothing", "نرمی حرکت نشانگر (بیشتر = نرم‌تر)", "float", 1, 15, 0.5),
    ("deadzone", "ناحیهٔ مرده (پیکسل)", "int", 0, 30, 1),
    ("margin", "حاشیهٔ ناحیهٔ فعال (پیکسل؛ 0 = کل تصویر کنترل صفحه است)", "int", 0, 250, 2),
    ("landmark_alpha", "هموارسازی دست (کمتر = نرم‌تر)", "float", 0.1, 1.0, 0.05),
    ("click_cooldown", "فاصلهٔ بین کلیک‌ها (ثانیه)", "float", 0.1, 2.0, 0.05),
    ("action_cooldown", "فاصلهٔ بین دستورها (ثانیه)", "float", 0.3, 5.0, 0.1),
    ("scroll_speed", "سرعت اسکرول", "float", 0.5, 15.0, 0.5),
    ("custom_threshold", "حساسیت ژست سفارشی (کمتر = سخت‌گیرتر)", "float", 0.05, 0.6, 0.01),
    ("vote_frames", "تعداد فریم رأی‌گیری ژست", "int", 2, 12, 1),
    ("vote_min", "حداقل رأی لازم", "int", 1, 12, 1),
    ("click_rewind", "برگشت نشانگر هنگام کلیک (فریم)", "int", 0, 10, 1),
    ("swipe_distance", "مسافت لازم برای کشیدن دست (نسبت به عرض تصویر)", "float", 0.15, 0.7, 0.01),
    ("swipe_window", "حداکثر زمان کشیدن دست (ثانیه)", "float", 0.2, 1.2, 0.05),
    ("swipe_cooldown", "فاصلهٔ بین دو کشیدن (ثانیه)", "float", 0.3, 3.0, 0.1),
]
CAMERA_SPEC = [
    ("camera_index", "شمارهٔ دوربین", "int", 0, 9, 1),
    ("detect_conf", "حساسیت تشخیص (کمتر = دست دورتر را هم می‌بیند)", "float", 0.25, 0.9, 0.05),
    ("edge_pad", "حاشیهٔ مجازی اطراف تصویر (پوشش لبه‌ها؛ 0 = خاموش)", "float", 0.0, 0.30, 0.02),
]
CAM_SIZES = {640: 480, 1280: 720, 1920: 1080}
LW = FRAME_W  # عرض فضای منطقی پردازش (ارتفاع از نسبت تصویر محاسبه می‌شود)

MOTION_SPEC = [
    ("motion_start_speed", "سرعت شروع حرکت (کمتر = حساس‌تر)", "float", 0.5, 6.0, 0.1),
    ("motion_still_time", "مکث پایان حرکت (ثانیه)", "float", 0.1, 1.0, 0.05),
    ("motion_threshold", "سخت‌گیری تطبیق (کمتر = سخت‌گیرتر)", "float", 0.10, 0.80, 0.01),
    ("motion_max_time", "حداکثر مدت یک حرکت (ثانیه)", "float", 0.8, 6.0, 0.1),
    ("motion_min_len", "حداقل طول حرکت (به اندازهٔ کف دست)", "float", 0.3, 5.0, 0.1),
]

ADVANCED_SPEC = [
    ("ext_angle", "زاویهٔ باز بودن انگشت (درجه)", "int", 100, 175, 1),
    ("tuck_on", "آستانهٔ بسته شدن شست (ماشه)", "float", 0.2, 1.0, 0.01),
    ("tuck_off", "آستانهٔ باز شدن شست", "float", 0.3, 1.5, 0.01),
    ("pinch_on", "آستانهٔ شروع نیشگون", "float", 0.1, 0.8, 0.01),
    ("pinch_off", "آستانهٔ پایان نیشگون", "float", 0.1, 1.0, 0.01),
    ("pinch_far", "فاصلهٔ نوک اشاره از مچ برای تشخیص نیشگون (در برابر مشت)", "float", 0.5, 1.3, 0.01),
]

# ============================ ژست‌های آماده ============================
BUILTIN_GESTURES = {
    "point": ("☝️ اشاره (شست باز)", "فقط انگشت اشاره بالا و شست باز (شکل L)"),
    "trigger": ("👉 ماشه (شست بسته)", "مثل ژست اشاره، ولی شست را روی انگشت اشاره ببندید"),
    "peace": ("✌️ دو انگشت", "اشاره و میانی بالا، بقیه بسته"),
    "three": ("🖖 سه انگشت", "اشاره، میانی و حلقه بالا، انگشت کوچک بسته"),
    "four": ("🤚 چهار انگشت (شست بسته)", "چهار انگشت بالا و شست روی کف دست"),
    "palm": ("🖐️ کف دست باز", "هر پنج انگشت کاملاً باز"),
    "fist": ("✊ مشت", "همهٔ انگشت‌ها بسته"),
    "thumbs_up": ("👍 شست بالا", "مشت با شست رو به بالا"),
    "pinch": ("🤏 نیشگون", "شست و اشاره به هم، سه انگشت دیگر بسته"),
    "ok": ("👌 اوکی", "شست و اشاره به هم، سه انگشت دیگر باز"),
    "rock": ("🤟 راک", "اشاره و انگشت کوچک بالا"),
    "call": ("🤙 تماس", "شست و انگشت کوچک باز، بقیه بسته"),
    "swipe_left": ("👈 کشیدن دست به چپ",
                   "کف دست باز را سریع به سمت چپ خودتان تکان دهید"),
    "swipe_right": ("👉 کشیدن دست به راست",
                    "کف دست باز را سریع به سمت راست خودتان تکان دهید"),
    "swipe_up": ("👆 کشیدن دست به بالا",
                 "کف دست باز را سریع به بالا تکان دهید"),
    "swipe_down": ("👇 کشیدن دست به پایین",
                   "کف دست باز را سریع به پایین تکان دهید"),
}

# ============================== عمل‌ها ==============================
# (کلید، برچسب، گروه، نوع پارامتر)
ACTIONS = [
    ("none", "بدون عمل", "—", None),
    ("move_cursor", "حرکت نشانگر ماوس", "ماوس", None),
    ("drag", "نگه‌داشتن و کشیدن (Drag)", "ماوس", None),
    ("scroll", "اسکرول (دست را بالا/پایین ببرید)", "ماوس", None),
    ("pause", "توقف (هیچ کاری نکن)", "ماوس", None),
    ("left_click", "کلیک چپ", "ماوس", None),
    ("right_click", "کلیک راست", "ماوس", None),
    ("double_click", "دابل کلیک", "ماوس", None),
    ("middle_click", "کلیک وسط", "ماوس", None),
    ("open_app", "باز کردن برنامه", "سیستم", "file"),
    ("open_url", "باز کردن وب‌سایت", "سیستم", "text"),
    ("run_command", "اجرای دستور (Command)", "سیستم", "text"),
    ("show_desktop", "نمایش دسکتاپ", "سیستم", None),
    ("alt_tab", "تعویض پنجره (Alt+Tab)", "سیستم", None),
    ("task_view", "نمای وظایف (Win+Tab)", "سیستم", None),
    ("screenshot", "اسکرین‌شات", "سیستم", None),
    ("hotkey", "میانبر صفحه‌کلید", "صفحه‌کلید", "hotkey"),
    ("type_text", "تایپ متن", "صفحه‌کلید", "text"),
    ("copy", "کپی (Ctrl+C)", "صفحه‌کلید", None),
    ("paste", "پیست (Ctrl+V)", "صفحه‌کلید", None),
    ("undo", "بازگشت (Ctrl+Z)", "صفحه‌کلید", None),
    ("ppt_start", "شروع نمایش از ابتدا (F5)", "پاورپوینت", None),
    ("ppt_start_current", "شروع نمایش از اسلاید فعلی (Shift+F5)", "پاورپوینت", None),
    ("ppt_presenter", "نمای ارائه‌دهنده (Alt+F5)", "پاورپوینت", None),
    ("ppt_next", "اسلاید بعدی", "پاورپوینت", None),
    ("ppt_prev", "اسلاید قبلی", "پاورپوینت", None),
    ("ppt_first", "اولین اسلاید (Home)", "پاورپوینت", None),
    ("ppt_last", "آخرین اسلاید (End)", "پاورپوینت", None),
    ("ppt_goto_slide", "رفتن به اسلاید شمارهٔ …", "پاورپوینت", "text"),
    ("ppt_all_slides", "نمایش همهٔ اسلایدها (Ctrl+S)", "پاورپوینت", None),
    ("ppt_black", "صفحهٔ سیاه (B)", "پاورپوینت", None),
    ("ppt_white", "صفحهٔ سفید (W)", "پاورپوینت", None),
    ("ppt_pen", "قلم (Ctrl+P)", "پاورپوینت", None),
    ("ppt_laser", "لیزر (Ctrl+L)", "پاورپوینت", None),
    ("ppt_eraser", "پاک‌کن (Ctrl+E)", "پاورپوینت", None),
    ("ppt_arrow", "نشانگر عادی (Ctrl+A)", "پاورپوینت", None),
    ("ppt_clear_ink", "پاک کردن همهٔ نوشته‌ها (E)", "پاورپوینت", None),
    ("ppt_end", "پایان نمایش (Esc)", "پاورپوینت", None),
    ("http_get", "درخواست وب (GET) — مثلاً چراغ هوشمند", "سیستم", "text"),
    ("http_post", "درخواست وب (POST) — آدرس | متن", "سیستم", "text"),
    ("volume_slider", "کنترل صدا با بالا/پایین بردن دست", "پیوسته", None),
    ("seek_slider", "جلو/عقب ویدیو با حرکت افقی دست", "پیوسته", None),
    ("two_hand_zoom", "زوم با دو دست (Ctrl+اسکرول)", "پیوسته", None),
    ("overlay_laser", "لیزر روی صفحه (روشن/خاموش)", "ابزار ارائه", None),
    ("overlay_draw", "نقاشی روی صفحه (روشن/خاموش)", "ابزار ارائه", None),
    ("overlay_spot", "نورافکن روی صفحه (روشن/خاموش)", "ابزار ارائه", None),
    ("overlay_clear", "پاک کردن نقاشی‌های روی صفحه", "ابزار ارائه", None),
    ("overlay_color", "رنگ بعدی قلم", "ابزار ارائه", None),
    ("overlay_timer", "زمان‌سنج ارائه (شروع/توقف)", "ابزار ارائه", None),
    ("overlay_magnifier", "ذره‌بین ویندوز (روشن/خاموش)", "ابزار ارائه", None),
    ("overlay_pen", "قلم: نقاشی روی صفحه با نگه‌داشتن ژست", "پیوسته", None),
    ("airkb_toggle", "کیبورد هوایی (نمایش/پنهان)", "ابزار ارائه", None),
    ("ha_service", "Home Assistant — دامنه.سرویس [entity] [JSON]", "اتصال‌ها", "text"),
    ("mqtt_publish", "MQTT — موضوع | پیام", "اتصال‌ها", "text"),
    ("hue_light", "Hue — شمارهٔ چراغ on/off/toggle/bri:N", "اتصال‌ها", "text"),
    ("obs_request", "OBS — مثلاً ToggleRecord", "اتصال‌ها", "text"),
    ("speak_text", "گفتن یک متن با صدا", "اتصال‌ها", "text"),
    ("media_play_pause", "پخش / توقف مدیا", "مدیا", None),
    ("media_next", "آهنگ بعدی", "مدیا", None),
    ("media_prev", "آهنگ قبلی", "مدیا", None),
    ("volume_up", "افزایش صدا", "مدیا", None),
    ("volume_down", "کاهش صدا", "مدیا", None),
    ("volume_mute", "قطع / وصل صدا", "مدیا", None),
]
ACTION_INFO = {a[0]: a for a in ACTIONS}
CONTINUOUS = {"none", "move_cursor", "drag", "scroll", "pause",
              "volume_slider", "seek_slider", "two_hand_zoom", "overlay_pen"}
TWO_HAND = {"two_hand_zoom"}
CLICKS = {"left_click", "right_click", "double_click", "middle_click"}


def all_actions(custom_actions=()):
    lst = list(ACTIONS)
    for ca in custom_actions:
        lst.append(("custom:" + ca["id"], ca["name"], "عمل‌های من", None))
    for key, label, kind in PLUGINS.actions:
        lst.append((key, label, "افزونه‌ها", kind))
    return lst


def action_label(key, custom_actions=()):
    for a in all_actions(custom_actions):
        if a[0] == key:
            return f"{a[2]} › {a[1]}"
    return key


def default_bindings():
    def b(name, gesture, action, param="", enabled=True):
        return {"id": uuid.uuid4().hex[:8], "name": name, "gesture": gesture,
                "action": action, "param": param, "enabled": enabled}
    return [
        b("حرکت ماوس", "point", "move_cursor"),
        b("کلیک چپ", "trigger", "left_click"),
        b("کلیک راست", "peace", "right_click"),
        b("کشیدن", "fist", "drag"),
        b("اسکرول", "pinch", "scroll"),
        b("توقف", "palm", "pause"),
        b("دابل کلیک", "ok", "double_click"),
        b("پخش / توقف مدیا", "thumbs_up", "media_play_pause"),
        b("نمایش دسکتاپ", "three", "show_desktop"),
        b("باز کردن Notepad", "rock", "open_app",
          "notepad.exe" if IS_WIN else ""),
    ]


def powerpoint_bindings():
    def b(name, gesture, action, param=""):
        return {"id": uuid.uuid4().hex[:8], "name": name, "gesture": gesture,
                "action": action, "param": param, "enabled": True}
    return [
        b("حرکت ماوس (لیزر)", "point", "move_cursor"),
        b("کلیک چپ", "trigger", "left_click"),
        b("رسم با قلم (کشیدن)", "fist", "drag"),
        b("اسلاید بعدی (✌️)", "peace", "ppt_next"),
        b("اسلاید قبلی (🖖)", "three", "ppt_prev"),
        b("اسلاید بعدی (کشیدن دست به چپ)", "swipe_left", "ppt_next"),
        b("اسلاید قبلی (کشیدن دست به راست)", "swipe_right", "ppt_prev"),
        b("پایان نمایش (کشیدن به بالا)", "swipe_up", "ppt_end"),
        b("شروع از اسلاید فعلی (کشیدن به پایین)", "swipe_down", "ppt_start_current"),
        b("قلم", "rock", "ppt_pen"),
        b("لیزر", "call", "ppt_laser"),
        b("صفحهٔ سیاه", "four", "ppt_black"),
        b("نشانگر عادی", "ok", "ppt_arrow"),
        b("پاک کردن نوشته‌ها", "thumbs_up", "ppt_clear_ink"),
        b("توقف", "palm", "pause"),
    ]


def browser_bindings():
    def b(name, gesture, action, param=""):
        return {"id": uuid.uuid4().hex[:8], "name": name, "gesture": gesture,
                "action": action, "param": param, "enabled": True, "hold": 0}
    return [
        b("حرکت ماوس", "point", "move_cursor"),
        b("کلیک چپ", "trigger", "left_click"),
        b("کلیک راست", "peace", "right_click"),
        b("اسکرول", "pinch", "scroll"),
        b("کشیدن", "fist", "drag"),
        b("توقف", "palm", "pause"),
        b("صفحهٔ قبل (کشیدن به راست)", "swipe_right", "hotkey", "alt+left"),
        b("صفحهٔ بعد (کشیدن به چپ)", "swipe_left", "hotkey", "alt+right"),
        b("رفرش (کشیدن به پایین)", "swipe_down", "hotkey", "f5"),
        b("تب جدید", "thumbs_up", "hotkey", "ctrl+t"),
        b("بستن تب", "call", "hotkey", "ctrl+w"),
        b("بازگرداندن تب بسته", "three", "hotkey", "ctrl+shift+t"),
        b("تب بعدی", "rock", "hotkey", "ctrl+tab"),
        b("زوم با دو دست", "four", "two_hand_zoom"),
    ]


def media_bindings():
    def b(name, gesture, action, param=""):
        return {"id": uuid.uuid4().hex[:8], "name": name, "gesture": gesture,
                "action": action, "param": param, "enabled": True, "hold": 0}
    return [
        b("حرکت ماوس", "point", "move_cursor"),
        b("کلیک چپ", "trigger", "left_click"),
        b("توقف", "palm", "pause"),
        b("صدا با بالا/پایین بردن دست (مشت)", "fist", "volume_slider"),
        b("جلو/عقب ویدیو (دو انگشت)", "peace", "seek_slider"),
        b("پخش / توقف", "thumbs_up", "media_play_pause"),
        b("آهنگ بعدی", "swipe_right", "media_next"),
        b("آهنگ قبلی", "swipe_left", "media_prev"),
        b("صدا بیشتر", "swipe_up", "volume_up"),
        b("صدا کمتر", "swipe_down", "volume_down"),
        b("قطع صدا", "call", "volume_mute"),
    ]


def presenter_bindings():
    def b(name, gesture, action, param=""):
        return {"id": uuid.uuid4().hex[:8], "name": name, "gesture": gesture,
                "action": action, "param": param, "enabled": True, "hold": 0}
    return [
        b("حرکت ماوس", "point", "move_cursor"),
        b("کلیک چپ", "trigger", "left_click"),
        b("نقاشی روی صفحه با قلم (مشت)", "fist", "overlay_pen"),
        b("روشن/خاموش کردن حالت نقاشی", "rock", "overlay_draw"),
        b("لیزر", "call", "overlay_laser"),
        b("نورافکن", "ok", "overlay_spot"),
        b("پاک کردن نقاشی‌ها", "four", "overlay_clear"),
        b("زمان‌سنج", "thumbs_up", "overlay_timer"),
        b("اسلاید بعدی", "peace", "ppt_next"),
        b("اسلاید قبلی", "three", "ppt_prev"),
        b("اسلاید بعدی (کشیدن به چپ)", "swipe_left", "ppt_next"),
        b("اسلاید قبلی (کشیدن به راست)", "swipe_right", "ppt_prev"),
        b("توقف", "palm", "pause"),
    ]


PROFILES = {"default": default_bindings, "powerpoint": powerpoint_bindings,
            "browser": browser_bindings, "media": media_bindings,
            "presenter": presenter_bindings, "empty": lambda: []}
PROFILE_NAMES = {"default": "پیش‌فرض (ماوس)", "powerpoint": "ارائهٔ پاورپوینت 📽️",
                 "browser": "مرورگر 🌐", "media": "پخش‌کننده / رسانه 🎵",
                 "presenter": "ارائه‌دهندهٔ حرفه‌ای (ابزار روی صفحه) 🎤",
                 "empty": "خالی (از صفر)"}


# ============================ ذخیره و بازیابی ============================
CONFIG_MAP = {  # کلید داخلی ← کلید در فایل
    "bindings": "bindings", "customs": "customs", "owner": "owner",
    "actions": "custom_actions", "motions": "motions", "hidden": "hidden_builtin",
    "sequences": "sequences", "profiles": "profiles", "app_rules": "app_rules",
    "voices": "voices",
}


def load_config():
    """برمی‌گرداند: (تنظیمات، دیکشنری داده‌ها)"""
    settings = dict(DEFAULT_SETTINGS)
    data = {"bindings": None, "customs": [], "owner": None, "actions": [],
            "motions": [], "hidden": [], "sequences": [], "profiles": [],
            "app_rules": [], "voices": []}
    try:
        raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        settings.update(raw.get("settings", {}))
        if int(raw.get("settings", {}).get("cfg_version", 1)) < 2:
            settings["margin"] = DEFAULT_SETTINGS["margin"]  # کل تصویر را پوشش بده
        settings["cfg_version"] = 2
        for k, src in CONFIG_MAP.items():
            if src in raw and raw[src] is not None:
                data[k] = raw[src]
    except Exception:
        pass
    if data["bindings"] is None:
        data["bindings"] = default_bindings()
    return settings, data


def save_config(settings, data):
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        out = {"settings": settings}
        for k, dst in CONFIG_MAP.items():
            out[dst] = data.get(k)
        CONFIG_FILE.write_text(json.dumps(out, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    except Exception as e:
        print("ذخیرهٔ تنظیمات ناموفق بود:", e)


# ============================== اجرای عمل‌ها ==============================
KEYMAP = {"meta": "win", "return": "enter", "esc": "esc", "escape": "esc",
          "del": "delete", "ins": "insert", "pgup": "pageup",
          "pgdown": "pagedown", "control": "ctrl", "plus": "+",
          "print": "printscreen", "sysreq": "printscreen"}


def qt_seq_to_text(seq_str):
    chord = seq_str.split(", ")[0]
    if chord.endswith("++"):
        chord = chord[:-2] + "+plus"
    return "+".join(p.strip().lower() for p in chord.split("+") if p.strip())


def press_hotkey(*keys):
    try:
        pyautogui.hotkey(*keys)
    except Exception as e:
        print("میانبر ناموفق بود:", keys, e)


def open_app(path):
    if not path:
        return
    if IS_WIN:
        try:
            os.startfile(path)  # noqa
        except OSError:
            subprocess.Popen(path, shell=True)
    elif IS_MAC:
        subprocess.Popen(["open", path] if os.path.exists(path)
                         else ["open", "-a", path])
    else:
        p_ = os.path.expanduser(path)
        if os.path.isdir(p_) or (os.path.isfile(p_) and not os.access(p_, os.X_OK)):
            subprocess.Popen(["xdg-open", p_])
        else:
            import shlex
            subprocess.Popen(shlex.split(p_))


def paste_text(text):
    try:
        import pyperclip
        pyperclip.copy(text)
        press_hotkey("command" if IS_MAC else "ctrl", "v")
    except Exception as e:
        print("تایپ متن ناموفق بود:", e)


# ------------------------- عمل‌های ساخته‌شده توسط کاربر -------------------------
CUSTOM_ACTIONS = {}          # کلید "custom:<id>" ← لیست مرحله‌ها
_macro_lock = threading.Lock()

STEP_TYPES = [
    ("hotkey", "میانبر صفحه‌کلید (مثل alt+f4)", "hotkey"),
    ("key", "فشردن یک کلید (مثل enter)", "text"),
    ("type_text", "تایپ متن", "text"),
    ("open_app", "باز کردن برنامه", "file"),
    ("open_url", "باز کردن وب‌سایت", "text"),
    ("run_command", "اجرای دستور", "text"),
    ("http_get", "درخواست وب (GET)", "text"),
    ("http_post", "درخواست وب (POST): آدرس | متن", "text"),
    ("click_at", "کلیک در نقطه (x,y,left)", "text"),
    ("move_to", "رفتن نشانگر به (x,y)", "text"),
    ("ha_service", "Home Assistant", "text"),
    ("mqtt_publish", "MQTT", "text"),
    ("hue_light", "Hue", "text"),
    ("obs_request", "OBS", "text"),
    ("speak_text", "گفتن متن با صدا", "text"),
    ("left_click", "کلیک چپ", None),
    ("right_click", "کلیک راست", None),
    ("double_click", "دابل کلیک", None),
    ("middle_click", "کلیک وسط", None),
    ("scroll", "اسکرول (عدد مثبت = بالا، منفی = پایین)", "text"),
    ("wait", "صبر (میلی‌ثانیه)", "text"),
    ("run_action", "اجرای یک عمل آماده", "action"),
]
STEP_INFO = {t[0]: t for t in STEP_TYPES}

POPULAR_HOTKEYS = [
    ("بستن پنجره (Alt+F4)", "alt+f4"),
    ("تعویض پنجره (Alt+Tab)", "alt+tab"),
    ("نمایش دسکتاپ (Win+D)", "win+d"),
    ("بستن تب (Ctrl+W)", "ctrl+w"),
    ("تب جدید (Ctrl+T)", "ctrl+t"),
    ("بازگرداندن تب بسته (Ctrl+Shift+T)", "ctrl+shift+t"),
    ("ذخیره (Ctrl+S)", "ctrl+s"),
    ("بازگشت (Ctrl+Z)", "ctrl+z"),
    ("تمام‌صفحه (F11)", "f11"),
    ("رفرش (F5)", "f5"),
    ("Escape", "esc"),
    ("اسکرین‌شات ناحیه (Win+Shift+S)", "win+shift+s"),
    ("قفل ویندوز (Win+L)", "win+l"),
    ("مدیریت وظایف (Ctrl+Shift+Esc)", "ctrl+shift+esc"),
]

PRESET_ACTIONS = [
    ("بستن پنجره (Alt+F4)", [{"type": "hotkey", "param": "alt+f4"}]),
    ("بستن تب مرورگر (Ctrl+W)", [{"type": "hotkey", "param": "ctrl+w"}]),
    ("تب جدید (Ctrl+T)", [{"type": "hotkey", "param": "ctrl+t"}]),
    ("بازگرداندن تب بسته (Ctrl+Shift+T)", [{"type": "hotkey", "param": "ctrl+shift+t"}]),
    ("اسکرین‌شات ناحیه (Win+Shift+S)", [{"type": "hotkey", "param": "win+shift+s"}]),
    ("قفل کردن ویندوز (Win+L)", [{"type": "hotkey", "param": "win+l"}]),
    ("ذخیره (Ctrl+S)", [{"type": "hotkey", "param": "ctrl+s"}]),
    ("بازگشت مرورگر (Alt+Left)", [{"type": "hotkey", "param": "alt+left"}]),
    ("پیشروی مرورگر (Alt+Right)", [{"type": "hotkey", "param": "alt+right"}]),
    ("تمام‌صفحه (F11)", [{"type": "key", "param": "f11"}]),
]


CUSTOM_NAMES = {}


def set_custom_actions(actions):
    CUSTOM_ACTIONS.clear()
    CUSTOM_NAMES.clear()
    for a in actions or []:
        key = "custom:" + a["id"]
        CUSTOM_ACTIONS[key] = {"steps": list(a.get("steps", [])),
                               "only_if": a.get("only_if", ""),
                               "repeat": int(a.get("repeat", 1) or 1)}
        CUSTOM_NAMES[key] = a.get("name", "")


def step_summary(st):
    info = STEP_INFO.get(st.get("type"))
    label = info[1].split(" (")[0] if info else str(st.get("type"))
    p = str(st.get("param", "")).strip()
    return f"{label}: {p}" if p else label


def run_step(st):
    t = st.get("type")
    p = str(st.get("param", "")).strip()
    try:
        if t == "wait":
            time.sleep(max(0.0, float(p or 0)) / 1000.0)
        elif t == "key":
            pyautogui.press(KEYMAP.get(p.lower(), p.lower()))
        elif t == "scroll":
            pyautogui.scroll(int(float(p or 0)))
        elif t == "run_action":
            if p and not p.startswith("custom:"):
                run_action(p, track=False)
        else:
            run_action(t, p, track=False)
    except Exception as e:
        print("خطا در مرحلهٔ عمل:", t, e)


def app_matches(spec, exe, title):
    """شرط «فقط وقتی این برنامه فعال است»: exe:chrome ، title:Docs یا فقط نام برنامه"""
    spec = (spec or "").strip().lower()
    if not spec:
        return True
    if spec.startswith("title:"):
        return spec[6:].strip() in (title or "").lower()
    name = spec[4:] if spec.startswith("exe:") else spec
    return (exe or "").replace(".exe", "") == name.strip().replace(".exe", "")


def run_macro(steps, only_if="", repeat=1):
    """اجرای مرحله‌های یک عمل در نخ جدا (تا تشخیص دست متوقف نشود)"""
    def work():
        if not _macro_lock.acquire(blocking=False):
            return
        try:
            if only_if:
                exe, title = get_active_app()
                if (exe or title) and not app_matches(only_if, exe, title):
                    return
            for _ in range(max(1, min(int(repeat or 1), 50))):
                for st in steps:
                    run_step(st)
        finally:
            _macro_lock.release()
    threading.Thread(target=work, daemon=True).start()


def media_key(name):
    """کلید رسانه؛ در لینوکس اگر pactl / playerctl نصب باشد از آن‌ها استفاده می‌شود"""
    if IS_LINUX:
        cmds = {"volumeup": ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+3%"],
                "volumedown": ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-3%"],
                "volumemute": ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"],
                "playpause": ["playerctl", "play-pause"],
                "nexttrack": ["playerctl", "next"],
                "prevtrack": ["playerctl", "previous"]}
        cmd = cmds.get(name)
        if cmd and shutil.which(cmd[0]):
            try:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
                return
            except Exception:
                pass
    pyautogui.press(name)


def linux_screenshot():
    for cmd in (["flameshot", "gui"], ["gnome-screenshot", "-a"],
                ["spectacle", "-r"], ["xfce4-screenshooter", "-r"]):
        if shutil.which(cmd[0]):
            subprocess.Popen(cmd)
            return
    pyautogui.screenshot(str(Path.home() / "screenshot.png"))


def action_speech(action):
    if action in CUSTOM_NAMES:
        return CUSTOM_NAMES[action]
    for a in ACTIONS:
        if a[0] == action:
            return a[1].split(" (")[0].split(" — ")[0]
    return action


def type_char(ch):
    """تایپ یک نویسه (غیر لاتین با کلیپ‌بورد)"""
    if ch.isascii():
        pyautogui.write(ch)
    else:
        paste_text(ch)


def press_special(name):
    pyautogui.press({"Space": "space", "Enter": "enter", "⌫": "backspace"}.get(name, name))


DANGEROUS_HOTKEYS = {"alt+f4", "win+l", "ctrl+alt+delete", "ctrl+shift+esc"}


def is_dangerous(action, param, custom_actions=()):
    def hk(a, p):
        return a == "hotkey" and (p or "").lower().replace(" ", "") in DANGEROUS_HOTKEYS
    if hk(action, param):
        return True
    if action.startswith("custom:"):
        for ca in custom_actions:
            if "custom:" + ca["id"] == action:
                return any(hk(s_.get("type"), s_.get("param")) for s_ in ca.get("steps", []))
    return False


def apply_tremor(cfg):
    """حالت لرزش دست: هموارسازی قوی‌تر، ناحیهٔ مردهٔ بزرگ‌تر و کلیک با مکث طولانی‌تر"""
    if cfg.get("tremor_mode"):
        cfg["landmark_alpha"] = min(cfg["landmark_alpha"], 0.25)
        cfg["smoothing"] = max(cfg["smoothing"], 8.0)
        cfg["deadzone"] = max(cfg["deadzone"], 6)
        cfg["vote_frames"] = max(int(cfg["vote_frames"]), 5)
        cfg["vote_min"] = min(max(int(cfg["vote_min"]), 4), cfg["vote_frames"])
        cfg["dwell_time"] = max(cfg["dwell_time"], 1.4)
        cfg["dwell_radius"] = max(cfg["dwell_radius"], 22)
        cfg["click_cooldown"] = max(cfg["click_cooldown"], 0.6)
    return cfg


def _after_action(action):
    stats = RUNTIME.get("stats")
    if stats is not None:
        stats.action(action)
    if RUNTIME.get("tts"):
        integ.speak(action_speech(action))


def run_action(action, param="", track=True):
    p = (param or "").strip()
    if track:
        _after_action(action)
    try:
        if action.startswith("custom:"):
            ca = CUSTOM_ACTIONS.get(action)
            if ca and ca["steps"]:
                run_macro(ca["steps"], ca["only_if"], ca["repeat"])
        elif action == "left_click":
            pyautogui.click()
        elif action == "right_click":
            pyautogui.rightClick()
        elif action == "double_click":
            pyautogui.doubleClick()
        elif action == "middle_click":
            pyautogui.middleClick()
        elif action == "open_app":
            open_app(p)
        elif action == "open_url":
            if p:
                webbrowser.open(p if "://" in p else "https://" + p)
        elif action == "run_command":
            if p:
                subprocess.Popen(p, shell=True)
        elif action == "http_get":
            if p:
                http_request("GET", p)
        elif action == "http_post":
            if p:
                http_request("POST", p)
        elif action.startswith("overlay_") or action == "airkb_toggle":
            hook = HOOKS.get("overlay")
            if hook:
                hook(action)
        elif action == "ha_service":
            integ.ha_call(p)
        elif action == "mqtt_publish":
            integ.mqtt_publish(p)
        elif action == "hue_light":
            integ.hue_light(p)
        elif action == "obs_request":
            integ.obs_request(p)
        elif action == "speak_text":
            integ.speak(p)
        elif action == "click_at":
            x_, y_, *btn = [t.strip() for t in p.split(",")]
            pyautogui.click(int(x_), int(y_), button=(btn[0] if btn else "left"))
        elif action == "move_to":
            x_, y_ = [int(t) for t in p.split(",")[:2]]
            pyautogui.moveTo(x_, y_)
        elif action.startswith("plugin:"):
            PLUGINS.run(action, p)
        elif action == "hotkey":
            keys = [KEYMAP.get(k, k) for k in
                    p.lower().replace(" ", "").split("+") if k]
            if keys:
                press_hotkey(*keys)
        elif action == "type_text":
            if p:
                paste_text(p)
        elif action == "show_desktop":
            if IS_WIN:
                press_hotkey("win", "d")
            elif IS_MAC:
                press_hotkey("fn", "f11")
            else:
                press_hotkey("winleft", "d")
        elif action == "alt_tab":
            press_hotkey("alt", "tab")
        elif action == "task_view":
            press_hotkey("winleft" if IS_LINUX else "win", "tab")
        elif action == "screenshot":
            if IS_WIN:
                press_hotkey("win", "shift", "s")
            elif IS_MAC:
                press_hotkey("command", "shift", "4")
            else:
                linux_screenshot()
        elif action == "copy":
            press_hotkey("command" if IS_MAC else "ctrl", "c")
        elif action == "paste":
            press_hotkey("command" if IS_MAC else "ctrl", "v")
        elif action == "undo":
            press_hotkey("command" if IS_MAC else "ctrl", "z")
        elif action == "ppt_start":
            pyautogui.press("f5")
        elif action == "ppt_start_current":
            press_hotkey("shift", "f5")
        elif action == "ppt_presenter":
            press_hotkey("alt", "f5")
        elif action == "ppt_next":
            pyautogui.press("pagedown")
        elif action == "ppt_prev":
            pyautogui.press("pageup")
        elif action == "ppt_first":
            pyautogui.press("home")
        elif action == "ppt_last":
            pyautogui.press("end")
        elif action == "ppt_goto_slide":
            num = "".join(ch for ch in p if ch.isdigit())
            if num:
                pyautogui.write(num)
                pyautogui.press("enter")
        elif action == "ppt_all_slides":
            press_hotkey("ctrl", "s")
        elif action == "ppt_black":
            pyautogui.press("b")
        elif action == "ppt_white":
            pyautogui.press("w")
        elif action == "ppt_pen":
            press_hotkey("ctrl", "p")
        elif action == "ppt_laser":
            press_hotkey("ctrl", "l")
        elif action == "ppt_eraser":
            press_hotkey("ctrl", "e")
        elif action == "ppt_arrow":
            press_hotkey("ctrl", "a")
        elif action == "ppt_clear_ink":
            pyautogui.press("e")
        elif action == "ppt_end":
            pyautogui.press("esc")
        elif action == "media_play_pause":
            media_key("playpause")
        elif action == "media_next":
            media_key("nexttrack")
        elif action == "media_prev":
            media_key("prevtrack")
        elif action == "volume_up":
            media_key("volumeup")
        elif action == "volume_down":
            media_key("volumedown")
        elif action == "volume_mute":
            media_key("volumemute")
    except Exception as e:
        print("خطا در اجرای عمل", action, ":", e)


# ============================== تشخیص ژست ==============================
def d(a, b):
    return float(np.linalg.norm(a - b))


def angle(a, b, c):
    v1, v2 = a - b, c - b
    cosv = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-9)
    return math.degrees(math.acos(float(np.clip(cosv, -1, 1))))


FINGERS = {"index": (5, 6, 8), "middle": (9, 10, 12),
           "ring": (13, 14, 16), "pinky": (17, 18, 20)}


def pose_vector(pts):
    """بردار نرمال‌شدهٔ حالت دست (مستقل از موقعیت و اندازه)"""
    palm = d(pts[0], pts[9]) + 1e-6
    return ((pts - pts[0]) / palm)[1:].flatten()


def pose_distance(a, b):
    diff = (np.asarray(a) - np.asarray(b)).reshape(-1, 2)
    return float(np.mean(np.linalg.norm(diff, axis=1)))


# طول استخوان‌های دست (از مختصات سه‌بعدی واقعی MediaPipe) = «امضای شکل دست»
BONES = [(1, 2), (2, 3), (3, 4), (5, 6), (6, 7), (7, 8), (9, 10), (10, 11),
         (11, 12), (13, 14), (14, 15), (15, 16), (17, 18), (18, 19), (19, 20),
         (5, 9), (9, 13), (13, 17), (0, 5), (0, 17)]


def hand_signature(world):
    """نسبت طول استخوان‌ها به طول کف دست (مستقل از فاصله از دوربین)"""
    w = np.array([[l.x, l.y, l.z] for l in world.landmark])
    ref = float(np.linalg.norm(w[0] - w[9])) + 1e-9
    return np.array([np.linalg.norm(w[a] - w[b]) for a, b in BONES]) / ref


def sig_distance(a, b):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return float(np.mean(np.abs(a - b) / (np.abs(b) + 1e-6)))


class GestureClassifier:
    def __init__(self):
        self.thumb_tucked = False
        self.pinching = False
        self.info = {}

    def __call__(self, p, c):
        palm = d(p[0], p[9]) + 1e-6
        ang = {n: angle(p[m], p[pp], p[t]) for n, (m, pp, t) in FINGERS.items()}
        ext = {n: a_ > c["ext_angle"] for n, a_ in ang.items()}
        index, middle = ext["index"], ext["middle"]
        ring, pinky = ext["ring"], ext["pinky"]
        others = middle or ring or pinky
        four = index and middle and ring and pinky

        thumb_ratio = d(p[4], p[5]) / palm
        if self.thumb_tucked:
            if thumb_ratio > c["tuck_off"]:
                self.thumb_tucked = False
        elif thumb_ratio < c["tuck_on"]:
            self.thumb_tucked = True
        thumb_open = not self.thumb_tucked

        pinch_ratio = d(p[4], p[8]) / palm
        # در مشت، نوک اشاره نزدیک مچ است؛ در نیشگون واقعی دورتر است
        far_v = d(p[8], p[0]) / palm
        index_far = far_v > c.get("pinch_far", 0.9)
        if self.pinching:
            if pinch_ratio > c["pinch_off"] or not index_far:
                self.pinching = False
        elif pinch_ratio < c["pinch_on"] and index_far:
            self.pinching = True

        thumb_up = (thumb_open and p[4][1] < p[3][1]
                    and p[4][1] < p[5][1] - 0.2 * palm)

        self.info = {
            "fingers": "".join(k[0].upper() if v else k[0]
                               for k, v in ext.items()),
            "thumb": f"{thumb_ratio:.2f}",
            "pinch": f"{pinch_ratio:.2f}",
            "angles": list(ang.values()),
            "thumb_v": float(thumb_ratio),
            "pinch_v": float(pinch_ratio),
            "far_v": float(far_v),
        }

        if self.pinching and middle and ring and pinky:
            return "ok"
        if four and thumb_open:
            return "palm"
        if four:
            return "four"
        if self.pinching and not others:
            return "pinch"
        if index and middle and not ring and not pinky:
            return "peace"
        if index and middle and ring and not pinky:
            return "three"
        if index and pinky and not middle and not ring:
            return "rock"
        if pinky and not (index or middle or ring) and thumb_open:
            return "call"
        if index and not others:
            return "point" if thumb_open else "trigger"
        if not (index or middle or ring or pinky):
            return "thumbs_up" if thumb_up else "fist"
        return "none"


# ============================== موتور دوربین ==============================
def open_camera(idx):
    if isinstance(idx, str) and not idx.strip().isdigit():
        cap = cv2.VideoCapture(idx.strip())          # آدرس RTSP / HTTP (گوشی)
    elif IS_WIN:
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
    elif IS_LINUX:
        cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
    else:
        cap = cv2.VideoCapture(idx)
    return cap if cap.isOpened() else None


def make_roi(pts_px, fw, fh, factor=2.4, min_frac=0.30):
    """ناحیهٔ مربعی اطراف دست برای بزرگ‌نمایی (pts_px: نقاط دست به پیکسل تصویر کامل)"""
    x0, y0 = pts_px.min(axis=0)
    x1, y1 = pts_px.max(axis=0)
    side = max(x1 - x0, y1 - y0) * factor
    side = max(side, min_frac * fh)
    side = min(side, fh, fw)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    bx = int(np.clip(cx - side / 2, 0, fw - side))
    by = int(np.clip(cy - side / 2, 0, fh - side))
    sd = int(side)
    return (bx, by, bx + sd, by + sd)


SCAN_FACTORS = [0.62, 0.45, 0.34]


def scan_tiles(fw, fh, level=0):
    """نواحی هم‌پوشان که کل تصویر را می‌پوشانند؛ نواحی نزدیک مرکز اول جستجو می‌شوند"""
    side = max(int(min(fw, fh) * SCAN_FACTORS[max(0, min(level, 2))]), 32)
    step = max(int(side * 0.6), 1)

    def positions(total):
        if total <= side:
            return [0]
        pos = list(range(0, total - side, step))
        if not pos or (total - side) - pos[-1] > step * 0.35:
            pos.append(total - side)
        else:
            pos[-1] = total - side
        return pos

    tiles = [(x, y, x + side, y + side)
             for y in positions(fh) for x in positions(fw)]
    cx, cy = fw / 2.0, fh / 2.0
    tiles.sort(key=lambda t: (t[0] + side / 2 - cx) ** 2 + (t[1] + side / 2 - cy) ** 2)
    return tiles


def grow_box(box, factor, pw, ph):
    """بزرگ‌کردن یک ناحیهٔ مربعی حول مرکزش (داخل تصویر)"""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    side = min((x1 - x0) * factor, pw, ph)
    bx = int(np.clip(cx - side / 2, 0, pw - side))
    by = int(np.clip(cy - side / 2, 0, ph - side))
    return (bx, by, bx + int(side), by + int(side))


def enhance_image(rgb, clahe):
    """بهبود نور و کنتراست (فقط برای تشخیص، نه نمایش)"""
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)


def plausible_hand(p):
    """رد تشخیص‌های اشتباه: نسبت اندازهٔ انگشت و پهنای کف دست باید شبیه دست واقعی باشد"""
    palm = d(p[0], p[9])
    if palm < 3:
        return False
    finger = d(p[9], p[10]) + d(p[10], p[11]) + d(p[11], p[12])
    width = d(p[5], p[17])
    return 0.3 < finger / palm < 2.5 and 0.2 < width / palm < 1.8


def dedupe_hands(cands):
    """حذف دست‌های تکراری که از دو ناحیهٔ هم‌پوشان پیدا شده‌اند"""
    out = []
    for c in sorted(cands, key=lambda c: -c["palm"]):
        if all(d(c["pts"][0], o["pts"][0]) > 0.5 * max(c["palm"], o["palm"], 1.0)
               for o in out):
            out.append(c)
    return out


def system_info():
    try:
        from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
        qt = f"PyQt6 {PYQT_VERSION_STR} / Qt {QT_VERSION_STR}"
    except Exception:
        qt = "PyQt6"
    return "\n".join([
        f"{APP_NAME} {APP_VERSION}",
        f"Python {platform.python_version()} — {platform.system()} {platform.release()}",
        f"OpenCV {getattr(cv2, '__version__', '?')}",
        f"MediaPipe {getattr(mp, '__version__', '?')}",
        f"NumPy {np.__version__}",
        qt,
        f"Config: {CONFIG_FILE}",
    ])


def run_hands(hands, rgb, box, out_side=512):
    """تشخیص روی یک ناحیه؛ ناحیه‌های کوچک بزرگ‌نمایی می‌شوند"""
    x0, y0, x1, y1 = box
    crop = rgb[y0:y1, x0:x1]
    ch, cw = crop.shape[:2]
    if 0 < max(cw, ch) < out_side:
        k = out_side / float(max(cw, ch))
        crop = cv2.resize(crop, (int(cw * k), int(ch * k)),
                          interpolation=cv2.INTER_LANCZOS4)
    return hands.process(np.ascontiguousarray(crop))


def extract_hands(result, box, scale, offset=0.0):
    """تبدیل خروجی MediaPipe به دست‌ها در فضای منطقی (box = ناحیهٔ پردازش‌شده به px)"""
    out = []
    if result is None or not result.multi_hand_landmarks:
        return out
    cw, ch = box[2] - box[0], box[3] - box[1]
    worlds = result.multi_hand_world_landmarks or []
    sides = result.multi_handedness or []
    for i, hl in enumerate(result.multi_hand_landmarks):
        world = worlds[i] if i < len(worlds) else None
        label = (sides[i].classification[0].label.lower()
                 if i < len(sides) else "?")
        full = np.array([[box[0] + l.x * cw, box[1] + l.y * ch]
                         for l in hl.landmark])
        p = (full - offset) * scale
        out.append({"world": world, "label": label, "pts": p,
                    "palm": d(p[0], p[9])})
    return out


def draw_hand(img, pts, line_color, dot_color=(255, 255, 255)):
    for a, b in mp.solutions.hands.HAND_CONNECTIONS:
        cv2.line(img, (int(pts[a][0]), int(pts[a][1])),
                 (int(pts[b][0]), int(pts[b][1])), line_color, 2)
    for p in pts:
        cv2.circle(img, (int(p[0]), int(p[1])), 3, dot_color, -1)


# ------------------------- ژست‌های متحرک (مسیر حرکت دست) -------------------------
MOTION_N = 32


def path_length(pts):
    pts = np.asarray(pts, dtype=float)
    if len(pts) < 2:
        return 0.0
    return float(np.sum(np.linalg.norm(np.diff(pts, axis=0), axis=1)))


def resample_path(pts, n=MOTION_N):
    pts = np.asarray(pts, dtype=float)
    if len(pts) < 2:
        return None
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    total = float(seg.sum())
    if total < 1e-6:
        return None
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    targets = np.linspace(0.0, total, n)
    return np.stack([np.interp(targets, cum, pts[:, 0]),
                     np.interp(targets, cum, pts[:, 1])], axis=1)


def normalize_path(path):
    p = np.asarray(path, dtype=float)
    p = p - p.mean(axis=0)
    size = max(float(np.ptp(p[:, 0])), float(np.ptp(p[:, 1])), 1e-6)
    return p / size


def path_distance(a, b):
    return float(np.mean(np.linalg.norm(np.asarray(a) - np.asarray(b), axis=1)))


class MotionDetector:
    """تشخیص شروع و پایان یک حرکت سریع دست و برگرداندن مسیر آن"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.last = None
        self.speed = 0.0
        self.pre = deque(maxlen=8)
        self.moving = False
        self.buf = []
        self.start_t = 0.0
        self.still_since = None

    def _end(self):
        self.moving = False
        self.buf = []
        self.still_since = None
        self.pre.clear()
        self.speed = 0.0

    def feed(self, t, x, y, pose, palm, cfg):
        """ورودی هر فریم؛ هنگام پایان یک حرکت لیست (t,x,y,pose,palm) برمی‌گرداند"""
        rec = (t, float(x), float(y), pose, float(palm))
        if self.last is None:
            self.last = (t, x, y)
            self.pre.append(rec)
            return None
        lt, lx, ly = self.last
        dt = max(t - lt, 1e-3)
        inst = math.hypot(x - lx, y - ly) / dt / max(palm, 1.0)
        self.speed = 0.6 * self.speed + 0.4 * inst
        self.last = (t, x, y)

        if not self.moving:
            self.pre.append(rec)
            if self.speed > cfg["motion_start_speed"]:
                self.moving = True
                self.buf = list(self.pre)
                self.start_t = self.buf[0][0]
                self.still_since = None
            return None

        self.buf.append(rec)
        if t - self.start_t > cfg["motion_max_time"]:
            self._end()
            return None
        if self.speed < cfg["motion_start_speed"] * 0.5:
            if self.still_since is None:
                self.still_since = t
            if t - self.still_since >= cfg["motion_still_time"]:
                seg = [r for r in self.buf if r[0] <= self.still_since]
                self._end()
                return seg
        else:
            self.still_since = None
        return None


def segment_from_samples(samples, cfg):
    """از نمونه‌های ضبط‌شده، بلندترین حرکت را جدا می‌کند"""
    det = MotionDetector()
    best = None
    for r in samples:
        seg = det.feed(r[0], r[1], r[2], r[3], r[4], cfg)
        if seg is not None and (best is None or len(seg) > len(best)):
            best = seg
    if det.moving and len(det.buf) > (len(best) if best else 0):
        best = list(det.buf)
    return best


def motion_template(seg):
    """(مسیر نرمال‌شده، حالت غالب دست، سهم آن) از یک حرکت؛ در صورت نامعتبر بودن None"""
    if not seg or len(seg) < 6:
        return None
    pts = np.array([[r[1], r[2]] for r in seg])
    palm = float(np.mean([r[4] for r in seg]))
    if path_length(pts) < 0.8 * max(palm, 1.0):
        return None
    path = resample_path(pts)
    if path is None:
        return None
    poses = [r[3] for r in seg]
    major, cnt = Counter(poses).most_common(1)[0]
    return normalize_path(path), major, cnt / len(poses)


def match_motion(seg, motions, cfg):
    """تطبیق یک حرکت با ژست‌های متحرک ثبت‌شده؛ (کلید، فاصله) یا None"""
    if not seg or len(seg) < 6:
        return None
    pts = np.array([[r[1], r[2]] for r in seg])
    palm = float(np.mean([r[4] for r in seg]))
    if path_length(pts) < cfg["motion_min_len"] * max(palm, 1.0):
        return None
    path = resample_path(pts)
    if path is None:
        return None
    norm = normalize_path(path)
    poses = [r[3] for r in seg]
    major, cnt = Counter(poses).most_common(1)[0]
    share = cnt / len(poses)
    best = None
    for m in motions:
        if m["pose"] != "any" and not (major == m["pose"] and share >= 0.6):
            continue
        dd = min(path_distance(norm, t) for t in m["templates"])
        if best is None or dd < best[1]:
            best = (m["key"], dd)
    if best and best[1] < cfg["motion_threshold"]:
        return best
    return None


# ------------------------- ابزارهای سیستمی -------------------------
_last_sound = {"t": 0.0}


def play_sound(kind):
    """صدای کوتاه بازخورد (ویندوز و لینوکس، بدون متوقف کردن برنامه)"""
    if not (IS_WIN or IS_LINUX):
        return
    now = time.time()
    if now - _last_sound["t"] < 0.08:
        return
    _last_sound["t"] = now
    f, ms = {"click": (1200, 30), "action": (900, 60), "lock": (1500, 90),
             "unlock": (500, 90), "pause": (400, 80)}.get(kind, (900, 50))

    def work():
        try:
            if IS_WIN:
                import winsound
                winsound.Beep(f, ms)
            else:
                snd = "/usr/share/sounds/freedesktop/stereo/bell.oga"
                if shutil.which("paplay") and os.path.exists(snd):
                    subprocess.run(["paplay", snd], timeout=2,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif shutil.which("canberra-gtk-play"):
                    subprocess.run(["canberra-gtk-play", "-i", "bell"], timeout=2,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
    threading.Thread(target=work, daemon=True).start()


def linux_active_app():
    """(نام فرایند پنجرهٔ فعال، عنوان) با xprop — فقط X11"""
    if not shutil.which("xprop"):
        return "", ""
    try:
        out = subprocess.run(["xprop", "-root", "_NET_ACTIVE_WINDOW"],
                             capture_output=True, text=True, timeout=1).stdout
        m = re.search(r"0x[0-9a-fA-F]+", out)
        if not m or int(m.group(0), 16) == 0:
            return "", ""
        info = subprocess.run(
            ["xprop", "-id", m.group(0), "_NET_WM_PID", "_NET_WM_NAME", "WM_NAME"],
            capture_output=True, text=True, timeout=1).stdout
        pid = re.search(r"_NET_WM_PID\(CARDINAL\) = (\d+)", info)
        title = (re.search(r'_NET_WM_NAME\(UTF8_STRING\) = "(.*)"', info)
                 or re.search(r'WM_NAME\(\w+\) = "(.*)"', info))
        exe = ""
        if pid:
            try:
                exe = pathlib.Path(f"/proc/{pid.group(1)}/comm").read_text().strip().lower()
            except Exception:
                pass
        return exe, (title.group(1) if title else "")
    except Exception:
        return "", ""


def get_active_app():
    """(نام برنامهٔ فعال، عنوان پنجره) — ویندوز و لینوکس (X11)"""
    if IS_LINUX:
        return linux_active_app()
    if not IS_WIN:
        return "", ""
    try:
        import ctypes
        from ctypes import wintypes
        user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
        user32.GetForegroundWindow.restype = wintypes.HWND
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return "", ""
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buf, 512)
        title = buf.value
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        h = kernel32.OpenProcess(0x1000, False, pid.value)
        exe = ""
        if h:
            size = wintypes.DWORD(512)
            b2 = ctypes.create_unicode_buffer(512)
            if kernel32.QueryFullProcessImageNameW(h, 0, b2, ctypes.byref(size)):
                exe = os.path.basename(b2.value).lower()
            kernel32.CloseHandle(h)
        return exe, title
    except Exception:
        return "", ""


_VK_MODS = {"ctrl": 0x11, "control": 0x11, "alt": 0x12, "shift": 0x10,
            "win": 0x5B, "meta": 0x5B}
_VK_NAMES = {"esc": 0x1B, "escape": 0x1B, "space": 0x20, "enter": 0x0D,
             "tab": 0x09, "pause": 0x13, "home": 0x24, "end": 0x23,
             "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
             "insert": 0x2D, "delete": 0x2E, "pageup": 0x21, "pagedown": 0x22}


def parse_hotkey(text):
    """'ctrl+alt+h' ← (لیست کلیدهای ترکیبی، کد کلید) ؛ نامعتبر = None"""
    mods, vk = [], None
    for tok in (text or "").lower().replace(" ", "").split("+"):
        if not tok:
            continue
        if tok in _VK_MODS:
            mods.append(_VK_MODS[tok])
        elif tok in _VK_NAMES:
            vk = _VK_NAMES[tok]
        elif len(tok) == 1 and tok.isalnum():
            vk = ord(tok.upper())
        elif tok[0] == "f" and tok[1:].isdigit() and 1 <= int(tok[1:]) <= 12:
            vk = 0x70 + int(tok[1:]) - 1
        else:
            return None
    if vk is None or not mods:
        return None
    return mods, vk


AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def autostart_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --minimized'
    exe = sys.executable
    pyw = exe.replace("python.exe", "pythonw.exe")
    if os.path.exists(pyw):
        exe = pyw
    return f'"{exe}" "{os.path.abspath(sys.argv[0])}" --minimized'


def set_autostart(enabled):
    """روشن/خاموش کردن اجرای خودکار (ویندوز: Run ؛ لینوکس: ~/.config/autostart)"""
    if IS_LINUX:
        try:
            f = pathlib.Path.home() / ".config" / "autostart" / "hand-control-pro.desktop"
            if enabled:
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text("[Desktop Entry]\nType=Application\n"
                             f"Name={APP_NAME}\nExec={autostart_command()}\n"
                             "Icon=input-mouse\nX-GNOME-Autostart-enabled=true\n",
                             encoding="utf-8")
            elif f.exists():
                f.unlink()
            return True
        except Exception as e:
            print("تنظیم اجرای خودکار ناموفق بود:", e)
            return False
    if not IS_WIN:
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0,
                            winreg.KEY_SET_VALUE) as k:
            if enabled:
                winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, autostart_command())
            else:
                try:
                    winreg.DeleteValue(k, APP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        print("تنظیم اجرای خودکار ناموفق بود:", e)
        return False


def http_request(method, spec):
    """درخواست وب در نخ جدا. spec = 'آدرس' یا 'آدرس | متن'"""
    def work():
        try:
            import urllib.request
            url, _, body = [x.strip() for x in spec.partition("|")]
            if "://" not in url:
                url = "http://" + url
            data = body.encode("utf-8") if method == "POST" else None
            req = urllib.request.Request(url, data=data, method=method)
            if data is not None and body and body[0] in "{[":
                req.add_header("Content-Type", "application/json")
            urllib.request.urlopen(req, timeout=5).close()
        except Exception as e:
            print("درخواست وب ناموفق بود:", e)
    threading.Thread(target=work, daemon=True).start()


def _pct(vals, q):
    return float(np.percentile(np.asarray(vals, dtype=float), q))


def compute_calibration(data):
    """data = {مرحله: [نمونه‌ها]} ← (تغییرهای پیشنهادی تنظیمات، خطوط گزارش)"""
    upd, rpt = {}, []

    def vals(step, key):
        out = []
        for smp in data.get(step, []):
            v = smp[key]
            out.extend(v if isinstance(v, (list, tuple)) else [v])
        return out

    open_a, fist_a = vals("open", "angles"), vals("fist", "angles")
    if open_a and fist_a:
        lo, hi = _pct(open_a, 10), _pct(fist_a, 90)
        if lo - hi >= 15:
            upd["ext_angle"] = int(round(np.clip((lo + hi) / 2, 100, 172)))
            rpt.append(f"✅ زاویهٔ انگشت: باز ≥ {lo:.0f}° ، بسته ≤ {hi:.0f}° ← آستانه {upd['ext_angle']}°")
        else:
            rpt.append("⚠️ انگشت‌های باز و بسته به‌اندازهٔ کافی فرق نداشتند؛ آستانهٔ زاویه تغییر نکرد.")

    tucked = vals("trigger", "thumb_v")
    opened = vals("point", "thumb_v") + vals("open", "thumb_v")
    if tucked and opened:
        t, o = float(np.median(tucked)), float(np.median(opened))
        if o - t >= 0.15:
            upd["tuck_on"] = round(t + 0.4 * (o - t), 2)
            upd["tuck_off"] = round(t + 0.7 * (o - t), 2)
            rpt.append(f"✅ شست: بسته ≈ {t:.2f} ، باز ≈ {o:.2f} ← آستانه‌ها {upd['tuck_on']} / {upd['tuck_off']}")
        else:
            rpt.append("⚠️ حالت شست باز و بسته خیلی شبیه هم بود؛ آستانهٔ ماشه تغییر نکرد.")

    pin = vals("pinch", "pinch_v")
    notpin = vals("open", "pinch_v") + vals("point", "pinch_v")
    if pin and notpin:
        pm, nm = _pct(pin, 75), float(np.median(notpin))
        if nm - pm >= 0.2:
            on = float(np.clip(pm * 1.3 + 0.02, 0.12, nm * 0.7))
            off = float(np.clip(on * 1.4, on + 0.05, nm * 0.9))
            upd["pinch_on"], upd["pinch_off"] = round(on, 2), round(off, 2)
            rpt.append(f"✅ نیشگون: چسبیده ≈ {pm:.2f} ، باز ≈ {nm:.2f} ← آستانه‌ها {upd['pinch_on']} / {upd['pinch_off']}")
        else:
            rpt.append("⚠️ نیشگون واضح نبود؛ آستانه‌ها تغییر نکرد.")

    far_p, far_f = vals("pinch", "far_v"), vals("fist", "far_v")
    if far_p and far_f:
        lo, hi = _pct(far_p, 10), _pct(far_f, 90)
        if lo - hi >= 0.05:
            upd["pinch_far"] = round(float(np.clip((lo + hi) / 2, 0.5, 1.3)), 2)
            rpt.append(f"✅ جدا کردن نیشگون از مشت ← {upd['pinch_far']}")

    pts = [smp["px"] for smp in data.get("point", [])]
    if len(pts) >= 8:
        a_ = np.asarray(pts, dtype=float)
        jit = float(np.sqrt(np.var(a_[:, 0]) + np.var(a_[:, 1])))
        upd["smoothing"] = round(float(np.clip(3 + 1.2 * jit, 3, 9)), 1)
        rpt.append(f"✅ لرزش دست ≈ {jit:.1f}px ← نرمی ماوس {upd['smoothing']}")
    return upd, rpt


def new_lock_state():
    return {"locked": False, "last_pos": None, "last_seen": 0.0,
            "score_ema": None, "bad": 0}


def select_hand(cands, st, cfg, owner_sig, now, enrolling=False):
    """انتخاب دستی که باید دنبال شود. برمی‌گرداند: (دست، وضعیت قفل، شباهت)"""
    if enrolling:
        valid = list(cands)
    else:
        valid = [c for c in cands
                 if c["palm"] >= cfg["min_hand_size"]
                 and (cfg["hand_side"] == "any" or c["label"] == cfg["hand_side"])]
    jump = 0.35 * FRAME_W
    use_lock = bool(cfg["owner_lock"]) and owner_sig is not None

    def nearest(cs):
        if st["last_pos"] is None or not cs:
            return None
        c = min(cs, key=lambda c: d(c["pts"][9], st["last_pos"]))
        return c if d(c["pts"][9], st["last_pos"]) < jump else None

    if enrolling:
        return (max(valid, key=lambda c: c["palm"]) if valid else None), "off", -1.0

    if not use_lock:
        chosen = None
        if valid:
            if now - st["last_seen"] < 1.0:
                chosen = nearest(valid)
            if chosen is None:
                chosen = max(valid, key=lambda c: c["palm"])
        state = "no_owner" if cfg["owner_lock"] else "off"
        return chosen, state, -1.0

    # ---- قفل روی دست ثبت‌شده ----
    if st["locked"] and now - st["last_seen"] > cfg["lock_timeout"]:
        st.update(locked=False, score_ema=None, bad=0)

    if st["locked"]:
        chosen = nearest(valid)
        score = -1.0
        if (chosen is not None and chosen["world"] is not None
                and GestureClassifier()(chosen["pts"], cfg) in ("palm", "four")):
            s_now = sig_distance(hand_signature(chosen["world"]), owner_sig)
            score = s_now
            ema = s_now if st["score_ema"] is None else \
                0.85 * st["score_ema"] + 0.15 * s_now
            st["score_ema"] = ema
            if ema > cfg["owner_threshold"] * 1.5:
                st["bad"] += 1
                if st["bad"] >= 10:  # این دست مال صاحب نیست
                    st.update(locked=False, score_ema=None, bad=0)
                    chosen = None
            else:
                st["bad"] = 0
        return chosen, ("locked" if st["locked"] else "waiting"), score

    # برای قفل شدن: کف دست باز + شباهت کافی
    best, best_s = None, 9.0
    for c in valid:
        if c["world"] is None:
            continue
        if GestureClassifier()(c["pts"], cfg) not in ("palm", "four"):
            continue
        sc = sig_distance(hand_signature(c["world"]), owner_sig)
        if sc < best_s:
            best, best_s = c, sc
    if best is not None and best_s < cfg["owner_threshold"]:
        st.update(locked=True, score_ema=best_s, bad=0)
        return best, "locked", best_s
    return None, "waiting", (best_s if best is not None else -1.0)


def detect_swipe(hist, cfg):
    """hist: لیست (زمان، x، y) مرکز کف دست در پنجرهٔ زمانی اخیر"""
    if len(hist) < 4:
        return None
    dx = hist[-1][1] - hist[0][1]
    dy = hist[-1][2] - hist[0][2]
    thr = cfg["swipe_distance"] * FRAME_W
    if abs(dx) > thr and abs(dx) > 1.8 * abs(dy):
        return "swipe_right" if dx > 0 else "swipe_left"
    if abs(dy) > thr * 0.8 and abs(dy) > 1.8 * abs(dx):
        return "swipe_down" if dy > 0 else "swipe_up"
    return None


class Engine(QThread):
    frame_ready = pyqtSignal(QImage)
    gesture_changed = pyqtSignal(str)
    error = pyqtSignal(str)
    recording_progress = pyqtSignal(int)
    recording_done = pyqtSignal(object)
    enroll_progress = pyqtSignal(int)
    enroll_done = pyqtSignal(object)
    lock_status = pyqtSignal(str, float)
    motion_recorded = pyqtSignal(object)
    motion_detected = pyqtSignal(str)
    stats = pyqtSignal(str)
    collect_progress = pyqtSignal(int)
    collect_done = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.cfg = dict(DEFAULT_SETTINGS)
        self.binding_map = {}
        self.hold_map = {}
        self.customs = []
        self.motions = []
        self.sequences = []
        self.need_two = False
        self.pose_model = hlearn.PoseModel()
        self._head_reset = False
        self.owner_sig = None
        self.execute = True
        self.preview = True
        self._quit = False
        self._rec_n = 0
        self._rec_buf = []
        self._enroll_n = 0
        self._enroll_buf = []
        self._mrec_until = 0.0
        self._mrec_active = False
        self._mrec_buf = []
        self._cal_n = 0
        self._cal_buf = []
        self._lock = threading.Lock()

    # ---------- کنترل از بیرون ----------
    def update_config(self, settings, bindings, customs, owner=None,
                      motions=None, actions=None, sequences=None):
        bmap, hold_map = {}, {}
        for b in bindings:
            if not b.get("enabled"):
                continue
            hold = float(b.get("hold", 0) or 0)
            if b.get("confirm") and hold <= 0:
                hold = 1.2                      # عمل خطرناک: فقط با نگه‌داشتن ژست
            if hold > 0:
                hold_map.setdefault(b["gesture"], []).append(
                    (hold, b["action"], b.get("param", "")))
            elif b["gesture"] not in bmap:
                bmap[b["gesture"]] = (b["action"], b.get("param", ""))
        for k in hold_map:
            hold_map[k].sort()
        cl = [("custom:" + c["id"], np.array(c["vec"], dtype=float))
              for c in customs if not c.get("samples")]
        self.pose_model = hlearn.PoseModel().fit(
            {"custom:" + c["id"]: c["samples"] for c in customs if c.get("samples")})
        ml = [{"key": "motion:" + m["id"], "pose": m.get("pose", "any"),
               "templates": [np.array(t, dtype=float) for t in m["templates"]]}
              for m in (motions or [])]
        sq = [{"key": "seq:" + q["id"], "steps": list(q["steps"]),
               "window": float(q.get("window", 2.5))}
              for q in (sequences or []) if len(q.get("steps", [])) >= 2]
        set_custom_actions(actions)
        self.cfg = apply_tremor(dict(settings))
        self.binding_map = bmap
        self.hold_map = hold_map
        self.customs = cl
        self.motions = ml
        self.sequences = sq
        self.need_two = (any(a in TWO_HAND for a, _p in bmap.values())
                         or any(a in TWO_HAND for lst in hold_map.values()
                                for _h, a, _p in lst))
        self.owner_sig = (np.array(owner["sig"], dtype=float)
                          if owner and owner.get("sig") else None)

    def start_recording(self, n):
        with self._lock:
            self._rec_buf = []
            self._rec_n = int(n)

    def cancel_recording(self):
        with self._lock:
            self._rec_n = 0
            self._rec_buf = []

    def start_enroll(self, n):
        with self._lock:
            self._enroll_buf = []
            self._enroll_n = int(n)

    def cancel_enroll(self):
        with self._lock:
            self._enroll_n = 0
            self._enroll_buf = []

    def start_motion_record(self, seconds):
        with self._lock:
            self._mrec_buf = []
            self._mrec_until = time.time() + float(seconds)
            self._mrec_active = True

    def cancel_motion_record(self):
        with self._lock:
            self._mrec_active = False
            self._mrec_buf = []

    def start_collect(self, n):
        with self._lock:
            self._cal_buf = []
            self._cal_n = int(n)

    def cancel_collect(self):
        with self._lock:
            self._cal_n = 0
            self._cal_buf = []

    def recenter_head(self):
        self._head_reset = True

    def stop(self):
        self._quit = True
        self.wait(3000)

    def _snd(self, kind):
        if self.cfg.get("sound"):
            play_sound(kind)

    # ---------- حلقهٔ اصلی ----------
    def run(self):
        try:
            self._loop()
        except Exception as e:  # نمایش خطا به‌جای بسته شدن بی‌صدا
            self.error.emit(f"خطا در پردازش: {e}")

    def _loop(self):
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0
        screen_w, screen_h = pyautogui.size()

        cfg = self.cfg
        cap = open_camera((cfg.get("camera_source") or "").strip()
                          or int(cfg["camera_index"]))
        if cap is None:
            self.error.emit(
                f"دوربین شمارهٔ {cfg['camera_index']} باز نشد. "
                "شمارهٔ دوربین را در تنظیمات عوض کنید یا دسترسی دوربین ویندوز را بررسی کنید.")
            return
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        req_w = int(cfg["cam_width"])
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, req_w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_SIZES.get(req_w, 480))
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        conf = float(cfg["detect_conf"])
        h_track = mp.solutions.hands.Hands(
            static_image_mode=False, max_num_hands=3,
            min_detection_confidence=conf, min_tracking_confidence=0.5)
        h_static = mp.solutions.hands.Hands(  # برای ناحیه‌های بزرگ‌نمایی‌شده
            static_image_mode=True, max_num_hands=2,
            min_detection_confidence=conf)
        h_scan = mp.solutions.hands.Hands(  # جستجوی دست‌های کوچک: آستانهٔ پایین‌تر
            static_image_mode=True, max_num_hands=2,
            min_detection_confidence=max(0.25, conf - 0.15))
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

        classify = GestureClassifier()
        votes = deque(maxlen=int(cfg["vote_frames"]))
        stable = prev_stable = "none"
        smooth_pts = None
        dragging = False
        drag_idle = 0
        prev_scroll_y = None
        cursor = list(pyautogui.position())
        pos_hist = deque(maxlen=16)
        last_click = last_action = last_swipe = last_seq = 0.0
        flash_text, flash_until = "", 0.0
        swipe_hist = deque()
        detector = MotionDetector()
        st = new_lock_state()
        last_status = ("", 0.0)
        last_status_t = 0.0
        roi_box = None
        tile_dims, tile_list, tile_i = None, [], 0
        stats_t = 0.0
        fps, t_prev = 0.0, time.time()
        hold_t0, hold_fired = time.time(), set()
        seq_hist = deque(maxlen=12)
        slider_ref = None
        zoom_ref = None
        dwell_anchor, dwell_t0, dwell_fired = None, 0.0, False
        prev_lock = ""
        idle_n = 0
        fmesh = None
        head = hhead.HeadTracker()
        pen_down = False

        def screen_rect(c):
            m = c.get("monitor_rect")
            if m and len(m) == 4:
                return m
            return (0, 0, screen_w, screen_h)

        def map_point(px, py, c, lh):
            ox, oy, sw, sh = screen_rect(c)
            mx = c["margin"]
            my = c["margin"] * lh / LW
            x = ox + float(np.interp(px, (mx, LW - mx), (0, sw)))
            y = oy + float(np.interp(py, (my, lh - my), (0, sh)))
            return x, y

        def move_cursor(px, py, c, lh):
            x, y = map_point(px, py, c, lh)
            dx, dy = x - cursor[0], y - cursor[1]
            if math.hypot(dx, dy) < c["deadzone"]:
                return
            cursor[0] += dx / c["smoothing"]
            cursor[1] += dy / c["smoothing"]
            pyautogui.moveTo(cursor[0], cursor[1])

        try:
            while not self._quit:
                ok, frame = cap.read()
                if not ok:
                    self.error.emit("خواندن تصویر از دوربین ناموفق بود.")
                    break
                cfg = self.cfg
                bmap = self.binding_map
                hmap = self.hold_map
                customs = self.customs
                owner_sig = self.owner_sig
                need_two = self.need_two
                if votes.maxlen != int(cfg["vote_frames"]):
                    votes = deque(votes, maxlen=int(cfg["vote_frames"]))

                frame = cv2.flip(frame, 1)
                fh, fw = frame.shape[:2]
                scale = LW / float(fw)
                lh = int(round(fh * scale))
                view = cv2.resize(frame, (LW, lh))
                now = time.time()
                dt_ = now - t_prev
                fps = 0.9 * fps + 0.1 / max(dt_, 1e-3)
                t_prev = now
                stats_obj = RUNTIME.get("stats")
                if stats_obj is not None:
                    stats_obj.tick(now - st["last_seen"] < 0.5, dt_)

                # ---- حالت کم‌مصرف: وقتی دستی نیست بیشتر فریم‌ها پردازش نمی‌شوند ----
                if (cfg.get("low_power") and not cfg.get("head_control")
                        and now - st["last_seen"] > float(cfg.get("idle_after", 6.0))
                        and not (self._rec_n or self._enroll_n or self._mrec_active
                                 or self._cal_n)):
                    idle_n += 1
                    if idle_n % 3:
                        time.sleep(0.05)
                        continue
                else:
                    idle_n = 0

                # تصویر مخصوص تشخیص: بهبود نور + حاشیهٔ مجازی تا دست‌های کنار تصویر هم دیده شوند
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                if cfg["enhance"]:
                    rgb = enhance_image(rgb, clahe)
                pad = int(float(cfg["edge_pad"]) * min(fw, fh))
                if pad > 0:
                    rgb = cv2.copyMakeBorder(rgb, pad, pad, pad, pad,
                                             cv2.BORDER_CONSTANT, value=(0, 0, 0))
                pw, ph = fw + 2 * pad, fh + 2 * pad
                level = int(cfg["scan_level"])
                if tile_dims != (pw, ph, level):
                    tile_dims = (pw, ph, level)
                    tile_list = scan_tiles(pw, ph, level)

                # ---- تشخیص: ناحیهٔ بزرگ‌نمایی ← ناحیهٔ بزرگ‌تر ← تصویر کامل ← جستجوی نواحی ----
                # (وقتی عمل دو دستی داریم، هر دو دست باید دیده شوند: بدون زوم روی یک دست)
                cands, path = [], "full"
                if (cfg["far_mode"] and roi_box is not None and not need_two
                        and now - st["last_seen"] < 1.0):
                    cands = extract_hands(
                        run_hands(h_static, rgb, roi_box), roi_box, scale, pad)
                    path = "roi"
                    if not cands and now - st["last_seen"] < 0.5:
                        big = grow_box(roi_box, 1.8, pw, ph)
                        cands = extract_hands(
                            run_hands(h_static, rgb, big), big, scale, pad)
                        path = "roi+"
                if not cands:
                    cands = extract_hands(h_track.process(rgb), (0, 0, pw, ph),
                                          scale, pad)
                    path = "full"
                if not cands and cfg["far_mode"] and tile_list:
                    for _ in range((1, 2, 3)[max(0, min(level, 2))]):
                        box = tile_list[tile_i % len(tile_list)]
                        tile_i += 1
                        cands += extract_hands(run_hands(h_scan, rgb, box), box,
                                               scale, pad)
                        if cands:
                            break
                    path = "tile"
                cands = [c for c in cands if plausible_hand(c["pts"])]
                if len(cands) > 1:
                    cands = dedupe_hands(cands)

                enrolling = self._enroll_n > 0
                chosen, lock_state, score_now = select_hand(
                    cands, st, cfg, owner_sig, now, enrolling)

                # ---- رسم: دست انتخاب‌شده سبز، بقیه قرمز (نادیده گرفته می‌شوند) ----
                for c in cands:
                    if c is chosen:
                        if cfg["show_landmarks"]:
                            draw_hand(view, c["pts"], (80, 220, 120))
                    else:
                        draw_hand(view, c["pts"], (60, 60, 230), (200, 200, 255))

                # صدای قفل
                if lock_state != prev_lock:
                    if lock_state == "locked":
                        self._snd("lock")
                    elif prev_lock == "locked":
                        self._snd("unlock")
                    prev_lock = lock_state

                # دست تازه‌پیداشده از جستجوی نواحی: اول تأیید می‌شود (فریم بعد با زوم دوباره دیده شود)
                if chosen is not None and path == "tile":
                    near = (st["last_pos"] is not None
                            and now - st["last_seen"] < 0.4
                            and d(chosen["pts"][9], st["last_pos"]) < 0.2 * LW)
                    st["last_pos"] = chosen["pts"][9].copy()
                    st["last_seen"] = now
                    roi_box = make_roi(chosen["pts"] / scale + pad, pw, ph)
                    if not near:
                        chosen = None

                raw = "none"
                pts = None
                second = None
                if chosen is not None:
                    others = [c for c in cands if c is not chosen]
                    if others:
                        second = max(others, key=lambda c: c["palm"])
                    st["last_pos"] = chosen["pts"][9].copy()
                    st["last_seen"] = now
                    roi_box = make_roi(chosen["pts"] / scale + pad, pw, ph)
                    a = cfg["landmark_alpha"]
                    if chosen["palm"] < 60:  # دست دور = نویز بیشتر = هموارسازی بیشتر
                        a = max(0.25, a * chosen["palm"] / 60.0)
                    cur = chosen["pts"]
                    smooth_pts = cur if smooth_pts is None else (
                        a * cur + (1 - a) * smooth_pts)
                    pts = smooth_pts

                    raw = classify(pts, cfg)
                    vec = pose_vector(pts)

                    # ژست‌های سفارشی (حالت ثابت) اولویت دارند: اول مدل نمونه‌محور، بعد میانگین قدیمی
                    lab, _ratio = (self.pose_model.predict(vec)
                                   if self.pose_model.classes else (None, 9.0))
                    if lab:
                        raw = lab
                    else:
                        best_key, best_d = None, 9.0
                        for key, tv in customs:
                            dd = pose_distance(vec, tv)
                            if dd < best_d:
                                best_key, best_d = key, dd
                        if best_key and best_d < cfg["custom_threshold"]:
                            raw = best_key

                    # ضبط ژست ثابت جدید
                    if self._rec_n > 0:
                        with self._lock:
                            self._rec_buf.append(vec)
                            n = len(self._rec_buf)
                            target = self._rec_n
                        self.recording_progress.emit(n)
                        if n >= target:
                            with self._lock:
                                mean = np.mean(self._rec_buf, axis=0)
                                samples_ = [v_.tolist() for v_ in self._rec_buf[::2]]
                                self._rec_n = 0
                                self._rec_buf = []
                            self.recording_done.emit(
                                {"vec": mean.tolist(), "samples": samples_})

                    # ضبط ژست متحرک
                    if self._mrec_active:
                        with self._lock:
                            self._mrec_buf.append(
                                (now, float(pts[9][0]), float(pts[9][1]),
                                 raw, float(chosen["palm"])))

                    # نمونه‌برداری برای کالیبراسیون
                    if self._cal_n > 0:
                        info = classify.info
                        smp = {"angles": list(info["angles"]),
                               "thumb_v": info["thumb_v"],
                               "pinch_v": info["pinch_v"],
                               "far_v": info["far_v"],
                               "palm": float(chosen["palm"]),
                               "px": (float(pts[8][0]), float(pts[8][1]))}
                        with self._lock:
                            self._cal_buf.append(smp)
                            n = len(self._cal_buf)
                            target = self._cal_n
                        self.collect_progress.emit(n)
                        if n >= target:
                            with self._lock:
                                buf = list(self._cal_buf)
                                self._cal_n = 0
                                self._cal_buf = []
                            self.collect_done.emit(buf)

                    # ثبت دست صاحب (فقط وقتی یک دست در تصویر است)
                    if (enrolling and len(cands) == 1 and raw == "palm"
                            and chosen["world"] is not None):
                        with self._lock:
                            self._enroll_buf.append(hand_signature(chosen["world"]))
                            n = len(self._enroll_buf)
                            target = self._enroll_n
                        self.enroll_progress.emit(n)
                        if n >= target:
                            with self._lock:
                                arr = np.array(self._enroll_buf)
                                self._enroll_n = 0
                                self._enroll_buf = []
                            med = np.median(arr, axis=0)
                            dists = [sig_distance(x, med) for x in arr]
                            suggest = float(np.clip(np.mean(dists) * 3 + 0.04,
                                                    0.10, 0.35))
                            self.enroll_done.emit(
                                {"sig": med.tolist(), "suggest": suggest})

                    votes.append(raw)
                    best, cnt = Counter(votes).most_common(1)[0]
                    if cnt >= int(cfg["vote_min"]):
                        stable = best
                else:
                    smooth_pts = None
                    votes.clear()
                    stable = "none"

                # پایان ضبط حرکت (زمان‌بندی‌شده)
                if self._mrec_active and now >= self._mrec_until:
                    with self._lock:
                        buf = list(self._mrec_buf)
                        self._mrec_active = False
                        self._mrec_buf = []
                    self.motion_recorded.emit(buf)

                changed = stable != prev_stable
                if changed:
                    self.gesture_changed.emit(stable)
                    if stable != "none":
                        if stats_obj is not None:
                            stats_obj.gesture(stable)
                        PLUGINS.notify("gesture", stable)
                    hold_t0 = now
                    hold_fired = set()
                    if stable != "none":
                        seq_hist.append((now, stable))

                executing = (self.execute and self._rec_n == 0
                             and not enrolling and not self._mrec_active
                             and self._cal_n == 0)
                action, param = bmap.get(stable, ("none", "")) if executing \
                    else ("none", "")

                # ---- رها کردن Drag ----
                if dragging:
                    if action == "drag":
                        drag_idle = 0
                    else:
                        drag_idle += 1
                        if drag_idle >= 5:
                            pyautogui.mouseUp()
                            dragging = False
                if action != "scroll":
                    prev_scroll_y = None
                if pen_down and action != "overlay_pen":
                    pen_down = False
                    if HOOKS.get("overlay"):
                        HOOKS["overlay"]("overlay_pen_up")
                if action not in ("volume_slider", "seek_slider"):
                    slider_ref = None
                if action != "two_hand_zoom":
                    zoom_ref = None
                if action != "move_cursor":
                    dwell_anchor = None

                # ---- اجرای عمل ----
                if pts is not None and action != "none":
                    if action == "move_cursor":
                        px, py = pts[int(cfg["pointer_landmark"])]
                        move_cursor(px, py, cfg, lh)
                        pos_hist.append(map_point(px, py, cfg, lh))
                        if cfg["dwell_click"]:      # کلیک با مکث
                            here = np.array([px, py], dtype=float)
                            if (dwell_anchor is None
                                    or d(here, dwell_anchor) > cfg["dwell_radius"]):
                                dwell_anchor, dwell_t0, dwell_fired = here, now, False
                            elif not dwell_fired:
                                prog = min(1.0, (now - dwell_t0) / cfg["dwell_time"])
                                cv2.circle(view, (int(px), int(py)),
                                           int(8 + 14 * prog), (0, 255, 255), 2)
                                if prog >= 1.0:
                                    run_action("left_click")
                                    dwell_fired = True
                                    self._snd("click")
                                    flash_text, flash_until = "DWELL CLICK", now + 0.4
                    elif action == "drag":
                        if not dragging:
                            pyautogui.mouseDown()
                            dragging = True
                            drag_idle = 0
                        move_cursor(pts[9][0], pts[9][1], cfg, lh)
                    elif action == "scroll":
                        y = (pts[4][1] + pts[8][1]) / 2
                        if prev_scroll_y is not None:
                            dy = y - prev_scroll_y
                            if abs(dy) > 3:
                                pyautogui.scroll(int(-dy * cfg["scroll_speed"]))
                        prev_scroll_y = y
                    elif action in ("volume_slider", "seek_slider"):
                        vert = action == "volume_slider"
                        cur_v = float(pts[9][1] if vert else pts[9][0])
                        if slider_ref is None:
                            slider_ref = cur_v
                        step = float(cfg["slider_step"])
                        delta = cur_v - slider_ref
                        if abs(delta) >= step:
                            n_ = min(int(abs(delta) // step), 5)
                            if vert:
                                key = "volumeup" if delta < 0 else "volumedown"
                            else:
                                key = "right" if delta > 0 else "left"
                            for _ in range(n_):
                                if key.startswith("volume"):
                                    media_key(key)
                                else:
                                    pyautogui.press(key)
                            slider_ref += math.copysign(n_ * step, delta)
                    elif action == "two_hand_zoom":
                        if second is not None and second["palm"] >= 0.5 * chosen["palm"]:
                            dist_h = d(pts[9], second["pts"][9])
                            if zoom_ref is None:
                                zoom_ref = dist_h
                            step = float(cfg["zoom_step"])
                            delta = dist_h - zoom_ref
                            if abs(delta) >= step:
                                n_ = min(int(abs(delta) // step), 4)
                                pyautogui.keyDown("ctrl")
                                pyautogui.scroll(int(math.copysign(120 * n_, delta)))
                                pyautogui.keyUp("ctrl")
                                zoom_ref += math.copysign(n_ * step, delta)
                        else:
                            zoom_ref = None
                    elif action == "overlay_pen":
                        if not pen_down:
                            pen_down = True
                            if HOOKS.get("overlay"):
                                HOOKS["overlay"]("overlay_pen_down")
                        move_cursor(pts[9][0], pts[9][1], cfg, lh)
                    elif action == "pause":
                        pass
                    elif changed:
                        if action in CLICKS:
                            if now - last_click > cfg["click_cooldown"]:
                                rw = int(cfg["click_rewind"])
                                if rw and len(pos_hist) >= rw:
                                    rx, ry = pos_hist[-rw]
                                    cursor[0], cursor[1] = rx, ry
                                    pyautogui.moveTo(rx, ry)
                                run_action(action, param)
                                last_click = now
                                self._snd("click")
                                flash_text = action.split(":")[0].upper()
                                flash_until = now + 0.4
                        elif now - last_action > cfg["action_cooldown"]:
                            run_action(action, param)
                            last_action = now
                            self._snd("action")
                            flash_text = action.split(":")[0].upper()
                            flash_until = now + 0.6

                # ---- کنترل با سر و پلک (دسترس‌پذیری) ----
                if cfg.get("head_control"):
                    if fmesh is None:
                        fmesh = mp.solutions.face_mesh.FaceMesh(
                            max_num_faces=1, refine_landmarks=False,
                            min_detection_confidence=0.5, min_tracking_confidence=0.5)
                    if self._head_reset:
                        head.recenter()
                        self._head_reset = False
                    fres = fmesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    if (fres.multi_face_landmarks and executing
                            and action != "move_cursor"):
                        nose_, fwid, el_, er_ = hhead.face_metrics(
                            fres.multi_face_landmarks[0].landmark, fw, fh)
                        head.gain = float(cfg.get("head_gain", 2.2))
                        (hu, hv), hev = head.update(now, nose_, fwid, el_, er_)
                        ox_, oy_, sw_, sh_ = screen_rect(cfg)
                        cursor[0] += (ox_ + hu * sw_ - cursor[0]) / cfg["smoothing"]
                        cursor[1] += (oy_ + hv * sh_ - cursor[1]) / cfg["smoothing"]
                        pyautogui.moveTo(cursor[0], cursor[1])
                        for ev_ in hev:
                            run_action("left_click" if ev_ == "click" else ev_)
                            self._snd("click")

                # ---- ژست با نگه‌داشتن (Hold) ----
                if executing and stable != "none" and stable in hmap:
                    for hsec, hact, hparam in hmap[stable]:
                        hkey = (hsec, hact)
                        if (now - hold_t0 >= hsec and hkey not in hold_fired
                                and hact not in CONTINUOUS):
                            hold_fired.add(hkey)
                            run_action(hact, hparam)
                            self._snd("action")
                            flash_text, flash_until = f"HOLD {hsec:g}s", now + 0.6

                # ---- ترتیب ژست‌ها (Sequence) ----
                if executing and changed and stable != "none" and self.sequences:
                    for sq in self.sequences:
                        n_ = len(sq["steps"])
                        if len(seq_hist) >= n_ and now - last_seq > 1.0:
                            tail = list(seq_hist)[-n_:]
                            if ([g for _t, g in tail] == sq["steps"]
                                    and now - tail[0][0] <= sq["window"]):
                                self.motion_detected.emit(sq["key"])
                                if sq["key"] in bmap:
                                    sact, sparam = bmap[sq["key"]]
                                    if sact not in CONTINUOUS:
                                        run_action(sact, sparam)
                                        self._snd("action")
                                        flash_text, flash_until = "SEQUENCE", now + 0.6
                                last_seq = now
                                seq_hist.clear()
                                break

                # ---- کشیدن دست (Swipe) با کف دست باز ----
                if executing and pts is not None and stable in ("palm", "four"):
                    swipe_hist.append((now, float(pts[9][0]), float(pts[9][1])))
                    while swipe_hist and now - swipe_hist[0][0] > cfg["swipe_window"]:
                        swipe_hist.popleft()
                    if now - last_swipe > cfg["swipe_cooldown"]:
                        skey = detect_swipe(swipe_hist, cfg)
                        if skey and skey in bmap:
                            sact, sparam = bmap[skey]
                            if sact not in CONTINUOUS:
                                run_action(sact, sparam)
                                last_swipe = now
                                swipe_hist.clear()
                                self._snd("action")
                                flash_text = skey.upper()
                                flash_until = now + 0.6
                else:
                    swipe_hist.clear()

                # ---- ژست‌های متحرک ثبت‌شده توسط کاربر ----
                if executing and pts is not None and self.motions:
                    seg = detector.feed(now, pts[9][0], pts[9][1], raw,
                                        chosen["palm"], cfg)
                    if seg is not None:
                        hit = match_motion(seg, self.motions, cfg)
                        if hit:
                            self.motion_detected.emit(hit[0])
                            if hit[0] in bmap:
                                mact, mparam = bmap[hit[0]]
                                if mact not in CONTINUOUS and now - last_action > 0.4:
                                    run_action(mact, mparam)
                                    last_action = now
                                    self._snd("action")
                                    flash_text = "MOTION"
                                    flash_until = now + 0.6
                else:
                    detector.reset()

                prev_stable = stable

                # ---- وضعیت قفل برای رابط ----
                if lock_state != last_status[0] or now - last_status_t > 0.4:
                    self.lock_status.emit(lock_state, float(score_now))
                    last_status = (lock_state, score_now)
                    last_status_t = now

                # ---- آمار زنده (برای تنظیم تشخیص از فاصله) ----
                if now - stats_t > 0.5:
                    stats_t = now
                    extra = ""
                    if chosen is not None:
                        pf = chosen["palm"] / scale          # اندازهٔ کف دست به پیکسل تصویر اصلی
                        dist = 0.095 * (fw / 1.4) / max(pf, 1.0)   # تخمین تقریبی (دید ~۷۰ درجه)
                        extra = f" · کف دست {pf:.0f}px · ≈{dist:.1f} متر"
                    self.stats.emit(f"{path} · {fps:.0f}fps · {fw}×{fh}{extra} · "
                                    f"دست‌ها: {len(cands)}")

                # ---- نمایش ----
                if self.preview:
                    mx = int(cfg["margin"])
                    my = int(cfg["margin"] * lh / LW)
                    cv2.rectangle(view, (mx, my), (LW - mx, lh - my),
                                  (255, 0, 255), 1)
                    if path in ("roi", "roi+") and roi_box is not None:
                        cv2.rectangle(
                            view,
                            (int((roi_box[0] - pad) * scale),
                             int((roi_box[1] - pad) * scale)),
                            (int((roi_box[2] - pad) * scale),
                             int((roi_box[3] - pad) * scale)),
                            (255, 200, 0), 1)
                    cv2.putText(view, f"{stable}", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                    if executing and stable in hmap:
                        rem = [hs - (now - hold_t0) for hs, ha, hp in hmap[stable]
                               if (hs, ha) not in hold_fired]
                        if rem and min(rem) > 0:
                            cv2.putText(view, f"HOLD {min(rem):.1f}s", (10, 88),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2)
                    if lock_state == "locked":
                        cv2.putText(view, "OWNER LOCKED", (LW - 230, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    elif lock_state == "waiting":
                        cv2.putText(view, "SHOW OPEN PALM TO LOCK",
                                    (LW - 330, 30), cv2.FONT_HERSHEY_SIMPLEX,
                                    0.65, (0, 165, 255), 2)
                    if pts is not None:
                        info = classify.info
                        cv2.putText(
                            view,
                            f"IMRP:{info['fingers']} thumb:{info['thumb']} "
                            f"pinch:{info['pinch']}",
                            (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                            (255, 255, 0), 1)
                    cv2.putText(view, f"{path}  {fps:.0f}fps  {fw}x{fh}",
                                (10, lh - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                                (180, 180, 180), 1)
                    if now < flash_until:
                        cv2.putText(view, flash_text, (20, lh - 35),
                                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 200, 255), 3)

                    rgb_view = cv2.cvtColor(view, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb_view.shape
                    self.frame_ready.emit(
                        QImage(rgb_view.data, w, h, ch * w,
                               QImage.Format.Format_RGB888).copy())
        finally:
            if dragging:
                pyautogui.mouseUp()
            cap.release()
            h_track.close()
            h_static.close()
            h_scan.close()
            if fmesh is not None:
                fmesh.close()


# ============================== پنجرهٔ ضبط ژست ==============================
class RecordDialog(QDialog):
    FRAMES = 25

    def __init__(self, engine, default_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ضبط ژست جدید")
        self.engine = engine
        self.result_gesture = None
        self._done = False
        self.count = 0

        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit(default_name)
        form.addRow("نام ژست:", self.name_edit)
        lay.addLayout(form)

        self.video = QLabel()
        self.video.setFixedSize(480, 360)
        self.video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video.setStyleSheet("background:#111; color:#aaa;")
        self.video.setText("در انتظار تصویر دوربین…")
        lay.addWidget(self.video)

        self.status = QLabel(
            "دستتان را در حالت دلخواه جلوی دوربین بگیرید و «شروع ضبط» را بزنید. "
            "بعد از ۳ ثانیه ضبط شروع می‌شود؛ دست را ثابت نگه دارید.")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)

        self.bar = QProgressBar()
        self.bar.setRange(0, self.FRAMES)
        lay.addWidget(self.bar)

        row = QHBoxLayout()
        self.btn_start = QPushButton("شروع ضبط")
        self.btn_cancel = QPushButton("انصراف")
        row.addWidget(self.btn_start)
        row.addWidget(self.btn_cancel)
        lay.addLayout(row)

        self.btn_start.clicked.connect(self.start_clicked)
        self.btn_cancel.clicked.connect(self.reject)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)

        engine.frame_ready.connect(self.on_frame)
        engine.recording_progress.connect(self.on_progress)
        engine.recording_done.connect(self.on_done)

    def on_frame(self, img):
        self.video.setPixmap(QPixmap.fromImage(img).scaled(
            self.video.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))

    def start_clicked(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "نام", "یک نام برای ژست بنویسید.")
            return
        self.btn_start.setEnabled(False)
        self.bar.setValue(0)
        self.count = 3
        self.status.setText(f"آماده شوید… {self.count}")
        self.timer.start(1000)

    def tick(self):
        self.count -= 1
        if self.count > 0:
            self.status.setText(f"آماده شوید… {self.count}")
            return
        self.timer.stop()
        self.status.setText("در حال ضبط… دست را ثابت و داخل کادر نگه دارید.")
        self.engine.start_recording(self.FRAMES)
        QTimer.singleShot(15000, self.on_timeout)

    def on_progress(self, n):
        self.bar.setValue(min(n, self.FRAMES))

    def on_timeout(self):
        if not self._done and self.isVisible() and not self.btn_start.isEnabled():
            self.engine.cancel_recording()
            self.status.setText("دست پیدا نشد. دوباره تلاش کنید و دست را داخل کادر بگیرید.")
            self.btn_start.setEnabled(True)

    def on_done(self, vec):
        if self._done or vec is None:
            return
        self._done = True
        samples = None
        if isinstance(vec, dict):
            samples = vec.get("samples")
            vec = vec["vec"]
        self.result_gesture = {"id": uuid.uuid4().hex[:8],
                               "name": self.name_edit.text().strip(),
                               "vec": [float(x) for x in vec]}
        if samples:
            self.result_gesture["samples"] = [[float(x) for x in s_] for s_ in samples]
        self.accept()

    def done(self, r):
        self.timer.stop()
        try:
            self.engine.frame_ready.disconnect(self.on_frame)
            self.engine.recording_progress.disconnect(self.on_progress)
            self.engine.recording_done.disconnect(self.on_done)
        except Exception:
            pass
        self.engine.cancel_recording()
        super().done(r)


class EnrollDialog(QDialog):
    FRAMES = 45

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ثبت دست من")
        self.engine = engine
        self.owner = None
        self._done = False
        self.count = 0

        lay = QVBoxLayout(self)
        self.video = QLabel("در انتظار تصویر دوربین…")
        self.video.setFixedSize(480, 360)
        self.video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video.setStyleSheet("background:#111; color:#aaa;")
        lay.addWidget(self.video)

        self.status = QLabel(
            "فقط دست خودتان در تصویر باشد. کف دست را کاملاً باز، رو به دوربین و "
            "با انگشت‌های کمی باز نگه دارید، بعد «شروع» را بزنید. "
            "بعد از ۳ ثانیه ضبط می‌شود؛ دست را ثابت نگه دارید.")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)

        self.bar = QProgressBar()
        self.bar.setRange(0, self.FRAMES)
        lay.addWidget(self.bar)

        row = QHBoxLayout()
        self.btn_start = QPushButton("شروع")
        self.btn_cancel = QPushButton("انصراف")
        row.addWidget(self.btn_start)
        row.addWidget(self.btn_cancel)
        lay.addLayout(row)

        self.btn_start.clicked.connect(self.start_clicked)
        self.btn_cancel.clicked.connect(self.reject)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)

        engine.frame_ready.connect(self.on_frame)
        engine.enroll_progress.connect(self.on_progress)
        engine.enroll_done.connect(self.on_done)

    def on_frame(self, img):
        self.video.setPixmap(QPixmap.fromImage(img).scaled(
            self.video.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))

    def start_clicked(self):
        self.btn_start.setEnabled(False)
        self.bar.setValue(0)
        self.count = 3
        self.status.setText(f"آماده شوید… {self.count}")
        self.timer.start(1000)

    def tick(self):
        self.count -= 1
        if self.count > 0:
            self.status.setText(f"آماده شوید… {self.count}")
            return
        self.timer.stop()
        self.status.setText("در حال ضبط… کف دست باز را ثابت نگه دارید "
                            "(اگر نوار پیش نمی‌رود، مطمئن شوید فقط یک دست در تصویر است).")
        self.engine.start_enroll(self.FRAMES)
        QTimer.singleShot(25000, self.on_timeout)

    def on_progress(self, n):
        self.bar.setValue(min(n, self.FRAMES))

    def on_timeout(self):
        if not self._done and self.isVisible() and not self.btn_start.isEnabled():
            self.engine.cancel_enroll()
            self.status.setText("ضبط کامل نشد. فقط دست خودتان باشد، کف دست باز و رو به دوربین، و دوباره امتحان کنید.")
            self.btn_start.setEnabled(True)

    def on_done(self, data):
        if self._done or not data:
            return
        self._done = True
        self.owner = data
        self.accept()

    def done(self, r):
        self.timer.stop()
        try:
            self.engine.frame_ready.disconnect(self.on_frame)
            self.engine.enroll_progress.disconnect(self.on_progress)
            self.engine.enroll_done.disconnect(self.on_done)
        except Exception:
            pass
        self.engine.cancel_enroll()
        super().done(r)


# ============================== پنجرهٔ ویرایش ژست ==============================
class BindingDialog(QDialog):
    def __init__(self, main, binding=None):
        super().__init__(main)
        self.main = main
        self.setWindowTitle("ویرایش ژست" if binding else "ژست جدید")
        self.setMinimumWidth(600)
        self.binding = dict(binding) if binding else {
            "id": uuid.uuid4().hex[:8], "name": "", "gesture": "",
            "action": "none", "param": "", "enabled": True}

        lay = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit(self.binding["name"])
        form.addRow("نام:", self.name_edit)

        # ژست
        self.gesture_combo = QComboBox()
        g_row = QHBoxLayout()
        g_row.addWidget(self.gesture_combo, 1)
        self.btn_record = QPushButton("➕ ژست ثابت")
        self.btn_record.setToolTip("ضبط یک حالت دست با دوربین")
        self.btn_motion = QPushButton("🌀 ژست متحرک")
        self.btn_motion.setToolTip("ضبط یک حرکت دست (مثلاً کشیدن دایره)")
        g_row.addWidget(self.btn_record)
        g_row.addWidget(self.btn_motion)
        form.addRow("ژست:", g_row)
        self.gesture_hint = QLabel()
        self.gesture_hint.setWordWrap(True)
        self.gesture_hint.setProperty("muted", True)
        form.addRow("", self.gesture_hint)

        self.hold_spin = QDoubleSpinBox()
        self.hold_spin.setRange(0.0, 10.0)
        self.hold_spin.setSingleStep(0.1)
        self.hold_spin.setDecimals(1)
        self.hold_spin.setSuffix("  ثانیه")
        self.hold_spin.setSpecialValueText("فوری (بدون نگه‌داشتن)")
        self.hold_spin.setValue(float(self.binding.get("hold", 0) or 0))
        form.addRow("نگه‌داشتن ژست:", self.hold_spin)
        self.confirm_chk = QCheckBox("نیاز به تأیید: ژست باید ۱٫۲ ثانیه نگه داشته شود (برای کارهای خطرناک)")
        self.confirm_chk.setChecked(bool(self.binding.get("confirm", False)))
        form.addRow("", self.confirm_chk)
        self.need_combo = QComboBox()
        self.need_combo.addItem("— بدون شرط —", "")
        for lb_, k_ in self.main.gesture_choices():
            if not k_.startswith(("swipe_", "motion:", "seq:", "voice:")):
                self.need_combo.addItem(lb_, k_)
        self.need_combo.setCurrentIndex(
            max(self.need_combo.findData(self.binding.get("need_gesture", "")), 0))
        form.addRow("(فقط دستور صوتی) همزمان با ژست:", self.need_combo)

        # عمل
        self.action_combo = QComboBox()
        a_row = QHBoxLayout()
        a_row.addWidget(self.action_combo, 1)
        self.btn_new_action = QPushButton("➕ عمل جدید")
        self.btn_new_action.setToolTip("ساخت عمل دلخواه، مثلاً Alt+F4")
        a_row.addWidget(self.btn_new_action)
        form.addRow("عمل:", a_row)

        # پارامتر
        self.param_edit = QLineEdit(self.binding.get("param", ""))
        self.btn_browse = QPushButton("انتخاب برنامه…")
        p_row = QHBoxLayout()
        p_row.addWidget(self.param_edit, 1)
        p_row.addWidget(self.btn_browse)
        self.param_label = QLabel("پارامتر:")
        form.addRow(self.param_label, p_row)

        self.key_edit = QKeySequenceEdit()
        self.key_label = QLabel("ضبط میانبر:")
        form.addRow(self.key_label, self.key_edit)
        self.param_hint = QLabel()
        self.param_hint.setWordWrap(True)
        self.param_hint.setProperty("muted", True)
        form.addRow("", self.param_hint)

        self.enabled_check = QCheckBox("فعال")
        self.enabled_check.setChecked(bool(self.binding.get("enabled", True)))
        form.addRow("", self.enabled_check)
        lay.addLayout(form)

        row = QHBoxLayout()
        self.btn_test = QPushButton("▶ آزمایش عمل")
        row.addWidget(self.btn_test)
        row.addStretch(1)
        lay.addLayout(row)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                              QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("ذخیره")
        bb.button(QDialogButtonBox.StandardButton.Cancel).setText("انصراف")
        bb.accepted.connect(self.try_accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

        self.fill_gestures(self.binding["gesture"])
        self.fill_actions(self.binding["action"])

        self.gesture_combo.currentIndexChanged.connect(self.update_gesture_hint)
        self.action_combo.currentIndexChanged.connect(self.update_param_ui)
        self.btn_record.clicked.connect(self.record_new)
        self.btn_motion.clicked.connect(self.record_motion_new)
        self.btn_new_action.clicked.connect(self.new_action_clicked)
        self.btn_browse.clicked.connect(self.browse)
        self.key_edit.keySequenceChanged.connect(self.key_changed)
        self.btn_test.clicked.connect(self.test_action)
        self.update_gesture_hint()
        self.update_param_ui()

    # ---------- پر کردن لیست‌ها ----------
    def fill_gestures(self, select_key):
        self.gesture_combo.blockSignals(True)
        self.gesture_combo.clear()
        for label, key in self.main.gesture_choices(include=select_key):
            self.gesture_combo.addItem(label, key)
        i = self.gesture_combo.findData(select_key)
        self.gesture_combo.setCurrentIndex(max(i, 0))
        self.gesture_combo.blockSignals(False)

    def fill_actions(self, select_key):
        self.action_combo.blockSignals(True)
        self.action_combo.clear()
        for key, label, group, _ in all_actions(self.main.custom_actions):
            self.action_combo.addItem(f"{group} › {label}", key)
        i = self.action_combo.findData(select_key)
        self.action_combo.setCurrentIndex(max(i, 0))
        self.action_combo.blockSignals(False)

    def action_kind(self, action):
        for a in all_actions(self.main.custom_actions):
            if a[0] == action:
                return a[3]
        return None

    def update_gesture_hint(self):
        key = self.gesture_combo.currentData() or ""
        if key in BUILTIN_GESTURES:
            self.gesture_hint.setText(BUILTIN_GESTURES[key][1])
        elif key.startswith("motion:"):
            self.gesture_hint.setText(
                "ژست متحرک: حرکت ثبت‌شده را با همان حالت دست انجام دهید و در پایان لحظه‌ای مکث کنید.")
        elif key.startswith("seq:"):
            self.gesture_hint.setText(
                "ترتیب ژست‌ها: ژست‌های تعریف‌شده را پشت سر هم و در مهلت مشخص انجام دهید.")
        elif key:
            self.gesture_hint.setText("ژست ثابتی که خودتان با دوربین ثبت کرده‌اید.")
        else:
            self.gesture_hint.setText("یک ژست انتخاب کنید یا با دکمه‌های کنار آن ژست جدید ضبط کنید.")

    def update_param_ui(self):
        action = self.action_combo.currentData()
        kind = self.action_kind(action)
        self.param_edit.setVisible(kind is not None)
        self.param_label.setVisible(kind is not None)
        self.btn_browse.setVisible(kind == "file")
        self.key_edit.setVisible(kind == "hotkey")
        self.key_label.setVisible(kind == "hotkey")
        hints = {
            "file": "مسیر برنامه (مثلاً C:\\Windows\\System32\\calc.exe) یا فقط نام آن، مثل notepad.exe",
            "text": {"open_url": "آدرس سایت، مثلاً youtube.com",
                     "run_command": "دستور کامل، مثلاً: explorer C:\\Users",
                     "type_text": "متنی که تایپ می‌شود (فارسی هم پشتیبانی می‌شود)",
                     "ppt_goto_slide": "شمارهٔ اسلاید، مثلاً 5",
                     "http_get": "آدرس کامل، مثلاً http://192.168.1.20/light/on",
                     "http_post": "آدرس | متن ارسالی، مثلاً http://host/api | {\"on\": true}"}.get(action, ""),
            "hotkey": "مثلاً ctrl+shift+t یا win+d (برای Alt+F4 تایپ کنید یا از «عمل جدید» استفاده کنید)",
            None: "",
        }
        h = hints[kind]
        self.param_hint.setText(h if isinstance(h, str) else "")

    # ---------- دکمه‌ها ----------
    def browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "انتخاب برنامه", "",
            "Programs (*.exe *.lnk *.bat *.cmd);;All files (*)")
        if path:
            self.param_edit.setText(path)

    def key_changed(self, seq):
        text = seq.toString()
        if text:
            self.param_edit.setText(qt_seq_to_text(text))

    def record_new(self):
        c = self.main.record_gesture()
        if c:
            self.fill_gestures("custom:" + c["id"])
            self.update_gesture_hint()

    def record_motion_new(self):
        m = self.main.record_motion()
        if m:
            self.fill_gestures("motion:" + m["id"])
            self.update_gesture_hint()

    def new_action_clicked(self):
        a = self.main.new_action()
        if a:
            self.fill_actions("custom:" + a["id"])
            self.update_param_ui()

    def test_action(self):
        action = self.action_combo.currentData()
        if action in CONTINUOUS:
            QMessageBox.information(
                self, "آزمایش", "این عمل فقط هنگام انجام ژست جلوی دوربین کار می‌کند.")
            return
        QTimer.singleShot(300, lambda: run_action(action, self.param_edit.text()))

    def try_accept(self):
        action = self.action_combo.currentData()
        kind = self.action_kind(action)
        gkey = self.gesture_combo.currentData() or ""
        if not gkey:
            QMessageBox.warning(self, "ژست", "یک ژست انتخاب کنید.")
            return
        if kind and not self.param_edit.text().strip():
            QMessageBox.warning(self, "پارامتر", "پارامتر این عمل را وارد کنید.")
            return
        if (gkey.startswith(("motion:", "swipe_", "seq:"))
                or self.hold_spin.value() > 0) \
                and action in CONTINUOUS and action != "none":
            QMessageBox.warning(
                self, "ژست متحرک",
                "ژست‌های متحرک (و کشیدن دست) فقط برای عمل‌های لحظه‌ای مناسب‌اند، "
                "نه حرکت نشانگر، کشیدن یا اسکرول.")
            return
        if (not self.confirm_chk.isChecked()
                and is_dangerous(action, self.param_edit.text(), self.main.custom_actions)):
            if QMessageBox.question(
                    self, "عمل خطرناک",
                    "این عمل می‌تواند پنجره را ببندد یا سیستم را قفل کند.\n"
                    "«نیاز به تأیید با نگه‌داشتن ژست» فعال شود؟") == \
                    QMessageBox.StandardButton.Yes:
                self.confirm_chk.setChecked(True)
        label = action_label(action, self.main.custom_actions).split(" › ")[-1]
        name = self.name_edit.text().strip() or \
            f"{self.gesture_combo.currentText()} → {label}"
        self.binding.update({
            "name": name, "gesture": gkey, "action": action,
            "param": self.param_edit.text().strip() if kind else "",
            "enabled": self.enabled_check.isChecked(),
            "hold": round(self.hold_spin.value(), 1),
            "confirm": self.confirm_chk.isChecked(),
            "need_gesture": self.need_combo.currentData() or "",
        })
        self.accept()


class SettingsTab(QWidget):
    changed = pyqtSignal()

    def __init__(self, settings):
        super().__init__()
        self.widgets = {}
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)
        inner = QWidget()
        scroll.setWidget(inner)
        lay = QVBoxLayout(inner)

        # ---- دوربین و فاصله ----
        cam = QGroupBox("📷 دوربین و تشخیص از فاصله")
        f1 = QFormLayout(cam)
        self._build(f1, CAMERA_SPEC, settings)
        self.res_combo = QComboBox()
        self.res_combo.addItem("640×480 — سریع", 640)
        self.res_combo.addItem("1280×720 — پیشنهادی برای فاصله", 1280)
        self.res_combo.addItem("1920×1080 — دورترین، سنگین‌تر", 1920)
        self.res_combo.setCurrentIndex(
            max(self.res_combo.findData(int(settings["cam_width"])), 0))
        self.res_combo.currentIndexChanged.connect(self.changed.emit)
        f1.addRow("کیفیت تصویر دوربین:", self.res_combo)
        self.far_check = QCheckBox("حالت دور: زوم خودکار روی دست + جستجوی نواحی تصویر")
        self.far_check.setChecked(bool(settings["far_mode"]))
        self.far_check.toggled.connect(self.changed.emit)
        f1.addRow("", self.far_check)
        self.scan_combo = QComboBox()
        self.scan_combo.addItem("عادی — سریع", 0)
        self.scan_combo.addItem("دور — پیشنهادی", 1)
        self.scan_combo.addItem("خیلی دور — دقیق‌تر ولی کندتر هنگام جستجو", 2)
        self.scan_combo.setCurrentIndex(
            max(self.scan_combo.findData(int(settings["scan_level"])), 0))
        self.scan_combo.currentIndexChanged.connect(self.changed.emit)
        f1.addRow("دقت جستجوی دست در کل تصویر:", self.scan_combo)
        self.enh_check = QCheckBox("بهبود خودکار نور و کنتراست (برای نور کم)")
        self.enh_check.setChecked(bool(settings["enhance"]))
        self.enh_check.toggled.connect(self.changed.emit)
        f1.addRow("", self.enh_check)
        hint = QLabel("برای دست‌های دور، کیفیت 1280×720 یا بالاتر و «حالت دور» را روشن "
                      "نگه دارید و ناحیهٔ فعال (حاشیه) را کمتر کنید. پیدا کردن اولیهٔ "
                      "دست دور ممکن است چند فریم طول بکشد.")
        hint.setWordWrap(True)
        hint.setProperty("muted", True)
        f1.addRow("", hint)
        self.btn_scan = QPushButton("🔍 جستجوی دوربین‌های موجود")
        f1.addRow("", self.btn_scan)
        lay.addWidget(cam)

        # ---- حرکت و کلیک ----
        box = QGroupBox("🖱️ حرکت، کلیک و ژست‌ها")
        form = QFormLayout(box)
        self._build(form, SETTINGS_SPEC, settings)

        self.pointer_combo = QComboBox()
        self.pointer_combo.addItem("ریشهٔ انگشت اشاره (پایدارتر)", 5)
        self.pointer_combo.addItem("مفصل میانی اشاره", 6)
        self.pointer_combo.addItem("نوک انگشت اشاره (حساس‌تر)", 8)
        self.pointer_combo.setCurrentIndex(
            max(self.pointer_combo.findData(settings["pointer_landmark"]), 0))
        self.pointer_combo.currentIndexChanged.connect(self.changed.emit)
        form.addRow("نقطهٔ کنترل نشانگر:", self.pointer_combo)

        self.show_lm = QCheckBox("نمایش اسکلت دست روی تصویر")
        self.show_lm.setChecked(bool(settings["show_landmarks"]))
        self.show_lm.toggled.connect(self.changed.emit)
        form.addRow("", self.show_lm)
        lay.addWidget(box)

        # ---- ژست‌های متحرک ----
        mbox = QGroupBox("🌀 ژست‌های متحرک (حرکت دست)")
        mform = QFormLayout(mbox)
        self._build(mform, MOTION_SPEC, settings)
        lay.addWidget(mbox)

        # ---- پیشرفته ----
        adv = QGroupBox("⚙️ پیشرفته (فقط در صورت اشتباه تشخیص دادن)")
        aform = QFormLayout(adv)
        self._build(aform, ADVANCED_SPEC, settings)
        lay.addWidget(adv)

        self.btn_reset = QPushButton("بازگشت تنظیمات به پیش‌فرض")
        self.btn_reset.setProperty("variant", "danger")
        lay.addWidget(self.btn_reset)
        lay.addStretch(1)

    def _build(self, form, spec, settings):
        for key, label, kind, lo, hi, step in spec:
            if kind == "int":
                w = QSpinBox()
                w.setRange(int(lo), int(hi))
                w.setSingleStep(int(step))
                w.setValue(int(settings[key]))
            else:
                w = QDoubleSpinBox()
                w.setRange(lo, hi)
                w.setSingleStep(step)
                w.setDecimals(2)
                w.setValue(float(settings[key]))
            w.valueChanged.connect(self.changed.emit)
            form.addRow(label + ":", w)
            self.widgets[key] = w

    def values(self):
        v = {k: w.value() for k, w in self.widgets.items()}
        v["pointer_landmark"] = int(self.pointer_combo.currentData())
        v["show_landmarks"] = self.show_lm.isChecked()
        v["far_mode"] = self.far_check.isChecked()
        v["cam_width"] = int(self.res_combo.currentData())
        v["scan_level"] = int(self.scan_combo.currentData())
        v["enhance"] = self.enh_check.isChecked()
        if v["vote_min"] > v["vote_frames"]:
            v["vote_min"] = v["vote_frames"]
        return v

    def set_values(self, settings):
        for k, w in self.widgets.items():
            w.blockSignals(True)
            w.setValue(settings[k])
            w.blockSignals(False)
        for w, setter in (
                (self.pointer_combo, lambda w: w.setCurrentIndex(
                    max(w.findData(settings["pointer_landmark"]), 0))),
                (self.res_combo, lambda w: w.setCurrentIndex(
                    max(w.findData(int(settings["cam_width"])), 0))),
                (self.show_lm, lambda w: w.setChecked(bool(settings["show_landmarks"]))),
                (self.scan_combo, lambda w: w.setCurrentIndex(
                    max(w.findData(int(settings["scan_level"])), 0))),
                (self.enh_check, lambda w: w.setChecked(bool(settings["enhance"]))),
                (self.far_check, lambda w: w.setChecked(bool(settings["far_mode"])))):
            w.blockSignals(True)
            setter(w)
            w.blockSignals(False)


class StepDialog(QDialog):
    """ویرایش یک مرحله از یک عمل دلخواه"""

    def __init__(self, parent=None, step=None):
        super().__init__(parent)
        self.setWindowTitle("مرحلهٔ عمل")
        self.setMinimumWidth(520)
        self.step = dict(step) if step else {"type": "hotkey", "param": ""}

        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.type_combo = QComboBox()
        for key, label, _ in STEP_TYPES:
            self.type_combo.addItem(label, key)
        self.type_combo.setCurrentIndex(
            max(self.type_combo.findData(self.step["type"]), 0))
        form.addRow("نوع مرحله:", self.type_combo)

        self.hot_combo = QComboBox()
        self.hot_combo.addItem("— انتخاب میانبر رایج —", "")
        for label, keys in POPULAR_HOTKEYS:
            self.hot_combo.addItem(label, keys)
        self.hot_label = QLabel("میانبر رایج:")
        form.addRow(self.hot_label, self.hot_combo)

        self.act_combo = QComboBox()
        for key, label, group, kind in ACTIONS:
            if key not in CONTINUOUS and kind is None:
                self.act_combo.addItem(f"{group} › {label}", key)
        self.act_label = QLabel("عمل:")
        form.addRow(self.act_label, self.act_combo)

        self.param_edit = QLineEdit(str(self.step.get("param", "")))
        self.btn_browse = QPushButton("انتخاب برنامه…")
        prow = QHBoxLayout()
        prow.addWidget(self.param_edit, 1)
        prow.addWidget(self.btn_browse)
        self.param_label = QLabel("مقدار:")
        form.addRow(self.param_label, prow)

        self.key_edit = QKeySequenceEdit()
        self.key_label = QLabel("ضبط کلیدها:")
        form.addRow(self.key_label, self.key_edit)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.hint.setProperty("muted", True)
        form.addRow("", self.hint)
        lay.addLayout(form)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                              QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("تأیید")
        bb.button(QDialogButtonBox.StandardButton.Cancel).setText("انصراف")
        bb.accepted.connect(self.try_accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

        if self.step["type"] == "run_action":
            self.act_combo.setCurrentIndex(
                max(self.act_combo.findData(self.step.get("param", "")), 0))

        self.type_combo.currentIndexChanged.connect(self.update_ui)
        self.hot_combo.activated.connect(self.hot_chosen)
        self.btn_browse.clicked.connect(self.browse)
        self.key_edit.keySequenceChanged.connect(self.key_changed)
        self.update_ui()

    def update_ui(self):
        t = self.type_combo.currentData()
        kind = STEP_INFO[t][2]
        self.param_edit.setVisible(kind in ("text", "hotkey", "file"))
        self.param_label.setVisible(kind in ("text", "hotkey", "file"))
        self.btn_browse.setVisible(kind == "file")
        self.hot_combo.setVisible(kind == "hotkey")
        self.hot_label.setVisible(kind == "hotkey")
        self.key_edit.setVisible(kind == "hotkey")
        self.key_label.setVisible(kind == "hotkey")
        self.act_combo.setVisible(kind == "action")
        self.act_label.setVisible(kind == "action")
        self.hint.setText({
            "hotkey": "کلیدها را با + بنویسید: alt+f4 ، ctrl+shift+t ، win+d . "
                      "توجه: ویندوز Alt+F4 را مستقیم نمی‌گیرد؛ آن را تایپ کنید یا از لیست انتخاب کنید.",
            "key": "نام یک کلید: enter ، esc ، tab ، space ، f5 ، left ، pagedown …",
            "type_text": "متنی که تایپ می‌شود (فارسی هم پشتیبانی می‌شود)",
            "wait": "مدت صبر به میلی‌ثانیه، مثلاً 500",
            "scroll": "مثلاً 300 برای بالا یا -300 برای پایین",
            "open_url": "مثلاً youtube.com",
            "run_command": "دستور کامل خط فرمان",
            "click_at": "مثلاً 800,450,left",
            "move_to": "مثلاً 800,450",
            "ha_service": "مثلاً light.turn_on light.salon",
            "hue_light": "مثلاً 3 toggle",
            "obs_request": "مثلاً ToggleRecord",
            "http_get": "آدرس کامل، مثلاً http://192.168.1.20/light/on",
            "http_post": "آدرس | متن ارسالی (JSON هم می‌شود)، مثلاً http://host/api | {\"on\": true}",
        }.get(t, ""))

    def hot_chosen(self, _i):
        keys = self.hot_combo.currentData()
        if keys:
            self.param_edit.setText(keys)

    def browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "انتخاب برنامه", "",
            "Programs (*.exe *.lnk *.bat *.cmd);;All files (*)")
        if path:
            self.param_edit.setText(path)

    def key_changed(self, seq):
        text = seq.toString()
        if text:
            self.param_edit.setText(qt_seq_to_text(text))

    def try_accept(self):
        t = self.type_combo.currentData()
        kind = STEP_INFO[t][2]
        if kind == "action":
            param = self.act_combo.currentData() or ""
        else:
            param = self.param_edit.text().strip() if kind else ""
        if kind in ("text", "hotkey", "file") and not param:
            QMessageBox.warning(self, "مقدار", "مقدار این مرحله را وارد کنید.")
            return
        if t in ("wait", "scroll"):
            try:
                float(param)
            except ValueError:
                QMessageBox.warning(self, "مقدار", "یک عدد وارد کنید.")
                return
        self.step = {"type": t, "param": param}
        self.accept()


class ActionDialog(QDialog):
    """ساخت یا ویرایش یک عمل دلخواه (یک یا چند مرحله پشت سر هم)"""

    def __init__(self, main, action=None):
        super().__init__(main)
        self.main = main
        self.setWindowTitle("ویرایش عمل" if action else "عمل جدید")
        self.setMinimumSize(560, 460)
        self.action = copy.deepcopy(action) if action else {
            "id": uuid.uuid4().hex[:8], "name": "", "steps": []}
        if "id" not in self.action:
            self.action["id"] = uuid.uuid4().hex[:8]

        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit(self.action.get("name", ""))
        self.name_edit.setPlaceholderText("مثلاً: بستن پنجره")
        form.addRow("نام عمل:", self.name_edit)
        self.only_edit = QLineEdit(self.action.get("only_if", ""))
        self.only_edit.setPlaceholderText("خالی = همیشه ؛ مثال: exe:chrome  یا  title:Docs")
        form.addRow("فقط وقتی این برنامه فعال است:", self.only_edit)
        self.repeat_spin = QSpinBox()
        self.repeat_spin.setRange(1, 50)
        self.repeat_spin.setValue(int(self.action.get("repeat", 1) or 1))
        form.addRow("تعداد تکرار:", self.repeat_spin)
        lay.addLayout(form)

        info = QLabel("مرحله‌ها به ترتیب اجرا می‌شوند. مثلاً برای بستن پنجره فقط یک مرحلهٔ "
                      "«میانبر صفحه‌کلید» با alt+f4 کافی است.")
        info.setWordWrap(True)
        info.setProperty("muted", True)
        lay.addWidget(info)

        self.list = QListWidget()
        lay.addWidget(self.list, 1)

        r = QHBoxLayout()
        self.btn_add = QPushButton("➕ مرحله")
        self.btn_add.setProperty("variant", "primary")
        self.btn_edit = QPushButton("✏️ ویرایش")
        self.btn_del = QPushButton("🗑️ حذف")
        self.btn_del.setProperty("variant", "danger")
        self.btn_up = QPushButton("▲")
        self.btn_down = QPushButton("▼")
        for b in (self.btn_add, self.btn_edit, self.btn_del, self.btn_up,
                  self.btn_down):
            r.addWidget(b)
        lay.addLayout(r)

        self.btn_rec = QPushButton("⏺ ضبط ماکرو (ماوس و صفحه‌کلید)")
        lay.addWidget(self.btn_rec)
        self.test_lbl = QLabel("")
        self.test_lbl.setProperty("muted", True)
        self.btn_test = QPushButton("▶ آزمایش (۳ ثانیه بعد اجرا می‌شود)")
        lay.addWidget(self.btn_test)
        lay.addWidget(self.test_lbl)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                              QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("ذخیره")
        bb.button(QDialogButtonBox.StandardButton.Cancel).setText("انصراف")
        bb.accepted.connect(self.try_accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

        self.btn_add.clicked.connect(self.add_step)
        self.btn_edit.clicked.connect(self.edit_step)
        self.list.itemDoubleClicked.connect(lambda *_: self.edit_step())
        self.btn_del.clicked.connect(self.del_step)
        self.btn_up.clicked.connect(lambda: self.move_step(-1))
        self.btn_down.clicked.connect(lambda: self.move_step(1))
        self.btn_test.clicked.connect(self.test_steps)
        self.btn_rec.clicked.connect(self.record_macro)
        self.refresh()

    def refresh(self, select=None):
        self.list.clear()
        for i, st in enumerate(self.action["steps"]):
            self.list.addItem(f"{i + 1}.  {step_summary(st)}")
        if select is not None and 0 <= select < self.list.count():
            self.list.setCurrentRow(select)

    def add_step(self):
        dlg = StepDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.action["steps"].append(dlg.step)
            self.refresh(len(self.action["steps"]) - 1)

    def edit_step(self):
        r = self.list.currentRow()
        if r < 0:
            return
        dlg = StepDialog(self, self.action["steps"][r])
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.action["steps"][r] = dlg.step
            self.refresh(r)

    def del_step(self):
        r = self.list.currentRow()
        if r >= 0:
            del self.action["steps"][r]
            self.refresh(min(r, len(self.action["steps"]) - 1))

    def move_step(self, d_):
        r = self.list.currentRow()
        n = r + d_
        steps = self.action["steps"]
        if r < 0 or not 0 <= n < len(steps):
            return
        steps[r], steps[n] = steps[n], steps[r]
        self.refresh(n)

    def record_macro(self):
        dlg = MacroRecordDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.steps:
            self.action["steps"].extend(dlg.steps)
            self.refresh(len(self.action["steps"]) - 1)

    def test_steps(self):
        if not self.action["steps"]:
            return
        steps = list(self.action["steps"])
        self.test_lbl.setText("۳ ثانیه دیگر اجرا می‌شود؛ پنجرهٔ مورد نظر را فعال کنید…")
        only, rep_ = self.only_edit.text().strip(), self.repeat_spin.value()
        QTimer.singleShot(3000, lambda: (run_macro(steps, only, rep_),
                                         self.test_lbl.setText("اجرا شد.")))

    def try_accept(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "نام", "یک نام برای عمل بنویسید.")
            return
        if not self.action["steps"]:
            QMessageBox.warning(self, "مرحله", "حداقل یک مرحله اضافه کنید.")
            return
        self.action["name"] = name
        self.action["only_if"] = self.only_edit.text().strip()
        self.action["repeat"] = self.repeat_spin.value()
        self.accept()


class PathPreview(QWidget):
    """نمایش مسیر نرمال‌شدهٔ یک حرکت دست"""

    def __init__(self):
        super().__init__()
        self.path = None
        self.setMinimumSize(130, 130)

    def set_path(self, p):
        self.path = None if p is None else np.asarray(p, dtype=float)
        self.update()

    def paintEvent(self, _e):
        qp = QPainter(self)
        qp.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.path is None:
            return
        w, h = self.width(), self.height()
        pts = [QPointF((x + 0.5) * 0.8 * w + 0.1 * w,
                       (y + 0.5) * 0.8 * h + 0.1 * h) for x, y in self.path]
        qp.setPen(QPen(QColor("#6d8bff"), 3))
        for a, b in zip(pts, pts[1:]):
            qp.drawLine(a, b)
        qp.setPen(QPen(QColor("#2fd6a1"), 10))
        qp.drawPoint(pts[0])
        qp.setPen(QPen(QColor("#ff5c75"), 10))
        qp.drawPoint(pts[-1])


class MotionRecordDialog(QDialog):
    SAMPLES = 3
    WINDOW = 2.8

    def __init__(self, engine, cfg, default_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ضبط ژست متحرک")
        self.engine = engine
        self.cfg = cfg
        self.result_motion = None
        self.templates = []
        self.majors = []
        self.count = 0

        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit(default_name)
        form.addRow("نام ژست:", self.name_edit)
        self.pose_combo = QComboBox()
        self.pose_combo.addItem("فقط با همان حالت دستی که موقع ضبط داشتید (پیشنهادی)", "lock")
        self.pose_combo.addItem("با هر حالت دست", "any")
        form.addRow("حالت دست:", self.pose_combo)
        lay.addLayout(form)

        mid = QHBoxLayout()
        self.video = QLabel("در انتظار تصویر دوربین…")
        self.video.setFixedSize(420, 315)
        self.video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video.setStyleSheet("background:#111; color:#aaa;")
        mid.addWidget(self.video)
        self.preview = PathPreview()
        mid.addWidget(self.preview, 1)
        lay.addLayout(mid)

        self.status = QLabel(
            f"حرکت دلخواه را {self.SAMPLES} بار انجام می‌دهیم تا دقیق شود. "
            "«شروع نمونه» را بزنید، بعد از ۳ ثانیه حرکت کنید (مثلاً کشیدن دایره، "
            "موج دادن یا زیگزاگ) و در پایان لحظه‌ای مکث کنید. دست را همیشه با "
            "یک حالت ثابت (مثلاً کف دست باز) نگه دارید.")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        self.bar = QProgressBar()
        self.bar.setRange(0, self.SAMPLES)
        lay.addWidget(self.bar)

        row = QHBoxLayout()
        self.btn_start = QPushButton("شروع نمونه ۱")
        self.btn_start.setProperty("variant", "primary")
        self.btn_cancel = QPushButton("انصراف")
        row.addWidget(self.btn_start)
        row.addWidget(self.btn_cancel)
        lay.addLayout(row)

        self.btn_start.clicked.connect(self.start_clicked)
        self.btn_cancel.clicked.connect(self.reject)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        engine.frame_ready.connect(self.on_frame)
        engine.motion_recorded.connect(self.on_samples)

    def on_frame(self, img):
        self.video.setPixmap(QPixmap.fromImage(img).scaled(
            self.video.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))

    def start_clicked(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "نام", "یک نام برای ژست بنویسید.")
            return
        self.btn_start.setEnabled(False)
        self.count = 3
        self.status.setText(f"آماده شوید… {self.count}")
        self.timer.start(1000)

    def tick(self):
        self.count -= 1
        if self.count > 0:
            self.status.setText(f"آماده شوید… {self.count}")
            return
        self.timer.stop()
        self.status.setText("حالا حرکت دهید! 👋 (در پایان لحظه‌ای مکث کنید)")
        self.engine.start_motion_record(self.WINDOW)

    def on_samples(self, samples):
        seg = segment_from_samples(samples, self.cfg) if samples else None
        tpl = motion_template(seg)
        if tpl is None:
            self.status.setText(
                "حرکتی تشخیص داده نشد. دست را داخل کادر نگه دارید، "
                "حرکت را سریع‌تر و بزرگ‌تر انجام دهید و دوباره امتحان کنید.")
            self.btn_start.setEnabled(True)
            return
        norm, major, _share = tpl
        self.templates.append(norm)
        self.majors.append(major)
        self.preview.set_path(norm)
        self.bar.setValue(len(self.templates))
        if len(self.templates) < self.SAMPLES:
            self.status.setText(
                f"نمونهٔ {len(self.templates)} ثبت شد ✅ — همان حرکت را دوباره انجام دهید.")
            self.btn_start.setText(f"شروع نمونه {len(self.templates) + 1}")
            self.btn_start.setEnabled(True)
            return
        pose = "any"
        if self.pose_combo.currentData() == "lock":
            pose = Counter(self.majors).most_common(1)[0][0]
        self.result_motion = {
            "id": uuid.uuid4().hex[:8],
            "name": self.name_edit.text().strip(),
            "pose": pose,
            "templates": [t.tolist() for t in self.templates],
        }
        self.accept()

    def done(self, r):
        self.timer.stop()
        try:
            self.engine.frame_ready.disconnect(self.on_frame)
            self.engine.motion_recorded.disconnect(self.on_samples)
        except Exception:
            pass
        self.engine.cancel_motion_record()
        super().done(r)


class AppearanceTab(QWidget):
    changed = pyqtSignal()
    SWATCHES = ["#6d8bff", "#a78bfa", "#ec4899", "#f97316",
                "#22c55e", "#06b6d4", "#eab308", "#ef4444"]

    def __init__(self, settings):
        super().__init__()
        self.accent = settings["accent"]
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)
        inner = QWidget()
        scroll.setWidget(inner)
        lay = QVBoxLayout(inner)

        box = QGroupBox("🎨 ظاهر برنامه")
        form = QFormLayout(box)

        self.theme = QComboBox()
        self.theme.addItem("تیره", "dark")
        self.theme.addItem("روشن", "light")
        self.theme.addItem("نیمه‌شب (مشکی کامل)", "midnight")
        self.theme.setCurrentIndex(max(self.theme.findData(settings["theme"]), 0))
        form.addRow("تم:", self.theme)

        arow = QHBoxLayout()
        self.accent_btn = QPushButton("انتخاب رنگ…")
        arow.addWidget(self.accent_btn)
        for col in self.SWATCHES:
            b = QPushButton()
            b.setFixedSize(26, 26)
            b.setStyleSheet(f"background:{col}; border-radius:13px; border:none;")
            b.clicked.connect(lambda _=False, c=col: self.set_accent(c))
            arow.addWidget(b)
        arow.addStretch(1)
        form.addRow("رنگ اصلی:", arow)
        self.accent_preview = QLabel("   ")
        form.addRow("رنگ فعلی:", self.accent_preview)

        self.font_size = QSpinBox()
        self.font_size.setRange(8, 16)
        self.font_size.setValue(int(settings["font_size"]))
        form.addRow("اندازهٔ نوشته:", self.font_size)

        self.radius = QSpinBox()
        self.radius.setRange(0, 24)
        self.radius.setValue(int(settings["radius"]))
        form.addRow("گردی گوشه‌ها:", self.radius)

        self.density = QComboBox()
        self.density.addItem("راحت", "comfortable")
        self.density.addItem("فشرده", "compact")
        self.density.setCurrentIndex(max(self.density.findData(settings["density"]), 0))
        form.addRow("تراکم:", self.density)

        self.rtl = QCheckBox("چیدمان راست‌به‌چپ (فارسی)")
        self.rtl.setChecked(bool(settings["ui_rtl"]))
        form.addRow("", self.rtl)
        self.preview_chk = QCheckBox("نمایش پیش‌نمایش دوربین (خاموش کردن مصرف CPU را کم می‌کند)")
        self.preview_chk.setChecked(bool(settings["show_preview"]))
        form.addRow("", self.preview_chk)
        self.aot = QCheckBox("همیشه روی بقیهٔ پنجره‌ها")
        self.aot.setChecked(bool(settings["always_on_top"]))
        form.addRow("", self.aot)
        lay.addWidget(box)

        self.btn_reset = QPushButton("بازگشت ظاهر به پیش‌فرض")
        self.btn_reset.setProperty("variant", "danger")
        lay.addWidget(self.btn_reset)
        lay.addStretch(1)

        self.accent_btn.clicked.connect(self.pick_color)
        self.theme.currentIndexChanged.connect(self.changed.emit)
        self.density.currentIndexChanged.connect(self.changed.emit)
        for w in (self.font_size, self.radius):
            w.valueChanged.connect(self.changed.emit)
        for w in (self.rtl, self.preview_chk, self.aot):
            w.toggled.connect(self.changed.emit)
        self.update_preview()

    def update_preview(self):
        self.accent_preview.setStyleSheet(
            f"background:{self.accent}; border-radius:8px;")

    def set_accent(self, col):
        self.accent = col
        self.update_preview()
        self.changed.emit()

    def pick_color(self):
        c = QColorDialog.getColor(QColor(self.accent), self, "انتخاب رنگ اصلی")
        if c.isValid():
            self.set_accent(c.name())

    def values(self):
        return {
            "theme": self.theme.currentData(),
            "accent": self.accent,
            "font_size": self.font_size.value(),
            "radius": self.radius.value(),
            "density": self.density.currentData(),
            "ui_rtl": self.rtl.isChecked(),
            "show_preview": self.preview_chk.isChecked(),
            "always_on_top": self.aot.isChecked(),
        }

    def set_values(self, st):
        widgets = (self.theme, self.density, self.font_size, self.radius,
                   self.rtl, self.preview_chk, self.aot)
        for w in widgets:
            w.blockSignals(True)
        self.theme.setCurrentIndex(max(self.theme.findData(st["theme"]), 0))
        self.density.setCurrentIndex(max(self.density.findData(st["density"]), 0))
        self.font_size.setValue(int(st["font_size"]))
        self.radius.setValue(int(st["radius"]))
        self.rtl.setChecked(bool(st["ui_rtl"]))
        self.preview_chk.setChecked(bool(st["show_preview"]))
        self.aot.setChecked(bool(st["always_on_top"]))
        for w in widgets:
            w.blockSignals(False)
        self.accent = st["accent"]
        self.update_preview()


class AboutDialog(QDialog):
    def __init__(self, main):
        super().__init__(main)
        self.setWindowTitle(f"دربارهٔ {APP_NAME}")
        self.setMinimumWidth(580)
        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        title = QLabel(f"🖐️  {APP_NAME}")
        title.setObjectName("title")
        ver = QLabel(f"نسخهٔ {APP_VERSION}")
        ver.setProperty("muted", True)
        lay.addWidget(title)
        lay.addWidget(ver)

        body = QLabel(
            "<div dir='rtl'>"
            "<p>با این برنامه فقط با یک وب‌کم و حرکت دست، کامپیوتر را کنترل می‌کنید. "
            "همهٔ پردازش‌ها روی همین کامپیوتر انجام می‌شود و تصویر دوربین ذخیره یا ارسال نمی‌شود.</p>"
            "<p><b>امکانات</b></p><ul>"
            "<li>حرکت ماوس، کلیک، کشیدن و اسکرول با ژست</li>"
            "<li>ژست‌های ثابت (حالت دست) و متحرک (حرکت دست) دلخواه</li>"
            "<li>عمل‌های دلخواه: میانبر صفحه‌کلید، باز کردن برنامه یا سایت، تایپ متن و ماکرو</li>"
            "<li>پروفایل ارائهٔ پاورپوینت با کشیدن دست</li>"
            "<li>قفل روی دست شما، وقتی چند نفر جلوی دوربین‌اند</li>"
            "<li>تشخیص از فاصله: زوم خودکار روی دست، جستجو در کل تصویر و پوشش لبه‌ها</li>"
            "<li>ظاهر قابل شخصی‌سازی: تم، رنگ، اندازه و چیدمان</li>"
            "<li>پروفایل خودکار برای هر برنامه، آیکون کنار ساعت و میانبر سراسری</li>"
            "<li>کالیبراسیون، حالت تمرین، کنترل صدا و زوم با دو دست، کلیک با مکث</li>"
            "<li>ژست با نگه‌داشتن، ترتیب ژست‌ها، پشتیبان‌گیری و چندمانیتوره</li>"
            "<li>ابزار ارائه روی صفحه (لیزر، نقاشی، نورافکن)، کیبورد هوایی و نوشتن در هوا</li>"
            "<li>دستور صوتی آفلاین، کنترل با سر و پلک، حالت لرزش دست، یادگیری ژست از نمونه‌ها</li>"
            "<li>ضبط ماکرو، افزونه‌ها، اتصال به Home Assistant / MQTT / Hue / OBS</li>"
            "<li>کنترل از گوشی، گوشی به‌عنوان دوربین، آمار و یادآور استراحت، زبان انگلیسی</li>"
            "</ul>"
            "<p><b>شروع سریع</b></p><ol>"
            "<li>«شروع دوربین» را بزنید و کف دست باز را نشان دهید.</li>"
            "<li>با انگشت اشاره (شست باز) نشانگر را حرکت دهید.</li>"
            "<li>برای کلیک، شست را روی انگشت اشاره ببندید.</li>"
            "<li>ژست‌ها و عمل‌ها را در تب «ژست‌ها و دستورها» تغییر دهید.</li>"
            "</ol>"
            "<p><b>کلیدهای میانبر:</b> F1 = این پنجره، Delete = حذف ردیف انتخاب‌شده.</p>"
            "<p>ساخته‌شده با MediaPipe، OpenCV، PyQt6، PyAutoGUI و NumPy.</p>"
            "</div>")
        body.setTextFormat(Qt.TextFormat.RichText)
        body.setWordWrap(True)
        lay.addWidget(body)

        self.info = system_info()
        info_lbl = QLabel(self.info)
        info_lbl.setProperty("muted", True)
        info_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        info_lbl.setStyleSheet("font-family: Consolas, monospace;")
        lay.addWidget(info_lbl)

        row = QHBoxLayout()
        self.btn_folder = QPushButton("📂 باز کردن پوشهٔ تنظیمات")
        self.btn_copy = QPushButton("📋 کپی اطلاعات سیستم")
        self.btn_close = QPushButton("بستن")
        self.btn_close.setProperty("variant", "primary")
        for b in (self.btn_folder, self.btn_copy, self.btn_close):
            row.addWidget(b)
        lay.addLayout(row)

        self.btn_folder.clicked.connect(self.open_folder)
        self.btn_copy.clicked.connect(self.copy_info)
        self.btn_close.clicked.connect(self.accept)

    def open_folder(self):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            open_app(str(CONFIG_DIR))
        except Exception as e:
            QMessageBox.warning(self, "خطا", str(e))

    def copy_info(self):
        QApplication.clipboard().setText(self.info)
        self.btn_copy.setText("✅ کپی شد")


HAND_SHAPES = [(30, 48, 40, 34), (30, 22, 8, 34), (41, 15, 8, 40),
               (52, 15, 8, 40), (63, 22, 8, 34)]


def make_app_icon(accent="#6d8bff", size=128):
    """آیکون برنامه (پنجره و کنار ساعت): مربع گرادیان با شکل دست"""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    k = size / 100.0
    g = QLinearGradient(0, 0, size, size)
    g.setColorAt(0, QColor(mix_colors(accent, "#ffffff", 0.25)))
    g.setColorAt(1, QColor(accent))
    p.setBrush(QBrush(g))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(QRectF(0, 0, size, size), 22 * k, 22 * k)
    p.setBrush(QColor("#ffffff"))
    for x, y, w, h in HAND_SHAPES:
        p.drawRoundedRect(QRectF(x * k, y * k, w * k, h * k), 4 * k, 4 * k)
    p.save()
    p.translate(28 * k, 62 * k)
    p.rotate(-35)
    p.drawRoundedRect(QRectF(-4 * k, -16 * k, 8 * k, 24 * k), 4 * k, 4 * k)
    p.restore()
    p.end()
    return QIcon(pm)


class HotkeyWatcher(QThread):
    """میانبر سراسری (حتی وقتی برنامه پنهان است) — فقط ویندوز"""
    triggered = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.keys = {}
        self.keys_text = {}
        self._down = {}
        self._quit = False

    def set_hotkeys(self, mapping):
        self.keys = {n: parse_hotkey(t) for n, t in mapping.items()}
        self.keys = {n: v for n, v in self.keys.items() if v}
        self.keys_text = {n: t for n, t in mapping.items() if parse_hotkey(t)}

    def run_pynput(self):
        """میانبر سراسری در لینوکس (X11) با pynput — اختیاری؛ بدون آن فقط منوی کنار ساعت"""
        try:
            from pynput import keyboard
        except Exception:
            return

        def fmt(text):
            out = []
            for tok in text.lower().replace(" ", "").split("+"):
                if tok in ("ctrl", "control"):
                    out.append("<ctrl>")
                elif tok in ("alt", "shift"):
                    out.append(f"<{tok}>")
                elif tok in ("win", "meta"):
                    out.append("<cmd>")
                elif len(tok) == 1:
                    out.append(tok)
                else:
                    out.append(f"<{tok}>")
            return "+".join(out)

        listener, sig = None, None
        while not self._quit:
            cur = dict(self.keys_text)
            if cur != sig:
                if listener is not None:
                    listener.stop()
                mapping = {fmt(t): (lambda n=n: self.triggered.emit(n))
                           for n, t in cur.items()}
                try:
                    listener = keyboard.GlobalHotKeys(mapping)
                    listener.start()
                except Exception:
                    listener = None
                sig = cur
            self.msleep(200)
        if listener is not None:
            listener.stop()

    def stop(self):
        self._quit = True
        self.wait(1000)

    def run(self):
        if not IS_WIN:
            self.run_pynput()
            return
        try:
            import ctypes
            user32 = ctypes.windll.user32
        except Exception:
            return
        while not self._quit:
            for name, (mods, vk) in list(self.keys.items()):
                pressed = (all(user32.GetAsyncKeyState(m) & 0x8000 for m in mods)
                           and bool(user32.GetAsyncKeyState(vk) & 0x8000))
                if pressed and not self._down.get(name):
                    self._down[name] = True
                    self.triggered.emit(name)
                elif not pressed:
                    self._down[name] = False
            self.msleep(40)


class BehaviorTab(QWidget):
    changed = pyqtSignal()

    def __init__(self, settings, screen_labels):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)
        inner = QWidget()
        scroll.setWidget(inner)
        lay = QVBoxLayout(inner)

        g1 = QGroupBox("🚀 شروع و پنهان‌سازی")
        f1 = QFormLayout(g1)
        self.autostart = QCheckBox("اجرای خودکار همراه روشن شدن ویندوز")
        self.start_min = QCheckBox("شروع به‌صورت پنهان (فقط آیکون کنار ساعت)")
        self.auto_cam = QCheckBox("روشن کردن خودکار دوربین هنگام شروع")
        self.close_tray = QCheckBox("با بستن پنجره، به کنار ساعت برود (خروج از منوی آیکون)")
        for w, k in ((self.autostart, "autostart"), (self.start_min, "start_minimized"),
                     (self.auto_cam, "auto_start_camera"),
                     (self.close_tray, "close_to_tray")):
            w.setChecked(bool(settings[k]))
            f1.addRow("", w)
        lay.addWidget(g1)

        g2 = QGroupBox("⌨️ میانبر سراسری (فقط ویندوز)")
        f2 = QFormLayout(g2)
        self.hk_toggle = QLineEdit(settings["hotkey_toggle"])
        self.hk_stop = QLineEdit(settings["hotkey_stop"])
        f2.addRow("مکث / ادامهٔ اجرای دستورها:", self.hk_toggle)
        f2.addRow("توقف اضطراری (خاموش کردن دوربین):", self.hk_stop)
        self.hk_note = QLabel("مثل ctrl+alt+h — حداقل یک کلید ترکیبی (ctrl, alt, shift, win) لازم است.")
        self.hk_note.setProperty("muted", True)
        self.hk_note.setWordWrap(True)
        f2.addRow("", self.hk_note)
        lay.addWidget(g2)

        g3 = QGroupBox("🖥️ مانیتور")
        f3 = QFormLayout(g3)
        self.monitor = QComboBox()
        self.monitor.addItem("مانیتور اصلی", 0)
        self.monitor.addItem("همهٔ مانیتورها (یکپارچه)", -1)
        for i, lb in enumerate(screen_labels, start=1):
            self.monitor.addItem(f"مانیتور {i}: {lb}", i)
        self.monitor.setCurrentIndex(max(self.monitor.findData(int(settings["monitor"])), 0))
        f3.addRow("نشانگر روی:", self.monitor)
        lay.addWidget(g3)

        g4 = QGroupBox("🎚️ کنترل پیوسته و دو دست")
        f4 = QFormLayout(g4)
        self.slider_step = QSpinBox()
        self.slider_step.setRange(3, 60)
        self.slider_step.setValue(int(settings["slider_step"]))
        self.zoom_step = QSpinBox()
        self.zoom_step.setRange(4, 80)
        self.zoom_step.setValue(int(settings["zoom_step"]))
        f4.addRow("هر چند پیکسل حرکت = یک پله صدا / جلو-عقب:", self.slider_step)
        f4.addRow("هر چند پیکسل فاصلهٔ دو دست = یک پله زوم:", self.zoom_step)
        lay.addWidget(g4)

        g5 = QGroupBox("⏱️ کلیک با مکث (بدون حرکت شست)")
        f5 = QFormLayout(g5)
        self.dwell = QCheckBox("وقتی نشانگر ثابت ماند، خودش کلیک کند")
        self.dwell.setChecked(bool(settings["dwell_click"]))
        self.dwell_time = QDoubleSpinBox()
        self.dwell_time.setRange(0.3, 5.0)
        self.dwell_time.setSingleStep(0.1)
        self.dwell_time.setValue(float(settings["dwell_time"]))
        self.dwell_radius = QSpinBox()
        self.dwell_radius.setRange(3, 60)
        self.dwell_radius.setValue(int(settings["dwell_radius"]))
        f5.addRow("", self.dwell)
        f5.addRow("مدت ثابت ماندن (ثانیه):", self.dwell_time)
        f5.addRow("حداکثر لرزش مجاز (پیکسل):", self.dwell_radius)
        lay.addWidget(g5)

        g6 = QGroupBox("🔔 بازخورد")
        f6 = QFormLayout(g6)
        self.sound = QCheckBox("صدای کوتاه هنگام کلیک، اجرای عمل و قفل شدن (ویندوز)")
        self.sound.setChecked(bool(settings["sound"]))
        f6.addRow("", self.sound)
        lay.addWidget(g6)
        lay.addStretch(1)

        for w in (self.autostart, self.start_min, self.auto_cam, self.close_tray,
                  self.dwell, self.sound):
            w.toggled.connect(self.changed.emit)
        for w in (self.slider_step, self.zoom_step, self.dwell_time, self.dwell_radius):
            w.valueChanged.connect(self.changed.emit)
        self.monitor.currentIndexChanged.connect(self.changed.emit)
        self.hk_toggle.editingFinished.connect(self.on_hk)
        self.hk_stop.editingFinished.connect(self.on_hk)

    def on_hk(self):
        bad = [n for n, w in (("مکث", self.hk_toggle), ("توقف", self.hk_stop))
               if w.text().strip() and not parse_hotkey(w.text())]
        self.hk_note.setText("⚠️ میانبر نامعتبر: " + "، ".join(bad) if bad else
                             "مثل ctrl+alt+h — حداقل یک کلید ترکیبی (ctrl, alt, shift, win) لازم است.")
        self.changed.emit()

    def values(self):
        return {
            "autostart": self.autostart.isChecked(),
            "start_minimized": self.start_min.isChecked(),
            "auto_start_camera": self.auto_cam.isChecked(),
            "close_to_tray": self.close_tray.isChecked(),
            "hotkey_toggle": self.hk_toggle.text().strip().lower(),
            "hotkey_stop": self.hk_stop.text().strip().lower(),
            "monitor": int(self.monitor.currentData()),
            "slider_step": self.slider_step.value(),
            "zoom_step": self.zoom_step.value(),
            "dwell_click": self.dwell.isChecked(),
            "dwell_time": self.dwell_time.value(),
            "dwell_radius": self.dwell_radius.value(),
            "sound": self.sound.isChecked(),
        }

    def set_values(self, st):
        pairs = ((self.autostart, "autostart"), (self.start_min, "start_minimized"),
                 (self.auto_cam, "auto_start_camera"), (self.close_tray, "close_to_tray"),
                 (self.dwell, "dwell_click"), (self.sound, "sound"))
        for w, k in pairs:
            w.blockSignals(True)
            w.setChecked(bool(st[k]))
            w.blockSignals(False)
        for w, k in ((self.slider_step, "slider_step"), (self.zoom_step, "zoom_step"),
                     (self.dwell_time, "dwell_time"), (self.dwell_radius, "dwell_radius")):
            w.blockSignals(True)
            w.setValue(st[k])
            w.blockSignals(False)
        self.hk_toggle.setText(st["hotkey_toggle"])
        self.hk_stop.setText(st["hotkey_stop"])
        self.monitor.blockSignals(True)
        self.monitor.setCurrentIndex(max(self.monitor.findData(int(st["monitor"])), 0))
        self.monitor.blockSignals(False)


class SequenceDialog(QDialog):
    """ساخت ترتیب ژست‌ها: مثلاً مشت ← کف دست"""

    def __init__(self, main, seq=None):
        super().__init__(main)
        self.main = main
        self.setWindowTitle("ترتیب ژست‌ها")
        self.setMinimumSize(480, 420)
        self.seq = copy.deepcopy(seq) if seq else {
            "id": uuid.uuid4().hex[:8], "name": "", "steps": [], "window": 2.5}

        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit(self.seq["name"])
        self.name_edit.setPlaceholderText("مثلاً: مشت و بعد کف دست")
        form.addRow("نام:", self.name_edit)
        self.window = QDoubleSpinBox()
        self.window.setRange(0.5, 8.0)
        self.window.setSingleStep(0.5)
        self.window.setValue(float(self.seq.get("window", 2.5)))
        form.addRow("مهلت کل ترتیب (ثانیه):", self.window)
        lay.addLayout(form)
        info = QLabel("ژست‌ها را به همان ترتیب پشت سر هم انجام دهید. بین ژست‌ها می‌توانید دست را "
                      "رها کنید. بعد در «ژست‌ها و دستورها» به یک عمل لحظه‌ای وصلش کنید.")
        info.setProperty("muted", True)
        info.setWordWrap(True)
        lay.addWidget(info)

        self.list = QListWidget()
        lay.addWidget(self.list, 1)
        r = QHBoxLayout()
        self.btn_add = QPushButton("➕ ژست")
        self.btn_add.setProperty("variant", "primary")
        self.btn_del = QPushButton("🗑️ حذف")
        self.btn_up = QPushButton("▲")
        self.btn_down = QPushButton("▼")
        for b in (self.btn_add, self.btn_del, self.btn_up, self.btn_down):
            r.addWidget(b)
        lay.addLayout(r)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                              QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("ذخیره")
        bb.button(QDialogButtonBox.StandardButton.Cancel).setText("انصراف")
        bb.accepted.connect(self.try_accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

        self.btn_add.clicked.connect(self.add_step)
        self.btn_del.clicked.connect(self.del_step)
        self.btn_up.clicked.connect(lambda: self.move(-1))
        self.btn_down.clicked.connect(lambda: self.move(1))
        self.refresh()

    def choices(self):
        return [(lb, k) for lb, k in self.main.gesture_choices()
                if not k.startswith(("swipe_", "motion:", "seq:"))]

    def refresh(self, select=None):
        self.list.clear()
        for i, k in enumerate(self.seq["steps"]):
            self.list.addItem(f"{i + 1}.  {self.main.gesture_label(k)}")
        if select is not None and 0 <= select < self.list.count():
            self.list.setCurrentRow(select)

    def add_step(self):
        ch = self.choices()
        labels = [lb for lb, _k in ch]
        text, ok = QInputDialog.getItem(self, "ژست", "یک ژست انتخاب کنید:",
                                        labels, 0, False)
        if ok and text in labels:
            self.seq["steps"].append(ch[labels.index(text)][1])
            self.refresh(len(self.seq["steps"]) - 1)

    def del_step(self):
        r = self.list.currentRow()
        if r >= 0:
            del self.seq["steps"][r]
            self.refresh(min(r, len(self.seq["steps"]) - 1))

    def move(self, d_):
        r = self.list.currentRow()
        n = r + d_
        steps = self.seq["steps"]
        if r < 0 or not 0 <= n < len(steps):
            return
        steps[r], steps[n] = steps[n], steps[r]
        self.refresh(n)

    def try_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "نام", "یک نام بنویسید.")
            return
        steps = self.seq["steps"]
        if len(steps) < 2:
            QMessageBox.warning(self, "ژست‌ها", "حداقل دو ژست لازم است.")
            return
        if any(steps[i] == steps[i + 1] for i in range(len(steps) - 1)):
            QMessageBox.warning(self, "ژست‌ها",
                                "دو ژست مساوی پشت سر هم نمی‌تواند باشد (تغییری دیده نمی‌شود).")
            return
        self.seq["name"] = self.name_edit.text().strip()
        self.seq["window"] = self.window.value()
        self.accept()


class RuleDialog(QDialog):
    """قانون پروفایل خودکار: وقتی این برنامه فعال بود، این پروفایل فعال شود"""

    def __init__(self, main, rule=None):
        super().__init__(main)
        self.main = main
        self.setWindowTitle("قانون برنامه")
        self.setMinimumWidth(520)
        self.rule = copy.deepcopy(rule) if rule else {
            "id": uuid.uuid4().hex[:8], "name": "", "match_type": "exe",
            "match": "", "profile": "default"}
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit(self.rule["name"])
        form.addRow("نام:", self.name_edit)
        self.type_combo = QComboBox()
        self.type_combo.addItem("نام فایل برنامه (مثل powerpnt.exe)", "exe")
        self.type_combo.addItem("بخشی از عنوان پنجره (مثل Google Slides)", "title")
        self.type_combo.setCurrentIndex(
            max(self.type_combo.findData(self.rule["match_type"]), 0))
        form.addRow("تطبیق با:", self.type_combo)
        self.match_edit = QLineEdit(self.rule["match"])
        form.addRow("مقدار:", self.match_edit)
        self.btn_detect = QPushButton("🎯 تشخیص برنامهٔ فعال (۳ ثانیه بعد)")
        form.addRow("", self.btn_detect)
        self.detect_lbl = QLabel("")
        self.detect_lbl.setProperty("muted", True)
        self.detect_lbl.setWordWrap(True)
        form.addRow("", self.detect_lbl)
        self.profile_combo = QComboBox()
        for label, key in main.all_profiles():
            self.profile_combo.addItem(label, key)
        self.profile_combo.setCurrentIndex(
            max(self.profile_combo.findData(self.rule["profile"]), 0))
        form.addRow("پروفایل:", self.profile_combo)
        lay.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                              QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("ذخیره")
        bb.button(QDialogButtonBox.StandardButton.Cancel).setText("انصراف")
        bb.accepted.connect(self.try_accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.btn_detect.clicked.connect(self.detect)

    def detect(self):
        self.detect_lbl.setText("در ۳ ثانیه به پنجرهٔ برنامهٔ مورد نظر بروید…")
        QTimer.singleShot(3000, self.do_detect)

    def do_detect(self):
        exe, title = get_active_app()
        if not exe and not title:
            self.detect_lbl.setText("برنامه‌ای تشخیص داده نشد (این قابلیت فقط ویندوز است).")
            return
        self.detect_lbl.setText(f"تشخیص داده شد: {exe} — «{title}»")
        if self.type_combo.currentData() == "exe" and exe:
            self.match_edit.setText(exe)
        elif title:
            self.match_edit.setText(title)
        if not self.name_edit.text().strip() and exe:
            self.name_edit.setText(exe.replace(".exe", ""))

    def try_accept(self):
        if not self.match_edit.text().strip():
            QMessageBox.warning(self, "مقدار", "مقدار تطبیق را وارد کنید.")
            return
        self.rule.update({
            "name": self.name_edit.text().strip() or self.match_edit.text().strip(),
            "match_type": self.type_combo.currentData(),
            "match": self.match_edit.text().strip(),
            "profile": self.profile_combo.currentData(),
        })
        self.accept()


class CalibrationDialog(QDialog):
    STEPS = [
        ("open", "۱ از ۵ — کف دست را کاملاً باز و رو به دوربین نگه دارید (انگشت‌ها کمی از هم باز)."),
        ("fist", "۲ از ۵ — دستتان را مشت کنید."),
        ("trigger", "۳ از ۵ — فقط انگشت اشاره را بالا بیاورید و شست را روی انگشت اشاره ببندید (حالت ماشه)."),
        ("point", "۴ از ۵ — فقط اشاره بالا و شست باز (شکل L). دست را کاملاً ثابت نگه دارید."),
        ("pinch", "۵ از ۵ — نوک شست و اشاره را به هم بچسبانید (نیشگون)."),
    ]
    FRAMES = 35

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self.setWindowTitle("کالیبراسیون ژست‌ها")
        self.setMinimumWidth(560)
        self.engine = engine
        self.idx = 0
        self.data = {}
        self.updates = {}
        self.count = 0
        self._busy = False

        lay = QVBoxLayout(self)
        self.video = QLabel("در انتظار تصویر دوربین…")
        self.video.setFixedSize(480, 360)
        self.video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video.setStyleSheet("background:#111; color:#aaa;")
        lay.addWidget(self.video, 0, Qt.AlignmentFlag.AlignCenter)
        self.status = QLabel("")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        self.bar = QProgressBar()
        self.bar.setRange(0, self.FRAMES)
        lay.addWidget(self.bar)
        row = QHBoxLayout()
        self.btn_start = QPushButton("شروع")
        self.btn_start.setProperty("variant", "primary")
        self.btn_apply = QPushButton("✅ اعمال تنظیمات")
        self.btn_apply.setProperty("variant", "primary")
        self.btn_apply.setVisible(False)
        self.btn_cancel = QPushButton("انصراف")
        row.addWidget(self.btn_start)
        row.addWidget(self.btn_apply)
        row.addWidget(self.btn_cancel)
        lay.addLayout(row)

        self.btn_start.clicked.connect(self.start_clicked)
        self.btn_apply.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        engine.frame_ready.connect(self.on_frame)
        engine.collect_progress.connect(self.on_progress)
        engine.collect_done.connect(self.on_done)
        self.show_step()

    def on_frame(self, img):
        self.video.setPixmap(QPixmap.fromImage(img).scaled(
            self.video.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))

    def show_step(self):
        self.bar.setValue(0)
        self.status.setText(self.STEPS[self.idx][1] +
                            "\nآماده بودید «شروع» را بزنید؛ بعد از ۳ ثانیه نمونه‌برداری می‌شود.")
        self.btn_start.setEnabled(True)

    def start_clicked(self):
        self.btn_start.setEnabled(False)
        self.count = 3
        self.status.setText(f"آماده شوید… {self.count}")
        self.timer.start(1000)

    def tick(self):
        self.count -= 1
        if self.count > 0:
            self.status.setText(f"آماده شوید… {self.count}")
            return
        self.timer.stop()
        self.status.setText("در حال نمونه‌برداری… دست را ثابت نگه دارید.")
        self._busy = True
        self.engine.start_collect(self.FRAMES)
        QTimer.singleShot(14000, self.on_timeout)

    def on_progress(self, n):
        self.bar.setValue(min(n, self.FRAMES))

    def on_timeout(self):
        if self._busy and self.isVisible():
            self._busy = False
            self.engine.cancel_collect()
            self.status.setText("دست در تصویر دیده نشد. دست را داخل کادر بگیرید و دوباره «شروع» را بزنید.")
            self.btn_start.setEnabled(True)

    def on_done(self, samples):
        if not self._busy:
            return
        self._busy = False
        self.data[self.STEPS[self.idx][0]] = samples
        self.idx += 1
        if self.idx < len(self.STEPS):
            self.show_step()
            return
        self.updates, rpt = compute_calibration(self.data)
        self.btn_start.setVisible(False)
        self.btn_apply.setVisible(bool(self.updates))
        self.status.setText("نتیجه:\n" + "\n".join(rpt) if rpt else
                            "اندازه‌گیری کافی نبود؛ دوباره امتحان کنید.")

    def done(self, r):
        self.timer.stop()
        self._busy = False
        try:
            self.engine.frame_ready.disconnect(self.on_frame)
            self.engine.collect_progress.disconnect(self.on_progress)
            self.engine.collect_done.disconnect(self.on_done)
        except Exception:
            pass
        self.engine.cancel_collect()
        super().done(r)


class PracticeDialog(QDialog):
    """حالت تمرین: هر ژست را انجام بدهید؛ در پایان می‌بینید کدام‌ها با هم قاطی می‌شوند"""
    TIMEOUT = 6.0

    def __init__(self, main, engine, targets):
        super().__init__(main)
        self.main = main
        self.engine = engine
        self.targets = list(targets)
        self.setWindowTitle("حالت تمرین")
        self.setMinimumWidth(600)
        self.prev_exec = engine.execute
        engine.execute = False          # در تمرین هیچ دستوری اجرا نشود
        self.order = []
        self.idx = -1
        self.results = []
        self.current = "none"
        self.waiting = False
        self.t0 = 0.0
        self.seen = Counter()

        lay = QVBoxLayout(self)
        self.video = QLabel("در انتظار تصویر دوربین…")
        self.video.setFixedSize(420, 315)
        self.video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video.setStyleSheet("background:#111; color:#aaa;")
        lay.addWidget(self.video, 0, Qt.AlignmentFlag.AlignCenter)
        self.target_lbl = QLabel("هر ژست را وقتی نمایش داده شد انجام دهید.")
        self.target_lbl.setObjectName("gesture")
        self.target_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.target_lbl)
        self.how_lbl = QLabel("")
        self.how_lbl.setProperty("muted", True)
        self.how_lbl.setWordWrap(True)
        self.how_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.how_lbl)
        self.bar = QProgressBar()
        self.bar.setRange(0, max(1, len(self.targets)))
        lay.addWidget(self.bar)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ژست", "نتیجه", "زمان", "اشتباه با"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setVisible(False)
        lay.addWidget(self.table)
        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        lay.addWidget(self.summary)
        row = QHBoxLayout()
        self.btn_start = QPushButton("شروع تمرین")
        self.btn_start.setProperty("variant", "primary")
        self.btn_close = QPushButton("بستن")
        row.addWidget(self.btn_start)
        row.addWidget(self.btn_close)
        lay.addLayout(row)

        self.btn_start.clicked.connect(self.start)
        self.btn_close.clicked.connect(self.accept)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        engine.frame_ready.connect(self.on_frame)
        engine.gesture_changed.connect(self.on_gesture)

    def on_frame(self, img):
        self.video.setPixmap(QPixmap.fromImage(img).scaled(
            self.video.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))

    def start(self):
        if not self.targets:
            return
        self.order = list(self.targets)
        random.shuffle(self.order)
        self.results = []
        self.idx = -1
        self.table.setVisible(False)
        self.summary.setText("")
        self.btn_start.setEnabled(False)
        self.timer.start(100)
        self.next_target()

    def next_target(self):
        self.idx += 1
        self.bar.setValue(self.idx)
        if self.idx >= len(self.order):
            self.finish()
            return
        key, label, how = self.order[self.idx]
        self.target_lbl.setText(label)
        self.how_lbl.setText(how)
        self.t0 = time.time()
        self.seen = Counter()
        self.waiting = True

    def on_gesture(self, key):
        self.current = key
        if not self.waiting or key == "none":
            return
        target = self.order[self.idx][0]
        if key == target:
            self.waiting = False
            self.results.append((self.order[self.idx], True, time.time() - self.t0, None))
            self.next_target()
        else:
            self.seen[key] += 1

    def tick(self):
        if self.waiting and time.time() - self.t0 > self.TIMEOUT:
            self.waiting = False
            wrong = self.seen.most_common(1)[0][0] if self.seen else None
            self.results.append((self.order[self.idx], False, None, wrong))
            self.next_target()

    def finish(self):
        self.timer.stop()
        self.waiting = False
        self.target_lbl.setText("تمام شد 🎉")
        self.how_lbl.setText("")
        self.table.setVisible(True)
        self.table.setRowCount(len(self.results))
        ok_n = 0
        for r, ((key, label, _how), ok, t, wrong) in enumerate(self.results):
            ok_n += 1 if ok else 0
            vals = [label, "✅" if ok else "❌",
                    f"{t:.1f} ثانیه" if t is not None else "—",
                    "" if ok else (self.main.gesture_label(wrong) if wrong else "هیچ")]
            for c, v in enumerate(vals):
                self.table.setItem(r, c, QTableWidgetItem(v))
        total = max(1, len(self.results))
        msg = f"موفق: {ok_n} از {total} ({100 * ok_n // total}٪)."
        if ok_n < total:
            msg += " برای ژست‌های ❌ طرز انجام را در «ژست‌های آماده» ببینید یا «کالیبراسیون» را اجرا کنید."
        self.summary.setText(msg)
        self.btn_start.setText("تمرین دوباره")
        self.btn_start.setEnabled(True)

    def done(self, r):
        self.timer.stop()
        self.engine.execute = self.prev_exec
        try:
            self.engine.frame_ready.disconnect(self.on_frame)
            self.engine.gesture_changed.disconnect(self.on_gesture)
        except Exception:
            pass
        super().done(r)


class OwnerTab(QWidget):
    changed = pyqtSignal()

    def __init__(self, settings, enrolled):
        super().__init__()
        lay = QVBoxLayout(self)
        info = QLabel(
            "وقتی چند نفر جلوی دوربین‌اند، برنامه فقط دست «شما» را دنبال می‌کند و "
            "بقیه را (با رنگ قرمز روی تصویر) نادیده می‌گیرد.\n"
            "روش: یک بار دست خودتان را ثبت کنید. بعد برای شروع، کف دست بازتان را "
            "نشان دهید تا قفل شود؛ از آن به بعد دست شما دنبال می‌شود، حتی با مشت و ژست‌های دیگر.")
        info.setWordWrap(True)
        lay.addWidget(info)

        box = QGroupBox("قفل روی دست من")
        form = QFormLayout(box)

        self.lock_check = QCheckBox("فقط دست من را دنبال کن")
        self.lock_check.setChecked(bool(settings["owner_lock"]))
        form.addRow("", self.lock_check)

        self.enrolled_lbl = QLabel()
        form.addRow("وضعیت ثبت:", self.enrolled_lbl)

        row = QHBoxLayout()
        self.btn_enroll = QPushButton("✋ ثبت دست من")
        self.btn_clear = QPushButton("حذف ثبت")
        row.addWidget(self.btn_enroll)
        row.addWidget(self.btn_clear)
        form.addRow("", row)

        self.status_lbl = QLabel("—")
        form.addRow("وضعیت لحظه‌ای:", self.status_lbl)

        self.thr = QDoubleSpinBox()
        self.thr.setRange(0.05, 0.50)
        self.thr.setSingleStep(0.01)
        self.thr.setDecimals(2)
        self.thr.setValue(float(settings["owner_threshold"]))
        form.addRow("سخت‌گیری شباهت (کمتر = سخت‌گیرتر):", self.thr)

        self.side = QComboBox()
        self.side.addItem("هر دو دست", "any")
        self.side.addItem("فقط دست راست", "right")
        self.side.addItem("فقط دست چپ", "left")
        self.side.setCurrentIndex(max(self.side.findData(settings["hand_side"]), 0))
        form.addRow("دست مجاز:", self.side)

        self.min_size = QSpinBox()
        self.min_size.setRange(0, 250)
        self.min_size.setValue(int(settings["min_hand_size"]))
        form.addRow("نادیده گرفتن دست‌های کوچک/دور (پیکسل، 0 = خاموش):", self.min_size)

        self.timeout = QDoubleSpinBox()
        self.timeout.setRange(0.5, 6.0)
        self.timeout.setSingleStep(0.5)
        self.timeout.setValue(float(settings["lock_timeout"]))
        form.addRow("مهلت گم شدن دست قبل از باز شدن قفل (ثانیه):", self.timeout)
        lay.addWidget(box)

        note = QLabel(
            "توجه: این روش با شکل و نسبت انگشت‌ها دست شما را از بقیه جدا می‌کند و "
            "امنیتی نیست؛ دست‌های مشابه ممکن است اشتباه شوند. برای جداسازی بهتر، "
            "«نادیده گرفتن دست‌های دور» و «دست مجاز» را هم تنظیم کنید.")
        note.setWordWrap(True)
        note.setProperty("muted", True)
        lay.addWidget(note)
        lay.addStretch(1)

        for w in (self.lock_check,):
            w.toggled.connect(self.changed.emit)
        for w in (self.thr, self.min_size, self.timeout):
            w.valueChanged.connect(self.changed.emit)
        self.side.currentIndexChanged.connect(self.changed.emit)
        self.set_enrolled(enrolled)

    def values(self):
        return {
            "owner_lock": self.lock_check.isChecked(),
            "owner_threshold": self.thr.value(),
            "hand_side": self.side.currentData(),
            "min_hand_size": self.min_size.value(),
            "lock_timeout": self.timeout.value(),
        }

    def set_values(self, settings):
        for w in (self.lock_check, self.thr, self.min_size, self.timeout, self.side):
            w.blockSignals(True)
        self.lock_check.setChecked(bool(settings["owner_lock"]))
        self.thr.setValue(float(settings["owner_threshold"]))
        self.side.setCurrentIndex(max(self.side.findData(settings["hand_side"]), 0))
        self.min_size.setValue(int(settings["min_hand_size"]))
        self.timeout.setValue(float(settings["lock_timeout"]))
        for w in (self.lock_check, self.thr, self.min_size, self.timeout, self.side):
            w.blockSignals(False)

    def set_enrolled(self, enrolled):
        self.enrolled_lbl.setText("✅ دست شما ثبت شده است" if enrolled
                                  else "❌ هنوز دستی ثبت نشده")
        self.btn_clear.setEnabled(enrolled)

    def set_status(self, state, score):
        sc = f" (شباهت {score:.2f})" if score >= 0 else ""
        text = {
            "off": "قفل خاموش است",
            "no_owner": "قفل روشن است ولی هنوز دستی ثبت نکرده‌اید",
            "waiting": "در انتظار: کف دست بازتان را نشان دهید" + sc,
            "locked": "قفل شد ✅ — دست شما دنبال می‌شود" + sc,
        }.get(state, state)
        self.status_lbl.setText(text)


# ============================== تم و ظاهر ==============================
PALETTES = {
    "dark": {"bg": "#0e1118", "surface": "#151a26", "card": "#1b2132",
             "border": "#2b3350", "text": "#e8ebf4", "muted": "#8d96ad",
             "ok": "#2fd6a1", "warn": "#ffb454", "danger": "#ff5c75"},
    "midnight": {"bg": "#000000", "surface": "#0a0b10", "card": "#10121a",
                 "border": "#22263a", "text": "#eceff8", "muted": "#7f88a0",
                 "ok": "#2fd6a1", "warn": "#ffb454", "danger": "#ff5c75"},
    "light": {"bg": "#f2f4fa", "surface": "#ffffff", "card": "#ffffff",
              "border": "#dde2ef", "text": "#1b2033", "muted": "#6b7390",
              "ok": "#0f9d73", "warn": "#c77700", "danger": "#e0364f"},
}


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#%02x%02x%02x" % tuple(int(max(0, min(255, round(v)))) for v in rgb)


def mix_colors(c1, c2, t):
    a, b = _hex_to_rgb(c1), _hex_to_rgb(c2)
    return _rgb_to_hex([a[i] * (1 - t) + b[i] * t for i in range(3)])


def luminance(h):
    r, g, b = _hex_to_rgb(h)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0


def make_palette(st):
    c = dict(PALETTES.get(st.get("theme", "dark"), PALETTES["dark"]))
    acc = str(st.get("accent", DEFAULT_SETTINGS["accent"]))
    try:
        if not acc.startswith("#") or len(acc) != 7:
            raise ValueError
        _hex_to_rgb(acc)
    except Exception:
        acc = DEFAULT_SETTINGS["accent"]
    c["accent"] = acc
    c["accent_hover"] = mix_colors(acc, "#ffffff", 0.18)
    c["accent_text"] = "#0b0f1a" if luminance(acc) > 0.6 else "#ffffff"
    c["sel"] = mix_colors(c["card"], acc, 0.22)
    c["ok_bg"] = mix_colors(c["card"], c["ok"], 0.18)
    return c


def build_qss(st):
    c = make_palette(st)
    r = int(st.get("radius", 12))
    c["r"] = f"{r}px"
    c["r_s"] = f"{max(r - 3, 2)}px"
    c["r_l"] = f"{r + 4}px"
    c["fs"] = int(st.get("font_size", 10))
    comfy = st.get("density", "comfortable") == "comfortable"
    c["bpad"] = "8px 14px" if comfy else "4px 10px"
    c["ipad"] = "6px 10px" if comfy else "3px 8px"
    return """
QWidget { background: transparent; color: %(text)s;
          font-family: "Segoe UI", "Vazirmatn", "Noto Sans", "DejaVu Sans", "Tahoma";
          font-size: %(fs)spt; }
QMainWindow, QDialog { background: %(bg)s; }
QLabel { background: transparent; }
QLabel[muted="true"] { color: %(muted)s; }
QLabel#title { font-size: 19pt; font-weight: 700; }
QLabel#gesture { font-size: 17pt; font-weight: 700; color: %(accent)s; padding: 4px 2px; }
QLabel#video { background: #05070b; color: #7d869c; border-radius: %(r_l)s;
               border: 1px solid %(border)s; font-size: 12pt; }
QLabel#chip { background: %(card)s; border: 1px solid %(border)s; border-radius: 13px;
              padding: 5px 13px; color: %(muted)s; }
QLabel#chip[state="ok"] { background: %(ok_bg)s; border-color: %(ok)s; color: %(ok)s; }
QLabel#chip[state="warn"] { border-color: %(warn)s; color: %(warn)s; }
QLabel#empty { color: %(muted)s; padding: 26px; border: 1px dashed %(border)s;
               border-radius: %(r)s; }
QFrame#card { background: %(card)s; border: 1px solid %(border)s; border-radius: %(r_l)s; }
QGroupBox { background: %(card)s; border: 1px solid %(border)s; border-radius: %(r)s;
            margin-top: 18px; padding: 18px 12px 12px 12px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 16px; padding: 0 8px;
                   color: %(accent)s; }
QTabWidget::pane { border: 1px solid %(border)s; border-radius: %(r)s;
                   background: %(card)s; top: -1px; }
QTabBar::tab { background: transparent; color: %(muted)s; padding: 9px 13px;
               margin: 2px 2px; border-radius: %(r_s)s; }
QTabBar::tab:selected { background: %(accent)s; color: %(accent_text)s; font-weight: 600; }
QTabBar::tab:hover:!selected { background: %(sel)s; color: %(text)s; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QKeySequenceEdit {
    background: %(surface)s; border: 1px solid %(border)s; border-radius: %(r_s)s;
    padding: %(ipad)s; min-height: 20px; selection-background-color: %(accent)s; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid %(accent)s; }
QComboBox QAbstractItemView { background: %(surface)s; border: 1px solid %(border)s;
    selection-background-color: %(sel)s; selection-color: %(text)s; outline: 0; }
QPushButton { background: %(surface)s; border: 1px solid %(border)s; border-radius: %(r_s)s;
              padding: %(bpad)s; color: %(text)s; }
QPushButton:hover { border-color: %(accent)s; }
QPushButton:pressed { background: %(sel)s; }
QPushButton:disabled { color: %(muted)s; background: %(bg)s; border-color: %(border)s; }
QPushButton[variant="primary"] { border: none; color: %(accent_text)s; font-weight: 600;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                stop:0 %(accent_hover)s, stop:1 %(accent)s); }
QPushButton[variant="primary"]:hover { background: %(accent_hover)s; }
QPushButton[variant="danger"] { color: %(danger)s; border-color: %(danger)s;
              background: transparent; }
QPushButton[variant="danger"]:hover { background: %(danger)s; color: #ffffff; }
QPushButton[variant="ghost"] { background: transparent; border: 1px solid transparent;
              color: %(muted)s; }
QPushButton[variant="ghost"]:hover { color: %(text)s; border-color: %(border)s; }
QCheckBox { background: transparent; spacing: 8px; }
QCheckBox::indicator, QTableView::indicator { width: 18px; height: 18px;
    border-radius: 5px; border: 1px solid %(border)s; background: %(surface)s; }
QCheckBox::indicator:checked, QTableView::indicator:checked {
    background: %(accent)s; border: 1px solid %(accent)s; }
QTableWidget, QListWidget { background: %(surface)s; alternate-background-color: %(card)s;
    border: 1px solid %(border)s; border-radius: %(r)s; gridline-color: transparent;
    selection-background-color: %(sel)s; selection-color: %(text)s; outline: 0; }
QTableWidget::item { padding: 4px 8px; border: none; }
QListWidget::item { padding: 9px 10px; border-radius: %(r_s)s; }
QListWidget::item:selected { background: %(sel)s; color: %(text)s; }
QHeaderView::section { background: %(card)s; color: %(muted)s; border: none;
    border-bottom: 1px solid %(border)s; padding: 9px; font-weight: 600; }
QProgressBar { background: %(surface)s; border: 1px solid %(border)s;
               border-radius: 8px; text-align: center; min-height: 16px; }
QProgressBar::chunk { background: %(accent)s; border-radius: 7px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: %(border)s; border-radius: 4px; min-height: 28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:horizontal { background: %(border)s; border-radius: 4px; min-width: 28px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QMenu { background: %(card)s; border: 1px solid %(border)s; padding: 6px;
        border-radius: %(r_s)s; }
QMenu::item { padding: 7px 22px; border-radius: 6px; }
QMenu::item:selected { background: %(sel)s; }
QMenu::separator { height: 1px; background: %(border)s; margin: 5px 8px; }
QToolTip { background: %(card)s; color: %(text)s; border: 1px solid %(border)s;
           padding: 6px; }
""" % c


# ============================== پنجرهٔ اصلی ==============================
class Bridge(QObject):
    """پل بین نخ‌های دیگر (موتور، سرور وب) و رابط کاربری"""
    overlay_cmd = pyqtSignal(str)
    remote_cmd = pyqtSignal(str)


class LangFilter(QObject):
    """هر پنجرهٔ گفتگوی تازه‌باز را به زبان انتخابی ترجمه می‌کند"""

    def eventFilter(self, obj, ev):
        try:
            if ev.type() == QEvent.Type.Show and isinstance(obj, QDialog) \
                    and i18n._STATE["dict"]:
                i18n.translate_tree(obj)
        except Exception:
            pass
        return False


class MacroRecordDialog(QDialog):
    """ضبط ماوس و صفحه‌کلید و تبدیل به مرحله‌های عمل"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ضبط ماکرو")
        self.setMinimumWidth(460)
        self.steps = []
        self.rec = None
        self.count = 0
        lay = QVBoxLayout(self)
        self.status = QLabel(
            "«شروع ضبط» را بزنید. بعد از ۳ ثانیه هر کلیک و تایپی که انجام دهید ثبت می‌شود. "
            "کارتان که تمام شد «پایان ضبط» را بزنید.\n"
            "نیاز: pip install pynput (روی Wayland کار نمی‌کند).")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        row = QHBoxLayout()
        self.btn_start = QPushButton("⏺ شروع ضبط")
        self.btn_start.setProperty("variant", "primary")
        self.btn_stop = QPushButton("⏹ پایان ضبط")
        self.btn_stop.setEnabled(False)
        self.btn_cancel = QPushButton("انصراف")
        for b in (self.btn_start, self.btn_stop, self.btn_cancel):
            row.addWidget(b)
        lay.addLayout(row)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.btn_start.clicked.connect(self.start)
        self.btn_stop.clicked.connect(self.stop)
        self.btn_cancel.clicked.connect(self.reject)

    def start(self):
        self.btn_start.setEnabled(False)
        self.count = 3
        self.status.setText(f"آماده شوید… {self.count}")
        self.timer.start(1000)

    def tick(self):
        self.count -= 1
        if self.count > 0:
            self.status.setText(f"آماده شوید… {self.count}")
            return
        self.timer.stop()
        try:
            self.rec = hmacro.MacroRecorder()
            self.rec.start()
        except ImportError:
            self.status.setText("pynput نصب نیست: pip install pynput")
            self.btn_start.setEnabled(True)
            return
        except Exception as e:
            self.status.setText(f"ضبط شروع نشد: {e}")
            self.btn_start.setEnabled(True)
            return
        self.status.setText("🔴 در حال ضبط… کارتان را انجام دهید.")
        self.btn_stop.setEnabled(True)

    def stop(self):
        events = self.rec.stop() if self.rec else []
        while events and events[-1]["kind"] == "click":   # کلیک روی دکمهٔ «پایان»
            events.pop()
            break
        self.steps = hmacro.events_to_steps(events)
        if not self.steps:
            self.status.setText("چیزی ضبط نشد.")
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)
            return
        self.accept()

    def done(self, r):
        self.timer.stop()
        if self.rec is not None and r != QDialog.DialogCode.Accepted:
            try:
                self.rec.stop()
            except Exception:
                pass
        super().done(r)


class AirCharDialog(MotionRecordDialog):
    SAMPLES = 2


EXTRA_KEYS = ("language", "head_control", "head_gain", "tremor_mode", "low_power",
              "idle_after", "fatigue_minutes", "tts", "voice_enabled", "voice_model",
              "ha_url", "ha_token", "mqtt_host", "mqtt_port", "mqtt_user",
              "mqtt_pass", "hue_bridge", "hue_user", "obs_host", "obs_port",
              "obs_pass", "remote_enabled", "remote_port", "remote_pin",
              "camera_source", "update_url", "airkb_scale")


class ToolsTab(QWidget):
    """ابزارهای ویژه: ارائه روی صفحه، کیبورد، صدا، اتصال‌ها، افزونه‌ها، دسترس‌پذیری، گوشی، آمار"""
    changed = pyqtSignal()

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.fields = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        self.sub = QTabWidget()
        self.sub.setUsesScrollButtons(True)
        lay.addWidget(self.sub)
        for title, fn in (("ارائه روی صفحه", self.page_overlay),
                          ("کیبورد و نوشتن هوایی", self.page_keyboard),
                          ("صدا", self.page_voice),
                          ("اتصال‌ها", self.page_integrations),
                          ("افزونه‌ها", self.page_plugins),
                          ("دسترس‌پذیری", self.page_access),
                          ("گوشی و به‌روزرسانی", self.page_remote),
                          ("آمار", self.page_stats)):
            self.sub.addTab(self.wrap(fn()), title)

    # ---------- کمکی ----------
    def wrap(self, w):
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setFrameShape(QFrame.Shape.NoFrame)
        sc.setWidget(w)
        return sc

    def note(self, text):
        lb = QLabel(text)
        lb.setWordWrap(True)
        lb.setProperty("muted", True)
        return lb

    def add(self, form, key, label, kind, lo=0, hi=100, step=1, items=None):
        st = self.main.settings
        if kind == "check":
            w = QCheckBox(label)
            w.setChecked(bool(st[key]))
            w.toggled.connect(self.changed.emit)
            form.addRow("", w)
        else:
            if kind == "int":
                w = QSpinBox()
                w.setRange(int(lo), int(hi))
                w.setSingleStep(int(step))
                w.setValue(int(st[key]))
                w.valueChanged.connect(self.changed.emit)
            elif kind == "float":
                w = QDoubleSpinBox()
                w.setRange(lo, hi)
                w.setSingleStep(step)
                w.setDecimals(2)
                w.setValue(float(st[key]))
                w.valueChanged.connect(self.changed.emit)
            elif kind == "combo":
                w = QComboBox()
                for lb_, d_ in items:
                    w.addItem(lb_, d_)
                w.setCurrentIndex(max(w.findData(st[key]), 0))
                w.currentIndexChanged.connect(self.changed.emit)
            else:
                w = QLineEdit(str(st[key]))
                if kind == "secret":
                    w.setEchoMode(QLineEdit.EchoMode.Password)
                w.editingFinished.connect(self.changed.emit)
            form.addRow(label + ":", w)
        self.fields[key] = (kind, w)
        return w

    def values(self):
        out = {}
        for key, (kind, w) in self.fields.items():
            if kind == "check":
                out[key] = w.isChecked()
            elif kind in ("int", "float"):
                out[key] = w.value()
            elif kind == "combo":
                out[key] = w.currentData()
            else:
                out[key] = w.text().strip()
        return out

    def set_values(self, st):
        for key, (kind, w) in self.fields.items():
            w.blockSignals(True)
            if kind == "check":
                w.setChecked(bool(st[key]))
            elif kind in ("int", "float"):
                w.setValue(st[key])
            elif kind == "combo":
                w.setCurrentIndex(max(w.findData(st[key]), 0))
            else:
                w.setText(str(st[key]))
            w.blockSignals(False)

    def button(self, text, fn, variant=None):
        b = QPushButton(text)
        if variant:
            b.setProperty("variant", variant)
        b.clicked.connect(lambda _=False: fn())
        return b

    # ---------- صفحه‌ها ----------
    def page_overlay(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(self.note(
            "ابزارهای ارائه روی کل صفحه، در هر برنامه‌ای (نه فقط پاورپوینت): لیزر، نقاشی با ژست، "
            "نورافکن و زمان‌سنج. این‌ها «عمل» هستند و به هر ژستی وصل می‌شوند (گروه «ابزار ارائه»). "
            "برای شروع سریع، پروفایل «ارائه‌دهندهٔ حرفه‌ای» را بارگذاری کنید."))
        box = QGroupBox("🎤 امتحان مستقیم")
        g = QGridLayout(box)
        items = [("🔴 لیزر", "overlay_laser"), ("✏️ نقاشی", "overlay_draw"),
                 ("🔦 نورافکن", "overlay_spot"), ("🧹 پاک کردن", "overlay_clear"),
                 ("🎨 رنگ قلم", "overlay_color"), ("⏱ زمان‌سنج", "overlay_timer"),
                 ("🔍 ذره‌بین ویندوز", "overlay_magnifier"), ("⌨️ کیبورد هوایی", "airkb_toggle")]
        for i, (t, a) in enumerate(items):
            g.addWidget(self.button(t, lambda a=a: self.main.overlay_action(a)), i // 4, i % 4)
        lay.addWidget(box)
        lay.addWidget(self.note(
            "نقاشی: «نقاشی» را روشن کنید، بعد مشت (یا ژستی که به «قلم» وصل کرده‌اید) را نگه دارید و دست را حرکت دهید. "
            "ذره‌بین از ذره‌بین خود ویندوز استفاده می‌کند."))
        lay.addWidget(self.button("بارگذاری پروفایل «ارائه‌دهندهٔ حرفه‌ای»",
                                  lambda: self.main.load_builtin_profile("presenter"), "primary"))
        lay.addStretch(1)
        return w

    def page_keyboard(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(self.note(
            "کیبورد هوایی: یک کیبورد فارسی/انگلیسی روی صفحه که با اشاره و «کلیک با مکث» "
            "(تب رفتار) تایپ می‌کند. فوکوس را از برنامهٔ مقصد نمی‌گیرد."))
        form = QFormLayout()
        self.add(form, "airkb_scale", "اندازهٔ کلیدها", "float", 0.6, 2.2, 0.1)
        lay.addLayout(form)
        lay.addWidget(self.button("⌨️ نمایش / پنهان کردن کیبورد هوایی",
                                  lambda: self.main.overlay_action("airkb_toggle"), "primary"))
        lay.addWidget(self.note(
            "نوشتن در هوا: برای هر نویسه (ارقام یا حروف) یک بار با دست آن را «می‌کشید» و برنامه به‌صورت "
            "ژست متحرک ثبتش می‌کند. با یک ژستی بنویسید که برایش دستور تعریف نکرده‌اید (مثلاً ✌️ یا 🖖)."))
        lay.addWidget(self.button("✍️ ساخت الفبای هوایی…", self.main.air_write_wizard))
        lay.addStretch(1)
        return w

    def page_voice(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(self.note(
            "دستور صوتی آفلاین با Vosk. ۱) pip install vosk sounddevice  ۲) یک مدل (مثلاً فارسی یا انگلیسی) را از "
            "alphacephei.com/vosk/models دانلود و از حالت زیپ خارج کنید و پوشهٔ آن را اینجا بدهید. "
            "عبارت‌ها را اضافه کنید و در «ژست‌ها و دستورها» هر عبارت (🎤) را به یک عمل وصل کنید."))
        form = QFormLayout()
        self.add(form, "voice_enabled", "گوش دادن به دستورهای صوتی", "check")
        self.model_edit = QLineEdit(str(self.main.settings["voice_model"]))
        self.model_edit.editingFinished.connect(self.changed.emit)
        self.fields["voice_model"] = ("text", self.model_edit)
        row = QHBoxLayout()
        row.addWidget(self.model_edit, 1)
        row.addWidget(self.button("انتخاب پوشه…", self.main.pick_voice_model))
        form.addRow("پوشهٔ مدل:", row)
        lay.addLayout(form)
        self.voice_status = QLabel("—")
        self.voice_status.setProperty("muted", True)
        lay.addWidget(self.voice_status)
        lay.addWidget(QLabel("عبارت‌های صوتی:"))
        self.voice_list = QListWidget()
        lay.addWidget(self.voice_list, 1)
        r = QHBoxLayout()
        r.addWidget(self.button("➕ عبارت", self.main.add_voice, "primary"))
        r.addWidget(self.button("✏️ ویرایش", self.main.edit_voice))
        r.addWidget(self.button("🗑️ حذف", self.main.delete_voice, "danger"))
        lay.addLayout(r)
        return w

    def page_integrations(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(self.note(
            "اتصال به سرویس‌های دیگر. بعد از تنظیم، از گروه «اتصال‌ها» در انتخاب عمل استفاده کنید. "
            "توکن‌ها در فایل تنظیمات به‌صورت متن ساده ذخیره می‌شوند."))
        for title, rows, test in (
                ("🏠 Home Assistant", [("ha_url", "آدرس (http://…:8123)", "text"),
                                      ("ha_token", "توکن دسترسی بلندمدت", "secret")], "ha"),
                ("💡 Philips Hue", [("hue_bridge", "آدرس IP پل", "text"),
                                   ("hue_user", "نام کاربری (کلید)", "secret")], "hue"),
                ("📡 MQTT (نیاز: pip install paho-mqtt)",
                 [("mqtt_host", "میزبان", "text"), ("mqtt_port", "پورت", "int"),
                  ("mqtt_user", "نام کاربری", "text"), ("mqtt_pass", "گذرواژه", "secret")], "mqtt"),
                ("🎥 OBS (نیاز: pip install obsws-python)",
                 [("obs_host", "میزبان", "text"), ("obs_port", "پورت", "int"),
                  ("obs_pass", "گذرواژه", "secret")], "obs")):
            box = QGroupBox(title)
            f = QFormLayout(box)
            for key, label, kind in rows:
                self.add(f, key, label, kind, 1, 65535)
            f.addRow("", self.button("آزمایش اتصال", lambda t=test: self.main.test_integration(t)))
            lay.addWidget(box)
        box = QGroupBox("🔊 صدای راهنما")
        f = QFormLayout(box)
        self.add(f, "tts", "نام هر عمل اجرا‌شده را با صدا بگو (TTS)", "check")
        lay.addWidget(box)
        lay.addStretch(1)
        return w

    def page_plugins(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(self.note(
            "افزونه = یک فایل پایتون در پوشهٔ plugins که عمل یا رویداد جدید اضافه می‌کند. "
            "⚠️ افزونه‌ها کد دلخواه اجرا می‌کنند؛ فقط افزونهٔ مورد اعتماد بگذارید."))
        self.plugin_list = QListWidget()
        lay.addWidget(self.plugin_list, 1)
        r = QHBoxLayout()
        r.addWidget(self.button("📂 باز کردن پوشه", self.main.open_plugins_folder))
        r.addWidget(self.button("📄 ساخت افزونهٔ نمونه", self.main.create_example_plugin))
        r.addWidget(self.button("🔄 بارگذاری دوباره", self.main.reload_plugins, "primary"))
        lay.addLayout(r)
        return w

    def page_access(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        box = QGroupBox("♿ دسترس‌پذیری")
        f = QFormLayout(box)
        self.add(f, "head_control", "کنترل نشانگر با سر (پلک بلند = کلیک، چشمک چپ = کلیک راست، راست = دابل)", "check")
        self.add(f, "head_gain", "حساسیت حرکت سر", "float", 0.8, 6.0, 0.1)
        f.addRow("", self.button("🎯 تنظیم مجدد مرکز سر", self.main.recenter_head))
        self.add(f, "tremor_mode", "حالت لرزش دست (هموارسازی و کلیک با مکث قوی‌تر)", "check")
        lay.addWidget(box)
        box2 = QGroupBox("⚡ بهره‌وری و سلامت")
        f2 = QFormLayout(box2)
        self.add(f2, "low_power", "حالت کم‌مصرف وقتی دستی نیست", "check")
        self.add(f2, "idle_after", "بعد از چند ثانیه بدون دست", "float", 2, 60, 1)
        self.add(f2, "fatigue_minutes", "یادآور استراحت هر … دقیقه (۰ = خاموش)", "int", 0, 180, 5)
        lay.addWidget(box2)
        box3 = QGroupBox("🌐 زبان رابط")
        f3 = QFormLayout(box3)
        items = [("فارسی", "fa"), ("English", "en")]
        try:
            for p in sorted(i18n.lang_dir().glob("*.json")):
                if p.stem not in ("fa", "en"):
                    items.append((p.stem, p.stem))
        except Exception:
            pass
        self.add(f3, "language", "زبان", "combo", items=items)
        f3.addRow("", self.button("📝 استخراج متن‌ها برای ترجمه (مثلاً عربی)", self.main.export_strings))
        lay.addWidget(box3)
        lay.addStretch(1)
        return w

    def page_remote(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        box = QGroupBox("📱 گوشی به‌عنوان دوربین")
        f = QFormLayout(box)
        self.add(f, "camera_source", "آدرس تصویر (rtsp:// یا http://…/video؛ خالی = وب‌کم)", "text")
        lay.addWidget(box)
        box2 = QGroupBox("🕹️ کنترل برنامه از مرورگر گوشی (شبکهٔ محلی)")
        f2 = QFormLayout(box2)
        self.add(f2, "remote_enabled", "فعال (نیاز به PIN؛ فقط در شبکهٔ مورد اعتماد روشن کنید)", "check")
        self.add(f2, "remote_port", "پورت", "int", 1024, 65535)
        self.pin_edit = self.add(f2, "remote_pin", "PIN", "text")
        f2.addRow("", self.button("🔑 PIN جدید", self.main.new_remote_pin))
        lay.addWidget(box2)
        self.remote_url = QLabel("—")
        self.remote_url.setProperty("muted", True)
        self.remote_url.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self.remote_url)
        box3 = QGroupBox("⬆️ به‌روزرسانی")
        f3 = QFormLayout(box3)
        self.add(f3, "update_url", "آدرس JSON نسخه (مثل {\"version\":\"4.1\",\"url\":\"…\"})", "text")
        f3.addRow("", self.button("بررسی نسخهٔ جدید", self.main.check_updates))
        lay.addWidget(box3)
        lay.addStretch(1)
        return w

    def page_stats(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.stats_lbl = QLabel("—")
        self.stats_lbl.setWordWrap(True)
        lay.addWidget(self.stats_lbl)
        self.stats_table = QTableWidget(0, 3)
        self.stats_table.setHorizontalHeaderLabels(["نوع", "نام", "تعداد امروز"])
        self.stats_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.stats_table.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.stats_table, 1)
        lay.addWidget(self.button("🔄 به‌روزرسانی آمار", self.refresh_stats, "primary"))
        return w

    def refresh_stats(self):
        stats = RUNTIME.get("stats")
        if stats is None:
            return
        days = stats.minutes_by_day(7)
        today = days[-1][1] if days else 0
        self.stats_lbl.setText(
            f"زمان فعال امروز: {today} دقیقه\n" +
            "۷ روز اخیر: " + " · ".join(f"{d[5:]}: {m}" for d, m in days))
        rows = ([("ژست", self.main.gesture_label(k), n) for k, n in stats.top("gestures", 8)]
                + [("عمل", action_label(k, self.main.custom_actions), n)
                   for k, n in stats.top("actions", 8)])
        self.stats_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, v in enumerate(row):
                self.stats_table.setItem(r, c, QTableWidgetItem(str(v)))

    def refresh_plugins(self):
        self.plugin_list.clear()
        for key, label, _k in PLUGINS.actions:
            self.plugin_list.addItem(f"🧩 {label}")
        for err in PLUGINS.errors:
            self.plugin_list.addItem(f"⚠️ {err}")
        if self.plugin_list.count() == 0:
            self.plugin_list.addItem("هیچ افزونه‌ای بارگذاری نشده است.")

    def refresh_voices(self):
        self.voice_list.clear()
        for v in self.main.voices:
            self.voice_list.addItem(f"🎤 {v['name']}")


class ExtrasMixin:
    """سرویس‌های اضافه‌شده به پنجرهٔ اصلی: ابزار ارائه، صدا، گوشی، آمار، افزونه، زبان"""

    def init_extras(self):
        self.bridge = Bridge()
        self.bridge.overlay_cmd.connect(self.on_overlay_cmd)
        self.bridge.remote_cmd.connect(self.on_remote_cmd)
        HOOKS["overlay"] = lambda cmd: self.bridge.overlay_cmd.emit(cmd)
        self.overlay = None
        self.airkb = None
        self.mag_on = False
        self.voice = None
        self.remote = None
        self._remote_status = {"camera": False, "exec": True, "profile": ""}
        RUNTIME["stats"] = UsageStats(CONFIG_DIR / "stats.json")
        PLUGINS.load()
        self.sync_runtime()
        self.lang_filter = LangFilter()
        QApplication.instance().installEventFilter(self.lang_filter)
        self._lang = "fa"
        self.apply_language()
        self.tools_tab.refresh_voices()
        self.tools_tab.refresh_plugins()
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self.extras_tick)
        self.stats_timer.start(30000)
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.refresh_remote_status)
        self.status_timer.start(1000)
        self.sync_services()

    def sync_runtime(self):
        RUNTIME["tts"] = bool(self.settings.get("tts"))
        integ.set_config(self.settings)

    def shutdown_extras(self):
        for name in ("voice", "remote"):
            obj = getattr(self, name, None)
            if obj is not None:
                try:
                    obj.stop()
                except Exception:
                    pass
        for w in (getattr(self, "overlay", None), getattr(self, "airkb", None)):
            if w is not None:
                w.close()
        if RUNTIME.get("stats") is not None:
            RUNTIME["stats"].save()

    def extras_tick(self):
        stats = RUNTIME.get("stats")
        if stats is None:
            return
        stats.save()
        if stats.break_due(int(self.settings.get("fatigue_minutes", 0))):
            self.notify("وقت استراحت است! چند دقیقه دستتان را رها کنید و کش و قوس بدهید 🙂")
        self.tools_tab.refresh_stats()

    def extras_settings_changed(self, old):
        self.sync_runtime()
        new = self.settings
        if new.get("language") != old.get("language"):
            self.apply_language()
        if new.get("camera_source") != old.get("camera_source") and self.engine is not None:
            self.stop_engine()
            self.start_engine()
        self.sync_services(old)

    # ---------- زبان ----------
    def apply_language(self):
        code = self.settings.get("language", "fa")
        if self._lang != "fa":
            rev = {v: k for k, v in i18n.load_dictionary(self._lang).items() if v}
            i18n.translate_tree(self, rev)
        i18n.set_language(code)
        i18n.translate_tree(self)
        if code != self._lang:
            self.settings["ui_rtl"] = code in ("fa", "ar")
            self.appearance_tab.set_values(self.settings)
            self.apply_appearance()
        self._lang = code

    def export_strings(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "ذخیرهٔ قالب ترجمه", "translation_template.json", "JSON (*.json)")
        if not path:
            return
        d_ = i18n.collect_strings(self)
        pathlib.Path(path).write_text(json.dumps(d_, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
        QMessageBox.information(
            self, "ترجمه",
            f"{len(d_)} متن ذخیره شد. مقدارها را ترجمه کنید و فایل را با نام کد زبان (مثلاً ar.json) "
            f"در این پوشه بگذارید:\n{i18n.lang_dir()}")

    # ---------- ابزار ارائه و کیبورد هوایی ----------
    def overlay_action(self, name):
        self.bridge.overlay_cmd.emit(name)

    def on_overlay_cmd(self, name):
        if name == "airkb_toggle":
            return self.toggle_airkb()
        if name == "overlay_magnifier":
            return self.toggle_magnifier()
        cmd = {"overlay_laser": "laser", "overlay_draw": "draw", "overlay_spot": "spot",
               "overlay_clear": "clear", "overlay_timer": "timer", "overlay_color": "color",
               "overlay_pen_down": "pen_down", "overlay_pen_up": "pen_up"}.get(name)
        if not cmd:
            return
        if self.overlay is None:
            self.overlay = ovl.OverlayWindow()
        self.overlay.command(cmd)

    def toggle_magnifier(self):
        if IS_WIN:
            press_hotkey("win", "esc") if self.mag_on else press_hotkey("win", "add")
            self.mag_on = not self.mag_on
        else:
            self.notify("ذره‌بین فقط در ویندوز پشتیبانی می‌شود.")

    def toggle_airkb(self):
        if self.airkb is not None and self.airkb.isVisible():
            self.airkb.hide()
            return
        if self.airkb is None:
            self.airkb = ovl.AirKeyboard(type_char, press_special,
                                         float(self.settings.get("airkb_scale", 1.0)))
        else:
            self.airkb.scale = float(self.settings.get("airkb_scale", 1.0))
            self.airkb.build()
        self.airkb.adjustSize()
        scr = QGuiApplication.primaryScreen().availableGeometry()
        self.airkb.move(scr.center().x() - self.airkb.width() // 2,
                        scr.bottom() - self.airkb.height() - 20)
        self.airkb.show()

    def air_write_wizard(self):
        sets = ["ارقام 0 تا 9", "حروف انگلیسی a تا z", "متن دلخواه (خودم می‌نویسم)"]
        choice, ok = QInputDialog.getItem(self, "الفبای هوایی", "کدام نویسه‌ها؟", sets, 0, False)
        if not ok:
            return
        if choice == sets[0]:
            chars = list("0123456789")
        elif choice == sets[1]:
            chars = list("abcdefghijklmnopqrstuvwxyz")
        else:
            txt, ok = QInputDialog.getText(self, "نویسه‌ها", "نویسه‌ها را پشت هم بنویسید:")
            if not ok or not txt.strip():
                return
            chars = [c for c in dict.fromkeys(txt) if not c.isspace()]
        eng = self.start_engine()
        made = 0
        for ch in chars:
            dlg = AirCharDialog(eng, self.settings, f"نوشتن «{ch}»", self)
            dlg.setWindowTitle(f"الفبای هوایی — «{ch}»  ({made + 1} از {len(chars)})")
            if self.exec_dialog(dlg) != QDialog.DialogCode.Accepted or not dlg.result_motion:
                break
            m = dlg.result_motion
            self.motions.append(m)
            self.bindings.append({"id": uuid.uuid4().hex[:8], "name": f"نوشتن {ch}",
                                  "gesture": "motion:" + m["id"], "action": "type_text",
                                  "param": ch, "enabled": True, "hold": 0})
            made += 1
        if made:
            self.persist()
            self.refresh_customs()
            self.refresh_table()
            QMessageBox.information(self, "الفبای هوایی", f"{made} نویسه ساخته شد.")

    # ---------- صدا ----------
    def pick_voice_model(self):
        path = QFileDialog.getExistingDirectory(self, "پوشهٔ مدل Vosk")
        if path:
            self.tools_tab.model_edit.setText(path)
            self.on_settings_changed()

    def add_voice(self):
        text, ok = QInputDialog.getText(self, "عبارت صوتی", "چه عبارتی گفته شود؟ (مثلاً «اسلاید بعدی»)")
        if ok and text.strip():
            self.voices.append({"id": uuid.uuid4().hex[:8], "name": text.strip()})
            self.persist()
            self.tools_tab.refresh_voices()
            self.sync_services()

    def selected_voice(self):
        r = self.tools_tab.voice_list.currentRow()
        return self.voices[r] if 0 <= r < len(self.voices) else None

    def edit_voice(self):
        v = self.selected_voice()
        if not v:
            return
        text, ok = QInputDialog.getText(self, "عبارت صوتی", "عبارت جدید:", text=v["name"])
        if ok and text.strip():
            v["name"] = text.strip()
            self.persist()
            self.tools_tab.refresh_voices()
            self.refresh_table()
            self.sync_services()

    def delete_voice(self):
        v = self.selected_voice()
        if not v:
            return
        key = "voice:" + v["id"]
        self.push_undo()
        self.bindings = [b for b in self.bindings if b["gesture"] != key]
        self.voices = [x for x in self.voices if x["id"] != v["id"]]
        self.persist()
        self.tools_tab.refresh_voices()
        self.refresh_table()
        self.sync_services()

    def on_voice_heard(self, text):
        phrase = hvoice.match_phrase(text, [v["name"] for v in self.voices])
        if not phrase:
            return
        v = next(x for x in self.voices if x["name"] == phrase)
        key = "voice:" + v["id"]
        for b in self.effective_bindings():
            if b["enabled"] and b["gesture"] == key and b["action"] not in CONTINUOUS:
                need = b.get("need_gesture", "")
                if need and self.last_stable != need:
                    continue
                run_action(b["action"], b.get("param", ""))
                break
        self.gesture_lbl.setText("🎤 " + phrase)

    # ---------- گوشی (سرور وب) ----------
    def new_remote_pin(self):
        self.settings["remote_pin"] = hremote.new_pin()
        self.tools_tab.set_values(self.settings)
        self.on_settings_changed()

    def lan_ip(self):
        import socket
        try:
            s_ = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s_.connect(("10.255.255.255", 1))
            ip = s_.getsockname()[0]
            s_.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def refresh_remote_status(self):
        eng_on = self.engine is not None and self.engine.isRunning()
        self._remote_status = {"camera": bool(eng_on),
                               "exec": bool(self.exec_check.isChecked()),
                               "profile": self.profile_name(self.manual_profile or self.active_profile)
                               if (self.manual_profile or self.active_profile) else "فعلی"}

    def on_remote_cmd(self, cmd):
        if cmd == "toggle_exec":
            self.exec_check.setChecked(not self.exec_check.isChecked())
        elif cmd == "exec_on":
            self.exec_check.setChecked(True)
        elif cmd == "exec_off":
            self.exec_check.setChecked(False)
        elif cmd == "camera_on":
            self.start_engine()
        elif cmd == "camera_off":
            self.stop_engine()
        elif cmd == "stop":
            self.exec_check.setChecked(False)
            self.stop_engine()
        elif cmd.startswith("profile:"):
            key = cmd[8:]
            if key in PROFILES or key.startswith("user:"):
                self.set_manual_profile(key)
        elif cmd.startswith("action:"):
            run_action(cmd[7:])

    def sync_services(self, old=None):
        """صدا و سرور گوشی را مطابق تنظیمات روشن/خاموش/راه‌اندازی دوباره می‌کند"""
        st = self.settings
        old = old or {}

        def changed(*keys):
            return old is None or any(st.get(k) != old.get(k) for k in keys) or not old

        # --- صدا ---
        want_voice = bool(st.get("voice_enabled") and st.get("voice_model")
                          and self.voices)
        if self.voice is not None and (not want_voice or changed("voice_model", "voice_enabled")
                                       or getattr(self.voice, "phrases", None)
                                       != [v["name"] for v in self.voices]):
            self.voice.stop()
            self.voice = None
        if want_voice and self.voice is None:
            self.voice = hvoice.VoiceListener(st["voice_model"], [v["name"] for v in self.voices])
            self.voice.heard.connect(self.on_voice_heard)
            self.voice.status.connect(self.tools_tab.voice_status.setText)
            self.voice.start()
        elif not want_voice:
            self.tools_tab.voice_status.setText("خاموش")
        # --- سرور گوشی ---
        if self.remote is not None and (not st.get("remote_enabled")
                                        or changed("remote_port", "remote_pin")):
            self.remote.stop()
            self.remote = None
        if st.get("remote_enabled") and self.remote is None:
            if not st.get("remote_pin"):
                st["remote_pin"] = hremote.new_pin()
                self.tools_tab.set_values(st)
                self.persist()
            try:
                self.remote = hremote.RemoteServer(
                    "0.0.0.0", st["remote_port"], st["remote_pin"],
                    lambda cmd: (self.bridge.remote_cmd.emit(cmd), True)[1],
                    lambda: self._remote_status)
                self.remote.start()
                self.tools_tab.remote_url.setText(
                    f"آدرس در گوشی: http://{self.lan_ip()}:{self.remote.port}/?pin={st['remote_pin']}")
            except Exception as e:
                self.remote = None
                self.tools_tab.remote_url.setText(f"سرور شروع نشد: {e}")
        elif not st.get("remote_enabled"):
            self.tools_tab.remote_url.setText("خاموش")

    # ---------- افزونه‌ها ----------
    def reload_plugins(self):
        PLUGINS.load()
        self.tools_tab.refresh_plugins()

    def open_plugins_folder(self):
        PLUGINS.folder.mkdir(parents=True, exist_ok=True)
        open_app(str(PLUGINS.folder))

    def create_example_plugin(self):
        p = PLUGINS.write_example()
        self.reload_plugins()
        QMessageBox.information(self, "افزونه", f"فایل نمونه ساخته شد:\n{p}")

    # ---------- اتصال‌ها و به‌روزرسانی ----------
    def test_integration(self, kind):
        st = self.settings
        try:
            if kind == "ha":
                r = integ.http_json("GET", st["ha_url"].rstrip("/") + "/api/", None,
                                    {"Authorization": "Bearer " + st["ha_token"]})
                msg = f"متصل شد: {r if isinstance(r, str) else r.get('message', 'OK')}"
            elif kind == "hue":
                r = integ.http_json("GET", f"http://{st['hue_bridge']}/api/{st['hue_user']}/lights")
                msg = f"متصل شد: {len(r)} چراغ پیدا شد." if isinstance(r, dict) else str(r)
            elif kind == "mqtt":
                integ.mqtt_publish("handcontrol/test | hello")
                msg = "پیام آزمایشی ارسال شد (در صورت نصب بودن paho-mqtt)."
            else:
                integ.obs_request("GetVersion")
                msg = "درخواست به OBS ارسال شد (در صورت نصب بودن obsws-python)."
        except Exception as e:
            msg = f"ناموفق: {e}"
        QMessageBox.information(self, "آزمایش اتصال", msg)

    def check_updates(self):
        url = self.settings.get("update_url", "").strip()
        if not url:
            QMessageBox.information(self, "به‌روزرسانی", "آدرس JSON نسخه را وارد کنید.")
            return
        try:
            info = hupdate.check(url, APP_VERSION)
        except Exception as e:
            QMessageBox.warning(self, "به‌روزرسانی", f"بررسی ناموفق بود: {e}")
            return
        if not info:
            QMessageBox.information(self, "به‌روزرسانی", f"نسخهٔ شما ({APP_VERSION}) آخرین نسخه است.")
            return
        if QMessageBox.question(
                self, "نسخهٔ جدید",
                f"نسخهٔ {info.get('version')} موجود است.\n{info.get('notes', '')}\n\nصفحهٔ دانلود باز شود؟") == \
                QMessageBox.StandardButton.Yes and info.get("url"):
            webbrowser.open(info["url"])

    # ---------- دسترس‌پذیری ----------
    def recenter_head(self):
        if self.engine is not None:
            self.engine.recenter_head()
            self.notify("مرکز سر تنظیم شد؛ حالا سرتان را صاف و رو به دوربین نگه دارید.")

    def load_builtin_profile(self, key):
        b = self.profile_bindings(key)
        if b is not None:
            self.apply_profile_bindings(b, self.profile_name(key))


class MainWindow(ExtrasMixin, QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — کنترل با ژست دست")
        self.resize(1400, 820)

        self.first_run = not CONFIG_FILE.exists()
        self.settings, d_ = load_config()
        self.bindings = d_["bindings"]
        self.customs = d_["customs"]
        self.owner = d_["owner"]
        self.custom_actions = d_["actions"]
        self.motions = d_["motions"]
        self.hidden = d_["hidden"]
        self.sequences = d_["sequences"]
        self.profiles = d_["profiles"]
        self.app_rules = d_["app_rules"]
        self.voices = d_["voices"]
        self.last_stable = "none"
        set_custom_actions(self.custom_actions)
        self.engine = None
        self.undo_stack = []
        self._aot = bool(self.settings.get("always_on_top"))
        self._quitting = False
        self.active_profile = None      # پروفایل انتخاب‌شده توسط قانون برنامه
        self.manual_profile = None      # پروفایل انتخاب‌دستی از منوی کنار ساعت
        self.tray = None
        self.setWindowIcon(make_app_icon(self.settings["accent"]))

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 18)
        root.setSpacing(14)

        # ---- هدر ----
        header = QHBoxLayout()
        tbox = QVBoxLayout()
        tbox.setSpacing(0)
        ttl = QLabel("🖐️  Hand Control Pro")
        ttl.setObjectName("title")
        sub = QLabel("کنترل کامپیوتر با ژست دست")
        sub.setProperty("muted", True)
        tbox.addWidget(ttl)
        tbox.addWidget(sub)
        header.addLayout(tbox)
        header.addStretch(1)
        self.chip_cam = self.make_chip("📷 دوربین: خاموش")
        self.chip_lock = self.make_chip("🔒 قفل: خاموش")
        self.chip_profile = self.make_chip("📌 پروفایل: فعلی")
        header.addWidget(self.chip_cam)
        header.addWidget(self.chip_lock)
        header.addWidget(self.chip_profile)
        self.btn_calib = QPushButton("🎯 کالیبراسیون")
        self.btn_practice = QPushButton("🏋️ تمرین")
        self.btn_theme = QPushButton()
        self.btn_about = QPushButton("ℹ️ درباره")
        for b in (self.btn_calib, self.btn_practice, self.btn_theme, self.btn_about):
            b.setProperty("variant", "ghost")
            header.addWidget(b)
        self.btn_theme.setToolTip("تغییر تم تیره / روشن")
        self.btn_about.setToolTip("دربارهٔ برنامه (F1)")
        root.addLayout(header)

        # ---- بدنه ----
        body = QHBoxLayout()
        body.setSpacing(16)
        root.addLayout(body, 1)

        left = QFrame()
        left.setObjectName("card")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(14, 14, 14, 14)
        lv.setSpacing(10)
        self.video = QLabel()
        self.video.setObjectName("video")
        self.video.setMinimumSize(520, 340)
        self.video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.show_idle_video()
        lv.addWidget(self.video, 1)
        self.gesture_lbl = QLabel("ژست فعلی: —")
        self.gesture_lbl.setObjectName("gesture")
        lv.addWidget(self.gesture_lbl)
        self.stats_lbl = QLabel("")
        self.stats_lbl.setProperty("muted", True)
        self.stats_lbl.setToolTip("روش تشخیص · سرعت · وضوح · اندازهٔ کف دست · فاصلهٔ تقریبی")
        lv.addWidget(self.stats_lbl)
        row = QHBoxLayout()
        self.btn_toggle = QPushButton("▶  شروع دوربین")
        self.btn_toggle.setProperty("variant", "primary")
        self.btn_toggle.setMinimumHeight(42)
        self.exec_check = QCheckBox("اجرای دستورها (کنترل واقعی کامپیوتر)")
        self.exec_check.setChecked(True)
        row.addWidget(self.btn_toggle, 1)
        row.addWidget(self.exec_check)
        lv.addLayout(row)
        body.addWidget(left, 5)

        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)
        body.addWidget(self.tabs, 7)

        self.tabs.addTab(self.build_gestures_tab(), "ژست‌ها و دستورها")
        self.tabs.addTab(self.build_actions_tab(), "عمل‌های من")
        self.tabs.addTab(self.build_mine_tab(), "ژست‌های من")
        self.tabs.addTab(self.build_library_tab(), "ژست‌های آماده")
        self.tabs.addTab(self.build_profiles_tab(), "پروفایل‌ها و برنامه‌ها")
        self.appearance_tab = AppearanceTab(self.settings)
        self.tabs.addTab(self.appearance_tab, "ظاهر")
        self.behavior_tab = BehaviorTab(self.settings, self.screen_labels())
        self.tabs.addTab(self.behavior_tab, "رفتار")
        self.tools_tab = ToolsTab(self)
        self.tabs.addTab(self.tools_tab, "ابزارهای ویژه")
        self.settings_tab = SettingsTab(self.settings)
        self.tabs.addTab(self.settings_tab, "تنظیمات")
        self.owner_tab = OwnerTab(self.settings, self.owner is not None)
        self.tabs.addTab(self.owner_tab, "قفل روی دست من")

        self.connect_signals()
        self.refresh_table()
        self.refresh_customs()
        self.refresh_actions()
        self.refresh_library()
        self.refresh_profiles()
        self.apply_appearance()
        self.update_profile_chip()
        self.setup_tray()
        self.setup_hotkeys()

        self.app_timer = QTimer(self)
        self.app_timer.timeout.connect(self.check_active_app)
        self.app_timer.start(800)
        self.init_extras()

    # ---------- ساخت تب‌ها ----------
    def build_gestures_tab(self):
        t1 = QWidget()
        l1 = QVBoxLayout(t1)
        l1.setContentsMargins(12, 12, 12, 12)
        self.empty_lbl = QLabel(
            "هنوز هیچ ژستی تعریف نشده است.\n"
            "با «➕ جدید» یک ژست بسازید یا از پایین یک پروفایل بارگذاری کنید.")
        self.empty_lbl.setObjectName("empty")
        self.empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l1.addWidget(self.empty_lbl)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["فعال", "نام", "ژست", "عمل", "پارامتر"])
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hh.setStretchLastSection(True)
        self.table.setColumnWidth(0, 56)
        self.table.setColumnWidth(1, 160)
        self.table.setColumnWidth(2, 190)
        self.table.setColumnWidth(3, 200)
        l1.addWidget(self.table, 1)
        sc = QShortcut(QKeySequence("Delete"), self.table)
        sc.setContext(Qt.ShortcutContext.WidgetShortcut)
        sc.activated.connect(self.del_binding)

        r = QHBoxLayout()
        self.btn_new = QPushButton("➕ جدید")
        self.btn_new.setProperty("variant", "primary")
        self.btn_edit = QPushButton("✏️ ویرایش")
        self.btn_dup = QPushButton("📄 تکرار")
        self.btn_del = QPushButton("🗑️ حذف")
        self.btn_del.setProperty("variant", "danger")
        self.btn_undo = QPushButton("↩ بازگردانی")
        for b in (self.btn_new, self.btn_edit, self.btn_dup, self.btn_del,
                  self.btn_undo):
            r.addWidget(b)
        l1.addLayout(r)

        prow = QHBoxLayout()
        self.profile_combo = QComboBox()
        self.btn_profile = QPushButton("بارگذاری پروفایل")
        self.btn_clear_all = QPushButton("حذف همه")
        self.btn_clear_all.setProperty("variant", "danger")
        prow.addWidget(self.profile_combo, 1)
        prow.addWidget(self.btn_profile)
        prow.addWidget(self.btn_clear_all)
        l1.addLayout(prow)
        return t1

    def build_actions_tab(self):
        t = QWidget()
        la = QVBoxLayout(t)
        la.setContentsMargins(12, 12, 12, 12)
        ia = QLabel("اینجا عمل‌های دلخواه خودتان را بسازید؛ مثلاً «بستن پنجره» با Alt+F4 "
                    "یا چند مرحله پشت سر هم. بعد در تب «ژست‌ها و دستورها» به هر ژستی "
                    "(ثابت یا متحرک) وصلش کنید.")
        ia.setProperty("muted", True)
        ia.setWordWrap(True)
        la.addWidget(ia)
        self.action_list = QListWidget()
        la.addWidget(self.action_list, 1)
        ra = QHBoxLayout()
        self.btn_anew = QPushButton("➕ عمل جدید")
        self.btn_anew.setProperty("variant", "primary")
        self.btn_aedit = QPushButton("✏️ ویرایش")
        self.btn_adup = QPushButton("📄 تکرار")
        self.btn_adel = QPushButton("🗑️ حذف")
        self.btn_adel.setProperty("variant", "danger")
        for b in (self.btn_anew, self.btn_aedit, self.btn_adup, self.btn_adel):
            ra.addWidget(b)
        la.addLayout(ra)
        pr = QHBoxLayout()
        self.preset_combo = QComboBox()
        for name, _steps in PRESET_ACTIONS:
            self.preset_combo.addItem(name)
        self.btn_preset = QPushButton("افزودن نمونهٔ آماده")
        pr.addWidget(self.preset_combo, 1)
        pr.addWidget(self.btn_preset)
        la.addLayout(pr)
        return t

    def build_mine_tab(self):
        t2 = QWidget()
        l2 = QVBoxLayout(t2)
        l2.setContentsMargins(12, 12, 12, 12)
        info2 = QLabel(
            "ثابت = یک حالت دست · متحرک = یک حرکت دست (مثل دایره) · "
            "ترتیب = چند ژست پشت سر هم (مثل مشت ← کف دست). "
            "اینجا بسازید، بعد در تب «ژست‌ها و دستورها» به یک عمل وصلشان کنید.")
        info2.setProperty("muted", True)
        info2.setWordWrap(True)
        l2.addWidget(info2)
        l2.addWidget(QLabel("ژست‌های ثابت (حالت دست):"))
        self.custom_list = QListWidget()
        l2.addWidget(self.custom_list, 1)
        l2.addWidget(QLabel("ژست‌های متحرک (حرکت دست):"))
        self.motion_list = QListWidget()
        l2.addWidget(self.motion_list, 1)
        l2.addWidget(QLabel("ترتیب ژست‌ها:"))
        self.seq_list = QListWidget()
        l2.addWidget(self.seq_list, 1)
        r2 = QHBoxLayout()
        self.btn_rec = QPushButton("⭐ ژست ثابت")
        self.btn_rec_motion = QPushButton("🌀 ژست متحرک")
        self.btn_seq = QPushButton("🔗 ترتیب")
        for b in (self.btn_rec, self.btn_rec_motion, self.btn_seq):
            b.setProperty("variant", "primary")
            r2.addWidget(b)
        self.btn_edit_mine = QPushButton("✏️ ویرایش ترتیب")
        self.btn_ren = QPushButton("تغییر نام")
        self.btn_cdel = QPushButton("حذف")
        self.btn_cdel.setProperty("variant", "danger")
        for b in (self.btn_edit_mine, self.btn_ren, self.btn_cdel):
            r2.addWidget(b)
        l2.addLayout(r2)
        return t2

    def build_profiles_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        info = QLabel("پروفایل = یک مجموعهٔ کامل از ژست‌ها و دستورها. می‌توانید پروفایل‌های خودتان را "
                      "ذخیره کنید و با «قانون برنامه» تعیین کنید هر برنامه کدام پروفایل را فعال کند.")
        info.setProperty("muted", True)
        info.setWordWrap(True)
        lay.addWidget(info)

        lay.addWidget(QLabel("پروفایل‌های من:"))
        self.profile_list = QListWidget()
        lay.addWidget(self.profile_list, 1)
        r = QHBoxLayout()
        self.btn_prof_save = QPushButton("💾 ذخیرهٔ ژست‌های فعلی")
        self.btn_prof_save.setProperty("variant", "primary")
        self.btn_prof_load = QPushButton("📥 بارگذاری")
        self.btn_prof_ren = QPushButton("تغییر نام")
        self.btn_prof_del = QPushButton("حذف")
        self.btn_prof_del.setProperty("variant", "danger")
        for b in (self.btn_prof_save, self.btn_prof_load, self.btn_prof_ren,
                  self.btn_prof_del):
            r.addWidget(b)
        lay.addLayout(r)
        r1 = QHBoxLayout()
        self.btn_prof_exp = QPushButton("📤 خروجی پروفایل")
        self.btn_prof_imp = QPushButton("📥 وارد کردن پروفایل")
        r1.addWidget(self.btn_prof_exp)
        r1.addWidget(self.btn_prof_imp)
        lay.addLayout(r1)

        self.auto_chk = QCheckBox("تغییر خودکار پروفایل بر اساس برنامهٔ فعال (فقط ویندوز)")
        self.auto_chk.setChecked(bool(self.settings["auto_profile"]))
        lay.addWidget(self.auto_chk)
        self.rule_table = QTableWidget(0, 3)
        self.rule_table.setHorizontalHeaderLabels(["نام", "تطبیق", "پروفایل"])
        self.rule_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.rule_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.rule_table.setAlternatingRowColors(True)
        self.rule_table.setShowGrid(False)
        self.rule_table.verticalHeader().setVisible(False)
        self.rule_table.horizontalHeader().setStretchLastSection(True)
        self.rule_table.setColumnWidth(0, 150)
        self.rule_table.setColumnWidth(1, 220)
        lay.addWidget(self.rule_table, 1)
        r2 = QHBoxLayout()
        self.btn_rule_new = QPushButton("➕ قانون جدید")
        self.btn_rule_new.setProperty("variant", "primary")
        self.btn_rule_edit = QPushButton("✏️ ویرایش")
        self.btn_rule_del = QPushButton("🗑️ حذف")
        self.btn_rule_del.setProperty("variant", "danger")
        self.btn_rule_sugg = QPushButton("✨ قانون‌های پیشنهادی")
        for b in (self.btn_rule_new, self.btn_rule_edit, self.btn_rule_del,
                  self.btn_rule_sugg):
            r2.addWidget(b)
        lay.addLayout(r2)

        r3 = QHBoxLayout()
        self.btn_backup = QPushButton("📦 پشتیبان‌گیری کامل")
        self.btn_restore = QPushButton("♻️ بازیابی از پشتیبان")
        r3.addWidget(self.btn_backup)
        r3.addWidget(self.btn_restore)
        lay.addLayout(r3)
        return w

    def connect_signals(self):
        self.btn_theme.clicked.connect(self.toggle_theme)
        self.btn_about.clicked.connect(self.show_about)
        self.btn_calib.clicked.connect(self.run_calibration)
        self.btn_practice.clicked.connect(self.run_practice)
        QShortcut(QKeySequence("F1"), self, activated=self.show_about)
        self.btn_toggle.clicked.connect(self.toggle_engine)
        self.exec_check.toggled.connect(self.on_exec_toggled)
        self.btn_new.clicked.connect(self.new_binding)
        self.btn_edit.clicked.connect(self.edit_binding)
        self.btn_dup.clicked.connect(self.dup_binding)
        self.btn_del.clicked.connect(self.del_binding)
        self.btn_undo.clicked.connect(self.undo)
        self.btn_profile.clicked.connect(self.load_profile)
        self.btn_clear_all.clicked.connect(self.delete_all)
        self.table.cellDoubleClicked.connect(lambda *_: self.edit_binding())
        self.table.itemChanged.connect(self.on_table_item_changed)

        self.btn_anew.clicked.connect(lambda: self.new_action())
        self.btn_aedit.clicked.connect(self.edit_action)
        self.action_list.itemDoubleClicked.connect(lambda *_: self.edit_action())
        self.btn_adup.clicked.connect(self.dup_action)
        self.btn_adel.clicked.connect(self.del_action)
        self.btn_preset.clicked.connect(self.add_preset)

        self.btn_rec.clicked.connect(self.record_gesture)
        self.btn_rec_motion.clicked.connect(self.record_motion)
        self.btn_seq.clicked.connect(lambda: self.new_sequence())
        self.btn_edit_mine.clicked.connect(self.edit_sequence)
        self.seq_list.itemDoubleClicked.connect(lambda *_: self.edit_sequence())
        self.btn_ren.clicked.connect(self.rename_custom)
        self.btn_cdel.clicked.connect(self.delete_custom)
        lists = (self.custom_list, self.motion_list, self.seq_list)
        for lw in lists:
            lw.itemSelectionChanged.connect(
                lambda lw=lw: self.set_active_list(lw, lists))

        self.btn_prof_save.clicked.connect(self.save_profile)
        self.btn_prof_load.clicked.connect(self.load_user_profile)
        self.btn_prof_ren.clicked.connect(self.rename_profile)
        self.btn_prof_del.clicked.connect(self.delete_profile)
        self.btn_prof_exp.clicked.connect(self.export_profile)
        self.btn_prof_imp.clicked.connect(self.import_profile)
        self.auto_chk.toggled.connect(self.on_auto_toggled)
        self.btn_rule_new.clicked.connect(self.new_rule)
        self.btn_rule_edit.clicked.connect(self.edit_rule)
        self.rule_table.cellDoubleClicked.connect(lambda *_: self.edit_rule())
        self.btn_rule_del.clicked.connect(self.del_rule)
        self.btn_rule_sugg.clicked.connect(self.add_suggested_rules)
        self.btn_backup.clicked.connect(self.export_all)
        self.btn_restore.clicked.connect(self.import_all)

        self.appearance_tab.changed.connect(self.on_settings_changed)
        self.appearance_tab.btn_reset.clicked.connect(self.reset_appearance)
        self.behavior_tab.changed.connect(self.on_settings_changed)
        self.tools_tab.changed.connect(self.on_settings_changed)
        self.settings_tab.changed.connect(self.on_settings_changed)
        self.settings_tab.btn_scan.clicked.connect(self.scan_cameras)
        self.settings_tab.btn_reset.clicked.connect(self.reset_settings)
        self.owner_tab.changed.connect(self.on_settings_changed)
        self.owner_tab.btn_enroll.clicked.connect(self.enroll_owner)
        self.owner_tab.btn_clear.clicked.connect(self.clear_owner)
        self.btn_hide_all.clicked.connect(self.hide_all_builtins)
        self.btn_show_all.clicked.connect(self.show_all_builtins)
        self.lib_table.itemChanged.connect(self.on_library_item_changed)

    # ---------- ظاهر ----------
    def make_chip(self, text):
        lb = QLabel(text)
        lb.setObjectName("chip")
        lb.setProperty("state", "off")
        return lb

    def set_chip(self, lb, text, state):
        lb.setText(i18n.tr(text))
        lb.setProperty("state", state)
        lb.style().unpolish(lb)
        lb.style().polish(lb)

    def apply_appearance(self):
        st = self.settings
        app = QApplication.instance()
        app.setStyleSheet(build_qss(st))
        app.setFont(QFont("Segoe UI", int(st["font_size"])))
        app.setLayoutDirection(Qt.LayoutDirection.RightToLeft if st["ui_rtl"]
                               else Qt.LayoutDirection.LeftToRight)
        rh = 40 if st["density"] == "comfortable" else 30
        for t in (self.table, self.lib_table, self.rule_table):
            t.verticalHeader().setDefaultSectionSize(rh)
        self.btn_theme.setText("☀️" if st["theme"] != "light" else "🌙")
        icon = make_app_icon(st["accent"])
        self.setWindowIcon(icon)
        if self.tray is not None:
            self.tray.setIcon(icon)
        if bool(st["always_on_top"]) != self._aot:
            self._aot = bool(st["always_on_top"])
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, self._aot)
            self.show()
        if self.engine is not None:
            self.engine.preview = bool(st["show_preview"])
            if not st["show_preview"]:
                self.video.clear()
                self.video.setText("پیش‌نمایش خاموش است")

    def toggle_theme(self):
        self.settings["theme"] = "light" if self.settings.get("theme") != "light" \
            else "dark"
        self.appearance_tab.set_values(self.settings)
        self.apply_appearance()
        self.persist()

    def reset_appearance(self):
        for k in ("theme", "accent", "font_size", "radius", "density",
                  "ui_rtl", "show_preview", "always_on_top"):
            self.settings[k] = DEFAULT_SETTINGS[k]
        self.appearance_tab.set_values(self.settings)
        self.apply_appearance()
        self.persist()

    def show_idle_video(self):
        self.video.clear()
        self.video.setText("📷\n\nدوربین خاموش است\nبرای شروع «شروع دوربین» را بزنید")

    # ---------- آیکون کنار ساعت و میانبر سراسری ----------
    def setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(make_app_icon(self.settings["accent"]), self)
        self.tray.setToolTip(APP_NAME)
        menu = QMenu()
        act_show = menu.addAction("نمایش / پنهان کردن پنجره")
        act_show.triggered.connect(self.toggle_window)
        act_cam = menu.addAction("شروع / توقف دوربین")
        act_cam.triggered.connect(self.toggle_engine)
        self.act_exec = menu.addAction("اجرای دستورها")
        self.act_exec.setCheckable(True)
        self.act_exec.setChecked(True)
        self.act_exec.toggled.connect(self.exec_check.setChecked)
        menu.addSeparator()
        self.menu_prof = menu.addMenu("پروفایل")
        self.menu_prof.aboutToShow.connect(self.fill_profile_menu)
        menu.addSeparator()
        act_about = menu.addAction("درباره")
        act_about.triggered.connect(self.show_about)
        act_quit = menu.addAction("خروج")
        act_quit.triggered.connect(self.quit_app)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

    def fill_profile_menu(self):
        self.menu_prof.clear()
        a0 = self.menu_prof.addAction("خودکار (بر اساس برنامهٔ فعال)")
        a0.setCheckable(True)
        a0.setChecked(self.manual_profile is None)
        a0.triggered.connect(lambda: self.set_manual_profile(None))
        self.menu_prof.addSeparator()
        for label, key in self.all_profiles():
            a = self.menu_prof.addAction(label)
            a.setCheckable(True)
            a.setChecked(self.manual_profile == key)
            a.triggered.connect(lambda _c=False, k=key: self.set_manual_profile(k))

    def set_manual_profile(self, key):
        self.manual_profile = key
        self.update_profile_chip()
        self.push_engine_config()

    def on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.DoubleClick,
                      QSystemTrayIcon.ActivationReason.Trigger):
            self.toggle_window()

    def toggle_window(self):
        if self.isVisible() and not self.isMinimized():
            self.hide()
        else:
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def quit_app(self):
        self._quitting = True
        self.close()

    def setup_hotkeys(self):
        self.hotkeys = HotkeyWatcher()
        self.hotkeys.triggered.connect(self.on_hotkey)
        self.apply_hotkeys()
        self.hotkeys.start()

    def apply_hotkeys(self):
        self.hotkeys.set_hotkeys({"toggle": self.settings["hotkey_toggle"],
                                  "stop": self.settings["hotkey_stop"]})

    def notify(self, text):
        if self.tray is not None:
            self.tray.showMessage(APP_NAME, text,
                                  QSystemTrayIcon.MessageIcon.Information, 1500)

    def on_hotkey(self, name):
        if name == "toggle":
            self.exec_check.setChecked(not self.exec_check.isChecked())
            self.notify("اجرای دستورها " + ("روشن شد" if self.exec_check.isChecked()
                                            else "متوقف شد (مکث)"))
            if self.settings.get("sound"):
                play_sound("pause")
        elif name == "stop":
            self.exec_check.setChecked(False)
            self.stop_engine()
            self.notify("توقف اضطراری: دوربین خاموش شد.")

    # ---------- کتابخانهٔ ژست‌های آماده ----------
    def build_library_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        info = QLabel("ژست‌های آمادهٔ برنامه. تیک را بردارید تا از لیست ژست‌ها حذف شود، "
                      "یا همه را یک‌جا حذف کنید و فقط ژست‌های خودتان را بسازید. "
                      "هر وقت خواستید برمی‌گردانید.")
        info.setProperty("muted", True)
        info.setWordWrap(True)
        lay.addWidget(info)
        self.lib_table = QTableWidget(len(BUILTIN_GESTURES), 3)
        self.lib_table.setHorizontalHeaderLabels(["نمایش", "ژست", "طرز انجام"])
        self.lib_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.lib_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.lib_table.setAlternatingRowColors(True)
        self.lib_table.setShowGrid(False)
        self.lib_table.verticalHeader().setVisible(False)
        self.lib_table.horizontalHeader().setStretchLastSection(True)
        self.lib_table.setColumnWidth(0, 64)
        self.lib_table.setColumnWidth(1, 220)
        lay.addWidget(self.lib_table, 1)
        r = QHBoxLayout()
        self.btn_hide_all = QPushButton("🗑️ حذف همهٔ ژست‌های آماده")
        self.btn_hide_all.setProperty("variant", "danger")
        self.btn_show_all = QPushButton("↩ بازگردانی همه")
        r.addWidget(self.btn_hide_all)
        r.addWidget(self.btn_show_all)
        lay.addLayout(r)
        return w

    def refresh_library(self):
        self.lib_table.blockSignals(True)
        for i, (key, (label, how)) in enumerate(BUILTIN_GESTURES.items()):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Unchecked if key in self.hidden
                              else Qt.CheckState.Checked)
            chk.setData(Qt.ItemDataRole.UserRole, key)
            self.lib_table.setItem(i, 0, chk)
            self.lib_table.setItem(i, 1, QTableWidgetItem(label))
            self.lib_table.setItem(i, 2, QTableWidgetItem(how))
        self.lib_table.blockSignals(False)

    def bindings_using(self, keys):
        return [b for b in self.bindings if b["gesture"] in keys]

    def on_library_item_changed(self, item):
        if item.column() != 0:
            return
        key = item.data(Qt.ItemDataRole.UserRole)
        visible = item.checkState() == Qt.CheckState.Checked
        if visible:
            if key in self.hidden:
                self.hidden.remove(key)
            self.persist()
            return
        used = self.bindings_using({key})
        if used and QMessageBox.question(
                self, "حذف ژست",
                f"{len(used)} دستور از این ژست استفاده می‌کند و همراهش حذف می‌شود. ادامه می‌دهید؟") \
                != QMessageBox.StandardButton.Yes:
            self.refresh_library()
            return
        if used:
            self.push_undo()
            self.bindings = [b for b in self.bindings if b["gesture"] != key]
        if key not in self.hidden:
            self.hidden.append(key)
        self.persist()
        self.refresh_table()

    def hide_all_builtins(self):
        keys = set(BUILTIN_GESTURES.keys())
        used = self.bindings_using(keys)
        msg = "همهٔ ژست‌های آماده از لیست حذف شوند؟"
        if used:
            msg += f"\n({len(used)} دستور وابسته به آن‌ها هم حذف می‌شود؛ با «بازگردانی» برمی‌گردد)"
        if QMessageBox.question(self, "حذف همه", msg) != QMessageBox.StandardButton.Yes:
            return
        self.push_undo()
        self.bindings = [b for b in self.bindings if b["gesture"] not in keys]
        self.hidden = list(BUILTIN_GESTURES.keys())
        self.persist()
        self.refresh_library()
        self.refresh_table()

    def show_all_builtins(self):
        self.hidden = []
        self.persist()
        self.refresh_library()

    def gesture_choices(self, include=None):
        out = []
        for key, (label, _) in BUILTIN_GESTURES.items():
            if key not in self.hidden or key == include:
                out.append((label, key))
        for c in self.customs:
            out.append(("⭐ " + c["name"], "custom:" + c["id"]))
        for m in self.motions:
            out.append(("🌀 " + m["name"], "motion:" + m["id"]))
        for q in self.sequences:
            out.append(("🔗 " + q["name"], "seq:" + q["id"]))
        for v in self.voices:
            out.append(("🎤 " + v["name"], "voice:" + v["id"]))
        return out

    # ---------- کمکی ----------
    def gesture_label(self, key):
        if key in BUILTIN_GESTURES:
            return BUILTIN_GESTURES[key][0]
        for prefix, items, icon in (("custom:", self.customs, "⭐ "),
                                    ("motion:", self.motions, "🌀 "),
                                    ("seq:", self.sequences, "🔗 "),
                                    ("voice:", self.voices, "🎤 ")):
            if key.startswith(prefix):
                for it in items:
                    if prefix + it["id"] == key:
                        return icon + it["name"]
                return "(ژست حذف‌شده)"
        return "—" if key == "none" else key

    def data_dict(self):
        return {"bindings": self.bindings, "customs": self.customs,
                "owner": self.owner, "actions": self.custom_actions,
                "motions": self.motions, "hidden": self.hidden,
                "sequences": self.sequences, "profiles": self.profiles,
                "app_rules": self.app_rules, "voices": self.voices}

    def persist(self):
        set_custom_actions(self.custom_actions)
        self.settings["monitor_rect"] = self.screen_rect(int(self.settings["monitor"]))
        self.sync_runtime()
        save_config(self.settings, self.data_dict())
        self.push_engine_config()

    def push_engine_config(self):
        if self.engine is not None:
            self.engine.update_config(
                self.settings, self.effective_bindings(), self.customs, self.owner,
                self.motions, self.custom_actions, self.sequences)

    def ask_first_run(self):
        box = QMessageBox(self)
        box.setWindowTitle("خوش آمدید")
        box.setText("چطور شروع کنیم؟\n"
                    "• با پیش‌فرض‌ها: ژست‌ها و دستورهای آماده\n"
                    "• از صفر: دستورها خالی ولی ژست‌های آماده در دسترس\n"
                    "• از صفر کامل: حتی ژست‌های آماده هم حذف شوند\n"
                    "(بعداً هر کدام را می‌توانید تغییر دهید.)")
        box.addButton("با پیش‌فرض‌ها", QMessageBox.ButtonRole.AcceptRole)
        b2 = box.addButton("از صفر", QMessageBox.ButtonRole.ActionRole)
        b3 = box.addButton("از صفر کامل", QMessageBox.ButtonRole.ActionRole)
        box.exec()
        if box.clickedButton() in (b2, b3):
            self.bindings = []
        if box.clickedButton() is b3:
            self.hidden = list(BUILTIN_GESTURES.keys())
        self.persist()
        self.refresh_table()
        self.refresh_library()

    # ---------- مانیتور ----------
    def screen_labels(self):
        try:
            return [f"{int(s.geometry().width() * s.devicePixelRatio())}×"
                    f"{int(s.geometry().height() * s.devicePixelRatio())}"
                    for s in QGuiApplication.screens()]
        except Exception:
            return []

    def screen_rect(self, idx):
        """[x, y, عرض, ارتفاع] به پیکسل فیزیکی؛ None = مانیتور اصلی"""
        if idx == 0:
            return None
        try:
            rects = []
            for sc in QGuiApplication.screens():
                g, k = sc.geometry(), sc.devicePixelRatio()
                rects.append([int(g.x() * k), int(g.y() * k),
                              int(g.width() * k), int(g.height() * k)])
            if not rects:
                return None
            if idx == -1:
                x0 = min(r[0] for r in rects)
                y0 = min(r[1] for r in rects)
                x1 = max(r[0] + r[2] for r in rects)
                y1 = max(r[1] + r[3] for r in rects)
                return [x0, y0, x1 - x0, y1 - y0]
            return rects[idx - 1] if 1 <= idx <= len(rects) else None
        except Exception:
            return None

    # ---------- پروفایل‌ها ----------
    def all_profiles(self):
        out = [(PROFILE_NAMES[k], k) for k in PROFILES]
        out += [("⭐ " + p["name"], "user:" + p["id"]) for p in self.profiles]
        return out

    def profile_name(self, key):
        if key in PROFILE_NAMES:
            return PROFILE_NAMES[key]
        for p in self.profiles:
            if "user:" + p["id"] == key:
                return p["name"]
        return key

    def profile_bindings(self, key):
        if key in PROFILES:
            return PROFILES[key]()
        for p in self.profiles:
            if "user:" + p["id"] == key:
                return copy.deepcopy(p["bindings"])
        return None

    def effective_bindings(self):
        key = self.manual_profile or self.active_profile
        if key:
            b = self.profile_bindings(key)
            if b is not None:
                return b
        return self.bindings

    def update_profile_chip(self):
        if self.manual_profile:
            self.set_chip(self.chip_profile,
                          f"📌 پروفایل (دستی): {self.profile_name(self.manual_profile)}", "warn")
        elif self.active_profile:
            self.set_chip(self.chip_profile,
                          f"📌 پروفایل: {self.profile_name(self.active_profile)}", "ok")
        else:
            self.set_chip(self.chip_profile, "📌 پروفایل: فعلی", "off")

    def check_active_app(self):
        if not self.settings.get("auto_profile") or not self.app_rules \
                or self.manual_profile:
            if self.active_profile is not None and not self.settings.get("auto_profile"):
                self.active_profile = None
                self.update_profile_chip()
                self.push_engine_config()
            return
        exe, title = get_active_app()
        if not exe and not title:
            return
        own = os.path.basename(sys.executable).lower()
        if (exe in (own, "python.exe", "pythonw.exe") or exe.startswith("python")
                or APP_NAME in title):
            return                      # پنجرهٔ خود برنامه: پروفایل تغییر نکند
        new = None
        for r in self.app_rules:
            m = r["match"].lower().strip()
            if not m:
                continue
            hit = (exe.replace(".exe", "") == m.replace(".exe", "")) \
                if r["match_type"] == "exe" \
                else (m in title.lower())
            if hit:
                new = r["profile"]
                break
        if new != self.active_profile:
            self.active_profile = new
            self.update_profile_chip()
            self.push_engine_config()

    def refresh_profiles(self):
        self.profile_combo.clear()
        for label, key in self.all_profiles():
            self.profile_combo.addItem(label, key)
        self.profile_list.clear()
        for p in self.profiles:
            it = QListWidgetItem(f"⭐ {p['name']}    —    {len(p['bindings'])} دستور")
            it.setData(Qt.ItemDataRole.UserRole, p["id"])
            self.profile_list.addItem(it)
        self.rule_table.setRowCount(len(self.app_rules))
        for r, rule in enumerate(self.app_rules):
            kind = "برنامه" if rule["match_type"] == "exe" else "عنوان"
            for c, v in enumerate((rule["name"], f"{kind}: {rule['match']}",
                                   self.profile_name(rule["profile"]))):
                self.rule_table.setItem(r, c, QTableWidgetItem(v))

    def selected_profile(self):
        it = self.profile_list.currentItem()
        if not it:
            return None
        pid = it.data(Qt.ItemDataRole.UserRole)
        return next((p for p in self.profiles if p["id"] == pid), None)

    def save_profile(self):
        name, ok = QInputDialog.getText(self, "ذخیرهٔ پروفایل", "نام پروفایل:")
        if not ok or not name.strip():
            return
        self.profiles.append({"id": uuid.uuid4().hex[:8], "name": name.strip(),
                              "bindings": copy.deepcopy(self.bindings)})
        self.persist()
        self.refresh_profiles()

    def load_user_profile(self):
        p = self.selected_profile()
        if not p:
            QMessageBox.information(self, "پروفایل", "اول یک پروفایل را انتخاب کنید.")
            return
        self.apply_profile_bindings(copy.deepcopy(p["bindings"]), p["name"])

    def rename_profile(self):
        p = self.selected_profile()
        if not p:
            return
        name, ok = QInputDialog.getText(self, "تغییر نام", "نام جدید:", text=p["name"])
        if ok and name.strip():
            p["name"] = name.strip()
            self.persist()
            self.refresh_profiles()
            self.update_profile_chip()

    def delete_profile(self):
        p = self.selected_profile()
        if not p:
            return
        key = "user:" + p["id"]
        used = [r for r in self.app_rules if r["profile"] == key]
        msg = f"پروفایل «{p['name']}» حذف شود؟"
        if used:
            msg += f"\n({len(used)} قانون برنامه که از آن استفاده می‌کند هم حذف می‌شود)"
        if QMessageBox.question(self, "حذف", msg) != QMessageBox.StandardButton.Yes:
            return
        self.profiles = [x for x in self.profiles if x["id"] != p["id"]]
        self.app_rules = [r for r in self.app_rules if r["profile"] != key]
        if self.manual_profile == key:
            self.manual_profile = None
        if self.active_profile == key:
            self.active_profile = None
        self.persist()
        self.refresh_profiles()
        self.update_profile_chip()

    def apply_profile_bindings(self, bindings, name=""):
        if QMessageBox.question(
                self, "پروفایل",
                "همهٔ ژست‌های فعلی با این پروفایل جایگزین شوند؟\n"
                "(ژست‌های سفارشی حذف نمی‌شوند؛ با «بازگردانی» برمی‌گردد)") != \
                QMessageBox.StandardButton.Yes:
            return
        self.push_undo()
        for b in bindings:
            b["id"] = uuid.uuid4().hex[:8]
        self.bindings = bindings
        used = {b["gesture"] for b in self.bindings}
        self.hidden = [h for h in self.hidden if h not in used]
        self.persist()
        self.refresh_table()
        self.refresh_library()

    def load_profile(self):
        key = self.profile_combo.currentData()
        b = self.profile_bindings(key)
        if b is not None:
            self.apply_profile_bindings(b, self.profile_name(key))

    def on_auto_toggled(self, on):
        self.settings["auto_profile"] = bool(on)
        self.persist()

    # ---------- قانون‌های برنامه ----------
    def selected_rule_index(self):
        rows = sorted({i.row() for i in self.rule_table.selectedIndexes()})
        return rows[0] if rows else -1

    def new_rule(self):
        dlg = RuleDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.app_rules.append(dlg.rule)
            self.persist()
            self.refresh_profiles()

    def edit_rule(self):
        i = self.selected_rule_index()
        if i < 0:
            QMessageBox.information(self, "ویرایش", "اول یک قانون را انتخاب کنید.")
            return
        dlg = RuleDialog(self, self.app_rules[i])
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.app_rules[i] = dlg.rule
            self.persist()
            self.refresh_profiles()

    def del_rule(self):
        i = self.selected_rule_index()
        if i < 0:
            return
        del self.app_rules[i]
        self.persist()
        self.refresh_profiles()

    def add_suggested_rules(self):
        sugg = [("پاورپوینت", "exe", "powerpnt.exe", "powerpoint"),
                ("Google Slides", "title", "Google Slides", "powerpoint"),
                ("Chrome", "exe", "chrome.exe", "browser"),
                ("Edge", "exe", "msedge.exe", "browser"),
                ("Firefox", "exe", "firefox.exe", "browser"),
                ("VLC", "exe", "vlc.exe", "media"),
                ("Spotify", "exe", "spotify.exe", "media"),
                ("Windows Media Player", "exe", "wmplayer.exe", "media"),
                ("Chromium", "exe", "chromium", "browser"),
                ("LibreOffice Impress", "title", "Impress", "powerpoint")]
        have = {(r["match_type"], r["match"].lower()) for r in self.app_rules}
        n = 0
        for name, mt, m, prof in sugg:
            if (mt, m.lower()) not in have:
                self.app_rules.append({"id": uuid.uuid4().hex[:8], "name": name,
                                       "match_type": mt, "match": m, "profile": prof})
                n += 1
        self.persist()
        self.refresh_profiles()
        QMessageBox.information(self, "قانون‌ها", f"{n} قانون پیشنهادی اضافه شد.")

    # ---------- پشتیبان‌گیری ----------
    def export_all(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "پشتیبان‌گیری", "hand_control_backup.json", "JSON (*.json)")
        if not path:
            return
        try:
            out = {"app": APP_NAME, "version": APP_VERSION,
                   "settings": {k: v for k, v in self.settings.items()
                                if k != "monitor_rect"}}
            for k, dst in CONFIG_MAP.items():
                if k != "owner":                  # امضای دست شخصی است؛ همراه پشتیبان نمی‌رود
                    out[dst] = self.data_dict()[k]
            pathlib.Path(path).write_text(
                json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
            QMessageBox.information(self, "پشتیبان", "پشتیبان ذخیره شد.")
        except Exception as e:
            QMessageBox.warning(self, "خطا", str(e))

    def import_all(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "بازیابی", "", "JSON (*.json)")
        if not path:
            return
        try:
            raw = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"فایل خوانده نشد: {e}")
            return
        box = QMessageBox(self)
        box.setWindowTitle("بازیابی")
        box.setText("موارد داخل فایل چطور وارد شوند؟")
        b_rep = box.addButton("جایگزین همه", QMessageBox.ButtonRole.DestructiveRole)
        b_add = box.addButton("افزودن به موارد فعلی", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("انصراف", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked not in (b_rep, b_add):
            return
        self.push_undo()
        if clicked is b_rep:
            self.settings.update({k: v for k, v in raw.get("settings", {}).items()
                                  if k in DEFAULT_SETTINGS and k != "monitor_rect"})
            for k, src in CONFIG_MAP.items():
                if k != "owner" and src in raw and raw[src] is not None:
                    setattr(self, "custom_actions" if k == "actions" else k, raw[src])
        else:
            def merge(cur, new):
                ids = {x["id"] for x in cur}
                cur.extend(x for x in (new or []) if x["id"] not in ids)
            merge(self.customs, raw.get("customs"))
            merge(self.motions, raw.get("motions"))
            merge(self.custom_actions, raw.get("custom_actions"))
            merge(self.sequences, raw.get("sequences"))
            merge(self.profiles, raw.get("profiles"))
            merge(self.app_rules, raw.get("app_rules"))
            merge(self.voices, raw.get("voices"))
            merge(self.bindings, raw.get("bindings"))
        self.tools_tab.set_values(self.settings)
        self.tools_tab.refresh_voices()
        self.settings_tab.set_values(self.settings)
        self.owner_tab.set_values(self.settings)
        self.appearance_tab.set_values(self.settings)
        self.behavior_tab.set_values(self.settings)
        self.persist()
        self.refresh_all()
        QMessageBox.information(self, "بازیابی", "انجام شد.")

    def refresh_all(self):
        self.tools_tab.refresh_voices()
        self.refresh_table()
        self.refresh_customs()
        self.refresh_actions()
        self.refresh_library()
        self.refresh_profiles()
        self.apply_appearance()

    def export_profile(self):
        p = self.selected_profile()
        if not p:
            QMessageBox.information(self, "پروفایل", "اول یک پروفایل را انتخاب کنید.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "خروجی پروفایل", f"{p['name']}.json", "JSON (*.json)")
        if path:
            try:
                pathlib.Path(path).write_text(
                    json.dumps({"profile": p}, ensure_ascii=False, indent=2),
                    encoding="utf-8")
            except Exception as e:
                QMessageBox.warning(self, "خطا", str(e))

    def import_profile(self):
        path, _ = QFileDialog.getOpenFileName(self, "وارد کردن پروفایل", "", "JSON (*.json)")
        if not path:
            return
        try:
            p = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))["profile"]
            self.profiles.append({"id": uuid.uuid4().hex[:8],
                                  "name": str(p.get("name", "پروفایل واردشده")),
                                  "bindings": list(p["bindings"])})
            self.persist()
            self.refresh_profiles()
        except Exception as e:
            QMessageBox.warning(self, "خطا", f"فایل پروفایل معتبر نیست: {e}")

    # ---------- موتور ----------
    def start_engine(self):
        if self.engine is not None and self.engine.isRunning():
            return self.engine
        eng = Engine()
        eng.update_config(self.settings, self.effective_bindings(), self.customs,
                          self.owner, self.motions, self.custom_actions,
                          self.sequences)
        eng.execute = self.exec_check.isChecked()
        eng.preview = bool(self.settings["show_preview"])
        eng.frame_ready.connect(self.on_frame)
        eng.gesture_changed.connect(self.on_gesture)
        eng.motion_detected.connect(self.on_motion_detected)
        eng.error.connect(self.on_error)
        eng.lock_status.connect(self.on_lock_status)
        eng.stats.connect(self.stats_lbl.setText)
        eng.finished.connect(self.on_engine_finished)
        self.engine = eng
        eng.start()
        self.btn_toggle.setText("⏹  توقف دوربین")
        self.set_chip(self.chip_cam, "📷 دوربین: روشن", "ok")
        return eng

    def stop_engine(self):
        if self.engine is not None:
            eng = self.engine
            try:
                eng.finished.disconnect(self.on_engine_finished)
            except Exception:
                pass
            eng.stop()
            self.engine = None
        self.reset_idle_ui()

    def reset_idle_ui(self):
        self.btn_toggle.setText("▶  شروع دوربین")
        self.show_idle_video()
        self.gesture_lbl.setText("ژست فعلی: —")
        self.stats_lbl.setText("")
        self.set_chip(self.chip_cam, "📷 دوربین: خاموش", "off")
        self.set_chip(self.chip_lock, "🔒 قفل: خاموش", "off")

    def toggle_engine(self):
        if self.engine is not None and self.engine.isRunning():
            self.stop_engine()
        else:
            self.start_engine()

    def on_engine_finished(self):
        self.engine = None
        self.reset_idle_ui()

    def on_error(self, msg):
        QMessageBox.warning(self, "خطا", msg)

    def on_exec_toggled(self, on):
        if self.engine is not None:
            self.engine.execute = on
        if self.tray is not None and self.act_exec.isChecked() != on:
            self.act_exec.blockSignals(True)
            self.act_exec.setChecked(on)
            self.act_exec.blockSignals(False)

    def on_frame(self, img):
        self.video.setPixmap(QPixmap.fromImage(img).scaled(
            self.video.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))

    def on_gesture(self, key):
        self.last_stable = key
        self.gesture_lbl.setText(f"ژست فعلی: {self.gesture_label(key)}")

    def on_motion_detected(self, key):
        self.gesture_lbl.setText(f"تشخیص داده شد: {self.gesture_label(key)}")

    def on_lock_status(self, state, score):
        self.owner_tab.set_status(state, score)
        text, st = {
            "off": ("🔒 قفل: خاموش", "off"),
            "no_owner": ("🔒 قفل: دستی ثبت نشده", "warn"),
            "waiting": ("🔒 قفل: کف دست باز را نشان دهید", "warn"),
            "locked": ("🔒 قفل: ✅ دست شما", "ok"),
        }.get(state, ("🔒 قفل", "off"))
        self.set_chip(self.chip_lock, text, st)

    def exec_dialog(self, dlg):
        """اجرای پنجرهٔ گفتگو؛ پیش‌نمایش دوربین موقتاً روشن می‌ماند"""
        prev = None
        if self.engine is not None:
            prev = self.engine.preview
            self.engine.preview = True
        try:
            return dlg.exec()
        finally:
            if self.engine is not None and prev is not None:
                self.engine.preview = bool(self.settings["show_preview"])

    # ---------- کالیبراسیون و تمرین ----------
    def run_calibration(self):
        eng = self.start_engine()
        dlg = CalibrationDialog(eng, self)
        if self.exec_dialog(dlg) == QDialog.DialogCode.Accepted and dlg.updates:
            self.settings.update(dlg.updates)
            self.settings_tab.set_values(self.settings)
            self.persist()
            QMessageBox.information(self, "کالیبراسیون", "تنظیمات اعمال شد. حالا با «🏋️ تمرین» امتحانش کنید.")

    def run_practice(self):
        eng = self.start_engine()
        targets = [(k, lb, BUILTIN_GESTURES[k][1])
                   for k, (lb, _h) in BUILTIN_GESTURES.items()
                   if k not in self.hidden and not k.startswith("swipe_")]
        targets += [("custom:" + c["id"], "⭐ " + c["name"], "ژست ثابت ثبت‌شدهٔ شما")
                    for c in self.customs]
        if not targets:
            QMessageBox.information(self, "تمرین", "ژستی برای تمرین نیست.")
            return
        self.exec_dialog(PracticeDialog(self, eng, targets))

    # ---------- جدول ژست‌ها ----------
    def refresh_table(self, select_row=None):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.bindings))
        ro = ~Qt.ItemFlag.ItemIsEditable
        for r, b in enumerate(self.bindings):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable |
                         Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            chk.setCheckState(Qt.CheckState.Checked if b["enabled"]
                              else Qt.CheckState.Unchecked)
            self.table.setItem(r, 0, chk)
            hold = float(b.get("hold", 0) or 0)
            glabel = self.gesture_label(b["gesture"]) + (f"  ⏱ {hold:g}s" if hold else "")
            vals = [b["name"], glabel,
                    action_label(b["action"], self.custom_actions),
                    b.get("param", "")]
            for c, v in enumerate(vals, start=1):
                it = QTableWidgetItem(v)
                it.setFlags(it.flags() & ro)
                self.table.setItem(r, c, it)
        self.table.blockSignals(False)
        empty = not self.bindings
        self.empty_lbl.setVisible(empty)
        self.table.setVisible(not empty)
        self.btn_undo.setEnabled(bool(self.undo_stack))
        self.btn_clear_all.setEnabled(not empty)
        if select_row is not None and 0 <= select_row < len(self.bindings):
            self.table.selectRow(select_row)

    def on_table_item_changed(self, item):
        if item.column() != 0:
            return
        r = item.row()
        if 0 <= r < len(self.bindings):
            self.bindings[r]["enabled"] = \
                item.checkState() == Qt.CheckState.Checked
            self.persist()

    def selected_rows(self):
        return sorted({i.row() for i in self.table.selectedIndexes()})

    def push_undo(self):
        self.undo_stack.append(copy.deepcopy(self.bindings))
        del self.undo_stack[:-20]

    def undo(self):
        if not self.undo_stack:
            return
        self.bindings = self.undo_stack.pop()
        self.persist()
        self.refresh_table()

    def resolve_conflict(self, b):
        hold = float(b.get("hold", 0) or 0)
        for other in self.bindings:
            if (other["id"] != b["id"] and other["enabled"] and b["enabled"]
                    and other["gesture"] == b["gesture"]
                    and float(other.get("hold", 0) or 0) == hold):
                ans = QMessageBox.question(
                    self, "ژست تکراری",
                    f"این ژست قبلاً برای «{other['name']}» استفاده شده است.\n"
                    "آن را غیرفعال کنم تا ژست جدید جایگزین شود؟")
                if ans == QMessageBox.StandardButton.Yes:
                    other["enabled"] = False

    def new_binding(self):
        dlg = BindingDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            b = dlg.binding
            self.push_undo()
            self.resolve_conflict(b)
            self.bindings.append(b)
            self.persist()
            self.refresh_table(len(self.bindings) - 1)

    def edit_binding(self):
        rows = self.selected_rows()
        if not rows:
            QMessageBox.information(self, "ویرایش", "اول یک ردیف را انتخاب کنید.")
            return
        r = rows[0]
        dlg = BindingDialog(self, self.bindings[r])
        if dlg.exec() == QDialog.DialogCode.Accepted:
            b = dlg.binding
            self.push_undo()
            self.resolve_conflict(b)
            self.bindings[r] = b
            self.persist()
            self.refresh_table(r)

    def dup_binding(self):
        rows = self.selected_rows()
        if not rows:
            return
        r = rows[0]
        self.push_undo()
        b = dict(self.bindings[r])
        b["id"] = uuid.uuid4().hex[:8]
        b["name"] += " (کپی)"
        b["enabled"] = False
        self.bindings.insert(r + 1, b)
        self.persist()
        self.refresh_table(r + 1)

    def del_binding(self):
        rows = self.selected_rows()
        if not rows:
            return
        names = "، ".join(f"«{self.bindings[r]['name']}»" for r in rows[:3])
        if len(rows) > 3:
            names += " …"
        if QMessageBox.question(
                self, "حذف", f"{len(rows)} مورد حذف شود؟\n{names}") != \
                QMessageBox.StandardButton.Yes:
            return
        self.push_undo()
        self.bindings = [b for i, b in enumerate(self.bindings) if i not in rows]
        self.persist()
        self.refresh_table(min(rows[0], len(self.bindings) - 1))

    def delete_all(self):
        if not self.bindings:
            return
        if QMessageBox.question(
                self, "حذف همه",
                "همهٔ ژست‌ها و دستورها حذف شوند؟\n(با «بازگردانی» می‌توانید برگردانید)") != \
                QMessageBox.StandardButton.Yes:
            return
        self.push_undo()
        self.bindings = []
        self.persist()
        self.refresh_table()

    # ---------- عمل‌های من ----------
    def refresh_actions(self):
        self.action_list.clear()
        for a in self.custom_actions:
            summary = " ← ".join(step_summary(s_) for s_ in a["steps"][:3])
            if len(a["steps"]) > 3:
                summary += " …"
            it = QListWidgetItem(f"⚡ {a['name']}    —    {summary}")
            it.setData(Qt.ItemDataRole.UserRole, a["id"])
            self.action_list.addItem(it)

    def selected_action(self):
        it = self.action_list.currentItem()
        if not it:
            return None
        aid = it.data(Qt.ItemDataRole.UserRole)
        return next((a for a in self.custom_actions if a["id"] == aid), None)

    def new_action(self, preset=None):
        dlg = ActionDialog(self, preset)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.custom_actions.append(dlg.action)
            self.persist()
            self.refresh_actions()
            self.refresh_table()
            return dlg.action
        return None

    def edit_action(self):
        a = self.selected_action()
        if not a:
            QMessageBox.information(self, "ویرایش", "اول یک عمل را انتخاب کنید.")
            return
        dlg = ActionDialog(self, a)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            i = self.custom_actions.index(a)
            self.custom_actions[i] = dlg.action
            self.persist()
            self.refresh_actions()
            self.refresh_table()

    def dup_action(self):
        a = self.selected_action()
        if not a:
            return
        b = copy.deepcopy(a)
        b["id"] = uuid.uuid4().hex[:8]
        b["name"] += " (کپی)"
        self.custom_actions.append(b)
        self.persist()
        self.refresh_actions()

    def del_action(self):
        a = self.selected_action()
        if not a:
            return
        key = "custom:" + a["id"]
        used = [b for b in self.bindings if b["action"] == key]
        msg = f"عمل «{a['name']}» حذف شود؟"
        if used:
            msg += f"\n({len(used)} دستور وابسته به آن هم حذف می‌شود)"
        if QMessageBox.question(self, "حذف", msg) != QMessageBox.StandardButton.Yes:
            return
        if used:
            self.push_undo()
            self.bindings = [b for b in self.bindings if b["action"] != key]
        self.custom_actions = [x for x in self.custom_actions if x["id"] != a["id"]]
        self.persist()
        self.refresh_actions()
        self.refresh_table()

    def add_preset(self):
        i = self.preset_combo.currentIndex()
        name, steps = PRESET_ACTIONS[i]
        self.custom_actions.append({"id": uuid.uuid4().hex[:8], "name": name,
                                    "steps": copy.deepcopy(steps)})
        self.persist()
        self.refresh_actions()
        self.action_list.setCurrentRow(self.action_list.count() - 1)

    # ---------- ژست‌های ثابت، متحرک و ترتیب ----------
    def refresh_customs(self):
        self.custom_list.clear()
        for c in self.customs:
            it = QListWidgetItem("⭐ " + c["name"])
            it.setData(Qt.ItemDataRole.UserRole, c["id"])
            self.custom_list.addItem(it)
        self.motion_list.clear()
        for m in self.motions:
            pose = "هر حالت" if m.get("pose") == "any" else \
                self.gesture_label(m.get("pose", "any"))
            it = QListWidgetItem(f"🌀 {m['name']}    —    حالت دست: {pose}")
            it.setData(Qt.ItemDataRole.UserRole, m["id"])
            self.motion_list.addItem(it)
        self.seq_list.clear()
        for q in self.sequences:
            steps = "  ←  ".join(self.gesture_label(k) for k in q["steps"])
            it = QListWidgetItem(f"🔗 {q['name']}    —    {steps}")
            it.setData(Qt.ItemDataRole.UserRole, q["id"])
            self.seq_list.addItem(it)

    def set_active_list(self, active, lists):
        if active.selectedItems():
            for other in lists:
                if other is not active:
                    other.blockSignals(True)
                    other.clearSelection()
                    other.blockSignals(False)

    def record_gesture(self):
        eng = self.start_engine()
        dlg = RecordDialog(eng, f"ژست من {len(self.customs) + 1}", self)
        if self.exec_dialog(dlg) == QDialog.DialogCode.Accepted and dlg.result_gesture:
            c = dlg.result_gesture
            self.customs.append(c)
            self.persist()
            self.refresh_customs()
            self.refresh_table()
            return c
        return None

    def record_motion(self):
        eng = self.start_engine()
        dlg = MotionRecordDialog(eng, self.settings,
                                 f"ژست متحرک {len(self.motions) + 1}", self)
        if self.exec_dialog(dlg) == QDialog.DialogCode.Accepted and dlg.result_motion:
            m = dlg.result_motion
            self.motions.append(m)
            self.persist()
            self.refresh_customs()
            self.refresh_table()
            return m
        return None

    def new_sequence(self):
        dlg = SequenceDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.sequences.append(dlg.seq)
            self.persist()
            self.refresh_customs()
            self.refresh_table()
            return dlg.seq
        return None

    def edit_sequence(self):
        kind, g = self.selected_gesture_item()
        if kind != "seq" or not g:
            QMessageBox.information(self, "ویرایش", "اول یک «ترتیب ژست» را انتخاب کنید.")
            return
        dlg = SequenceDialog(self, g)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            i = self.sequences.index(g)
            self.sequences[i] = dlg.seq
            self.persist()
            self.refresh_customs()
            self.refresh_table()

    def selected_gesture_item(self):
        """(نوع، دیکشنری ژست) برای مورد انتخاب‌شده در یکی از سه لیست"""
        for kind, lw, items in (("motion", self.motion_list, self.motions),
                                ("seq", self.seq_list, self.sequences),
                                ("custom", self.custom_list, self.customs)):
            if lw.selectedItems():
                gid = lw.currentItem().data(Qt.ItemDataRole.UserRole)
                return kind, next((x for x in items if x["id"] == gid), None)
        return None, None

    def rename_custom(self):
        kind, g = self.selected_gesture_item()
        if not g:
            return
        name, ok = QInputDialog.getText(self, "تغییر نام", "نام جدید:", text=g["name"])
        if ok and name.strip():
            g["name"] = name.strip()
            self.persist()
            self.refresh_customs()
            self.refresh_table()

    def delete_custom(self):
        kind, g = self.selected_gesture_item()
        if not g:
            return
        key = f"{kind}:{g['id']}"
        used = [b for b in self.bindings if b["gesture"] == key]
        msg = f"ژست «{g['name']}» حذف شود؟"
        if used:
            msg += f"\n({len(used)} دستور وابسته به آن هم حذف می‌شود)"
        if QMessageBox.question(self, "حذف", msg) != QMessageBox.StandardButton.Yes:
            return
        self.push_undo()
        self.bindings = [b for b in self.bindings if b["gesture"] != key]
        if kind == "motion":
            self.motions = [x for x in self.motions if x["id"] != g["id"]]
        elif kind == "seq":
            self.sequences = [x for x in self.sequences if x["id"] != g["id"]]
        else:
            self.customs = [x for x in self.customs if x["id"] != g["id"]]
            self.sequences = [q for q in self.sequences if key not in q["steps"]]
        self.persist()
        self.refresh_customs()
        self.refresh_table()

    # ---------- تنظیمات ----------
    def on_settings_changed(self):
        old_all = dict(self.settings)
        self.settings.update(self.tools_tab.values())
        self._settings_core()
        self.extras_settings_changed(old_all)

    def _settings_core(self):
        old = {k: self.settings.get(k) for k in
               ("camera_index", "cam_width", "detect_conf", "autostart",
                "hotkey_toggle", "hotkey_stop", "monitor")}
        self.settings.update(self.settings_tab.values())
        self.settings.update(self.owner_tab.values())
        self.settings.update(self.appearance_tab.values())
        self.settings.update(self.behavior_tab.values())
        if self.settings["autostart"] != old["autostart"]:
            set_autostart(bool(self.settings["autostart"]))
        self.persist()
        self.apply_appearance()
        if (self.settings["hotkey_toggle"] != old["hotkey_toggle"]
                or self.settings["hotkey_stop"] != old["hotkey_stop"]):
            self.apply_hotkeys()
        if any(self.settings[k] != old[k] for k in
               ("camera_index", "cam_width", "detect_conf")) \
                and self.engine is not None:
            self.stop_engine()
            self.start_engine()

    def reset_settings(self):
        keep_keys = ("theme", "accent", "font_size", "radius", "density", "ui_rtl",
                     "show_preview", "always_on_top", "autostart", "start_minimized",
                     "auto_start_camera", "close_to_tray", "hotkey_toggle",
                     "hotkey_stop", "monitor", "sound", "auto_profile",
                     "slider_step", "zoom_step", "dwell_click", "dwell_time",
                     "dwell_radius")
        keep = {k: self.settings[k] for k in keep_keys + EXTRA_KEYS}
        self.settings = dict(DEFAULT_SETTINGS)
        self.settings.update(keep)
        self.settings_tab.set_values(self.settings)
        self.owner_tab.set_values(self.settings)
        self.persist()

    def scan_cameras(self):
        was_running = self.engine is not None and self.engine.isRunning()
        if was_running:
            self.stop_engine()
        found = []
        for i in range(5):
            cap = open_camera(i)
            if cap is not None:
                found.append(i)
                cap.release()
        if found:
            QMessageBox.information(
                self, "دوربین‌ها",
                "دوربین‌های قابل استفاده: " + "، ".join(map(str, found)) +
                "\nیکی از این شماره‌ها را در «شمارهٔ دوربین» بگذارید.")
        else:
            QMessageBox.warning(self, "دوربین‌ها", "هیچ دوربینی پیدا نشد.")
        if was_running:
            self.start_engine()

    def show_about(self):
        AboutDialog(self).exec()

    # ---------- قفل روی دست ----------
    def enroll_owner(self):
        eng = self.start_engine()
        dlg = EnrollDialog(eng, self)
        if self.exec_dialog(dlg) == QDialog.DialogCode.Accepted and dlg.owner:
            self.owner = {"sig": dlg.owner["sig"]}
            self.settings["owner_threshold"] = round(dlg.owner["suggest"], 2)
            if not self.settings["owner_lock"]:
                if QMessageBox.question(
                        self, "قفل",
                        "دست شما ثبت شد. قفل روی دست فعال شود؟") == \
                        QMessageBox.StandardButton.Yes:
                    self.settings["owner_lock"] = True
            self.owner_tab.set_values(self.settings)
            self.owner_tab.set_enrolled(True)
            self.persist()

    def clear_owner(self):
        if QMessageBox.question(self, "حذف", "ثبت دست شما حذف شود؟") == \
                QMessageBox.StandardButton.Yes:
            self.owner = None
            self.settings["owner_lock"] = False
            self.owner_tab.set_values(self.settings)
            self.owner_tab.set_enrolled(False)
            self.persist()

    def closeEvent(self, e):
        if (self.settings.get("close_to_tray") and self.tray is not None
                and not self._quitting):
            e.ignore()
            self.hide()
            self.notify("برنامه در کنار ساعت در حال اجراست. برای خروج از منوی آیکون استفاده کنید.")
            return
        self.app_timer.stop()
        self.shutdown_extras()
        self.hotkeys.stop()
        self.stop_engine()
        save_config(self.settings, self.data_dict())
        if self.tray is not None:
            self.tray.hide()
        super().closeEvent(e)
        QApplication.quit()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    if win.tray is not None:
        app.setQuitOnLastWindowClosed(False)
    hidden = ("--minimized" in sys.argv or bool(win.settings.get("start_minimized"))) \
        and win.tray is not None
    if not hidden:
        win.show()
    if IS_LINUX and os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland":
        QTimer.singleShot(700, lambda: QMessageBox.warning(
            win, "Wayland",
            "نشست فعلی شما Wayland است. در Wayland برنامه‌ها اجازهٔ کنترل ماوس و صفحه‌کلید "
            "را ندارند، پس دستورها اجرا نمی‌شوند (تشخیص دست و ضبط ژست‌ها کار می‌کند).\n\n"
            "برای کنترل واقعی کامپیوتر، هنگام ورود به سیستم نشست «Xorg / X11» را انتخاب کنید "
            "(مثلاً «Ubuntu on Xorg»)."))
    if win.first_run:
        QTimer.singleShot(400, win.ask_first_run)
    if win.settings.get("auto_start_camera"):
        QTimer.singleShot(800, win.start_engine)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
