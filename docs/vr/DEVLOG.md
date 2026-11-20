# BOTW VR: bitácora de desarrollo

Registro de lo hecho, cómo se probó y lo que queda. Lo más reciente arriba. Los detalles técnicos de cada cambio están
en [../VR.md](../VR.md) (variables, tests) y la ingeniería inversa en [re-notes.md](re-notes.md); lo que hay que
probar con el visor puesto, en [CHECKLIST.md](CHECKLIST.md).

## 2026-11-20 (a caballo; revisión del trabajo de otra IA)

### Revisión de lo hecho con otra IA (Codex)

| Cambio | Revisión |
|---|---|
| Commit `4b08705`: `vr` informa por mano `*_hand_active` / `*_hand_valid` / `*_hand_tracked` (sección siguiente) | correcto: pide el estado de la acción de pose y localiza el espacio bajo el lock de entrada; los tests `arms` y `lost` lo cubren. Es lo que hace falta para el diagnóstico de los controles reales del Quest |
| `test_vr_game.py`: `vr` con 60 s de espera | correcto: una lectura de GPU para las capturas de fake_xr puede frenar el presentador más de los 10 s por defecto |
| `test_vr_bow.py`: `--capture-every` (30 por defecto) y 60 s de espera | correcto: con capturas continuas el arco no llegaba al disparo |
| Jugado por Codex (fake_xr): caminar 5,64 m, dirección relativa a la vista con la cabeza girada 90°, agacharse 1,55 → 0,88 m; arco: la flecha siguió la línea de las manos (−19,5° contra −20,1° esperados), puntos de trayectoria solo tensado; runas por la mano (tres alturas, cielo / suelo) y por la cabeza; runa desde la cadera izquierda + gatillo derecho como A | coincide con lo medido acá |
| Scripts de exploración del caballo (`build/vr/codex_horse_*.py`, locales) | encontraron caballos en el establo Dueling Peaks pero no llegaron a montar: los del corral no se montan |

### A caballo (jugado, fake_xr, estéreo)

Herramienta nueva `tools/vr/play_horse.py <partida>`: aparece junto al establo Dueling Peaks, busca el caballo libre
más cercano (posición en vivo por `SAVAGEWIND_VR_LOG_MODELS=Horse_Link`), aparece agachado detrás de él según hacia
dónde se movía, presiona A y lo calma con L si corcovea, hasta que los flags digan "a caballo"; después cabalga.

| Qué | Resultado |
|---|---|
| Montar un caballo salvaje | logrado (a los ~13-28 intentos: huyen). Los del corral del establo no se montan |
| Bit "a caballo" | **confirmado en Switch**: flags `0x100000` (1 << 20), como el enum de BetterVR |
| Caminar con el stick | 7,4-12,7 m en 3 s |
| Espuela (A derecho, BetterVR) | más rápido: 11 m en 2 s |
| Freno (grip izquierdo = B) | 0,02-0,04 m/s en menos de un segundo |
| Altura del ojo montado | en la cabeza real de Link: ~2,9 m sobre el suelo (posición del jugador a 2,35 m, la cabeza 0,57 m más arriba); el giro del cuerpo no se aplica a caballo |
| Imagen del visor montado | pasto, árboles y las manos; el cuello del caballo no entra porque la cabeza simulada mira hacia donde mira la cámara, no hacia donde va el caballo |

Observado, sin cambiar: el grip izquierdo mantenido frena y, con el caballo ya quieto, el juego desmonta (en BOTW B
detenido = bajarse; BetterVR mapea igual). El palmeo para calmar (L) no se llegó a ver en el juego: Link se había
bajado antes (sigue cubierto por el test unitario). Un caballo salvaje recién montado tira a Link a los pocos
segundos si no se lo calma.

## 2026-11-20 (diagnóstico de controles)

- El comando `vr` ahora separa, para cada mano, acción de pose activa, pose válida y pose rastreada
  (`left_hand_*`, `right_hand_*`). Una sesión FOCUSED podía decir `controllers: true` aunque los controles de Quest no
  dieran posición. La simulación de manos no altera estos campos: muestran el estado de los controles reales.
