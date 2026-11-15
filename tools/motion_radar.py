"""Radar del terror en estilo «motion design» (tipografía cinética, como los reels de Remotion/GSAP).
Se dibuja en HTML/CSS y se captura fotograma a fotograma con Chrome (Playwright), sincronizado con la voz.

Uso: python3 -I tools/motion_radar.py radar/<ID> salida.mp4"""
import json
import math
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
TMP = Path(tempfile.mkdtemp(prefix="motion_"))
VOZ = D / "voces" / "completa.mp3"
VDUR = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(VOZ)]))
TEXTO = H["texto"]


# ---------------------------------------------------------------- tiempos de cada frase en la voz
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


def at(phrase):
    k = TEXTO.lower().find(phrase.lower())
    if k < 0:
        raise SystemExit(f"Frase no encontrada en el texto: {phrase}")
    target, acc = k / len(TEXTO) * SPEECH, 0.0
    for a, b in SPANS:
        if acc + (b - a) >= target:
            return round(a + (target - acc), 3)
        acc += b - a
    return SPANS[-1][1]


C = {k: at(v) for k, v in {
    "por": "Por qué", "vp": "Victorian Psycho", "s1": "Porque este viernes", "v13": "viernes trece", "cines": "los cines",
    "nov": "novela española", "s2": "La escribió", "vf": "Virginia Feito", "hw": "Hollywood", "s3": "Maika Monroe",
    "long": "Longlegs", "win": "es Winifred", "inst": "una institutriz", "xix": "siglo diecinueve", "poco": "poco a poco",
    "desap": "desaparecer", "s4": "La comparan", "ap": "American Psycho", "te": "tacitas", "s5": "En Rotten Tomatoes",
    "p74": "setenta y cuatro", "jn": "Jack Nicholson", "res": "El resplandor", "s6": "Si quieres", "sig": "sígueme",
    "ste": "Esto es Shorts"}.items()}
C["end"] = round(VDUR + 1.3, 2)
TOTAL = C["end"]
print("Marcas:", C, flush=True)

IM = {i: (D / "imgs" / f"escena_{i}.jpg").as_uri() for i in range(6)}
GOV = (D / "imgs" / "personaje_institutriz.png").as_uri()
FONTS = {"black": "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf",
         "mono": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
         "pop": "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf",
         "popm": "/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf",
         "serif": "/usr/share/fonts/truetype/google-fonts/Lora-Variable.ttf"}

EYE = """<svg viewBox="0 0 120 120" width="100%" height="100%"><circle cx="60" cy="60" r="56" fill="#e2262b" stroke="#0d0a0b" stroke-width="6"/>
<path d="M18 60 Q60 20 102 60 Q60 100 18 60Z" fill="#efe8dc"/><circle class="pupil" cx="60" cy="60" r="16" fill="#0d0a0b"/>
<rect class="lid" x="10" y="14" width="100" height="26" fill="#e2262b"/></svg>"""

