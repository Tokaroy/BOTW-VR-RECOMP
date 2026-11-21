# BOTW VR: bitácora de desarrollo

Registro de lo hecho, cómo se probó y lo que queda. Lo más reciente arriba. Los detalles técnicos de cada cambio están
en [../VR.md](../VR.md) (variables, tests) y la ingeniería inversa en [re-notes.md](re-notes.md); lo que hay que
probar con el visor puesto, en [CHECKLIST.md](CHECKLIST.md).

## 2026-11-20 (en el Quest: Magnesis no sube ni baja y es muy sensible; el parry no sale nunca)

- **Magnesis:** con la muñeca (como BetterVR) iba a los costados con nada y casi no subía ni bajaba. Probé después la
  dirección del brazo desde el pecho: con la mano cerca del cuerpo los ángulos salían igual de desparejos (subir 25 cm
  la mano subía 0,5 m el objeto). Ahora cuenta lo que la mano se movió desde que agarraste (suavizado 0,1 s, medido
  desde los pies de Link para que caminar no lo mueva): 0,6 m de mano a un costado lo giran un radián alrededor de
  Link, y hacia arriba lo suben tanto como está de lejos. Simulador (espada a 7 m, con 0,5 m): mano 25 cm arriba,
  +3,5 m; 30 cm a cada lado, ±35°, y volvió al centro; la muñeca sola, nada; el stick, de 2,5 a 20 m.
  `SAVAGEWIND_VR_TRACE_MAGNESIS=1` escribe en el log lo que se movió la mano y lo que se le dio al juego.
- **Parry:** 18 cm en 0,15 s a 1,6 m/s no salía nunca. Ahora 10 cm en 0,2 s a 1 m/s, hacia adelante o alejándose de
  la cabeza.

## 2026-11-20 (en el Quest: parry muy sensible; Magnesis movido con las manos)

- **Parry:** bastaba que la velocidad de la mano izquierda subiera 35 m/s² entre dos cuadros mientras cubrías, y el
  temblor del seguimiento o un movimiento chico lo lograban. Ahora hace falta empujar el escudo hacia adelante
  (horizontal, hacia donde mirás) 18 cm en 0,15 s, a 1,6 m/s o más, con 0,6 s entre parries.
  `test_vr_gestures`: el temblor, un empuje lento y un barrido de costado no hacen parry; un empujón sí.
- **Magnesis con las manos (como BetterVR):** mientras Magnesis sostiene algo, el objeto cuelga de la mano derecha en
  un palo imaginario: sigue sus movimientos y gira e inclina con hacia dónde apunta. El stick derecho solo lo acerca o
  lo aleja; no gira la vista. Se escribe en la acción de Magnesis del juego (distancia, altura, dirección), hallada
  con fnprof y `mem path` (re-notes). La cámara del juego gira sola para seguir al objeto; eso giraba la vista y, con
  ella, la mano en el mundo, y el objeto se escapaba de costado. Ahora, mientras tanto, cualquier giro de la cámara del
  juego se compensa en la vista. `SAVAGEWIND_VR_MAGNESIS_HAND=0` deja los controles del juego. Simulador (la espada
  a 7 m): inclinar la mano 20° la subió 2,15 m, girarla 25° a cada lado la llevó ±24° y al volver al centro volvió;
  stick arriba 1 s, a 20 m; abajo 1,5 s, a 3 m; stick a la derecha, sin giro; B la soltó.

## 2026-11-20 (en el Quest: ZL gira 180°, Magnesis no agarra, cadenas que se sacuden)

- **ZL gira la vista 180°:** ZL sin objetivo pone la cámara del juego detrás de Link, y Link puede estar mirando para
  cualquier lado (por ejemplo después de caminar hacia atrás). Ahora, en primera persona, un giro propio de la cámara
  del juego más rápido que 90°/s, con el stick derecho quieto, no gira la vista: se compensa en el giro de la vista.
  El juego camina a Link según la vista dibujada, así que el stick sigue yendo hacia donde mirás.
  `SAVAGEWIND_VR_KEEP_VIEW=0` lo apaga; el campo de `vr` `kept_turns` cuenta las compensaciones. Simulador: después
  de caminar hacia atrás, un toque de ZL giraba la vista 179,9° y ahora 3,5-6°.
