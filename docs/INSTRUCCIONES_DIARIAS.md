# Short de terror diario (estilo cómic narrado) — procedimiento

Canal: **Shorts Terror España** (YouTube) vía **Metricool**, `blogId` **7969360**, Europe/Madrid.
Formato: short vertical 1080×1920 de 40–55 s, historia narrada (voz Edge TTS) sobre ilustraciones de **cómic de terror** generadas por IA, con movimiento de cámara, subtítulos grandes y sonido sintetizado. Mismo sistema que los vídeos largos (`docs/INSTRUCCIONES_LARGOS.md`), en vertical.

## Pasos de cada día

1. Lee `historias/HISTORIAL.md` (no repitas escenario, amenaza ni giro de los últimos 30 días).
2. Escribe la historia en `cortos/NNN_slug/historia.json` (NNN = siguiente número del historial) con `"formato": "vertical"`. Formato y reglas abajo.
3. Commit + `git -c push.negotiate=true push` a `main` → la Action **«Preparar vídeo largo»** genera `voces/`, `imgs/` (verticales) y `preparado.txt` (2–6 min).
4. Espera (bucle `git fetch --depth 1 origin +refs/heads/main:refs/remotes/origin/main` cada 20 s, máx. 30 min) a que exista `origin/main:cortos/NNN_slug/preparado.txt`; luego `git reset --hard origin/main`.
5. Mira las imágenes con Read. Monta: `python3 -I tools/largo.py cortos/NNN_slug /tmp/NNN_slug.mp4` (≈3–5 min).
6. Revisa 4 fotogramas y la duración (≤ 59 s; si pasa, acorta el texto y repite desde el paso 2 con otro NNN_slug).
7. Sube: `bash tools/subir_largo.sh NNN_slug /tmp/NNN_slug.mp4` y espera `origin/main:largos/NNN_slug/url.txt` (la Action de publicación lo escribe ahí también para los shorts).
8. Busca en Metricool (getScheduledPosts) el **primer día a partir de hoy sin ningún short de YouTube programado** (ignora borradores `draft: true` y vídeos largos) y programa a las **20:00** con createScheduledPost:
   - `media`: `[contenido de url.txt]`, `providers`: `[{"network":"youtube"}]`, `draft`: false, `autoPublish`: true
   - `text`: `descripcion` del JSON
   - `youtubeData`: `{"title": titulo_youtube, "type":"short", "privacy":"public", "tags":[5–8 etiquetas], "category":"ENTERTAINMENT", "madeForKids": false, "isAiGeneratedContent": true}`
9. Añade una línea a `historias/HISTORIAL.md`: `NNN | fecha programada | escenario | amenaza | giro`. Commit + push.
10. Resume en 2–3 líneas: título, de qué va, día y hora.

Si algo falla, no programes nada a medias y explica el error.

## Formato de `historia.json`

```json
{
  "formato": "vertical",
  "titulo": "El último autobús",
  "titulo_youtube": "gancho fuerte, máx. 90 caracteres 😨 #shorts",
  "descripcion": "1–2 frases + pregunta al público + 4–5 hashtags",
  "final": ["¿Tú te habrías bajado?", "Sígueme para más"],
  "voz": {"voz": "es-ES-AlvaroNeural", "rate": "-5%", "pitch": "-4Hz"},
  "bloques": [
    {"texto": "Gancho de 1 frase que obligue a quedarse.", "imagen": "prompt EN INGLÉS de la viñeta", "ambiente": "interior"},
    {"texto": "...", "imagen": "=", "sfx": [{"tipo": "golpes", "en": "llamaron"}]},
    {"texto": "Frase final con el giro.", "imagen": "...", "sfx": [{"tipo": "golpe_final"}], "pausa": 1.2}
  ]
}
```

- 7–10 bloques, **110–140 palabras en total** (≈ 40–55 s). 5–8 imágenes distintas (`"="` reutiliza la anterior).
- El primer bloque es el gancho (se entiende sin contexto y crea una pregunta). El último, el giro.
- `ambiente`: interior | viento | lluvia | fuego | estatica. `sfx`: golpes | aranazos | telefono | respiracion | latido | golpe_final.
- Alterna voces entre días: es-ES-AlvaroNeural, es-ES-ElviraNeural, es-MX-JorgeNeural, es-MX-DaliaNeural.

## Reglas de la historia

- Español de España, primera persona, frases cortas para escuchar. Original (nada de creepypastas conocidas).
- Varía escenario (residencia, autobús nocturno, ascensor, gasolinera, faro, hospital, pueblo, garaje, camping, hotel…), amenaza y giro.
- Estilo de imagen: cómic de terror (lo añade la Action). Describe cada viñeta: plano, personaje (misma descripción en todas), lugar y luz. Sin texto en la imagen.
- Terror psicológico; sin gore explícito, sin violencia sexual, sin menores en peligro grave, sin suicidio ni autolesiones, sin personas, marcas ni sucesos reales.
