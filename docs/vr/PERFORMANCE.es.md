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

Esperado (una estimación, no medido): la traducción una vez por par (~5 ms: un techo de CPU cerca de 200 pares por
segundo); la GPU pasa a ser el límite, hoy ~6,9 ms por par al 70%, menos con las cascadas y los vértices una sola
vez: más o menos 1,4 veces los fps de hoy, limitado por la GPU.

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
