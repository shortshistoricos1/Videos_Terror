"""Historia de terror en estilo motion design: tarjeta de cómic con personaje animado + narración que aparece
palabra a palabra al ritmo de la voz, palabras clave en rojo, conversaciones de chat en el móvil, contador y cierre de marca.
HTML/CSS animado por tiempo y capturado con Chrome (Playwright).

Uso: python3 -I tools/historia_motion.py <carpeta> salida.mp4
  - "formato": "vertical"  -> short 1080x1920 (cortos/)
  - cualquier otro         -> vídeo largo 1920x1080 (largos/): intro con título, capítulos, miniatura.jpg y capitulos.txt
Lee historia.json, voces/bloque_XXX.mp3, imgs/bloque_XXX.jpg e imgs/personaje_<id>.png.

Chat en un bloque (opcional):
  "chat": {"contacto": "Jefe", "avatar": "id_personaje|?", "hora": "03:12",
           "mensajes": [{"de": "el|yo", "texto": "...", "en": "frase del texto donde aparece", "borrado": false}]}"""
import html as H_
import json
import os
import re
import subprocess
import sys
import tempfile
import wave
from multiprocessing import Process
from pathlib import Path

import numpy as np

D = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
H = json.loads((D / "historia.json").read_text(encoding="utf-8"))
VERT = H.get("formato") == "vertical"
W, HH = (1080, 1920) if VERT else (1920, 1080)
FPS, SR = 30, 44100
TMP = Path(tempfile.mkdtemp(prefix="histm_"))
esc = lambda s: H_.escape(str(s))
NUM = {"uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9,
       "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15}


def dur_of(f):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)]))


def spans_of(f, d):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(f), "-af", "silencedetect=noise=-33dB:d=0.15", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    sp, cur = [], 0.0
    for s, e in zip(st, en + [d] * (len(st) - len(en))):
        if s > cur + 0.05:
            sp.append((cur, s))
        cur = e
    if cur < d - 0.05:
        sp.append((cur, d))
    return sp or [(0.0, d)]


def frac_to_time(sp, x):
    tot = sum(b - a for a, b in sp)
    target, acc = x * tot, 0.0
    for a, b in sp:
        if acc + (b - a) >= target:
            return a + (target - acc)
        acc += b - a
    return sp[-1][1]


def word_time(b, frase, default):
    """Momento en que la voz dice `frase` dentro del bloque b."""
    if not frase:
        return default
    k0 = b["texto"].lower().find(frase.lower())
    if k0 < 0:
        return default
    return b["wt"][min(len(b["wt"]) - 1, len(b["texto"][:k0].split()))]


# ---------------------------------------------------------------- coherencia de los chats
# Un bloque con chat es una conversación ESCRITA: la narración no puede hablar de llamadas, voces ni susurros.
VOZ = re.compile(r"\b(susurr\w*|grit\w*|llam(ó|o|aba|ada|adas)\b|son(ó|aba) el (teléfono|móvil)|descolg\w*|colg(ó|ué)\w*|"
                 r"al otro lado de la línea|su voz|una voz|me dijo|dijo|contest(ó|é)|habl(ó|aba))", re.I)
mal = []
for i, b in enumerate(H["bloques"]):
    if b.get("chat"):
        for m in VOZ.finditer(b["texto"]):
            mal.append(f"bloque {i}: «{m.group(0)}» en «{b['texto']}»")
        if any(s.get("tipo") == "telefono" for s in b.get("sfx", [])):
            mal.append(f"bloque {i}: sfx «telefono» (timbre de llamada) en un bloque de chat")
if mal:
    sys.exit("INCOHERENTE: estos bloques son un chat escrito pero la narración habla de llamada/voz:\n  " + "\n  ".join(mal) +
             "\nReescribe el texto como mensajes (vibró el móvil, me llegó un mensaje, leí, escribió, respondí) y vuelve a generar las voces.")

# ---------------------------------------------------------------- cronología
INTRO = 0.0 if VERT else 4.2
blocks, t, last_img = [], INTRO, None
first_img = next((D / "imgs" / f"bloque_{i:03d}.jpg" for i in range(len(H["bloques"]))
                  if (D / "imgs" / f"bloque_{i:03d}.jpg").exists()), None)
if first_img is None:
    sys.exit("No hay ninguna imagen en imgs/")
for i, b in enumerate(H["bloques"]):
    f = D / "voces" / f"bloque_{i:03d}.mp3"
    if not f.exists():
        print(f"aviso: falta {f.name}, se omite el bloque", flush=True)
        continue
    vd = dur_of(f)
    chap = b.get("tipo") == "capitulo"
    pre, post = (0.7, 1.1) if chap else (0.3, float(b.get("pausa", 0.55)))
    img = D / "imgs" / f"bloque_{i:03d}.jpg"
    if img.exists() and not chap:
        last_img = img
    sp = spans_of(f, vd)
    words, pos, wt = b["texto"].split(), 0, []
    for w in words:
        k = b["texto"].find(w, pos)
        wt.append(round(t + pre + frac_to_time(sp, k / len(b["texto"])), 3))
        pos = k + len(w)
    blocks.append(dict(b, i=i, f=f, vd=vd, chap=chap, start=t, vstart=t + pre, end=t + pre + vd + post,
                       img=last_img or first_img, words=words, wt=wt))
    t += pre + vd + post
