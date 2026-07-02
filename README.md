# Dragon MediaPlayer

Reproductor multimedia de escritorio hecho en Python con Tkinter y VLC. Reproduce archivos de audio y video locales, y también enlaces directos o de YouTube.

## Características

- Reproduce video y audio local desde una carpeta que tú eliges.
- Reproduce URLs directas y links de YouTube (usando yt-dlp para resolverlos).
- Controles básicos: play/pausa, detener, anterior/siguiente dentro de la carpeta cargada.
- Barra de progreso y control de volumen.
- Pantalla completa con doble clic sobre el video, y `Esc` para salir.
- Sin dependencias de imágenes externas: la interfaz usa solo símbolos de texto, así que el proyecto se puede copiar y correr en cualquier equipo sin preparar carpetas extra.

## Requisitos

- Python 3.10 o superior.
- [VLC media player](https://www.videolan.org/vlc/) instalado en el sistema (no basta con la librería de Python, se necesita el programa).

**Importante:** la arquitectura de VLC debe coincidir con la de tu Python. Si tu Python es de 64 bits, instala la versión de VLC de 64 bits. Mezclarlas es la causa más común de errores al importar la librería `vlc`.

## Instalación

Clona el repositorio e instala las dependencias:

```bash
git clone https://github.com/tu-usuario/dragon-mediaplayer.git
cd dragon-mediaplayer
pip install -r requirements.txt
```

Después instala VLC desde la página oficial si todavía no lo tienes.

## Uso

```bash
python Media_player.py
```

Desde la interfaz puedes:

- Pegar una URL (incluyendo links de YouTube) y darle a **REPRODUCIR**.
- Usar los botones **📁 Música** o **📁 Video** para elegir una carpeta y cargar los archivos que tenga adentro.
- Seleccionar cualquier archivo del menú desplegable para reproducirlo.
- Usar los botones de control o la barra espaciadora para pausar/reanudar.

## Estructura del proyecto

```
dragon-mediaplayer/
├── Media_player.py     # Aplicación principal
├── requirements.txt    # Dependencias de Python
├── README.md
└── .gitignore
```

## Problemas conocidos

- Al reproducir ciertos videos (sobre todo streams resueltos de YouTube), pueden aparecer mensajes en consola como `get_buffer() failed` o `decode_slice_header error`. Son avisos internos del decodificador H.264 de VLC y en la mayoría de los casos no afectan la reproducción; solo hay que revisarlos si el video se traba o se desincroniza de verdad.
- La app usa `winfo_id()` para enlazar la salida de video, lo cual funciona en Windows, Linux y macOS, pero no se ha probado a fondo fuera de Windows.

## Licencia

Este proyecto está bajo la licencia MIT. Revisa el archivo `LICENSE` para más detalles.
