"""Radar del terror en estilo motion design (plantilla genérica, se rellena desde historia.json).
HTML/CSS animado por tiempo y capturado fotograma a fotograma con Chrome (Playwright), sincronizado con la voz.

Uso: python3 -I tools/radar_motion.py radar/<ID> salida.mp4
Necesita: historia.json (formato "radar"), voces/completa.mp3 e imgs/escena_N.jpg (+ personaje_<id>.png).
Formato de escenas/elementos: docs/INSTRUCCIONES_RADAR.md"""
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
TMP = Path(tempfile.mkdtemp(prefix="radarm_"))
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


def at(phrase, default=None):
    k = TEXTO.lower().find(phrase.lower()) if phrase else -1
    if k < 0:
        if default is None:
            raise SystemExit(f"Frase no encontrada en el texto: «{phrase}»")
        return default
    target, acc = k / len(TEXTO) * SPEECH, 0.0
    for a, b in SPANS:
        if acc + (b - a) >= target:
            return round(a + (target - acc), 3)
        acc += b - a
    return SPANS[-1][1]


esc = lambda s: H_.escape(str(s))
FONTS = {"black": "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf",
         "mono": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
         "serif": "/usr/share/fonts/truetype/google-fonts/Lora-Variable.ttf"}
EYE = """<svg viewBox="0 0 120 120" width="100%" height="100%"><circle cx="60" cy="60" r="55" fill="#e2262b" stroke="#efe8dc" stroke-width="7"/>
<path d="M18 60 Q60 20 102 60 Q60 100 18 60Z" fill="#efe8dc"/><circle class="pupil" cx="60" cy="60" r="16" fill="#0d0a0b"/>
<rect class="lid" x="10" y="14" width="100" height="26" fill="#e2262b"/></svg>"""

# Marca: "terror" (Shorts Terror España, por defecto) o "radar_viral" (Radar Viral: lo más buscado del día, para TikTok)
VIRAL = H.get("marca") == "radar_viral"
RADAR = """<svg viewBox="0 0 120 120" width="100%" height="100%"><defs><linearGradient id="rg" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#22d3ee"/><stop offset="1" stop-color="#ff2d78"/></linearGradient></defs>
<circle cx="60" cy="60" r="55" fill="#0b1326" stroke="url(#rg)" stroke-width="7"/>
<circle cx="60" cy="60" r="38" fill="none" stroke="#22d3ee" stroke-opacity=".45" stroke-width="3"/>
<circle cx="60" cy="60" r="21" fill="none" stroke="#22d3ee" stroke-opacity=".45" stroke-width="3"/>
<g class="sweep"><path d="M60 60 L60 7 A53 53 0 0 1 106 34 Z" fill="#22d3ee" fill-opacity=".28"/></g>
<path d="M51 44 L77 60 L51 76 Z" fill="#ff2d78"/><circle class="pupil" cx="60" cy="60" r="0"/><rect class="lid" width="0" height="0"/></svg>"""
if VIRAL:
    EYE = RADAR
MARCA1, MARCA2 = ("RADAR VIRAL", "LO MÁS BUSCADO HOY") if VIRAL else ("SHORTS TERROR", "ESPAÑA")

