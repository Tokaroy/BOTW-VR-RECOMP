# BOTW VR: plan

*In English: [VR-PLAN.md](VR-PLAN.md)*

Objetivo: un modo VR de PC (OpenXR, 6DOF, estéreo) en Savage Wind Recomp con los fps de código nativo, portando lo que
BetterVR aprendió en Cemu. Todo detrás de un flag: sin `VR=1` (al compilar) y `SAVAGEWIND_VR=1` (al correr) el juego es
el de upstream.

## Dónde está (2026-11-21)

Las fases originales están hechas:

| Fase | Qué | Estado |
|---|---|---|
| 0 | Flag de compilación, loader OpenXR, matemática de poses y proyecciones, el runtime de prueba fake_xr, CI | hecha |
| 1 | Sesión OpenXR sobre el Vulkan del juego; la pantalla virtual | hecha |
| 2 | Seguimiento de la cabeza, la proyección del visor | hecha |
| 3 | Estéreo: un cuadro del juego por ojo, el reloj una vez por par | hecha |
| 4 | El HUD aparte; los menús en la pantalla virtual | hecha |
| 5 | Controles de VR (Touch, Index, WMR, Vive, Pico, Vive Cosmos, Steam Frame, simple) | hecha |
| 6 | Confort: giro, escala de habitación (simple), altura, HUD, modos de cinemática, viñeta, presets | hecha |
| 7 | Los brazos de Link por IK, su cabeza oculta, primera y tercera persona | hecha |
| 8 | Combate con movimiento, el arco con las manos, Magnesis con la mano, tirar con la mano | hecha |
| 9 | Rendimiento: campo y TAA por ojo; sombras una vez por par (apagado: parpadeo); multiview y modo Mono por completar | en parte |
| 10 | Publicación: instalador, zip de Windows, AppImage de Linux, página Opciones > VR | hecha |

El estado de cada feature, con lo que comprobaron las pruebas automáticas y una persona con el visor:
[vr/FEATURES.es.md](vr/FEATURES.es.md). La bitácora: [vr/DEVLOG.es.md](vr/DEVLOG.es.md).

## Lo que sigue

1. **Rendimiento VR.** Completar multiview, medir en CPU de gama alta y en hardware más lento, y planear el selector
   Automático / Compatibilidad / Multiview / Mono. El modo Mono comparte una imagen entre ojos, sin profundidad
   estereoscópica, y debe ser una opción explícita de accesibilidad/rendimiento. El plan ejecutable está en
   [vr/PERFORMANCE-PLAN.es.md](vr/PERFORMANCE-PLAN.es.md).
2. **Validación con el visor.** El jugador prueba las filas de la tabla (⬜ en la columna humana) y las reporta por ID
   ([vr/CHECKLIST.es.md](vr/CHECKLIST.es.md)); lo que falla se arregla primero.
3. **El resto de BetterVR** (filas ❌ en Implementado), cada una necesita código de 1.9.0 todavía por encontrar
   ([vr/BETTERVR-GAP.es.md](vr/BETTERVR-GAP.es.md)): girar con la muñeca en Magnesis, escaleras, escala de habitación
   completa, la colisión de la cámara en tercera persona, la cámara en la foca de arena, marcadores y la rueda de
   stamina sobre el HUD flotante, la sombra de la cabeza en primera persona.
4. **Gráficos:** renderizado foveado (un runtime que lo ofrezca, o sombreado de tasa variable en el backend Vulkan),
   una vista de espectador para el monitor, más pasadas dibujadas una vez por par.
5. **Upstream:** proponer a Savage Wind los ganchos genéricos (proyección, presentación, ritmo de cuadros).
