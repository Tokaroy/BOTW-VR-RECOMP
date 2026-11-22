# PC Maker

El PC Maker prepara una carpeta local que podés copiar al dispositivo y abrir sin compilar ahí el código del juego.
Descarga una rama, tag o commit de GitHub, copia los archivos de juego que selecciones a un clon temporal, genera y
compila la biblioteca correspondiente y prepara el runtime con esos archivos en una carpeta nueva.

Los archivos del juego y la biblioteca generada permanecen en la PC. El Maker nunca los sube. La carpeta de salida
contiene archivos personales del juego: no la subas, no la incluyas en un commit ni la compartas.

## Iniciarlo

En Windows, hacé doble clic en `BOTW VR PC Maker.bat`. En Linux, ejecutá `tools/vr/maker.sh` desde un checkout.
También podés abrir la ventana con `python tools/vr/maker.py` o usar la terminal:

```sh
python3 tools/vr/maker.py --target linux \
    --game-files /ruta/a/extracted \
    --output /ruta/a/paquete-nuevo \
    --ref main
```

La carpeta elegida debe contener `exefs/` y `romfs/`. El Maker comprueba los archivos de ExeFS, la firma `NSO0` y
que `romfs/System/Version.txt` indique 1.9.0 y contrasta el build ID de ExeFS con la tabla de versiones compatibles
antes de compilar. También copia las carpetas opcionales `aoc1/` a `aoc8/`. No copia partidas, ajustes, keys ni
archivos ajenos. La ruta de salida no debe existir. Dejá al menos 35 GB libres.

La URL fuente predeterminada es `https://github.com/guideahon/BOTW-VR-RECOMP.git`; elegí el ref en la ventana o pasá
`--source` y `--ref`. El Maker usa un clon temporal y no cambia el checkout desde el que lo iniciaste. Si falla,
borra ese trabajo temporal; `--keep-work` lo conserva para depurar. Cada ejecución crea un log detallado en
`~/Savage Wind VR Maker Logs/`, incluso si falla la validación antes de compilar. Adjuntalo al informar errores del
Maker.

## Destinos

- **Windows x64**: compilá desde Windows con MSYS2 UCRT64 configurado por `tools/setup_windows.ps1`. Abrí
  `Savage Wind VR.exe`; la carpeta incluye un runtime con nombre VR, la biblioteca del juego y los archivos elegidos.
- **Linux x86_64**: compilá desde Linux x86_64. El Maker compila SDL3, FFmpeg y shaderc desde las fuentes fijadas
  por el proyecto, sin contenedores. El AppImage y su carpeta hermana `data/` forman un paquete transferible. Abrí
  el AppImage o `Run Savage Wind VR.sh`.
- **Steam Frame ARM64**: compilá desde Linux x86_64 con `--target steamframe --sysroot <ruta>`. El sysroot debe ser
  una raíz de desarrollo Debian Linux AArch64 (`usr/lib/aarch64-linux-gnu`), con headers y bibliotecas de glibc y
  `libopenxr_loader.so`. El cruce usa ese
  sysroot y compila SDL3, FFmpeg, headers de Vulkan y shaderc desde las fuentes fijadas; no usa Docker ni Podman.
  Transferí la carpeta completa y abrí su AppImage. El rendimiento y el inicio dentro del visor todavía necesitan
  pruebas en el Steam Frame.

Para x86_64, `--cpu auto` usa el perfil de la CPU de la PC compiladora. Usá `--cpu v2` (SSE4.2) o `--cpu v3`
(AVX2/FMA/BMI2) si el dispositivo de destino es distinto. Elegí un perfil que soporte esa CPU.

El Maker compila para el sistema operativo anfitrión: Windows se compila en Windows; Linux PC y Steam Frame, en
Linux. Así usa las herramientas nativas del sistema sin depender de emulación o contenedores.

Cada paquete incluye `BUILD-INFO.txt` con el commit y el destino. En Windows las partidas y los ajustes quedan junto
al launcher VR. En Linux quedan en `data/`, junto al AppImage; al mover la carpeta, el AppImage detecta esos datos.
Si el AppImage Linux no abre, `data/savagewind-launcher.log` registra el fallo de inicio. Si el runtime arranca,
`data/savagewind.log` contiene el diagnóstico; el informe de problemas incluye ambos logs y sus versiones anteriores.
