# Radar Viral (TikTok, publica cada día a las 13:00): procedimiento

Cuenta: **TikTok @radarviral45seg** vía **Metricool**, `blogId` **7969360**, Europe/Madrid. **Solo TikTok** (el YouTube de la misma marca es el canal de terror; aquí no se publica nada en YouTube).
Formato: vídeo vertical 1080×1920 de **más de 1 minuto (65–80 s)**, porque TikTok solo paga (Creator Rewards) por vídeos de más de 1 minuto, con el tema **más buscado HOY en España, de cualquier temática** (no de terror). Va contado con voz generada gratis (Edge TTS, como los vídeos largos) y con gráficos de tipografía cinética sincronizados (búsqueda que se escribe, sellos, fechas, contadores, tarjetas, titulares), con la marca **Radar Viral**: azul noche, rosa y cian, y un radar con botón de play. Motor: `tools/radar_motion.py` con `"marca": "radar_viral"` (mismo formato de escenas y elementos que `docs/INSTRUCCIONES_RADAR.md`).

## Pasos

1. **Tema de hoy: SIEMPRE lo más buscado de verdad, comprobado en las tendencias del día** (no elijas un tema de las noticias por tu cuenta):
   - **a) Tendencias de X en España:** WebFetch de `https://trends24.in/spain/index.html` (la última hora y la sección de lo que lleva más tiempo en tendencia).
   - **b) Google España:** WebSearch «tendencias Google España hoy» y «lo más buscado hoy España» (modo `extended`). NO uses la página trends.google.*/trending con WebFetch: devuelve las tendencias de EE. UU., no las de España.
   - **c) Noticias del día:** WebSearch del nombre de cada tendencia para saber POR QUÉ es tendencia hoy (fecha de hoy o de ayer).
   - Haz una lista de las 10 primeras tendencias. Descarta las prohibidas (abajo) y elige la que esté **más arriba y en más fuentes a la vez** (p. ej. en X España y además en Google o en las noticias). Si es un hashtag de un programa de TV, sirve si se puede explicar con datos.
   - No repitas temas de `historias/HISTORIAL_RADAR_VIRAL.md`. Comprueba cada dato en al menos 2 fuentes con fecha de hoy o de ayer.
   - En el historial anota en `fuentes` también dónde salió como tendencia (p. ej. «trends24 X España n.º 2 + Google»).
   - **Evita** muertes y tragedias recientes, víctimas, crímenes, menores, suicidio, salud de personas concretas y rumores sin confirmar.
   - Con política, solo hechos verificables y neutrales, sin opinar ni tomar partido. Si dudas, elige otro tema.
2. **Guion** (`texto`, **160–190 palabras**, para que el vídeo dure 65–80 s): empieza con una pregunta gancho («¿Por qué todo el mundo busca hoy…?», «¿Quién es…?», «¿Qué ha pasado con…?»). Siguen 8–10 datos concretos y verificados (contexto, cifras, quién, por qué importa, qué pasa ahora), con números y fechas escritos en letra, como se pronuncian. Termina SIEMPRE con: «Si quieres saber lo más buscado de cada día, sígueme. Soy Radar Viral.»
3. **Voz (gratis, sin ElevenLabs):** NO uses ElevenLabs. No pongas `voz_url`; pon en el JSON `"voz": {"voz": "es-ES-AlvaroNeural", "rate": "+0%", "pitch": "-2Hz"}` (puedes alternar con es-ES-ElviraNeural). La Action genera `voces/completa.mp3` a partir de `texto` con Edge TTS, igual que en los vídeos largos.
4. Escribe `radar/rvNNN_slug/historia.json` (NNN = siguiente número del historial de Radar Viral, p. ej. `rv001_…`) con:
   - `"formato": "radar"` y `"marca": "radar_viral"`
   - `"estilo_imagen": ", bold flat vector editorial illustration, clean geometric shapes, navy blue background with cyan and pink accents, soft gradients, modern explainer style, no text, no letters, no logos, no watermark"`
   - `"estilo_personaje": ", full body character, standing, isolated on plain white background, centered, flat vector editorial illustration, clean shapes, no text, no logos"` (solo si usas `reparto`)
   - `"cierre_desde": "Si quieres"`, `"cierre": {"lema": "Lo más buscado de cada día", "comentario": "pregunta corta al público 👇"}`
   - Escenas y elementos como en `docs/INSTRUCCIONES_RADAR.md` (8–10 escenas; `fondo`: `dark` casi siempre, `red` (rosa en esta marca) 1–2 veces, `bone` 1 vez). La 1ª escena lleva `{"tipo": "tag", "texto": "Radar Viral · hoy"}` y `busqueda` con el término buscado.
   - Prompts de imagen EN INGLÉS describiendo un objeto, un lugar o una escena genérica. **Personas reales: solo por su nombre en texto, NUNCA dibujadas.** Sin logos, escudos, pósteres ni marcas.

   Commit + `git -c push.negotiate=true push`. Espera a `origin/main:radar/rvNNN_slug/preparado.txt`: bucle `git fetch --depth 1 origin +refs/heads/main:refs/remotes/origin/main` cada 20 s, máx. 25 min. Después `git reset --hard origin/main`.