HTML = r"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:Black;src:url(file://%(black)s)}
@font-face{font-family:Mono;src:url(file://%(mono)s)}
@font-face{font-family:Pop;src:url(file://%(pop)s)}
@font-face{font-family:PopM;src:url(file://%(popm)s)}
@font-face{font-family:Serif;src:url(file://%(serif)s)}
:root{--red:#e2262b;--bone:#efe8dc;--ink:#0d0a0b;--panel:#1b1517}
*{box-sizing:border-box;margin:0}
body{width:1080px;height:1920px;overflow:hidden;background:var(--ink);font-family:Black;color:var(--bone)}
.bg{position:absolute;inset:0}
.dark{background:radial-gradient(120%% 70%% at 50%% 38%%,#2a0c0e 0%%,#120a0b 55%%,#070505 100%%)}
.boneb{background:radial-gradient(120%% 80%% at 50%% 40%%,#f6f1e8 0%%,#e6ded1 70%%,#cfc5b6 100%%)}
.redb{background:radial-gradient(120%% 80%% at 50%% 35%%,#ff3b30 0%%,#d61f24 55%%,#8e0f13 100%%)}
.scene{position:absolute;inset:0;margin-top:120px;opacity:0;will-change:transform,opacity,filter}
.big{position:absolute;left:70px;right:60px;font-size:150px;line-height:.9;letter-spacing:-5px;text-transform:uppercase}
.mid{position:absolute;left:72px;right:60px;font-size:78px;line-height:.95;letter-spacing:-2px;text-transform:uppercase}
.label{position:absolute;left:76px;font-family:Mono;font-size:36px;letter-spacing:3px;color:var(--red)}
.card{position:absolute;background:var(--panel);border-radius:30px;border:2px solid rgba(255,255,255,.07);
 box-shadow:0 40px 80px rgba(0,0,0,.55);overflow:hidden}
.pill{position:absolute;background:var(--red);color:#fff;font-family:Mono;font-size:38px;padding:12px 26px;border-radius:12px;letter-spacing:1px}
.mono{font-family:Mono}
.ch{display:inline-block;white-space:pre;will-change:transform,opacity,filter}
.red{color:var(--red)} .ink{color:var(--ink)}
.photo{position:absolute;inset:0;background-size:cover;background-position:center}
.ember{position:absolute;border-radius:50%%;background:radial-gradient(circle,rgba(255,70,50,.9),rgba(255,40,30,0) 70%%)}
#prog{position:absolute;right:56px;top:96px;background:#140f10;border:2px solid rgba(255,255,255,.08);border-radius:14px;
 padding:12px 20px;font-family:Mono;font-size:30px;color:#cfc5b6;display:flex;gap:14px;align-items:center;z-index:50}
#prog .bar{width:28px;height:8px;border-radius:4px;background:#3a3133}
#prog .on{background:var(--red)}
.eye{position:absolute;width:150px;height:150px;z-index:40}
.tag{position:absolute;font-family:Mono;font-size:30px;color:#cfc5b6;background:#140f10;border-radius:10px;padding:10px 18px;border:2px solid rgba(255,255,255,.08)}
</style></head><body>
<div id="bgs"></div><div id="embers"></div>
<div id="prog"><span class="bar"></span><span class="bar"></span><span class="bar"></span><span class="bar"></span><span class="bar"></span><span id="pn">0/5</span></div>

<!-- 0 · gancho -->
<div class="scene" id="sc0">
 <div class="label" style="top:250px" id="l0">RADAR DEL TERROR · HOY</div>
 <div class="big" style="top:320px;font-size:118px" id="t0a" data-k>¿POR QUÉ TODOS HABLAN DE</div>
 <div class="big red" style="top:690px;font-size:132px" id="t0b" data-k>VICTORIAN PSYCHO?</div>
 <div class="card" style="left:70px;right:70px;top:1010px;height:150px;background:#efe8dc" id="search">
  <div style="position:absolute;left:46px;top:42px;width:58px;height:58px;border:9px solid #6b6266;border-radius:50%%"></div>
  <div style="position:absolute;left:92px;top:92px;width:30px;height:9px;background:#6b6266;transform:rotate(45deg);border-radius:4px"></div>
  <div class="mono ink" style="position:absolute;left:150px;top:46px;font-size:52px" id="typed"></div>
 </div>
 <div class="pill" style="left:70px;top:1220px" id="tend">● TENDENCIA HOY</div>
</div>

<!-- 1 · estreno -->
<div class="scene" id="sc1">
 <div class="label" style="top:250px">01 · ESTRENO</div>
 <div class="big" style="top:320px" id="t1a" data-k>VIERNES</div>
 <div class="card" style="left:70px;top:470px;width:520px;height:560px" id="cal">
  <div style="height:120px;background:var(--red);display:flex;align-items:center;justify-content:center;font-size:62px;color:#fff">NOVIEMBRE</div>
  <div style="position:absolute;top:150px;left:0;right:0;text-align:center;font-size:300px;line-height:1">13</div>
  <svg style="position:absolute;left:85px;top:145px" width="350" height="350"><circle id="ring13" cx="175" cy="175" r="155" fill="none" stroke="#e2262b" stroke-width="16" stroke-linecap="round" stroke-dasharray="974" stroke-dashoffset="974" transform="rotate(-90 175 175)"/></svg>
 </div>
 <div class="card" style="left:630px;top:470px;width:380px;height:560px" id="cine"><div class="photo" style="background-image:url(%(im1)s)"></div></div>
 <div class="mid" style="top:1080px" id="t1b" data-k>EN CINES DE EE. UU.</div>
 <div class="pill" style="left:70px;top:1210px;font-size:46px" id="novela">NOVELA ESPAÑOLA ✓</div>
</div>

<!-- 2 · autora -->
<div class="scene" id="sc2">
 <div class="label" style="top:250px;color:#fff">02 · LA AUTORA</div>
 <div class="big" style="top:320px;color:#fff" id="t2a" data-k>VIRGINIA</div>
 <div class="big ink" style="top:455px" id="t2b" data-k>FEITO</div>
 <div class="card" style="left:70px;right:70px;top:650px;height:520px" id="libro"><div class="photo" style="background-image:url(%(im2)s)"></div>
  <div class="tag" style="left:30px;bottom:30px;font-size:34px" id="esp">ESCRITORA ESPAÑOLA</div></div>
 <div class="mid" style="top:1230px;color:#fff" id="t2c" data-k>YA TRIUNFA EN HOLLYWOOD</div>
</div>

<!-- 3 · protagonista -->
<div class="scene" id="sc3">
 <div class="label" style="top:250px">03 · LA PROTAGONISTA</div>
 <div class="big" style="top:320px;font-size:120px" id="t3a" data-k>MAIKA MONROE</div>
 <div class="tag" style="left:76px;top:450px" id="longl">DE «LONGLEGS»</div>
 <div class="card" style="left:70px;right:70px;top:540px;height:720px" id="hall"><div class="photo" id="hallp" style="background-image:url(%(im3)s)"></div>
  <img id="gov" src="%(gov)s" style="position:absolute;left:50%%;bottom:-10px;height:640px;transform:translateX(-50%%)"></div>
 <div class="pill" style="left:70px;top:1300px" id="winif">ES WINIFRED</div>
 <div class="tag" style="left:420px;top:1306px;font-size:34px" id="inst">INSTITUTRIZ · SIGLO XIX</div>
 <div class="big red" style="top:1420px;font-size:116px" id="t3d" data-k>DESAPARECEN</div>
</div>

<!-- 4 · comparación -->
<div class="scene" id="sc4">
 <div class="label" style="top:250px">LA COMPARAN CON</div>
 <div class="big ink" style="top:320px;font-size:136px" id="t4a" data-k>AMERICAN PSYCHO</div>
 <div class="mid red" style="top:620px;font-size:96px" id="t4b" data-k>…CON TACITAS DE TÉ</div>
 <div class="card" style="left:70px;right:70px;top:800px;height:600px" id="te"><div class="photo" style="background-image:url(%(im4)s)"></div></div>
</div>

<!-- 5 · crítica + inspiración -->
<div class="scene" id="sc5">
 <div class="label" style="top:250px">04 · LA CRÍTICA</div>
 <div class="card" style="left:70px;right:70px;top:320px;height:520px" id="rt">
  <svg style="position:absolute;left:40px;top:60px" width="400" height="400"><circle cx="200" cy="200" r="170" fill="none" stroke="#3a3133" stroke-width="26"/>
   <circle id="ring74" cx="200" cy="200" r="170" fill="none" stroke="#e2262b" stroke-width="26" stroke-linecap="round" stroke-dasharray="1068" stroke-dashoffset="1068" transform="rotate(-90 200 200)"/></svg>
  <div style="position:absolute;left:40px;top:60px;width:400px;height:400px;display:flex;align-items:center;justify-content:center;font-size:140px" id="n74">0%%</div>
  <div class="mono" style="position:absolute;left:500px;top:150px;font-size:40px;color:#cfc5b6;line-height:1.5">ROTTEN<br>TOMATOES<br><span class="red">CRÍTICA</span></div>
 </div>
 <div class="label" style="top:920px" id="l5b">05 · SU INSPIRACIÓN</div>
 <div class="big" style="top:990px;font-size:120px" id="t5a" data-k>JACK NICHOLSON</div>
 <div class="mid red" style="top:1250px;font-size:86px" id="t5b" data-k>EN «EL RESPLANDOR»</div>
</div>

<!-- 6 · cierre -->
<div class="scene" id="sc6">
 <div class="big" style="top:420px;font-size:170px" id="t6a" data-k>SÍGUEME</div>
 <div class="mid red" style="top:640px" id="t6b" data-k>PARA EL TERROR DEL DÍA</div>
 <div class="card" style="left:70px;right:70px;top:820px;height:280px;display:flex;align-items:center;gap:40px;padding-left:50px" id="brand">
  <div style="width:180px;height:180px">%(eye)s</div>
  <div><div style="font-size:84px;line-height:.95">SHORTS TERROR</div><div style="font-family:Serif;font-size:48px;letter-spacing:14px;color:var(--red)">ESPAÑA</div></div>
 </div>
 <div class="card" style="left:70px;right:70px;top:1160px;height:150px;background:#140f10" id="coment">
  <div class="mono" style="position:absolute;left:36px;top:22px;font-size:28px;color:#8d8386">comentario</div>
  <div class="mono" style="position:absolute;left:36px;top:66px;font-size:48px" id="ctyped"></div>
 </div>
</div>

<div class="eye" id="mascot">%(eye)s</div>

<script>
const C = %(cues)s;
const IN=0.22, OUTD=0.22;
const clamp=(x,a=0,b=1)=>Math.min(b,Math.max(a,x));
const seg=(t,a,b)=>clamp((t-a)/(b-a));
const eOut=x=>1-Math.pow(1-x,3);
const eExpo=x=>x>=1?1:1-Math.pow(2,-10*x);
const eBack=x=>{const c=1.9;x=clamp(x);return 1+(c+1)*Math.pow(x-1,3)+c*Math.pow(x-1,2)};
const spring=x=>x<=0?0:1-Math.exp(-7*x)*Math.cos(11*x);
const $=id=>document.getElementById(id);
function tf(el,o,x=0,y=0,s=1,r=0,b=0){el.style.opacity=o;el.style.transform=`translate(${x}px,${y}px) scale(${s}) rotate(${r}deg)`;el.style.filter=b>0.05?`blur(${b}px)`:'none';}
// texto cinético: cada letra entra con muelle y desenfoque
document.querySelectorAll('[data-k]').forEach(el=>{const tx=el.textContent;el.textContent='';
  tx.split(' ').forEach((w,wi,arr)=>{const W=document.createElement('span');W.style.whiteSpace='nowrap';W.style.display='inline-block';
    [...w].forEach(c=>{const s=document.createElement('span');s.className='ch';s.textContent=c;W.appendChild(s);});
    el.appendChild(W);if(wi<arr.length-1)el.appendChild(document.createTextNode(' '));});});
function kin(id,t,t0,st=0.03,dur=0.5,vanish=null){const el=$(id);const cs=el.querySelectorAll('.ch');
  for(let i=0;i<cs.length;i++){const p=seg(t,t0+i*st,t0+i*st+dur);let o=clamp(p*2),y=(1-eBack(p))*90,b=(1-p)*14;
    if(vanish!==null){const q=seg(t,vanish+i*0.07,vanish+i*0.07+0.35);o*=1-q;y-=q*40;b+=q*10;}
    tf(cs[i],o,0,y,1,0,b);} }
function pop(id,t,t0,from=0.6){const p=seg(t,t0,t0+0.45);tf($(id),clamp(p*3),0,(1-eOut(p))*40,from+(1-from)*eBack(p),0,(1-p)*8);}
function slide(id,t,t0,dx=0,dy=120){const p=seg(t,t0,t0+0.55);const e=eExpo(p);tf($(id),clamp(p*3),dx*(1-e),dy*(1-e),0.94+0.06*e,0,(1-p)*10);}
// fondos
const SC=[["sc0","dark",0,C.s1],["sc1","dark",C.s1,C.s2],["sc2","redb",C.s2,C.s3],["sc3","dark",C.s3,C.s4],["sc4","boneb",C.s4,C.s5],["sc5","dark",C.s5,C.s6],["sc6","dark",C.s6,99]];
const bgs=$('bgs');SC.forEach(s=>{const d=document.createElement('div');d.className='bg '+s[1];d.style.opacity=0;d.id='bg_'+s[0];bgs.appendChild(d);});
const em=$('embers');const EM=[];for(let i=0;i<26;i++){const d=document.createElement('div');d.className='ember';const r=20+((i*37)%%70);
  d.style.width=d.style.height=r+'px';em.appendChild(d);EM.push({d,x:(i*157)%%1080,y:(i*331)%%1920,v:18+(i*13)%%40,ph:i*1.7});}
function render(t){
  // escenas y fondos
  SC.forEach(([id,bg,a,b])=>{const pin=seg(t,a,a+IN),pout=seg(t,b-OUTD,b);const vis=t>=a-0.01&&t<b;
    const el=$(id),g=$('bg_'+id);
    if(!vis){el.style.opacity=0;g.style.opacity=0;return;}
    g.style.opacity=1;tf(el,1-pout,0,0,1+0.04*pout+0.03*(1-eOut(pin)),0,pout*16);
  });
  const dark=!(t>=C.s2&&t<C.s3)&&!(t>=C.s4&&t<C.s5);
  EM.forEach((e,i)=>{const y=((e.y-t*e.v)%%1920+1920)%%1920;const x=e.x+30*Math.sin(t*0.6+e.ph);
    e.d.style.transform=`translate(${x}px,${y}px)`;e.d.style.opacity=dark?(0.25+0.25*Math.sin(t*1.3+e.ph)):0;});
  // progreso n/5
  const n=t>=C.jn?5:t>=C.p74?4:t>=C.s3?3:t>=C.s2?2:t>=C.s1?1:0;
  document.querySelectorAll('#prog .bar').forEach((b,i)=>b.className='bar'+(i<n?' on':''));$('pn').textContent=n+'/5';
  // 0
  pop('l0',t,0.05);kin('t0a',t,0.1,0.025);kin('t0b',t,C.vp-0.15,0.035);
  slide('search',t,C.vp+0.4);const word='victorian psycho';const k=Math.floor(clamp((t-C.vp-0.6)/1.1)*word.length);
  $('typed').textContent=word.slice(0,k)+((Math.floor(t*2.4)%%2)?'|':' ');
  pop('tend',t,Math.min(C.s1-0.9,C.vp+1.6),1.6);
  // 1
  kin('t1a',t,C.s1+0.05);slide('cal',t,C.s1+0.25,-200,0);slide('cine',t,C.s1+0.4,250,0);
  $('ring13').style.strokeDashoffset=974*(1-eOut(seg(t,C.v13+0.1,C.v13+0.8)));
  kin('t1b',t,C.cines-0.1,0.02);pop('novela',t,C.nov,1.7);
  // 2
  kin('t2a',t,C.s2+0.05);kin('t2b',t,C.vf+0.2);slide('libro',t,C.s2+0.3);pop('esp',t,C.vf+0.6);kin('t2c',t,C.hw-0.45,0.02);
  // 3
  kin('t3a',t,C.s3+0.05,0.03);pop('longl',t,C.long-0.1);slide('hall',t,C.s3+0.4);
  const pg=seg(t,C.win-0.1,C.win+0.9);$('gov').style.opacity=pg*((pg<1&&Math.floor(t*18)%%3==0)?0.3:1);
  $('gov').style.transform=`translateX(-50%%) scale(${0.92+0.08*eOut(pg)}) translateY(${(1-eOut(pg))*30}px)`;
  $('hallp').style.transform=`scale(${1.05+0.06*seg(t,C.s3,C.s4)})`;
  pop('winif',t,C.win);pop('inst',t,C.inst+0.3);kin('t3d',t,C.desap-0.2,0.04,0.45,C.desap+1.2);
  // 4
  kin('t4a',t,C.ap-0.1,0.03);kin('t4b',t,C.te-0.25,0.025);slide('te',t,C.te+0.1);
  // 5
  slide('rt',t,C.s5+0.05);const p74=eOut(seg(t,C.p74-0.2,C.p74+1.0));$('n74').textContent=Math.round(74*p74)+'%%';
  $('ring74').style.strokeDashoffset=1068*(1-0.74*p74);pop('l5b',t,C.jn-0.5);kin('t5a',t,C.jn-0.1,0.03);kin('t5b',t,C.res-0.2,0.025);
  // 6
  kin('t6a',t,C.s6+0.1,0.05);kin('t6b',t,C.s6+0.5,0.02);slide('brand',t,C.ste-0.2);slide('coment',t,C.ste+0.6);
  const cw='¿la verás? 👇';const kc=Math.floor(clamp((t-C.ste-0.9)/1.0)*[...cw].length);$('ctyped').textContent=[...cw].slice(0,kc).join('');
  // mascota (ojo) que parpadea y flota
  const m=$('mascot');const spots=[[860,1290],[860,1350],[880,1330],[860,1450],[870,1300],[860,1460],[860,1700]];
  const si=SC.findIndex(s=>t>=s[2]&&t<s[3]);const [mx,my]=spots[Math.max(0,si)];const ps=seg(t,(SC[Math.max(0,si)]||SC[0])[2]+0.5,(SC[Math.max(0,si)]||SC[0])[2]+1.0);
  tf(m,ps*(si===6?0:1),mx,my+10*Math.sin(t*2.2),0.6+0.4*eBack(ps),4*Math.sin(t*1.3));
  const bl=(t%%3.1)<0.14;m.querySelector('.lid').setAttribute('height',bl?84:26);
  m.querySelector('.pupil').setAttribute('cx',60+8*Math.sin(t*0.9));
  // sacudida en golpes de texto
  let sh=0;[C.vp,C.v13,C.nov,C.desap,C.ap,C.p74,C.s6].forEach(c=>{const d=t-c;if(d>=0&&d<0.35)sh+=14*Math.exp(-d*12);});
  document.body.style.transform=sh>0.3?`translate(${sh*Math.sin(t*95)}px,${sh*Math.cos(t*80)}px)`:'none';
  // fundido final
  document.body.style.opacity=1-seg(t,C.end-0.8,C.end);
}
window.render=render;
</script></body></html>"""

html = HTML % dict(FONTS, im1=IM[1], im2=IM[2], im3=IM[3], im4=IM[4], gov=GOV, eye=EYE, cues=json.dumps(C))
page_path = TMP / "radar.html"
page_path.write_text(html, encoding="utf-8")


# ---------------------------------------------------------------- audio
def build_audio():
    rng = np.random.default_rng(3)
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(VOZ), "-af", "highpass=f=60", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"])
    v = np.frombuffer(raw, np.float32)
    N = int((TOTAL + 0.3) * SR)
    mix = np.zeros(N, np.float32)
    mix[:min(N, len(v))] += v[:N] / (np.abs(v).max() + 1e-9) * 0.85
    x = np.arange(N, dtype=np.float32) / SR
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
    tk = np.arange(int(0.04 * SR)) / SR
    tick = np.sin(2 * np.pi * 1900 * tk) * np.exp(-tk * 130)
    for k in ("s1", "s2", "s3", "s4", "s5", "s6"):
        put(wh, C[k] - 0.2, 0.28)
    for k in ("vp", "v13", "nov", "desap", "ap", "p74", "s6"):
        put(hit, C[k], 0.32)
    for i in range(16):
        put(tick, C["vp"] + 0.6 + i * 1.1 / 16, 0.07)
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
        pg.goto(page_path.as_uri(), wait_until="load")
        pg.evaluate("document.fonts.ready.then(()=>1)")
        for f in range(NF):
            pg.evaluate(f"render({f / FPS:.4f})")
            proc.stdin.write(pg.screenshot(type="jpeg", quality=92))
            if f % 300 == 0:
                print(f"fotograma {f}/{NF}", flush=True)
        br.close()
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg falló")
    print("OK", OUT, f"{OUT.stat().st_size / 1e6:.1f} MB", flush=True)
