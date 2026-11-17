#!/usr/bin/env bash
# نصب Hand Control Pro روی لینوکس (X11). اجرا:  bash install_linux.sh
set -e
cd "$(dirname "$0")"
HERE="$(pwd)"

echo "== ۱) بسته‌های سیستم (نیاز به sudo) =="
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y python3-venv python3-tk python3-dev x11-utils xdotool \
    libgl1 libglib2.0-0 libxkbcommon-x11-0 libxcb-cursor0 libxcb-xinerama0 \
    pulseaudio-utils playerctl libportaudio2 fonts-noto-core fonts-noto-color-emoji
elif command -v dnf >/dev/null 2>&1; then
  sudo dnf install -y python3-tkinter python3-devel xorg-x11-utils xdotool mesa-libGL \
    xcb-util-cursor pulseaudio-utils playerctl google-noto-sans-arabic-fonts google-noto-color-emoji-fonts
elif command -v pacman >/dev/null 2>&1; then
  sudo pacman -S --needed --noconfirm tk xorg-xprop xdotool libxcb xcb-util-cursor \
    libpulse playerctl noto-fonts noto-fonts-emoji
else
  echo "مدیر بستهٔ شناخته‌نشده. دستی نصب کنید: tkinter، xprop، xdotool، libxcb-cursor، playerctl، فونت Noto"
fi

echo "== ۲) پیدا کردن پایتون 3.9 تا 3.12 (mediapipe روی ۳.۱۳ به بالا نصب نمی‌شود) =="
PYBIN=""
for c in python3.12 python3.11 python3.10 python3.9 python3; do
  if command -v "$c" >/dev/null 2>&1; then
    ok=$("$c" -c 'import sys; print((3,9) <= sys.version_info[:2] <= (3,12))')
    if [ "$ok" = "True" ]; then PYBIN="$c"; break; fi
  fi
done
if [ -z "$PYBIN" ]; then
  echo "پایتون 3.9 تا 3.12 پیدا نشد. با pyenv یا uv نصبش کنید (مثلاً: uv python install 3.12)، بعد دوباره اجرا کنید."
  exit 1
fi
echo "استفاده از: $PYBIN"

echo "== ۳) محیط مجازی و کتابخانه‌ها =="
"$PYBIN" -m venv venv
./venv/bin/python -m pip install --upgrade pip
./venv/bin/pip install --default-timeout=300 --retries 10 \
  numpy==1.26.4 mediapipe==0.10.21 pyautogui PyQt6 pynput

echo "== ۳٫۵) بسته‌های اختیاری (صدا، MQTT، OBS) — اگر خطا داد نادیده بگیرید =="
./venv/bin/pip install --default-timeout=300 --retries 5 vosk sounddevice paho-mqtt obsws-python \
  || echo "بسته‌های اختیاری نصب نشد؛ برنامه بدون آن‌ها کار می‌کند."

echo "== ۴) میان‌بر برنامه (منوی برنامه‌ها) =="
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/hand-control-pro.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=Hand Control Pro
Comment=کنترل کامپیوتر با ژست دست
Exec=$HERE/venv/bin/python $HERE/hand_control_pro.py
Icon=$HERE/app_icon.png
Terminal=false
Categories=Utility;
DESK

chmod +x run_linux.sh build_linux.sh 2>/dev/null || true
echo
echo "تمام شد ✅  اجرا:  ./run_linux.sh   (یا از منوی برنامه‌ها: Hand Control Pro)"
echo
echo "یادآوری‌ها:"
echo " • دوربین: اگر باز نشد، یک بار بزنید  sudo usermod -aG video \$USER  و از سیستم خارج/وارد شوید."
echo " • فقط نشست X11/Xorg: در صفحهٔ ورود «Ubuntu on Xorg» (یا مشابه) را انتخاب کنید؛ در Wayland ماوس کنترل نمی‌شود."
echo " • آیکون کنار ساعت در GNOME به افزونهٔ «AppIndicator» نیاز دارد."
