#!/usr/bin/env python3
"""The VR feature table: the one place each feature's state is kept. Run it to write docs/vr/FEATURES.md (English)
and docs/vr/FEATURES.es.md (Spanish) from ROWS below:

    python3 docs/vr/features.py

Each row: (id, origin, implemented, AI validated, human validated, English name, English how to test,
Spanish name, Spanish how to test).
  origin       BVR (from BetterVR), Mod (this mod's own), SW (Savage Wind, the PC recomp), or a mix
  implemented  Y done, P partly, N not yet, - not needed / not applicable
  AI validated Y checked by an automated test (fake_xr, the hand simulator, a unit test, a profile), P partly,
               N not checked yet, - not applicable. Never a headset.
  human        '' not tested yet, 'ok', 'fail: <what>' or 'partial: <what>' as the player reported it in a headset,
               '-' not applicable
Human results come only from the player (they test in the headset and report by ID); the AI never fills that column.
"""
import os

ROWS = [
    # ---- V. Headset and picture
    ('V01', 'BVR', 'Y', 'Y', 'ok', 'OpenXR session: the game starts in the headset (Virtual Desktop / SteamVR / Link)', 'Start the VR shortcut: the game shows in the headset',
     'Sesión OpenXR: arranca en el visor (Virtual Desktop / SteamVR / Link)', 'Abrir con el acceso de VR: el juego aparece en el visor'),
    ('V02', 'Mod', 'Y', 'Y', '', 'No headset or runtime: it goes on flat and says why', 'Start with Virtual Desktop not connected: it plays on the monitor and the log says why',
     'Sin visor o sin runtime sigue en plano y lo dice', 'Abrir sin Virtual Desktop conectado: juega en el monitor, el log dice por qué'),
    ('V03', 'BVR', 'Y', 'Y', '', 'Virtual screen for menus, loading and the title', 'Title screen: a floating screen ahead',
     'Pantalla virtual para menús, carga y título', 'Pantalla de título: una pantalla flotante adelante'),
    ('V04', 'BVR', 'Y', 'Y', '', 'Real stereo (a picture per eye, no alternating)', 'In play, close one eye then the other: right depth, eyes not swapped',
     'Estéreo real (una imagen por ojo, sin alternar)', 'En juego, cerrar un ojo y otro: profundidad correcta, ojos no invertidos'),
    ('V05', 'BVR', 'Y', 'Y', '', '6DOF: turning, tilting, moving the head', 'Look around, crouch, lean: the view follows with no lag',
     '6DOF: girar, inclinar, moverse con la cabeza', 'Mirar alrededor, agacharse, asomarse: la vista acompaña sin retraso'),
    ('V06', 'Mod', 'Y', 'Y', '', "Each eye's own field of view (asymmetric)", 'The picture sharp to its edges, not stretched looking sideways',
     'Campo visual propio de cada ojo (asimétrico)', 'Bordes de la imagen nítidos, sin estirarse al mirar de reojo'),
    ('V07', 'Mod', 'Y', 'Y', '', 'The world at normal speed in stereo', 'Grass, water and people move at normal speed',
     'El mundo a velocidad normal en estéreo', 'Pasto, agua y gente a velocidad normal (ni lenta ni rápida)'),
    ('V08', 'Mod', 'Y', 'Y', '', 'Eye resolution (1080 to 2160; 1440 by default), applied live', 'Options > VR > Eye resolution in play: sharper or faster at once, no restart',
     'Resolución de los ojos (1080 a 2160; 1440 por defecto), en vivo', 'Opciones > VR > Resolución de los ojos jugando: más nítido o más rápido al instante, sin reiniciar'),
    ('V09', 'SW', 'Y', 'N', '', 'Render scale (Video > Advanced) sharpens the picture', 'Set it to 150%: sharper, fewer fps',
     'Escala de render (Video avanzado) afina la imagen', 'Subirla a 150%: más nítido, menos fps'),
    ('V10', 'Mod', 'Y', 'Y', '', 'TAA in stereo (a history per eye)', 'Anti-aliasing TAA: no ghost of one eye in the other, smooth edges',
     'TAA en estéreo (historia por ojo)', 'Anti-aliasing TAA: sin fantasmas de un ojo en el otro, bordes suaves'),
    ('V11', 'BVR', 'Y', 'Y', '', 'No depth of field or lens flare in VR', 'Look at the sun and far away: no flares, no blur',
     'Sin profundidad de campo ni lens flare en VR', 'Mirar al sol y lejos: sin destellos ni desenfoque'),
    ('V12', 'Mod', 'Y', 'Y', '', 'The monitor window shows the left eye only', 'Look at the monitor: it does not flicker between eyes',
     'La ventana del monitor muestra solo el ojo izquierdo', 'Mirar el monitor: no parpadea entre ojos'),
    ('V13', 'Mod', 'Y', 'Y', '', "The sun's shadows steady in both eyes", 'Tree shadows do not flicker',
     'Sombras del sol estables en los dos ojos', 'Las sombras de los árboles no parpadean'),
    ('V14', 'Mod', 'Y', 'Y', '', 'Video rows that do nothing in VR hidden', 'Options > Video: no fullscreen, monitor, field of view, frame rate, VSync',
     'Filas de Video que no hacen nada en VR, ocultas', 'Opciones > Video: no están pantalla completa, monitor, campo visual, fps, VSync'),
    ('V15', 'BVR', 'P', 'Y', '', 'Depth for reprojection (SAVAGEWIND_VR_DEPTH=1)', 'Off by default: with Virtual Desktop the GPU device was lost',
     'Profundidad para reproyección (SAVAGEWIND_VR_DEPTH=1)', 'Apagada: con Virtual Desktop se perdía el dispositivo'),
    ('V16', 'Mod', 'Y', 'Y', '', 'The session lost (headset off, Virtual Desktop closed): goes on flat', 'Close Virtual Desktop while playing: the game goes on on the monitor',
     'Si se pierde la sesión sigue en plano', 'Cerrar Virtual Desktop jugando: el juego sigue en el monitor'),
    ('V17', 'Mod', 'Y', 'N', '', 'Snapdragon GSR upscaler (single pass, no history)', 'Video > Advanced > Upscaler: Snapdragon GSR, a smaller Render scale: sharp edges, no ghosting',
     'Upscaler Snapdragon GSR (una pasada, sin historia)', 'Video avanzado > Upscaler: Snapdragon GSR y una escala de render menor: bordes nítidos, sin fantasmas'),
    ('V18', 'Mod', 'Y', 'P', '', 'Performance rows on the VR page (FPS overlay, render scale, upscaler, its mode or Dynamic, anti-aliasing)', 'Options > VR: change them in play with the FPS overlay on and watch the frame rate move',
     'Filas de rendimiento en la página VR (overlay de FPS, escala de render, upscaler, su modo o Dinámico, anti-aliasing)', 'Opciones > VR: cambiarlas jugando con el overlay de FPS y ver cómo se mueven los fps'),
    # ---- P. View and camera
    ('P01', 'BVR', 'Y', 'Y', '', "First person: the eye in Link's head", 'Options > VR > View: First person',
     'Primera persona: el ojo en la cabeza de Link', 'Opciones > VR > Vista: Primera persona'),
    ('P02', 'BVR', 'Y', 'Y', '', "Link's head hidden (face, hair, hat)", 'Look down and around: no inside of his head',
     'Cabeza de Link oculta (cara, pelo, gorro)', 'Mirar abajo y alrededor: no se ve el interior de la cabeza'),
    ('P03', 'BVR', 'Y', 'Y', '', "Third person (the game's camera)", 'View: Third person; the head moves the look',
     'Tercera persona (la cámara del juego)', 'Vista: Tercera persona; la cabeza mueve la mirada'),
    ('P04', 'BVR', 'Y', 'Y', '', "Third-person camera distance", 'Options > VR > Third-person distance',
     'Distancia de la cámara en tercera persona', 'Opciones > VR > Distancia en tercera persona'),
    ('P05', 'BVR', 'Y', 'Y', '', 'Recentring the view', 'Command vr recenter, or back from a menu: the view faces Link\'s way',
     'Recentrar la vista', 'Comando vr recenter o volver de un menú: la vista mira hacia donde mira Link'),
    ('P06', 'Mod', 'Y', 'Y', '', 'Crouched, swimming or riding, the eye goes down with his head', 'Crouch (L3): the view goes down; swim; ride',
     'Agachado, nadando o a caballo el ojo baja con la cabeza', 'Agacharse (L3): la vista baja; nadar; montar'),
    ('P07', 'BVR', 'Y', 'Y', '', "Link's body turns to where you look", 'Look to a side standing: the body follows, the arms still reach your hands',
     'El cuerpo de Link gira hacia donde mirás', 'Mirar a un costado parado: el cuerpo acompaña, los brazos llegan a las manos'),
    ('P08', 'Mod', 'Y', 'Y', '', "The game camera's fast turns do not turn the view (lock on)", 'Lock on with the left trigger: the view does not jerk',
     'Las vueltas rápidas de la cámara del juego no giran la vista (fijar)', 'Fijar con el gatillo izquierdo: la vista no pega un tirón'),
    ('P09', 'BVR', '-', '-', '', 'No tumbling view on strong hits (BetterVR: prevent ragdoll)', 'A strong hit: the view moves but never tumbles (here the eye is always upright)',
     'Sin volteretas de la vista con golpes fuertes', 'Un golpe fuerte: la vista se mueve pero no da vueltas (acá el ojo siempre está derecho)'),
    ('P10', 'BVR', 'Y', 'Y', '', 'Climbing: the eye off the wall', 'Climb a wall: you never see inside the rock',
     'Escalando: el ojo afuera de la pared', 'Escalar una pared: nunca se ve el interior de la roca'),
    ('P11', 'BVR', 'Y', 'Y', '', 'Swimming: the eye above the water', "Swim: the eye just above the surface, following Link's head",
     'Nadando: el ojo arriba del agua', 'Nadar: el ojo justo sobre la superficie, siguiendo la cabeza de Link'),
    ('P12', 'BVR', 'Y', 'Y', '', 'The scope (Sheikah Slate) on the virtual screen, with its zoom', 'Right stick click held: the scope on the flat screen; let go: the world',
     'La mira (tableta sheikah) en la pantalla virtual, con zoom', 'Clic del stick derecho mantenido: la mira en la pantalla plana; soltar: el mundo'),
    ('P13', 'BVR', 'Y', 'Y', '', 'Shrine doors and LinkTag actors in stereo', 'Enter a shrine: the door opens normally',
     'Puertas de santuario y actores LinkTag en estéreo', 'Entrar a un santuario: la puerta se abre normal'),
    ('P14', 'BVR', 'P', 'N', '', 'Third-person camera without collision where it gets in the way', 'Only the distance is done; walls still push the camera',
     'Cámara en tercera persona sin colisión donde molesta', 'Solo la distancia; las paredes todavía empujan la cámara'),
    ('P15', 'BVR', 'N', 'N', '', 'The camera riding a sand seal', 'Not done',
     'La cámara montando una foca de arena', 'No hecho'),
    # ---- B. Body and hands
    ('B01', 'BVR', 'Y', 'Y', '', "Link's arms follow the controllers (two-bone IK)", "Move your hands: Link's are where yours are (the arm poses: B10)",
     'Los brazos de Link siguen los controles (IK de dos huesos)', 'Mover las manos: las de Link están donde las tuyas (las poses de los brazos: B10)'),
    ('B02', 'BVR', 'Y', 'Y', '', 'Clothes and armor follow the arms', 'Wear other armor: sleeves and gloves follow',
     'La ropa y la armadura siguen los brazos', 'Ponerse otra armadura: mangas y guantes acompañan'),
    ('B03', 'Mod', 'Y', 'Y', '', 'Natural wrist and forearm turn', 'Palm up and down: the forearm turns, the wrist does not fold',
     'Giro natural de muñeca y antebrazo', 'Palma arriba y abajo: el antebrazo gira, la muñeca no se dobla rara'),
    ('B04', 'Mod', 'Y', 'Y', '', 'Elbows down, no "chicken wings"', 'Hands ahead at chest height: elbows down',
     'Codos abajo, sin "alas de pollo"', 'Manos adelante a la altura del pecho: codos hacia abajo'),
    ('B05', 'Mod', 'Y', 'Y', '', 'Controller markers in menus and third person', 'In a menu: a pale blue disc at each hand. Options > VR > Show the controllers',
     'Marcadores de los controles en menús y tercera persona', 'En un menú: un disco celeste en cada mano. Opciones > VR > Mostrar los controles'),
    ('B06', 'Mod', 'Y', 'Y', '', 'What Link holds is read from the game', 'Equip a sword, bow, shield: the gestures know what you hold',
     'Lo que Link tiene en la mano se lee del juego', 'Equipar espada, arco, escudo: los gestos saben qué tenés'),
    ('B07', 'BVR', 'Y', 'N', '', 'Torches, Bokoblin arms and branches as weapons', 'Pick up a torch or a Bokoblin arm: it is used as a sword',
     'Antorchas, brazos de bokoblin y ramas como armas', 'Agarrar una antorcha o un brazo de bokoblin: se usa como espada'),
    ('B08', 'BVR', 'N', 'N', '', "Link's head keeps its shadow in first person", 'Not done: the hidden head has no shadow',
     'La cabeza de Link conserva su sombra en primera persona', 'No hecho: la cabeza oculta no tiene sombra'),
    ('B09', 'BVR', '-', 'Y', '', "Link and his weapon do not fade with the camera near", 'Not needed: in first-person captures the hands and weapons are solid',
     'Link y su arma no se vuelven transparentes con la cámara cerca', 'No hace falta: en las capturas de primera persona manos y armas se ven sólidas'),
    ('B10', 'Mod', 'Y', 'Y', '', 'Natural arm poses while moving and turning the hands (elbow, shoulder, forearm roll)', 'Move the hands around, raise them overhead, turn the palms up and down: the elbows and shoulders look natural, nothing snaps (SAVAGEWIND_VR_ARM_RIG=0: the first rig, to compare)',
     'Poses naturales de los brazos al mover y girar las manos (codo, hombro, giro del antebrazo)', 'Mover las manos, subirlas sobre la cabeza, girar las palmas arriba y abajo: codos y hombros naturales, nada salta (SAVAGEWIND_VR_ARM_RIG=0: el rig anterior, para comparar)'),
    ('B11', 'Mod', 'Y', 'Y', '', "Link's hands and arms at the right depth in both eyes while turning (the right frame's skeleton placed with the pair's anchor)", 'Hold the hands ahead and turn with the stick: the hands stay single, not crossed or doubled',
     'Las manos y brazos de Link a la profundidad correcta en los dos ojos al girar (el esqueleto del cuadro derecho con el ancla del par)', 'Con las manos adelante, girar con el stick: las manos se ven de a una, ni cruzadas ni dobles'),
    # ---- C. Controls (Quest layout)
    ('C01', 'BVR', 'Y', 'Y', '', 'Left stick: walk where you look', 'Walk looking to a side: he goes where you look',
     'Stick izquierdo: caminar hacia donde mirás', 'Caminar mirando a un lado: va hacia donde mirás'),
    ('C02', 'BVR', 'Y', 'Y', '', 'Walk where the left controller points', 'Options > VR > Walking direction: the left hand',
     'Caminar hacia donde apunta el control izquierdo', 'Opciones > VR > Dirección al caminar: la mano izquierda'),
    ('C03', 'Mod', 'Y', 'Y', '', 'Left stick click: crouch; held: run', 'Hold the click while walking: he runs',
     'Clic del stick izquierdo: agacharse; mantenido: correr', 'Mantener el clic caminando: corre'),
    ('C04', 'BVR', 'Y', 'Y', '', 'Right stick: turn (smooth, snap or head only)', 'Options > VR > Turning; try the three',
     'Stick derecho: girar (suave, por pasos o solo cabeza)', 'Opciones > VR > Giro; probar los tres'),
    ('C05', 'Mod', 'Y', 'Y', '', 'Right stick up: jump', 'Push the right stick up: he jumps (not during Magnesis)',
     'Stick derecho arriba: saltar', 'Empujar el stick derecho arriba: salta (no durante Magnesis)'),
    ('C06', 'Mod', 'Y', 'Y', '', 'A: accept, interact', 'Talk, open a chest with A',
     'A: aceptar, interactuar', 'Hablar, abrir un cofre con A'),
    ('C07', 'Mod', 'Y', 'Y', '', 'B: cancel, put away (a tap; held does not run)', 'Hold B: he does not run',
     'B: cancelar, guardar (un toque; mantenido no corre)', 'Mantener B: no corre'),
    ('C08', 'Mod', 'Y', 'Y', '', 'Right trigger: attack with the right hand', 'Sword out: the right trigger attacks',
     'Gatillo derecho: atacar con la mano derecha', 'Espada afuera: el gatillo derecho ataca'),
    ('C09', 'Mod', 'Y', 'Y', '', "Right trigger held: a charged attack (the weapons' menu: the right shoulder's grip; SAVAGEWIND_VR_TRIGGER_MENUS=1: also the trigger held, hand empty)", 'Sword out, hold the trigger: Link charges, let go: the spin',
     'Gatillo derecho mantenido: ataque cargado (menú de armas: el grip en el hombro derecho; SAVAGEWIND_VR_TRIGGER_MENUS=1: también el gatillo mantenido con la mano vacía)', 'Espada en mano, mantener el gatillo: Link carga, al soltar: el giro'),
    ('C10', 'Mod', 'Y', 'Y', '', 'Left trigger: guard, lock on, and a parry at the press', 'Shield: press just before a hit: parry',
     'Gatillo izquierdo: cubrirse, fijar y parry al apretar', 'Escudo: apretar justo antes del golpe: parry'),
    ('C11', 'Mod', 'Y', 'Y', '', "Left trigger held: the guard as long as held (the shields' menu: the left shoulder's grip)", 'Shield out, hold the trigger: he keeps guarding, no menu',
     'Gatillo izquierdo mantenido: la guardia mientras se mantenga (menú de escudos: el grip en el hombro izquierdo)', 'Escudo en mano, mantener el gatillo: sigue cubriéndose, sin menú'),
    ('C12', 'Mod', 'Y', 'Y', '', 'A while guarding does not parry', 'Guarding, press A: nothing',
     'A cubriéndote no hace parry', 'Cubierto, apretar A: no hace nada'),
    ('C13', 'Mod', 'Y', 'Y', '', 'Right grip: the bow out or away', 'Right grip away from the body: bow out; again: away',
     'Grip derecho: sacar o guardar el arco', 'Grip derecho lejos del cuerpo: arco afuera; otra vez: lo guarda'),
    ('C14', 'Mod', 'Y', 'Y', '', "Right grip held: the bows' menu", 'Hold it: the bows menu; no arrow on letting go',
     'Grip derecho mantenido: menú de arcos', 'Mantener: el menú de arcos; al soltar no sale flecha'),
    ('C15', 'Mod', 'Y', 'Y', '', "Left grip held with the bow out: the arrows' menu", 'Bow out, hold the left grip: the arrows menu',
     'Grip izquierdo mantenido con el arco afuera: menú de flechas', 'Arco afuera, mantener el grip izquierdo: el menú de flechas'),
    ('C16', 'BVR', 'Y', 'Y', '', 'Left grip: grab, interact', 'Left grip at an object: he picks it up',
     'Grip izquierdo: agarrar, interactuar', 'Grip izquierdo frente a un objeto: lo levanta'),
    ('C17', 'Mod', 'Y', 'Y', '', "Y: the rune; held: the runes' menu", 'Y: the rune out; hold: the menu',
     'Y: la runa; mantenido: menú de runas', 'Y: saca la runa; mantener: el menú'),
    ('C18', 'Mod', 'Y', 'Y', '', 'X: the map', 'X: the map opens',
     'X: el mapa', 'X: abre el mapa'),
    ('C19', 'Mod', 'Y', 'Y', '', 'Menu button: pause', 'Left menu button: the pause menu',
     'Botón menú: pausa', 'Botón menú izquierdo: el menú de pausa'),
    ('C20', 'BVR', 'Y', 'Y', '', 'Right stick click: inventory; held: the scope', 'Click: the inventory',
     'Clic del stick derecho: inventario; mantenido: la mira', 'Clic: el inventario'),
    ('C21', 'BVR', 'Y', 'Y', '', "In menus the buttons are the game's letters (triggers L / R)", 'Inventory: the triggers turn the pages',
     'En menús los botones son las letras del juego (gatillos L / R)', 'Inventario: los gatillos cambian de página'),
    ('C22', 'Mod', 'Y', 'Y', '', 'A button held when a menu opens or closes is not repeated', 'Open the map with X held: it does not close by itself',
     'Un botón mantenido al abrir o cerrar un menú no se repite', 'Abrir el mapa con X mantenido: no se cierra solo'),
    ('C23', 'Mod', 'Y', 'Y', '', 'Quest button icons instead of Switch ones', 'Video > Button icons: Automatic; prompts show A, B, the triggers',
     'Íconos de botones del Quest en vez de los de Switch', 'Video > Íconos de botones: Automático; los carteles muestran A, B, gatillos'),
    ('C24', 'BVR', 'Y', 'Y', '', "The game's rumble on the controllers", 'Hit or get hit: it vibrates',
     'La vibración del juego en los controles', 'Golpear o recibir un golpe: vibra'),
    ('C25', 'BVR', 'Y', 'Y', '', 'Vibration strength', 'Options > VR > Vibration and Vibration strength',
     'Fuerza de la vibración', 'Opciones > VR > Vibración y Fuerza de la vibración'),
    ('C26', 'BVR', 'Y', 'Y', '', 'Left-handed mode (hands swapped)', 'Options > VR > Left-handed: everything to the other hand',
     'Modo zurdo (manos intercambiadas)', 'Opciones > VR > Zurdo: todo pasa a la otra mano'),
    ('C27', 'BVR', 'Y', 'Y', '', "BetterVR's buttons (SAVAGEWIND_VR_CONTROLS=bettervr)", 'B jumps, A held runs',
     'Botones de BetterVR (SAVAGEWIND_VR_CONTROLS=bettervr)', 'B salta, A mantenido corre'),
    ('C28', 'Mod', 'Y', 'Y', '', 'Classic layout (SAVAGEWIND_VR_CONTROLS=classic)', 'Buttons as a gamepad, no gestures',
     'Esquema clásico (SAVAGEWIND_VR_CONTROLS=classic)', 'Botones como un joystick, sin gestos'),
    ('C29', 'BVR', 'Y', 'N', '', 'Index, WMR, Vive, Pico, Vive Cosmos and Steam Frame controllers', 'Only with those controllers',
     'Controles Index, WMR, Vive, Pico, Vive Cosmos y Steam Frame', 'Solo si tenés esos controles'),
    ('C30', 'Mod', 'Y', 'Y', '', 'A gamepad still works next to the VR controllers', 'Connect an Xbox controller: it plays too',
     'Un joystick común sigue funcionando junto a los de VR', 'Conectar un control Xbox: también juega'),
    ('C31', 'BVR', 'Y', 'Y', '', 'Stick dead zone', 'Options > VR > Stick dead zone: raise it if Link walks on his own',
     'Zona muerta de los sticks', 'Opciones > VR > Zona muerta de los sticks: subila si Link camina solo'),
    ('C32', 'BVR', 'Y', 'P', '', "Fix controller rotation (Meta's Oculus runtime)", 'Options > VR > Fix controller rotation: Automatic turns it on with the Oculus runtime',
     'Corregir la rotación de los controles (runtime Oculus de Meta)', 'Opciones > VR > Corregir la rotación de los controles: Automático la activa con el runtime Oculus'),
    ('C33', 'BVR', 'Y', 'Y', '', 'No "nothing to draw" head shake', 'Without a bow, the right grip or trigger does not make Link shake his head',
     'Sin sacudida de cabeza cuando no hay nada para sacar', 'Sin arco, el grip derecho o el gatillo no hacen que Link sacuda la cabeza'),
    ('C34', 'BVR', 'Y', 'P', '', 'Ladders handled specially (up and down whatever the view)', 'On a ladder, look to a side and push forward: Link climbs (the turn checked on flat ground, not yet on a ladder)',
     'Escaleras con manejo especial (subir y bajar mire donde mire)', 'En una escalera, mirar a un costado y empujar adelante: Link sube (el giro probado en llano, todavía no en una escalera)'),
    ('C35', 'Mod', 'Y', 'P', 'ok', 'A quick menu does not turn the view (the right stick picks in it)', 'Hold the runes or weapons menu, push the right stick to the sides, let go: the view looks where it did',
     'Un menú rápido no gira la vista (el stick derecho elige en él)', 'Mantener el menú de runas o armas, mover el stick derecho a los costados, soltar: la vista mira adonde miraba'),
    # ---- G. Gestures and body slots
    ('G01', 'BVR', 'Y', 'Y', '', 'Right shoulder + grip: the weapon out or away', 'Right hand at the shoulder, grip: sword out; again: away',
     'Hombro derecho + grip: sacar o guardar el arma', 'Mano derecha al hombro, grip: espada afuera; otra vez: la guarda'),
    ('G02', 'BVR', 'Y', 'Y', '', "Right shoulder grip held: the weapons' menu", 'Hold 0.5 s: the menu',
     'Hombro derecho, grip mantenido: menú de armas', 'Mantener 0,5 s: el menú'),
    ('G03', 'BVR', 'Y', 'Y', '', 'Left shoulder + grip: the bow', 'Hand at the left shoulder, grip: the bow',
     'Hombro izquierdo + grip: el arco', 'Mano al hombro izquierdo, grip: el arco'),
    ('G04', 'BVR', 'Y', 'Y', '', 'Left shoulder held: shields (with a weapon out) or bows', 'Hold 0.5 s: the menu',
     'Hombro izquierdo mantenido: escudos (con arma) o arcos', 'Mantener 0,5 s: el menú'),
    ('G05', 'BVR', 'Y', 'Y', '', 'Left hip + grip: the rune; held: the runes', 'Hand at the left hip',
     'Cadera izquierda + grip: la runa; mantenido: las runas', 'Mano a la cadera izquierda'),
    ('G06', 'BVR', 'Y', 'Y', '', 'Right hip grip held: drop what that hand holds', 'Options > VR > Drop gesture; hold 0.5 s: the weapon falls (never the Slate)',
     'Cadera derecha, grip mantenido: soltar lo de esa mano', 'Opciones > VR > Gesto de soltar; mantener 0,5 s: el arma cae (la tableta nunca)'),
    ('G07', 'BVR', 'Y', 'Y', '', 'Throw the weapon: trigger held at the shoulder, let go', 'Weapon out, trigger at the right shoulder, let go: thrown',
     'Lanzar el arma: gatillo mantenido en el hombro, soltar', 'Arma afuera, gatillo en el hombro derecho, soltar: la tira'),
    ('G08', 'Mod', 'Y', 'Y', '', 'Whistle: both hands at the mouth + both triggers', 'The horse comes; at the mouth the triggers do not guard or attack',
     'Silbido: las dos manos en la boca + los dos gatillos', 'Viene el caballo; en la boca los gatillos no cubren ni atacan'),
    ('G09', 'BVR', 'Y', 'Y', '', "BetterVR's whistle: both grips at the mouth", 'bettervr layout: grips at the mouth',
     'Silbido de BetterVR: los dos grips en la boca', 'Esquema bettervr: grips en la boca'),
    ('G10', 'BVR', 'Y', 'Y', '', "Physical parry: a quick push of the left hand while guarding", 'Shield up, push the left hand ahead: parry',
     'Parry físico: un empuje rápido de la mano izquierda cubriéndote', 'Escudo arriba, empujar la mano izquierda adelante: parry'),
    ('G11', 'BVR', 'Y', 'Y', '', 'Guard by raising the shield hand', 'Options > VR > Raise the left hand to guard; hand in front of the chest: guards',
     'Cubrirse levantando la mano del escudo', 'Opciones > VR > Levantar la mano izquierda para cubrirse; mano frente al pecho: se cubre'),
    ('G12', 'BVR', 'Y', 'Y', '', 'A vibration at each body slot', 'Pass the hand over the shoulder: it vibrates',
     'Vibración al tocar cada lugar del cuerpo', 'Pasar la mano por el hombro: vibra'),
    ('G13', 'BVR', 'Y', 'Y', '', "The body slots' guide", 'Options > VR > Body slot guide: pale discs at the shoulders, hips and mouth when a hand is near',
     'Guía de los lugares del cuerpo', 'Opciones > VR > Guía de los lugares del cuerpo: discos celestes en hombros, caderas y boca al acercar la mano'),
    ('G14', 'BVR', '-', 'N', '', 'The shield aimed by the hand (the guard faces the view)', 'Not needed if the guard follows the view (BetterVR sets it from Link\'s facing; here Link turns to the view to guard): guarding, does it block hits from the side you look at?',
     'El escudo apuntado con la mano (la guardia mira hacia la vista)', 'No haría falta si la guardia sigue la vista (BetterVR la toma de hacia dónde mira Link; acá Link gira a la vista al cubrirse): cubierto, ¿bloquea golpes del lado al que mirás?'),
    # ---- A. Combat
    ('A01', 'BVR', 'Y', 'Y', '', "Slashes and stabs by motion (Acudofy's analysis)", 'Options > VR > Motion combat; slash the air: Link attacks; thrust: a stab',
     'Cortes y estocadas con movimiento (análisis de Acudofy)', 'Opciones > VR > Combate con movimiento; cortar en el aire: Link ataca; estocada: estocada'),
    ('A02', 'BVR', 'Y', 'Y', '', 'Slow moves and wrist flicks do not count', 'Move the hand slowly: no attack',
     'Movimientos lentos o de muñeca no cuentan', 'Mover la mano despacio: no ataca'),
    ('A03', 'BVR', 'Y', 'Y', '', "The weapon hits where it is (its hitbox follows the hand)", 'Hit an enemy at your side: it is hit where the hand is',
     'Pega donde está el arma (su hitbox sigue la mano)', 'Pegarle a un enemigo al costado: le pega donde está la mano'),
    ('A04', 'BVR', 'Y', 'Y', '', 'It hits when swung, harder the faster', 'A soft swing and a hard one: different damage',
     'Pega cuando la movés, más fuerte cuanto más rápido', 'Golpe suave y golpe fuerte: distinto daño'),
    ('A05', 'BVR', 'Y', 'Y', '', 'One hit per swing', 'Options > VR > One hit per swing: the same enemy is not hit twice',
     'Un golpe por tajo', 'Opciones > VR > Un golpe por tajo: no le pega dos veces al mismo'),
    ('A06', 'BVR', 'Y', 'Y', '', 'Cutting trees', 'A chop at a tree: it falls',
     'Cortar árboles', 'Hachazo a un árbol: cae'),
    ('A07', 'Mod', 'Y', 'Y', '', "A swing also plays Link's attack", "Options > VR > Swings play Link's attack: off, it hits without the animation",
     'El tajo también hace el ataque de Link', 'Opciones > VR > Los tajos hacen el ataque de Link: apagado, pega sin la animación'),
    ('A08', 'BVR', 'Y', 'Y', '', 'Easy swings profile', 'Options > VR > Easy swings',
     'Perfil de tajos fáciles', 'Opciones > VR > Tajos fáciles'),
    ('A09', 'BVR', 'Y', 'Y', '', 'Two-handed weapons held with both hands', 'Options > VR > Two-handed grip; a claymore out, left grip on the hilt: the blade points at the other hand',
     'Armas a dos manos con las dos manos', 'Opciones > VR > Agarre a dos manos; mandoble afuera, grip izquierdo en el mango: la hoja apunta a la otra mano'),
    ('A10', 'BVR', 'Y', 'N', '', 'Lighting fires, cutting ropes by motion', 'A torch to the grass; cut a rope',
     'Prender fuego, cortar cuerdas con movimiento', 'Antorcha al pasto; cortar una cuerda'),
    # ---- R. Bow
    ('R01', 'BVR', 'Y', 'Y', 'ok', 'Aiming with the hands (string hand to bow hand)', 'The arrow flies along the hands\' line, not where you look',
     'Apuntar con las manos (de la cuerda al arco)', 'La flecha sale por la línea de las manos, no hacia donde mirás'),
    ('R02', 'BVR', 'Y', 'Y', '', 'Trajectory arc (yellow dots) and its modes', 'Draw: the dots show; Options > VR > Bow trajectory: Full, Faint, Aiming dot only, Off',
     'Arco de trayectoria (puntos amarillos) y sus modos', 'Tensar: se ven los puntos; Opciones > VR > Trayectoria del arco: Completa, Tenue, Solo el punto de mira, Desactivada'),
    ('R03', 'Mod', 'Y', 'Y', '', 'The arrow stays on the bow while drawing', 'Draw: the arrow points at the bow, not anywhere',
     'La flecha queda sobre el arco al tensar', 'Tensar: la flecha apunta al arco, no a cualquier lado'),
    ('R04', 'Mod', 'Y', 'Y', '', 'No arrow when letting go of a bow menu', 'Bows menu, let go: no shot',
     'Al soltar un menú de arco no sale flecha', 'Menú de arcos y soltar: no dispara'),
    ('R05', 'SW', 'Y', 'N', '', 'Slow motion jumping with the bow', 'Jump from high and draw: slow motion',
     'Cámara lenta saltando con el arco', 'Saltar desde alto y tensar: cámara lenta'),
    ('R06', 'Mod', 'Y', 'Y', '', 'Aiming with the head', 'Options > VR > Aim the bow with your hands: off, arrows fly where you look',
     'Apuntar con la cabeza', 'Opciones > VR > Apuntar el arco con las manos: apagado, sale hacia donde mirás'),
    ('R07', 'BVR', 'Y', 'Y', '', 'The string follows the drawing hand', 'Draw: the string goes to your hand',
     'La cuerda sigue a la mano que tensa', 'Tensar: la cuerda va a tu mano'),
    # ---- U. Runes
    ('U01', 'BVR', 'Y', 'Y', '', 'Runes aimed with the head (the reticle)', 'Bombs, Stasis, Cryonis aim at the view\'s centre',
     'Runas apuntadas con la cabeza (retícula)', 'Bomba, Stasis, Cryonis apuntan al centro de la vista'),
    ('U02', 'Mod', 'Y', 'Y', '', 'The right trigger uses the rune', 'Rune out, right trigger: it is used',
     'El gatillo derecho usa la runa', 'Runa afuera, gatillo derecho: la usa'),
    ('U03', 'BVR+Mod', 'Y', 'Y', '', 'Magnesis by hand: left and right', 'Grab something with Magnesis, move the hand sideways',
     'Magnesis con la mano: izquierda y derecha', 'Agarrar algo con Magnesis, mover la mano al costado'),
    ('U04', 'Mod', 'Y', 'Y', '', 'Magnesis: up and down by hand', 'Raise and lower the hand: the object follows',
     'Magnesis: subir y bajar con la mano', 'Subir y bajar la mano: el objeto acompaña'),
    ('U05', 'Mod', 'Y', 'Y', '', 'Magnesis: the stick brings it near or far', 'Right stick up and down',
     'Magnesis: el stick acerca o aleja', 'Stick derecho arriba y abajo'),
    ('U06', 'Mod', 'Y', 'Y', '', 'Magnesis: the view does not turn by itself', 'Move the object: the view stays',
     'Magnesis: la vista no gira sola', 'Mover el objeto: la vista queda quieta'),
    ('U07', 'SW', 'Y', 'P', '', 'Stasis, Cryonis, bombs', 'Use them as usual',
     'Stasis, Cryonis, bombas', 'Usarlas normal'),
    ('U08', 'BVR', 'N', 'N', '', 'Magnesis: twist the wrist to spin the object', 'Not done',
     'Magnesis: girar el objeto con la muñeca', 'No hecho'),
    # ---- I. Objects
    ('I01', 'SW', 'Y', 'N', '', 'Lifting objects', 'A at a pot or a small rock: he lifts it',
     'Levantar objetos', 'A frente a una maceta o roca chica: la levanta'),
    ('I02', 'BVR', 'Y', 'N', '', "Throwing with the hand's velocity", 'Carrying it: right trigger pressed, swing the hand and let go: it flies where you threw',
     'Tirar con la velocidad de la mano', 'Cargándola: gatillo derecho apretado, tirar la mano y soltar: sale hacia donde tiraste'),
    ('I03', 'BVR', 'Y', 'N', '', 'What you carry drawn in your hand(s)', 'Carrying: small things in the right hand, big ones between the hands, scaled down',
     'Lo que cargás se ve en la mano', 'Cargando: lo chico en la mano derecha, lo grande entre las dos manos, achicado'),
    ('I04', 'Mod', 'Y', 'Y', 'ok', "The item windows: a chest's item, a new item, the inventory's description", "Open a chest; open the inventory: the boxes at the game's size and place",
     'Las ventanas de objetos: el del cofre, el objeto nuevo, la descripción del inventario', 'Abrir un cofre; abrir el inventario: los cuadros del tamaño y en el lugar del juego'),
    ('I05', 'SW', 'Y', 'N', '', 'Riding a horse', 'Mount and ride: the view follows',
     'Montar a caballo', 'Subir y andar: la vista acompaña'),
    ('I06', 'SW', 'Y', 'P', '', 'Gliding, climbing, swimming', 'Try each',
     'Planear, escalar, nadar', 'Probar cada uno'),
    ('I07', 'SW', 'Y', 'N', '', 'Cooking, talking, shopping', 'Cook at a pot, buy at a shop',
     'Cocinar, hablar, comprar', 'Cocinar en una olla, comprar en una tienda'),
    ('I08', 'BVR', 'Y', 'Y', '', 'Soothing the horse: on horseback with nothing in hand, the right trigger (BetterVR 1.0.2)', 'Ride with no weapon out and pull the right trigger: the horse calms down, no weapon is drawn; with a weapon out it attacks',
     'Calmar al caballo: montado y con la mano vacía, el gatillo derecho (BetterVR 1.0.2)', 'Montar sin arma afuera y apretar el gatillo derecho: el caballo se calma, no saca el arma; con un arma afuera ataca'),
    ('I09', 'Mod', 'Y', 'Y', '', "Petting the horse: an empty hand patting low ahead (its neck)", "Riding, pat the air low in front of you: Link pets the horse",
     'Acariciar al caballo: palmear con la mano vacía bajo y adelante (su cuello)', 'Montado, palmear el aire bajo y adelante: Link acaricia al caballo'),
    # ---- K. Comfort
    ('K01', 'BVR', 'Y', 'Y', '', 'Smooth turning and its speed', 'Options > VR > Turning speed',
     'Giro suave y su velocidad', 'Opciones > VR > Velocidad de giro'),
    ('K02', 'BVR', 'Y', 'Y', '', 'Snap turning and its angle', 'Options > VR > Snap angle',
     'Giro por pasos y su ángulo', 'Opciones > VR > Ángulo del paso'),
    ('K03', 'Mod', 'Y', 'Y', '', 'Turning with the head only', 'Turning: Head only; the stick does not turn',
     'Giro solo con la cabeza', 'Giro: Solo cabeza; el stick no gira'),
    ('K04', 'Mod', 'Y', 'Y', '', 'Comfort vignette while moving', 'Options > VR > Comfort vignette: High; walking darkens the edges',
     'Viñeta de confort al moverse', 'Opciones > VR > Viñeta de confort: Alta; caminar oscurece los bordes'),
    ('K05', 'BVR', 'Y', 'Y', '', 'Seated or standing', 'Options > VR > Play position: Standing uses your real height',
     'Sentado o parado', 'Opciones > VR > Posición de juego: Parado usa tu altura real'),
    ('K06', 'BVR', 'Y', 'Y', '', 'Height offset (-30 to +30 cm)', 'Options > VR > Height',
     'Ajuste de altura (-30 a +30 cm)', 'Opciones > VR > Altura'),
    ('K07', 'BVR+Mod', 'P', 'Y', '', 'Roomscale: walking in the room walks Link (the simple way)', 'Options > VR > Roomscale; two steps in the room: Link walks; at a wall the view comes back',
     'Escala de habitación: caminar en la sala camina a Link (la forma simple)', 'Opciones > VR > Escala de habitación; dos pasos en la sala: Link camina; contra una pared la vista vuelve'),
    ('K08', 'BVR', 'Y', 'Y', '', 'Comfort presets (Gentle, Balanced, Immersive)', 'Options > VR > Comfort preset; change a row after it: Custom',
     'Presets de confort (Suave, Equilibrado, Inmersivo)', 'Opciones > VR > Preset de confort; cambiar una fila después: Personalizado'),
    ('K09', 'BVR', 'N', 'N', '', "Full roomscale (Link's body moved with its own world casts)", 'Not done: the simple roomscale above',
     'Escala de habitación completa (el cuerpo de Link movido con sus propios rayos)', 'No hecho: está la versión simple'),
    # ---- H. HUD and menus
    ('H01', 'BVR', 'Y', 'Y', '', 'The HUD apart, floating ahead', 'Hearts and minimap on a panel ahead, not on the eyes',
     'El HUD aparte, flotando adelante', 'Corazones y minimapa en un panel delante, no pegados a los ojos'),
    ('H02', 'BVR', 'Y', 'Y', '', 'The HUD follows the gaze or stays', 'Options > VR > HUD follows your gaze: off, it stays low ahead',
     'El HUD sigue la mirada o queda fijo', 'Opciones > VR > El HUD sigue tu mirada: apagado, queda abajo'),
    ('H03', 'BVR', 'Y', 'Y', '', 'HUD size and distance', 'Options > VR > HUD size / HUD distance',
     'Tamaño y distancia del HUD', 'Opciones > VR > Tamaño / Distancia del HUD'),
    ('H04', 'BVR', 'Y', 'Y', '', 'Pause, map, inventory on the virtual screen', 'Open them: a floating screen',
     'Pausa, mapa, inventario en la pantalla virtual', 'Abrirlos: una pantalla flotante'),
    ('H05', 'Mod', 'Y', 'Y', '', "Savage Wind's overlay menu on the virtual screen", 'Open with F1 or hold the VR menu button for 0.6 s during play',
     'El menú de Savage Wind en la pantalla virtual', 'Abrir con F1 o mantener 0,6 s el botón menú del visor durante el juego'),
    ('H06', 'BVR', 'Y', 'Y', '', 'Performance overlay in the headset', 'Video > Performance overlay: up and to the right',
     'Overlay de rendimiento en el visor', 'Video > Overlay de rendimiento: arriba a la derecha'),
    ('H07', 'BVR', 'Y', 'Y', '', 'VR options in the game', 'Pause > System > Options > VR',
     'Opciones de VR dentro del juego', 'Pausa > Sistema > Opciones > VR'),
    ('H08', 'BVR', 'Y', 'Y', '', 'Controls guide page', 'Options > VR > Controls guide: each button and gesture',
     'Página de guía de controles', 'Opciones > VR > Guía de controles: cada botón y gesto'),
    ('H09', 'SW', 'Y', 'N', '', 'Dialogues and texts readable', 'Talk to someone: it reads well on the screen',
     'Diálogos y textos legibles', 'Hablar con alguien: se lee bien en la pantalla'),
    ('H10', 'BVR', 'Y', 'P', '', 'Screen markers placed on the floating HUD (names, targets)', 'Lock on to an enemy, pin a map marker: the marker sits over the thing, not nearer the centre (HUD following the gaze)',
     'Marcadores de pantalla sobre el HUD flotante (nombres, objetivos)', 'Fijar un enemigo, poner un pin en el mapa: el marcador queda sobre la cosa, no más al centro (HUD que sigue la mirada)'),
    ('H11', 'BVR', 'Y', 'P', '', 'The stamina wheel placed for the floating HUD (first person: under the hearts)', 'Sprint or climb in first person: the wheel under the hearts',
     'La rueda de stamina ubicada para el HUD flotante (primera persona: bajo los corazones)', 'Correr o escalar en primera persona: la rueda bajo los corazones'),
    ('H12', 'BVR', '-', 'Y', '', 'UI blending fixes', 'Not needed here: the HUD is split another way; captures look right',
     'Arreglos de transparencias de la interfaz', 'No hace falta: el HUD se separa de otra forma; las capturas se ven bien'),
    # ---- E. Events and cutscenes
    ('E01', 'BVR', 'Y', 'Y', '', "Automatic cutscene mode (BetterVR's table of 1497 events)", 'Options > VR > Cutscenes: Automatic',
     'Modo de cinemáticas automático (tabla de 1497 eventos de BetterVR)', 'Opciones > VR > Cinemáticas: Automático'),
    ('E02', 'BVR', 'Y', 'Y', '', 'Cutscenes always first person, third person or flat', 'Try each mode with an event (opening a chest)',
     'Cinemáticas siempre en primera, tercera persona o en pantalla', 'Probar cada modo con un evento (abrir un cofre)'),
    ('E03', 'BVR', 'Y', 'Y', '', 'Black bars for cutscenes on the flat screen', 'Options > VR > Cutscene black bars',
     'Barras negras para cinemáticas en la pantalla', 'Opciones > VR > Barras negras en cinemáticas'),
    ('E04', 'Mod', 'Y', 'Y', '', 'Events without the frame rate drop (chests appearing, opening)', 'Clear a camp: the chest appears at a good frame rate',
     'Eventos sin bajada de fps (aparece el cofre, abrirlo)', 'Limpiar un campamento: aparece el cofre a buen fps'),
    ('E05', 'SW+Mod', 'Y', 'N', '', 'Events that must run at 30 fps (Kohga) on the screen', 'Only if you get there',
     'Eventos que deben ir a 30 fps (Kohga) en la pantalla', 'Solo si llegás'),
    # ---- O. Options, install and platform
    ('O01', 'Mod', 'Y', 'Y', '', 'Installer Install BOTW VR.bat', 'Install from scratch',
     'Instalador Install BOTW VR.bat', 'Instalar de cero'),
    ('O02', 'Mod', 'Y', 'Y', '', 'The VR launcher (Savage Wind VR.exe)', 'Start it from Virtual Desktop',
     'El lanzador de VR (Savage Wind VR.exe)', 'Abrirlo desde Virtual Desktop'),
    ('O03', 'Mod', 'Y', 'Y', '', 'The options are kept between runs', 'Change one, restart: it stays',
     'Las opciones se guardan entre sesiones', 'Cambiar algo, reiniciar: sigue'),
    ('O04', 'Mod', 'Y', 'Y', '', 'The VR options in Spanish', 'Language Spanish: all VR texts in Spanish',
     'Las opciones de VR en español', 'Idioma español: todo lo de VR en español'),
    ('O05', 'Mod', 'Y', 'Y', '', 'The vr console command (status)', 'In-game console: vr',
     'El comando vr en la consola (estado)', 'Consola del juego: vr'),
    ('O06', 'Mod', 'Y', 'P', '', 'Linux (AppImage with VR)', 'Only with Linux and SteamVR / Monado / WiVRn',
     'Linux (AppImage con VR)', 'Solo si tenés Linux y SteamVR / Monado / WiVRn'),
    ('O07', 'BVR', 'N', 'N', '', 'Foveated rendering', 'Not done (Virtual Desktop did not offer the extension)',
     'Renderizado foveado', 'No hecho (Virtual Desktop no ofrecía la extensión)'),
    ('O08', 'BVR', 'N', 'N', '', 'Spectator / recording view (wider, no HUD)', 'Not done: the monitor shows the left eye',
     'Vista de espectador / grabación (más ancha, sin HUD)', 'No hecho: el monitor muestra el ojo izquierdo'),
    ('O09', 'BVR', '-', '-', '', 'Boot straight into the game', 'Not needed: the VR launcher starts the game directly',
     'Arrancar directo al juego', 'No hace falta: el lanzador de VR arranca el juego directo'),
    ('O10', 'Mod', 'Y', 'Y', '', "A window the system keeps at another size (Steam Frame standalone, gamescope): the eyes at their own resolution, the eyes fused", 'Steam Frame: Options > VR > Eye resolution changes the sharpness; no eyestrain',
     'Ventana que el sistema deja de otro tamaño (Steam Frame standalone, gamescope): los ojos a su resolución y bien fusionados', 'Steam Frame: Opciones > VR > Resolución de los ojos cambia la nitidez; sin fatiga visual'),
    ('O11', 'Mod', 'Y', 'Y', '', 'No freezes from the monitor window: in play it is not updated (SAVAGEWIND_VR_MIRROR=1: shown)', 'Play with the game window on the monitor, move it: the headset never freezes (before: up to 2 s)',
     'Sin congelamientos por la ventana del monitor: jugando no se actualiza (SAVAGEWIND_VR_MIRROR=1: se muestra)', 'Jugar con la ventana del juego en el monitor, moverla: el visor nunca se congela (antes: hasta 2 s)'),
    ('O12', 'Mod', 'Y', 'Y', '', 'Lighter barriers between render passes in VR (SAVAGEWIND_VK_BARRIER_FRAG=0: as before)', 'Compare the fps with and without; the picture the same (terrain, grass, water, effects)',
     'Barreras más livianas entre pases de render en VR (SAVAGEWIND_VK_BARRIER_FRAG=0: como antes)', 'Comparar los fps con y sin; la imagen igual (terreno, pasto, agua, efectos)'),
    ('O13', 'Mod', 'Y', 'N', '', "The sun's shadows drawn once a stereo pair: off by default, the right eye's shadows came out wrong (SAVAGEWIND_VR_SHADOWS_ONCE=1: on)", 'Stand still near shadows (trees, rocks): the same shadows in both eyes',
     'Las sombras del sol dibujadas una vez por par estéreo: apagado por defecto, las sombras del ojo derecho salían mal (SAVAGEWIND_VR_SHADOWS_ONCE=1: encendido)', 'Quieto cerca de sombras (árboles, rocas): las mismas sombras en los dos ojos'),
    ('O14', 'Mod', 'Y', 'Y', '', 'The HUD layer made once a stereo pair', 'The HUD (hearts, minimap, stamina) shows and updates as before',
     'La capa del HUD hecha una vez por par estéreo', 'El HUD (corazones, minimapa, vigor) se ve y se actualiza como antes'),
    ('O15', 'Mod', 'Y', 'Y', '', 'Linux 6.7+: the game geometry in video memory (SAVAGEWIND_NO_WRITE_WATCH=1: as before; Windows already had it)', 'Linux: the log says "write watch: userfaultfd" and "heap copy in video memory: on"',
     'Linux 6.7+: la geometría del juego en memoria de video (SAVAGEWIND_NO_WRITE_WATCH=1: como antes; Windows ya lo tenía)', 'Linux: el log dice "write watch: userfaultfd" y "heap copy in video memory: on"'),
    ('O16', 'Mod', 'Y', 'Y', '', 'The game\'s HUD drawn only in the right eye\'s frame, which makes the HUD layer (SAVAGEWIND_VR_HUD_ONCE=0: in both)', 'The HUD (hearts, minimap, stamina, prompts) shows and updates as before; compare the fps with and without',
     'El HUD del juego dibujado solo en el cuadro del ojo derecho, que arma la capa del HUD (SAVAGEWIND_VR_HUD_ONCE=0: en los dos)', 'El HUD (corazones, minimapa, vigor, indicaciones) se ve y se actualiza como antes; comparar los fps con y sin'),
    ('O17', 'Mod', 'P', 'N', '', 'Synchronous stereo, in progress (SAVAGEWIND_VR_SYNC=1, off by default): one game frame a pair, its lists translated again for the right eye with its camera - both eyes the same moment, the game simulated once a pair. The geometry and the light are right, eye-independent passes drawn once, the sun shadows right in both eyes; one far tree black and now and then a darker right eye (docs/vr/SYNC_STEREO.md)', 'Not for play yet',
     'Estéreo sincrónico, en desarrollo (SAVAGEWIND_VR_SYNC=1, apagado por defecto): un cuadro del juego por par, sus listas traducidas otra vez para el ojo derecho con su cámara - los dos ojos en el mismo momento, el juego simulado una vez por par. La geometría y la luz están bien, las pasadas que no dependen del ojo se dibujan una vez, las sombras del sol bien en los dos ojos; un árbol lejano negro y a veces el ojo derecho más oscuro (docs/vr/SYNC_STEREO.md)', 'Todavía no es para jugar'),
    ('O18', 'Mod', 'P', 'Y', '', 'Multiview (SAVAGEWIND_VR_SYNC=1 SAVAGEWIND_VR_MV=1, off by default): both eyes drawn in one pass from one game frame, the HUD apart, TAA per eye - 145 headset fps against 100 in normal stereo with TAA (fake_xr, RTX 3090)', 'With the variables set: the hands and the world at the right depth in both eyes, no eye darker or doubled',
     'Multiview (SAVAGEWIND_VR_SYNC=1 SAVAGEWIND_VR_MV=1, apagado por defecto): los dos ojos dibujados en una pasada desde un cuadro del juego, con el HUD aparte y TAA por ojo - 145 fps en el visor contra 100 en estéreo normal con TAA (fake_xr, RTX 3090)', 'Con las variables: las manos y el mundo a la profundidad justa en los dos ojos, ningún ojo más oscuro ni doble'),
    # ---- S. Savage Wind (the recomp) in VR
    ('S01', 'SW', 'Y', 'N', '', 'The whole game and both DLC (1.9.0)', 'Use something of the DLC (Majora\'s Mask, the Trial of the Sword)',
     'Todo el juego y los dos DLC (1.9.0)', 'Usar algo del DLC (Máscara de Majora, la prueba de la espada)'),
    ('S02', 'SW', 'Y', 'N', '', 'Graphics presets (Potato to Savage)', 'Video > Preset: the picture changes in the headset',
     'Presets gráficos (Potato a Savage)', 'Video > Preset: cambia la imagen en el visor'),
    ('S03', 'SW', 'Y', 'Y', '', 'Draw distance, shadows, quality', 'Video > Advanced: it shows in the headset',
     'Distancia de dibujado, sombras, calidad', 'Video avanzado: se nota en el visor'),
    ('S04', 'SW', 'Y', 'N', '', 'DLSS / FSR 3 / FSR 4 / XeSS', 'Video > Upscaler: does it look right in both eyes? (off recommended)',
     'DLSS / FSR 3 / FSR 4 / XeSS', 'Video > Upscaler: ¿se ve bien en los dos ojos? (recomendado apagado)'),
    ('S05', 'SW', 'Y', 'N', '', 'FSR 3 frame generation', 'Probably no use in VR',
     'Generación de frames FSR 3', 'Probablemente no sirve en VR'),
    ('S06', 'SW', '-', '-', '-', 'HDR', 'In VR the window stays SDR',
     'HDR', 'En VR la ventana queda SDR'),
    ('S07', 'SW', 'Y', 'N', '', 'Colour grading, colour vision filters', 'Options > Colour: applied in the headset?',
     'Gradación de color, filtros de daltonismo', 'Opciones > Color: ¿se aplica en el visor?'),
    ('S08', 'SW', '-', '-', '-', 'Keyboard and mouse', 'Not for VR',
     'Teclado y mouse', 'No aplica en VR'),
    ('S09', 'SW', '-', '-', '-', 'Gyro, Steam Input', 'Not for VR',
     'Giroscopio, Steam Input', 'No aplica en VR'),
    ('S10', 'SW', 'Y', 'N', '', 'Save profiles, backups, Wii U / Cemu import', 'Load an imported save',
     'Perfiles de guardado, backups, importar Wii U / Cemu', 'Cargar una partida importada'),
    ('S11', 'SW', 'Y', 'N', '', 'Photo mode', 'Does it work in VR?',
     'Modo foto', '¿Funciona con VR puesto?'),
    ('S12', 'SW', 'Y', 'P', '', 'Cheats, assists and the teleport', 'Teleport: the view arrives right',
     'Trucos, asistencias y teletransporte', 'Teletransportarse: la vista llega bien'),
    ('S13', 'SW', 'Y', 'N', '', 'amiibo', 'Use the amiibo rune',
     'amiibo', 'Usar la runa amiibo'),
    ('S14', 'SW', 'Y', 'Y', '', 'Quick inventory drop and sort', 'The drop gesture uses it',
     'Soltar y ordenar en el inventario rápido', 'El gesto de soltar lo usa'),
    ('S15', 'SW', '-', '-', '-', '30 to 360 fps', 'In VR the headset sets the frame rate (twice its Hz)',
     '30 a 360 fps', 'En VR los fps los marca el visor (el doble de su Hz)'),
    ('S16', 'SW', 'Y', 'N', '', 'Discord Rich Presence', 'Optional',
     'Discord Rich Presence', 'Opcional'),
]

