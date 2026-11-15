# Vídeo largo de terror (lunes, miércoles y viernes) — procedimiento

Canal: **Shorts Terror España** (YouTube) vía **Metricool**, `blogId` **7969360**, Europe/Madrid.
Formato: 1920×1080, 12–14 min, historia narrada (voz Edge TTS generada por GitHub Actions), imágenes IA por escena (Pollinations, generadas por GitHub Actions), subtítulos, capítulos y sonido sintetizado.

## Pasos

1. Lee `historias/HISTORIAL_LARGOS.md` y escribe una historia NUEVA (reglas abajo) en `largos/NNN_slug/historia.json` (NNN = siguiente número; el 000 es Valdecaña).
2. Commit + `git -c push.negotiate=true push` a `main`. Esto lanza la Action **«Preparar vídeo largo»**, que genera `voces/` e `imgs/` y escribe `preparado.txt` (5–15 min).
3. Espera (bucle con `git fetch --depth 1 origin main` cada 30 s, máx. 45 min) a que exista `origin/main:largos/NNN_slug/preparado.txt`; luego `git pull --depth 1` (o `git reset --hard origin/main` si el clon es superficial).
   Si en 45 min no aparece, termina explicando que la Action falló (el usuario puede verla en la pestaña Actions del repo).
4. Comprueba que hay voces para todos los bloques y mira 3–4 imágenes con Read. Una imagen que falte se sustituye sola por la anterior.
5. Monta: `python3 -I tools/largo.py largos/NNN_slug /tmp/NNN_slug.mp4` en segundo plano (≈25–35 min con 2 núcleos) y espera a que termine.
6. Revisa 6 fotogramas repartidos y el volumen (`ebur128`, objetivo ≈ −16 LUFS). Debe pesar < 1,5 GB.
7. Commit + push de `largos/NNN_slug/miniatura.jpg` y `capitulos.txt` (los crea el montaje).
8. Sube el vídeo: `bash tools/subir_largo.sh NNN_slug /tmp/NNN_slug.mp4`. La Action **«Publicar vídeo largo»** lo une, crea la release `largo-NNN_slug` y escribe `largos/NNN_slug/url.txt` en `main` (2–5 min). Espera a ese archivo igual que en el paso 3.
9. Programa en Metricool (createScheduledPost) **hoy a las 18:00** (Europe/Madrid); si hoy ya hay un vídeo largo programado (ignora borradores `draft: true` y shorts), el siguiente lunes/miércoles/viernes libre:
   - `media`: `[contenido de url.txt]`
   - `providers`: `[{"network":"youtube"}]`, `draft`: false, `autoPublish`: true
   - `text`: descripción del JSON + línea en blanco + "Capítulos:" + contenido de `capitulos.txt` + hashtags
   - `youtubeData`: `{"title": titulo_youtube, "type":"video", "privacy":"public", "tags":[...8–12...], "category":"ENTERTAINMENT", "madeForKids": false, "isAiGeneratedContent": true}`
   - `videoThumbnailUrl`: `https://raw.githubusercontent.com/shortshistoricos1/videos_terror/main/largos/NNN_slug/miniatura.jpg`. Si Metricool responde `VIDEO_THUMBNAIL_NOT_APPLICABLE`, repite la llamada sin ese campo.
10. Añade una línea a `historias/HISTORIAL_LARGOS.md` y haz push. Resume en 3 líneas: título, de qué va y cuándo se publica.

Si algo falla, no programes nada a medias; explica qué paso falló.

## Formato de `historia.json`

```json
{
  "titulo": "LAS NORMAS DE VALDECAÑA",
  "subtitulo": "Una historia de miedo",
  "titulo_youtube": "gancho fuerte, máx. 90 caracteres | Historia de terror",
  "descripcion": "2–4 frases que enganchen sin destripar el final + pregunta al público",
  "tags": ["historias de miedo", "terror", "..."],
  "final": ["¿Tú habrías llamado?", "Suscríbete para más historias de miedo"],
  "miniatura": {"texto1": "NO LLAMES", "texto2": "LAS 7 NORMAS DE LA CASA", "bloque": 11},
  "voz": {"voz": "es-ES-AlvaroNeural", "rate": "-8%", "pitch": "-5Hz"},
  "bloques": [
    {"texto": "Narración del bloque (1–3 frases, 25–45 palabras).",
     "imagen": "prompt EN INGLÉS de la escena: lugar, luz, encuadre, objeto o figura (sin texto, sin gore, sin personas reales)",
     "ambiente": "interior | viento | nieve | lluvia | fuego | estatica",
     "sfx": [{"tipo": "golpes | aranazos | telefono | respiracion | latido | golpe_final", "en": "frase exacta del texto donde suena"}],
     "pausa": 0.6},
    {"tipo": "capitulo", "texto": "Uno. El anuncio."},
    {"texto": "...", "imagen": "=", "ambiente": "interior"}
  ]
}
```

- `"imagen": "="` reutiliza la imagen anterior (la cámara sigue acercándose). Usa 22–30 imágenes distintas por vídeo.
- Capítulos: `{"tipo":"capitulo","texto":"Número en letra. Título."}` (8–10 capítulos). La voz los lee.
- `pausa`: segundos de silencio tras el bloque (0.6 normal; 1.2–2.6 tras frases de impacto).
- `golpe_final` va en el bloque de la revelación (suena al terminar la frase). `latido` cubre todo su bloque.
- Voces válidas: es-ES-AlvaroNeural (por defecto), es-ES-ElviraNeural (narradora), es-MX-JorgeNeural, es-MX-DaliaNeural. Alterna según el narrador.

## Reglas de la historia

- 1.500–1.800 palabras de narración (≈ 12–14 min), 50–65 bloques. Primera persona, español de España, frases cortas y orales (se van a escuchar, no leer).
- Estructura: gancho en los primeros 20 s (adelanta el peligro sin destriparlo) → presentación → escalada con 3–5 sucesos cada vez peores → clímax → giro final que obligue a repensar la historia.
- Original. Nada de creepypastas conocidas ni de copiar películas.
- Variedad respecto al historial: escenario (pueblo, ciudad, carretera, hospital, faro, internado, autobús nocturno, mina, residencia, barco, casa rural…), tipo de amenaza (doble, presencia, reglas, objeto maldito, desaparición, bucle temporal, vecino…) y giro.
- Terror psicológico; sin gore explícito, sin violencia sexual, sin menores en peligro grave, sin suicidio ni autolesiones, sin personas, marcas ni sucesos reales.
- Prompts de imagen coherentes entre sí (misma casa, mismo personaje: describe edad, ropa y pelo igual en todos los prompts).
