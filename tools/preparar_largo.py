"""Se ejecuta en GitHub Actions: genera voces (Edge TTS) e imágenes (Pollinations) para cada
largos/<ID>/historia.json que aún no las tenga."""
import asyncio
import base64
import io
import json
import os
import time
import urllib.parse
from pathlib import Path

import edge_tts
import requests
from PIL import Image

ESTILO = (", creepy comic book illustration, graphic novel art, thick black ink outlines, cel shading, "
          "flat muted desaturated colors, eerie night atmosphere, dramatic shadows, detailed background, "
          "horror comic panel, clean artwork without any speech bubbles, captions, letters or text, no watermark")


async def voces(d, h):
    v = h.get("voz", {})
    voz, rate, pitch = v.get("voz", "es-ES-AlvaroNeural"), v.get("rate", "-8%"), v.get("pitch", "-5Hz")
    (d / "voces").mkdir(exist_ok=True)
    sem = asyncio.Semaphore(5)

    async def una(i, texto):
        dst = d / "voces" / f"bloque_{i:03d}.mp3"
        if dst.exists() and dst.stat().st_size > 2000:
            return
        async with sem:
            for k in range(5):
                try:
                    await edge_tts.Communicate(texto, voz, rate=rate, pitch=pitch).save(str(dst))
                    print("voz ok", dst.name, flush=True)
                    return
                except Exception as e:
                    print("voz error", dst.name, e, flush=True)
                    await asyncio.sleep(3 + 3 * k)
        raise RuntimeError(f"sin voz {dst}")

    await asyncio.gather(*(una(i, b["texto"]) for i, b in enumerate(h["bloques"])))


CF_ID, CF_TOKEN = os.environ.get("CF_ACCOUNT_ID", "").strip(), os.environ.get("CF_API_TOKEN", "").strip()
LOG = []


def log(*a):
    line = " ".join(str(x) for x in a)
    print(line, flush=True)
    LOG.append(line)


CF_AGOTADO = False