T_CIERRE = t
TOTAL = round(t + (4.6 if VERT else 7.0), 2)
STORY = [b for b in blocks if not b["chap"]]
CHAPS = [b for b in blocks if b["chap"]]
N = len(STORY)
print(f"{len(blocks)} bloques ({len(CHAPS)} capítulos) · {T_CIERRE / 60:.2f} min de historia · total {TOTAL / 60:.2f} min", flush=True)

FONTS = {"black": "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf",
         "mono": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
         "serif": "/usr/share/fonts/truetype/google-fonts/Lora-Variable.ttf",
         "emoji": "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"}
EYE = """<svg viewBox="0 0 120 120" width="100%" height="100%"><circle cx="60" cy="60" r="55" fill="#e2262b" stroke="#efe8dc" stroke-width="7"/>
<path d="M18 60 Q60 20 102 60 Q60 100 18 60Z" fill="#efe8dc"/><circle class="pupil" cx="60" cy="60" r="16" fill="#0d0a0b"/>
<rect class="lid" x="10" y="14" width="100" height="26" fill="#e2262b"/></svg>"""

# medidas según formato
if VERT:
    COL_W, CARD_H, CHAT_H, TXT_H, TXT_MAX = 952, 820, 900, 700, 74
else:
    COL_W, CARD_H, CHAT_H, TXT_H, TXT_MAX = 680, 800, 800, 780, 70


def font_for(text, avail_h, pills):
    """Tamaño de letra para que la narración quepa en el hueco disponible."""
    chars = max(20, len(text))
    h = avail_h - (120 if pills else 0)
    fs = (h * COL_W / (0.66 * 1.04 * chars)) ** 0.5
    return int(max(40, min(TXT_MAX, fs)))


# ---------------------------------------------------------------- HTML
GROUPS, HITS, BLIPS, scenes = [], [], [], []
titulo = H.get("titulo", "")


def group(a, b, bg, sid):
    g = {"a": a, "b": b, "bg": bg, "id": sid, "it": []}
    GROUPS.append(g)
    return g["it"]


def chat_html(i, b, c):
    """Tarjeta de móvil con conversación. Devuelve html y añade los tiempos al grupo."""
    nombre = c.get("contacto", "Desconocido")
    av = c.get("avatar", "")
    pp = D / "imgs" / f"personaje_{av}.png"
    if av and pp.exists():
        avatar = f'<div class="av"><img src="{pp.as_uri()}"></div>'
    else:
        avatar = f'<div class="av">{esc("?" if av == "?" else nombre[:1].upper())}</div>'
    msgs = c.get("mensajes", [])
    h0, m0 = (int(x) for x in (c.get("hora", "03:12").split(":") + ["0"])[:2])
    # mensajes con "en": cuando la voz dice esa frase; los demás, repartidos hasta casi el final del bloque (incluida la pausa)
    a, z = b["vstart"] + 0.2, b["end"] - 0.9
    anc = [word_time(b, m.get("en"), None) for m in msgs]
    tm, k = [None] * len(msgs), 0
    while k < len(msgs):
        if anc[k] is not None:
            tm[k] = anc[k]
            k += 1
            continue
        j = k
        while j < len(msgs) and anc[j] is None:
            j += 1
        lo = (tm[k - 1] + 0.9) if k else a
        hi = (anc[j] - 0.9) if j < len(msgs) else z
        for q in range(k, j):
            tm[q] = lo + (hi - lo) * ((q - k) / max(1, j - k - 1) if j - k > 1 else 0.0)
        k = j
    times, rows = [], ""
    for k, m in enumerate(msgs):
        de = "out" if m.get("de", "el") in ("yo", "Y", "out") else "in"
        t0 = tm[k]
        if times and t0 < times[-1][0] + 0.6:
            t0 = times[-1][0] + 0.6
        hora = m.get("hora", f"{h0:02d}:{(m0 + k) % 60:02d}")
        tick = ' <span class="tk">✓✓</span>' if de == "out" else ""
        rows += (f'<div class="msg {de}" id="b{i}m{k}"><div class="bt" id="b{i}m{k}t">{esc(m["texto"])}</div>'
                 f'<div class="meta">{hora}{tick}</div></div>')
        times.append((round(t0, 3), de, 1 if m.get("borrado") else 0))
        BLIPS.append((t0, de))
    rows += f'<div class="msg in typing" id="b{i}ty"><div class="bt"><i></i><i></i><i></i></div></div>'
    html = (f'<div class="card chat" id="b{i}card"><div class="ch-h"><span class="bk">‹</span>{avatar}'
            f'<div><div class="nm">{esc(nombre)}</div><div class="st" id="b{i}st">en línea</div></div>'
            f'<span class="ic">☏</span></div><div class="ch-b" id="b{i}cb">{rows}</div></div>')
    return html, times


# intro (solo vídeo largo)
if not VERT:
    it = group(0, INTRO, "dark", "scI")
    scenes.append(f'''<div class="scene" id="scI"><div class="center">
 <div class="tag" id="iA">{esc(H.get("subtitulo", "Una historia de miedo").upper())}</div>
 <div class="big" id="iB" data-k style="text-align:center">{esc(titulo.upper())}</div>
 <div class="brandmini" id="iC"><div style="width:84px;height:84px">{EYE}</div><div>SHORTS TERROR <span style="color:var(--red)">ESPAÑA</span></div></div>
</div></div>''')
    it += [("pop", "iA", 0.2), ("kin", "iB", 0.5), ("slide", "iC", 1.6)]
    HITS.append(0.5)

