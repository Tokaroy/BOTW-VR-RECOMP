# BOTW VR: bitácora de desarrollo

*In English (shorter): [DEVLOG.md](DEVLOG.md)*

Registro de lo hecho, cómo se probó y lo que queda. Lo más reciente arriba. Los detalles técnicos de cada cambio están
en [../VR.md](../VR.md) (variables, tests) y la ingeniería inversa en [re-notes.md](re-notes.md); lo que hay que
probar con el visor puesto, en [CHECKLIST.es.md](CHECKLIST.es.md); el estado de cada feature, en
[FEATURES.es.md](FEATURES.es.md).

## 2026-11-23 (reporte sobre el rigging de los brazos)

- El jugador reporta que las muñecas siguen los controles, pero los brazos de Link quedan en posiciones poco naturales
  al mover o girar las manos (B01: implementación parcial, falla en el visor). En `vr_skel.c::solve_arm`, la orientación
  de la mano influye en el codo (`SAVAGEWIND_VR_ELBOW_FOLLOW`, por defecto 3) y el objetivo de la muñeca tiene un
  desplazamiento de 5 cm hacia atrás del control. Conviene comparar por separado movimiento y giro en el simulador y en
  el visor antes de cambiar cualquiera de los dos; es un punto probable para investigar, no una causa confirmada.

## 2026-11-23 (el alcance de los brazos; marcadores del HUD y la rueda de stamina en el HUD flotante)

- **P11, nadar:** jugado en el Dominio Zora (`tools/vr/play_water.py`, flags 0x410): la imagen del ojo muestra la
  superficie del agua desde justo arriba, siguiendo la cabeza de Link.
- **Para después:** C34 (escaleras: los flags de movimiento 0x10 / 0x12 marcan una escalera, pero el giro del stick
  ahí no se puede verificar sin poner a Link en una escalera en el simulador) y G14 (la guardia apuntada con la mano:
  todavía no se encontró la dirección de guardia del juego).
- **Brazos:** el ojo en primera persona 4 cm más adelante (22 cm) dejó las manos 4 cm más lejos de los hombros de
  Link, más allá de los 12 cm que el IK puede estirar un brazo (`test_vr_game.py` arms: 2,3 cm cortos). Ahora estira
  hasta 16 cm: 0,000 m.
- **H10, marcadores sobre el HUD flotante:** se parchea el mundo-a-pantalla de la interfaz (1.9.0 main+0xe1dde0,
  encontrado desde Projection::cameraPosToScreenPos de sead en main+0xeb44f8, su único llamador en juego) donde carga
  el resultado (sitio `ui_project`, main+0xe1de34). Nombres y marcadores se dibujan para todo el campo del ojo (45 a
  50 grados por lado) pero el panel del HUD cubre unos 30: quedaban corridos hacia el centro (un enemigo a 30 grados
  aparecía a 17). Ahora van donde la línea del ojo cruza el panel, como hook_PlaceScreenMarker de BetterVR (con el HUD
  siguiendo la mirada; `SAVAGEWIND_VR_UI_PROJECT=0` lo apaga). Es un sitio nuevo: el código del juego se vuelve a
  armar en el primer arranque.
- **H11, la rueda de stamina:** su llamador (main+0xe1ad80) pide un punto 1,8 m sobre los pies de Link, dentro de su
  cabeza en primera persona; ahí queda bajo los corazones (layout -482, +170, como BetterVR). Probado contra fake_xr
  por los contadores (`vr`: ui_stamina, ui_projected); la rueda todavía no se vio en una captura (la partida de prueba
  tiene la stamina llena).

## 2026-11-22 (Steam Frame: el mundo pixelado y los ojos que no se fusionan)

- Un tester con Steam Frame standalone (la AppImage aarch64): el mundo se veía pixelado con cualquier resolución de
  ojos o escala de render (los menús nítidos) y los ojos no se fusionaban (fatiga visual). La causa: ahí el sistema
  deja la ventana del juego de su propio tamaño, el juego dibujaba el mundo a ese tamaño y el frustum de la cámara
  tomaba la forma de la ventana en vez de la de la imagen de los ojos. Ahora el juego dibuja al tamaño de los ojos sea
  cual sea la ventana (device.c; la ventana muestra esa imagen escalada para entrar), el frustum toma la forma de la
  imagen de los ojos (xr_vulkan.c) y, con el HUD en la imagen, los ojos reciben una copia de la imagen del juego, no
  la ventana (exec.c).
- Probado contra fake_xr con la ventana fija en 1280x720 (`tools/vr/test_vr_fixed_window.py`): el juego dibuja a
  1374x1440, las swapchains de los ojos son de 1374x1440 y el desplazamiento entre ojos es el mismo que con la ventana
  con forma de visor (dx -3); antes, 1280x720 y el desplazamiento al doble (dx -6). Falta verlo en el Frame.
