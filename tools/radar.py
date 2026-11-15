"""Short estilo Radar (lo más buscado de terror del día) con la marca Shorts Terror España.
Gráficos animados sincronizados con la voz (búsqueda que se escribe, titulares, sellos, contadores,
fechas, tarjetas) sobre fondos de cómic de terror con animación 2.5D, logo fijo y cierre con SÍGUEME.

Uso: python3 -I tools/radar.py radar/<ID> salida.mp4
Necesita: historia.json (formato "radar"), voces/completa.mp3, imgs/escena_N.jpg (+ _depth.png)."""
import json
import math
import re
import subprocess
import sys
import tempfile
import textwrap
import wave
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from anim25d import MOVES, Actor, Scene, blit, ease_out_back, prep_sprite, smooth  # noqa: E402

D = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
H = json.loads((D / "historia.json").read_text(encoding="utf-8"))
OW, OH, FPS, SR = 1080, 1920, 30, 44100
GF = "/usr/share/fonts/truetype/google-fonts/"
F_B, F_M, F_SERIF = GF + "Poppins-Bold.ttf", GF + "Poppins-Medium.ttf", GF + "Lora-Variable.ttf"
RED, BONE, INK, PANEL = (225, 38, 38), (242, 236, 226), (8, 6, 10), (16, 12, 16)
TMP = Path(tempfile.mkdtemp(prefix="radar_"))
rng = np.random.default_rng(7)


def font(p, s):
    return ImageFont.truetype(p, int(s))


def to_spr(im):
    """PIL RGBA -> float BGRA para blit()."""
    a = np.asarray(im.convert("RGBA")).astype(np.float32)
    return np.dstack([a[..., 2], a[..., 1], a[..., 0], a[..., 3]])


def seg(t, a, b):
    return min(1.0, max(0.0, (t - a) / max(1e-6, b - a)))


# ======================================================================  tiempos de la voz
VOZ = D / "voces" / "completa.mp3"
VDUR = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(VOZ)]))
TEXTO = H["texto"]


def speech_spans():
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(VOZ), "-af", "silencedetect=noise=-33dB:d=0.18", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    spans, cur = [], 0.0
    for s, e in zip(starts, ends + [VDUR] * (len(starts) - len(ends))):
        if s > cur + 0.05:
            spans.append((cur, s))
        cur = e
    if cur < VDUR - 0.05:
        spans.append((cur, VDUR))
    return spans or [(0.0, VDUR)]


SPANS = speech_spans()
SPEECH = sum(b - a for a, b in SPANS)


def speech_to_time(x):
    """x en [0,1] de tiempo HABLADO -> segundo real (saltando silencios)."""
    target, acc = x * SPEECH, 0.0
    for a, b in SPANS:
        if acc + (b - a) >= target:
            return a + (target - acc)
        acc += b - a
    return SPANS[-1][1]


# peso por carácter: las pausas largas (… . ?) ya están en los silencios
def at(phrase, default=None):
    k = TEXTO.lower().find(phrase.lower()) if phrase else -1
    if k < 0:
        return default
    return speech_to_time(k / max(1, len(TEXTO)))


# ======================================================================  piezas gráficas
def panel(w, h, border=RED, fill=PANEL, r=26):
    im = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((26, 30, w + 26, h + 30), r, fill=(0, 0, 0, 150))                 # sombra
    d.rounded_rectangle((14, 14, w + 14, h + 14), r, fill=fill + (238,), outline=border + (255,), width=6)
    return im, d


def fit_font(text, path, size, maxw):
    f = font(path, size)
    while f.getlength(text) > maxw and size > 20:
        size -= 4
        f = font(path, size)
    return f


def search_bar(txt, cursor):
    im, d = panel(900, 130, border=(70, 70, 80), fill=(236, 232, 226), r=65)
    d.ellipse((60, 52, 104, 96), outline=(90, 90, 100, 255), width=7)
    d.line((98, 92, 120, 114), fill=(90, 90, 100, 255), width=8)
    f = fit_font(txt or " ", F_M, 60, 700)
    d.text((150, 79), txt, font=f, fill=(25, 22, 28, 255), anchor="lm")
    if cursor:
        x = 150 + f.getlength(txt) + 6
        d.rectangle((x, 48, x + 5, 110), fill=RED + (255,))
    return to_spr(im)


