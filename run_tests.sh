#!/usr/bin/env bash
# اجرای همهٔ تست‌ها (بدون دوربین و بدون PyQt6 نصب‌شده؛ فقط numpy لازم است)
cd "$(dirname "$0")"
python3 -m unittest discover -s tests -t . -v