chap_n = 0
for b in blocks:
    i = b["i"]
    if b["chap"]:
        chap_n += 1
        m = re.match(r"\s*([^\.]+)\.\s*(.+?)\.?\s*$", b["texto"])
        num = m.group(1).strip().lower() if m else str(chap_n)
        b["chapt"] = (NUM.get(num, chap_n), (m.group(2) if m else b["texto"]).upper())
        it = group(b["start"], b["end"], "red", f"sc{i}")
        scenes.append(f'''<div class="scene" id="sc{i}"><div class="center">
 <div class="pill dk" id="b{i}n">CAPÍTULO {b["chapt"][0]}</div>
 <div class="big" id="b{i}h" data-k style="text-align:center">{esc(b["chapt"][1])}</div></div></div>''')
        it += [("pop", f"b{i}n", b["start"] + 0.15), ("kin", f"b{i}h", b["vstart"])]
        HITS.append(b["start"] + 0.15)
        continue
    imp_words = {re.sub(r"\W", "", w.lower()) for x in b.get("impactos", []) for w in x["texto"].split()}
    fondo = b.get("fondo") or ("red" if any(s.get("tipo") == "golpe_final" for s in b.get("sfx", [])) else
                               "bone" if b.get("impactos") and i % 2 == 0 else "dark")
    it = group(b["start"], b["end"], fondo, f"sc{i}")
    chat = b.get("chat")
    if chat:
        card, ctimes = chat_html(i, b, chat)
        it.append(("chat", f"b{i}", ctimes))
    else:
        pj_html = ""
        for k, p in enumerate(b.get("personajes", [])):
            pp = D / "imgs" / f"personaje_{p['quien']}.png"
            if pp.exists():
                x = float(p.get("x", 0.5)) * 100
                alto = float(p.get("alto", 0.55 if VERT else 0.72)) * (150 if VERT else 120)
                pj_html += (f'<img class="pj{" sil" if p.get("silueta") else ""}" id="b{i}p{k}" src="{pp.as_uri()}" '
                            f'style="left:{x}%;height:{int(alto)}%{";--mx:-1" if p.get("espejo") else ""}">')
                it.append(("pj", f"b{i}p{k}", word_time(b, p.get("en", ""), b["start"] + 0.3), p.get("anim", "aparece"),
                           -1 if p.get("espejo") else 1))
        card = (f'<div class="card img {"cam" if b.get("ambiente") == "estatica" else ""}" id="b{i}card">'
                f'<div class="photo" id="b{i}ph" style="background-image:url({b["img"].as_uri()})"></div>{pj_html}'
                f'<div class="rec" id="b{i}rec">● REC 03:0{min(9, i % 10)}</div></div>')
        it.append(("kb", f"b{i}ph", b["start"], b["end"], i % 3))
    avail = (HH - 230 - (CHAT_H if chat else CARD_H) - 110) if VERT else TXT_H
    fs = font_for(b["texto"], avail, b.get("impactos"))
    words_html = "".join(f'<span class="w{" hl" if re.sub(r"[^\\wáéíóúñü]", "", w.lower()) in imp_words else ""}" id="b{i}w{j}">{esc(w)}</span> '
                         for j, w in enumerate(b["words"]))
    head = (f'<div class="tag" id="b{i}tt">{esc(titulo.upper())}</div>' if VERT and i == STORY[0]["i"] and titulo else "")
    pills = ""
    for k, x in enumerate(b.get("impactos", [])):
        t0 = word_time(b, x.get("en", x["texto"]), b["vstart"] + 0.5)
        pills += f'<div class="pill" id="b{i}i{k}">{esc(x["texto"].upper())}</div>'
        it.append(("pop", f"b{i}i{k}", t0, 1.8))
        HITS.append(t0)
    scenes.append(f'''<div class="scene" id="sc{i}"><div class="stack">{head}{card}
  <div class="rc"><div class="txt" id="b{i}txt" style="font-size:{fs}px">{words_html}</div>{pills}</div></div></div>''')
    it.append(("slide", f"b{i}card", b["start"] + 0.05))
    it.append(("words", f"b{i}", b["wt"]))
    if head:
        it.append(("pop", f"b{i}tt", b["start"] + 0.1))
    for s in b.get("sfx", []):
        if s.get("tipo") in ("golpe_final", "golpes"):
            HITS.append(b["vstart"] + b["vd"] + 0.1 if s["tipo"] == "golpe_final" else word_time(b, s.get("en"), b["vstart"] + 0.5))

fin = H.get("final", ["¿Tú qué habrías hecho?", "Sígueme para más"])
sig = "SÍGUEME" if VERT else "SUSCRÍBETE"
it = group(T_CIERRE, TOTAL + 1, "dark", "scC")
scenes.append(f'''<div class="scene" id="scC"><div class="stack fin">
 <div class="big" id="cA" data-k>{esc(fin[0].upper())}</div>
 <div class="pill" id="cB" style="font-size:64px;padding:18px 40px">{sig}</div>
 <div class="card brand" id="cC"><div style="width:170px;height:170px;flex:none">{EYE}</div>
  <div><div style="font-size:76px;line-height:.95">SHORTS TERROR</div><div style="font-family:Serif;font-size:46px;letter-spacing:14px;color:var(--red)">ESPAÑA</div></div></div>
 <div class="card coment" id="cD"><div class="mono" style="font-size:28px;color:#8d8386">comentario</div><div class="mono" style="font-size:46px;margin-top:8px" id="cDt" data-word="{esc(H.get("comentario", "yo no salgo ni loco 😨"))}"></div></div>
</div></div>''')
it += [("kin", "cA", T_CIERRE + 0.1), ("pop", "cB", T_CIERRE + 1.0, 1.6), ("slide", "cC", T_CIERRE + 1.6), ("slide", "cD", T_CIERRE + 2.2),
       ("type", "cDt", T_CIERRE + 2.5)]