# ---------------------------------------------------------------- escenas -> HTML + línea de tiempo
FONDOS = ["dark", "dark", "red", "dark", "bone", "dark", "red", "dark"]
escenas = H["escenas"]
T_CIERRE = at(H.get("cierre_desde", "Si quieres"))
TOTAL = round(VDUR + 1.3, 2)
starts = [0.0] + [at(e["desde"]) for e in escenas[1:]]
bounds = starts + [T_CIERRE]
num_total = sum(1 for e in escenas if e.get("etiqueta"))
scenes_html, timeline, hits, n_count, prog = [], [], [], 0, []
for i, e in enumerate(escenas):
    a, b = bounds[i], bounds[i + 1]
    fondo = e.get("fondo") or FONDOS[i % len(FONDOS)]
    txtcol = {"dark": "var(--bone)", "red": "#fff", "bone": "var(--ink)"}[fondo]
    acc = {"dark": "var(--red)", "red": "var(--ink)", "bone": "var(--red)"}[fondo]
    if e.get("etiqueta"):
        n_count += 1
        prog.append((a, n_count))
    items = []
    if e.get("etiqueta"):
        items.append(f'<div class="label" id="e{i}_lab" style="color:{acc if fondo != "dark" else "var(--red)"}">{esc(e["etiqueta"])}</div>')
        timeline.append(("pop", f"e{i}_lab", a + 0.05))
    img = (D / "imgs" / f"escena_{i}.jpg")
    for j, el in enumerate(e.get("elementos", [])):
        eid, tipo = f"e{i}_{j}", el["tipo"]
        t0 = at(el["en"]) if el.get("en") else a + 0.1 + 0.25 * j
        if tipo in ("titulo", "subtitulo", "desaparece"):
            cls = "big" if tipo != "subtitulo" else "mid"
            col = {"rojo": acc, "acento": acc}.get(el.get("color", ""), txtcol)
            size = el.get("tam")
            st = f"color:{col};" + (f"font-size:{int(size)}px;" if size else "")
            if tipo == "titulo" and not size and len(el["texto"]) > 14:
                st += "font-size:120px;"
            items.append(f'<div class="{cls}" id="{eid}" data-k style="{st}">{esc(el["texto"].upper())}</div>')
            timeline.append(("kin", eid, t0 - 0.1, (t0 + 1.0) if tipo == "desaparece" else None))
            if el.get("golpe") or tipo == "titulo" and j == 0:
                hits.append(t0)
        elif tipo == "busqueda":
            items.append(f'<div class="card search" id="{eid}"><div class="lupa"></div><div class="lupa2"></div>'
                         f'<div class="mono ink typed" id="{eid}_t" data-word="{esc(el["texto"])}"></div></div>')
            timeline.append(("slide", eid, t0))
            timeline.append(("type", eid + "_t", t0 + 0.25))
        elif tipo in ("sello", "pill"):
            items.append(f'<div class="pill" id="{eid}">{esc(el["texto"].upper())}</div>')
            timeline.append(("pop", eid, t0, 1.6))
            hits.append(t0)
        elif tipo == "tag":
            items.append(f'<div class="tag" id="{eid}">{esc(el["texto"].upper())}</div>')
            timeline.append(("pop", eid, t0))
        elif tipo == "fecha":
            items.append(f'<div class="card cal" id="{eid}"><div class="calh">{esc(el.get("mes", "").upper())}</div>'
                         f'<div class="caln">{esc(el["dia"])}</div><svg class="calr" width="350" height="350"><circle id="{eid}_r" cx="175" cy="175" r="150" fill="none" '
                         f'stroke="#e2262b" stroke-width="16" stroke-linecap="round" stroke-dasharray="943" stroke-dashoffset="943" transform="rotate(-90 175 175)"/></svg>'
                         f'<div class="calf">{esc(el.get("etiqueta", "").upper())}</div></div>')
            timeline.append(("slide", eid, t0 - 0.3))
            timeline.append(("ring", eid + "_r", t0 + 0.1, 943, 1.0))
            hits.append(t0)
        elif tipo == "dato":
            v = float(el["valor"])
            items.append(f'<div class="card dato" id="{eid}"><svg class="dr" width="400" height="400"><circle cx="200" cy="200" r="165" fill="none" stroke="#3a3133" stroke-width="26"/>'
                         f'<circle id="{eid}_r" cx="200" cy="200" r="165" fill="none" stroke="#e2262b" stroke-width="26" stroke-linecap="round" stroke-dasharray="1037" stroke-dashoffset="1037" transform="rotate(-90 200 200)"/></svg>'
                         f'<div class="dn" id="{eid}_n">0</div><div class="mono dl">{esc(el.get("etiqueta", "").upper())}</div></div>')
            frac = min(1.0, v / 100) if el.get("sufijo", "") == "%" else 1.0
            timeline.append(("slide", eid, t0 - 0.4))
            timeline.append(("ring", eid + "_r", t0 - 0.1, 1037, frac))
            timeline.append(("count", eid + "_n", t0 - 0.1, v, el.get("sufijo", "")))
            hits.append(t0)
        elif tipo == "imagen":
            src = img.as_uri() if img.exists() else ""
            pj = ""
            for k, p in enumerate(el.get("personajes", [])):
                pp = D / "imgs" / f"personaje_{p['quien']}.png"
                if pp.exists():
                    pj += f'<img class="pj" id="{eid}_p{k}" src="{pp.as_uri()}" style="height:{int(float(p.get("alto", 0.9)) * 100)}%">'
                    timeline.append(("pj", f"{eid}_p{k}", at(p["en"]) if p.get("en") else t0 + 0.4, p.get("anim", "aparece")))
            alto = int(el.get("alto", 620))
            items.append(f'<div class="card img" id="{eid}" style="height:{alto}px"><div class="photo" id="{eid}_ph" style="background-image:url({src})"></div>{pj}'
                         + (f'<div class="tag over">{esc(el["pie"].upper())}</div>' if el.get("pie") else "") + '</div>')
            timeline.append(("slide", eid, t0))
            timeline.append(("kb", eid + "_ph", a, b))
        elif tipo == "tarjeta":
            items.append(f'<div class="card tarj" id="{eid}"><div class="tt">{esc(el.get("titulo", "").upper())}</div><div class="tx">{esc(el.get("texto", ""))}</div></div>')
            timeline.append(("slide", eid, t0, -300 if j % 2 else 300, 0))
    scenes_html.append(f'<div class="scene" id="sc{i}"><div class="stack">{"".join(items)}</div></div>')
    timeline.insert(0, ("scene", f"sc{i}", a, b, fondo))
