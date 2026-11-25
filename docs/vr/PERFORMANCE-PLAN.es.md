# Plan de acción: rendimiento de VR

*In English: [PERFORMANCE-PLAN.md](PERFORMANCE-PLAN.md)*

*Estado: en ejecución. Actualizado el 2026-11-25 (tarde). Lo de abajo de "Estado actual" es el plan original; las
cifras y el estado vigentes son los de esta sección.*

## Estado actual (2026-11-25)

Medido en Windows, Ryzen 9 9950X3D (~5,3 GHz efectivos), RTX 3090 driver 616.92, fake_xr a 500 Hz, ojos de 1718x1800,
build de desarrollo, Meseta de los Albores, partida de scratch, 5 rondas intercaladas
([DEVLOG.es.md](DEVLOG.es.md)):

| Ruta | fps visor | × | ms por par (p95 / p99) | GPU | Estado |
|---|---|---|---|---|---|
| Estéreo (compatibilidad) | 98,5 | 1,00 | 10,15 (10,4 / 11,0) | 69% | **por defecto** (Automático) |
| Multiview | 147,5 | 1,50 | 6,78 (7,3 / 8,0) | 69% | experimental (Opciones > VR > Renderizado: Multiview); fue el modo por defecto unas horas del 2026-11-25, hasta que en el visor se vieron humo, suelo y marcadores en un solo ojo |
| Mono | 178,6 | 1,81 | 5,60 (5,8 / 6,1) | 64% | sólo si se elige; nunca automático |
| Estéreo sincrónico (prototipo) | 79,6 | 0,81 | 12,56 | 41% | investigación, oculto (`SAVAGEWIND_VR_SYNC=1`) |

- **Hecho:** el selector (Opciones > VR > Renderizado, también en el launcher; Automático elige Estéreo por ahora (Multiview cuando los dos ojos coincidan); Mono nunca automático); el fallback a Estéreo con
  un driver sin multiview; el giro suave en multiview (saltaba de a 0,35 rad) y la vista con el ancla de las manos;
  Mono comprobado (mismos bytes en los dos ojos, vistas desde el centro de la cabeza, una actualización por par); las
  herramientas (`vr frametimes`, `vr lead`, `test_vr_mono.py`, `test_vr_sun_flare.py`, `--mode` en los tests).
- **Sigue limitado por la CPU** en los tres modos (el hilo `nvn-queue` ocupado, GPU 64-69%): foveación o resolución
  dinámica todavía no ayudarían en este equipo.
- **Pendiente:** PGO contra PGO; un visor real (FPS, reproyección, `vr lead`, comodidad de Mono); una CPU más lenta
  (estimado, no medido: una de ~70% del rendimiento por hilo dejaría Estéreo bajo 72 Hz y Multiview dentro de 90 Hz);
  en multiview los vectores de movimiento por objeto, Escalado/Nitidez/Color por ojo y las pasadas de reflejos de 64x64
  mezcladas; los destellos del sol (un jugador reporta resuelto en 25,2; fake_xr muestra un velo y una raya roja en VR
  por defecto que hay que identificar); las manos al moverlas (reporte de 25,2: medir `vr lead` en el visor).

## Objetivo

Subir y estabilizar los cuadros por segundo de VR, priorizando las CPU más lentas sin perder la ruta de compatibilidad.
Ofrecer modos claros para que cada persona elija entre compatibilidad, estéreo multiview y una imagen mono compartida
por ambos ojos. La opción mono debe estar identificada también como una opción de accesibilidad para personas con
visión monocular; no debe activarse automáticamente.

## Diagnóstico y evidencia disponible

La medición de rendimiento más reciente se hizo en Windows, con una RTX 3090, fakeXR a 1718x1800 por ojo y una ruta de
la Meseta de los Albores. Dio aproximadamente 102 FPS de visor en build de desarrollo y 114 FPS en el zip de release
con PGO. La GPU estaba cerca del 70% de uso. El hilo serial `nvn-queue` tardaba unos 4,9 ms de CPU por cuadro del juego
al traducir unos 3460 dibujos. El usuario informa que su equipo usa un Ryzen 9 9950X3D; al repetir la prueba, registrar
explícitamente el modelo y confirmar que corresponde a esa medición.

El estéreo actual procesa dos cuadros del juego por par de ojos. Como aproximación, 4,9 ms por cuadro son unos 9,8 ms
por par, frente a 11,1 ms disponibles a 90 Hz. La cuenta no incluye todos los costos del runtime y no reemplaza una
medición de visor: indica que hay poco margen incluso en una CPU de gama alta. El benchmark en esa máquina no basta
para garantizar rendimiento en los equipos de otras personas.

