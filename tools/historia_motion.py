"""Historia de terror (short vertical) en estilo motion design: tarjeta de cómic con personaje animado +
narración que aparece palabra a palabra al ritmo de la voz, palabras clave en rojo, contador n/N y cierre de marca.
HTML/CSS animado por tiempo y capturado con Chrome (Playwright).

Uso: python3 -I tools/historia_motion.py cortos/<ID> salida.mp4
Usa el mismo historia.json que tools/largo.py (formato "vertical"): bloques, voces/bloque_XXX.mp3, imgs/bloque_XXX.jpg."""
import html as H_
import json
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
from playwright.sync_api import sync_playwright

D = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()
H = json.loads((D / "historia.json").read_text(encoding="utf-8"))
FPS, SR = 30, 44100
TMP = Path(tempfile.mkdtemp(prefix="histm_"))
esc = lambda s: H_.escape(str(s))


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


# ---------------------------------------------------------------- cronología
blocks, t, last_img = [], 0.0, None
for i, b in enumerate(H["bloques"]):
    f = D / "voces" / f"bloque_{i:03d}.mp3"
    vd = dur_of(f)
    pre, post = 0.3, float(b.get("pausa", 0.55))
    img = D / "imgs" / f"bloque_{i:03d}.jpg"
    if img.exists():
        last_img = img
    sp = spans_of(f, vd)
    words, pos, wt = b["texto"].split(), 0, []
    for w in words:
        k = b["texto"].find(w, pos)
        wt.append(round(t + pre + frac_to_time(sp, k / len(b["texto"])), 3))
        pos = k + len(w)
    blocks.append(dict(b, i=i, f=f, vd=vd, start=t, vstart=t + pre, end=t + pre + vd + post, img=last_img, words=words, wt=wt))
    t += pre + vd + post
T_CIERRE = t
TOTAL = round(t + 4.6, 2)
N = len(blocks)
print(f"{N} bloques · {T_CIERRE:.1f} s de historia · total {TOTAL:.1f} s", flush=True)

FONTS = {"black": "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf",
         "mono": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
         "serif": "/usr/share/fonts/truetype/google-fonts/Lora-Variable.ttf"}
EYE = """<svg viewBox="0 0 120 120" width="100%" height="100%"><circle cx="60" cy="60" r="55" fill="#e2262b" stroke="#efe8dc" stroke-width="7"/>
<path d="M18 60 Q60 20 102 60 Q60 100 18 60Z" fill="#efe8dc"/><circle class="pupil" cx="60" cy="60" r="16" fill="#0d0a0b"/>
<rect class="lid" x="10" y="14" width="100" height="26" fill="#e2262b"/></svg>"""