HITS.append(T_CIERRE + 1.0)

CSS = """
@font-face{font-family:Black;src:url(file://%(black)s)}@font-face{font-family:Mono;src:url(file://%(mono)s)}@font-face{font-family:Serif;src:url(file://%(serif)s)}
@font-face{font-family:Emo;src:url(file://%(emoji)s)}
:root{--red:#e2262b;--bone:#efe8dc;--ink:#0d0a0b;--panel:#1b1517}
*{box-sizing:border-box;margin:0}
body{width:%(W)spx;height:%(HH)spx;overflow:hidden;background:var(--ink);font-family:Black,Emo;color:var(--bone)}
.bg{position:absolute;inset:0;opacity:0}
.dark{background:radial-gradient(120%% 70%% at 50%% 38%%,#2a0c0e 0%%,#120a0b 55%%,#070505 100%%)}
.bone{background:radial-gradient(120%% 80%% at 50%% 40%%,#f6f1e8 0%%,#e6ded1 70%%,#cfc5b6 100%%)}
.red{background:radial-gradient(120%% 80%% at 50%% 35%%,#ff3b30 0%%,#d61f24 55%%,#8e0f13 100%%)}
.scene{position:absolute;inset:0;opacity:0;display:none}
.stack{position:absolute;left:64px;right:64px;top:0;padding-top:230px;display:flex;flex-direction:column;align-items:flex-start;gap:30px}
.center{position:absolute;inset:0;padding:0 120px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:44px}
.big{font-size:120px;line-height:.92;letter-spacing:-4px;text-transform:uppercase;width:100%%}
.card{position:relative;background:var(--panel);border-radius:30px;border:2px solid rgba(255,255,255,.07);box-shadow:0 40px 80px rgba(0,0,0,.55);overflow:hidden;width:100%%}
.img{height:%(CARD_H)spx}.photo{position:absolute;inset:-4%%;background-size:cover;background-position:center}
.cam .photo{filter:grayscale(1) contrast(1.25) brightness(1.05)}
.cam::after{content:"";position:absolute;inset:0;background:repeating-linear-gradient(0deg,rgba(0,0,0,.18) 0 2px,transparent 2px 5px)}
.rec{position:absolute;right:26px;top:24px;font-family:Mono;font-size:28px;color:#ff4a3d;opacity:0}
.cam .rec{opacity:1}
.pj{position:absolute;bottom:-6px;transform:translateX(-50%%);opacity:0}
.pj.sil{filter:brightness(0) drop-shadow(0 0 18px rgba(255,60,50,.8)) drop-shadow(0 0 3px #efe8dc)}
.txt{line-height:1.04;letter-spacing:-2px;text-transform:uppercase;width:100%%}
.w{display:inline-block;opacity:0}.w.hl{color:var(--red)}
.onbone .w{color:var(--ink)}.onbone .w.hl{color:var(--red)}
.pill{background:var(--red);color:#fff;font-family:Mono;font-size:46px;padding:12px 28px;border-radius:12px;letter-spacing:2px;opacity:0}
.pill.dk{background:#140f10;border:2px solid rgba(255,255,255,.15);font-size:44px}
.tag{font-family:Mono;font-size:32px;color:#cfc5b6;background:#140f10;border-radius:10px;padding:10px 18px;border:2px solid rgba(255,255,255,.08);opacity:0}
.rc{display:contents}.mono{font-family:Mono}.ch{display:inline-block;white-space:pre}
.brand{display:flex;align-items:center;gap:40px;padding:40px 50px}.coment{padding:24px 36px;background:#140f10}
.brandmini{display:flex;align-items:center;gap:22px;font-size:40px;opacity:0}
.ember{position:absolute;border-radius:50%%;background:radial-gradient(circle,rgba(255,70,50,.9),rgba(255,40,30,0) 70%%)}
#prog{position:absolute;right:56px;top:96px;background:#140f10;border:2px solid rgba(255,255,255,.08);border-radius:14px;padding:12px 20px;font-family:Mono;font-size:28px;color:#cfc5b6;display:flex;gap:10px;align-items:center;z-index:50}
#prog .bar{width:20px;height:8px;border-radius:4px;background:#3a3133}#prog .on{background:var(--red)}
#logo{position:absolute;left:56px;top:88px;display:flex;align-items:center;gap:14px;z-index:50;font-size:32px}
#logo .e{width:64px;height:64px}
/* chat */
.chat{height:%(CHAT_H)spx;background:#0f0b0c;display:flex;flex-direction:column}
.ch-h{display:flex;align-items:center;gap:20px;padding:22px 28px;background:#1d1617;border-bottom:2px solid rgba(255,255,255,.06);flex:none}
.bk{font-size:64px;line-height:1;color:#cfc5b6;margin-top:-8px}.ic{margin-left:auto;font-size:48px;color:#cfc5b6;font-family:Mono}
.av{width:%(AV)spx;height:%(AV)spx;border-radius:50%%;background:var(--red);display:flex;align-items:center;justify-content:center;font-size:%(AVF)spx;overflow:hidden;flex:none}
.av img{width:100%%;height:180%%;object-fit:cover;object-position:top;background:#2a2122}
.nm{font-size:%(NMF)spx;letter-spacing:-1px}.st{font-family:Mono;font-size:%(STF)spx;color:#8d8386;margin-top:4px}.st.ty{color:#ff5a4e}
.ch-b{flex:1;display:flex;flex-direction:column;justify-content:flex-end;gap:16px;padding:26px 26px 30px;overflow:hidden;
 background:radial-gradient(circle at 20%% 10%%,rgba(226,38,43,.10),transparent 50%%),repeating-radial-gradient(circle at 0 0,rgba(255,255,255,.025) 0 2px,transparent 2px 26px),#0f0b0c}
.msg{max-width:80%%;padding:16px 22px 10px;border-radius:26px;display:none;flex-direction:column;flex:none;transform-origin:left bottom}
.msg.in{align-self:flex-start;background:#2a2224;border-bottom-left-radius:8px}
.msg.out{align-self:flex-end;background:#7d1418;border-bottom-right-radius:8px;transform-origin:right bottom}
.bt{font-family:Black,Emo;font-size:%(MF)spx;line-height:1.15;letter-spacing:-.5px;color:#f3ede4;text-transform:none}
.bt.del{font-family:Mono;font-style:italic;color:#9a8f92;font-size:%(MDF)spx}
.meta{font-family:Mono;font-size:%(MTF)spx;color:rgba(239,232,220,.55);align-self:flex-end;margin-top:6px}.tk{color:#ff8a80}
.typing .bt{display:flex;gap:12px;padding:10px 6px}.typing i{width:18px;height:18px;border-radius:50%%;background:#cfc5b6;display:block}
""" % dict(FONTS, W=W, HH=HH, CARD_H=CARD_H, CHAT_H=CHAT_H, AV=92 if VERT else 80, AVF=50 if VERT else 42, NMF=46 if VERT else 40,
           STF=26 if VERT else 22, MF=44 if VERT else 36, MDF=34 if VERT else 28, MTF=22 if VERT else 19)