- Probado: `make VR=1 -j8` y escenario `arms` de `test_vr_game.py` con `fake_xr`: ambas manos activas, válidas y
  rastreadas; 46 cuadros con los dos brazos resueltos, error máximo de muñeca 0,000 m. El escenario `lost` confirmó
  los seis campos en `false` tras perder la sesión y que el juego sigue en plano; `make VR=1 test-vr` pasó (1901
  comprobaciones). Falta verificar esos campos con los controles reales de Quest en la mano.

## 2026-11-19 / 20

### Probado en el visor real (Meta Quest 3 por Virtual Desktop, RTX 3090)

| Qué | Resultado |
|---|---|
| Crash "device lost" (GPU) a los pocos segundos de empezar | **Arreglado y confirmado**: ~3 min en dos sesiones sin pérdida del dispositivo (antes, segundos). Causa: Virtual Desktop envía sus propios timers de GPU en la cola de Vulkan de la sesión dentro de `xrBeginFrame`, sin sincronizar con nuestro hilo de grabación. Ahora todas las llamadas OpenXR que pueden enviar trabajo van bajo el lock de la cola (`XRQ`, runtime/vr/xr_vulkan.c) |
| Sesión | FOCUSED, 90 fps estables |
| Estéreo | 90 pares por segundo (el juego a ~180 fps internos) |
| Catalejo | pasa a la pantalla virtual y vuelve al 3D |
| Brazos con manos simuladas sobre el visor real | ambas muñecas en su objetivo (0 cm) |
| Controles reales | **sin verificar**: en esas pruebas Virtual Desktop no dio la posición de ningún control (¿dormidos o no sostenidos?) |

Con el visor apoyado (sensor de proximidad descubierto) la sesión queda en SYNCHRONIZED y no se muestra: es del
visor, no del juego.

### Herramientas nuevas

- **Simulador de manos** `tools/vr/handsim.py`: arranca el juego en VR y mueve cabeza y manos (posición y giro)
  mientras corre, por el archivo en vivo de fake_xr (`FAKE_XR_LIVE`). Poses predefinidas (incluida la pose real del
  Quest en reposo), `hand` / `handq` / `rel`, `move` (movimiento suave, con velocidad real), `tap`, `draw` (sacar el
  arma), `sweep` (girar una mano por pasos con captura), `shot` / `xshot` (ventana / lo que recibe el visor), `arms`
  (error de muñecas, flexión, giro del antebrazo, giro del cuerpo), `focus` / `unfocus`, `game <comando>`.
  ```
  python tools/vr/handsim.py --save <partida de prueba> "pose ahead" "wait 1" "shot ahead" arms
  ```
- **Modo híbrido sobre el visor real**: `--runtime-json <json de Virtual Desktop>`: el visor pone cabeza e imagen y las
  manos simuladas entran al juego por `SAVAGEWIND_VR_SIM_HANDS` (solo para los brazos; gestos y combate leen los
  controles reales).
- **Sonda** `build/vr/xrprobe.exe` (local): con `XR_RUNTIME_JSON` del runtime imprime `system 0` si hay visor,
  `system -35` si no.
- **Logs de desarrollo**: `SAVAGEWIND_LOG_NEW_FS` (cada shader la primera vez que dibuja), `SAVAGEWIND_WATCH_FS`
  (cuándo dibujan ciertos shaders), `SAVAGEWIND_LOG_SCREENS` ahora marca con `*` las pantallas que dibujan; el `vr`
  de control reporta `move_flags`.

### Cambios (todos con tests)