# ---------------------------------------------------------------- HTML de cada bloque
TL, HITS, scenes = [], [], []
titulo = H.get("titulo", "")
for b in blocks:
    i = b["i"]
    imp_words = {re.sub(r"\W", "", w.lower()) for x in b.get("impactos", []) for w in x["texto"].split()}
    fondo = b.get("fondo") or ("red" if any(s.get("tipo") == "golpe_final" for s in b.get("sfx", [])) else
                               "bone" if b.get("impactos") and i % 2 == 0 else "dark")
    pj_html = ""
    for k, p in enumerate(b.get("personajes", [])):
        pp = D / "imgs" / f"personaje_{p['quien']}.png"
        if pp.exists():
            x = float(p.get("x", 0.5)) * 100
            pj_html += f'<img class="pj" id="b{i}p{k}" src="{pp.as_uri()}" style="left:{x}%;height:{int(float(p.get("alto", 0.55)) * 150)}%">'
            en = p.get("en", "")
            k0 = b["texto"].find(en) if en else -1
            t0 = b["wt"][len(b["texto"][:k0].split())] if k0 >= 0 else b["start"] + 0.3
            TL.append(("pj", f"b{i}p{k}", t0, p.get("anim", "aparece")))
    words_html = "".join(f'<span class="w{" hl" if re.sub(r"[^\\wáéíóúñü]", "", w.lower()) in imp_words else ""}" id="b{i}w{j}">{esc(w)}</span> '
                         for j, w in enumerate(b["words"]))
    head = (f'<div class="tag" id="b{i}tt">{esc(titulo.upper())}</div>' if i == 0 and titulo else "")
    pills = ""
    for k, x in enumerate(b.get("impactos", [])):
        en = x.get("en", x["texto"])
        k0 = b["texto"].lower().find(en.lower())
        t0 = b["wt"][len(b["texto"][:k0].split())] if k0 >= 0 else b["vstart"] + 0.5
        pills += f'<div class="pill" id="b{i}i{k}">{esc(x["texto"].upper())}</div>'
        TL.append(("pop", f"b{i}i{k}", t0, 1.8))
        HITS.append(t0)
    scenes.append(f'''<div class="scene" id="sc{i}"><div class="stack">{head}
  <div class="card img {"cam" if b.get("ambiente") == "estatica" else ""}" id="b{i}card"><div class="photo" id="b{i}ph" style="background-image:url({b["img"].as_uri()})"></div>{pj_html}
   <div class="rec" id="b{i}rec">● REC 03:0{min(9, i)}</div></div>
  <div class="txt" id="b{i}txt">{words_html}</div>{pills}</div></div>''')
    TL.insert(0, ("scene", f"sc{i}", b["start"], b["end"], fondo))
    TL.append(("slide", f"b{i}card", b["start"] + 0.05))
    TL.append(("kb", f"b{i}ph", b["start"], b["end"], i % 3))
    TL.append(("words", f"b{i}", b["wt"]))
    if head:
        TL.append(("pop", f"b{i}tt", b["start"] + 0.1))
    for s in b.get("sfx", []):
        if s.get("tipo") in ("golpe_final", "golpes"):
            HITS.append(b["vstart"] + b["vd"] + 0.1 if s["tipo"] == "golpe_final" else b["vstart"] + 0.5)
fin = H.get("final", ["¿Tú qué habrías hecho?", "Sígueme para más"])
scenes.append(f'''<div class="scene" id="scC"><div class="stack" style="padding-top:330px">
 <div class="big" id="cA" data-k>{esc(fin[0].upper())}</div>
 <div class="pill" id="cB" style="font-size:64px;padding:18px 40px">SÍGUEME</div>
 <div class="card brand" id="cC"><div style="width:170px;height:170px;flex:none">{EYE}</div>
  <div><div style="font-size:76px;line-height:.95">SHORTS TERROR</div><div style="font-family:Serif;font-size:46px;letter-spacing:14px;color:var(--red)">ESPAÑA</div></div></div>
 <div class="card coment" id="cD"><div class="mono" style="font-size:28px;color:#8d8386">comentario</div><div class="mono" style="font-size:46px;margin-top:8px" id="cDt" data-word="{esc(H.get("comentario", "yo no salgo ni loco 😨"))}"></div></div>
</div></div>''')
TL.insert(0, ("scene", "scC", T_CIERRE, 999, "dark"))
TL += [("kin", "cA", T_CIERRE + 0.1), ("pop", "cB", T_CIERRE + 1.0, 1.6), ("slide", "cC", T_CIERRE + 1.6), ("slide", "cD", T_CIERRE + 2.2),
       ("type", "cDt", T_CIERRE + 2.5)]
HITS.append(T_CIERRE + 1.0)