SECTIONS = [  # (id prefix, English title, Spanish title)
    ('V', 'V. Headset and picture', 'V. Visor e imagen'),
    ('P', 'P. View and camera', 'P. Vista y cámara'),
    ('B', 'B. Body and hands', 'B. Cuerpo y manos'),
    ('C', 'C. Controls (Quest layout)', 'C. Controles (esquema Quest)'),
    ('G', 'G. Gestures and body slots', 'G. Gestos y lugares del cuerpo'),
    ('A', 'A. Combat', 'A. Combate'),
    ('R', 'R. Bow', 'R. Arco'),
    ('U', 'U. Runes', 'U. Runas'),
    ('I', 'I. Objects', 'I. Objetos'),
    ('K', 'K. Comfort', 'K. Confort'),
    ('H', 'H. HUD and menus', 'H. HUD y menús'),
    ('E', 'E. Events and cutscenes', 'E. Eventos y cinemáticas'),
    ('O', 'O. Options, install and platform', 'O. Opciones, instalación y plataforma'),
    ('S', 'S. Savage Wind (the PC recomp) in VR', 'S. Savage Wind (el recomp de PC) en VR'),
]

IMPL = {'Y': '✅', 'P': '🟡', 'N': '❌', '-': '➖'}
AI = {'Y': '✅', 'P': '🟡', 'N': '⬜', '-': '➖'}


