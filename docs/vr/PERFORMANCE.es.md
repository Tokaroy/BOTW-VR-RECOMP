# Rendimiento en VR: cómo se mide, dónde se va el tiempo, y por qué lo de BetterVR es más rápido

*In English: [PERFORMANCE.md](PERFORMANCE.md)*

## Por qué una recomp todavía no es más rápida que BetterVR en VR

El código del juego corre nativo acá, así que la simulación no es lo que nos limita. Lo que limita es cómo se arma un
cuadro estéreo:

| | Savage Wind VR (`SAVAGEWIND_VR_STEREO=1`, por defecto) | BetterVR 1.0.1 (Cemu) |
|---|---|---|
| Cuadros del juego por cuadro del visor | 2: uno por ojo (el juego al doble del visor) | 1 |
| Traducción de cada dibujo a Vulkan (CPU) | dos veces, una por ojo, en un solo hilo (`nvn-queue`) | una |
| Cada dibujo en la GPU | dos veces: dos cuadros separados | una, en dos capas (**multiview** de Vulkan: `gl_ViewIndex` elige la cámara de cada ojo) |
| Pasadas que no dependen del ojo (cascadas de sombra, cubemaps) | dos veces (una sola sale mal: [DEVLOG.es.md](DEVLOG.es.md) 2026-11-25) | una ("secciones mono") |
| Menos píxeles en los bordes | no | render foveado (su Cemu: `LatteView_RequestFoveation`) |

Medido acá (Windows, RTX 3090, ojos de fake_xr de 1718x1800, Meseta de los Albores, método abajo): **~102 cuadros por
segundo en el visor con un build de desarrollo, ~114 con el zip del release**; la GPU **~70% ocupada**; el límite es el
hilo que traduce, **~4,9 ms de CPU por cuadro del juego** (~3460 dibujos: descriptor sets 1,36 ms, preparación 1,28 ms,
texturas 0,71 ms, vértices 0,52 ms). Dos de esos por cuadro del visor: ~100 pares por segundo como máximo, sea cual sea
la GPU. BetterVR paga su traducción una vez por cuadro del visor.

No medido acá: los fps de BetterVR en esta máquina (necesita Cemu y el juego de Wii U). La comparación de arriba es de
las arquitecturas; números de jugadores que tengan los dos en el mismo visor y resolución son bienvenidos.

El prototipo de estéreo sincrónico ([SYNC_STEREO.md](SYNC_STEREO.md), `SAVAGEWIND_VR_SYNC=1`) simula una vez por par
pero igual traduce cada dibujo dos veces (repite las listas para el ojo derecho), más su propio costo: 85-87 fps contra
102. Solo no es el camino rápido; lo que encontró (qué constantes tienen la cámara, qué pasadas dependen del ojo) es lo
que multiview necesita.

## El plan: multiview

1. Las pasadas de la escena dibujadas una vez en objetivos de dos capas con `VkRenderPassMultiviewCreateInfo` (máscara
   0b11); los objetivos que dependen del ojo son los que marca el estéreo sincrónico (exec.c `sync_draw_dep`: dibujos
   que leen las filas de la cámara o texturas dibujadas por ellos); el resto (cascadas de sombra, cubemaps, compute)
   queda de una capa y se dibuja una vez.
2. Los shaders traducidos (runtime/nvn/maxwell/translate.c) leen las filas de la cámara por vista: el cbuf 3 de la
   escena, filas 0-13 (vista, vista-proyección, proyección, inversa), 21-34 (las del cuadro anterior), 42-53 (las
   cascadas de sombra desde el espacio de vista), la vista e inversa del bloque env (cbuf 4/5 en +0x2b0), la posición
   del ojo: de un segundo buffer cuando `gl_ViewIndex == 1`, con los valores del ojo derecho como los arma
   `vr_sync_patch` (vr_sync.c).
3. Las texturas leídas de un objetivo de dos capas leen la capa del propio dibujo (`gl_ViewIndex`).
4. El juego a un cuadro por cuadro del visor (la cámara del estéreo sincrónico: la del ojo izquierdo, los campos de los
   dos ojos para el culling).

El techo, medido: mono (`SAVAGEWIND_VR_STEREO=0`: una traducción y una imagen por cuadro del visor, los dos ojos con
la misma imagen) da **173 fps en el visor** contra 102 en estéreo (build de desarrollo, GPU al 68%): eso vale traducir
una vez por par del lado de la CPU. Multiview le vuelve a sumar a la GPU la segunda vista: hoy un par le cuesta ~6,9
ms (70% a 102), así que ~145 pares por segundo si no cambia nada más, más con las cascadas y los vértices una sola vez.
Esperado: ~1,4 veces los fps de hoy, limitado por la GPU.