CSS = """
@font-face{font-family:Black;src:url(file://%(black)s)}@font-face{font-family:Mono;src:url(file://%(mono)s)}@font-face{font-family:Serif;src:url(file://%(serif)s)}
:root{--red:#e2262b;--bone:#efe8dc;--ink:#0d0a0b;--panel:#1b1517}
*{box-sizing:border-box;margin:0}
body{width:1080px;height:1920px;overflow:hidden;background:var(--ink);font-family:Black;color:var(--bone)}
.bg{position:absolute;inset:0;opacity:0}
.dark{background:radial-gradient(120%% 70%% at 50%% 38%%,#2a0c0e 0%%,#120a0b 55%%,#070505 100%%)}
.bone{background:radial-gradient(120%% 80%% at 50%% 40%%,#f6f1e8 0%%,#e6ded1 70%%,#cfc5b6 100%%)}
.red{background:radial-gradient(120%% 80%% at 50%% 35%%,#ff3b30 0%%,#d61f24 55%%,#8e0f13 100%%)}
.scene{position:absolute;inset:0;opacity:0}
.stack{position:absolute;left:64px;right:64px;top:0;padding-top:230px;display:flex;flex-direction:column;align-items:flex-start;gap:30px}
.big{font-size:120px;line-height:.92;letter-spacing:-4px;text-transform:uppercase;width:100%%}
.card{position:relative;background:var(--panel);border-radius:30px;border:2px solid rgba(255,255,255,.07);box-shadow:0 40px 80px rgba(0,0,0,.55);overflow:hidden;width:100%%}
.img{height:820px}.photo{position:absolute;inset:-4%%;background-size:cover;background-position:center}
.cam .photo{filter:grayscale(1) contrast(1.25) brightness(1.05)}
.cam::after{content:"";position:absolute;inset:0;background:repeating-linear-gradient(0deg,rgba(0,0,0,.18) 0 2px,transparent 2px 5px)}
.rec{position:absolute;right:26px;top:24px;font-family:Mono;font-size:28px;color:#ff4a3d;opacity:0}
.cam .rec{opacity:1}
.pj{position:absolute;bottom:-6px;transform:translateX(-50%%);opacity:0}
.txt{font-size:74px;line-height:1.02;letter-spacing:-2px;text-transform:uppercase;width:100%%}
.w{display:inline-block;opacity:0}.w.hl{color:var(--red)}
.bone .w,.onbone .w{color:var(--ink)}
.pill{background:var(--red);color:#fff;font-family:Mono;font-size:46px;padding:12px 28px;border-radius:12px;letter-spacing:2px;opacity:0}
.tag{font-family:Mono;font-size:32px;color:#cfc5b6;background:#140f10;border-radius:10px;padding:10px 18px;border:2px solid rgba(255,255,255,.08);opacity:0}
.mono{font-family:Mono}.ch{display:inline-block;white-space:pre}
.brand{display:flex;align-items:center;gap:40px;padding:40px 50px}.coment{padding:24px 36px;background:#140f10}
.ember{position:absolute;border-radius:50%%;background:radial-gradient(circle,rgba(255,70,50,.9),rgba(255,40,30,0) 70%%)}
#prog{position:absolute;right:56px;top:96px;background:#140f10;border:2px solid rgba(255,255,255,.08);border-radius:14px;padding:12px 20px;font-family:Mono;font-size:28px;color:#cfc5b6;display:flex;gap:10px;align-items:center;z-index:50}
#prog .bar{width:20px;height:8px;border-radius:4px;background:#3a3133}#prog .on{background:var(--red)}
#logo{position:absolute;left:56px;top:88px;display:flex;align-items:center;gap:14px;z-index:50;font-size:32px}
#logo .e{width:64px;height:64px}
""" % FONTS

