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
          "horror comic panel, no text, no speech bubbles, no watermark")


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


def cloudflare(prompt, seed, vertical):
    """FLUX.1 schnell en Cloudflare Workers AI (gratis hasta 10.000 neuronas/día). Devuelve bytes JPG o None."""
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ID}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    r = requests.post(url, headers={"Authorization": f"Bearer {CF_TOKEN}"},
                      json={"prompt": prompt[:2000], "steps": 6, "seed": seed}, timeout=120)
    if r.status_code != 200:
        print("cloudflare", r.status_code, r.text[:300], flush=True)
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
    w, hh = (1080, 1920) if vertical else (1920, 1080)
    url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt) +
           f"?width={w}&height={hh}&seed={seed}&nologo=true&model=flux")
    r = requests.get(url, timeout=180)
    if r.status_code == 200 and r.headers.get("content-type", "").startswith("image") and len(r.content) > 20000:
        return r.content
    print("pollinations", r.status_code, flush=True)
    return None


def imagenes(d, h):
    (d / "imgs").mkdir(exist_ok=True)
    estilo = h.get("estilo_imagen", ESTILO)
    vertical = h.get("formato") == "vertical"
    motor = cloudflare if CF_ID and CF_TOKEN else pollinations
    print("Motor de imágenes:", motor.__name__, flush=True)
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
                print("imagen error", e, flush=True)
            time.sleep(5 + 8 * k)
        else:
            print("SIN IMAGEN", dst.name, "(el montaje usará la anterior)", flush=True)
        time.sleep(1 if motor is cloudflare else 4)


for hj in sorted(list(Path("largos").glob("*/historia.json")) + list(Path("cortos").glob("*/historia.json"))):
    d = hj.parent
    if (d / "preparado.txt").exists():
        continue
    h = json.loads(hj.read_text(encoding="utf-8"))
    print("Preparando", d, flush=True)
    asyncio.run(voces(d, h))
    imagenes(d, h)
    (d / "preparado.txt").write_text("ok\n")
