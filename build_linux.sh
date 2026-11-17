#!/usr/bin/env bash
# ساخت یک فایل اجرایی تک‌فایل برای لینوکس (بعد از install_linux.sh)
set -e
cd "$(dirname "$0")"
[ -x venv/bin/python ] || { echo "اول bash install_linux.sh را اجرا کنید."; exit 1; }
./venv/bin/pip install --default-timeout=300 --retries 10 pyinstaller
[ -f make_icon.py ] && ./venv/bin/python make_icon.py || true
./venv/bin/pyinstaller --noconfirm --clean --onefile --name HandControlPro \
  --collect-all mediapipe --hidden-import pyperclip hand_control_pro.py
echo "خروجی: $(pwd)/dist/HandControlPro"