JS = r"""
const TL=%(tl)s, HITS=%(hits)s, END=%(end)s, BST=%(bst)s, CIERRE=%(cierre)s;
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
const EM=[];for(let i=0;i<24;i++){const d=document.createElement('div');d.className='ember';const r=20+((i*37)%%70);d.style.width=d.style.height=r+'px';
 bgs.after(d);EM.push({d,x:(i*157)%%1080,y:(i*331)%%1920,v:18+(i*13)%%40,ph:i*1.7});}
function render(t){
 let curBg='dark';
 TL.forEach(it=>{const [k,id]=it;
  if(k==='scene'){const el=$(id);const [,,a,b,bg]=it;const vis=t>=a-0.01&&t<b;if(!vis){el.style.opacity=0;return;}curBg=bg;
    el.classList.toggle('onbone',bg==='bone');
    const pin=seg(t,a,a+0.22),pout=seg(t,b-0.22,b);tf(el,1-pout,0,0,1+0.04*pout+0.03*(1-eOut(pin)),0,pout*16);return;}
  if(k==='words'){const wt=it[2];wt.forEach((w0,j)=>{const el=$(id+'w'+j);const p=seg(t,w0-0.05,w0+0.3);
    const hl=el.classList.contains('hl');tf(el,clamp(p*2),0,(1-eBack(p))*50,hl?1+0.25*Math.exp(-Math.max(0,t-w0)*6):1,0,(1-p)*10);});return;}
  const el=$(id);if(!el)return;
  if(k==='kin'){const [,,t0]=it;const cs=el.querySelectorAll('.ch');
    for(let i=0;i<cs.length;i++){const p=seg(t,t0+i*0.03,t0+i*0.03+0.5);tf(cs[i],clamp(p*2),0,(1-eBack(p))*90,1,0,(1-p)*14);}}
  else if(k==='pop'){const [,,t0,from=0.6]=it;const p=seg(t,t0,t0+0.45);tf(el,clamp(p*3),0,(1-eOut(p))*40,from+(1-from)*eBack(p),-2,(1-p)*8);}
  else if(k==='slide'){const [,,t0]=it;const p=seg(t,t0,t0+0.55);const e=eExpo(p);tf(el,clamp(p*3),0,120*(1-e),0.94+0.06*e,0,(1-p)*10);}
  else if(k==='type'){const [,,t0]=it;const w=[...el.dataset.word];const n=Math.floor(clamp((t-t0)/Math.max(0.6,w.length*0.07))*w.length);
    el.textContent=w.slice(0,n).join('')+((n<w.length||Math.floor(t*2.4)%%2)?'|':' ');}
  else if(k==='kb'){const [,,a,b,m]=it;const p=seg(t,a,b);const tx=[0,-30,30][m]*p, s=[1.0+0.10*p,1.08-0.06*p,1.03+0.07*p][m];
    el.style.transform=`translateX(${tx}px) scale(${s})`;}
  else if(k==='pj'){const [,,t0,an]=it;const p=seg(t,t0,t0+0.9);let o=p,x=0,y=(1-eOut(p))*40,r=0,s=0.94+0.06*eOut(p),sx=1;
    if(an==='aparece')o=p*((p<1&&Math.floor(t*18)%%3===0)?0.3:1);
    if(an==='camina'){x=(1-eOut(seg(t,t0,t0+1.6)))*-520;y=-Math.abs(Math.sin(t*10))*12*(1-seg(t,t0,t0+1.6));o=seg(t,t0,t0+0.3);}
    if(an==='tiembla'){x=6*Math.sin(t*61);r=0.8*Math.sin(t*47);}
    if(an==='gira'){const q=seg(t,t0,t0+0.6);sx=Math.cos(Math.PI*eOut(q))||0.02;o=1;}
    if(an==='se_acerca')s=0.6+0.6*seg(t,t0,t0+5);
    el.style.opacity=o;el.style.transform=`translateX(calc(-50%% + ${x}px)) translateY(${y+5*Math.sin(t*1.8)}px) scale(${s*sx},${s}) rotate(${r}deg)`;}
 });
 Object.entries(BG).forEach(([k,d])=>d.style.opacity=(k===curBg)?1:0);
 EM.forEach(e=>{const y=((e.y-t*e.v)%%1920+1920)%%1920;e.d.style.transform=`translate(${e.x+30*Math.sin(t*0.6+e.ph)}px,${y}px)`;
  e.d.style.opacity=curBg==='dark'?(0.25+0.25*Math.sin(t*1.3+e.ph)):0;});
 let n=0;BST.forEach((a,k)=>{if(t>=a)n=k+1;});if(t>=CIERRE)n=BST.length;
 document.querySelectorAll('#prog .bar').forEach((b,i)=>b.className='bar'+(i<n?' on':''));$('pn').textContent=n+'/'+BST.length;
 const lg=$('logo');lg.style.opacity=t<CIERRE?1:0;lg.style.color=curBg==='bone'?'#0d0a0b':'#efe8dc';
 lg.querySelector('.lid').setAttribute('height',(t%%3.3)<0.14?84:26);
 let sh=0;HITS.forEach(c=>{const d=t-c;if(d>=0&&d<0.35)sh+=13*Math.exp(-d*12);});
 document.body.style.transform=sh>0.3?`translate(${sh*Math.sin(t*95)}px,${sh*Math.cos(t*80)}px)`:'none';
 document.body.style.opacity=1-seg(t,END-0.8,END);
}
window.render=render;"""

