# 🖐️ Hand Control Pro 4.0
### کنترل کامپیوتر با حرکات دست | Control Your Computer with Hand Gestures

<p align="center">
  <b>English | فارسی</b>
</p>

<p align="center">
  An advanced hands-free desktop control system powered by Python, MediaPipe and OpenCV.
  <br>
  یک سیستم پیشرفته برای کنترل بدون لمس کامپیوتر با استفاده از پایتون، مدیاپایپ و OpenCV.
</p>

---

## 🌍 Language | زبان

- [English](#-english)
- [فارسی](#-فارسی)

---

# 🇬🇧 English

## 📖 About

**Hand Control Pro 4.0** is an advanced desktop control application that allows users to interact with their computer using hand gestures, head movements, eye blinks, and voice commands.

The project combines real-time computer vision, gesture recognition, desktop automation, and external integrations into one application.

## ✨ Features

| Feature | Description |
|---|---|
| 🖐️ Hand Tracking | Real-time hand detection and tracking |
| 🎯 Gesture Learning | Learn custom gestures from user samples |
| 🧠 Smart Recognition | Nearest-neighbor classification and data augmentation |
| 👤 Head Tracking | Control the cursor using head movements |
| 👁️ Eye Tracking | Execute actions using eye blinks |
| 🎨 Screen Overlay | Laser pointer, drawing, spotlight and timer |
| ⌨️ Air Keyboard | Virtual keyboard controlled by gestures |
| 🎙️ Voice Commands | Offline voice recognition using Vosk |
| 🏠 Smart Integrations | Home Assistant, MQTT and Philips Hue |
| 🎥 OBS Integration | Integration with OBS Studio |
| 🎬 Macro Recorder | Record and replay mouse and keyboard actions |
| 🔌 Plugin System | Support for custom plugins |
| 📱 Remote Control | Control your computer through a mobile browser |
| 📊 Statistics | Usage statistics and break reminders |
| 🌍 Multilingual | Multiple language support |
| 🔄 Updater | Check for application updates |

## 🛠️ Technologies

- Python 3.12
- NumPy
- MediaPipe
- OpenCV
- PyAutoGUI
- PyQt6
- Vosk (Optional)

## 📥 Installation

### Windows

**Requirements:**
- Python 3.12
- Webcam
- Windows 10/11

Clone the repository:

```bash
git clone https://github.com/alisanvahedpour-hash/Hand-Control-Pro.git
cd Hand-Control-Pro
```

Install dependencies:

```bash
pip install numpy==1.26.4 mediapipe==0.10.21 pyautogui PyQt6
```

Run the application:

```bash
python hand_control_pro.py
```

### Linux (X11)

Install:

```bash
bash install_linux.sh
```

Run:

```bash
./run_linux.sh
```

## 📦 Optional Components

Install additional components on Windows:

```bash
install_extras.bat
```

Optional components include:

- Voice recognition
- Macro recording
- MQTT integration
- OBS integration

## 🏗️ Project Structure

| File / Directory | Description |
|---|---|
| `hand_control_pro.py` | Main application and GUI |
| `hcx/learn.py` | Gesture learning engine |
| `hcx/headtrack.py` | Head and eye tracking |
| `hcx/overlay.py` | Screen overlays and air keyboard |
| `hcx/voice.py` | Offline voice recognition |
| `hcx/integrations.py` | External integrations |
| `hcx/macro.py` | Macro recording |
| `hcx/plugins.py` | Plugin system |
| `hcx/remote.py` | Mobile remote control |
| `hcx/stats.py` | Statistics and break reminders |
| `hcx/updater.py` | Update checker |
| `hcx/i18n.py` | Language support |
| `tests/` | Automated tests |

## 🧪 Testing

The project includes **61 automated tests**.

Windows:

```bash
run_tests.bat
```

Linux:

```bash
bash run_tests.sh
```

Python:

```bash
python -m unittest discover -s tests -t .
```

Only NumPy is required for the automated test suite.

**Note:** Real camera behavior, desktop interactions, and external services should be tested separately.

## 📦 Building

Build Windows executable:

```bash
build_exe.bat
```

Create an installer using Inno Setup and `installer.iss`.

## 💾 Data Storage

Application data is stored in:

```text
~/.hand_control/
```

Structure:

```text
.hand_control/
├── config.json
├── stats.json
├── plugins/
└── lang/
    └── <language_code>.json
```

## 🔐 Privacy

- Local gesture recognition.
- Offline voice recognition support.
- PIN-protected remote control.
- Extensible plugin architecture.

## 📄 License

Choose and add an appropriate open-source license.

---

# 🇮🇷 فارسی

## 📖 معرفی پروژه

**Hand Control Pro 4.0** یک نرم‌افزار پیشرفته برای کنترل کامپیوتر با استفاده از حرکات دست، حرکت سر، پلک زدن و فرمان‌های صوتی است.

این پروژه با ترکیب بینایی ماشین، تشخیص ژست، اتوماسیون دسکتاپ و اتصال به سرویس‌های خارجی، امکان کنترل کامپیوتر بدون نیاز به لمس ماوس و صفحه‌کلید را فراهم می‌کند.

## ✨ قابلیت‌ها

| قابلیت | توضیحات |
|---|---|
| 🖐️ تشخیص دست | شناسایی و ردیابی لحظه‌ای دست |
| 🎯 یادگیری ژست | یادگیری حرکات دلخواه با نمونه‌های کاربر |
| 🧠 تشخیص هوشمند | طبقه‌بندی نزدیک‌ترین همسایه و افزایش داده |
| 👤 ردیابی سر | کنترل نشانگر ماوس با حرکت سر |
| 👁️ تشخیص پلک | اجرای دستورات با پلک زدن |
| 🎨 ابزارهای صفحه | لیزر، نقاشی، نورافکن و زمان‌سنج |
| ⌨️ کیبورد هوایی | صفحه‌کلید مجازی با کنترل حرکتی |
| 🎙️ فرمان صوتی | تشخیص آفلاین صدا با استفاده از Vosk |
| 🏠 خانه هوشمند | اتصال به Home Assistant، MQTT و Hue |
| 🎥 اتصال به OBS | یکپارچه‌سازی با OBS Studio |
| 🎬 ضبط ماکرو | ضبط و اجرای مجدد حرکات ماوس و صفحه‌کلید |
| 🔌 سیستم افزونه | امکان اضافه کردن افزونه‌های اختصاصی |
| 📱 کنترل از راه دور | کنترل کامپیوتر از طریق مرورگر گوشی با PIN |
| 📊 آمار | ثبت فعالیت و یادآوری زمان استراحت |
| 🌍 چندزبانه | پشتیبانی از زبان‌های مختلف |
| 🔄 به‌روزرسانی | بررسی نسخه‌های جدید برنامه |

## 🛠️ فناوری‌های استفاده‌شده

- Python 3.12
- NumPy
- MediaPipe
- OpenCV
- PyAutoGUI
- PyQt6
- Vosk (اختیاری)

## 📥 نصب و راه‌اندازی

### ویندوز

**پیش‌نیازها:**
- پایتون نسخه 3.12
- وب‌کم
- ویندوز 10 یا 11

ابتدا مخزن پروژه را دریافت کنید:

```bash
git clone https://github.com/alisanvahedpour-hash/Hand-Control-Pro.git
cd Hand-Control-Pro
```

نصب کتابخانه‌های موردنیاز:

```bash
pip install numpy==1.26.4 mediapipe==0.10.21 pyautogui PyQt6
```

اجرای برنامه:

```bash
python hand_control_pro.py
```

### لینوکس (X11)

نصب:

```bash
bash install_linux.sh
```

اجرا:

```bash
./run_linux.sh
```

## 📦 نصب قابلیت‌های اختیاری

برای نصب امکانات اضافی در ویندوز:

```bash
install_extras.bat
```

این امکانات شامل موارد زیر هستند:

- تشخیص فرمان صوتی
- ضبط و اجرای ماکرو
- اتصال MQTT
- اتصال به OBS

## 🏗️ ساختار پروژه

| فایل یا پوشه | وظیفه |
|---|---|
| `hand_control_pro.py` | برنامه اصلی، رابط کاربری و موتور تشخیص ژست |
| `hcx/learn.py` | یادگیری و تشخیص ژست |
| `hcx/headtrack.py` | ردیابی سر و چشم |
| `hcx/overlay.py` | ابزارهای روی صفحه و کیبورد هوایی |
| `hcx/voice.py` | تشخیص آفلاین صدا |
| `hcx/integrations.py` | اتصال به سرویس‌های خارجی |
| `hcx/macro.py` | ضبط ماکرو |
| `hcx/plugins.py` | مدیریت افزونه‌ها |
| `hcx/remote.py` | کنترل از طریق گوشی |
| `hcx/stats.py` | آمار و یادآوری استراحت |
| `hcx/updater.py` | بررسی به‌روزرسانی |
| `hcx/i18n.py` | مدیریت زبان‌ها |
| `tests/` | تست‌های خودکار |

## 🧪 آزمایش برنامه

این پروژه دارای **۶۱ تست خودکار** است.

اجرای تست در ویندوز:

```bash
run_tests.bat
```

اجرای تست در لینوکس:

```bash
bash run_tests.sh
```

اجرای مستقیم با پایتون:

```bash
python -m unittest discover -s tests -t .
```

برای اجرای تست‌ها فقط کتابخانه NumPy لازم است.

**نکته:** تست‌های خودکار عملکرد منطقی برنامه را بررسی می‌کنند. عملکرد واقعی دوربین، کنترل صفحه‌نمایش و سرویس‌های خارجی باید جداگانه آزمایش شود.

## 📦 ساخت فایل اجرایی

برای ساخت فایل EXE در ویندوز:

```bash
build_exe.bat
```

برای ساخت نصب‌کننده ویندوز، فایل `installer.iss` را با نرم‌افزار Inno Setup باز و کامپایل کنید.

## 💾 محل ذخیره اطلاعات

اطلاعات برنامه در مسیر زیر ذخیره می‌شوند:

```text
~/.hand_control/
```

ساختار اطلاعات:

```text
.hand_control/
├── config.json
├── stats.json
├── plugins/
└── lang/
    └── <language_code>.json
```

## 🔐 امنیت و حریم خصوصی

- تشخیص ژست به‌صورت محلی انجام می‌شود.
- امکان استفاده از تشخیص صوتی آفلاین وجود دارد.
- کنترل از راه دور با PIN محافظت می‌شود.
- سیستم افزونه امکان توسعه مستقل قابلیت‌ها را فراهم می‌کند.

---

## 🚀 Future Development | توسعه آینده

- Advanced AI-based gesture recognition
- Improved gesture customization
- Enhanced accessibility
- More smart home integrations
- Advanced desktop automation

- توسعه تشخیص ژست با هوش مصنوعی
- شخصی‌سازی بیشتر حرکات دست
- بهبود امکانات دسترس‌پذیری
- اتصال به سرویس‌های بیشتر خانه هوشمند
- توسعه قابلیت‌های اتوماسیون دسکتاپ

---

## 📄 License | مجوز

Choose an appropriate open-source license before publishing.

پیش از انتشار عمومی پروژه، مجوز متن‌باز مناسب را انتخاب و به مخزن اضافه کنید.
---
## 🤖 Development Credits |  اعتبار توسعه

**HandControlPro** was developed through a collaboration between its creator and Artificial Intelligence (AI).

The project concept, direction, design decisions, development, testing, and final implementation were led by the creator, with AI assistance used for coding, debugging, problem-solving, and optimization.

**HandControlPro** با همکاری سازنده پروژه و هوش مصنوعی توسعه داده شده است.

ایده اصلی، مدیریت پروژه، تصمیم‌گیری‌های طراحی، توسعه، آزمایش و پیاده‌سازی نهایی توسط سازنده انجام شده و از هوش مصنوعی برای کمک در کدنویسی، اشکال‌زدایی، حل مشکلات و بهینه‌سازی استفاده شده است.

**Created by:** Project Creator  
**Development Assistance:** Artificial Intelligence (AI)
---

<p align="center">
  <b>🖐️ Hand Control Pro 4.0</b>
  <br>
  Control Your Digital World with Your Hands.
  <br>
  دنیای دیجیتال خود را با دستانتان کنترل کنید.
</p>