def cloudflare(prompt, seed, vertical):
    """FLUX.1 schnell en Cloudflare Workers AI (gratis hasta 10.000 neuronas/día). Devuelve bytes JPG o None.
    Si se acaba la cuota diaria gratuita, pasa solo a Pollinations (gratis) hasta que termine la ejecución."""
    global CF_AGOTADO
    if CF_AGOTADO:
        return pollinations(prompt, seed, vertical)
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ID}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    r = requests.post(url, headers={"Authorization": f"Bearer {CF_TOKEN}"},
                      json={"prompt": prompt[:2000], "steps": 4}, timeout=120)
    if r.status_code != 200:
        log("cloudflare", r.status_code, r.text[:200])
        if r.status_code == 429 or "daily free allocation" in r.text or "4006" in r.text:
            CF_AGOTADO = True
            log("Cuota diaria de Cloudflare agotada: sigo con Pollinations")
            return pollinations(prompt, seed, vertical)
        return None
    im = Image.open(io.BytesIO(base64.b64decode(r.json()["result"]["image"]))).convert("RGB")
    w, h = im.size  # 1024x1024: recorte al formato del vídeo
    if vertical:
        cw = int(h * 9 / 16)
        im = im.crop(((w - cw) // 2, 0, (w - cw) // 2 + cw, h))
    else:
        ch = int(w * 9 / 16)
        im = im.crop((0, (h - ch) // 2, w, (h - ch) // 2 + ch))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=95)
    return buf.getvalue()


def pollinations(prompt, seed, vertical):
    """Respaldo gratuito. Se pide un 8 % más alto y se recorta la franja de abajo (donde pone su marca de agua)."""
    w, hh = (1080, 1920) if vertical else (1920, 1080)
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt[:1500]) +
           f"?width={w}&height={int(hh * 1.08)}&seed={seed}&nologo=true&model=flux")
    for k in range(6):  # el plan gratuito limita peticiones seguidas (402/429/503): esperar y reintentar
        r = requests.get(url, timeout=180)
        if r.status_code in (402, 429, 500, 502, 503):
            log("pollinations", r.status_code, "espero", 15 + 10 * k, "s")
            time.sleep(15 + 10 * k)
            continue
        break
    if r.status_code == 200 and r.headers.get("content-type", "").startswith("image") and len(r.content) > 20000:
        im = Image.open(io.BytesIO(r.content)).convert("RGB")
        W_, H_ = im.size
        cut = int(H_ / 1.08)
        im = im.crop((0, 0, W_, cut)).resize((w, hh), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=93)
        log("pollinations ok")
        return buf.getvalue()
    log("pollinations", r.status_code)
    return None


def imagenes_radar(d, h):
    (d / "imgs").mkdir(exist_ok=True)
    estilo = h.get("estilo_imagen", ESTILO)
    motor = cloudflare if CF_ID and CF_TOKEN else pollinations
    for i, e in enumerate(h.get("escenas", [])):
        p = e.get("imagen")
        dst = d / "imgs" / f"escena_{i}.jpg"
        if not p or p == "=" or (dst.exists() and dst.stat().st_size > 20000):
            continue
        for k in range(5):
            try:
                data = motor(p + estilo, 2000 + i + 97 * k, True)
                if data:
                    dst.write_bytes(data)
                    log("escena ok", dst.name)
                    break
            except Exception as ex:
                log("escena error", repr(ex)[:300])
            time.sleep(5 + 8 * k)


def voz_url(d, h):
    """Voz del Radar: si hay voz_url (ElevenLabs) se descarga; si no, se genera gratis con Edge TTS a partir de "texto"."""
    url = h.get("voz_url")
    dst = d / "voces" / "completa.mp3"
    if dst.exists():
        return
    if not url:
        dst.parent.mkdir(exist_ok=True)
        v = h.get("voz", {})
        voz, rate, pitch = v.get("voz", "es-ES-AlvaroNeural"), v.get("rate", "+0%"), v.get("pitch", "-2Hz")
        for k in range(5):
            try:
                asyncio.run(edge_tts.Communicate(h["texto"], voz, rate=rate, pitch=pitch).save(str(dst)))
                log("voz Edge TTS ok", voz, dst.stat().st_size, "bytes")
                return
            except Exception as e:
                log("voz Edge TTS error", repr(e)[:200])
                time.sleep(3 + 3 * k)
        raise RuntimeError("sin voz para el Radar")
    dst.parent.mkdir(exist_ok=True)
    r = requests.get(url, timeout=120)
    if r.status_code == 200 and len(r.content) > 5000:
        dst.write_bytes(r.content)
        log("voz ElevenLabs ok", len(r.content), "bytes")
    else:
        log("voz ElevenLabs ERROR", r.status_code)


def imagenes(d, h):
    (d / "imgs").mkdir(exist_ok=True)
    estilo = h.get("estilo_imagen", ESTILO)
    vertical = h.get("formato") == "vertical"
    motor = cloudflare if CF_ID and CF_TOKEN else pollinations
    log("Motor de imágenes:", motor.__name__, "| account id:", len(CF_ID), "caracteres | token:", len(CF_TOKEN), "caracteres")
    for i, b in enumerate(h["bloques"]):
        p = b.get("imagen")
        if not p or p == "=" or b.get("tipo") == "capitulo":
            continue
        dst = d / "imgs" / f"bloque_{i:03d}.jpg"
        if dst.exists() and dst.stat().st_size > 20000:
            continue
        for k in range(5):
            try:
                data = motor(p + estilo, 1000 + i + 97 * k, vertical)
                if data:
                    dst.write_bytes(data)
                    print("imagen ok", dst.name, flush=True)
                    break
            except Exception as e:
                log("imagen error", repr(e)[:300])
            time.sleep(5 + 8 * k)
        else:
            log("SIN IMAGEN", dst.name)
        time.sleep(1 if motor is cloudflare else 4)


ESTILO_PJ = (", full body character, standing, isolated on plain white background, centered, creepy comic book "
             "illustration, graphic novel art, thick black ink outlines, cel shading, flat muted desaturated colors, "
             "no text, no logos, no brands, no watermark, no shadow on the floor")
_REMBG = None


def reparto(d, h):
    """Genera cada personaje una vez (fondo blanco) y le quita el fondo con rembg -> imgs/personaje_<id>.png (RGBA)."""
    global _REMBG
    pj = h.get("reparto", {})
    if not pj:
        return
    (d / "imgs").mkdir(exist_ok=True)
    motor = cloudflare if CF_ID and CF_TOKEN else pollinations
    estilo_pj = h.get("estilo_personaje", ESTILO_PJ)
    for k, (pid, prompt) in enumerate(pj.items()):
        dst = d / "imgs" / f"personaje_{pid}.png"
        if dst.exists():
            continue
        data = None
        for intento in range(4):
            try:
                data = motor(prompt + estilo_pj, 500 + k + 31 * intento, False) if motor is pollinations else _cf_square(prompt + estilo_pj)
                if data:
                    break
            except Exception as e:
                log("personaje error", pid, repr(e)[:200])
            time.sleep(5)
        if not data:
            log("SIN PERSONAJE", pid)
            continue
        try:
            if _REMBG is None:
                from rembg import new_session
                _REMBG = new_session("isnet-general-use")
            from rembg import remove
            im = Image.open(io.BytesIO(data)).convert("RGB")
            out = remove(im, session=_REMBG)
            bb = out.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
            if bb:
                out = out.crop(bb)
            out.save(dst)
            log("personaje ok", dst.name, out.size)
        except Exception as e:
            log("recorte error", pid, repr(e)[:300])


def _poll_square(prompt):
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt[:1500]) +
           "?width=1024&height=1106&seed=77&nologo=true&model=flux")
    r = requests.get(url, timeout=180)
    if r.status_code == 200 and r.headers.get("content-type", "").startswith("image") and len(r.content) > 20000:
        im = Image.open(io.BytesIO(r.content)).convert("RGB")
        im = im.crop((0, 0, im.size[0], int(im.size[1] / 1.08)))
        buf = io.BytesIO()
        im.save(buf, "PNG")
        return buf.getvalue()
    log("pollinations personaje", r.status_code)
    return None


