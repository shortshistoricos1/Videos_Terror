"""Monta un vídeo largo de terror (1920x1080, 24 fps) a partir de largos/<ID>/.
Uso: python3 -I tools/largo.py largos/<ID> <salida.mp4> [N_BLOQUES_PRUEBA]
Necesita: historia.json, voces/bloque_XXX.mp3 (de la Action) e imgs/bloque_XXX.jpg (de la Action).
Genera además largos/<ID>/miniatura.jpg y largos/<ID>/capitulos.txt."""
import json
import math
import re
import subprocess
import sys
import tempfile
import textwrap
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

D = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
LIMIT = int(sys.argv[3]) if len(sys.argv) > 3 else None
ROOT = Path(__file__).resolve().parent.parent
H = json.loads((D / "historia.json").read_text(encoding="utf-8"))
TMP = Path(tempfile.mkdtemp(prefix="largo_"))
SEG, TXT, IMG = TMP / "seg", TMP / "txt", TMP / "img"
for p in (SEG, TXT, IMG):
    p.mkdir()
FPS, SR = 24, 44100
GF = "/usr/share/fonts/truetype/google-fonts/"
F_SUB, F_SERIF, F_BOLD = GF + "Poppins-Medium.ttf", GF + "Lora-Variable.ttf", GF + "Poppins-Bold.ttf"
NUM = {"uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9,
       "diez": 10, "once": 11, "doce": 12}


def dur_of(f):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(f)]))


