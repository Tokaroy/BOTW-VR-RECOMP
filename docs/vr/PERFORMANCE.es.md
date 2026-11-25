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
| La variante multiview de los shaders (`ShaderKey.multiview`, runtime/nvn/maxwell/translate.c `cbuf_ref`): el cbuf 3 declarado el doble de largo, la copia del ojo izquierdo y después la del derecho, cada lectura `gl_ViewIndex` x sus filas más adelante (`MV_CBUFS`, hasta `MV_MAX_ROWS` = 2048 vec4 por ojo: las dos en un uniform buffer de 64 KB); `ShaderInfo.mv_cbufs` / `mv_rows` dicen qué enlazar | hecho; `SAVAGEWIND_VK_MV_TEST=1` traduce y compila la variante de cada shader de vértices y fragmentos que usa el juego, sin usarla: 0 fallas en ~400 shaders en la Meseta (2026-11-25), ~2/3 leen el cbuf 3 |
| El dispositivo con la feature `multiview` (`g_vk.multiview`) | hecho (un driver sin ella lo dice en el log) |
| Pipelines con `VkPipelineRenderingCreateInfo.viewMask` 0b11 | lo siguiente |
| Texturas de imágenes de dos capas leídas en la capa del propio dibujo (`ShaderKey.mv_tex`, translate.c `mv_layer_rewrite`: esos slots pasan a samplers de arreglo, cada `texture` / `textureLod` / `textureGather` / `texelFetch` recibe la capa `gl_ViewIndex`, `textureSize` su `.xy`) | hecho; `SAVAGEWIND_VK_MV_TEST=1` ahora también lee cada slot 2D por ojo: 0 fallas en ~400 shaders (una muestra en mvtest_sample.glsl) |
| Objetivos de dos capas para las pasadas que dependen del ojo (las marcas del estéreo sincrónico) | por hacer |
| La copia del ojo derecho del cbuf 3 (el parche de vr_sync.c) enlazada después de la izquierda | por hacer |
| La cadena de post-proceso (TAA, el HUD aparte, FSR) por capa, cada capa al swapchain de su ojo | por hacer |

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
