"""ساخت آیکون برنامه (app_icon.ico) — نیاز به Pillow (همراه mediapipe نصب می‌شود)"""
from PIL import Image, ImageDraw

SIZE = 512
ACCENT = (109, 139, 255)


def lerp(a, b, t):
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def build():
    k = SIZE / 100.0
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    # پس‌زمینهٔ گرادیان
    grad = Image.new("RGBA", (SIZE, SIZE))
    gp = grad.load()
    light = lerp(ACCENT, (255, 255, 255), 0.25)
    for y in range(SIZE):
        for x in range(SIZE):
            gp[x, y] = lerp(light, ACCENT, (x + y) / (2.0 * SIZE)) + (255,)
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, SIZE, SIZE), radius=int(22 * k), fill=255)
    img.paste(grad, (0, 0), mask)

    d = ImageDraw.Draw(img)
    white = (255, 255, 255, 255)
    for x, y, w, h in [(30, 48, 40, 34), (30, 22, 8, 34), (41, 15, 8, 40),
                       (52, 15, 8, 40), (63, 22, 8, 34)]:
        d.rounded_rectangle((x * k, y * k, (x + w) * k, (y + h) * k),
                            radius=int(4 * k), fill=white)
    # شست (چرخیده)
    thumb = Image.new("RGBA", (int(40 * k), int(40 * k)), (0, 0, 0, 0))
    ImageDraw.Draw(thumb).rounded_rectangle(
        (16 * k, 4 * k, 24 * k, 28 * k), radius=int(4 * k), fill=white)
    thumb = thumb.rotate(35, resample=Image.BICUBIC, center=(20 * k, 20 * k))
    img.alpha_composite(thumb, (int(28 * k - 20 * k), int(62 * k - 16 * k)))
    return img


if __name__ == "__main__":
    img = build()
    img.save("app_icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                                    (64, 64), (128, 128), (256, 256)])
    img.resize((256, 256)).save("app_icon.png")
    print("app_icon.ico ساخته شد")
