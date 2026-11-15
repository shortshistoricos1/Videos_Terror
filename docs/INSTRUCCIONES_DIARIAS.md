# Short de terror diario — procedimiento

Canal: **Shorts Terror España** (YouTube), publicado vía **Metricool**, marca `shorts.historia.e`, `blogId` **7969360**, zona horaria Europe/Madrid.
Formato: short vertical 1080×1920 de ~45–55 s, historia de miedo contada como **conversación de chat** (sin voz), con sonido sintetizado.

## Pasos de cada día

1. Lee `historias/HISTORIAL.md` para no repetir contacto, situación ni giro de los últimos 30 días.
2. Escribe una historia NUEVA y original en `historias/NNN_slug.json` (NNN = siguiente número). Reglas abajo.
3. Genera el vídeo:
   `python3 -I tools/chat_short.py historias/NNN_slug.json videos/NNN_slug.mp4`
   (tarda ~2 min; necesita ffmpeg, Pillow, numpy y las fuentes Poppins de `/usr/share/fonts/truetype/google-fonts/`).
4. Revisa 3 fotogramas (inicio, mitad, final) con ffmpeg y míralos: texto legible, nada cortado. Si algo falla, corrige el JSON y repite.
5. Sube el vídeo: `git add` + commit + `git -c push.negotiate=true push` a `main`.
6. Busca en Metricool (getScheduledPosts, blogId 7969360) el **primer día a partir de hoy sin ningún short de YouTube programado** (ignora los borradores, `draft: true`, y los vídeos largos) y programa ahí el short a las **20:00** (Europe/Madrid) con createScheduledPost:
   - `media`: `["https://raw.githubusercontent.com/shortshistoricos1/videos_terror/main/videos/NNN_slug.mp4"]`
   - `providers`: `[{"network":"youtube"}]`, `draft`: false, `autoPublish`: true
   - `text`: el campo `descripcion` del JSON
   - `youtubeData`: `{"title": titulo_youtube, "type":"short", "privacy":"public", "tags":[...5–8 etiquetas de terror en español...], "category":"ENTERTAINMENT", "madeForKids": false, "isAiGeneratedContent": true}`
7. Cuando Metricool responda OK (copia el vídeo a su servidor), **borra los mp4 de `videos/`** con más de 2 días (git rm + push) para que el repo no crezca.
8. Añade una línea a `historias/HISTORIAL.md`: `NNN | fecha programada | contacto | situación | giro final`. Commit + push.
9. Resume en 2–3 líneas en español qué historia se hizo y para qué día quedó programada.

Si un paso falla (Metricool, push, render), no publiques nada a medias: explica el error en el resumen.

## Formato del JSON

```json
{
  "titulo_youtube": "máx. 90 caracteres, gancho + emoji + #shorts",
  "descripcion": "1–2 frases + pregunta al público + 4–5 hashtags",
  "contact": "nombre del contacto (cabecera del chat)",
  "intro": ["línea 1", "línea 2 (parte blanca) ", "parte roja", "línea 3", "texto pequeño gris"],
  "end": ["pregunta final línea 1", "línea 2 en rojo", "texto pequeño"],
  "script": [["M","texto del contacto","2:13"], ["Y","texto del protagonista","2:13"], ..., ["KNOCK3"], ..., ["TYPESTOP"], ["BANNER"], ["M","...","2:17"], ["FINAL"]],
  "banner": {"from": "quien manda la notificación del giro", "text": "texto de la notificación (máx. ~110 caracteres)"}
}
```

Orden **obligatorio** de los eventos especiales (el generador depende de él): mensajes → `KNOCK3` (tres golpes en una puerta/ventana/pared) → mensajes → `TYPESTOP` (el contacto escribe y se calla) → `BANNER` (notificación de un tercero que revela el giro) → 1–3 mensajes finales del contacto → `FINAL`.
"M" = el contacto, "Y" = el protagonista. Horas coherentes y crecientes (madrugada). 14–20 mensajes en total para que dure 45–55 s.

## Reglas de la historia

- Español de España, natural, frases cortas como en WhatsApp. Sin faltas.
- Original: nunca copiar creepypastas conocidas ("yo también lo he oído", etc.).
- Varía cada día: tipo de contacto (madre, hermano, pareja, compañero de piso, abuela, amigo, vecina, número desconocido, canguro, jefe, grupo de clase…), lugar (piso, pueblo, casa rural, autocaravana, residencia, hotel, camping, garaje…) y tipo de giro (suplantación, el contacto ya estaba muerto, está dentro de casa, era el propio protagonista, la hora es imposible, el móvil estaba apagado…).
- El giro tiene que entenderse con la notificación `BANNER` + el último mensaje.
- Terror psicológico, sin gore explícito, sin violencia contra menores, sin suicidio ni autolesiones, sin personas reales ni marcas.
