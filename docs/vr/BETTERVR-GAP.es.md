# BOTW VR contra BetterVR: lo que todavía falta

*In English: [BETTERVR-GAP.md](BETTERVR-GAP.md)*

BetterVR ([Crementif/BotW-BetterVR](https://github.com/Crementif/BotW-BetterVR), versión 1.0.2 del
2026-11-20) es la referencia que sigue este mod: un mod de VR para la versión de Wii U del juego, que corre en Cemu.
Este mod porta sus ideas al juego de Switch 1.9.0 recompilado de forma nativa por Savage Wind.

Todas las features, incluidas las de BetterVR, con su estado y cuánto están probadas, están en la tabla:
[FEATURES.es.md](FEATURES.es.md) (las filas de BetterVR dicen BVR). Esta página lista solo lo que BetterVR hace y este
mod todavía no, al 2026-11-22, con lo que necesita cada cosa. "Código del juego" son funciones o campos de 1.9.0 que
falta encontrar; las direcciones de Wii U de BetterVR solo dicen qué buscar ([re-notes.md](re-notes.md), en inglés,
cuenta cómo se encontraron las demás).

| ID en la tabla | Qué hace BetterVR | Qué hace falta |
|---|---|---|
| U08 | **Girar en Magnesis**: girar la muñeca gira el objeto agarrado (magnesis.cpp `hook_GetMagnesisHeldBodySpin`: una velocidad angular en su cuerpo rígido justo después de que el juego lo empuja) | código del juego: dónde el administrador de Magnesis (su instancia en main+0x1e15f18) empuja el cuerpo, y `RigidBody::setAngularVelocity` / `getTransform` |
| C34 | **Escaleras**: subir y bajar mire donde mire, sin quedar trabado detrás (player.cpp `hook_FixLadder`, `hook_StoreLadderState`) | código del juego: el estado de escalera y la dirección de subida |
| K09 | **Escala de habitación completa**: el cuerpo de Link movido adonde camina el jugador, con sus propios rayos contra el mundo (roomscale.cpp) | código del juego: la actualización de la posición del jugador y un rayo; acá se empuja el stick hacia la cabeza |
| P14 | **Colisión de la cámara en tercera persona** salteada donde molesta (camera.cpp `hook_SkipCameraCollision`) | código del juego: el paso de colisión de la cámara; acá solo está la distancia |
| P15 | **La cámara en la foca de arena** (game_state.cpp `hook_PlayerIsRidingSandSeal`) | código del juego: el estado de montar la foca |
| H10 | **Marcadores de pantalla en el HUD flotante**: nombres y marcadores donde la línea desde los ojos cruza el panel (interface_hooks.cpp `hook_PlaceScreenMarker`) | código del juego: la proyección de cámara a pantalla que usan los marcadores |
| H11 | **La rueda de stamina** ubicada para el panel del HUD (`hook_FixStaminaGaugeScreenPosition`) | código del juego: la posición en pantalla del medidor (los parches de diseño de UI de tools/patches.py podrían llegar) |
| B08 | **La cabeza de Link conserva su sombra** oculta en primera persona (head_visibility.cpp: los materiales de la cabeza fuera solo de la vista principal) | código del juego: las banderas de vista de los materiales del modelo gsys en Switch. BetterVR 1.0.2 (484f85e) muestra cuáles: borra el bit 4 de las opciones de vista (los pases de cámara) y el 0x8000 del estado del material (Z pre-pass seleccionable), sin tocar los bits 0 y 1 (la sombra); en Wii U las opciones de vista están en +0x3c, los estados en +0x44 y la cantidad de vistas en +0x90. Acá la cabeza se oculta todavía achicando sus huesos, así que no da sombra |
| O07 | **Renderizado foveado** (en el sombreado de su fork de Cemu) | el backend Vulkan: sombreado de tasa variable, o un runtime que ofrezca `XR_FB_foveation` (el VDXR de Virtual Desktop no lo ofrecía) |
| O08 | **Vista de grabación / espectador** (Punch In, Más ancha, Más ancha sin HUD) | una cámara aparte, más ancha, para la ventana del monitor |
| G14 | **La dirección de la guardia** tomada de la vista (camera.cpp `hook_OverrideGuardDirection`) | probablemente no haga falta: acá el juego lee la vista que dibuja, así que cubrirse mira hacia la vista; a comprobar con el visor |

Hecho desde la primera versión de esta lista (2026-11-21): tirar lo levantado con la velocidad de la mano, lo cargado
en las manos, la cuerda del arco a la mano, sin sacudida de cabeza, presets de confort, la zona muerta de los sticks y
la corrección de rotación de los controles, la guía de controles, la guía de los lugares del cuerpo, los modos del arco
de trayectoria, la cámara al escalar, y los controles de Steam Frame, Pico y Vive Cosmos; de la 1.0.2 (2026-11-22),
el gatillo derecho que calma al caballo con la mano vacía (I08). De la 1.0.2 no hace falta acá: el parpadeo de los
objetivos de las runas (un parche FPS++ de Cemu para lecturas diferidas de la GPU) y el pelo y el casco vistos al
mirar arriba (acá la cabeza se oculta por sus huesos, los del casco incluidos).

## Donde este mod va más allá de BetterVR

- **Nativo, sin emulador.** El juego de Switch 1.9.0 recompilado a x86-64: unos 110 pares estéreo por segundo a 1080
  líneas por ojo en una RTX 3090 (fake_xr), así que 90 Hz se sostiene donde Cemu sufre.
- **Lo de PC de Savage Wind**: DLSS, FSR, XeSS, escala de render, distancia de dibujado, sombras y TAA por ojo en
  estéreo.
- **El juego 1.9.0 con los dos DLC.**
- Builds de **Linux** (un AppImage) además de Windows.
- **Pruebas sin visor**: el runtime fake_xr, el simulador de manos y las pruebas de juego.
