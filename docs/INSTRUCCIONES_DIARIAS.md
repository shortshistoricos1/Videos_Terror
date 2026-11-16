# Short de terror diario (estilo cómic narrado) — procedimiento

Canal: **Shorts Terror España** (YouTube) vía **Metricool**, `blogId` **7969360**, Europe/Madrid.
Formato: short vertical 1080×1920 de 40–58 s, montado en estilo motion design (tools/historia_motion.py), historia narrada (voz Edge TTS) sobre ilustraciones de **cómic de terror** generadas por IA, con movimiento de cámara, subtítulos grandes y sonido sintetizado. Mismo sistema que los vídeos largos (`docs/INSTRUCCIONES_LARGOS.md`), en vertical.

## Pasos de cada día

1. Lee `historias/HISTORIAL.md` (no repitas escenario, amenaza ni giro de los últimos 30 días).
2. Escribe la historia en `cortos/NNN_slug/historia.json` (NNN = siguiente número del historial) con `"formato": "vertical"`. Formato y reglas abajo.
3. Commit + `git -c push.negotiate=true push` a `main` → la Action **«Preparar vídeo largo»** genera `voces/`, `imgs/` (verticales) y `preparado.txt` (2–6 min).
4. Espera (bucle `git fetch --depth 1 origin +refs/heads/main:refs/remotes/origin/main` cada 20 s, máx. 30 min) a que exista `origin/main:cortos/NNN_slug/preparado.txt`; luego `git reset --hard origin/main`.
5. Mira las imágenes con Read. Monta en **estilo motion design** (viñetas de cómic en tarjetas + narración palabra a palabra + marca): `python3 -I tools/historia_motion.py cortos/NNN_slug /tmp/NNN_slug.mp4` (≈2 min). Opcional en el JSON: `"comentario"` (texto que se escribe en la caja de comentario del cierre, p. ej. "yo no salgo ni loco 😨").
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

## Personajes animados (úsalos en casi todas las escenas)

Los personajes se generan aparte (fondo recortado automáticamente) y se animan encima del fondo, sincronizados con la voz.

- En el JSON, `"reparto"`: `{"id": "descripción EN INGLÉS del personaje: edad, pelo, ropa, rasgos"}` (1–3 personajes). Se genera UNA vez y se reutiliza en todo el vídeo, así siempre es igual. Monstruos/sombras: descríbelos de cuerpo entero.
- En cada bloque, `"personajes": [{"quien": "id", "anim": "...", "x": 0.5, "y": 0.97, "alto": 0.72, "desde": "izq|der", "en": "frase exacta donde empieza", "silueta": false, "espejo": false}]`
  - `anim`: `respira` (quieto), `camina` (entra andando desde `desde` hasta `x`), `asoma` (se asoma desde un lado), `se_acerca` (crece hacia cámara), `aparece` (surge parpadeando), `tiembla` (miedo), `gira` (se da la vuelta).
  - `x`: posición horizontal (0–1); `y`: dónde pisa (0.97 = abajo); `alto`: altura respecto a la pantalla (0.72 horizontal, 0.5 vertical; menos si está lejos).
  - `silueta: true` para criaturas/sombras (negro con contraluz). `espejo: true` para que mire al otro lado.
- **Si un bloque lleva personajes, el prompt de `imagen` de ese fondo debe ser SIN personas** ("..., no people").
- `"impactos": [{"texto": "DOCE", "en": "Doce"}]`: palabra clave que salta en grande al decirla (1 cada 2–4 bloques, en momentos de tensión).
- Los `sfx` `golpes` y `golpe_final` añaden solos fogonazo y sacudida de cámara.

## Reglas de la historia

- Español de España, primera persona, frases cortas para escuchar. Original (nada de creepypastas conocidas).
- Varía escenario (residencia, autobús nocturno, ascensor, gasolinera, faro, hospital, pueblo, garaje, camping, hotel…), amenaza y giro.
- Estilo de imagen: cómic de terror (lo añade la Action). Describe cada viñeta: plano, personaje (misma descripción en todas), lugar y luz. Sin texto en la imagen.
- Terror psicológico; sin gore explícito, sin violencia sexual, sin menores en peligro grave, sin suicidio ni autolesiones, sin personas, marcas ni sucesos reales.