# ---------- imágenes: normalizadas a 2400x1350 con gradación de terror ----------
def prep_img(src, dst):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    s = max(2400 / w, 1350 / h)
    im = im.resize((int(w * s + 1), int(h * s + 1)), Image.LANCZOS)
    w, h = im.size
    im = im.crop(((w - 2400) // 2, (h - 1350) // 2, (w - 2400) // 2 + 2400, (h - 1350) // 2 + 1350))
    a = np.asarray(im, np.float32) / 255.0
    g = a.mean(2, keepdims=True)
    a = g + (a - g) * 0.88                       # algo menos de saturación
    a = a * np.array([0.93, 0.98, 1.06])         # tono frío
    a = np.clip((a - 0.5) * 1.08 + 0.47, 0, 1)   # algo más de contraste y oscuridad
    y, x = np.ogrid[:1350, :2400]
    dd = np.sqrt(((x - 1200) / 1200) ** 2 + ((y - 675) / 675) ** 2)
    a = a * np.clip(1 - 0.55 * (dd / 1.414) ** 2.2, 0, 1)[..., None]
    Image.fromarray((a * 255).astype(np.uint8)).save(dst, quality=94)


blocks, last_img = [], None
for i, b in enumerate(H["bloques"]):
    if LIMIT and i >= LIMIT:
        break
    b = dict(b, i=i, vdur=dur_of(D / "voces" / f"bloque_{i:03d}.mp3"))
    b.setdefault("tipo", "narracion")
    if b["tipo"] != "capitulo":
        src = D / "imgs" / f"bloque_{i:03d}.jpg"
        if src.exists():
            dst = IMG / f"b{i:03d}.jpg"
            prep_img(src, dst)
            last_img = dst
        b["img"] = last_img
    blocks.append(b)
first = next((b["img"] for b in blocks if b.get("img")), None)
if first is None:
    sys.exit("No hay ninguna imagen en imgs/")
for b in blocks:
    if b["tipo"] != "capitulo" and b["img"] is None:
        b["img"] = first
for k, b in enumerate(blocks):
    if b["tipo"] == "capitulo":
        nxt = next((x["img"] for x in blocks[k + 1:] if x["tipo"] != "capitulo"), first)
        b["img"] = nxt
        m = re.match(r"\s*([^\.]+)\.\s*(.+?)\.?\s*$", b["texto"])
        num = m.group(1).strip().lower() if m else ""
        b["chap"] = (NUM.get(num, num.upper()), (m.group(2) if m else b["texto"]).upper())
        b["pre"], b["post"] = 0.7, 1.1
    else:
        b["pre"] = 0.25
        b["post"] = float(b.get("pausa", 0.6))

t = 0.0
prev_img, prev_z, flip = None, 1.0, 0
for b in blocks:
    b["nf"] = int(math.ceil((b["pre"] + b["vdur"] + b["post"]) * FPS))
    b["dur"] = b["nf"] / FPS
    b["start"] = t
    t += b["dur"]
    if b["tipo"] == "capitulo":
        continue
    delta = min(0.16, 0.011 * b["dur"])
    if b["img"] == prev_img and prev_z + delta <= 1.45:
        z0 = prev_z
    else:
        z0 = 1.0
        flip += 1
    fx = [0.5, 0.35, 0.65, 0.45, 0.58][flip % 5]
    fy = [0.45, 0.4, 0.5, 0.55, 0.42][flip % 5]
    b["z"], b["f"] = (z0, z0 + delta), (fx, fy)
    prev_img, prev_z = b["img"], z0 + delta
END_CARD = 6.0
TOTAL = t + END_CARD
print(f"{len(blocks)} bloques · {TOTAL / 60:.2f} min", flush=True)

caps = ["0:00 Introducción"]
for b in blocks:
    if "chap" in b:
        s = int(b["start"])
        caps.append(f"{s // 60}:{s % 60:02d} {b['chap'][0]}. {b['chap'][1].capitalize()}")
(D / "capitulos.txt").write_text("\n".join(caps) + "\n", encoding="utf-8")


def chunks(text):
    out = []
    for s in re.findall(r"[^.?!…]+[.?!…]*", text):
        s = s.strip()
        while len(s) > 80:
            cut = max(s.rfind(", ", 0, 80), s.rfind(": ", 0, 80))
            if cut < 25:
                cut = s.rfind(" ", 0, 78)
            out.append(s[:cut + 1].strip())
            s = s[cut + 1:].strip()
        if s:
            out.append(s)
    merged = []
    for c in out:
        if merged and len(merged[-1]) + len(c) < 34:
            merged[-1] += " " + c
        else:
            merged.append(c)
    return merged


def esc(p):
    return str(p).replace(":", r"\:")


def seg_filter(b):
    d = b["dur"]
    parts = []
    if "chap" in b:
        n, title = b["chap"]
        f1, f2 = TXT / f"c{b['i']:03d}_a.txt", TXT / f"c{b['i']:03d}_b.txt"
        f1.write_text(f"CAPÍTULO {n}", encoding="utf-8")
        f2.write_text(title, encoding="utf-8")
        al = "if(lt(t,0.9),0,if(lt(t,1.5),(t-0.9)/0.6,1))"
        fs = 110 if len(title) <= 22 else 84
        parts.append(f"[0:v]scale=1920:1080,boxblur=22:2,eq=brightness=-0.22:saturation=0.5,"
                     f"drawtext=fontfile={F_SUB}:textfile={esc(f1)}:expansion=none:fontsize=40:fontcolor=0xE04040:"
                     f"x=(w-text_w)/2:y=440:alpha='{al}',drawbox=x=860:y=510:w=200:h=3:color=0xE04040@0.8:t=fill,"
                     f"drawtext=fontfile={F_SERIF}:textfile={esc(f2)}:expansion=none:fontsize={fs}:fontcolor=0xF0EEE8:"
                     f"x=(w-text_w)/2:y=545:alpha='{al}'")
    else:
        z0, z1 = b["z"]
        fx, fy = b["f"]
        Z = f"({z0}+({z1}-{z0})*t/{d:.3f})"
        chain = (f"[0:v]scale=w='2*trunc(1920*{Z}/2)':h='2*trunc(1080*{Z}/2)':eval=frame:flags=bicubic,"
                 f"crop=1920:1080:x='(iw-1920)*{fx}':y='(ih-1080)*{fy}'")
        if b.get("ambiente") == "nieve":
            chain += "[bg];[1:v]format=rgba,colorchannelmixer=aa=0.6[sn];[bg][sn]overlay=x=0:y='mod(t*75,1080)-1080':shortest=1"
        parts.append(chain)
        parts.append("eq=brightness='0.012*sin(2*PI*0.27*t)+0.012*(random(0)-0.5)':eval=frame")
        cs = chunks(b["texto"])
        w = [len(c) + 10 for c in cs]
        t0, t1 = b["pre"] + 0.05, b["pre"] + b["vdur"] - 0.2
        acc = t0
        for k, (c, wk) in enumerate(zip(cs, w)):
            a, e = acc, acc + (t1 - t0) * wk / sum(w)
            acc = e
            fp = TXT / f"s{b['i']:03d}_{k:02d}.txt"
            fp.write_text("\n".join(textwrap.wrap(c, 46)), encoding="utf-8")
            parts.append(f"drawtext=fontfile={F_SUB}:textfile={esc(fp)}:expansion=none:fontsize=44:text_align=center:"
                         f"fontcolor=0xF2F2F2:line_spacing=10:box=1:boxcolor=black@0.55:boxborderw=18:"
                         f"x=(w-text_w)/2:y=h-text_h-80:enable='between(t,{a:.2f},{e:.2f})'")
        if b["i"] == 0:
            ft, fs2 = TXT / "title.txt", TXT / "title2.txt"
            ft.write_text(H["titulo"].upper(), encoding="utf-8")
            fs2.write_text(H.get("subtitulo", "Una historia de miedo"), encoding="utf-8")
            al = f"if(lt(t,0.4),0,if(lt(t,1.6),(t-0.4)/1.2,if(gt(t,{d - 1.0:.2f}),({d:.2f}-t)/0.8,1)))"
            tsz = 104 if len(H["titulo"]) <= 26 else 80
            parts.append(f"drawbox=x=0:y=60:w=iw:h=260:color=black@0.35:t=fill")
            parts.append(f"drawtext=fontfile={F_SERIF}:textfile={esc(ft)}:expansion=none:fontsize={tsz}:fontcolor=0xF2EFE6:"
                         f"borderw=3:bordercolor=black@0.6:x=(w-text_w)/2:y=105:alpha='{al}'")
            parts.append(f"drawtext=fontfile={F_SUB}:textfile={esc(fs2)}:expansion=none:fontsize=40:fontcolor=0xE04040:"
                         f"x=(w-text_w)/2:y=232:alpha='{al}'")
    parts.append("noise=alls=5:allf=t+u")
    parts.append(f"fade=t=in:st=0:d=0.4,fade=t=out:st={d - 0.4:.3f}:d=0.4,format=yuv420p[v]")
    return ",".join(parts)


ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-r", str(FPS), "-g", "48", "-pix_fmt", "yuv420p", "-threads", "1"]


def render(b):
    out = SEG / f"seg_{b['i']:03d}.mp4"
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-loop", "1", "-framerate", str(FPS),
           "-t", f"{b['dur']:.4f}", "-i", str(b["img"])]
    if b["tipo"] != "capitulo" and b.get("ambiente") == "nieve":
        cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{b['dur']:.4f}", "-i", str(ROOT / "assets" / "snow.png")]
    cmd += ["-filter_complex", seg_filter(b), "-map", "[v]", "-frames:v", str(b["nf"])] + ENC + [str(out)]
    subprocess.run(cmd, check=True)
    return out


def render_end():
    out = SEG / "seg_end.mp4"
    f1, f2 = TXT / "end1.txt", TXT / "end2.txt"
    fin = H.get("final", ["¿Tú qué habrías hecho?", "Suscríbete para más historias de miedo"])
    f1.write_text(fin[0], encoding="utf-8")
    f2.write_text(fin[1], encoding="utf-8")
    al = "if(lt(t,0.6),t/0.6,1)"
    vf = (f"[0:v]scale=1920:1080,boxblur=24:2,eq=brightness=-0.32:saturation=0.4,"
          f"drawtext=fontfile={F_SERIF}:textfile={esc(f1)}:expansion=none:fontsize=96:fontcolor=0xF0EEE8:x=(w-text_w)/2:y=430:alpha='{al}',"
          f"drawtext=fontfile={F_SUB}:textfile={esc(f2)}:expansion=none:fontsize=42:fontcolor=0xE04040:x=(w-text_w)/2:y=590:alpha='{al}',"
          f"noise=alls=5:allf=t+u,fade=t=in:st=0:d=0.8,fade=t=out:st={END_CARD - 1.0}:d=1.0,format=yuv420p[v]")
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-loop", "1", "-framerate", str(FPS),
                    "-t", str(END_CARD), "-i", str(blocks[-1]["img"]), "-filter_complex", vf, "-map", "[v]",
                    "-frames:v", str(int(END_CARD * FPS))] + ENC + [str(out)], check=True)
    return out


