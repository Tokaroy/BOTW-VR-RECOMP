# Inventario de features para testear (VR)

Todas las features del mod (BOTW VR Recomp), de BetterVR (la referencia, para Wii U en Cemu) y de Savage Wind (el
recomp de PC en el que se apoya), en una sola tabla por tema, para ir probándolas en el visor. Hecho el 2026-11-21
leyendo el código de BetterVR (commit 2e06b31, `src/`, `resources/`), [VR.md](../VR.md), [BETTERVR-GAP.md](BETTERVR-GAP.md)
y el README de Savage Wind.

**Cómo usarla:** probá fila por fila y anotá en **Resultado** `OK`, `Falla: ...` o `Raro: ...`. Para reportar alcanza
con el ID (por ejemplo "C07 falla: la espada sale de la mano izquierda") y, si se puede, una captura de la ventana del
juego y el `savagewind.log`. Lo que sigue a las tablas ([Lo de BetterVR](#lo-de-bettervr-lo-que-faltaba-y-qué-se-hizo-el-2026-11-21)) no se
puede probar todavía: es lo que falta.

**Columnas:**
- **Origen**: `BVR` viene de BetterVR (portado), `Mod` es propio de este mod, `SW` es de Savage Wind, `BVR+Mod`
  portado y cambiado.
- **Estado**: ✅ hecho (probado solo con el simulador salvo que diga "visor"), 🟡 parcial, ❌ falta, ➖ no aplica.
- **Cómo probar**: con el esquema de controles Quest (el de fábrica). Las opciones están en Pausa > Sistema >
  Opciones > VR.

## V. Visor e imagen

| ID | Feature | Origen | Estado | Cómo probar | Resultado |
|---|---|---|---|---|---|
| V01 | Sesión OpenXR, arranca en el visor (Virtual Desktop / SteamVR / Link) | BVR | ✅ visor | Abrir con el acceso de VR: el juego aparece en el visor | |
| V02 | Sin visor o sin runtime sigue en plano y lo dice | Mod | ✅ | Abrir sin Virtual Desktop conectado: juega en el monitor, el log dice por qué | |
| V03 | Pantalla virtual para menús, carga y título | BVR | ✅ visor | Pantalla de título: una pantalla flotante adelante | |
| V04 | Estéreo real (una imagen por ojo, sin alternar) | BVR | ✅ visor | En juego, cerrar un ojo y otro: profundidad correcta, ojos no invertidos | |
| V05 | 6DOF: girar, inclinar, moverse con la cabeza | BVR | ✅ | Mirar alrededor, agacharse, asomarse: la vista acompaña sin retraso | |
| V06 | Campo visual de cada ojo propio (asimétrico) | Mod | ✅ | Bordes de la imagen nítidos, sin estirarse al mirar de reojo | |
| V07 | El mundo a velocidad normal en estéreo | Mod | ✅ | Pasto, agua, NPCs a velocidad normal (ni cámara lenta ni rápida) | |
| V08 | Resolución de los ojos (1080 a 2160) | Mod | ✅ | Opciones > VR > Resolución de los ojos, reiniciar: más nítido a más alto | |
| V09 | Escala de render (Video avanzado) afina la imagen | SW | ✅ | Subirla a 150%: más nítido, menos fps | |
| V10 | TAA en estéreo (historia por ojo) | Mod | ✅ | Anti-aliasing TAA: sin fantasmas de un ojo en el otro, sin bordes serruchados | |
| V11 | Sin profundidad de campo ni lens flare en VR | BVR | ✅ | Mirar al sol, mirar lejos: sin destellos ni desenfoque | |
| V12 | La ventana del monitor muestra solo el ojo izquierdo | Mod | ✅ | Mirar el monitor: no parpadea entre ojos | |
| V13 | Sombras del sol estables en los dos ojos | Mod | ✅ | Sombras de árboles sin parpadear | |
| V14 | Filas de Video que no sirven en VR ocultas | Mod | ✅ | Opciones > Video: no están pantalla completa, monitor, FOV, fps, VSync | |
| V15 | Profundidad para reproyección (`SAVAGEWIND_VR_DEPTH=1`) | BVR | 🟡 apagada | Solo si querés arriesgar: con VD se perdía el dispositivo | |
| V16 | Fallback si se pierde la sesión (sacarse el visor, cerrar VD) | Mod | ✅ | Cerrar Virtual Desktop jugando: el juego sigue en plano | |

## P. Vista y cámara

| ID | Feature | Origen | Estado | Cómo probar | Resultado |
|---|---|---|---|---|---|
| P01 | Primera persona, el ojo en la cabeza de Link | BVR | ✅ visor | Opciones > VR > Vista: Primera persona | |
| P02 | Cabeza de Link oculta (cara, pelo, gorro) | BVR | ✅ | Mirar abajo y alrededor: no se ve el interior de la cabeza | |
| P03 | Tercera persona (cámara del juego) | BVR | ✅ | Vista: Tercera persona; la cabeza mueve la mirada | |
| P04 | Distancia de la cámara en tercera persona | BVR | ✅ | Opciones > VR > Distancia en tercera persona | |
| P05 | Recentrar la vista | BVR | ✅ | Comando `vr recenter` o volver de un menú: la vista mira hacia donde mira Link | |
| P06 | Agachado, nadando o a caballo el ojo baja con la cabeza | Mod | ✅ | Agacharse (L3): la vista baja; nadar; montar | |
| P07 | El cuerpo de Link gira hacia donde mirás | BVR | ✅ | Mirar a un costado parado: el cuerpo acompaña, los brazos siguen llegando a las manos | |
| P08 | Las vueltas rápidas de la cámara del juego no giran la vista (ZL) | Mod | ✅ | Fijar enemigo con gatillo izquierdo: la vista no pega un tirón | |
| P09 | Sin "volteretas" de vista al recibir golpes fuertes | BVR | ✅ distinto | Que te pegue un Moblin fuerte: la vista se mueve pero no da vueltas | |
| P10 | Cámara al escalar (no meterse en la pared) | BVR | 🟡 | Escalar pegado a una pared: ¿se ve la pared por dentro? | |
| P11 | Cámara nadando (arriba del agua) | BVR | 🟡 | Nadar: ¿el ojo queda abajo del agua? | |
| P12 | Mira (Sheikah Slate) en la pantalla virtual con zoom | BVR | ✅ | R3 mantenido: la mira aparece en la pantalla plana; soltar vuelve al mundo | |
| P13 | Puertas de santuario y actores con LinkTag en estéreo | BVR | ✅ | Entrar a un santuario: la puerta se abre normal | |

## B. Cuerpo y manos

| ID | Feature | Origen | Estado | Cómo probar | Resultado |
|---|---|---|---|---|---|
| B01 | Brazos de Link siguen los controles (IK de dos huesos) | BVR | ✅ | Mover las manos: las de Link están donde están las tuyas | |
| B02 | La ropa / armadura sigue los brazos | BVR | ✅ | Ponerse otra armadura: mangas y guantes acompañan | |
| B03 | Giro de muñeca y antebrazo naturales | Mod | ✅ | Palma arriba / abajo: el antebrazo gira, la muñeca no se dobla rara | |
| B04 | Codos abajo, sin "alas de pollo" | Mod | ✅ | Manos adelante a la altura del pecho: codos hacia abajo | |
| B05 | Marcadores de los controles en menús y tercera persona | Mod | ✅ | En un menú: un disco celeste en cada mano. Opciones > VR > Mostrar los controles | |
| B06 | Lo que Link tiene en la mano se lee del juego | Mod | ✅ | Equipar espada, arco, escudo: los gestos saben qué tenés | |
| B07 | Antorchas, brazos de bokoblin y ramas como armas | BVR | ✅ (son armas) | Agarrar una antorcha o un brazo de bokoblin: se usa como espada | |

## C. Controles (esquema Quest)

| ID | Feature | Origen | Estado | Cómo probar | Resultado |
|---|---|---|---|---|---|
| C01 | Stick izquierdo: caminar hacia donde mirás | BVR | ✅ | Caminar mirando a un lado: va hacia donde mirás | |
| C02 | Caminar hacia donde apunta el control izquierdo | BVR | ✅ | Opciones > VR > Dirección al caminar: Control | |
| C03 | L3 click: agacharse; L3 mantenido: correr | Mod | ✅ | Mantener L3 caminando: corre | |
| C04 | Stick derecho: girar (suave / por pasos / solo cabeza) | BVR | ✅ | Opciones > VR > Giro; probar los tres | |
| C05 | Stick derecho arriba: saltar | Mod | ✅ | Empujar el stick derecho arriba: salta (no durante Magnesis) | |
| C06 | A: aceptar / interactuar | Mod | ✅ | Hablar, abrir un cofre con A | |
| C07 | B: cancelar / guardar (un toque, mantenido no corre) | Mod | ✅ | Mantener B: no corre | |
| C08 | Gatillo derecho: atacar con lo de la mano derecha | Mod | ✅ | Espada afuera: gatillo derecho ataca | |
| C09 | Gatillo derecho mantenido 0,6 s: menú de armas | Mod | ✅ | Mantener: menú rápido de armas; soltar elige | |
| C10 | Gatillo izquierdo: cubrirse / fijar + parry al apretar | Mod | ✅ | Escudo: apretar justo antes del golpe: parry | |
| C11 | Gatillo izquierdo mantenido 0,7 s: menú de escudos | Mod | ✅ | Mantener: menú de escudos | |
| C12 | A con el escudo arriba no hace parry | Mod | ✅ | Cubierto, apretar A: no hace nada | |
| C13 | Grip derecho: sacar / guardar el arco | Mod | ✅ | Grip derecho lejos del cuerpo: arco afuera; otra vez: guarda | |
| C14 | Grip derecho mantenido: menú de arcos | Mod | ✅ | Mantener: menú de arcos; al soltar no sale flecha | |
| C15 | Grip izquierdo con el arco afuera mantenido: menú de flechas | Mod | ✅ | Arco afuera, mantener grip izquierdo: menú de flechas | |
| C16 | Grip izquierdo: agarrar / interactuar | BVR | ✅ | Grip izquierdo frente a un objeto: lo levanta | |
| C17 | Y: runa; mantenido: menú de runas | Mod | ✅ | Y: saca la runa; mantener: menú | |
| C18 | X: mapa | Mod | ✅ | X: abre el mapa | |
| C19 | Botón menú: pausa | Mod | ✅ | Menú izquierdo: pausa | |
| C20 | R3: inventario; R3 mantenido: mira | BVR | ✅ | Click derecho: inventario | |
| C21 | En menús los botones son las letras del juego (A, B, X, Y, gatillos = L/R) | BVR | ✅ | Inventario: gatillos cambian de página | |
| C22 | Un botón mantenido al abrir/cerrar menú no se repite | Mod | ✅ | Abrir el mapa con X mantenido: no se cierra solo | |
| C23 | Íconos de botones del Quest en vez de Switch | Mod | ✅ | Video > Íconos de botones: Automático; los carteles muestran A, B, gatillos | |
| C24 | Vibración del juego en los controles | BVR | ✅ | Golpear o recibir un golpe: vibra | |
| C25 | Fuerza de la vibración | BVR | ✅ | Opciones > VR > Vibración y Fuerza de la vibración | |
| C26 | Modo zurdo (manos intercambiadas) | BVR | ✅ | Opciones > VR > Zurdo: todo pasa a la otra mano | |
| C27 | Esquema BetterVR (`SAVAGEWIND_VR_CONTROLS=bettervr`) | BVR | ✅ | B salta, A mantenido corre | |
| C28 | Esquema clásico (`SAVAGEWIND_VR_CONTROLS=classic`) | Mod | ✅ | Botones como un joystick, sin gestos | |
| C29 | Controles Index, WMR, Vive | BVR | ✅ sin probar | Solo si tenés esos controles | |
| C30 | Joystick común sigue funcionando junto a los de VR | Mod | ✅ | Conectar un control Xbox: también juega | |

## G. Gestos y lugares del cuerpo

| ID | Feature | Origen | Estado | Cómo probar | Resultado |
|---|---|---|---|---|---|
| G01 | Hombro derecho + grip: sacar / guardar el arma | BVR | ✅ | Mano derecha al hombro, grip: espada afuera; otra vez: guarda | |
| G02 | Hombro derecho grip mantenido: menú de armas | BVR | ✅ | Mantener 0,5 s: menú | |
| G03 | Hombro izquierdo + grip: arco | BVR | ✅ | Mano al hombro izquierdo, grip: arco | |
| G04 | Hombro izquierdo mantenido: escudos (con arma) o arcos | BVR | ✅ | Mantener 0,5 s: menú | |
| G05 | Cadera izquierda + grip: runa; mantenido: runas | BVR | ✅ | Mano a la cadera izquierda | |
| G06 | Cadera derecha grip mantenido: soltar lo de esa mano | BVR | ✅ | Opciones > VR > Gesto de soltar; mantener 0,5 s: el arma cae al piso (la tableta nunca) | |
| G07 | Lanzar el arma: gatillo mantenido en el hombro, soltar | BVR | ✅ | Arma afuera, gatillo en el hombro derecho, soltar: la tira | |
| G08 | Silbido: dos manos en la boca + los dos gatillos | Mod | ✅ | Viene el caballo; en la boca los gatillos no cubren ni atacan | |
| G09 | Silbido BetterVR: dos grips en la boca | BVR | ✅ | Esquema bettervr: grips en la boca | |
| G10 | Parry físico: empuje rápido de la mano izquierda cubriéndote | BVR | ✅ | Escudo arriba, empujar la mano izquierda adelante: parry | |
| G11 | Cubrirse levantando la mano del escudo | BVR | ✅ | Opciones > VR > Levantar la mano izquierda para cubrirse; mano frente al pecho: se cubre | |
| G12 | Vibración al tocar cada lugar del cuerpo | BVR | ✅ | Pasar la mano por el hombro: vibra | |

## A. Combate

| ID | Feature | Origen | Estado | Cómo probar | Resultado |
|---|---|---|---|---|---|
| A01 | Cortes y estocadas con movimiento (análisis de Acudofy) | BVR | ✅ | Opciones > VR > Combate con movimiento; cortar en el aire: Link ataca; estocada: estocada | |
| A02 | Movimientos lentos o de muñeca no cuentan | BVR | ✅ | Mover la mano despacio: no ataca | |
| A03 | Pega donde está la espada (su hitbox sigue la mano) | BVR | ✅ | Pegarle a un enemigo al costado: le pega donde está la mano | |
| A04 | Pega cuando la movés, más fuerte cuanto más rápido | BVR | ✅ | Golpe suave vs. golpe fuerte: distinto daño | |
| A05 | Un golpe por tajo | BVR | ✅ | Opciones > VR > Un golpe por tajo: no le pega dos veces al mismo | |
| A06 | Cortar árboles con la espada | BVR | ✅ | Hachazo a un árbol: cae | |
| A07 | El movimiento también hace el ataque de Link | Mod | ✅ | Opciones > VR > Los tajos hacen el ataque de Link: apagada, pega sin la animación | |
| A08 | Perfil fácil de movimientos | BVR | ✅ | Opciones > VR > Tajos fáciles | |
| A09 | Armas a dos manos (mandobles, lanzas) con las dos manos | BVR | ✅ | Opciones > VR > Agarre a dos manos; mandoble afuera, grip izquierdo sobre el mango: la hoja apunta a la otra mano | |
| A10 | Prender fuego / cortar cuerdas con motion | BVR | ✅ (son golpes) | Antorcha al pasto, cortar una cuerda | |

## R. Arco

| ID | Feature | Origen | Estado | Cómo probar | Resultado |
|---|---|---|---|---|---|
| R01 | Apuntar con las manos (de la cuerda al arco) | BVR | ✅ | La flecha sale por la línea mano-arco, no hacia donde mirás | |
| R02 | Arco de trayectoria (puntos amarillos) | BVR | ✅ | Tensar: se ven los puntos; Opciones > VR > Trayectoria del arco | |
| R03 | La flecha queda sobre el arco mientras tensás | Mod | ✅ | Tensar: la flecha apunta al arco, no a cualquier lado | |
| R04 | Al soltar un menú de arco no sale flecha | Mod | ✅ | Menú de arcos y soltar: no dispara | |
| R05 | Cámara lenta saltando con el arco | SW | ✅ | Saltar desde alto y tensar: cámara lenta | |
| R06 | Apuntar con la cabeza | Mod | ✅ | Opciones > VR > Apuntar el arco con las manos: apagado, sale hacia donde mirás | |

## U. Runas

| ID | Feature | Origen | Estado | Cómo probar | Resultado |
|---|---|---|---|---|---|
| U01 | Apuntar runas con la cabeza (retícula) | BVR | ✅ | Bomba / Stasis / Cryonis: apuntan al centro de la vista | |
| U02 | Gatillo derecho activa la runa | Mod | ✅ | Runa afuera, gatillo derecho: la usa | |
| U03 | Magnesis con la mano: izquierda / derecha | BVR+Mod | ✅ | Agarrar algo con Magnesis, mover la mano al costado | |
| U04 | Magnesis: subir / bajar con la mano | Mod | ✅ | Subir y bajar la mano: el objeto sube y baja | |
| U05 | Magnesis: stick acerca / aleja | Mod | ✅ | Stick derecho arriba / abajo | |
| U06 | Magnesis: la vista no gira sola | Mod | ✅ | Mover el objeto: la vista queda quieta | |
| U07 | Stasis, Cryonis, bombas | SW | ✅ | Usarlas normal | |

## I. Interacción con objetos

| ID | Feature | Origen | Estado | Cómo probar | Resultado |
|---|---|---|---|---|---|
| I01 | Levantar y tirar objetos | SW+BVR | ✅ | A frente a una maceta o roca chica: la levanta; gatillo derecho apretado, tirar la mano y soltar: sale hacia donde tiraste | |
| I02 | Ventana del objeto nuevo (primera vez) | Mod | 🟡 | Sale arriba a la izquierda y deformada: mandar captura | |
| I03 | Escaleras | BVR | 🟡 | Subir una escalera mirándola | |
| I04 | Montar a caballo | SW | ✅ | Subir y andar: la vista acompaña | |
| I05 | Planear (paravela), escalar, nadar | SW | ✅ | Probar cada uno | |
| I06 | Cocinar, hablar, comprar | SW | ✅ | Cocinar en una olla, comprar en una tienda | |

## K. Confort

| ID | Feature | Origen | Estado | Cómo probar | Resultado |
|---|---|---|---|---|---|
| K01 | Giro suave con velocidad (lenta / normal / rápida) | BVR | ✅ | Opciones > VR > Velocidad de giro | |
| K02 | Giro por pasos y su ángulo | BVR | ✅ | Opciones > VR > Ángulo del paso | |
| K03 | Giro solo con la cabeza | Mod | ✅ | Giro: Solo cabeza; el stick no gira | |
| K04 | Viñeta al moverse | Mod | ✅ | Opciones > VR > Viñeta de confort: Alta; caminar oscurece los bordes | |
| K05 | Sentado / parado | BVR | ✅ | Opciones > VR > Posición de juego: Parado usa tu altura real | |
| K06 | Ajuste de altura (-30 a +30 cm) | BVR | ✅ | Opciones > VR > Altura | |
| K07 | Roomscale: caminar en la sala camina a Link | BVR+Mod | 🟡 simple | Opciones > VR > Escala de habitación; dar dos pasos en la sala: Link camina; contra una pared, la vista vuelve | |

## H. HUD y menús

| ID | Feature | Origen | Estado | Cómo probar | Resultado |
|---|---|---|---|---|---|
| H01 | HUD separado, flotando adelante | BVR | ✅ | Corazones y minimapa en un panel delante, no pegados a los ojos | |
| H02 | HUD que sigue la mirada o queda fijo | BVR | ✅ | Opciones > VR > El HUD sigue tu mirada: apagado, queda abajo | |
| H03 | Tamaño y distancia del HUD | BVR | ✅ | Opciones > VR > Tamaño / Distancia del HUD | |
| H04 | Pausa, mapa, inventario en la pantalla virtual | BVR | ✅ | Abrirlos: pantalla flotante | |
| H05 | Menú de Savage Wind (overlay) en la pantalla virtual | Mod | ✅ | Abrir el menú del recomp en juego | |
| H06 | Overlay de rendimiento en el visor | BVR | ✅ | Video > Overlay de rendimiento: arriba a la derecha | |
| H07 | Opciones VR dentro del juego | BVR | ✅ | Pausa > Sistema > Opciones > VR | |
| H08 | Diálogos y textos legibles | SW | ✅ | Hablar con un NPC: se lee bien en la pantalla | |

## E. Eventos y cinemáticas

| ID | Feature | Origen | Estado | Cómo probar | Resultado |
|---|---|---|---|---|---|
| E01 | Modo de cinemáticas automático (tabla de 1497 eventos de BetterVR) | BVR | ✅ | Opciones > VR > Cinemáticas: Automático | |
| E02 | Cinemáticas siempre en primera / tercera persona / pantalla | BVR | ✅ | Probar cada modo con un evento (abrir un cofre) | |
| E03 | Barras negras en pantalla para cinemáticas | BVR | ✅ | Opciones > VR > Barras negras en cinemáticas | |
| E04 | Eventos sin bajada de fps (cofres, aparecer cofre) | Mod | ✅ | Limpiar un campamento: aparece el cofre a buen fps | |
| E05 | Eventos que deben ir a 30 fps (Kohga) en pantalla | SW+Mod | ✅ | Solo si llegás | |

## O. Opciones, instalación y plataforma

| ID | Feature | Origen | Estado | Cómo probar | Resultado |
|---|---|---|---|---|---|
| O01 | Instalador `Install BOTW VR.bat` | Mod | ✅ | Instalar de cero | |
| O02 | Acceso directo / exe de VR (`Savage Wind VR.exe`) | Mod | ✅ | Abrirlo desde Virtual Desktop | |
| O03 | Las opciones se guardan entre sesiones | Mod | ✅ | Cambiar algo, reiniciar: sigue | |
| O04 | Traducción al español de las opciones VR | Mod | ✅ | Idioma español: todo VR en español | |
| O05 | Comando `vr` en la consola (estado) | Mod | ✅ | Consola del juego: `vr` | |
| O06 | Linux | Mod | 🟡 sin visor | Solo si tenés Linux + SteamVR | |

## S. Savage Wind (recomp) dentro de VR

Lo que trae el recomp de PC. Lo importante es si funciona o rompe algo con VR puesto.

| ID | Feature | Origen | Estado en VR | Cómo probar | Resultado |
|---|---|---|---|---|---|
| S01 | Todo el juego y los dos DLC (1.9.0) | SW | ✅ | Usar algo del DLC (Máscara de Majora, la prueba de la espada) | |
| S02 | Presets gráficos (Potato a Savage) | SW | ✅ | Video > Preset: cambia la imagen en el visor | |
| S03 | Distancia de dibujado, sombras, calidad | SW | ✅ | Video avanzado: se nota en el visor | |
| S04 | DLSS / FSR 3 / FSR 4 / XeSS | SW | ❓ sin probar | Video > Upscaler: ¿se ve bien en los dos ojos? (recomendado apagado) | |
| S05 | Generación de frames FSR 3 | SW | ❓ sin probar | Probablemente no sirve en VR | |
| S06 | HDR | SW | ➖ | En VR la ventana queda SDR | |
| S07 | Gradación de color, filtros de daltonismo | SW | ❓ | Opciones > Color: ¿se aplica en el visor? | |
| S08 | Teclado y mouse | SW | ➖ | No aplica en VR | |
| S09 | Giroscopio / Steam Input | SW | ➖ | No aplica en VR | |
| S10 | Perfiles de guardado, backups, importar Wii U / Cemu | SW | ✅ | Cargar una partida importada | |
| S11 | Modo foto | SW | ❓ | ¿Funciona con VR puesto? | |
| S12 | Trucos, asistencias y teletransporte | SW | ❓ | Teletransportarse: la vista llega bien | |
| S13 | amiibo | SW | ❓ | Usar una runa amiibo | |
| S14 | Soltar / ordenar en el inventario rápido | SW | ✅ | El soltar por gesto lo usa | |
| S15 | 30 a 360 fps (fps libres) | SW | ➖ | En VR los fps los marca el visor (el doble de su Hz) | |
| S16 | Discord Rich Presence | SW | ❓ | Opcional | |

## Lo de BetterVR (lo que faltaba, y qué se hizo el 2026-11-21)

Las filas con ✅ ya se pueden probar; las demás siguen faltando. El detalle, con lo que hace falta para cada uno, está en
[BETTERVR-GAP.md](BETTERVR-GAP.md).

| ID | Feature de BetterVR | Estado acá |
|---|---|---|
| X01 | Tirar objetos con la mano (dirección y fuerza del lanzamiento real) | ✅ sin probar en juego (el save de prueba no tiene nada para levantar): cargando algo, el gatillo derecho apretado y soltado mientras tirás la mano lo lanza con la velocidad de tu mano |
| X02 | Objetos chicos en una mano (bombas, macetas, piedras, cucos), achicados a la vista | ✅ sin probar en juego: cargando algo, se dibuja en la mano derecha (bombas, macetas chicas, cucos...) o entre las dos manos (lo grande), achicado; la física sigue sobre la cabeza hasta el lanzamiento |
| X03 | Magnesis: girar el objeto con la muñeca | ❌ |
| X04 | Cuerda del arco que sigue la mano, la flecha en la cuerda, tensar más que la animación | ✅ la cuerda va a la mano que tensa (hasta 0,9 m); las ramas del arco no se doblan más que la animación |
| X05 | Escudo apuntado con la mano (dirección de la guardia) | ❌ (BetterVR lo agregó después de 1.0.1) |
| X06 | Sin sacudir la cabeza cuando no hay nada para sacar | ✅ Y o ZR sin nada de ese tipo encima de Link no llegan al juego (sin sacudida) |
| X07 | Escaleras con manejo especial | ❌ |
| X08 | Roomscale completo (mueve el cuerpo con sus propios rayos) | 🟡 versión simple |
| X09 | Cámara al escalar fuera de la pared, al nadar arriba del agua | 🟡 |
| X10 | Cámara en tercera persona sin colisión donde molesta | 🟡 solo la distancia |
| X11 | Vista en primera persona sin ragdoll (opción) | ➖ acá la vista nunca da vueltas |
| X12 | Presets de confort (Suave, Balanceado, Inmersivo) | ✅ Opciones > VR > Preset de confort: Suave, Equilibrado, Inmersivo |
| X13 | Zona muerta del stick y arreglo de rotación (Oculus Link) | ✅ Opciones > VR > Zona muerta de los sticks y Corregir la rotación de los controles |
| X14 | Marcadores de pantalla sobre el HUD flotante (nombres, objetivos) | ❌ |
| X15 | Posición del medidor de stamina en el HUD flotante | ❌ |
| X16 | Arreglos de transparencias de la interfaz | ❓ sin revisar |
| X17 | Menú propio dentro de VR (mantener X) con guía de controles | ✅ Opciones > VR > Guía de controles (cada botón y gesto); no hay un menú flotante aparte |
| X18 | Guía 3D de los lugares del cuerpo (tocar X) | ✅ Opciones > VR > Guía de los lugares del cuerpo: discos celestes en hombros, caderas y boca al acercar la mano (o siempre) |
| X19 | Sombra de la cabeza de Link en primera persona | ❌ |
| X20 | Opacidad: Link y su arma no se vuelven transparentes con la cámara cerca | ❓ revisar en tercera persona |
| X21 | Objetos no se ocultan por estar "fuera de cámara" en un ojo | ❓ revisar en los bordes de la vista |
| X22 | Cámara montando la foca de arena | ❓ |
| X23 | Renderizado foveado | ❌ |
| X24 | Vista de grabación / espectador (más ancha, sin HUD) | ❌ |
| X25 | Controles de Steam Frame | ✅ sin probar: perfiles de Steam Frame, Pico 4 / Neo 3 y Vive Cosmos |
| X26 | Arrancar directo al juego (BootDirectlyIntoGame) | ➖ el exe de VR ya arranca directo |
| X27 | Opacidad del arco de trayectoria | ✅ Opciones > VR > Trayectoria del arco: Completa, Tenue, Solo el punto de mira, Desactivada (en vez de una opacidad continua) |

## Donde este mod va más allá de BetterVR

- Nativo, sin emulador: mucho más fps (unos 110 pares estéreo por segundo a 1080 en una RTX 3090, medido en fake_xr).
- Lo gráfico de Savage Wind: DLSS, FSR, escala de render, distancia de dibujado, sombras, TAA por ojo.
- Juego 1.9.0 con los DLC.
- Esquema de controles propio para Quest, Magnesis con subir / bajar a mano, la flecha sobre el arco, íconos del Quest.
- Pruebas sin visor (fake_xr, simulador de manos).