### Avance

| Paso | Estado |
|---|---|
| La variante multiview de los shaders (`ShaderKey.multiview`, runtime/nvn/maxwell/translate.c `cbuf_ref`): el cbuf 3 declarado el doble de largo, la copia del ojo izquierdo y después la del derecho, cada lectura `gl_ViewIndex` x sus filas más adelante (`MV_CBUFS`, hasta `MV_MAX_ROWS` = 512 vec4 por ojo); `ShaderInfo.mv_cbufs` / `mv_rows` dicen qué enlazar | hecho; `SAVAGEWIND_VK_MV_TEST=1` traduce y compila la variante de cada shader de vértices y fragmentos que usa el juego, sin usarla: 0 fallas en ~400 shaders en la Meseta (2026-11-25), ~2/3 leen el cbuf 3 |
| El dispositivo con la feature `multiview` (`g_vk.multiview`) | hecho (un driver sin ella lo dice en el log) |
| Pipelines con `VkPipelineRenderingCreateInfo.viewMask` 0b11 (`PipeState.view_mask`) | hecho |
| Texturas de imágenes de dos capas leídas en la capa del propio dibujo (`ShaderKey.mv_tex`, translate.c `mv_layer_rewrite`: esos slots pasan a samplers de arreglo, cada `texture` / `textureLod` / `textureGather` / `texelFetch` recibe la capa `gl_ViewIndex`, `textureSize` su `.xy`) | hecho; `SAVAGEWIND_VK_MV_TEST=1` ahora también lee cada slot 2D por ojo: 0 fallas en ~400 shaders (una muestra en mvtest_sample.glsl) |
| Multiview jugando, `SAVAGEWIND_VR_SYNC=1 SAVAGEWIND_VR_MV=1` (todavía apagado por defecto; pone SMAA en lugar de TAA solo) | **funciona, 2026-11-25: 150 fps en el visor contra 104 en estéreo normal** (builds de desarrollo, 3 corridas intercaladas de cada uno, GPU 64%); las manos a 0,56 m y el parche lejano a 4 px en los dos modos, el brillo de cada ojo como en estéreo normal |
| El HUD aparte por ojo: la copia sin HUD de cada capa (`fg_copy_hudless`, `fg_hudless_img_r`; la composición detectada en una escena por ojo sólo para eso, `scene_composite_`), conservada para el present del ojo derecho | hecho: los dos ojos sin HUD, la capa del HUD con 2,2% opaco como en estéreo normal; **con la configuración por defecto 150,5 fps en el visor contra 98,3 en estéreo normal con TAA y 104,3 con SMAA** (3 corridas de cada uno) |
| TAA por capa (multiview todavía no dibuja vectores de movimiento; los efectos del runtime - CAS, gradación, FSR - saltean una escena por ojo para que los ojos no difieran), las pasadas del cubemap de 64x64 que todavía mezclan objetivos por ojo y simples, un visor real | lo siguiente |

Cómo funciona (exec.c, textures.c, device.c; líneas `[vk-mv]` del log):
- **Imágenes por ojo**: los objetivos que marca el estéreo sincrónico, y los simples que comparten pasada con ellos,
  reciben una segunda capa entre cuadros (`vk_make_stereo`, `vk_mv_frame_end`): los 2D dos capas, los arrays 2D el
  doble de capas, intercaladas (la capa L del ojo e en 2L + e) para que una pasada multiview dibuje dos capas seguidas.
  El juego sigue viendo una textura 2D (o su array): una vista 2D de una capa muestra el ojo que se está haciendo
  (`vk_eye_layer`, 0 mientras se traduce).
- **Pasadas multiview**: una pasada con todos sus objetivos por ojo empieza con `viewMask` 0b11 y vistas de las dos capas
  (`vk_mv_attach`); sus pipelines llevan `PipeState.view_mask` (enteros: sin bibliotecas de pipelines) y también el de
  los borrados. Una pasada que mezcla objetivos por ojo y simples dibuja sólo el ojo izquierdo (queda en el log; sus
  objetivos simples pasan a ser por ojo para el cuadro siguiente).
- **Shaders**: todo dibujo que lee texturas por ojo o está en una pasada multiview toma la variante multiview
  (`ShaderKey.multiview` y `mv_tex`): fuera de una pasada multiview `gl_ViewIndex` es 0, el ojo izquierdo. Sus slots
  reescritos son texturas de arreglo (`ShaderInfo.tex[i].type`), así el renderer enlaza una vista de las capas de los dos
  ojos; antes de ese arreglo todas las vistas leían la capa 0 y los dos ojos salían iguales.
