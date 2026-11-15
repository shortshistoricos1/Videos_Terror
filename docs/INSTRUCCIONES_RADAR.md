# Radar del terror (short diario, publica a las 14:00) — procedimiento

Canal: **Shorts Terror España** (YouTube) vía **Metricool**, `blogId` **7969360**, Europe/Madrid.
Formato: short vertical 1080×1920 de 35–50 s al estilo «Radar Viral» pero con temática y marca de terror: el tema de terror del que más se habla HOY, contado con voz de **ElevenLabs** y gráficos animados sincronizados (búsqueda que se escribe, sellos, fechas, contadores, tarjetas, titulares) sobre fondos de cómic de terror con animación 2.5D, logo fijo arriba y cierre con «SÍGUEME». Motor: `tools/radar.py`. Ejemplo completo: `radar/001_victorian_psycho/historia.json`.

## Pasos

1. **Tema de hoy.** Busca con WebSearch (varias búsquedas, español e inglés) qué tema de terror es tendencia hoy: estrenos y taquilla de cine de terror, tráileres, series, videojuegos de terror, leyendas o fenómenos «inexplicables» virales, aniversarios de clásicos. Mira `historias/HISTORIAL_RADAR.md` para no repetir. Comprueba cada dato en al menos 2 fuentes con fecha reciente. **Evita** tragedias reales con víctimas, crímenes reales, menores, suicidio y gore.
2. **Guion** (`texto`, 90–120 palabras): empieza con «¿Por qué todo el mundo habla hoy de …?»; 5–7 datos concretos y verificados; números y fechas escritos en letra (como se pronuncian); termina SIEMPRE con: «Si quieres el terror del que todo el mundo habla, sígueme. Esto es Shorts Terror España.»
3. **Voz con el conector de ElevenLabs:** `creative_generate_speech` con `voice_id` **8HZqgqbee8zgakPIPwm5** (José Bionada, narrador castellano), `model_id` **eleven_v4**, `prompt` = el texto exacto. Espera con `creative_get_flow_run_status` (flow_id + session_ids) hasta `all_completed`, y copia el `content_url` de la PRIMERA generación al campo `voz_url` del JSON (el enlace caduca en ~2 h: sigue sin pausas).
4. Escribe `radar/NNN_slug/historia.json` (formato abajo) y haz commit + `git -c push.negotiate=true push`. La Action «Preparar» descarga la voz a `voces/completa.mp3`, genera las escenas verticales, los personajes y la profundidad, y escribe `preparado.txt` (3–6 min). Espera a `origin/main:radar/NNN_slug/preparado.txt` (bucle `git fetch --depth 1 origin +refs/heads/main:refs/remotes/origin/main` cada 20 s, máx. 25 min) y `git reset --hard origin/main`.
5. Comprueba que existe `voces/completa.mp3` y mira las escenas con Read (si alguna trae texto o bocadillos, bórrala junto a su `_depth.png` y `preparado.txt`, cambia el prompt y repite el paso 4).
6. Monta: `python3 -I tools/radar.py radar/NNN_slug /tmp/NNN_slug.mp4` (≈2–3 min). Revisa 6 fotogramas (gráficos legibles, nada tapado, subtítulos dentro de la pantalla).
7. Sube: `bash tools/subir_largo.sh NNN_slug /tmp/NNN_slug.mp4` y espera `origin/main:largos/NNN_slug/url.txt`.
8. Metricool (createScheduledPost) **hoy a las 14:00** (Europe/Madrid). Si ya son más de las 13:50, prográmalo para dentro de 10 minutos.
   - `media`: `[contenido de url.txt]`, `providers`: `[{"network":"youtube"}]`, `draft`: false, `autoPublish`: true
   - `text`: `descripcion` + línea en blanco + "Voz creada con inteligencia artificial (ElevenLabs)."
   - `youtubeData`: `{"title": titulo_youtube, "type":"short", "privacy":"public", "tags":[5–8], "category":"ENTERTAINMENT", "madeForKids": false, "isAiGeneratedContent": true}`
9. Añade una línea a `historias/HISTORIAL_RADAR.md` (NNN | fecha | tema | fuentes) y haz push. Resume: tema, título y hora de publicación.

Si algo falla, no programes nada a medias y explica el error.

## Formato de `historia.json`

```json
{
 "formato": "radar",
 "titulo_youtube": "¿Por qué todo el mundo habla de X? 😱 #shorts",
 "descripcion": "1–2 frases + pregunta + hashtags",
 "fuentes": ["url1", "url2"],
 "voz_url": "content_url del conector de ElevenLabs",
 "texto": "guion EXACTO que se ha locutado",
 "reparto": {"id": "descripción EN INGLÉS de un personaje genérico (nunca una persona real)"},
 "escenas": [
  {"imagen": "prompt EN INGLÉS del fondo (vertical, sin texto, sin personas si hay personaje)", "ambiente": "interior|viento|lluvia|fuego|estatica",
   "elementos": [{"tipo": "busqueda", "texto": "lo que se busca", "en": "frase exacta"}, {"tipo": "sello", "texto": "TENDENCIA HOY", "en": "..."}]},
  {"desde": "frase exacta donde empieza la escena", "imagen": "...", "elementos": [...], "personajes": [{"quien": "id", "anim": "aparece|asoma|camina|se_acerca|respira|tiembla", "en": "...", "alto": 0.5}]}
 ],
 "cierre_desde": "Si quieres"
}
```

- 5–7 escenas; la primera empieza en 0 y las demás en su frase `desde`. El cierre (logo + SÍGUEME) empieza en `cierre_desde`.
- Tipos de `elementos` (cada uno aparece cuando la voz dice su `en`; `y` opcional = altura 0–1):
  `busqueda` (barra que se escribe sola, solo en la escena 1), `titular` (texto enorme), `sello` (tampón rojo, máx. 3 palabras),
  `dato` (`valor` numérico que cuenta hasta su cifra + `sufijo` + `etiqueta`), `fecha` (`dia`, `mes`, `etiqueta`, con círculo rojo),
  `tarjeta` (`titulo` + `texto` corto). Máx. 2–3 elementos por escena y que no se solapen (usa `y` distintos: 0.18–0.56).
- Personas reales: solo por su nombre en texto (tarjetas/titulares), NUNCA dibujadas. Sin logos ni pósteres de películas.