if not VERT:
    CSS += """
.stack{left:90px;right:90px;padding-top:180px;flex-direction:row;gap:60px}
.stack>.card{width:1000px;flex:none}.rc{display:flex;flex-direction:column;gap:26px;align-items:flex-start;flex:1;min-width:0}
.stack.fin{flex-direction:column;left:200px;right:200px;padding-top:170px;gap:26px}
.stack.fin .big{font-size:104px}
.big{font-size:132px}
#prog{top:70px;right:90px}#logo{top:62px;left:90px}
"""

JS = r"""
const G=%(groups)s, HITS=%(hits)s, END=%(end)s, BST=%(bst)s, CIERRE=%(cierre)s, CAPS=%(caps)s, VERT=%(vert)s;
const clamp=(x,a=0,b=1)=>Math.min(b,Math.max(a,x)), seg=(t,a,b)=>clamp((t-a)/(b-a));
const eOut=x=>1-Math.pow(1-x,3), eExpo=x=>x>=1?1:1-Math.pow(2,-10*x);
const eBack=x=>{const c=1.9;x=clamp(x);return 1+(c+1)*Math.pow(x-1,3)+c*Math.pow(x-1,2)};
const $=id=>document.getElementById(id);
function tf(el,o,x=0,y=0,s=1,r=0,b=0){el.style.opacity=o;el.style.transform=`translate(${x}px,${y}px) scale(${s}) rotate(${r}deg)`;el.style.filter=b>0.05?`blur(${b}px)`:'none';}
document.querySelectorAll('[data-k]').forEach(el=>{const tx=el.textContent;el.textContent='';
 tx.split(' ').forEach((w,wi,arr)=>{const W=document.createElement('span');W.style.whiteSpace='nowrap';W.style.display='inline-block';
  [...w].forEach(c=>{const s=document.createElement('span');s.className='ch';s.textContent=c;W.appendChild(s);});
  el.appendChild(W);if(wi<arr.length-1)el.appendChild(document.createTextNode(' '));});});
const bgs=document.createElement('div');document.body.prepend(bgs);const BG={};
['dark','red','bone'].forEach(k=>{const d=document.createElement('div');d.className='bg '+k;bgs.appendChild(d);BG[k]=d;});
const SW=%(W)s, SH=%(HH)s;
const EM=[];for(let i=0;i<24;i++){const d=document.createElement('div');d.className='ember';const r=20+((i*37)%%70);d.style.width=d.style.height=r+'px';
 bgs.after(d);EM.push({d,x:(i*157)%%SW,y:(i*331)%%SH,v:18+(i*13)%%40,ph:i*1.7});}
G.forEach(g=>{g.el=$(g.id);});
function item(it,t){const [k,id]=it;
  if(k==='words'){const wt=it[2];wt.forEach((w0,j)=>{const el=$(id+'w'+j);const p=seg(t,w0-0.05,w0+0.3);
    const hl=el.classList.contains('hl');tf(el,clamp(p*2),0,(1-eBack(p))*50,hl?1+0.25*Math.exp(-Math.max(0,t-w0)*6):1,0,(1-p)*10);});return;}
  if(k==='chat'){const ms=it[2];let typing=false;
    ms.forEach(([t0,de,del],j)=>{const el=$(id+'m'+j);const on=t>=t0;el.style.display=on?'flex':'none';
      if(on){const p=seg(t,t0,t0+0.35);tf(el,clamp(p*3),0,(1-eOut(p))*30,0.7+0.3*eBack(p),0,0);
        const bt=$(id+'m'+j+'t');if(del&&t>=t0+1.8){if(!bt.dataset.o){bt.dataset.o=bt.textContent;}bt.textContent='⊘ Se eliminó este mensaje';bt.classList.add('del');}
        else if(bt.dataset.o){bt.textContent=bt.dataset.o;bt.classList.remove('del');}}
      if(de==='in'&&t>=t0-1.0&&t<t0)typing=true;});
    const ty=$(id+'ty');ty.style.display=typing?'flex':'none';
    if(typing){ty.querySelectorAll('i').forEach((d,n)=>{d.style.opacity=0.35+0.65*Math.max(0,Math.sin(t*9-n*0.9));
      d.style.transform=`translateY(${-6*Math.max(0,Math.sin(t*9-n*0.9))}px)`;});tf(ty,1);}
    const st=$(id+'st');st.textContent=typing?'escribiendo…':'en línea';st.classList.toggle('ty',typing);return;}
  const el=$(id);if(!el)return;
  if(k==='kin'){const [,,t0]=it;const cs=el.querySelectorAll('.ch');
    for(let i=0;i<cs.length;i++){const p=seg(t,t0+i*0.03,t0+i*0.03+0.5);tf(cs[i],clamp(p*2),0,(1-eBack(p))*90,1,0,(1-p)*14);}}
  else if(k==='pop'){const [,,t0,from=0.6]=it;const p=seg(t,t0,t0+0.45);tf(el,clamp(p*3),0,(1-eOut(p))*40,from+(1-from)*eBack(p),-2,(1-p)*8);}
  else if(k==='slide'){const [,,t0]=it;const p=seg(t,t0,t0+0.55);const e=eExpo(p);tf(el,clamp(p*3),0,120*(1-e),0.94+0.06*e,0,(1-p)*10);}
  else if(k==='type'){const [,,t0]=it;const w=[...el.dataset.word];const n=Math.floor(clamp((t-t0)/Math.max(0.6,w.length*0.07))*w.length);
    el.textContent=w.slice(0,n).join('')+((n<w.length||Math.floor(t*2.4)%%2)?'|':' ');}
  else if(k==='kb'){const [,,a,b,m]=it;const p=seg(t,a,b);const tx=[0,-30,30][m]*p, s=[1.0+0.10*p,1.08-0.06*p,1.03+0.07*p][m];
    el.style.transform=`translateX(${tx}px) scale(${s})`;}
  else if(k==='pj'){const [,,t0,an,mx=1]=it;const p=seg(t,t0,t0+0.9);let o=p,x=0,y=(1-eOut(p))*40,r=0,s=0.94+0.06*eOut(p),sx=1;
    if(an==='aparece')o=p*((p<1&&Math.floor(t*18)%%3===0)?0.3:1);
    if(an==='camina'){x=(1-eOut(seg(t,t0,t0+1.6)))*-520*mx;y=-Math.abs(Math.sin(t*10))*12*(1-seg(t,t0,t0+1.6));o=seg(t,t0,t0+0.3);}
    if(an==='asoma'){x=(1-eOut(seg(t,t0,t0+1.2)))*260*mx;o=seg(t,t0,t0+0.3);}
    if(an==='tiembla'){x=6*Math.sin(t*61);r=0.8*Math.sin(t*47);}
    if(an==='gira'){const q=seg(t,t0,t0+0.6);sx=Math.cos(Math.PI*eOut(q))||0.02;o=1;}
    if(an==='se_acerca')s=0.6+0.6*seg(t,t0,t0+5);
    el.style.opacity=o;el.style.transform=`translateX(calc(-50%% + ${x}px)) translateY(${y+5*Math.sin(t*1.8)}px) scale(${s*sx*mx},${s}) rotate(${r}deg)`;}
}
function render(t){
 let curBg='dark';
 G.forEach(g=>{const vis=t>=g.a-0.01&&t<g.b;g.el.style.display=vis?'block':'none';if(!vis)return;curBg=g.bg;
   g.el.classList.toggle('onbone',g.bg==='bone');
   const pin=seg(t,g.a,g.a+0.22),pout=seg(t,g.b-0.22,g.b);tf(g.el,1-pout,0,0,1+0.04*pout+0.03*(1-eOut(pin)),0,pout*16);
   g.it.forEach(it=>item(it,t));});
 Object.entries(BG).forEach(([k,d])=>d.style.opacity=(k===curBg)?1:0);
 EM.forEach(e=>{const y=((e.y-t*e.v)%%SH+SH)%%SH;e.d.style.transform=`translate(${e.x+30*Math.sin(t*0.6+e.ph)}px,${y}px)`;
  e.d.style.opacity=curBg==='dark'?(0.25+0.25*Math.sin(t*1.3+e.ph)):0;});
 const pr=$('prog');
 if(CAPS.length){let n=0;CAPS.forEach((a,k)=>{if(t>=a)n=k+1;});pr.style.opacity=(n>0&&t<CIERRE)?1:0;$('pn').textContent='CAPÍTULO '+n+'/'+CAPS.length;}
 else if(BST.length<=12){let n=0;BST.forEach((a,k)=>{if(t>=a)n=k+1;});if(t>=CIERRE)n=BST.length;
  document.querySelectorAll('#prog .bar').forEach((b,i)=>b.className='bar'+(i<n?' on':''));$('pn').textContent=n+'/'+BST.length;}
 else pr.style.opacity=0;
 const lg=$('logo');lg.style.opacity=(t<CIERRE&&t>=%(intro)s)?1:0;lg.style.color=curBg==='bone'?'#0d0a0b':'#efe8dc';
 lg.querySelector('.lid').setAttribute('height',(t%%3.3)<0.14?84:26);
 let sh=0;HITS.forEach(c=>{const d=t-c;if(d>=0&&d<0.35)sh+=13*Math.exp(-d*12);});
 document.body.style.transform=sh>0.3?`translate(${sh*Math.sin(t*95)}px,${sh*Math.cos(t*80)}px)`:'none';
 document.body.style.opacity=Math.min(1-seg(t,END-0.8,END), %(fadein)s);
}
window.render=render;"""