def _cf_square(prompt):
    global CF_AGOTADO
    if CF_AGOTADO:
        return _poll_square(prompt)
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ID}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    r = requests.post(url, headers={"Authorization": f"Bearer {CF_TOKEN}"}, json={"prompt": prompt[:2000], "steps": 4}, timeout=120)
    if r.status_code != 200:
        log("cloudflare", r.status_code, r.text[:200])
        if r.status_code == 429 or "daily free allocation" in r.text:
            CF_AGOTADO = True
            return _poll_square(prompt)
        return None
    return base64.b64decode(r.json()["result"]["image"])


_DEPTH = None


def profundidad(d):
    """Mapa de profundidad (Depth Anything V2 Small) para cada imagen: necesario para la animación 2.5D."""
    global _DEPTH
    for img in sorted(list((d / "imgs").glob("bloque_???.jpg")) + list((d / "imgs").glob("escena_*.jpg"))):  # solo fondos
        dst = img.with_name(img.stem + "_depth.png")
        if dst.exists():
            continue
        try:
            if _DEPTH is None:
                from transformers import pipeline
                _DEPTH = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf", device=-1)
            res = _DEPTH(Image.open(img).convert("RGB"))
            res["depth"].convert("L").resize(Image.open(img).size).save(dst)
            log("profundidad ok", dst.name)
        except Exception as e:
            log("profundidad error", img.name, repr(e)[:300])


for hj in sorted(list(Path("largos").glob("*/historia.json")) + list(Path("cortos").glob("*/historia.json")) + list(Path("radar").glob("*/historia.json"))):
    d = hj.parent
    if (d / "preparado.txt").exists():
        if (d / "imgs").exists() and any(not p.with_name(p.stem + "_depth.png").exists() for p in list((d / "imgs").glob("bloque_???.jpg")) + list((d / "imgs").glob("escena_*.jpg"))):
            profundidad(d)
        continue
    h = json.loads(hj.read_text(encoding="utf-8"))
    print("Preparando", d, flush=True)
    if h.get("formato") == "radar":
        voz_url(d, h)
        imagenes_radar(d, h)
    else:
        asyncio.run(voces(d, h))
        imagenes(d, h)
    reparto(d, h)
    profundidad(d)
    (d / "log_imagenes.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
    LOG.clear()
    (d / "preparado.txt").write_text("ok\n")
