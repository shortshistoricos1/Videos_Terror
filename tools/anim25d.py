"""Animación 2.5D: cámara que se mueve DENTRO de la imagen usando un mapa de profundidad
(paralaje), más niebla en movimiento, partículas, luces que parpadean, relámpagos y cámara en mano."""
import math

import cv2
import numpy as np

MOVES = ["dolly_in", "truck_right", "dolly_out", "truck_left", "crane_up"]


def smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def synthetic_depth(h, w):
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    x = np.linspace(-1, 1, w, dtype=np.float32)[None, :]
    return np.clip(0.25 + 0.65 * y ** 1.4 + 0.1 * (1 - np.abs(x)), 0, 1)


class Scene:
    def __init__(self, img_path, depth_path, OW, OH, ambiente="interior", seed=0):
        self.img = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
        self.BH, self.BW = self.img.shape[:2]
        if depth_path is not None and depth_path.exists():
            d = cv2.imread(str(depth_path), cv2.IMREAD_GRAYSCALE)
            d = cv2.resize(d, (self.BW, self.BH), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255.0
            d = cv2.GaussianBlur(d, (0, 0), 6)
            lo, hi = np.percentile(d, 2), np.percentile(d, 98)
            d = np.clip((d - lo) / max(1e-3, hi - lo), 0, 1)
        else:
            d = synthetic_depth(self.BH, self.BW)
        self.depth = d                       # 1 = cerca, 0 = lejos
        self.dmean = float(np.median(d))
        g = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        self.light = cv2.GaussianBlur(np.clip((g - 0.62) / 0.3, 0, 1), (0, 0), 18)
        self.OW, self.OH = OW, OH
        self.amb = ambiente
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        # rejilla de salida a media resolución (los mapas son suaves)
        hw, hh = OW // 2, OH // 2
        u, v = np.meshgrid(np.linspace(-OW / 2, OW / 2, hw, dtype=np.float32),
                           np.linspace(-OH / 2, OH / 2, hh, dtype=np.float32))
        self.U, self.V = u, v
        # niebla: textura de ruido el doble de ancha para desplazarla
        small = self.rng.random((10, 18)).astype(np.float32)
        fog = cv2.resize(small, (OW * 2, OH), interpolation=cv2.INTER_CUBIC)
        small2 = self.rng.random((24, 44)).astype(np.float32)
        fog = 0.65 * fog + 0.35 * cv2.resize(small2, (OW * 2, OH), interpolation=cv2.INTER_CUBIC)
        self.fog = np.clip(fog, 0, 1)
        outdoor = ambiente in ("viento", "nieve", "lluvia")
        self.fog_k = 0.20 if outdoor else 0.08
        self.fog_col = np.array([175, 160, 150], np.float32)  # BGR, gris azulado
        # partículas
        n = {"nieve": 380, "lluvia": 420}.get(ambiente, 70)
        self.px = self.rng.uniform(0, OW, n)
        self.py = self.rng.uniform(0, OH, n)
        self.pz = self.rng.uniform(0.2, 1.0, n)
        self.pphase = self.rng.uniform(0, 2 * np.pi, n)
        self.flash_times = sorted(self.rng.uniform(1.0, 60.0, 4)) if ambiente == "lluvia" else []

    actors, impactos, golpes = (), (), ()

    def frame(self, p, t, move, zbase=1.12, focus=(0.5, 0.45), tl=None):
        OW, OH, BW, BH = self.OW, self.OH, self.BW, self.BH
        e = smooth(p)
        z = zbase
        cx, cy = focus
        par_x = par_y = dolly = 0.0
        if move == "dolly_in":
            z = zbase * (1 + 0.07 * e)
            dolly = 0.10 * e
        elif move == "dolly_out":
            z = zbase * (1.07 - 0.07 * e)
            dolly = 0.10 * (1 - e)
        elif move == "truck_right":
            par_x = 0.030 * (e - 0.5) * 2
            cx += 0.015 * (e - 0.5)
        elif move == "truck_left":
            par_x = -0.030 * (e - 0.5) * 2
            cx -= 0.015 * (e - 0.5)
            par_y = 0.006 * (e - 0.5)
        elif move == "crane_up":
            par_y = -0.022 * (e - 0.5) * 2
            dolly = 0.04 * e
        # cámara en mano muy suave
        cx += 0.0012 * math.sin(t * 1.3) + 0.0007 * math.sin(t * 3.1 + self.seed)
        cy += 0.0012 * math.sin(t * 1.1 + 1) + 0.0007 * math.sin(t * 2.7)
        S = (OW / BW) * z
        sx = cx * BW + self.U / S
        sy = cy * BH + self.V / S
        d = cv2.remap(self.depth, sx, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        dd = d - self.dmean
        mx = sx + par_x * BW * dd - (sx - cx * BW) * dolly * dd
        my = sy + par_y * BH * dd - (sy - cy * BH) * dolly * dd
        mx = cv2.resize(mx, (OW, OH), interpolation=cv2.INTER_LINEAR)
        my = cv2.resize(my, (OW, OH), interpolation=cv2.INTER_LINEAR)
        out = cv2.remap(self.img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32)
        dfull = cv2.remap(self.depth, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        light = cv2.remap(self.light, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        # luces que parpadean
        if self.amb == "fuego":
            f = 0.10 * math.sin(t * 11.0) * math.sin(t * 3.7 + 1) + 0.06 * math.sin(t * 23.0)
        else:
            f = 0.05 * math.sin(t * 7.3) * math.sin(t * 0.9 + self.seed)
            if (t * 0.37 + self.seed * 0.13) % 1.0 < 0.035:
                f -= 0.45
        out *= (1 + f * light)[..., None]
        # niebla en movimiento (más en el fondo)
        off = int((t * 18) % OW)
        fogw = self.fog[:, off:off + OW]
        a = (self.fog_k * fogw * (1 - dfull) ** 1.3)[..., None]
        out = out * (1 - a) + self.fog_col * a
        # relámpagos
        for ft in self.flash_times:
            if 0 <= t - ft < 0.35:
                out += 160 * math.exp(-(t - ft) * 12) * (0.4 + 0.6 * (1 - dfull[..., None]))
        tl = t if tl is None else tl
        for a in self.actors:
            a.draw(out, tl)
        for ft, amp in self.golpes:                       # fogonazo en los golpes
            if 0 <= tl - ft < 0.3:
                out += 70 * amp * math.exp(-(tl - ft) * 14)
        for im in self.impactos:
            im.draw(out, tl)
        out = np.clip(out, 0, 255).astype(np.uint8)
        sh = sum(amp * 22 * math.exp(-(tl - ft) * 9) for ft, amp in self.golpes if 0 <= tl - ft < 0.6)
        if sh > 0.5:                                       # sacudida de cámara
            dx, dy = int(sh * math.sin(tl * 113)), int(sh * math.cos(tl * 97))
            out = cv2.warpAffine(out, np.float32([[1, 0, dx], [0, 1, dy]]), (OW, OH), borderMode=cv2.BORDER_REFLECT)
        # partículas
        ov = out.copy()
        if self.amb == "nieve":
            x = (self.px + 25 * np.sin(t * 0.8 + self.pphase) + t * 8) % OW
            y = (self.py + t * (40 + 110 * self.pz)) % OH
            for xi, yi, zi in zip(x, y, self.pz):
                cv2.circle(ov, (int(xi), int(yi)), max(1, int(1 + 3 * zi)), (245, 240, 235), -1, cv2.LINE_AA)
            out = cv2.addWeighted(ov, 0.75, out, 0.25, 0)
        elif self.amb == "lluvia":
            x = (self.px - t * 120) % OW
            y = (self.py + t * (700 + 600 * self.pz)) % OH
            for xi, yi, zi in zip(x, y, self.pz):
                L = int(14 + 26 * zi)
                cv2.line(ov, (int(xi), int(yi)), (int(xi - L * 0.18), int(yi + L)), (215, 205, 195), 1, cv2.LINE_AA)
            out = cv2.addWeighted(ov, 0.35, out, 0.65, 0)
        else:  # polvo flotando
            x = (self.px + 18 * np.sin(t * 0.35 + self.pphase) + t * 6) % OW
            y = (self.py - t * (6 + 10 * self.pz) + 10 * np.cos(t * 0.5 + self.pphase)) % OH
            for xi, yi, zi in zip(x, y, self.pz):
                cv2.circle(ov, (int(xi), int(yi)), max(1, int(1 + 2.5 * zi)), (200, 225, 240), -1, cv2.LINE_AA)
            out = cv2.addWeighted(ov, 0.30, out, 0.70, 0)
        return out


# ======================================================================  personajes animados
def ease_out_back(x):
    x = min(1.0, max(0.0, x))
    c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def prep_sprite(path, target_h, silueta=False, espejo=False):
    """Carga un personaje recortado (RGBA), lo adapta al tono de terror y lo escala a target_h píxeles."""
    im = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if im is None or im.shape[2] != 4:
        return None
    s = target_h / im.shape[0]
    im = cv2.resize(im, (max(2, int(im.shape[1] * s)), int(target_h)), interpolation=cv2.INTER_AREA)
    if espejo:
        im = im[:, ::-1]
    rgb = im[..., :3].astype(np.float32)
    a = im[..., 3:].astype(np.float32) / 255.0
    g = rgb.mean(2, keepdims=True)
    rgb = g + (rgb - g) * 0.8
    rgb = rgb * np.array([1.05, 0.97, 0.9], np.float32) * 0.82      # BGR: frío y algo más oscuro
    if silueta:
        rgb = rgb * 0.06
    # borde de luz tenue (rim light) para separarlo del fondo
    edge = cv2.GaussianBlur(a, (0, 0), 3)[..., None] if a.ndim == 2 else cv2.GaussianBlur(a[..., 0], (0, 0), 3)[..., None]
    rim = np.clip(edge - a, 0, 1) * 0 + np.clip(a - cv2.erode(a, np.ones((5, 5), np.uint8))[..., None] if a.ndim == 3 else 0, 0, 1)
    rgb = np.clip(rgb + rim * np.array([60, 40, 30], np.float32), 0, 255)
    return np.dstack([rgb, a[..., 0] * 255]).astype(np.float32)


def blit(frame, spr, cx, by, sx=1.0, sy=1.0, rot=0.0, alpha=1.0):
    """Pega spr (float BGRA) con el pie en (cx, by), escalado y rotado. frame: float32 BGR."""
    if alpha <= 0.01 or spr is None:
        return
    h, w = spr.shape[:2]
    ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    # matriz: sprite -> frame (ancla en el centro inferior)
    M = np.array([[sx * ca, -sy * sa, 0], [sx * sa, sy * ca, 0]], np.float32)
    M[:, 2] = np.array([cx, by], np.float32) - M[:, :2] @ np.array([w / 2, h], np.float32)
    pts = np.array([[0, 0, 1], [w, 0, 1], [0, h, 1], [w, h, 1]], np.float32) @ M.T
    x0, y0 = np.floor(pts.min(0)).astype(int)
    x1, y1 = np.ceil(pts.max(0)).astype(int)
    H, W = frame.shape[:2]
    X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if X1 <= X0 or Y1 <= Y0:
        return
    M2 = M.copy()
    M2[:, 2] -= np.array([X0, Y0], np.float32)
    warped = cv2.warpAffine(spr, M2, (X1 - X0, Y1 - Y0), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    a = (warped[..., 3:] / 255.0) * alpha
    roi = frame[Y0:Y1, X0:X1]
    roi[:] = roi * (1 - a) + warped[..., :3] * a


def shadow(frame, cx, by, wid, alpha):
    if alpha <= 0.01:
        return
    H, W = frame.shape[:2]
    rx, ry = int(wid * 0.55), max(4, int(wid * 0.09))
    x0, y0, x1, y1 = max(0, int(cx - rx * 1.6)), max(0, int(by - ry * 3)), min(W, int(cx + rx * 1.6)), min(H, int(by + ry * 3))
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    m = np.exp(-(((xx - cx) / rx) ** 2 + ((yy - by) / ry) ** 2) * 1.5) * 0.55 * alpha
    frame[y0:y1, x0:x1] *= (1 - m)[..., None]


class Actor:
    """Un personaje con una animación sincronizada. Tiempos en segundos LOCALES del bloque."""

    def __init__(self, spr, spec, OW, OH, dur):
        self.spr, self.OW, self.OH, self.dur = spr, OW, OH, dur
        self.anim = spec.get("anim", "respira")
        self.x, self.y = float(spec.get("x", 0.5)), float(spec.get("y", 0.97))
        self.t0 = float(spec.get("t0", 0.0))
        self.desde = spec.get("desde", "izq")
        self.seed = hash(str(spec)) % 1000 / 100.0

    def draw(self, frame, t):
        OW, OH = self.OW, self.OH
        w = self.spr.shape[1]
        tt = t - self.t0
        cx, by = self.x * OW, self.y * OH
        sx = sy = 1.0
        rot, alpha = 0.0, 1.0
        breath = 1 + 0.012 * math.sin(2 * math.pi * 0.28 * t + self.seed)
        sway = 0.7 * math.sin(2 * math.pi * 0.17 * t + self.seed)
        a = self.anim
        if a == "camina":
            dirn = 1 if self.desde == "izq" else -1
            start = -0.25 if dirn == 1 else 1.25
            T = max(1.0, self.dur - self.t0 - 0.3)
            k = smooth(max(0.0, tt) / T)
            cx = (start + (self.x - start) * k) * OW
            ph = max(0.0, tt) * 2 * math.pi * 1.7
            if k < 0.999:
                by -= abs(math.sin(ph)) * 0.014 * OH
                rot = 1.6 * math.sin(ph)
                sy = 1 + 0.012 * math.cos(2 * ph)
            else:
                sy = breath
            if tt < 0:
                alpha = 0
        elif a == "asoma":
            off = 0.22 if self.desde == "der" else -0.22
            k = ease_out_back(max(0.0, tt) / 1.1)
            cx = (self.x + off * (1 - k)) * OW
            rot = sway - 4 * (1 - min(1, max(0, tt) / 1.1)) * (1 if off > 0 else -1)
            sy = breath
            alpha = 1 if tt > 0 else 0
        elif a == "se_acerca":
            k = smooth(max(0.0, tt) / max(1.0, self.dur - self.t0))
            sx = sy = 0.55 + 0.75 * k
            by = (self.y + 0.05 * k) * OH
            alpha = min(1.0, max(0.0, tt) / 0.6)
            rot = sway * 0.5
        elif a == "aparece":
            if tt < 0:
                alpha = 0
            elif tt < 0.9:
                alpha = (0.15 + 0.85 * (tt / 0.9)) * (0.3 if int(tt * 18) % 3 == 0 else 1.0)
            sy = breath
        elif a == "tiembla":
            j = 0.004 * OW
            cx += j * math.sin(t * 61 + self.seed) + j * 0.6 * math.sin(t * 37)
            rot = 0.8 * math.sin(t * 47)
            sy = breath
        elif a == "gira":
            k = smooth((tt - 0.0) / 0.5) if tt > 0 else 0
            sx = math.cos(math.pi * k)
            sx = sx if abs(sx) > 0.04 else 0.04 * (1 if sx >= 0 else -1)
            sy = breath
        else:  # respira
            sy = breath
            rot = sway * 0.6
        sh_a = alpha * 0.9
        shadow(frame, cx, by, w * abs(sx), sh_a)
        blit(frame, self.spr, cx, by, sx, sy * 1.0, rot, alpha)


class Impacto:
    """Palabra clave que salta en grande cuando la dice el narrador."""

    def __init__(self, texto, t0, OW, OH, font_path, color=(40, 40, 230)):
        from PIL import Image, ImageDraw, ImageFont
        size = int(OH * (0.11 if OW > OH else 0.075))
        f = ImageFont.truetype(font_path, size)
        tw = int(f.getlength(texto)) + 60
        while tw > OW * 0.9 and size > 30:
            size -= 6
            f = ImageFont.truetype(font_path, size)
            tw = int(f.getlength(texto)) + 60
        im = Image.new("RGBA", (tw, int(size * 1.5)), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((tw / 2, size * 0.75), texto, font=f, fill=(230, 40, 40, 255), anchor="mm",
                                stroke_width=max(4, size // 14), stroke_fill=(0, 0, 0, 255))
        a = np.asarray(im).astype(np.float32)
        self.spr = np.dstack([a[..., 2], a[..., 1], a[..., 0], a[..., 3]])
        self.t0, self.OW, self.OH = t0, OW, OH

    def draw(self, frame, t):
        tt = t - self.t0
        if tt < 0 or tt > 1.7:
            return
        k = ease_out_back(tt / 0.28)
        s = 1.9 - 0.9 * k
        alpha = min(1.0, tt / 0.08) * (1 - smooth((tt - 1.35) / 0.35))
        blit(frame, self.spr, self.OW / 2, self.OH * 0.40 + self.spr.shape[0] / 2, s, s, -3, alpha)