- La suite después de integrar la rama de la release: pasan 19 de 20 (agacharse, los menús de pausa y `swing_hits`
  fallaron una vez y pasaron al repetirlos). Queda: en `test_vr_game.py` arms, cada muñeca a 2,1-2,3 cm de su control
  contra un límite de 2 cm, igual sin este cambio (antes de la integración pasaba).
- El trabajo sin commitear (Snapdragon GSR, el overlay manteniendo el botón menú, ojos a 1440 líneas) revisado, la
  opción de resolución de ojos arreglada (elegir 1080 guardaba el 1440 por defecto), traducido a los otros 12
  idiomas y commiteado.

## 2026-11-22 (Beta 1 fixes de Savage Wind, BetterVR 1.0.2, el PC Maker; release vr-2026.11.22)

- **Upstream:** integrados los "Beta 1 fixes" de Savage Wind (2ae4b39: bindings de lock-on y menús, el mapa en
  ultrawide, los compute shaders leyendo copias de sus constant buffers, la fila "Magnesis: acercar", reintento de un
  compilado que se cae).
- **BetterVR 1.0.2:** montado y con la mano vacía, el gatillo derecho calma al caballo (L) en vez de sacar el arma
  (I08; `test_vr_gestures` 162 chequeos). Sus otros dos cambios no hacen falta acá: el parpadeo de los objetivos de
  las runas es un parche FPS++ de Cemu, y el pelo y el casco al mirar arriba no pueden aparecer con la cabeza oculta
  por sus huesos. Las banderas de material que encontró (bit 4 de las opciones de vista, el Z pre-pass) son la pista
  para B08, la sombra de la cabeza.
- **El PC Maker** (rama de otro agente, 098e8ba) integrado, con dos arreglos: con SAVAGEWIND_HIDDEN ningún diálogo de
  error deja colgada una prueba (ni el del runtime ni el del lanzador del AppImage), y el lanzador le pasa TERM / INT
  / HUP al juego y conserva la entrada de la terminal (probado con un runtime de prueba).
- **Las opciones de VR en todos los idiomas:** los 119 textos de Opciones > VR y su guía de controles traducidos a los
  otros 12 idiomas del menú; `tools/i18n_check.py` vuelve a pasar (el workflow Tests fallaba en main desde el
  2026-11-21).
- **Release:** `vr-release.yml` también arma el zip de Windows (make dist VR=1 en un runner de Windows) y ejecuta el
  AppImage x86_64 montado con FUSE antes de adjuntarlo. Sus primeros builds encontraron tres bugs de empaquetado,
  todos arreglados: la libjsoncpp del loader de OpenXR nunca se empaquetaba (vr-2026.11.21 necesita la del sistema),
  el AppImage de Steam Frame traía un loader x86-64, y el lanzador nuevo pisaba el fd 3 de keepalive del runtime del
  AppImage (se desmontaba debajo del juego). El AppImage x86_64 publicado pasa los 16 escenarios de VR (82 chequeos).
- **Pruebas (Linux, RTX 3090, fake_xr):** todas las unitarias (VR, Maker, bindings); `test_vr_game.py` 16 escenarios
  sobre la build nueva (dos chequeos que fallaron mientras otro juego usaba la misma GPU pasan solos). El AppImage
  publicado vr-2026.11.21 pasa los mismos 16 escenarios (83 chequeos) con su propia carpeta de datos.

## 2026-11-21 (la tabla como lista de control; docs en inglés y español; el build de Linux)

- [FEATURES.es.md](FEATURES.es.md) / [FEATURES.md](FEATURES.md) se generan desde [features.py](features.py): cada
  feature tiene tres controles, implementada, validada por las pruebas automáticas de la IA y validada por una persona
  con el visor. La columna humana sale solo de lo que reporta el jugador.
- Las docs están en inglés por defecto con la versión en español al lado (`*.es.md`); se pusieron al día las que
  estaban desactualizadas (README, instalación, el plan, la lista de lo que falta de BetterVR, la checklist, ahora una
  guía corta de cómo probar y reportar).
- Linux: `tools/linux/package.sh` arma el AppImage con VR (`make appimage VR=1`): trae el loader de OpenXR y arranca en
  VR. `.github/workflows/vr-release.yml` lo compila en GitHub y lo sube a un release: publicado en vr-2026.11.21
  (`Savage_Wind-VR-0.6.0-alpha.6-x86_64.AppImage`, con `libopenxr_loader.so.1` adentro). No probado en un Linux con
  visor.

## 2026-11-21 (lo que faltaba de BetterVR, primera tanda)

