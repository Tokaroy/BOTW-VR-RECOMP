# BOTW VR Recomp (en español)

*In English: [README.md](../../README.md)*

**BOTW VR Recomp** es un fork de [Savage Wind Recomp](https://github.com/Revivedx/SavageWindRecomp) (un port nativo
para PC de *Breath of the Wild* 1.9.0, armado desde tu propia copia del juego) con un modo de VR para PC por OpenXR:
estéreo, seguimiento 6DOF de la cabeza, primera persona (o tercera), el HUD flotando adelante, los brazos de Link
siguiendo tus manos, los gestos de [BetterVR](https://github.com/Crementif/BotW-BetterVR), combate con movimiento, el
arco apuntado con las manos, Magnesis con la mano, tirar objetos con la mano y vibración.

No trae archivos del juego, claves ni firmware: necesitás tu propia copia, extraída de tu propia Nintendo Switch.

## Instalar

- **Versión publicada:** en [Releases](https://github.com/guideahon/BOTW-VR-RECOMP/releases) hay un zip para
  Windows y un AppImage para Linux. El código del juego se arma en tu PC desde tus archivos la primera vez.
- **Desde el código:** `Install BOTW VR.bat` en la raíz del repositorio pide tus carpetas y hace el resto.
- Paso a paso, cómo extraer tu juego y la forma manual: [SETUP.es.md](SETUP.es.md).

## Jugar

Todas las opciones de VR están en el juego: Pausa > Sistema > Opciones > **VR** (también desde las opciones de la
pantalla de título): vista, cinemáticas, giro, confort, manos, combate, arco, HUD, resolución de los ojos. Ahí mismo,
**Guía de controles** muestra qué hace cada botón y gesto.

El esquema de controles de fábrica (para Quest):

| Control | En el juego | Control | En el juego |
|---|---|---|---|
| A | aceptar, interactuar | B | cancelar, guardar (un toque) |
| stick izquierdo | caminar; clic: agacharse; mantenido: correr | stick derecho | girar; arriba: saltar; clic: inventario; mantenido: la mira |
| gatillo derecho | lo de la mano derecha (atacar, tensar, la runa); mantenido: menú de armas; cargando algo: soltalo para tirarlo | gatillo izquierdo | cubrirse y fijar, parry al apretar; mantenido: menú de escudos |
| grip derecho | sacar o guardar el arco; mantenido: menú de arcos | grip izquierdo | agarrar; con el arco afuera, mantenido: menú de flechas |
| Y | la runa; mantenido: menú de runas | X | el mapa |
| botón menú | pausa | las dos manos en la boca + los dos gatillos | silbido |

Los lugares del cuerpo (de BetterVR): hombro derecho + grip, el arma; hombro izquierdo, el arco; cadera izquierda, la
runa; cadera derecha mantenido, soltar lo de esa mano. Tajos y estocadas con el arma en la mano atacan donde va tu mano.

## Estado y pruebas

**Temprano.** Corre en un Quest 3 por Virtual Desktop. Cada feature, con lo que comprobaron las pruebas automáticas
(un runtime OpenXR falso y un simulador de manos) y una persona con el visor, está en la tabla:
**[FEATURES.es.md](FEATURES.es.md)**. Cómo probar y reportar por ID: [CHECKLIST.es.md](CHECKLIST.es.md). Lo que
BetterVR hace y este mod todavía no: [BETTERVR-GAP.es.md](BETTERVR-GAP.es.md). El plan: [../VR-PLAN.es.md](../VR-PLAN.es.md).
La bitácora: [DEVLOG.es.md](DEVLOG.es.md).

La referencia técnica (todas las variables, cómo se engancha al juego, las pruebas) está en inglés:
[../VR.md](../VR.md) y [re-notes.md](re-notes.md).

Como Savage Wind, está escrito casi entero por una IA (Claude Code), dirigida, probada y revisada por una persona. Se
agradece toda ayuda, desde features nuevas hasta jugarlo y reportar lo que ves: cualquiera con un agente de IA puede
tomar una fila de la tabla.

## Créditos

El diseño de VR, los controles, los gestos y la forma de Magnesis siguen a
[BetterVR](https://github.com/Crementif/BotW-BetterVR) de Crementif y colaboradores (su análisis de tajos, de Acudofy,
está portado bajo MIT en `third_party/BetterVR`). BetterVR a su vez agradece al
[proyecto de decompilación de BotW](https://github.com/zeldaret/botw) de leoetlino y otros.