for k in starts[1:] + [T_CIERRE]:
    hits.append(None)  # marcador (los whoosh se calculan aparte)
cierre = H.get("cierre", {})
com = cierre.get("comentario", "¿Lo sabías? 👇")
scenes_html.append(f"""<div class="scene" id="scC"><div class="stack" style="padding-top:300px">
 <div class="big" id="cA" data-k style="font-size:170px">SÍGUEME</div>
 <div class="mid red" id="cB" data-k>{esc(cierre.get("lema", "LO MÁS BUSCADO DE CADA DÍA" if VIRAL else "PARA EL TERROR DEL DÍA").upper())}</div>
 <div class="card brand" id="cC"><div style="width:180px;height:180px;flex:none">{EYE}</div>
  <div><div style="font-size:78px;line-height:.95">{MARCA1}</div><div style="font-family:{"Mono" if VIRAL else "Serif"};font-size:{38 if VIRAL else 48}px;letter-spacing:{4 if VIRAL else 14}px;color:{"#22d3ee" if VIRAL else "var(--red)"}">{MARCA2}</div></div></div>
 <div class="card coment" id="cD"><div class="mono" style="font-size:28px;color:#8d8386">comentario</div><div class="mono" style="font-size:48px;margin-top:8px" id="cDt" data-word="{esc(com)}"></div></div>
</div></div>""")
T_SIG = at("sígueme", T_CIERRE + 1.2)
T_STE = at("Radar Viral" if VIRAL else "Shorts Terror", T_CIERRE + 2.0)
timeline.insert(0, ("scene", "scC", T_CIERRE, 999, "dark"))
timeline += [("kin", "cA", T_CIERRE + 0.05, None), ("kin", "cB", T_CIERRE + 0.45, None), ("slide", "cC", T_STE - 0.3),
             ("slide", "cD", T_STE + 0.4), ("type", "cDt", T_STE + 0.7)]
