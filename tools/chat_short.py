"""Short de miedo en formato chat: "Ábreme".
Todo hecho a mano: interfaz dibujada con PIL, sonido sintetizado con numpy, montaje con ffmpeg."""
import math
import random
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import json
import sys
import tempfile
STORY = json.load(open(sys.argv[1], encoding="utf-8"))
OUT_FILE = Path(sys.argv[2])
OUT = OUT_FILE.parent
WORK = Path(tempfile.mkdtemp(prefix="chat_short_"))
OUT.mkdir(parents=True, exist_ok=True)
WORK.mkdir(parents=True, exist_ok=True)
W, H, FPS = 1080, 1920, 30
SR = 44100
FD = "/usr/share/fonts/truetype/google-fonts/"


def F(name, size):
    return ImageFont.truetype(FD + f"Poppins-{name}.ttf", size)


f_msg = F("Regular", 50)
f_time = F("Regular", 26)
f_name = F("Bold", 46)
f_status = F("Regular", 31)
f_bar = F("Medium", 36)
f_input = F("Regular", 44)
f_intro = F("Bold", 78)
f_intro_s = F("Medium", 40)
f_end = F("Bold", 92)
f_end_s = F("Regular", 44)
f_ban_t = F("Bold", 38)
f_ban_b = F("Regular", 38)
f_ban_s = F("Regular", 30)
f_avatar = F("Bold", 50)
f_chip = F("Medium", 28)

BG = (11, 11, 14)
HEADER = (22, 22, 26)
RECV = (40, 40, 46)
SENT = (43, 92, 226)
WHITE = (242, 242, 246)
GRAY = (140, 140, 150)
RED = (235, 55, 55)
GREEN = (90, 209, 122)
CHAT_TOP, CHAT_BOT = 250, 1715
MAXW = 760
PADX, PADY = 34, 20
LH = 66

# ---------------- Historia ----------------
SCRIPT = [tuple(x) for x in STORY["script"]]
BANNER_TEXT = STORY["banner"]["text"]

# ---------------- Cronología ----------------
INTRO_END = 2.7
t = 3.0
msgs, typing, inputs, knocks, sfx = [], [], [], [], []
banner_t = None
dip = None
for item in SCRIPT:
    kind = item[0]
    if kind == "M":
        text = item[1]
        typ = min(1.2, 0.45 + 0.018 * len(text))
        typing.append((t, t + typ))
        t += typ
        msgs.append(dict(side="M", text=text, time=item[2], t=t))
        sfx.append(("recv", t))
        t += 0.45 + 0.033 * len(text)
    elif kind == "Y":
        text = item[1]
        typ = len(text) / 28 + 0.15
        inputs.append((t, t + typ - 0.1, text))
        n = len(text)
        for c in range(n):
            sfx.append(("key", t + (typ - 0.1) * c / n))
        t += typ
        msgs.append(dict(side="Y", text=text, time=item[2], t=t))
        sfx.append(("send", t))
        t += 0.35 + 0.02 * len(text)
    elif kind == "KNOCK3":
        t += 0.2
        for k in range(3):
            knocks.append((t + 0.42 * k, 16, 0.8))
        heart_start = t
        t += 1.75
    elif kind == "TYPESTOP":
        typing.append((t + 0.3, t + 2.6))
        dip = (t + 0.3, None)
        t += 3.1
    elif kind == "BANNER":
        banner_t = t
        dip = (dip[0], t + 0.25)
        sfx.append(("chime", t))
        t += 4.4
    elif kind == "FINAL":
        t += 0.7
        for k in range(3):
            knocks.append((t + 0.33 * k, 34 + 14 * k, 1.15))
        black_t = knocks[-1][0] + 0.16
        sfx.append(("hit", black_t))
        end_t = black_t + 0.7
        T = end_t + 2.6
heart_end = black_t
NF = int(round(T * FPS))
print("golpes", [round(k[0],2) for k in knocks]); print(f"Duración: {T:.2f} s | banner {banner_t:.2f} | negro {black_t:.2f} | frames {NF}")


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