bars = "".join('<span class="bar"></span>' for _ in range(N))
page = f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div id="logo"><div class="e">{EYE}</div><div>SHORTS TERROR</div></div>
<div id="prog">{bars}<span id="pn">0/{N}</span></div>
{''.join(scenes)}
<script>{JS % dict(tl=json.dumps(TL), hits=json.dumps(HITS), end=TOTAL, bst=json.dumps([b["start"] for b in blocks]), cierre=T_CIERRE)}</script></body></html>"""
(TMP / "h.html").write_text(page, encoding="utf-8")


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
    tt = np.arange(int(0.4 * SR)) / SR
    wh = np.convolve(rng.standard_normal(len(tt)), np.ones(25) / 25, mode="same") * np.sin(np.pi * tt / 0.4) ** 2 * 3
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
    for b in blocks:
        for s in b.get("sfx", []):
            ty = s.get("tipo")
            if ty == "golpes":
                for k in range(3):
                    put(knock, b["vstart"] + 0.5 + 0.5 * k, 0.3)
            elif ty == "latido":
                tb = b["start"] + 0.2
                while tb < b["end"]:
                    put(thump, tb, 0.25)
                    put(thump, tb + 0.22, 0.15)
                    tb += 0.8
            elif ty == "telefono":
                put(ring, b["vstart"], 0.1)
            elif ty == "respiracion":
                put(br, b["vstart"] + 0.3, 0.12)
            elif ty == "golpe_final":
                put(hit, b["vstart"] + b["vd"] + 0.1, 0.6)
    for h in HITS:
        put(hit[:int(0.6 * SR)], h, 0.2)
    mix[-int(1.0 * SR):] *= np.linspace(1, 0, int(1.0 * SR))
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.9
    p = TMP / "mix.wav"
    with wave.open(str(p), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((np.stack([mix, mix], 1) * 32767).astype(np.int16).tobytes())
    return p


if __name__ == "__main__":
    wav = build_audio()
    NF = int(TOTAL * FPS)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "image2pipe", "-c:v", "mjpeg", "-r", str(FPS), "-i", "-",
           "-i", str(wav), "-map", "0:v", "-map", "1:a", "-vf", "noise=alls=4:allf=t+u,format=yuv420p",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-af", "loudnorm=I=-14:TP=-1.5:LRA=9",
           "-c:a", "aac", "-b:a", "192k", "-t", f"{TOTAL:.2f}", "-movflags", "+faststart", str(OUT)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        pg = br.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto((TMP / "h.html").as_uri(), wait_until="load")
        pg.evaluate("document.fonts.ready.then(()=>1)")
        for f in range(NF):
            pg.evaluate(f"render({f / FPS:.4f})")
            proc.stdin.write(pg.screenshot(type="jpeg", quality=92))
        br.close()
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg falló")
    print("OK", OUT, f"{OUT.stat().st_size / 1e6:.1f} MB", flush=True)