- **La cámara**: el cbuf 3 enlazado como la copia del ojo izquierdo y después la del derecho, `mv_rows` vec4 cada una
  (hasta 512); la copia derecha corregida sobre el bloque entero del juego (`vr_sync_patch_any`: un vertex shader que
  sólo recibe las filas de la vista-proyección igual obtiene la del ojo derecho, hecha con la proyección del bloque),
  sólo en los bloques donde la pasada izquierda encontró la cámara (`sync_cam_buf`), y reusada mientras la memoria del
  juego debajo no cambia (como `guest_copy`).
- **Los dos presents**: device.c `backend_present` presenta el cuadro para el ojo izquierdo, después pone
  `vk_eye_layer` = 1 y lo presenta otra vez como ojo derecho (la imagen del visor copiada de la capa derecha,
  `vr_hud_prepare`).
- Pruebas: `stereo_depth.py` (profundidad de las manos, el parche lejano), `SAVAGEWIND_VR_SYNC_LOG=1` (pasadas, dibujos
  multiview, pasadas mezcladas y sus objetivos, la imagen presentada), `SAVAGEWIND_VR_MV_DEBUG=2` (la copia derecha del
  cbuf 3 en cero: un ojo derecho negro prueba que la vista derecha la lee), `SAVAGEWIND_VR_MV_SHOW=1` (el ojo izquierdo
  muestra también la capa derecha), `SAVAGEWIND_VR_MV_DUMPVS=1` (el GLSL de vertex shaders multiview).
- Lección: un `getenv` llamado en cada dibujo costó el 40% del hilo traductor (el getenv de Windows es lento): las
  variables se leen una vez (un `static` en el primer uso).

### El diseño, pieza por pieza (para quien lo continúe)

1. **Qué objetivos llevan dos capas.** Los que marca el estéreo sincrónico (exec.c `sync_draw_dep`: dibujados por un
   dibujo que lee las filas de la cámara, o a partir de un objetivo así). Los objetivos viven entre cuadros: una vez
   marcada, la imagen de la textura se rehace con 2 capas (como `vk_make_scalable_like` rehace una imagen a otro tamaño,
   textures.c) y queda así. Las cascadas de sombra, los cubemaps y parecidos nunca se marcan: una capa, dibujados una vez
   (el ahorro de GPU).
2. **Una pasada a objetivos de dos capas es una pasada multiview**: `VkRenderingInfo.viewMask` = 0b11 (exec.c
   `begin_pass`), las vistas de los adjuntos `VK_IMAGE_VIEW_TYPE_2D_ARRAY` sobre las dos capas, sus pipelines hechos con
   la misma máscara (parte de la clave del pipeline) y la variante multiview de los shaders.
3. **Sus constantes**: el cbuf 3 enlazado como un buffer de `mv_rows[3]` vec4 del ojo izquierdo y otros tantos del
   derecho (`ShaderInfo.mv_cbufs`), la mitad derecha la izquierda con la cámara del ojo derecho (vr_sync.c
   `vr_sync_patch`: vista, vista-proyección, proyección, inversa, las del cuadro anterior, las cascadas de sombra desde
   el espacio de vista). Otros cbufs con la cámara (el bloque env en cbuf 4/5, la posición del ojo en cbuf 6) se suman a
   `MV_CBUFS` de la misma forma si hace falta.
4. **Texturas leídas en una pasada multiview desde un objetivo de dos capas** leen la capa del propio dibujo: el slot
   de textura del shader declarado como textura de arreglo y la capa de la coordenada `gl_ViewIndex` (una máscara por
   slot en la clave del shader: qué slots son de dos capas en ese dibujo). Fuera de las pasadas multiview (la cadena de
   post-proceso del runtime, una copia para la CPU) una textura de dos capas se lee con una vista 2D de una capa: la del
   ojo que se está terminando.
5. **Borrados y copias** a un objetivo de dos capas cubren las dos; una copia de una textura de dos capas a una de una
   (una lectura para la CPU, la copia sin HUD) toma la capa del ojo que se está terminando.
6. **El cuadro**: el juego como lo tiene el estéreo sincrónico (un cuadro del juego por par, la cámara del ojo
   izquierdo; la cámara y el campo del derecho hechos en la misma actualización, vr_camera.c `vr_sync_frame`). En el
   present (device.c `backend_present`): la cadena de post-proceso (TAA por ojo, el HUD aparte, FSR, `vk_vr_images`)
   corre para la capa 0 y se presenta como ojo izquierdo, después para la capa 1 como ojo derecho: el segundo present
   que ya hace el estéreo sincrónico, sin repetir las listas.