# ---------- audio ----------
rng = np.random.default_rng(21)
N = int((TOTAL + 0.5) * SR)
voice, amb, sfx = (np.zeros(N, np.float32) for _ in range(3))


def load(path, af):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(path), "-af", af, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"])
    return np.frombuffer(raw, np.float32)


def put(buf, sig, t0, g=1.0):
    i = int(t0 * SR)
    if 0 <= i < N:
        sig = sig[: N - i]
        buf[i:i + len(sig)] += sig * g


def tt(d):
    return np.arange(int(d * SR)) / SR


def lp(x, n):
    return np.convolve(x, np.ones(n) / n, mode="same")


def shaped(n, lo, hi):
    spec = np.fft.rfft(rng.standard_normal(n).astype(np.float32))
    fr = np.fft.rfftfreq(n, 1 / SR)
    y = np.fft.irfft(spec * (((fr > lo) & (fr < hi)) / np.sqrt(np.maximum(fr, 20) / 100)), n=n)
    return (y / (np.abs(y).max() + 1e-9)).astype(np.float32)


def knock():
    x = tt(0.6)
    s = (0.7 * np.sin(2 * np.pi * 95 * x) * np.exp(-x * 18) + 0.55 * np.sin(2 * np.pi * 190 * x) * np.exp(-x * 30)
         + 0.35 * np.sin(2 * np.pi * 410 * x) * np.exp(-x * 45) + lp(rng.standard_normal(len(x)), 12) * np.exp(-x * 70) * 0.8)
    return s * (1 - np.exp(-x * 2000))