hits = [h for h in hits if h is not None] + [T_CIERRE]

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
.stack{position:absolute;left:70px;right:70px;top:0;padding-top:330px;display:flex;flex-direction:column;align-items:flex-start;gap:26px}
.big{font-size:150px;line-height:.9;letter-spacing:-5px;text-transform:uppercase;width:100%%}
.mid{font-size:80px;line-height:.95;letter-spacing:-2px;text-transform:uppercase;width:100%%}
.mid.red{background:none;color:var(--red)}
.label{font-family:Mono;font-size:36px;letter-spacing:3px;color:var(--red)}
.card{position:relative;background:var(--panel);border-radius:30px;border:2px solid rgba(255,255,255,.07);box-shadow:0 40px 80px rgba(0,0,0,.55);overflow:hidden;width:100%%}
.pill{background:var(--red);color:#fff;font-family:Mono;font-size:42px;padding:12px 26px;border-radius:12px;letter-spacing:1px}
.tag{font-family:Mono;font-size:32px;color:#cfc5b6;background:#140f10;border-radius:10px;padding:10px 18px;border:2px solid rgba(255,255,255,.08)}
.tag.over{position:absolute;left:28px;bottom:28px}
.mono{font-family:Mono}.ink{color:var(--ink)}
.ch{display:inline-block;white-space:pre}
.photo{position:absolute;inset:0;background-size:cover;background-position:center}
.pj{position:absolute;left:50%%;bottom:-8px;transform:translateX(-50%%);opacity:0}
.search{height:150px;background:#efe8dc}.lupa{position:absolute;left:46px;top:42px;width:58px;height:58px;border:9px solid #6b6266;border-radius:50%%}
.lupa2{position:absolute;left:92px;top:92px;width:30px;height:9px;background:#6b6266;transform:rotate(45deg);border-radius:4px}
.typed{position:absolute;left:150px;top:46px;font-size:52px}
.cal{width:520px;height:600px}.calh{height:120px;background:var(--red);display:flex;align-items:center;justify-content:center;font-size:62px;color:#fff}
.caln{position:absolute;top:150px;left:0;right:0;text-align:center;font-size:290px;line-height:1}.calr{position:absolute;left:85px;top:140px}
.calf{position:absolute;bottom:26px;left:0;right:0;text-align:center;font-family:Mono;font-size:30px;color:#cfc5b6}
.dato{height:520px}.dr{position:absolute;left:40px;top:60px}.dn{position:absolute;left:40px;top:60px;width:400px;height:400px;display:flex;align-items:center;justify-content:center;font-size:130px}
.dl{position:absolute;left:480px;top:150px;right:30px;font-size:40px;color:#cfc5b6;line-height:1.5}
.tarj{padding:40px 46px}.tarj .tt{font-size:64px;color:var(--red);line-height:1}.tarj .tx{font-family:Mono;font-size:40px;color:#cfc5b6;margin-top:16px;line-height:1.35}
.brand{display:flex;align-items:center;gap:40px;padding:40px 50px}.coment{padding:24px 36px;background:#140f10}
.ember{position:absolute;border-radius:50%%;background:radial-gradient(circle,rgba(255,70,50,.9),rgba(255,40,30,0) 70%%)}
#prog{position:absolute;right:56px;top:96px;background:#140f10;border:2px solid rgba(255,255,255,.08);border-radius:14px;padding:12px 20px;font-family:Mono;font-size:30px;color:#cfc5b6;display:flex;gap:14px;align-items:center;z-index:50}
#prog .bar{width:28px;height:8px;border-radius:4px;background:#3a3133}#prog .on{background:var(--red)}
#logo{position:absolute;left:56px;top:92px;display:flex;align-items:center;gap:16px;z-index:50;font-size:34px}
#mascot{position:absolute;width:150px;height:150px;z-index:40}
""" % FONTS

JS = r"""
const TL=%(tl)s, PROG=%(prog)s, NTOT=%(ntot)d, HITS=%(hits)s, END=%(end)s;
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
const EM=[];for(let i=0;i<26;i++){const d=document.createElement('div');d.className='ember';const r=20+((i*37)%%70);d.style.width=d.style.height=r+'px';
 bgs.after(d);EM.push({d,x:(i*157)%%1080,y:(i*331)%%1920,v:18+(i*13)%%40,ph:i*1.7});}
function render(t){
 let curBg='dark';
 TL.forEach(it=>{const [k,id]=it;const el=$(id);if(!el)return;
  if(k==='scene'){const [,,a,b,bg]=it;const vis=t>=a-0.01&&t<b;if(!vis){el.style.opacity=0;return;}curBg=bg;
    const pin=seg(t,a,a+0.22),pout=seg(t,b-0.22,b);tf(el,1-pout,0,0,1+0.04*pout+0.03*(1-eOut(pin)),0,pout*16);}
  else if(k==='kin'){const [,,t0,van]=it;const cs=el.querySelectorAll('.ch');
    for(let i=0;i<cs.length;i++){const p=seg(t,t0+i*0.03,t0+i*0.03+0.5);let o=clamp(p*2),y=(1-eBack(p))*90,b=(1-p)*14;
      if(van!==null){const q=seg(t,van+i*0.07,van+i*0.07+0.35);o*=1-q;y-=q*40;b+=q*10;}tf(cs[i],o,0,y,1,0,b);}}
  else if(k==='pop'){const [,,t0,from=0.6]=it;const p=seg(t,t0,t0+0.45);tf(el,clamp(p*3),0,(1-eOut(p))*40,from+(1-from)*eBack(p),0,(1-p)*8);}
  else if(k==='slide'){const [,,t0,dx=0,dy=120]=it;const p=seg(t,t0,t0+0.55);const e=eExpo(p);tf(el,clamp(p*3),dx*(1-e),dy*(1-e),0.94+0.06*e,0,(1-p)*10);}
  else if(k==='type'){const [,,t0]=it;const w=[...el.dataset.word];const n=Math.floor(clamp((t-t0)/Math.max(0.6,w.length*0.07))*w.length);
    el.textContent=w.slice(0,n).join('')+((n<w.length||Math.floor(t*2.4)%%2)?'|':' ');}
  else if(k==='ring'){const [,,t0,L,f]=it;el.style.strokeDashoffset=L*(1-f*eOut(seg(t,t0,t0+1.0)));}
  else if(k==='count'){const [,,t0,v,suf]=it;const c=v*eOut(seg(t,t0,t0+1.0));el.textContent=(Number.isInteger(v)?Math.round(c):c.toFixed(1).replace('.',','))+suf;}
  else if(k==='kb'){const [,,a,b]=it;el.style.transform=`scale(${1.04+0.08*seg(t,a,b)}) translateY(${-14*seg(t,a,b)}px)`;}
  else if(k==='pj'){const [,,t0,an]=it;const p=seg(t,t0,t0+0.9);let o=p,x=0,y=(1-eOut(p))*40,r=0,s=0.92+0.08*eOut(p);
    if(an==='aparece')o=p*((p<1&&Math.floor(t*18)%%3===0)?0.3:1);
    if(an==='tiembla'){x=6*Math.sin(t*61);r=0.8*Math.sin(t*47);}
    if(an==='camina'){x=(1-eOut(p))*-500;y=-Math.abs(Math.sin(t*10))*10*(1-p);}
    if(an==='se_acerca'){s=0.6+0.5*seg(t,t0,t0+5);}
    el.style.opacity=o;el.style.transform=`translateX(calc(-50%% + ${x}px)) translateY(${y+4*Math.sin(t*1.8)}px) scale(${s}) rotate(${r}deg)`;}
 });
 Object.entries(BG).forEach(([k,d])=>d.style.opacity=(k===curBg)?1:0);
 EM.forEach(e=>{const y=((e.y-t*e.v)%%1920+1920)%%1920;e.d.style.transform=`translate(${e.x+30*Math.sin(t*0.6+e.ph)}px,${y}px)`;
  e.d.style.opacity=curBg==='dark'?(0.25+0.25*Math.sin(t*1.3+e.ph)):0;});
 let n=0;PROG.forEach(([a,k])=>{if(t>=a)n=k;});
 document.querySelectorAll('#prog .bar').forEach((b,i)=>b.className='bar'+(i<n?' on':''));$('pn').textContent=n+'/'+NTOT;
 const m=$('mascot');tf(m,t<END-1.5?1:0,870,1460+10*Math.sin(t*2.2),1,4*Math.sin(t*1.3));
 m.querySelector('.lid').setAttribute('height',(t%%3.1)<0.14?84:26);m.querySelector('.pupil').setAttribute('cx',60+8*Math.sin(t*0.9));
 let sh=0;HITS.forEach(c=>{const d=t-c;if(d>=0&&d<0.35)sh+=12*Math.exp(-d*12);});
 document.body.style.transform=sh>0.3?`translate(${sh*Math.sin(t*95)}px,${sh*Math.cos(t*80)}px)`:'none';
 document.body.style.opacity=1-seg(t,END-0.8,END);
}
window.render=render;"""

bars = "".join('<span class="bar"></span>' for _ in range(max(1, num_total)))
page = f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div id="prog">{bars}<span id="pn">0/{num_total}</span></div>
{''.join(scenes_html)}
<div id="mascot">{EYE}</div>
<script>{JS % dict(tl=json.dumps(timeline), prog=json.dumps(prog), ntot=max(1, num_total), hits=json.dumps(hits), end=TOTAL)}</script></body></html>"""
if VIRAL:  # paleta Radar Viral: azul noche, rosa y cian
    for a_, b_ in {"#e2262b": "#ff2d78", "#efe8dc": "#eef4ff", "#0d0a0b": "#070b16", "#1b1517": "#111a2e", "#140f10": "#0b1326",
                   "#2a0c0e": "#12285a", "#120a0b": "#0a1532", "#070505": "#040812", "#ff3b30": "#ff4f93", "#d61f24": "#e0186a",
                   "#8e0f13": "#7a0b3b", "#f6f1e8": "#f4f8ff", "#e6ded1": "#e2eaf8", "#cfc5b6": "#c3cee6", "#3a3133": "#26314d",
                   "#6b6266": "#5d6a86", "#8d8386": "#7f8aa5", "rgba(255,70,50,.9)": "rgba(34,211,238,.75)",
                   "rgba(255,40,30,0)": "rgba(34,211,238,0)"}.items():
        page = page.replace(a_, b_)
    page = page.replace("m.querySelector('.lid')", "m.querySelector('.sweep').setAttribute('transform',`rotate(${(t*140)%%360} 60 60)`);m.querySelector('.lid')".replace("%%", "%"))
page_path = TMP / "radar.html"
page_path.write_text(page, encoding="utf-8")


def build_audio():
    rng = np.random.default_rng(3)
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(VOZ), "-af", "highpass=f=60", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"])
    v = np.frombuffer(raw, np.float32)
    N = int((TOTAL + 0.3) * SR)
    mix = np.zeros(N, np.float32)
    mix[:min(N, len(v))] += v[:N] / (np.abs(v).max() + 1e-9) * 0.85
    x = np.arange(N, dtype=np.float32) / SR
    if VIRAL:
        beat = 60 / 112
        kt = np.arange(int(0.25 * SR)) / SR
        kick = np.sin(2 * np.pi * np.cumsum(55 + 90 * np.exp(-kt * 30)) / SR) * np.exp(-kt * 14)
        tick = np.convolve(rng.standard_normal(int(0.05 * SR)), [1, -1], mode="same") * np.exp(-np.arange(int(0.05 * SR)) / SR * 90)
        k = 0
        while k * beat < TOTAL - 1:
            i0 = int(k * beat * SR)
            n = min(len(kick), N - i0)
            mix[i0:i0 + n] += kick[:n].astype(np.float32) * 0.07
            i1 = int((k + 0.5) * beat * SR)
            n = min(len(tick), N - i1)
            if n > 0:
                mix[i1:i1 + n] += tick[:n].astype(np.float32) * 0.03
            k += 1
        mix += (0.02 * np.sin(2 * np.pi * 220 * x) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * x))).astype(np.float32)
    else:
        mix += (0.045 * np.sin(2 * np.pi * 55 * x) + 0.025 * np.sin(2 * np.pi * 110 * x) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.1 * x))).astype(np.float32)

    def put(sig, t0, g):
        i = int(t0 * SR)
        if 0 <= i < N:
            n = min(len(sig), N - i)
            mix[i:i + n] += sig[:n].astype(np.float32) * g

    tt = np.arange(int(0.4 * SR)) / SR
    wh = np.convolve(rng.standard_normal(len(tt)), np.ones(25) / 25, mode="same") * np.sin(np.pi * tt / 0.4) ** 2 * 3
    th = np.arange(int(1.0 * SR)) / SR
    ph = 2 * np.pi * np.cumsum(75 * np.exp(-th * 1.4)) / SR
    hit = ((np.sin(ph) + 0.5 * np.sin(2 * ph)) * np.exp(-th * 3.5) + rng.standard_normal(len(th)) * np.exp(-th * 30) * 0.4) * (1 - np.exp(-th * 900))
    for h in hits:
        put(hit, h, 0.18 if VIRAL else 0.3)
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
    print(f"Duración {TOTAL:.1f} s · escenas {[round(s, 1) for s in starts]} · cierre {T_CIERRE:.1f}", flush=True)
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
        pg.goto(page_path.as_uri(), wait_until="load")
        pg.evaluate("document.fonts.ready.then(()=>1)")
        for f in range(NF):
            pg.evaluate(f"render({f / FPS:.4f})")
            proc.stdin.write(pg.screenshot(type="jpeg", quality=92))
        br.close()
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg falló")
    print("OK", OUT, f"{OUT.stat().st_size / 1e6:.1f} MB", flush=True)