Hay dos resultados que no deben confundirse con una solución estéreo lista para usar:

- `SAVAGEWIND_VR_STEREO=0` dio unos 173 FPS con la misma imagen en ambos ojos. Es evidencia de potencial de velocidad
  y punto de partida para el modo mono, pero falta implementar y validar su cámara centrada, salida y accesibilidad.
- El prototipo `SAVAGEWIND_VR_SYNC=1` dio 85–87 FPS frente a 102 del estéreo normal y presentó errores entre ojos
  (árbol oscuro, diferencias de sombras/brillo). Es una herramienta de investigación; mantenerlo oculto y fuera de las
  opciones para jugadores.

En la rama de rendimiento `win-perf-bench` (commit `c37abcc`) ya están la feature Vulkan multiview, la variante de
shaders y la reescritura de lectura de texturas por capa. La prueba `SAVAGEWIND_VK_MV_TEST=1` compiló unos 400 shaders
observados en la Meseta sin fallos. Es una comprobación de traducción/compilación, no una ruta multiview funcional en
juego. Quedan los pipelines con `viewMask`, objetivos de dos capas, constantes por ojo, postproceso y presentación.
La estimación de ~145 pares/s es teórica y debe tratarse como objetivo de investigación, no como resultado garantizado.

### Reporte comunitario para reproducir