- **Lanzar con la mano:** la acción de lanzar lo levantado de 1.9.0 (su calc_ main+0xc76f54, del vtable 0x1cd4e20
  hallado por los parámetros ThrowSpeedF / ThrowSpeedY / SquatThrowSpeedF) llama a main+0xc76d60 en el cuadro de
  lanzamiento de su animación, que arma la velocidad en sp + 4. El parche `_grab_throw` (0xc76e20) la pasa a
  `vr_grab_throw`: con el gatillo derecho soltado durante un tirón de la mano, va la velocidad de la mano (la más
  rápida de los últimos 0,1 s, en el mundo, hasta 1,2 veces la del juego). "Cargando algo" es el bit 17 de player +
  0xc40, que pone la acción de levantar (main+0xc7721c, animación GrabUp) y saca el lanzamiento. Generado y compilado
  (233 sitios); no probado en juego: el save de prueba no tiene bombas ni nada para levantar cerca (test_vr_throw.py
  queda para un save que lo tenga).
- **Lo levantado en la mano:** en primera persona, el modelo sobre la cabeza va a la mano derecha (achicado a la
  mitad, la lista de BetterVR) o entre las dos manos. Mismo límite de prueba.
- **Cuerda del arco:** los huesos String_L_2 / String_R_2 del arco (hallados: 5 y 9 en Weapon_Bow_001) van a la mano
  que tensa. test_vr_bow pasa; en la captura del ojo la cuerda va del extremo del arco hacia la mano.
- **Sin sacudida de cabeza:** Y o ZR sin arma / arco encima (los modelos que vr_skel ve en las manos y la espalda)
  no llegan al juego. test_vr_bow y gestures pasan (no bloquea cuando hay).
- **Opciones:** Preset de confort (Suave, Equilibrado, Inmersivo), Zona muerta de los sticks (test_vr_input_map: 61),
  Corregir la rotación de los controles (el arreglo de BetterVR para el runtime Oculus), Guía de los lugares del
  cuerpo (con "siempre", fake_xr recibe 5 discos más por cuadro), Trayectoria del arco con modos, página Guía de
  controles. Perfiles de Steam Frame, Pico y Vive Cosmos.
- **Escalando:** el ojo iba adelante de la cabeza de Link, o sea dentro de la roca. Ahora va 0,3 m detrás de su
  cabeza (hacia donde mira su cuerpo). En el simulador, caminando contra la roca grande del Plateau hasta trepar
  (banderas 0x90): `climb_eye` 0,96 y la captura muestra la pared desde afuera.
- test_vr_game gestures: el chequeo esperaba el texto de antes del esquema Quest; arreglado.

## 2026-11-21 (silbido con los gatillos; opciones que no hacen nada en VR)

- **Silbido:** las dos manos a menos de 28 cm de la boca y los dos gatillos apretados (con los grips a 20 cm no te
  salía). Con las dos manos ahí, los gatillos no hacen otra cosa (ni cubrir, ni atacar, ni parry). `test_vr_gestures`
  (144).
- **Opciones:** en VR el visor fija la forma de la ventana, la frecuencia y el campo visual, y la ventana no es lo que
  ves: las filas de Video que no hacen nada ahí (pantalla completa, modo, monitor, tamaño de ventana, rellenar
  pantallas anchas, HUD en los bordes, campo visual, fps, VSync) ya no aparecen con VR. Nueva fila VR > Resolución de
  los ojos (1080, 1440, 1800, 2160; desde el próximo inicio; antes solo `SAVAGEWIND_VR_HEIGHT`): en fake_xr con 1440
  la ventana queda en 1374x1440. `test_vr_options` pasa. Lo que sí cambia la imagen en VR: el preset de gráficos y
  Video avanzado (escala de render, distancia de dibujado, sombras, anti-aliasing...).
- Revisado: arranca con VR y pasa la pantalla de inicio (el arreglo del cierre al iniciar, ahora con VR de verdad).

## 2026-11-20 (parry con el gatillo, menús de arco y flechas, la flecha sobre el arco, eventos lentos)

- **Eventos lentos (la causa):** en tu log, Demo040_0 (aparece el cofre) y Demo000_0 (abrirlo) iban a 38-46 fps
  dibujando lo mismo que el juego normal. El perfilador (prof, swprof) en el despertar de la nueva partida en fake_xr:
  el hilo que traduce los dibujos pasaba 18,8 ms por cuadro en "draw/pre", casi todo dentro de `event_at_30`
  (framepace.c), que VR pregunta en cada dibujo durante un evento (vr_world_view) y que leía una variable de entorno
  con getenv cada vez. Ahora la lee una vez. El despertar: de 88 a 260-318 fps (fake_xr, sin tope). Esto estaba desde
  antes de esta semana: cualquier evento en VR iba lento.
