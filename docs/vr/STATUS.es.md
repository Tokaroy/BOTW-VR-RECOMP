# BOTW VR: estado

*In English: [STATUS.md](STATUS.md)*

Resumen corto de lo hecho y lo que falta, al **2026-11-24** (release
[vr-2026.11.24.6](https://github.com/guideahon/BOTW-VR-RECOMP/releases/tag/vr-2026.11.24.6)). Cada feature con sus tres
controles (implementada, validada por IA, validada en el visor): [FEATURES.es.md](FEATURES.es.md). Lo hecho día a
día: [DEVLOG.es.md](DEVLOG.es.md).

**Números:** 183 features; 165 implementadas, 137 validadas por los tests automáticos (fake_xr, el simulador de
manos), 4 validadas en el visor, ninguna fallando en el visor. I04 (las ventanas de objetos) y C35 (un menú rápido no
gira la vista) se arreglaron y se validaron en el visor el 2026-11-24.

## Hecho el 2026-11-24

| ID | Qué | Cómo se comprobó |
|---|---|---|
| I04 | Ventanas de objetos (la caja del cofre, el objeto nuevo, la descripción del inventario, los corazones) del tamaño y en el lugar del juego | memoria de PauseMenuInfo en plano contra VR, capturas; validado en el visor |
| C35 | Cerrar un menú rápido ya no gira la vista | el giro de la cámara se descarta (línea de log); validado en el visor |
| U07 | Bombas de runa lanzadas con el gatillo derecho (caían a los pies); un lanzamiento sin mover la mano va adonde mirás | fake_xr: bombas redondas y cuadradas salen de las manos, el lanzamiento girado hacia la vista |
| O11 | Sin congelamientos por la ventana del monitor: jugando no se actualiza | fake_xr: ninguno de 2 s en 9 corridas (antes: la mitad) |
| O12 | Barreras más livianas entre pases de render en VR | 88,8 -> 96 fps en el visor; capturas iguales |
| O13 | Las sombras del sol una vez por par estéreo (corregido el ojo del cuadro: se leía un cuadro corrido) | 108 -> ~111-114; 0,07-0,16% de píxeles que cambian entre cuadros, como sin |
| O14 | La capa del HUD una vez por par estéreo | 86,7 -> 88,8; `test_vr_game.py` hud |
| O15 | Linux: la geometría del juego en memoria de video (seguimiento de escrituras con userfaultfd + PAGEMAP_SCAN) | 95,6 -> 107; en plano 225 fps igual |

Velocidad, solo Linux (fake_xr, RTX 3090, ojos de 1718x1800, Meseta de los Albores, mediana de 3): **85 -> ~111 fps en
el visor** (release vr-2026.11.24.6). Detalle: [DEVLOG.es.md](DEVLOG.es.md).

## Para probar en Windows

Nada del trabajo de rendimiento se midió en Windows. Mismo lugar y configuración cada vez, el contador de fps del juego
(o el del visor) con la cabeza quieta ~30 s, y `savagewind.log`:

1. **Los fps, vr-2026.11.24.3 contra vr-2026.11.24.6.** Windows ya tenía la geometría en memoria de video (O15 es solo
   Linux), así que la ganancia debería ser menor que el +30% de Linux.
2. **Cada cambio por separado** (una variable de entorno puesta antes de arrancar, de a una, contra ninguna):
   `SAVAGEWIND_VR_SHADOWS_ONCE=0` (O13), `SAVAGEWIND_VK_BARRIER_FRAG=0` (O12), `SAVAGEWIND_VR_MIRROR=1` (O11). Cada una
   por separado debería ir más lento que ninguna.
3. **Congelamientos (O11):** mover la ventana del juego en el monitor mientras se juega; el visor no debería frenarse.
   Con `SAVAGEWIND_VR_MIRROR=1`, lo mismo, para saber si en Windows también pasaban.
4. **La imagen:** sombras cerca de árboles y rocas con la cabeza quieta (sin parpadeo en ningún ojo, O13); terreno,
   pasto, agua, fuego, partículas, el HUD y el inventario como antes (O12, O14); la caja del objeto del cofre y la
   descripción del inventario a su tamaño (I04).
5. **La segunda cola del espejo** (O11): el log dice `presents on a thread of their own (second queue)` en NVIDIA Turing
   o más nuevas y en AMD; en una NVIDIA más vieja (GTX 10xx) no tiene que decirlo, y el juego no tiene que cerrarse en
   los primeros cuadros.
6. **Arreglos:** I04, C35, U07 (las bombas de runa lanzadas con el gatillo van adonde mirás).

Reportar: "Windows: .3 X fps, .6 Y fps", y los fps con cada variable.

## Hecho el 2026-11-22 / 23

| ID | Qué | Cómo se probó |
|---|---|---|
| V08 | Resolución de ojos 1440 líneas por defecto, en vivo (sin reiniciar) | `test_vr_eye_res.py`: 1080, 2160, 1440 jugando |
| V17 | Upscaler Snapdragon GSR (una pasada, liviano, para visores standalone) | compila y corre; calidad de imagen sin medir |
| V18 | Filas de rendimiento en la página VR: overlay de FPS, escala de render, upscaler, su modo (Dinámico), anti-aliasing | las mismas filas de las páginas de Video |
| O10 | Steam Frame / cualquier sistema que deja la ventana más chica: el mundo a la resolución de los ojos y bien fusionado | `test_vr_fixed_window.py` (ventana fija en 1280x720) |
| H05 | El overlay de Savage Wind: mantener 0,6 s el botón menú | `test_vr_overlay.py` |
| H10 | Marcadores en el HUD flotante (nombres, fijado, pines del mapa) donde están | contadores; no visto en una captura |
| H11 | La rueda de stamina bajo los corazones en primera persona | contadores; no vista en una captura |
| B10 / B01 | El rig de los brazos: codos y hombros naturales, giro del antebrazo continuo y limitado | `test_vr_arm_rig.py`, vistas desde afuera (`SAVAGEWIND_VR_DEBUG_CAM`) |
| C34 | Escaleras: adelante sube mires donde mires | `test_vr_ladder.py` (el signo del giro en llano) |
| P11 | Nadar: el ojo justo sobre el agua | jugado en el Dominio Zora |
| - | Más alcance de los brazos (el ojo 22 cm adelante) | `test_vr_game.py` arms |
| - | Releases para Windows, Linux PC y Steam Frame desde un solo workflow | vr-2026.11.22.2, vr-2026.11.23 |

## Esperando el visor

Implementado y probado en el simulador, nunca visto en un visor: todo lo de arriba y casi toda la tabla (la columna
"Validada por humano" está en ⬜ en 175 filas). Las primeras para probar: **B10, B01, V08, V18, H10, H11, C34, G14,
O10**. Reportar por ID ("B10 ok", "H11 falla: ...") con `savagewind.log`.

## Falta

| ID | Qué | Por qué no está | Próximo paso |
|---|---|---|---|
| - | Animales y enemigos se congelan a pocos metros y solo se mueven de cerca (reporte del visor, 2026-11-24) | no se reprodujo en fake_xr (los jabalíes y pájaros cerca de la partida de prueba no quedaron a la vista) | una partida frente a animales que se congelen, VR contra plano |
| - | Más velocidad en VR: ahora el límite es el hilo que traduce (100%, ~1,3 us por draw; GPU ~80%) | los descriptor sets, texturas y vértices por draw ya están ajustados | costos por draw (sets 1,2 ms, preparación 1,1 ms por cuadro) |
| H10, H11 | Verlos en una captura | la partida de prueba tiene la stamina llena y no hay marcadores en el mundo | una partida más avanzada (enemigos, pines, la stamina en uso) |
| C34 | Probarlo en una escalera real | no hay escalera cerca de la partida de prueba | una partida o un teletransporte junto a una escalera |
| G14 | La guardia apuntada con la mano | probablemente no haga falta: Link gira hacia la vista al cubrirse | comprobar en el visor que bloquea los golpes del lado al que mirás |
| O07 | Renderizado foveado | el foveado del runtime se aplica a lo que la app dibuja en la swapchain, y los ojos se copian ahí; hace falta sombreado de tasa variable dentro del render del propio juego | trabajo de diseño en el renderer Vulkan |
| O08 | Vista de espectador (más ancha, sin HUD) para el monitor | sin empezar | mostrar en la ventana la copia sin HUD |
| V15 | Profundidad para reproyección | apagada por defecto: con Virtual Desktop se perdía la GPU | reintentar con el lock de cola de OpenXR que ya está |
| P14 | Cámara en tercera persona sin colisión | solo está la distancia | ingeniería inversa de la colisión de la cámara |
| P15 | La cámara montando una foca de arena | sin hacer | ingeniería inversa |
| B08 | La cabeza de Link conserva su sombra en primera persona | sin hacer | la pista son los flags de material de BetterVR 1.0.2 |
| U08 | Magnesis: girar el objeto con la muñeca | sin hacer | ingeniería inversa de la rotación de Magnesis |
| K09 | Escala de habitación completa (el cuerpo de Link movido con sus propios rayos) | está la simple (K07) | ingeniería inversa |
| C32, I06, O06, S12 | Validadas en parte por los tests | necesitan visor o corridas en Linux / runtime de Oculus | reportes desde el visor y desde Linux |

## Avisos sobre los tests

- La suite en el juego (`build/vr/run_suite.sh`, 24 tests, ~55 min) tiene algunos escenarios sensibles al tiempo
  (cinema, agacharse, menús, `swing_hits`) que pueden fallar una vez y pasar al repetirlos: las capturas de fake_xr
  frenan el juego unos 4 s.
- Después de un build de Linux, `build/vr/fake_xr.json` apunta al `.so`: regenerarlo con `make VR=1 fake-xr` en
  Windows.
