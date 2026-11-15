"""Se ejecuta en GitHub Actions: genera voces (Edge TTS) e imágenes (Pollinations) para cada
largos/<ID>/historia.json que aún no las tenga."""
import asyncio
import json
import time
import urllib.parse
from pathlib import Path

import edge_tts
import requests

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


def imagenes(d, h):
    (d / "imgs").mkdir(exist_ok=True)
    estilo = h.get("estilo_imagen", ESTILO)
    for i, b in enumerate(h["bloques"]):
        p = b.get("imagen")
        if not p or p == "=" or b.get("tipo") == "capitulo":
            continue
        dst = d / "imgs" / f"bloque_{i:03d}.jpg"
        if dst.exists() and dst.stat().st_size > 20000:
            continue
        url = ("https://image.pollinations.ai/prompt/" + urllib.parse.quote(p + estilo) +
               f"?width=1920&height=1080&seed={1000 + i}&nologo=true&model=flux")
        for k in range(6):
            try:
                r = requests.get(url, timeout=180)
                if r.status_code == 200 and r.headers.get("content-type", "").startswith("image") and len(r.content) > 20000:
                    dst.write_bytes(r.content)
                    print("imagen ok", dst.name, flush=True)
                    break
                print("imagen intento", k, r.status_code, flush=True)
            except Exception as e:
                print("imagen error", e, flush=True)
            time.sleep(8 + 8 * k)
        else:
            print("SIN IMAGEN", dst.name, "(el montaje usará la anterior)", flush=True)
        time.sleep(4)


for hj in sorted(Path("largos").glob("*/historia.json")):
    d = hj.parent
    if (d / "preparado.txt").exists():
        continue
    h = json.loads(hj.read_text(encoding="utf-8"))
    print("Preparando", d, flush=True)
    asyncio.run(voces(d, h))
    imagenes(d, h)
    (d / "preparado.txt").write_text("ok\n")