- **Gatillo izquierdo:** cubre y, al apretarlo, hace parry (A 0,06 s después de levantar el escudo). A mientras
  cubrís ya no hace nada (era el parry del juego). B ahora es un toque: mantenido ya no corre (correr: L3).
- **Grip derecho mantenido:** el menú de arcos (el arco tensado, ZR, y 0,3 s después la cruceta a la derecha); antes
  abría el de armas. Con el arco afuera, el grip izquierdo mantenido abre el de flechas (cruceta a la izquierda). Al
  soltar, B con ZR todavía apretado cancela el tiro: no sale flecha.
- **La flecha sobre el arco:** mientras tensás, el modelo de la flecha se gira sobre la línea de la mano de la cuerda
  a la del arco (por donde sale). En fake_xr: sin esto quedaba a 66° de esa línea; con esto, 0°. El tiro sigue
  saliendo por esa línea (test_vr_bow pasa).
- **Ventana del objeto nuevo arriba a la izquierda y deformada:** no se pudo reproducir; hace falta una captura.
- `test_vr_gestures`: 142.

## 2026-11-20 (controles propios para el Quest; la ventana del objeto nuevo; opciones en el juego)

- **Esquema Quest (nuevo predeterminado):** A acepta (A), B cancela / guarda / corre (B), stick derecho arriba salta
  (X), gatillo derecho usa lo de la mano derecha (ataque, arco, runa) y mantenido 0,6 s abre el menú de armas,
  gatillo izquierdo cubre / fija (ZL) y mantenido 0,7 s abre el de escudos, grip derecho lejos del cuerpo saca el
  arco y mantenido abre el de arcos, grip izquierdo agarra, Y la runa, X el mapa, el botón de menú la pausa. Los
  lugares del cuerpo siguen igual. Los íconos de los avisos siguen este esquema (saltar: el stick derecho arriba del
  juego). `SAVAGEWIND_VR_CONTROLS=bettervr` vuelve al de BetterVR. `test_vr_gestures` (133) y `test_vr_bow` pasan.
  Contra: mantener el gatillo izquierdo más de 0,7 s ya no cubre (abre el menú); para cubrir largo, la mano levantada
  con el escudo.
- **Ventana del objeto nuevo:** no se pudo reproducir (la partida de prueba no tiene un objeto nuevo a mano). En tu
  log, al recibir el objeto el juego pasó a la pantalla virtual y el mouse se tomó y soltó varias veces (una pantalla
  de menú). Ahora el log dice por qué un evento va a la pantalla virtual (`[vr] event ... on the virtual screen:`).
  De paso: el despertar de la nueva partida (Demo102_0) iba a la pantalla virtual porque la detección del visor de la
  Pizarra se disparaba con sus shaders; en un evento ya no cuenta. Ese evento en 3D es pesado (11 ms por cuadro desde
  la cabeza de Link, 44 pares por segundo en fake_xr), es la escena.
- **Opciones de calidad en el juego:** ya están: Menú → Sistema → Opciones (Video, Video avanzado, VR).

## 2026-11-20 (en el Quest: correr con L3, eventos a 30 fps, el arco, íconos del Quest)

- **L3 mantenido corre** (B mientras se mantiene, después de 0,25 s; un toque sigue siendo agacharse). El visor de la
  Pizarra pasó a R3 mantenido (antes R3 mantenido abría el mapa, que ya está en X mantenido).
- **Eventos a 45-48 fps:** en tu log, Demo017_0 (y Demo002_0) bajaron de 180 a 48-97 fps. Esos eventos se muestran en la
  pantalla virtual (el juego pone su estado de pausa), y ahí cada cuadro del juego esperaba un cuadro del visor y el
  final del anterior: con la latencia quedaba en la mitad. Ahora, en modo estéreo, la pantalla virtual va como el
  juego: dos cuadros del juego por cuadro del visor (el primero no se manda). Simulador, el despertar de la nueva
  partida (Demo102_0): de 95-100 fps a 175, y el tramo de 45 a 87-110.
- **Arco:** no se pudo reproducir (test_vr_bow pasa). Punto frágil arreglado: si en un cuadro el juego no mostraba el
  arco en la mano izquierda, el gesto lo daba por guardado y el gatillo derecho mandaba atacar (sacaba la espada en
  vez de tensar). Ahora el arco sacado con el gesto sigue siendo el arco mientras no se vea otra cosa en las manos.
  Cada gatillo derecho deja en el log qué hizo y qué mostraba el juego en las manos.
- **Íconos del Quest:** con los controles de VR (Botones en Automático) los avisos del juego se dibujan como los
  botones del Quest que hacen cada cosa (A, B, X, Y, LT, RT, L3, R3, menú); en menús y diálogos, las letras tal cual.
  Dibujados por Savage Wind (nada de Meta). Revisado con el volcado de la hoja de glifos en el simulador.

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
