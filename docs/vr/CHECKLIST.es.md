# Probar con el visor

*In English: [CHECKLIST.md](CHECKLIST.md)*

Qué probar es la tabla de features, [FEATURES.es.md](FEATURES.es.md): cada fila tiene un ID, cómo probarla y tres
controles (implementada, validada por las pruebas automáticas de la IA, validada por una persona con el visor). La
columna humana se completa solo con lo que reporta el jugador.

## Este build: qué probar y qué ignorar

Las notas de cada release dicen lo mismo (pedido de un tester, 2026-11-25). Se actualiza con cada release;
vr-2026.11.26.1:

- **Opciones > VR > Rendimiento (nuevo, encendido por defecto):** en el visor la Distancia de dibujado es Potato y el
  Antialiasing SMAA, diga lo que diga Video (el juego en plano mantiene lo de Video). Cerca de 25-30% más de cuadros
  por segundo en todos los modos de Renderizado. De cerca la imagen debería verse igual; a lo lejos hay menos árboles y
  edificios, y los bordes algo menos suaves. Apagalo para comparar y decí si la velocidad lo vale. La línea
  `[vr] performance:` del log dice cuál corrió.
- **Windows: Savage Wind Configuration se abre primero**, como en Linux (en las builds VR de Windows se salteaba).
  Configurá VR ahí, apretá JUGAR y queda abierta al lado del juego.
- **Tercera persona en Estéreo (desde 25.10):** girando la cámara con el stick derecho, los dos ojos deberían juntarse.
  Si todavía se ve mal, decí qué modo de Renderizado y mandá el log.
- **Parpadeo al cerrar el inventario o un menú:** no lo reproducimos en ningún modo. Si lo seguís viendo, decí qué modo
  de Renderizado, si estabas cerca de fuego (antorchas, faroles: en Estéreo su luz titila distinto en cada ojo porque
  cada ojo es un cuadro distinto del juego; Multiview no) y mandá `savagewind.log`.
- **Tamaño de las manos:** decí si se ven muy grandes o muy chicas y a qué distancia, y qué Escala del mundo y
  Separación de ojos usás.
- **Multiview (Funciones experimentales):** en nuestras pruebas los dos ojos coinciden en siete lugares (humo, nieve,
  noche y lluvia, el mar, el suelo) y es ~30% más rápido que Estéreo. Reportá lo que todavía difiera entre ojos.
- **Ignorar por ahora:** los marcadores sobre enemigos están en el panel del HUD, no a la profundidad del enemigo
  (conocido).

## Cómo probar

1. Abrí el juego en VR (el acceso de VR, `Savage Wind VR.exe` o el AppImage de Linux) y cargá una partida.
2. Elegí filas con **Validado humano** en ⬜ (sin probar), o las que cambiaron hace poco (la entrada más nueva de
   [DEVLOG.es.md](DEVLOG.es.md) las nombra).
3. Hacé lo que dice **Cómo probar**.

## Cómo reportar

Una línea por fila, con su ID:

```
C07 ok
G08 falla: el caballo no viene con las dos manos en la boca
I04 en parte: ahora sale centrada, pero sigue estirada
```

Cuando algo falla, si podés, mandá también:

- una captura de la ventana del juego en el monitor en ese momento (muestra el ojo izquierdo);
- el `savagewind.log` de la carpeta del juego (registra lo que hizo el modo VR: líneas `[vr]`);
- el visor, el runtime (VDXR de Virtual Desktop, SteamVR...) y su frecuencia.
- los pasos mínimos para reproducirlo, con el resultado esperado y el observado.

Para convertir un reporte en un caso de regresión automático, usá el runtime guionado y la guía de
[casos de regresión repetibles](TESTING.es.md). Un test que pasa con el runtime falso no reemplaza la prueba con visor;
las dos columnas de validación siguen separadas. No subas al repo partidas, archivos extraídos ni código generado; si
un issue necesita una partida, seguí las [reglas para contribuir](../../CONTRIBUTING.md).

La IA marca la fila (✅ anda, ❌ falla, 🟡 en parte) en [features.py](features.py), arregla lo que falló, y lo
arreglado vuelve a ⬜ hasta que se pruebe de nuevo.

## Steam Frame en standalone (ARM64)

El AppImage experimental para Linux ARM64 está en [Releases](https://github.com/guideahon/BOTW-VR-RECOMP/releases).
Estas filas hay que validarlas en el dispositivo; las pruebas de IA y la emulación no cuentan como prueba de visor o juego:

- **O10:** completar la configuración inicial y llegar al juego con los controles del Steam Frame. Si se frena, usá
  la ruta completa que muestra la pantalla de error (normalmente `~/.local/share/savagewind/savagewind.log`, o bajo
  `$XDG_DATA_HOME/savagewind/`; `SAVAGEWIND_DATA_ROOT` cambia la carpeta de datos) e indicá el porcentaje. El 82% es la etapa de
  compilación del código del juego; adjuntá el log entero porque el error visible puede decir solo `1 error generated`.
  Sumá la versión del
  AppImage y de SteamOS, el driver Vulkan, cuánto tardó la configuración y las opciones VR elegidas.
- **V08:** fijate si 1440 líneas por ojo se ven nítidas y fluidas; probá 1080 si cae el rendimiento. En Windows con
  escritorio 1920x1080 y la opción Pantalla completa guardada, elegí 1440 o 1800 líneas por ojo, reiniciá y confirmá
  que el log `[vr]` informa esa resolución y no 1080. Si sigue limitada, adjuntá las líneas `[window] VR` y de los
  swapchains de los ojos.
- **P01:** recentrá sentado a tu distancia normal. Contá si ves la nariz, la cara o el gorro; no deberías tener que
  inclinarte hacia adelante para ocultarlos. Para una comparación controlada, iniciá con `SAVAGEWIND_VR_EYE_FORWARD=0.22`.
- **Estéreo / escala:** mirá un objeto que se mueva rápido mientras girás la cabeza y comprobá que ningún ojo se atrase
  ni muestre un cuadro viejo. En Opciones > VR compará Escala del mundo y Separación entre ojos al 100%; si los objetos
  cercanos generan efecto de ojos cruzados, probá Separación entre ojos al 80%. Informá qué valores te resultaron
  cómodos y adjuntá el log si aparece `[vr] skipped stereo composition`.
- **C19 / H05:** tocá el botón menú del visor para pausar; mantenelo 0,6 s para abrir el overlay de Savage Wind y
  volvé a mantenerlo para cerrarlo. X debería seguir abriendo el mapa; no debería hacer falta el teclado.
- **S04:** compará Snapdragon GSR 1 con Off o FSR 1 en el mismo modo de calidad. Contá la nitidez, los artefactos y
  el rendimiento en los dos ojos; incluí la frecuencia del visor y la resolución.

## Antes de reportar un cierre o una pantalla negra

- Las primeras líneas `[vr]` del log dicen qué runtime y qué visor encontró.
- `SAVAGEWIND_VR=0` (o el acceso plano) muestra si también pasa sin VR.