- **Magnesis:** el juego además traza un rayo propio por el centro de la imagen y usa la mano de Link (la de la
  Pizarra Sheikah). Con el campo descentrado de cada ojo, el centro de la imagen no es donde mirás, y con la mano de
  Link movida al control, apuntando a otro lado, no agarraba nada. Probado en `fake_xr` estéreo: solo la mano o solo la
  cabeza no agarraban; con campo simétrico y los brazos sin mover, la cabeza sola levantó la maza 16 m. Ahora:
  - mientras hay una runa apuntada, cada ojo usa un campo simétrico: el centro de la imagen (la mira del juego) es
    hacia donde mira la cabeza;
  - mientras hay una runa apuntada, los brazos de Link quedan con la animación del juego;
  - las runas se apuntan siempre con la mira (la cabeza); se sacaron el rayo amarillo y la opción "Apuntar las runas
    con la mano".
  `test_vr_rune_aim` reescrito: la selección queda en el centro (0,5 0,5), no sigue a la mano y no se dibuja rayo
  (pasa en estéreo).
- **Cadenas y objetos que se mueven solos:** el par estéreo daba 95% del tiempo de juego al cuadro izquierdo y 5% al
  derecho. Los solvers de física corrigen el error de una restricción como error / paso, así que un paso 19 veces más
  corto que el siguiente patea las cadenas y las pilas de objetos. Ahora el par se reparte parejo (50/50): el juego
  corre como en plano a doble cuadro, igual que los ojos alternados de BetterVR. Cada ojo muestra su propio momento,
  medio paso aparte. `SAVAGEWIND_VR_PAIR_SECOND=<0..0,5>` prueba otra proporción. Simulador: caminar en todas las
  direcciones va bien y quieto no se desliza (0,00 m). Las cadenas en sí no se probaron (no hay cadenas en la partición
  de prueba).

`make VR=1 test-vr` y `test_vr_swing_hits` pasan.

## 2026-11-20 (en el Quest: sombras que parpadean en el ojo izquierdo, ataques y agachadas solos)

Reportado: el ojo izquierdo tiene sombras que aparecen y desaparecen (el derecho bien); Link ataca con movimientos leves
de la mano; se agacha solo con el jugador parado.

- **Sombras:** el atajo que deja al ojo derecho reusar los mapas de sombra del izquierdo (`SAVAGEWIND_VR_SHADOWS_ONCE`)
  hacía parpadear el **izquierdo**. Medido en `fake_xr` en estéreo con la cabeza quieta (60 capturas por ojo, píxeles
  que saltan más de 40 de un cuadro al siguiente): ojo izquierdo 2,8% con el atajo contra 0,4% sin él; el derecho ~1,9%
  en los dos casos. Las pasadas de sombra del juego parecen construir sobre los mapas que dejó el cuadro anterior, y las
  del ojo derecho salteadas ya no lo hacen. Ahora apagado por defecto (`=1` lo prende). `test_vr_shadows` ya no exige
  que el atajo suba los cuadros por segundo (hoy daba -13%).
- **Ataques:** el análisis de tajos y estocadas (el de BetterVR) toma un giro rápido de muñeca por un tajo (7 rad/s, la
  mano casi sin moverse). Para apretar el ataque del juego y prender el sensor del arma ahora además pide que la mano
  recorra de verdad (pico de 2 m/s en un tajo, 1,5 m/s en una estocada; un giro de muñeca no llega a 1) y un arma cuerpo
  a cuerpo en la mano de Link (sin arma, el botón de ataque la desenvaina). Lo descartado se cuenta en `swings_ignored`
  (campo de `vr`). `test_vr_swing_hits`: su tajo era solo un giro sobre el lugar; ahora la mano también recorre 0,5 m.
- **Agacharse:** Link no se agachaba: era la vista. La cámara sigue la altura de la cabeza de Link (para bajar al
  agacharse, nadar o montar), y la animación de ataque baja su cabeza 33 cm por medio segundo: cada ataque falso bajaba
  la vista como si se agachara. Ahora la vista sigue a la cabeza solo con las banderas de movimiento de agachado, nadando
  o a caballo.

Probado con el simulador de manos (estéreo): giros de muñeca y movimientos chicos sin arma o con arma → ignorados, sin
ataque; tajos reales (la mano 0,5-0,8 m en 0,2 s) → atacan; la altura del ojo queda en 1,55 m al atacar (antes bajaba a
1,22) y baja a 0,87 m al agacharse con el clic del stick izquierdo. `make VR=1 test-vr` pasa; `test_vr_game --scenario
motion` y `test_vr_swing_hits` pasan.

## 2026-11-20 (en el Quest: Link no giraba con la vista, el stick atrás avanzaba)