def human(h, es):
    if h == '': return '⬜'
    if h == '-': return '➖'
    if h == 'ok': return '✅'
    kind, _, what = h.partition(':')
    mark = '❌' if kind == 'fail' else '🟡'
    return mark + (' ' + what.strip() if what else '')


TEXT = {
    'en': dict(
        title='# VR feature table',
        intro="""Every feature of this mod, of BetterVR (the reference, for the Wii U game on Cemu) and of Savage Wind (the PC
recomp it builds on) that matters in VR, with three checks each. This table is the project's control list: it is
generated from [features.py](features.py) (edit the rows there and run `python3 docs/vr/features.py`).
En español: [FEATURES.es.md](FEATURES.es.md).

- **Implemented**: ✅ done, 🟡 partly, ❌ not yet, ➖ not needed here.
- **AI validated**: ✅ checked by an automated test (the fake_xr runtime, the hand simulator, a unit test or a
  profile; never a headset), 🟡 partly, ⬜ not checked yet.
- **Human validated**: what the player saw in the headset. ⬜ not tested yet, ✅ works, ❌ fails, 🟡 partly. Only
  the player fills it: test a row and report it by its ID (for example "C07 fails: B still runs"), with a capture of
  the game window and `savagewind.log` if you can.
- **Origin**: BVR from BetterVR, Mod this mod's own, SW Savage Wind's.""",
        head='| ID | Feature | Origin | Implemented | AI validated | Human validated | How to test |',
        summary='Summary: {n} features; implemented {i}, AI validated {a}, human validated {h}, failing in the headset {f}.',
        beyond="""## Where this mod goes beyond BetterVR

- Native, no emulator: a much higher frame rate (about 110 stereo pairs a second at 1080 lines an eye on an RTX 3090,
  measured against fake_xr).
- Savage Wind's graphics: DLSS, FSR, render scale, draw distance, shadows, TAA per eye.
- The 1.9.0 game with both DLC.
- Its own Quest layout, Magnesis up and down by hand, the arrow on the bow, the Quest's button icons.
- Tests with no headset (fake_xr, the hand simulator)."""),
    'es': dict(
        title='# Tabla de features de VR',
        intro="""Cada feature de este mod, de BetterVR (la referencia, para el juego de Wii U en Cemu) y de Savage Wind (el recomp
de PC en el que se apoya) que importa en VR, con tres controles cada una. Esta tabla es la lista de control del
proyecto: se genera desde [features.py](features.py) (las filas se editan ahí y se corre `python3 docs/vr/features.py`).
In English: [FEATURES.md](FEATURES.md).

- **Implementado**: ✅ hecho, 🟡 en parte, ❌ todavía no, ➖ acá no hace falta.
- **Validado IA**: ✅ comprobado por una prueba automática (el runtime fake_xr, el simulador de manos, un test
  unitario o un perfil; nunca un visor), 🟡 en parte, ⬜ todavía no.
- **Validado humano**: lo que vio el jugador con el visor puesto. ⬜ sin probar, ✅ anda, ❌ falla, 🟡 en parte. Solo
  lo completa el jugador: probá una fila y reportala por su ID (por ejemplo "C07 falla: B todavía corre"), con una
  captura de la ventana del juego y el `savagewind.log` si podés.
- **Origen**: BVR de BetterVR, Mod propio de este mod, SW de Savage Wind.""",
        head='| ID | Feature | Origen | Implementado | Validado IA | Validado humano | Cómo probar |',
        summary='Resumen: {n} features; implementadas {i}, validadas por IA {a}, validadas por humano {h}, fallando en el visor {f}.',
        beyond="""## Donde este mod va más allá de BetterVR

- Nativo, sin emulador: muchos más fps (unos 110 pares estéreo por segundo a 1080 líneas por ojo en una RTX 3090,
  medido con fake_xr).
- Lo gráfico de Savage Wind: DLSS, FSR, escala de render, distancia de dibujado, sombras, TAA por ojo.
- El juego 1.9.0 con los dos DLC.
- Un esquema de controles propio para Quest, Magnesis arriba y abajo con la mano, la flecha sobre el arco, los íconos
  del Quest.
- Pruebas sin visor (fake_xr, el simulador de manos)."""),
}