5. Comprueba `voces/completa.mp3` y mira las escenas con Read. Si alguna trae texto, una cara reconocible o un logo, bórrala junto a su `_depth.png` y `preparado.txt`, cambia el prompt y repite el paso 4.
6. Monta: `python3 -I tools/radar_motion.py radar/rvNNN_slug /tmp/rvNNN_slug.mp4`. Revisa 6–8 fotogramas: nada se sale ni se solapa, y se lee bien. **Comprueba la duración con ffprobe: debe ser de 62 s o más.** Si sale más corto, alarga el guion con más datos verificados, borra `voces/completa.mp3` y `preparado.txt` y repite desde el paso 4.
7. Sube: `bash tools/subir_largo.sh rvNNN_slug /tmp/rvNNN_slug.mp4` y espera `origin/main:largos/rvNNN_slug/url.txt`.
8. Metricool (createScheduledPost) **hoy a las 13:00** (Europe/Madrid). Si ya son más de las 12:50, prográmalo para dentro de 10 minutos.
   - `providers`: `[{"network":"tiktok"}]` (SOLO TikTok), `media`: `[contenido de url.txt]`, `draft`: false, `autoPublish`: true
   - `text`: 1–2 frases con la pregunta gancho + pregunta al público + 4–6 hashtags (#loquesebusca #noticias #tendencias #radarviral + 1–2 del tema) + línea en blanco + "Voz creada con IA."
   - `tiktokData`: `{"privacyOption": "PUBLIC_TO_EVERYONE", "disableComment": false, "disableDuet": false, "disableStitch": false, "isAigc": true, "autoAddMusic": false, "commercialContentThirdParty": false, "commercialContentOwnBrand": false, "title": "pregunta gancho (máx. 90 caracteres)"}`
9. Añade una línea a `historias/HISTORIAL_RADAR_VIRAL.md` (NNN | fecha | tema | fuentes) y haz push. Resume: tema, título y hora de publicación, con las fuentes.

Si algo falla, no programes nada a medias y explica el error.

**Ilustraciones (obligatorio):** pon al menos 4 elementos `imagen` en el vídeo (en escenas distintas; `alto` 450–600). Si al acabar la Action falta alguna `imgs/escena_N.jpg`, NO la sustituyas por tarjetas de texto: borra `preparado.txt`, cambia algo mínimo en `historia.json` (p. ej. `"reintento_imagenes": 2`), haz push y espera otra vez (la Action vuelve a intentarlo y, si Cloudflare ha agotado su cuota gratuita, usa Pollinations). Solo si tras 2 reintentos sigue faltando, quita ese elemento `imagen`.