Reporte: al girar (la cabeza o el stick derecho) la vista gira pero Link sigue caminando para el mismo lado; a veces el
stick avanza siempre, aunque se empuje atrás; cajas y rocas se mueven solas.

Reproducido con el simulador de manos **en estéreo** (el modo del visor): con el stick atrás, con la cabeza girada 90°
a cualquier lado o después de girar con el stick derecho, Link corría siempre hacia el mismo lado (~32°, hacia donde
miraba al empezar) y, quieto, se deslizaba unos centímetros. En mono todo andaba (los tests de `test_vr_game.py` corren
en mono: no lo veían). Descartado: el giro del cuerpo hacia la vista (`SAVAGEWIND_VR_BODY_FOLLOW=0`, igual).

Causa: en estéreo cada par de cuadros (uno por ojo) avanza el tiempo del juego una vez: el izquierdo tomaba todo y el
derecho **0,001** de un cuadro de consola. El jugador y la física del juego no aguantan ese paso: Link no giraba hacia
el stick y lo que se apoya derivaba (con un paso así, cualquier cosa que se mueva en ese cuadro tiene velocidades
enormes: es lo más probable detrás de las cajas y rocas que se mueven solas). Arreglo (runtime/vr/vr_pair.h): el
cuadro derecho toma el 5% del tiempo del par y el izquierdo el 95% (probado: con 2% ya anda). Los dos ojos ven casi el
mismo momento (0,5 ms de diferencia a 90 Hz).

Probado en estéreo: atrás camina atrás (180°), la cabeza girada 90° a la izquierda o la derecha camina hacia donde
mira (0,1°), después del stick derecho también, y quieto no se mueve (0,00 m). `test_vr_pair` actualizado.

Sin confirmar: las cajas y rocas que se mueven solas (no hay una cerca del punto de prueba) y los "brazos estirados"
que se ven.

## 2026-11-20 (botones del Quest en los menús)

Reporte: el mapeo de botones confunde. Revisado contra los bindings de BetterVR para Touch (Quest;
`src/utils/controller_bindings.h`). En juego coincide: stick izquierdo mover (clic agacharse / catalejo), derecho girar
(clic inventario / mapa), B saltar, A interactuar / correr, Y izquierdo runa, gatillos usar lo de cada mano, grips
agarrar o los lugares del cuerpo. El error: BetterVR tiene **otro mapeo en los menús** y acá los gestos seguían
activos dentro del inventario, el mapa y los diálogos: B mandaba saltar (X) en vez de volver, el gatillo derecho
atacaba (Y: ordenar), A actuaba recién al soltarla y los grips mandaban A. Además los íconos de los botones salían de
teclado ("Más rápido [espacio]") porque los controles del visor no contaban como control.

Arreglo: en los menús (estado de pausa 2, el mapa, la pantalla de título, un diálogo) los botones van por su letra
como en BetterVR: A elige, B vuelve (y acelera el texto), X sostiene, Y ordena, gatillos L / R (pestañas), clic del
stick derecho cierra el inventario (+) o el mapa (-), sin gestos (`vr_pad_menu_buttons`, runtime/vr/vr_input_map.h).
Un botón apretado al abrir o cerrar un menú no cuenta hasta soltarlo. Usar los controles del visor pone los íconos de
control (letras de Nintendo). Probado con el simulador: clic derecho abre el inventario, gatillo derecho pasa a la
página siguiente, B cierra; clic mantenido abre el mapa y al soltarlo sigue abierto, B lo cierra; ya en juego B salta.
Test unitario `test_vr_input_map` (59 comprobaciones).

En juego, los íconos siguen siendo las letras del juego: su X (saltar) es la B derecha, su B (correr / guardar) la A
derecha mantenida, su Y (atacar) el gatillo derecho. BetterVR tiene lo mismo.

## 2026-11-20 (en el Quest: Link caminaba solo y la vista se separaba)

Reporte jugando en el visor: la vista quedaba dentro de una roca o separada del cuerpo, y Link caminaba solo sin tocar el
stick. Causa: la escala de habitación. Con la cabeza a más de 10 cm del ojo de Link empuja el stick hacia la cabeza y,
mientras tanto, deja el ojo quieto en el mundo moviendo el centro de la habitación con cada paso de Link, en cualquier
dirección. Si Link no podía llegar (una roca adelante) o algo lo movía para otro lado (la corriente, una pendiente), la
distancia no se cerraba nunca: el stick seguía empujando y la vista quedaba lejos de él.