# ---------------- Burbujas ----------------
def wrap(text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        cand = (cur + " " + w_).strip()
        if font.getlength(cand) <= maxw or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = w_
    lines.append(cur)
    return lines


def make_bubble(m):
    inner = MAXW - 2 * PADX
    lines = wrap(m["text"], f_msg, inner)
    widths = [f_msg.getlength(l) for l in lines]
    tw = f_time.getlength(m["time"])
    last = widths[-1] + 22 + tw
    if last <= inner + 90:
        bw = max(max(widths), last)
        bh = len(lines) * LH
    else:
        bw = max(widths)
        bh = len(lines) * LH + 34
    w_, h_ = int(bw + 2 * PADX), int(bh + 2 * PADY)
    im = Image.new("RGBA", (w_, h_), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = SENT if m["side"] == "Y" else RECV
    d.rounded_rectangle([0, 0, w_ - 1, h_ - 1], radius=38, fill=col + (255,))
    for i, l in enumerate(lines):
        d.text((PADX, PADY + i * LH + 4), l, font=f_msg, fill=WHITE)
    tcol = (205, 215, 255) if m["side"] == "Y" else GRAY
    d.text((w_ - PADX, h_ - PADY + 2), m["time"], font=f_time, fill=tcol, anchor="rd")
    return im


for m in msgs:
    m["img"] = make_bubble(m)

chip = Image.new("RGBA", (150, 56), (0, 0, 0, 0))
ImageDraw.Draw(chip).rounded_rectangle([0, 0, 149, 55], radius=18, fill=(30, 30, 35, 255))
ImageDraw.Draw(chip).text((75, 28), "HOY", font=f_chip, fill=GRAY, anchor="mm")


def typing_bubble(t):
    im = Image.new("RGBA", (170, 104), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, 169, 103], radius=38, fill=RECV + (255,))
    for i in range(3):
        ph = math.sin(2 * math.pi * 1.6 * t - i * 0.9)
        y = 52 - 7 * max(0, ph)
        g = int(120 + 80 * max(0, ph))
        d.ellipse([46 + i * 32 - 10, y - 10, 46 + i * 32 + 10, y + 10], fill=(g, g, g + 8, 255))
    return im


def is_typing(t):
    return any(a <= t < b for a, b in typing)


# ---------------- Capas fijas ----------------
def draw_statusbar(d, t):
    label = SCRIPT[0][2]
    for m in msgs:
        if m["t"] <= t:
            label = m["time"]
    d.text((70, 42), label, font=f_bar, fill=WHITE, anchor="lm")
    # cobertura
    for i in range(4):
        x = 850 + i * 16
        d.rectangle([x, 54 - 8 - i * 6, x + 10, 54], fill=WHITE if i < 2 else (90, 90, 96))
    # batería
    d.rounded_rectangle([930, 28, 1000, 56], radius=7, outline=WHITE, width=3)
    d.rectangle([1002, 36, 1007, 48], fill=WHITE)
    d.rectangle([936, 34, 951, 50], fill=RED)


def draw_header(d, t):
    d.rectangle([0, 0, W, CHAT_TOP], fill=HEADER)
    draw_statusbar(d, t)
    d.line([(52, 150), (32, 172), (52, 194)], fill=(120, 160, 255), width=6, joint="curve")
    d.ellipse([90, 122, 190, 222], fill=(120, 80, 160))
    d.text((140, 172), STORY["contact"][0].upper(), font=f_avatar, fill=WHITE, anchor="mm")
    d.text((215, 150), STORY["contact"], font=f_name, fill=WHITE, anchor="lm")
    if is_typing(t):
        d.text((215, 200), "escribiendo...", font=f_status, fill=GREEN, anchor="lm")
    else:
        d.text((215, 200), "en línea", font=f_status, fill=GRAY, anchor="lm")
    d.line([(0, CHAT_TOP - 1), (W, CHAT_TOP - 1)], fill=(34, 34, 40), width=2)


def draw_input(d, t):
    d.rectangle([0, CHAT_BOT, W, H], fill=(17, 17, 20))
    d.rounded_rectangle([30, 1745, 905, 1860], radius=57, fill=(34, 34, 39))
    txt = ""
    for a, b, text in inputs:
        if a <= t < b + 0.1:
            n = int(len(text) * min(1.0, (t - a) / (b - a)))
            txt = text[:n]
    if txt:
        shown = txt
        while f_input.getlength(shown) > 780:
            shown = shown[1:]
        d.text((72, 1802), shown, font=f_input, fill=WHITE, anchor="lm")
        if int(t * 2.5) % 2 == 0:
            x = 72 + f_input.getlength(shown) + 4
            d.rectangle([x, 1778, x + 3, 1828], fill=(120, 160, 255))
    else:
        d.text((72, 1802), "Mensaje", font=f_input, fill=(100, 100, 108), anchor="lm")
    col = SENT if txt else (52, 52, 58)
    d.ellipse([925, 1747, 1035, 1857], fill=col)
    d.polygon([(958, 1772), (1010, 1802), (958, 1832), (968, 1802)], fill=WHITE)


def banner_layer(t):
    lines = wrap(BANNER_TEXT, f_ban_b, 850)
    bh = 120 + len(lines) * 52 + 26
    im = Image.new("RGBA", (W - 60, bh + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 6, W - 61, bh + 6], radius=40, fill=(0, 0, 0, 150))
    d.rounded_rectangle([0, 0, W - 61, bh], radius=40, fill=(46, 46, 52, 250))
    d.ellipse([34, 34, 104, 104], fill=(52, 140, 90))
    d.text((69, 69), STORY["banner"]["from"][0].upper(), font=f_ban_t, fill=WHITE, anchor="mm")
    d.text((130, 50), STORY["banner"]["from"], font=f_ban_t, fill=WHITE, anchor="lm")
    d.text((W - 100, 50), "ahora", font=f_ban_s, fill=GRAY, anchor="rm")
    for i, l in enumerate(lines):
        d.text((130, 86 + i * 52), l, font=f_ban_b, fill=(225, 225, 230))
    return im


BANNER_IMG = banner_layer(0)

# ---------------- Composición ----------------
scroll = 0.0


def chat_frame(t):
    global scroll
    img = Image.new("RGB", (W, H), BG)
    items = [("chip", chip, None)]
    for m in msgs:
        if m["t"] <= t:
            items.append(("msg", m["img"], m))
    if is_typing(t):
        items.append(("typ", typing_bubble(t), None))
    ys, y, prev = [], 30, None
    for kind, im, m in items:
        side = m["side"] if m else ("M" if kind == "typ" else "C")
        if prev is not None:
            y += 16 if side == prev else 34
        ys.append(y)
        y += im.height
        prev = side
    total = y + 40
    avail = CHAT_BOT - CHAT_TOP
    target = max(0.0, total - avail)
    scroll += (target - scroll) * 0.35
    for (kind, im, m), yy in zip(items, ys):
        top = CHAT_TOP + yy - int(scroll)
        if top > CHAT_BOT or top + im.height < CHAT_TOP - 10:
            continue
        side = m["side"] if m else ("M" if kind == "typ" else "C")
        if kind == "msg" and t - m["t"] < 0.18:
            e = ease((t - m["t"]) / 0.18)
            s = 0.86 + 0.14 * e
            sim = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
            a = sim.getchannel("A").point(lambda v, e=e: int(v * e))
            sim.putalpha(a)
            im = sim
            top = top + (int(m["img"].height) - im.height)
        if side == "Y":
            x = W - 40 - im.width
        elif side == "M":
            x = 40
        else:
            x = (W - im.width) // 2
        img.paste(im, (x, top), im)
    d = ImageDraw.Draw(img)
    draw_header(d, t)
    draw_input(d, t)
    if banner_t is not None and t >= banner_t:
        p = ease((t - banner_t) / 0.4)
        by = int(-BANNER_IMG.height + p * (BANNER_IMG.height + 40))
        img.paste(BANNER_IMG, (30, by), BANNER_IMG)
    return img


def intro_frame(t):
    img = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((W // 2, 830), STORY["intro"][0], font=f_intro, fill=WHITE, anchor="mm")
    l2a, l2b = STORY["intro"][1], STORY["intro"][2]
    wa, wb = f_intro.getlength(l2a), f_intro.getlength(l2b)
    x0 = (W - wa - wb) / 2
    d.text((x0, 940), l2a, font=f_intro, fill=WHITE, anchor="lm")
    d.text((x0 + wa, 940), l2b, font=f_intro, fill=RED, anchor="lm")
    d.text((W // 2, 1060), STORY["intro"][3], font=f_intro, fill=WHITE, anchor="mm")
    d.text((W // 2, 1210), STORY["intro"][4], font=f_intro_s, fill=GRAY, anchor="mm")
    return img


def end_frame(t):
    img = Image.new("RGB", (W, H), (0, 0, 0))
    a = ease((t - end_t) / 0.5)
    d = ImageDraw.Draw(img)
    c = tuple(int(v * a) for v in WHITE)
    r = tuple(int(v * a) for v in RED)
    g = tuple(int(v * a) for v in GRAY)
    d.text((W // 2, 880), STORY["end"][0], font=f_end, fill=c, anchor="mm")
    d.text((W // 2, 1000), STORY["end"][1], font=f_end, fill=r, anchor="mm")
    d.text((W // 2, 1140), STORY["end"][2], font=f_end_s, fill=g, anchor="mm")
    return img


def postfx(img, t, fi):
    shake, chroma = 0.0, 0
    for kt, amp, _ in knocks:
        if 0 <= t - kt < 0.6:
            shake += amp * math.exp(-(t - kt) * 11)
        if 0 <= t - kt < 0.10:
            chroma = max(chroma, int(amp * 0.7))
    final_glitch = knocks[-3][0] <= t < black_t
    if shake < 0.5 and chroma == 0 and not final_glitch:
        return img
    arr = np.asarray(img).copy()
    rng = np.random.default_rng(fi)
    if chroma:
        arr[..., 0] = np.roll(arr[..., 0], chroma, axis=1)
        arr[..., 2] = np.roll(arr[..., 2], -chroma, axis=1)
        arr = np.clip(arr.astype(np.int16) + 30, 0, 255).astype(np.uint8)
    if final_glitch:
        for _ in range(7):
            y0 = int(rng.integers(0, H - 150))
            hh = int(rng.integers(20, 150))
            arr[y0:y0 + hh] = np.roll(arr[y0:y0 + hh], int(rng.integers(-90, 90)), axis=1)
        arr[..., 0] = np.clip(arr[..., 0].astype(np.int16) + 35, 0, 255).astype(np.uint8)
    out = Image.fromarray(arr)
    if shake >= 0.5:
        dx = int(shake * math.sin(t * 113))
        dy = int(shake * math.cos(t * 97))
        canvas = Image.new("RGB", (W, H), (0, 0, 0))
        canvas.paste(out, (dx, dy))
        out = canvas
    return out


# ---------------- Audio ----------------
N = int((T + 0.2) * SR)
rng = np.random.default_rng(7)
dry = np.zeros((N, 2))
fx = np.zeros((N, 2))


def place(buf, sig, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR)
    if i >= N:
        return
    sig = sig[: N - i]
    l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
    buf[i:i + len(sig), 0] += sig * gain * l * 1.414
    buf[i:i + len(sig), 1] += sig * gain * r * 1.414


def tt(d):
    return np.arange(int(d * SR)) / SR


def smooth(x, n):
    k = np.ones(n) / n
    return np.convolve(x, k, mode="same")


def key_click():
    x = tt(0.02)
    s = rng.standard_normal(len(x)) * np.exp(-x * 280)
    s = np.diff(s, prepend=0) * 0.5 + 0.4 * np.sin(2 * np.pi * 2300 * x) * np.exp(-x * 400)
    return s


def send_snd():
    x = tt(0.14)
    f = 500 + 700 * x / 0.14
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 30) * (1 - np.exp(-x * 600))


def recv_snd():
    x = tt(0.12)
    env = np.exp(-x * 38) * (1 - np.exp(-x * 900))
    a = np.sin(2 * np.pi * 880 * x) * env
    b = np.sin(2 * np.pi * 1320 * x) * env
    out = np.zeros(int(0.2 * SR))
    out[: len(a)] += a
    o = int(0.075 * SR)
    out[o:o + len(b)] += b
    return out


def knock_snd(bright=1.0):
    x = tt(0.6)
    s = (0.7 * np.sin(2 * np.pi * 95 * x) * np.exp(-x * 18)
         + 0.55 * np.sin(2 * np.pi * 190 * x) * np.exp(-x * 30)
         + 0.35 * bright * np.sin(2 * np.pi * 410 * x) * np.exp(-x * 45))
    nz = smooth(rng.standard_normal(len(x)), 12) * np.exp(-x * 70) * 0.9
    return (s + nz) * (1 - np.exp(-x * 2000))


def chime():
    out = np.zeros(int(1.0 * SR))
    for k, f in enumerate((1318.5, 987.8)):
        x = tt(0.8)
        s = (np.sin(2 * np.pi * f * x) + 0.3 * np.sin(4 * np.pi * f * x)) * np.exp(-x * 7) * (1 - np.exp(-x * 800))
        o = int(k * 0.16 * SR)
        out[o:o + len(s)] += s[: len(out) - o]
    return out


def thump():
    x = tt(0.32)
    env = np.exp(-x * 19) * (1 - np.exp(-x * 400))
    return (np.sin(2 * np.pi * 62 * x) + 0.6 * np.sin(2 * np.pi * 124 * x) + 0.25 * np.sin(2 * np.pi * 248 * x)) * env


def hit():
    x = tt(2.4)
    f = 75 * np.exp(-x * 0.6)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = (np.sin(ph) + 0.6 * np.sin(2 * ph) + 0.3 * np.sin(4 * ph)) * np.exp(-x * 1.8)
    nz = smooth(rng.standard_normal(len(x)), 6) * np.exp(-x * 5) * 0.8
    scr = 0.25 * (np.sin(2 * np.pi * 1760 * x) + np.sin(2 * np.pi * 1797 * x)) * np.exp(-x * 2.5)
    return (s + nz + scr) * (1 - np.exp(-x * 1500))


for kind, t0 in sfx:
    if kind == "key":
        place(dry, key_click(), t0, 0.13 * rng.uniform(0.7, 1.1), rng.uniform(-0.2, 0.2))
    elif kind == "send":
        place(dry, send_snd(), t0, 0.16)
    elif kind == "recv":
        place(dry, recv_snd(), t0, 0.2)
        place(fx, recv_snd(), t0, 0.05)
    elif kind == "chime":
        place(dry, chime(), t0, 0.32)
        place(fx, chime(), t0, 0.15)
    elif kind == "hit":
        place(dry, hit(), t0, 0.75)
        place(fx, hit(), t0, 0.35)
for kt, amp, g in knocks:
    k = knock_snd(1.3 if g > 1 else 1.0)
    place(dry, k, kt, 0.55 * g, 0.15)
    place(fx, k, kt, 0.3 * g)

# latido: de los primeros golpes al final, acelerando
tb = heart_start + 0.6
while tb < heart_end - 0.1:
    prog = (tb - heart_start) / (heart_end - heart_start)
    gain = 0.18 + 0.32 * prog
    if not (dip and dip[0] < tb < dip[1]):
        place(dry, thump(), tb, gain)
        place(dry, thump(), tb + 0.21, gain * 0.6)
    tb += 0.95 - 0.35 * prog

# ambiente
x = np.arange(N) / SR
spec = np.fft.rfft(rng.standard_normal(N))
fr = np.fft.rfftfreq(N, 1 / SR)
shape = 1 / np.sqrt(np.maximum(fr, 25) / 25) / (1 + (fr / 900) ** 2)
room = np.fft.irfft(spec * shape, n=N)
room /= np.max(np.abs(room)) + 1e-9
drone = (0.05 * np.sin(2 * np.pi * 55 * x)
         + 0.035 * np.sin(2 * np.pi * 110 * x) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * x))
         + 0.016 * np.sin(2 * np.pi * 196 * x) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * x))
         + 0.016 * np.sin(2 * np.pi * 207.65 * x) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.05 * x + 1))
         + 0.10 * room)
eerie = 0.010 * (np.sin(2 * np.pi * 1975 * x) + np.sin(2 * np.pi * 1982 * x))
pts_t = [0, 3.0, heart_start, dip[0], dip[0] + 0.4, dip[1] - 0.05, dip[1] + 0.6, black_t, black_t + 0.05, T]
pts_g = [0.0, 0.45, 0.8, 0.8, 0.12, 0.12, 1.15, 1.25, 0.25, 0.0]
env = np.interp(x, pts_t, pts_g)
eenv = np.interp(x, [0, dip[1], dip[1] + 2.5, black_t, black_t + 0.05, T], [0, 0, 1, 1, 0, 0])
amb = drone * env + eerie * eenv
dry[:, 0] += amb
dry[:, 1] += amb * 0.97

# reverberación del bus de efectos
ir_len = int(1.3 * SR)
ir_t = np.arange(ir_len) / SR
mixed = dry.copy()
for ch in range(2):
    ir = smooth(rng.standard_normal(ir_len), 4) * np.exp(-ir_t * 4.2)
    n = 1 << int(math.ceil(math.log2(N + ir_len)))
    wet = np.fft.irfft(np.fft.rfft(fx[:, ch], n) * np.fft.rfft(ir, n), n)[:N]
    wet /= np.max(np.abs(ir)) * 18
    mixed[:, ch] += wet + fx[:, ch] * 0.6
mixed /= np.max(np.abs(mixed)) / 0.89
wav = WORK / "audio.wav"
with wave.open(str(wav), "wb") as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    wf.writeframes((mixed * 32767).astype(np.int16).tobytes())
print("audio ok")

# ---------------- Render ----------------
out = OUT_FILE
cmd = [
    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
    "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-i", str(wav),
    "-filter_complex",
    "[0:v]vignette=angle=PI/5,eq=brightness='0.012*(random(0)-0.5)':eval=frame,"
    "noise=alls=6:allf=t+u,format=yuv420p[v];"
    "[1:a]loudnorm=I=-15:TP=-1.5:LRA=11,aresample=44100[a]",
    "-map", "[v]", "-map", "[a]",
    "-c:v", "libx264", "-preset", "medium", "-crf", "24", "-maxrate", "4M", "-bufsize", "8M",
    "-c:a", "aac", "-b:a", "192k", "-t", f"{T:.2f}", "-movflags", "+faststart", str(out),
]
proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
for fi in range(NF):
    t = fi / FPS
    if t < INTRO_END:
        frame = intro_frame(t)
        if t > INTRO_END - 0.35:
            frame = Image.blend(frame, Image.new("RGB", (W, H)), (t - (INTRO_END - 0.35)) / 0.35)
    elif t < black_t:
        frame = chat_frame(t)
        if t < 3.1:
            frame = Image.blend(Image.new("RGB", (W, H)), frame, ease((t - INTRO_END) / 0.4))
        frame = postfx(frame, t, fi)
    elif t < end_t:
        frame = Image.new("RGB", (W, H))
    else:
        frame = end_frame(t)
    proc.stdin.write(frame.tobytes())
proc.stdin.close()
proc.wait()
print("OK", out)
