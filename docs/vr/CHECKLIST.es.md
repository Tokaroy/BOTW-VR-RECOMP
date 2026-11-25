# Probar con el visor

*In English: [CHECKLIST.md](CHECKLIST.md)*

Qué probar es la tabla de features, [FEATURES.es.md](FEATURES.es.md): cada fila tiene un ID, cómo probarla y tres
controles (implementada, validada por las pruebas automáticas de la IA, validada por una persona con el visor). La
columna humana se completa solo con lo que reporta el jugador.

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

## Antes de reportar un cierre o una pantalla negra

- Las primeras líneas `[vr]` del log dicen qué runtime y qué visor encontró.
- `SAVAGEWIND_VR=0` (o el acceso plano) muestra si también pasa sin VR.