Arreglo (runtime/vr/vr_camera.c): el centro sólo acompaña la parte del paso de Link que va hacia la cabeza, sin pasarse;
y si en 0,7 s no se acerca 2 cm, o la cabeza queda a más de 60 cm, la vista vuelve sobre Link y deja de caminar (log
`[vr] roomscale: Link could not reach the head`). Probado: `test_vr_roomscale.py` pasa (0,52 m caminados por un paso de
50 cm); contra una pared de la meseta, con la cabeza 40 cm adentro, Link no avanza, la vista vuelve a 0,18 m de él (el
ojo adelante de la cabeza) y el stick deja de empujar.

## 2026-11-20 (silbido, menú rápido, arrojar el arma: jugado)

`tools/vr/play_misc.py <partida>` (jugar, no test): en la meseta, con el simulador de manos.

| Qué | Cómo | Resultado |
|---|---|---|
| Silbido | las dos manos ahuecadas en la boca (8 cm adelante y 10 cm abajo de los ojos), los dos grips | el control manda d-pad abajo (`controller_buttons` 0x8000) mientras se mantiene; no hay caballo registrado en la partida, así que no viene ninguno |
| Menú rápido | la mano derecha sobre el hombro derecho, grip mantenido 1,2 s, stick derecho a la derecha, soltar | se abre (estado de pausa 4, la pantalla 0x52 dibuja) en la pantalla virtual con las armas; al soltar se cierra y queda equipada la elegida (porra boko) |
| Arrojar | con el arma afuera, la mano sobre el hombro, gatillo derecho mantenido (Link levanta el arma), un tajo hacia adelante y soltar | el arma sale volando hacia adelante (se ve en el aire), la mano queda vacía y el gesto pasa a "nada en la mano" |

El log de modelos (`SAVAGEWIND_VR_LOG_MODELS`) deja de nombrar el arma arrojada: para medir dónde cae hay que seguir el
actor nuevo, no el modelo del arma en la mano.

## 2026-11-20 (Magnesis, nadar, planeador: jugado)

Todo con el simulador de manos contra fake_xr, en estéreo. Herramientas nuevas (jugar, no tests de pasa/falla):
`tools/vr/play_magnesis.py <partida>` y `tools/vr/play_water.py <partida>`.

| Qué | Dónde | Resultado |
|---|---|---|
| Magnesis con la mano | la meseta: la maza soltada con el gesto de la cadera derecha | elegida en el menú de runas (Y izquierdo mantenido + stick derecho a la izquierda: el imán en el HUD), usada con Y, la mano apuntada a la maza (su posición leída del log de modelos), agarrada con el gatillo derecho y levantada con el grip mantenido y la mano arriba: subió de y 249,9 a 271,0 (21 m en 2 s: la subida es de velocidad, mientras la mano está arriba) |
| Nadar | Zora's Domain (`SAVAGEWIND_TEST_WARP=3315.61,255.64,-501.00`), buscando agua alrededor | **bit de nadar confirmado**: flags `0x410` (1 << 4 \| 1 << 10); 6 m nadados con el stick; el ojo a 0,25 m sobre la posición de Link: la vista a ras del agua, las manos debajo (imagen del visor) |
| Planeador | desde 40 m sobre Zora's Domain, salto y salto otra vez en el aire | la partida lo tiene: flags `0x8002` (en el aire + **planeador, 1 << 15, confirmado**); al aterrizar vuelve a 0x18000001 |
| Mirar abajo | la meseta, cuello simulado | a 40° se ven manos, pies y la correa; a 70° el pecho (lo normal de un cuerpo en VR) |

Observado, sin cambiar: planeando, los brazos de Link siguen a los controles (no sostienen la manija del planeador).

Palmeo al caballo: siete corridas más de `play_horse.py` sin montar (antes 2 de 3). Link llega a subirse (flags
`0x80000000`, el caballo corcovea) pero lo tira aunque se lo calme con L; con la resistencia de la partida (una rueda)
no alcanza para domarlo, y las dos veces que montó fueron caballos que no corcovearon. El palmeo sigue cubierto solo por
el test unitario; `play_horse.py` ahora palmea apenas monta y cuenta las trazas `[vr] riding: L (pet the horse)`.

`handsim.py`: reintenta el reemplazo del archivo en vivo cuando fake_xr lo tiene abierto (Windows lo rechazaba).
Traza nueva con `SAVAGEWIND_VR_TRACE_GESTURES=1`: `[vr] riding: L (pet the horse)` en cada palmeo a caballo.

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