def scratch(d):
    x = tt(d)
    return shaped(len(x), 1500, 7000) * np.clip(np.sin(2 * np.pi * 1.4 * x), 0, 1) ** 2


def ring(d):
    x = tt(d)
    tone = np.sin(2 * np.pi * 820 * x) + 0.6 * np.sin(2 * np.pi * 1230 * x)
    return lp(tone * (np.sin(2 * np.pi * 22 * x) > 0) * ((x % 3.6) < 1.6), 20) * 0.6


def breath(d=2.4):
    x = tt(d)
    return shaped(len(x), 300, 2500) * np.sin(np.pi * np.clip(x / d, 0, 1)) ** 2


def thump():
    x = tt(0.32)
    return (np.sin(2 * np.pi * 62 * x) + 0.6 * np.sin(2 * np.pi * 124 * x) + 0.25 * np.sin(2 * np.pi * 248 * x)) * np.exp(-x * 19) * (1 - np.exp(-x * 400))


def boom():
    x = tt(3.0)
    ph = 2 * np.pi * np.cumsum(60 * np.exp(-x * 0.5)) / SR
    return ((np.sin(ph) + 0.5 * np.sin(2 * ph)) * np.exp(-x * 1.6) + lp(rng.standard_normal(len(x)), 30) * np.exp(-x * 3) * 0.5) * (1 - np.exp(-x * 60))


def hit():
    x = tt(3.0)
    ph = 2 * np.pi * np.cumsum(80 * np.exp(-x * 0.6)) / SR
    s = (np.sin(ph) + 0.6 * np.sin(2 * ph) + 0.3 * np.sin(4 * ph)) * np.exp(-x * 1.4)
    scr = 0.2 * (np.sin(2 * np.pi * 1760 * x) + np.sin(2 * np.pi * 1797 * x)) * np.exp(-x * 1.8)
    return (s + lp(rng.standard_normal(len(x)), 6) * np.exp(-x * 4) * 0.7 + scr) * (1 - np.exp(-x * 1500))


def when(b, phrase):
    k = b["texto"].find(phrase) if phrase else -1
    return b["start"] + b["pre"] + b["vdur"] * (max(k, 0) / max(1, len(b["texto"])))