En el comentario del 2026-11-25, [amzukk1 en r/PCVR](https://www.reddit.com/r/PCVR/comments/1y1iyqy/comment/19t68hb27qhmr/)
reportó sobre el build «25, 1»: sombras y separación de ojos corregidas; destellos del sol todavía visibles pese a
desactivarlos y aparentemente planos; escala de manos correcta en reposo, pero el render de las manos se desincroniza
de la vista principal al moverlas. Está asentado como reporte externo pendiente de reproducir en
[DEVLOG.es.md](DEVLOG.es.md), no como validación general del build.

## Modos que se ofrecerán

La interfaz final tendrá nombres y descripciones explícitos. La implementación puede usar una variable de entorno
interna durante el desarrollo, pero no exponerá modos incompletos en el menú.

| Opción | Comportamiento | Uso y reglas |
|---|---|---|
| **Automático (recomendado)** | Usa multiview cuando el dispositivo y la ruta estén soportados y validados; si no, usa compatibilidad. | Puede avisar qué ruta eligió y permitir cambiarla. Nunca elige Mono por cuenta propia. La detección de soporte no debe presentarse como prueba de que un driver rinde mejor. |
| **Compatibilidad** | Conserva el render estéreo actual, con una imagen distinta por ojo. | Fallback para hardware/driver con problemas de multiview. Debe seguir funcionando y servir para A/B. |
| **Multiview** | Una actualización del juego por par y dibujo de los dos ojos en las capas correspondientes. | Ruta estéreo de rendimiento. Requiere corrección visual completa antes de publicarse. |
| **Mono (misma imagen en cada ojo)** | Renderiza una vista centrada y comparte la misma imagen entre los ojos. | No hay disparidad binocular ni sensación de profundidad estereoscópica. Puede reducir el trabajo y sirve como opción de accesibilidad para personas con visión monocular, además de ser una alternativa de rendimiento. Siempre se elige explícitamente. |

Un cambio de modo podrá requerir reiniciar VR o reconstruir los pipelines; indicar ese requisito en la UI si no se puede
cambiar sin reiniciar. El modo Mono debe preservar el seguimiento 6DOF y la estabilidad de la imagen. La cámara debe
usar el punto medio entre ojos para evitar una vista desplazada hacia un lado. La imagen de escena y la UI deben salir
iguales en las dos capas antes de la distorsión/composición del runtime.

## Secuencia de trabajo

### 0. Preparar la base y preservar el trabajo existente

1. Leer `AGENTS.md`, `CONTRIBUTING.md`, este plan y la documentación de rendimiento de la rama `win-perf-bench`.
2. Revisar las ramas y worktrees antes de editar. Al escribir este plan, `vr` estaba en `abfa7e1` y
   `win-perf-bench` en `c37abcc`. El worktree `win-perf-bench` tenía cambios sin commit en
   `runtime/nvn/vulkan/device.c`, `exec.c`, `textures.c`, `vk.h` y `runtime/vr/vr_sync.c`: inspeccionarlos y
   preservarlos; no resetear, sobrescribir ni incluirlos por accidente.
3. Elegir una rama de trabajo derivada de la línea VR vigente e integrar los benchmarks y cambios multiview de forma
   revisable. No asumir que `vr` ya contiene los commits de `win-perf-bench`.
   Al escribir este plan, `tools/vr/bench/` y `stereo_depth.py` están en esa rama de rendimiento; confirmar su ubicación
   al integrarla antes de ejecutar las instrucciones de abajo.
4. No agregar archivos del juego, contenido extraído/generado ni partidas guardadas. Mantener capturas y resultados
   personales fuera del repositorio salvo que sean datos sintéticos permitidos.

### 1. Establecer una línea base por hardware

1. Ejecutar `tools/vr/bench/bench.py` en fakeXR a 500 Hz, misma partida de scratch, ruta, resolución por ojo y ajustes.
   Hacer 3–5 rondas A/B intercaladas y comparar medianas; una corrida aislada puede variar alrededor del 5%.
2. Comparar desarrollo con desarrollo y PGO con PGO. Guardar FPS del visor y del juego, p95, uso de GPU, tiempos de
   cuadro y bloqueos de más de 100 ms.
3. Perfilar `nvn-queue` con `tools/vr/bench/profile.py`; separar tiempo de traducción CPU de tiempo GPU.
4. Registrar CPU/modelo, frecuencia efectiva, GPU, driver, resolución, runtime, build, ruta y ajustes. Repetir en el
   Ryzen 9 9950X3D y en una CPU más lenta que represente el mínimo que el proyecto quiera soportar. Definir ese mínimo
   antes de declarar éxito; si no hay acceso a esa máquina, dejar explícita la limitación.
5. Usar varias zonas representativas, no sólo la Meseta. Las capturas visuales deben hacerse fuera de las corridas
   cronometradas porque frenan el juego durante segundos.

### 2. Completar multiview con fallback

1. Crear pipelines Vulkan compatibles con `viewMask = 0b11`, y objetivos/vistas de dos capas para pasadas que dependan
   del ojo. Incluir la máscara y formatos adecuados en las claves de pipeline.
2. Enlazar matrices y datos por ojo: cbuf 3, cámara anterior, bloque env de cbuf 4/5 y posición del ojo donde
   corresponda. Revisar culling con el campo combinado de ambos ojos.
3. Propagar correctamente las capas al muestrear, borrar, copiar, resolver y leer de vuelta texturas. Mantener
   monocapas y una sola ejecución para sombras/cubemaps/compute que realmente no dependen del ojo.
4. Hacer que TAA, HUD, FSR/u otro postproceso y presentación recorran correctamente cada capa sin compartir historial
   temporal entre ojos.
5. Mantener Compatibilidad como fallback cuando falte la feature Vulkan o el usuario seleccione esa opción. El fallo
   de creación de pipeline debe producir un log claro y fallback controlado, no pantalla negra.

### 3. Implementar el modo Mono

1. Renderizar desde una cámara centrada, actualizar el juego una vez por cuadro y duplicar la misma imagen de escena a
   ambas capas de salida. Evitar dibujar una vez por ojo si una misma capa se puede compartir sin copiar trabajo.
2. Revisar HUD, menús, TAA, postproceso, distorsión y escalado. Ningún elemento debe aparecer doble o desplazado entre
   ojos. Conservar seguimiento de cabeza y controles.
3. Añadir una opción claramente etiquetada, por ejemplo **Mono — misma imagen en cada ojo; sin profundidad
   estereoscópica**. Describir su propósito de accesibilidad y su compromiso visual. No activarla automáticamente por
   detección de CPU ni por falta de rendimiento.
4. Traducir los textos de UI en todas las tablas del proyecto y ejecutar el chequeo de internacionalización.

### 4. Verificar corrección antes de comparar velocidad

- **Shaders/pipelines:** ampliar `SAVAGEWIND_VK_MV_TEST=1` más allá de los shaders observados en la Meseta; cubrir
  variantes y escenas relevantes. Probar también un dispositivo/driver sin multiview y el fallback.
- **Estéreo Compatibilidad y Multiview:** usar `tools/vr/stereo_depth.py` con yaw de 37°, giro y caminata; comprobar
  ambos ojos, manos con disparidad/profundidad correcta, fondo distante, movimiento, árboles, sombras/cascadas, HUD y
  escenas con cambios de exposición. No aceptar árboles negros, ojos oscuros, parpadeos ni diferencias de TAA.
- **Mono:** confirmar igualdad de las dos imágenes de escena antes de la composición del runtime, disparidad binocular
  cero, cámara centrada, HUD/menús legibles y ausencia de duplicados. Verificar manualmente en visor comodidad y
  legibilidad, incluyendo la opción de accesibilidad; no inferir comodidad de fakeXR.
- **Reporte del build «25, 1»:** volver a comprobar sombras y separación de ojos; desactivar los destellos del sol y
  confirmar que desaparezcan; revisar si tienen profundidad por ojo cuando están activos. Para las manos, comparar
  quieto y en movimiento, registrar la pose de control y la vista principal, y localizar el primer cuadro de
  desincronización. Reproducir en visor real antes de marcarlo resuelto.
- **Regresión de juego:** comprobar que Compatibilidad conserva su conducta, Multiview no avanza la simulación dos
  veces por par, y Mono sigue permitiendo jugar y usar menús/controles.
- Reutilizar las pruebas VR existentes (`test_vr_game.py`, `test_vr_taa.py`, `test_vr_shadows.py`) cuando apliquen.
  Añadir aserciones automáticas para fallos visuales y estado de modo; los contadores de FPS por sí solos no validan
  corrección.

### 5. Medir y optimizar cada ruta

1. Repetir el A/B de la fase 1 para Compatibilidad, Multiview y Mono, por separado en cada clase de CPU y GPU. Publicar
   medianas y dispersión, no el mejor resultado individual.
2. En el equipo de referencia de gama alta, usar como primer objetivo una mejora de al menos 1,25× respecto de la
   línea base comparable (aprox. 128 FPS si la base de desarrollo es 102); 1,4× (~143–145 FPS) es aspiracional y
   depende del costo GPU real. No comparar build de desarrollo con PGO.
3. En la CPU mínima acordada, priorizar que los tiempos del par cumplan el refresco objetivo: 11,1 ms a 90 Hz,
   12,5 ms a 80 Hz o 13,9 ms a 72 Hz. Reportar p95/p99 y porcentaje de cuadros perdidos/reproyectados en visor real.
4. No aceptar regresiones mayores que el ruido de medición (cerca del 5% en las corridas descritas) ni nuevos bloqueos
   >100 ms. Si el cuello pasa a GPU, evaluar resolución dinámica, GSR/upscaler y foveación por separado, midiendo
   calidad y rendimiento. No atribuir mejoras a una opción no medida.

### 6. Selector, configuración y validación en visor

1. Exponer **Automático**, **Compatibilidad**, **Multiview** y **Mono** sólo cuando cada ruta habilitada haya pasado
   las pruebas. Auto selecciona una ruta estéreo soportada y validada; nunca Mono.
2. Mantener modo seleccionado por el usuario entre reinicios y explicar si se necesita reiniciar VR para aplicar el
   cambio. Permitir forzar Compatibilidad para resolver regresiones de driver.
3. Validar Multiview y Mono en un visor real (Quest 3/Virtual Desktop y otros dispositivos disponibles), midiendo
   frames perdidos/reproyectados y revisando la imagen con la persona usuaria. FakeXR es una herramienta determinista,
   no sustituye esta validación.
4. Actualizar documentación y tabla de features: indicar hardware, driver, runtime, resolución y ajustes; distinguir
   medido, probado automáticamente y validado por una persona.

## Criterios de finalización

- Las cuatro opciones entregan el comportamiento descrito; Mono tiene profundidad estereoscópica cero y se
  activa sólo por elección explícita.
- Multiview ofrece la mejora de CPU esperada y no muestra errores entre ojos; Compatibilidad sigue siendo un fallback
  estable y verificable.
- Los benchmarks documentan CPU (incluido 9950X3D), GPU/driver, build, resolución, runtime, FPS y frame times; hay una
  prueba en hardware más lento o queda declarada la limitación.
- La ruta recomendada cumple el presupuesto del refresco objetivo en el hardware mínimo acordado, o se documenta con
  precisión a qué refresco/hardware sí llega.
- La interfaz y los documentos explican claramente que Mono sacrifica profundidad estereoscópica y es una opción de
  accesibilidad/rendimiento, no el modo automático.

## Instrucción de traspaso a otra IA

Lee `AGENTS.md`, `CONTRIBUTING.md` y este documento. Antes de editar, inspecciona las ramas/worktrees actuales y
preserva cualquier cambio sin commit, en especial el trabajo multiview. Confirma qué partes de `win-perf-bench` ya se
integraron a la rama VR activa. Sigue las fases en orden: línea base, corrección multiview, modo Mono, pruebas,
benchmarks y finalmente selector de usuario. No expongas modos incompletos ni afirmes mejoras sin mediciones
comparables. Para cualquier cambio de rendimiento, registra FPS y frame times antes/después, CPU, GPU, driver,
resolución y ajustes.
