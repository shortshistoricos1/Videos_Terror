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

    def frame(self, p, t, move, zbase=1.12, focus=(0.5, 0.45)):
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
        out = np.clip(out, 0, 255).astype(np.uint8)
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