def build_audio():
    for b in blocks:
        put(voice, load(D / "voces" / f"bloque_{b['i']:03d}.mp3", "highpass=f=70,aecho=0.8:0.75:30|60:0.10|0.05"), b["start"] + b["pre"])
    voice[:] = voice / (np.abs(voice).max() + 1e-9) * 0.8
    x = np.arange(N, dtype=np.float32) / SR
    drone = (0.05 * np.sin(2 * np.pi * 55 * x) + 0.035 * np.sin(2 * np.pi * 110 * x) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * x))
             + 0.014 * np.sin(2 * np.pi * 196 * x) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * x))
             + 0.014 * np.sin(2 * np.pi * 207.65 * x) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.05 * x + 1)) + 0.07 * shaped(N, 20, 900))
    amb[:] += drone * (0.55 + 0.6 * np.clip(x / TOTAL, 0, 1) ** 1.5)
    srcs = {"viento": (lambda: shaped(N, 150, 1800) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.09 * x)), 0.06),
            "nieve": (None, 0.06), "lluvia": (lambda: shaped(N, 1500, 9000), 0.035),
            "estatica": (lambda: shaped(N, 800, 5000), 0.03), "fuego": (None, 0.05)}
    layers = {}
    for b in blocks:
        a = b.get("ambiente", "interior")
        if a == "nieve":
            a = "viento"
        if a not in ("viento", "lluvia", "estatica", "fuego"):
            continue
        L = layers.setdefault(a, np.zeros(N, np.float32))
        i0, i1 = int(b["start"] * SR), int((b["start"] + b["dur"]) * SR)
        L[i0:i1] = 1
    for a, L in layers.items():
        if a == "fuego":
            f = np.zeros(N, np.float32)
            idx = rng.integers(0, N, 9000)
            f[idx] = rng.uniform(-1, 1, len(idx))
            src = lp(f, 6) * 3 + shaped(N, 40, 300) * 0.3
        else:
            src = srcs[a][0]()
        amb[:] += src * lp(L, 2000) * srcs[a][1]
    for b in blocks:
        if "chap" in b:
            put(sfx, boom(), b["start"] + 0.2, 0.35)
        for s in b.get("sfx", []):
            ty, t0 = s.get("tipo"), when(b, s.get("en", ""))
            if ty == "golpes":
                for k in range(3):
                    put(sfx, knock(), t0 + 0.05 + 0.5 * k, 0.28)
            elif ty == "aranazos":
                put(sfx, scratch(4.5), t0, 0.07)
            elif ty == "telefono":
                put(sfx, ring(7.0), t0, 0.09)
            elif ty == "respiracion":
                for k in range(2):
                    put(sfx, breath(), t0 + 0.3 + k * 2.8, 0.1)
            elif ty == "latido":
                tb = b["start"] + 0.4
                while tb < b["start"] + b["dur"] - 0.3:
                    put(sfx, thump(), tb, 0.22)
                    put(sfx, thump(), tb + 0.22, 0.13)
                    tb += 0.8
            elif ty == "golpe_final":
                th = b["start"] + b["pre"] + b["vdur"] + 0.15
                put(sfx, hit(), th, 0.6)
                i0, n = int(th * SR), int(2.6 * SR)
                amb[i0:i0 + n] *= np.linspace(0.1, 1, n)[: len(amb[i0:i0 + n])]
    mix = voice + amb + sfx
    mix[-3 * SR:] *= np.linspace(1, 0, 3 * SR)
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.9
    p = TMP / "mix.wav"
    with wave.open(str(p), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((np.stack([mix, mix], 1) * 32767).astype(np.int16).tobytes())
    return p


def miniatura():
    mt = H.get("miniatura", {})
    k = int(mt.get("bloque", 0))
    src = next((b["img"] for b in blocks if b["i"] >= k and b["tipo"] != "capitulo"), first)
    im = Image.open(src).convert("RGB").resize((1280, 720), Image.LANCZOS)
    a = np.asarray(im, np.float32)
    a = a * (1 - np.clip(1 - np.arange(720) / 320, 0, 1)[:, None, None] * 0.6)
    im = Image.fromarray(a.astype(np.uint8))
    d = ImageDraw.Draw(im)
    t1, t2 = mt.get("texto1", "NO MIRES"), mt.get("texto2", H["titulo"].upper())
    s1 = 150
    while d.textlength(t1, font=ImageFont.truetype(F_BOLD, s1)) > 1180:
        s1 -= 8
    s2 = 58
    while d.textlength(t2, font=ImageFont.truetype(F_BOLD, s2)) > 1180:
        s2 -= 4
    d.text((640, 110), t1, font=ImageFont.truetype(F_BOLD, s1), fill=(235, 40, 40), anchor="mm", stroke_width=7, stroke_fill=(0, 0, 0))
    d.text((640, 215), t2, font=ImageFont.truetype(F_BOLD, s2), fill=(245, 240, 230), anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0))
    im.save(D / "miniatura.jpg", quality=90)


if __name__ == "__main__":
    miniatura()
    wav = build_audio()
    print("audio listo", flush=True)
    with ThreadPoolExecutor(2) as ex:
        segs = list(ex.map(render, blocks))
    segs.append(render_end())
    lst = TMP / "concat.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in segs))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100", "-c:a", "aac", "-b:a", "160k",
                    "-shortest", "-movflags", "+faststart", str(OUT)], check=True)
    print("OK", OUT, f"{OUT.stat().st_size / 1e6:.0f} MB", flush=True)