| Cambio | Por qué / cómo se encontró |
|---|---|
| Lock de cola OpenXR en todas las llamadas que envían | el crash de Virtual Desktop |
| Giro del antebrazo y codo que sigue a la mano | con el simulador: girar la mano 90° doblaba la muñeca; ahora el giro va al antebrazo; el codo se queda abajo (sin "alas de pollo") |
| El cuerpo de Link gira hacia donde mirás (como BetterVR) | corriendo de costado los brazos quedaban hasta 20 cm cortos; ahora 0. No al trepar, nadar, planear, montar o caer |
| Ancla "fresca" de cámara para brazos, arco y armas | como BetterVR: el esqueleto se calcula antes que la cámara del cuadro |
| El ojo sigue la cabeza de Link (agacharse, nadar, montar) | agachado la vista quedaba a altura de parado (1,55 → 0,9 m); el balanceo al caminar se filtra |
| El ojo adelante de la cabeza hacia donde mirás | mirando 180° atrás se veía la espalda de Link |
| Catalejo en la pantalla virtual con el zoom del juego | en VR se perdía el zoom y se veía borroso; detectado por 3 shaders de la lente (otros 2 también dibujan al apuntar Stasis, se descartaron) |
| Sin profundidad de campo ni destellos del sol en el visor | como BetterVR 1.0.1 |
| Escudo con la mano izquierda solo con escudo + arma de una mano, desde altura de pecho | antes fijaba objetivo (ZL) con la mano vacía |
| Trepando/planeando: A suelta al instante. A caballo: A, grip derecho acelera, izquierdo frena | como BetterVR 1.0.1 |
| A caballo: palmear el cuello con la mano vacía lo calma (L) | idea propia; solo test unitario (no hay caballo cerca de la partida de prueba) |
| Sacar un arma no cuenta como ataque (0,7 s) | jugando con el simulador: desenvainar del hombro se leía como estocada |
| Eventos antes de que Link esté en el mundo, en 3D | la suite completa detectó que la escena inicial del juego nuevo iba a pantalla plana |
| El giro del cuerpo solo a modelos pegados a un hueso de Link | revisión propia: un arma enemiga cerca podría haber girado con él |

### Ingeniería inversa

- **Flags de movimiento del jugador**: objeto jugador (`PlayerInfo + 0x60`) `+0xcec` en 1.9.0, mismos bits que el
  `PlayerMoveBitFlags` de BetterVR en Wii U (agachado `1<<2`, en el aire `1<<1`, trepando `1<<4|1<<7`, nadando
  `1<<10`, planeador `1<<15`, ragdoll `1<<19`, caballo `1<<20`). Encontrado comparando el objeto parado, agachado,
  saltando y trepando. Verificados: agachado, salto, trepar; el resto se toma del enum.
- **Catalejo**: no tiene pantalla de UI propia; se detecta por los shaders de su lente.

### Jugado con el simulador (estéreo, fake_xr)

Caminar (19 m), girar, saltar; arco desde el hombro izquierdo, tensado y disparado apuntando con las manos (arco de
trayectoria visible); Stasis apuntado con la mano a izquierda y derecha; espada: dos tajos y dos estocadas detectados
(potencia hasta 1,0); inventario y menú rápido de runas en la pantalla virtual; selección de Magnesis; trepar y soltar
con A; quitarse y ponerse el visor (foco).

### Tests

Suite completa (`build/vr/run_suite.sh`: test_vr_game + 19 tests) en verde tras arreglar `events`. Nuevos: escenario
`scope`, chequeo de agacharse en `firstperson`, Stasis no va a pantalla plana, archivo en vivo de fake_xr en
`test_fake_xr_session`, gestos de trepar / caballo / palmeo en `test_vr_gestures`, regla del escudo en
`test_vr_melee`.

### Pendiente

- Probar los **controles reales** del Quest (una pasada de 1 minuto con los controles en la mano).
- No probado en el juego por falta de objetos en la partida de prueba: escudo (el arma es a dos manos), Magnesis sobre
  metal, caballo, nadar, planeador.
- Mirando muy abajo (70°) asoma el interior del cuello de la túnica; con el movimiento real del cuello es menor.
- La cámara rune (foto) no se pudo probar: la partida no la tiene.