def titular(txt):
    f = fit_font(txt, F_B, 150, 960)
    w = int(f.getlength(txt)) + 60
    im = Image.new("RGBA", (w, int(f.size * 1.45)), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((w / 2, f.size * 0.72), txt, font=f, fill=BONE + (255,), anchor="mm",
                            stroke_width=max(6, f.size // 14), stroke_fill=INK + (255,))
    return to_spr(im)


def sello(txt):
    f = fit_font(txt, F_B, 70, 760)
    w, h = int(f.getlength(txt)) + 90, int(f.size * 1.7)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((8, 8, w - 8, h - 8), outline=RED + (255,), width=10, fill=(20, 6, 8, 200))
    d.text((w / 2, h / 2), txt, font=f, fill=RED + (255,), anchor="mm")
    a = np.asarray(im).copy()                       # textura de tampón gastado
    m = rng.random(a.shape[:2]) < 0.10
    a[m, 3] = (a[m, 3] * 0.35).astype(np.uint8)
    return to_spr(Image.fromarray(a).rotate(-4, expand=True, resample=Image.BICUBIC))


def dato_card(valor, sufijo, etiqueta):
    im, d = panel(860, 330)
    f = fit_font(f"{valor}{sufijo}", F_B, 190, 780)
    d.text((444, 150), f"{valor}{sufijo}", font=f, fill=RED + (255,), anchor="mm", stroke_width=6, stroke_fill=INK + (255,))
    d.text((444, 285), etiqueta, font=fit_font(etiqueta, F_B, 46, 780), fill=BONE + (255,), anchor="mm")
    return to_spr(im)


def fecha_card(dia, mes, etiqueta, ring):
    im, d = panel(620, 560)
    d.rectangle((14, 14, 634, 130), fill=RED + (255,))
    d.text((324, 72), mes.upper(), font=fit_font(mes.upper(), F_B, 64, 560), fill=BONE + (255,), anchor="mm")
    d.text((324, 300), str(dia), font=font(F_B, 230), fill=BONE + (255,), anchor="mm", stroke_width=6, stroke_fill=INK + (255,))
    if ring > 0:
        d.arc((150, 160, 498, 450), -90, -90 + 360 * ring, fill=RED + (255,), width=16)
    d.text((324, 510), etiqueta, font=fit_font(etiqueta, F_B, 40, 560), fill=BONE + (255,), anchor="mm")
    return to_spr(im)


def tarjeta(titulo, texto):
    lines = textwrap.wrap(texto, 26)
    h = 120 + 64 * len(lines)
    im, d = panel(880, h)
    d.text((60, 78), titulo.upper(), font=fit_font(titulo.upper(), F_B, 62, 800), fill=RED + (255,), anchor="lm")
    for i, l in enumerate(lines):
        d.text((60, 150 + 64 * i), l, font=font(F_M, 50), fill=BONE + (255,), anchor="lm")
    return to_spr(im)


# logo de la marca (fijo arriba y grande en el cierre)
def logo(scale=1.0):
    s = scale
    f1, f2 = font(F_B, 64 * s), font(F_SERIF, 40 * s)
    w = int(max(f1.getlength("SHORTS TERROR"), f2.getlength("E S P A Ñ A")) + 150 * s)
    h = int(140 * s)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy, r = int(62 * s), int(70 * s), int(50 * s)                       # ojo
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=RED + (255,), outline=INK + (255,), width=int(5 * s))
    d.ellipse((cx - r * 0.75, cy - r * 0.42, cx + r * 0.75, cy + r * 0.42), fill=BONE + (255,))
    d.ellipse((cx - r * 0.28, cy - r * 0.28, cx + r * 0.28, cy + r * 0.28), fill=INK + (255,))
    d.text((int(125 * s), int(48 * s)), "SHORTS TERROR", font=f1, fill=BONE + (255,), anchor="lm", stroke_width=int(4 * s), stroke_fill=INK + (255,))
    d.text((int(127 * s), int(108 * s)), "E S P A Ñ A", font=f2, fill=RED + (255,), anchor="lm", stroke_width=int(2 * s), stroke_fill=INK + (255,))
    return to_spr(im)


def boton():
    im = Image.new("RGBA", (640, 190), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((20, 26, 630, 186), 80, fill=(0, 0, 0, 160))
    d.rounded_rectangle((8, 8, 620, 168), 80, fill=RED + (255,), outline=BONE + (255,), width=6)
    d.text((314, 88), "SÍGUEME", font=font(F_B, 96), fill=(255, 255, 255, 255), anchor="mm")
    return to_spr(im)


def cursor():
    im = Image.new("RGBA", (120, 150), (0, 0, 0, 0))
    ImageDraw.Draw(im).polygon([(20, 8), (20, 100), (42, 82), (56, 122), (76, 114), (62, 76), (92, 76)],
                               fill=(250, 250, 250, 255), outline=(20, 20, 30, 255))
    return to_spr(im)


LOGO_S, LOGO_L, BOTON, CURSOR = logo(0.8), logo(1.25), boton(), cursor()


# ======================================================================  escenas y elementos
class Elem:
    def __init__(self, spec, t_scene0):
        self.s = spec
        self.tipo = spec["tipo"]
        self.t0 = at(spec.get("en", ""), t_scene0 + 0.2)
        self.y = float(spec.get("y", {"busqueda": 0.25, "titular": 0.38, "sello": 0.52, "dato": 0.45,
                                       "fecha": 0.42, "tarjeta": 0.47}.get(self.tipo, 0.45)))
        if self.tipo == "titular":
            self.spr = titular(spec["texto"].upper())
        elif self.tipo == "sello":
            self.spr = sello(spec["texto"].upper())
        elif self.tipo == "tarjeta":
            self.spr = tarjeta(spec.get("titulo", ""), spec.get("texto", ""))

    def draw(self, fr, t):
        tt = t - self.t0
        if tt < 0:
            return []
        shakes = []
        cx, cy = OW / 2, self.y * OH
        if self.tipo == "busqueda":
            txt = self.s["texto"]
            n = int(min(len(txt), max(0, tt - 0.15) / 0.07))
            spr = search_bar(txt[:n], n < len(txt) or int(t * 2.5) % 2 == 0)
            k = ease_out_back(tt / 0.4)
            blit(fr, spr, cx, cy + spr.shape[0] / 2, 0.7 + 0.3 * k, 0.7 + 0.3 * k, 0, min(1, tt / 0.15))
        elif self.tipo == "dato":
            v = float(self.s["valor"])
            cur = v * smooth(tt / 1.0)
            txt = f"{cur:.0f}" if float(v).is_integer() else f"{cur:.1f}".replace(".", ",")
            spr = dato_card(txt, self.s.get("sufijo", ""), self.s.get("etiqueta", "").upper())
            k = ease_out_back(tt / 0.45)
            blit(fr, spr, cx, cy + spr.shape[0] / 2, 0.6 + 0.4 * k, 0.6 + 0.4 * k, 0, min(1, tt / 0.15))
            if 1.0 <= tt < 1.05:
                shakes.append(0.5)
        elif self.tipo == "fecha":
            spr = fecha_card(self.s["dia"], self.s.get("mes", ""), self.s.get("etiqueta", "").upper(), smooth((tt - 0.5) / 0.6))
            k = ease_out_back(tt / 0.45)
            blit(fr, spr, cx, cy + spr.shape[0] / 2, 0.6 + 0.4 * k, 0.6 + 0.4 * k, -2, min(1, tt / 0.15))
        elif self.tipo == "sello":
            k = ease_out_back(tt / 0.25)
            s = 2.0 - 1.0 * k
            blit(fr, self.spr, cx, cy + self.spr.shape[0] / 2, s, s, 0, min(1, tt / 0.08))
            if tt < 0.05:
                shakes.append(0.8)
        elif self.tipo == "titular":
            k = ease_out_back(tt / 0.35)
            s = 0.5 + 0.5 * k
            blit(fr, self.spr, cx, cy + self.spr.shape[0] / 2, s, s, 0, min(1, tt / 0.12))
            if tt < 0.05:
                shakes.append(0.6)
        elif self.tipo == "tarjeta":
            k = ease_out_back(tt / 0.45)
            off = (1 - k) * (OW * 0.7) * (1 if int(self.t0 * 10) % 2 else -1)
            blit(fr, self.spr, cx + off, cy + self.spr.shape[0] / 2, 1, 1, 0, min(1, tt / 0.15))
        return shakes


escenas = H["escenas"]
for i, e in enumerate(escenas):
    e["t0"] = 0.0 if i == 0 else at(e.get("desde", ""), None)
    if e["t0"] is None:
        sys.exit(f"No encuentro la frase de inicio de la escena {i}: {e.get('desde')}")
T_CIERRE = at(H.get("cierre_desde", "Si quieres"), VDUR - 4.0)
TOTAL = VDUR + 1.6
for i, e in enumerate(escenas):
    e["t1"] = escenas[i + 1]["t0"] if i + 1 < len(escenas) else T_CIERRE
print(f"Duración {TOTAL:.1f} s · escenas {[round(e['t0'], 1) for e in escenas]} · cierre {T_CIERRE:.1f}", flush=True)


def build_scene(i, e):
    src = D / "imgs" / f"escena_{i}.jpg"
    if not src.exists():
        src = next((D / "imgs" / f"escena_{j}.jpg" for j in range(i, -1, -1) if (D / "imgs" / f"escena_{j}.jpg").exists()), None)
    pre = TMP / f"bg{i}.jpg"
    im = Image.open(src).convert("RGB")
    w, h = im.size
    s = max(1350 / w, 2400 / h)
    im = im.resize((int(w * s + 1), int(h * s + 1)), Image.LANCZOS)
    w, h = im.size
    im = im.crop(((w - 1350) // 2, (h - 2400) // 2, (w - 1350) // 2 + 1350, (h - 2400) // 2 + 2400))
    a = np.asarray(im, np.float32) / 255.0
    g = a.mean(2, keepdims=True)
    a = np.clip(((g + (a - g) * 0.9) * np.array([0.96, 0.98, 1.03]) - 0.5) * 1.06 + 0.49, 0, 1)
    Image.fromarray((a * 255).astype(np.uint8)).save(pre, quality=94)
    dsrc = src.with_name(src.stem + "_depth.png")
    dpre = None
    if dsrc.exists():
        dpre = TMP / f"bg{i}_d.png"
        Image.open(dsrc).convert("L").resize(Image.open(src).size).resize((int(Image.open(src).size[0] * s + 1), int(Image.open(src).size[1] * s + 1))) \
            .crop(((w - 1350) // 2, (h - 2400) // 2, (w - 1350) // 2 + 1350, (h - 2400) // 2 + 2400)).save(dpre)
    sc = Scene(pre, dpre, OW, OH, e.get("ambiente", "interior"), seed=i)
    actors = []
    for spec in e.get("personajes", []):
        p = D / "imgs" / f"personaje_{spec.get('quien', '')}.png"
        if p.exists():
            spr = prep_sprite(p, float(spec.get("alto", 0.42)) * OH, spec.get("silueta", False), spec.get("espejo", False))
            if spr is not None:
                t0 = at(spec.get("en", ""), e["t0"] + 0.3)
                actors.append((Actor(spr, dict(spec, t0=0.0, y=float(spec.get("y", 0.97))), OW, OH, e["t1"] - t0), t0))
    return sc, [Elem(x, e["t0"]) for x in e.get("elementos", [])], actors


SCENES = [build_scene(i, e) for i, e in enumerate(escenas)]
# degradado para que se lean los gráficos (arriba y abajo más oscuro)
yy = np.linspace(0, 1, OH, dtype=np.float32)[:, None]
SHADE = (0.68 + 0.32 * (1 - np.clip(np.abs(yy - 0.62) / 0.62, 0, 1)) ** 0.7)[..., None]
CLOSE_BG = None


def frame_at(t):
    global CLOSE_BG
    shakes = []
    if t < T_CIERRE:
        i = max(k for k, e in enumerate(escenas) if e["t0"] <= t)
        e = escenas[i]
        sc, elems, actors = SCENES[i]
        p = (t - e["t0"]) / max(0.5, e["t1"] - e["t0"])
        fr = sc.frame(p, t, MOVES[i % len(MOVES)], focus=(0.5, 0.45)).astype(np.float32)
        fr *= SHADE
        for a, t0 in actors:
            if t >= t0:
                a.draw(fr, t - t0)
        for el in elems:
            shakes += el.draw(fr, t)
        # transición: destello rojo al cambiar de escena
        if i > 0 and t - e["t0"] < 0.18:
            fr = fr * 0.6 + np.array([30, 30, 200], np.float32) * (0.4 * (1 - (t - e["t0"]) / 0.18))
        blit(fr, LOGO_S, OW / 2, 70 + LOGO_S.shape[0], 1, 1, 0, 0.95)       # logo fijo arriba
    else:
        tt = t - T_CIERRE
        if CLOSE_BG is None:
            sc0 = SCENES[-1][0]
            CLOSE_BG = sc0
        fr = CLOSE_BG.frame(1.0, t, "dolly_in").astype(np.float32) * 0.28
        k = ease_out_back(tt / 0.6)
        blit(fr, LOGO_L, OW / 2, OH * 0.40, 0.6 + 0.4 * k, 0.6 + 0.4 * k, 0, min(1, tt / 0.2))
        tb = at("sígueme", T_CIERRE + 1.2) - T_CIERRE
        kb = ease_out_back((tt - 0.4) / 0.5)
        press = 1 - 0.07 * math.exp(-((tt - tb - 0.15) / 0.12) ** 2)
        pulse = 1 + 0.025 * math.sin(t * 5) if tt > 1.0 else 1
        if tt > 0.4:
            blit(fr, BOTON, OW / 2, OH * 0.58, (0.6 + 0.4 * kb) * press * pulse, (0.6 + 0.4 * kb) * press * pulse, 0, min(1, (tt - 0.4) / 0.2))
        cu = smooth((tt - (tb - 0.9)) / 0.8)
        if cu > 0:
            blit(fr, CURSOR, OW * (0.78 - 0.14 * cu), OH * (0.66 - 0.05 * cu) + (8 if abs(tt - tb - 0.15) < 0.12 else 0), 1, 1, 0, min(1, cu * 3))
    fr = np.clip(fr, 0, 255).astype(np.uint8)
    sh = sum(shakes) * 18
    if sh > 0:
        fr = cv2.warpAffine(fr, np.float32([[1, 0, sh * math.sin(t * 90)], [0, 1, sh * math.cos(t * 70)]]), (OW, OH), borderMode=cv2.BORDER_REFLECT)
    return fr


# ======================================================================  audio: voz + ambiente + efectos
def build_audio():
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(VOZ), "-af", "highpass=f=60", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"])
    v = np.frombuffer(raw, np.float32)
    N = int((TOTAL + 0.3) * SR)
    mix = np.zeros(N, np.float32)
    mix[:len(v)] += v[:N] / (np.abs(v).max() + 1e-9) * 0.85
    x = np.arange(N, dtype=np.float32) / SR
    spec = np.fft.rfft(rng.standard_normal(N).astype(np.float32))
    fr = np.fft.rfftfreq(N, 1 / SR)
    room = np.fft.irfft(spec * ((fr > 20) & (fr < 700)) / np.sqrt(np.maximum(fr, 20) / 60), n=N).astype(np.float32)
    room /= np.abs(room).max() + 1e-9
    drone = 0.05 * np.sin(2 * np.pi * 55 * x) + 0.03 * np.sin(2 * np.pi * 110 * x) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.1 * x)) \
        + 0.012 * np.sin(2 * np.pi * 207.65 * x) + 0.06 * room
    mix += drone * 0.9

    def put(sig, t0, g):
        i = int(t0 * SR)
        if 0 <= i < N:
            n = min(len(sig), N - i)
            mix[i:i + n] += sig[:n] * g

    def whoosh():
        tt = np.arange(int(0.35 * SR)) / SR
        n = rng.standard_normal(len(tt)).astype(np.float32)
        n = np.convolve(n, np.ones(30) / 30, mode="same")
        return n * np.sin(np.pi * tt / 0.35) ** 2 * 3

    def hit():
        tt = np.arange(int(1.2 * SR)) / SR
        ph = 2 * np.pi * np.cumsum(70 * np.exp(-tt * 1.2)) / SR
        return ((np.sin(ph) + 0.5 * np.sin(2 * ph)) * np.exp(-tt * 3) + rng.standard_normal(len(tt)) * np.exp(-tt * 25) * 0.4) * (1 - np.exp(-tt * 800))

    def tick():
        tt = np.arange(int(0.05 * SR)) / SR
        return np.sin(2 * np.pi * 1800 * tt) * np.exp(-tt * 120)

    for i, e in enumerate(escenas):
        if i > 0:
            put(whoosh(), e["t0"] - 0.15, 0.25)
        for el in SCENES[i][1]:
            if el.tipo in ("sello", "titular"):
                put(hit(), el.t0, 0.35)
            elif el.tipo == "busqueda":
                for k in range(len(el.s["texto"])):
                    put(tick(), el.t0 + 0.15 + 0.07 * k, 0.06)
            else:
                put(whoosh(), el.t0 - 0.1, 0.18)
    put(hit(), T_CIERRE, 0.3)
    mix[-int(1.2 * SR):] *= np.linspace(1, 0, int(1.2 * SR))
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.9
    p = TMP / "mix.wav"
    with wave.open(str(p), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((np.stack([mix, mix], 1) * 32767).astype(np.int16).tobytes())
    return p


# ======================================================================  subtítulos (frases cortas)
def subs_filter():
    parts = []
    sents = [s.strip() for s in re.findall(r"[^.?!…]+[.?!…]*", TEXTO) if s.strip()]
    pos = 0
    chunks = []
    for s in sents:
        k = TEXTO.find(s, pos)
        words, cur = s.split(), []
        groups = []
        for w_ in words:
            if cur and len(" ".join(cur + [w_])) > 18:
                groups.append(" ".join(cur))
                cur = []
            cur.append(w_)
        if cur:
            groups.append(" ".join(cur))
        for c in groups:
            kk = TEXTO.find(c, k)
            chunks.append((c, kk))
            k = kk + len(c)
        pos = k
    for n, (c, k) in enumerate(chunks):
        a = speech_to_time(k / len(TEXTO))
        b = speech_to_time(chunks[n + 1][1] / len(TEXTO)) if n + 1 < len(chunks) else VDUR
        if a >= T_CIERRE - 0.05:
            break
        fp = TMP / f"s{n:03d}.txt"
        fp.write_text(c.upper(), encoding="utf-8")
        parts.append(f"drawtext=fontfile={F_B}:textfile={str(fp).replace(':', chr(92) + ':')}:expansion=none:fontsize=64:"
                     f"fontcolor=0xF2ECE2:borderw=5:bordercolor=black:x=(w-text_w)/2:y=h*0.80:enable='between(t,{a:.2f},{min(b, T_CIERRE):.2f})'")
    return ",".join(parts) if parts else "null"


if __name__ == "__main__":
    wav = build_audio()
    NF = int(TOTAL * FPS)
    vf = f"[0:v]{subs_filter()},noise=alls=5:allf=t+u,fade=t=in:st=0:d=0.3,fade=t=out:st={TOTAL - 0.8:.2f}:d=0.8,format=yuv420p[v]"
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OW}x{OH}",
           "-r", str(FPS), "-i", "-", "-i", str(wav), "-filter_complex", vf, "-map", "[v]", "-map", "1:a",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=9", "-c:a", "aac", "-b:a", "192k", "-t", f"{TOTAL:.2f}",
           "-movflags", "+faststart", str(OUT)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(NF):
        proc.stdin.write(frame_at(f / FPS).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg falló")
    print("OK", OUT, f"{OUT.stat().st_size / 1e6:.1f} MB", flush=True)
