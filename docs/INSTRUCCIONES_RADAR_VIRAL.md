# Radar Viral (TikTok, publica cada día a las 13:00): procedimiento

Cuenta: **TikTok @radarviral45seg** vía **Metricool**, `blogId` **7969360**, Europe/Madrid. **Solo TikTok** (el YouTube de la misma marca es el canal de terror; aquí no se publica nada en YouTube).
Formato: short vertical 1080×1920 de 35–50 s con el tema **más buscado HOY en España, de cualquier temática** (no de terror). Va contado con voz generada gratis (Edge TTS, como los vídeos largos) y con gráficos de tipografía cinética sincronizados (búsqueda que se escribe, sellos, fechas, contadores, tarjetas, titulares), con la marca **Radar Viral**: azul noche, rosa y cian, y un radar con botón de play. Motor: `tools/radar_motion.py` con `"marca": "radar_viral"` (mismo formato de escenas y elementos que `docs/INSTRUCCIONES_RADAR.md`).

## Pasos

1. **Tema de hoy.** Busca con WebSearch qué es lo más buscado HOY en España: Google Trends España, tendencias de X y TikTok, noticias del día. Haz varias búsquedas en español. Elige el tema con más tirón que se pueda explicar en 45 s con datos claros (estreno, deporte, famoso, tecnología, curiosidad, fenómeno, fiesta, tiempo…). Mira `historias/HISTORIAL_RADAR_VIRAL.md` para no repetir. Comprueba cada dato en al menos 2 fuentes con fecha de hoy o de ayer.
   - **Evita** muertes y tragedias recientes, víctimas, crímenes, menores, suicidio, salud de personas concretas y rumores sin confirmar.
   - Con política, solo hechos verificables y neutrales, sin opinar ni tomar partido. Si dudas, elige otro tema.
2. **Guion** (`texto`, 90–120 palabras): empieza con una pregunta gancho («¿Por qué todo el mundo busca hoy…?», «¿Quién es…?», «¿Qué ha pasado con…?»). Siguen 5–7 datos concretos y verificados, con números y fechas escritos en letra, como se pronuncian. Termina SIEMPRE con: «Si quieres saber lo más buscado de cada día, sígueme. Soy Radar Viral.»
3. **Voz (gratis, sin ElevenLabs):** NO uses ElevenLabs. No pongas `voz_url`; pon en el JSON `"voz": {"voz": "es-ES-AlvaroNeural", "rate": "+0%", "pitch": "-2Hz"}` (puedes alternar con es-ES-ElviraNeural). La Action genera `voces/completa.mp3` a partir de `texto` con Edge TTS, igual que en los vídeos largos.
4. Escribe `radar/rvNNN_slug/historia.json` (NNN = siguiente número del historial de Radar Viral, p. ej. `rv001_…`) con:
   - `"formato": "radar"` y `"marca": "radar_viral"`
   - `"estilo_imagen": ", bold flat vector editorial illustration, clean geometric shapes, navy blue background with cyan and pink accents, soft gradients, modern explainer style, no text, no letters, no logos, no watermark"`
   - `"estilo_personaje": ", full body character, standing, isolated on plain white background, centered, flat vector editorial illustration, clean shapes, no text, no logos"` (solo si usas `reparto`)
   - `"cierre_desde": "Si quieres"`, `"cierre": {"lema": "Lo más buscado de cada día", "comentario": "pregunta corta al público 👇"}`
   - Escenas y elementos como en `docs/INSTRUCCIONES_RADAR.md` (5–7 escenas; `fondo`: `dark` casi siempre, `red` (rosa en esta marca) 1–2 veces, `bone` 1 vez). La 1ª escena lleva `{"tipo": "tag", "texto": "Radar Viral · hoy"}` y `busqueda` con el término buscado.
   - Prompts de imagen EN INGLÉS describiendo un objeto, un lugar o una escena genérica. **Personas reales: solo por su nombre en texto, NUNCA dibujadas.** Sin logos, escudos, pósteres ni marcas.

   Commit + `git -c push.negotiate=true push`. Espera a `origin/main:radar/rvNNN_slug/preparado.txt`: bucle `git fetch --depth 1 origin +refs/heads/main:refs/remotes/origin/main` cada 20 s, máx. 25 min. Después `git reset --hard origin/main`.
5. Comprueba `voces/completa.mp3` y mira las escenas con Read. Si alguna trae texto, una cara reconocible o un logo, bórrala junto a su `_depth.png` y `preparado.txt`, cambia el prompt y repite el paso 4.
6. Monta: `python3 -I tools/radar_motion.py radar/rvNNN_slug /tmp/rvNNN_slug.mp4`. Revisa 6–8 fotogramas: nada se sale ni se solapa, y se lee bien.
7. Sube: `bash tools/subir_largo.sh rvNNN_slug /tmp/rvNNN_slug.mp4` y espera `origin/main:largos/rvNNN_slug/url.txt`.
8. Metricool (createScheduledPost) **hoy a las 13:00** (Europe/Madrid). Si ya son más de las 12:50, prográmalo para dentro de 10 minutos.
   - `providers`: `[{"network":"tiktok"}]` (SOLO TikTok), `media`: `[contenido de url.txt]`, `draft`: false, `autoPublish`: true
   - `text`: 1–2 frases con la pregunta gancho + pregunta al público + 4–6 hashtags (#loquesebusca #noticias #tendencias #radarviral + 1–2 del tema) + línea en blanco + "Voz creada con IA."
   - `tiktokData`: `{"privacyOption": "PUBLIC_TO_EVERYONE", "disableComment": false, "disableDuet": false, "disableStitch": false, "isAigc": true, "autoAddMusic": false, "commercialContentThirdParty": false, "commercialContentOwnBrand": false, "title": "pregunta gancho (máx. 90 caracteres)"}`
9. Añade una línea a `historias/HISTORIAL_RADAR_VIRAL.md` (NNN | fecha | tema | fuentes) y haz push. Resume: tema, título y hora de publicación, con las fuentes.

Si algo falla, no programes nada a medias y explica el error.