bars = "".join('<span class="bar"></span>' for _ in range(N)) if (N <= 12 and not CHAPS) else ""
page = f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div id="logo"><div class="e">{EYE}</div><div>SHORTS TERROR</div></div>
<div id="prog">{bars}<span id="pn"></span></div>
{''.join(scenes)}
<script>{JS % dict(groups=json.dumps(GROUPS), hits=json.dumps(sorted(HITS)), end=TOTAL, bst=json.dumps([b["start"] for b in STORY]),
                   cierre=T_CIERRE, caps=json.dumps([b["start"] for b in CHAPS]), vert="true" if VERT else "false", W=W, HH=HH,
                   intro=INTRO, fadein="1" if VERT else "seg(t,0,0.6)")}</script></body></html>"""
(TMP / "h.html").write_text(page, encoding="utf-8")

# capítulos para la descripción de YouTube
if not VERT:
    caps = ["0:00 Introducción"]
    for b in CHAPS:
        s = int(b["start"])
        caps.append(f"{s // 60}:{s % 60:02d} Capítulo {b['chapt'][0]}. {b['chapt'][1].capitalize()}")
    (D / "capitulos.txt").write_text("\n".join(caps) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- audio: voces + ambiente + efectos
def build_audio():
    rng = np.random.default_rng(5)
    Nn = int((TOTAL + 0.3) * SR)
    mix = np.zeros(Nn, np.float32)

    def put(sig, t0, g):
        i = int(t0 * SR)
        if 0 <= i < Nn:
            n = min(len(sig), Nn - i)
            mix[i:i + n] += np.asarray(sig[:n], np.float32) * g

    vv = np.zeros(Nn, np.float32)
    for b in blocks:
        raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(b["f"]), "-af", "highpass=f=70,aecho=0.8:0.75:30|60:0.10|0.05",
                                       "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"])
        v = np.frombuffer(raw, np.float32)
        i = int(b["vstart"] * SR)
        vv[i:i + len(v)] += v[:max(0, Nn - i)]
    mix += vv / (np.abs(vv).max() + 1e-9) * 0.85
    x = np.arange(Nn, dtype=np.float32) / SR
    mix += (0.05 * np.sin(2 * np.pi * 55 * x) + 0.03 * np.sin(2 * np.pi * 110 * x) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.1 * x))
            + 0.012 * np.sin(2 * np.pi * 207.65 * x)).astype(np.float32) * (0.7 + 0.5 * np.clip(x / T_CIERRE, 0, 1))
    th = np.arange(int(1.4 * SR)) / SR
    ph = 2 * np.pi * np.cumsum(70 * np.exp(-th * 1.2)) / SR
    hit = ((np.sin(ph) + 0.5 * np.sin(2 * ph)) * np.exp(-th * 2.8) + rng.standard_normal(len(th)) * np.exp(-th * 25) * 0.5) * (1 - np.exp(-th * 900))
    kt = np.arange(int(0.5 * SR)) / SR
    knock = (0.7 * np.sin(2 * np.pi * 95 * kt) * np.exp(-kt * 18) + 0.5 * np.sin(2 * np.pi * 190 * kt) * np.exp(-kt * 30)
             + np.convolve(rng.standard_normal(len(kt)), np.ones(12) / 12, mode="same") * np.exp(-kt * 70)) * (1 - np.exp(-kt * 2000))
    ht = np.arange(int(0.32 * SR)) / SR
    thump = (np.sin(2 * np.pi * 62 * ht) + 0.6 * np.sin(2 * np.pi * 124 * ht)) * np.exp(-ht * 19)
    rt = np.arange(int(3.2 * SR)) / SR
    ring = np.convolve((np.sin(2 * np.pi * 820 * rt) + 0.6 * np.sin(2 * np.pi * 1230 * rt)) * (np.sin(2 * np.pi * 22 * rt) > 0) * ((rt % 3.2) < 1.4),
                       np.ones(20) / 20, mode="same") * 0.6
    bt = np.arange(int(2.2 * SR)) / SR
    br = np.convolve(rng.standard_normal(len(bt)), np.ones(8) / 8, mode="same") * np.sin(np.pi * bt / 2.2) ** 2
    at = np.arange(int(0.6 * SR)) / SR
    scratch = np.convolve(rng.standard_normal(len(at)), np.ones(4) / 4, mode="same") * (0.5 + 0.5 * np.sin(2 * np.pi * 7 * at)) * np.sin(np.pi * at / 0.6)
    # aviso de mensaje: dos notas cortas y suaves (entrante) o una (saliente)
    bl = np.arange(int(0.09 * SR)) / SR
    env = np.sin(np.pi * bl / 0.09) ** 2
    note = lambda f: np.sin(2 * np.pi * f * bl) * env
    blip_in = np.concatenate([note(988), np.zeros(int(0.03 * SR)), note(1319)])
    blip_out = note(740)
    for b in blocks:
        for s in b.get("sfx", []):
            ty = s.get("tipo")
            t_en = word_time(b, s.get("en"), b["vstart"] + 0.5) if not b["chap"] else b["vstart"]
            if ty == "golpes":
                for k in range(3):
                    put(knock, t_en + 0.5 * k, 0.3)
            elif ty == "aranazos":
                put(scratch, t_en, 0.12)
                put(scratch, t_en + 0.7, 0.1)
            elif ty == "latido":
                tb = b["start"] + 0.2
                while tb < b["end"]:
                    put(thump, tb, 0.25)
                    put(thump, tb + 0.22, 0.15)
                    tb += 0.8
            elif ty == "telefono":
                put(ring, t_en if s.get("en") else b["vstart"], 0.1)
            elif ty == "respiracion":
                put(br, t_en if s.get("en") else b["vstart"] + 0.3, 0.12)
            elif ty == "golpe_final":
                put(hit, b["vstart"] + b["vd"] + 0.1, 0.6)
    for h in HITS:
        put(hit[:int(0.6 * SR)], h, 0.2)
    for t0, de in BLIPS:
        put(blip_in if de == "in" else blip_out, t0, 0.09 if de == "in" else 0.06)
    mix[-int(1.0 * SR):] *= np.linspace(1, 0, int(1.0 * SR))
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.9
    p = TMP / "mix.wav"
    with wave.open(str(p), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((np.stack([mix, mix], 1) * 32767).astype(np.int16).tobytes())
    return p


def render_part(f0, f1, out):
    from playwright.sync_api import sync_playwright
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "image2pipe", "-c:v", "mjpeg", "-r", str(FPS), "-i", "-",
           "-vf", "noise=alls=4:allf=t+u,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20" if VERT else "21", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with sync_playwright() as pw:
        brw = pw.chromium.launch()
        pg = brw.new_page(viewport={"width": W, "height": HH})
        pg.goto((TMP / "h.html").as_uri(), wait_until="load")
        pg.evaluate("document.fonts.ready.then(()=>1)")
        for f in range(f0, f1):
            pg.evaluate(f"render({f / FPS:.4f})")
            proc.stdin.write(pg.screenshot(type="jpeg", quality=90))
            if f0 == 0 and f % 1500 == 0 and f:
                print(f"  {f}/{f1} fotogramas", flush=True)
        brw.close()
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit(1)


def miniatura():
    from PIL import Image, ImageDraw, ImageFont
    mt = H.get("miniatura", {})
    k = int(mt.get("bloque", 0))
    src = next((b["img"] for b in STORY if b["i"] >= k), first_img)
    im = Image.open(src).convert("RGB")
    w, h = im.size
    s = max(1280 / w, 720 / h)
    im = im.resize((int(w * s + 1), int(h * s + 1)), Image.LANCZOS)
    w, h = im.size
    im = im.crop(((w - 1280) // 2, (h - 720) // 2, (w - 1280) // 2 + 1280, (h - 720) // 2 + 720))
    a = np.asarray(im, np.float32)
    a = a * (1 - np.clip(1 - np.arange(720) / 330, 0, 1)[:, None, None] * 0.65)
    im = Image.fromarray(a.astype(np.uint8))
    d = ImageDraw.Draw(im)
    fb = FONTS["black"]
    t1, t2 = mt.get("texto1", "NO MIRES"), mt.get("texto2", titulo.upper())
    s1 = 160
    while d.textlength(t1, font=ImageFont.truetype(fb, s1)) > 1180:
        s1 -= 8
    s2 = 60
    while d.textlength(t2, font=ImageFont.truetype(fb, s2)) > 1000:
        s2 -= 4
    d.text((640, 120), t1, font=ImageFont.truetype(fb, s1), fill=(226, 38, 43), anchor="mm", stroke_width=7, stroke_fill=(0, 0, 0))
    bw = d.textlength(t2, font=ImageFont.truetype(fb, s2)) + 60
    d.rounded_rectangle((640 - bw / 2, 205, 640 + bw / 2, 205 + s2 + 34), 14, fill=(13, 10, 11))
    d.text((640, 205 + (s2 + 34) / 2), t2, font=ImageFont.truetype(fb, s2), fill=(239, 232, 220), anchor="mm")
    im.save(D / "miniatura.jpg", quality=90)


if __name__ == "__main__":
    if not VERT:
        miniatura()
    wav = build_audio()
    NF = int(TOTAL * FPS)
    nw = 1 if NF < 2400 else max(1, min(3, os.cpu_count() or 1))
    cuts = [NF * k // nw for k in range(nw + 1)]
    parts = [TMP / f"part{k}.mp4" for k in range(nw)]
    ps = [Process(target=render_part, args=(cuts[k], cuts[k + 1], parts[k])) for k in range(nw)]
    for p in ps:
        p.start()
    for p in ps:
        p.join()
    if any(p.exitcode for p in ps):
        sys.exit("falló el render")
    (TMP / "list.txt").write_text("".join(f"file '{p}'\n" for p in parts))
    r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(TMP / "list.txt"),
                        "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=9",
                        "-c:a", "aac", "-b:a", "192k", "-t", f"{TOTAL:.2f}", "-movflags", "+faststart", str(OUT)])
    if r.returncode:
        sys.exit("ffmpeg falló")
    print("OK", OUT, f"{OUT.stat().st_size / 1e6:.1f} MB", flush=True)