7. **Lo que depende del ojo y no tiene dos capas** saldría igual en los dos ojos: el log de marcas
   (`SAVAGEWIND_VR_SYNC_LOG=1`) y `stereo_depth.py` (el parche lejano en 0 px, las manos a ~0,54 m) son las pruebas.

## Cómo medir

Todo corre contra **fake_xr** (`tools/vr/fake_xr`, lo compila `make VR=1`: `build/vr/fake_xr.dll`), un runtime OpenXR
sin visor: los mismos cuadros cada vez. Las herramientas están en `tools/vr/bench/` (Python 3 con numpy y Pillow para
las imágenes):

| Herramienta | Qué hace |
|---|---|
| `bench.py --case NOMBRE --exe EXE --save PARTIDA [--runs 3] [--env K=V ...]` | fps: por corrida ~12 s en el mundo en la Meseta, después 15 s medidos; la mediana como `SUMMARY` |
| `bench.py --ab RONDAS --exe-a A --exe-b B [--env-b K=V]` | A/B intercalado (A, B, A, B...): el reloj de la GPU y el ruido de la máquina cambian en minutos |
| `stereo_depth.py --case NOMBRE --exe EXE --save PARTIDA [--yaw 37] [--spin] [--walk]` | los dos ojos capturados tres veces con las manos adelante; el corrimiento de cada parche entre ojos y la profundidad que da (las manos ~0,54 m, las montañas lejanas ~0) |
| `profile.py --case NOMBRE --exe EXE --save PARTIDA` | las muestras del hilo traductor por función y línea (`--only archivo.swprof` para una captura ya hecha) |

Qué es cada número: **fps del visor** = `frames` del comando `vr` sobre el tiempo medido (lo que ve el jugador); **fps
del juego** = `frame` del comando `state` (el doble del visor en estéreo); **p95** = el comando `frames 10`; **GPU** =
uso de cada GPU según nvidia-smi; **congelamientos** = líneas del log `acquire blocked` / `present took` / `a wait for a
submission took` de más de 100 ms.

Reglas aprendidas a los golpes:
- **Una partida propia por corrida**: las herramientas copian `--save` a la carpeta de la corrida. Nunca les pases tus
  partidas.
- **Comparar lo comparable**: los zips del release se compilan con PGO (`make dist VR=1 DIST_PGO`), ~10% más rápidos que
  `make VR=1`. Desarrollo contra desarrollo.
- **Cada variante en su carpeta, con el nombre `savagewind.exe`**: la biblioteca del juego (`swgame.dll`) importa el
  ejecutable por ese nombre; una copia renombrada no arranca. Copiar `swgame.dll` y `swgame.dll.id` al lado.
- **Intercalar y repetir**: una corrida sola varía 5% (98-109 fps con el mismo build); 3-5 corridas intercaladas, la
  mediana.
- **Una captura frena el juego varios segundos** (fake_xr escribe PPMs): fuera de las corridas medidas, y separadas.
- **Girar la cabeza fuera de los ejes del mundo** (`--yaw 37`) al revisar cámaras: una vista alineada a los ejes se
  parece a una matriz identidad, y las búsquedas de la cámara encuentran falsos positivos.
- **Comparar ojos, no sólo cuadros**: revisar un ojo entre cuadros no vio las sombras mal del ojo derecho (2026-11-25).
- `SAVAGEWIND_VR_SYNC_LOG=1`, `SAVAGEWIND_VR_SYNC_DUMP=<w>`, `SAVAGEWIND_VR_SYNC_CENSUS=1` y `SAVAGEWIND_VR_SYNC_CHECK=1`
  ([../VR.md](../VR.md)) muestran qué marca el estéreo sincrónico, las constantes y el GLSL de una pasada, dónde está la
  cámara en las constantes, y si la vista hecha desde ojo/punto/arriba coincide con la del juego.
- El código del juego para leer: `generated/main/*.c` después de `make gen` (funciones `f_<dirección>`); los shaders
  traducidos: el GLSL que escribe `SAVAGEWIND_VR_SYNC_DUMP`. Las constantes de una pasada salen de `cbuf_info` en
  runtime/nvn/vulkan/exec.c; qué vec4 lee un shader está en `ShaderInfo.cbuf_rows` (runtime/nvn/maxwell/shader.h).