def write(lang):
    t = TEXT[lang]
    es = lang == 'es'
    n = len(ROWS)
    i = sum(r[2] == 'Y' for r in ROWS)
    a = sum(r[3] == 'Y' for r in ROWS)
    h = sum(r[4] == 'ok' for r in ROWS)
    f = sum(r[4].startswith('fail') for r in ROWS)
    out = [t['title'], '', t['intro'], '', t['summary'].format(n=n, i=i, a=a, h=h, f=f), '']
    for pre, en_t, es_t in SECTIONS:
        out += ['## ' + (es_t if es else en_t), '', t['head'], '|---|---|---|---|---|---|---|']
        for r in ROWS:
            if not r[0].startswith(pre): continue
            name, how = (r[7], r[8]) if es else (r[5], r[6])
            out.append('| %s | %s | %s | %s | %s | %s | %s |' % (r[0], name, r[1], IMPL[r[2]], AI[r[3]], human(r[4], es), how))
        out.append('')
    out.append(t['beyond'])
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'FEATURES.es.md' if es else 'FEATURES.md')
    open(path, 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')


if __name__ == '__main__':
    ids = [r[0] for r in ROWS]
    assert len(ids) == len(set(ids)), 'duplicate ids'
    for r in ROWS:
        assert len(r) == 9 and r[2] in IMPL and r[3] in AI, r[0]
    write('en')
    write('es')
    print('wrote FEATURES.md and FEATURES.es.md (%d rows)' % len(ROWS))
