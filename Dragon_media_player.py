import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yt_dlp
import os
import sys
import threading
from pathlib import Path

# Esto tiene que ir antes de "import vlc": el propio módulo vlc.py busca
# libvlc.dll apenas se importa, así que si VLC no está en el PATH hay que
# indicarle a Windows dónde buscar antes de que eso pase.
if sys.platform.startswith("win"):
    rutas_vlc_posibles = [
        Path(r"C:\Program Files\VideoLAN\VLC"),
        Path(r"C:\Program Files (x86)\VideoLAN\VLC"),
    ]
    for ruta in rutas_vlc_posibles:
        if ruta.exists():
            try:
                os.add_dll_directory(str(ruta))
            except Exception:
                pass
            break

import vlc

BASE_DIR = Path(__file__).resolve().parent

COLOR_FONDO = "#181818"
COLOR_CONTROLES = "#202020"
COLOR_TEXTO = "#FFFFFF"

# Símbolos de texto para los botones: nada de imágenes externas, así el
# proyecto se copia y corre tal cual en cualquier equipo.
SIMBOLOS = {
    "anterior": "⏮",
    "reproducir": "▶",
    "pausar": "⏸",
    "detener": "⏹",
    "siguiente": "⏭",
}

EXTENSIONES_AUDIO = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".wma"}
EXTENSIONES_VIDEO = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv"}


class ReproductorMultimedia:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Dragon Media Player")
        self.root.geometry("950x650")
        self.root.configure(bg="#000000")

        self.estilar_componentes()
        self.iniciar_vlc()

        self.reproduciendo = False
        self.pantalla_completa = False
        self.arrastrando_barra = False  # evita que la barra de progreso pelee con el usuario al moverla

        # Listas reales de archivos, vacías hasta que el usuario elija una carpeta
        self.playlist_audio: list[Path] = []
        self.playlist_video: list[Path] = []
        self.playlist_actual: list[Path] = []
        self.indice_actual: int = -1

        self.construir_interfaz()
        self.configurar_eventos()
        self.actualizar_progreso()

    def estilar_componentes(self):
        """Colores oscuros para los widgets ttk"""
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background=COLOR_FONDO)
        style.configure("TLabel", background=COLOR_FONDO, foreground=COLOR_TEXTO)
        style.configure("TButton", background="#333", foreground="white")
        style.configure("Horizontal.TScale", background=COLOR_CONTROLES)

    def iniciar_vlc(self):
        try:
            self.instance = vlc.Instance('--no-video-title-show')
            self.player = self.instance.media_player_new()
        except Exception as e:
            messagebox.showerror(
                "VLC no encontrado",
                "No se pudo inicializar VLC.\n\n"
                "Instala VLC (https://www.videolan.org/) y asegúrate de que "
                "coincida en arquitectura (32/64 bits) con tu Python.\n\n"
                f"Detalle: {e}"
            )
            raise

    def construir_interfaz(self):
        # Encabezado: URL y listas
        header_frame = tk.Frame(self.root, bg=COLOR_CONTROLES, pady=10, padx=10)
        header_frame.pack(fill=tk.X)

        url_container = tk.Frame(header_frame, bg=COLOR_CONTROLES)
        url_container.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(url_container, text="URL / Link:", bg=COLOR_CONTROLES, fg="#AAA").pack(anchor="w")
        self.url_entry = tk.Entry(url_container, bg="#333", fg="white", insertbackground="white", font=("Arial", 10))
        self.url_entry.pack(fill=tk.X, pady=2, ipady=3)

        self.btn_cargar = tk.Button(header_frame, text="REPRODUCIR", bg="#cc0000", fg="white",
                                     font=("Arial", 9, "bold"), borderwidth=0, command=self.reproducir_url)
        self.btn_cargar.pack(side=tk.LEFT, padx=10, fill=tk.Y)

        opts_frame = tk.Frame(header_frame, bg=COLOR_CONTROLES)
        opts_frame.pack(side=tk.RIGHT)

        tk.Button(opts_frame, text="📁 Música", bg="#333", fg="white", bd=0,
                  command=self.elegir_carpeta_audio).pack(side=tk.LEFT, padx=3)
        tk.Button(opts_frame, text="📁 Video", bg="#333", fg="white", bd=0,
                  command=self.elegir_carpeta_video).pack(side=tk.LEFT, padx=3)

        self.var_audio = tk.StringVar(value="Sin música cargada")
        self.om_audio = ttk.OptionMenu(opts_frame, self.var_audio, "Sin música cargada")
        self.om_audio.pack(side=tk.LEFT, padx=5)

        self.var_video = tk.StringVar(value="Sin videos cargados")
        self.om_video = ttk.OptionMenu(opts_frame, self.var_video, "Sin videos cargados")
        self.om_video.pack(side=tk.LEFT, padx=5)

        # Área de video
        self.video_container = tk.Frame(self.root, bg="black")
        self.video_container.pack(fill=tk.BOTH, expand=True)

        self.video_canvas = tk.Canvas(self.video_container, bg="black", highlightthickness=0)
        self.video_canvas.pack(fill=tk.BOTH, expand=True)

        self.root.update_idletasks()
        self._asignar_salida_video()

        # Barra de controles inferior
        controls_frame = tk.Frame(self.root, bg=COLOR_CONTROLES, height=80)
        controls_frame.pack(fill=tk.X, side=tk.BOTTOM)

        progress_container = tk.Frame(controls_frame, bg=COLOR_CONTROLES)
        progress_container.pack(fill=tk.X, padx=10, pady=5)

        self.lbl_tiempo_actual = tk.Label(progress_container, text="00:00", bg=COLOR_CONTROLES, fg="#AAA", font=("Arial", 8))
        self.lbl_tiempo_actual.pack(side=tk.LEFT)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Scale(progress_container, from_=0, to=100, variable=self.progress_var, command=self.set_posicion)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.progress_bar.bind("<ButtonPress-1>", lambda e: setattr(self, "arrastrando_barra", True))
        self.progress_bar.bind("<ButtonRelease-1>", self._soltar_progreso)

        self.lbl_tiempo_total = tk.Label(progress_container, text="00:00", bg=COLOR_CONTROLES, fg="#AAA", font=("Arial", 8))
        self.lbl_tiempo_total.pack(side=tk.RIGHT)

        buttons_container = tk.Frame(controls_frame, bg=COLOR_CONTROLES)
        buttons_container.pack(pady=10)

        def crear_btn(simbolo_key, cmd):
            btn = tk.Button(buttons_container, text=SIMBOLOS[simbolo_key], command=cmd,
                             bg=COLOR_CONTROLES, fg="white", activebackground="#333",
                             activeforeground="white", bd=0, cursor="hand2",
                             font=("Arial", 16), width=3)
            btn.pack(side=tk.LEFT, padx=10)
            return btn

        self.btn_anterior = crear_btn("anterior", self.anterior)
        self.btn_play = crear_btn("reproducir", self.alternar_reproduccion)
        self.btn_detener = crear_btn("detener", self.detener)
        self.btn_siguiente = crear_btn("siguiente", self.siguiente)

        vol_frame = tk.Frame(controls_frame, bg=COLOR_CONTROLES)
        vol_frame.place(relx=1.0, rely=0.6, anchor="e", x=-20)

        tk.Label(vol_frame, text="Vol", bg=COLOR_CONTROLES, fg="#AAA", font=("Arial", 8)).pack(side=tk.LEFT)
        self.vol_scale = ttk.Scale(vol_frame, from_=0, to=100, orient=tk.HORIZONTAL, command=self.set_volumen)
        self.vol_scale.set(50)
        self.vol_scale.pack(side=tk.LEFT, padx=5, ipadx=20)

    def _asignar_salida_video(self):
        """Enlaza el canvas de tkinter como salida de video de VLC según el sistema operativo"""
        handle = self.video_canvas.winfo_id()
        if sys.platform.startswith("win"):
            self.player.set_hwnd(handle)
        elif sys.platform.startswith("linux"):
            self.player.set_xwindow(handle)
        elif sys.platform == "darwin":
            self.player.set_nsobject(handle)

    def configurar_eventos(self):
        self.video_canvas.bind('<Double-Button-1>', self.alternar_pantalla_completa)
        self.root.bind('<Escape>', self.salir_pantalla_completa)
        self.root.bind('<space>', lambda e: self.alternar_reproduccion())

    def _soltar_progreso(self, event=None):
        self.arrastrando_barra = False

    def reproducir_url(self):
        url = self.url_entry.get().strip()
        if not url:
            return

        self.btn_cargar.config(state="disabled", text="Cargando...")
        hilo = threading.Thread(target=self._resolver_url, args=(url,), daemon=True)
        hilo.start()

    def _resolver_url(self, url: str):
        """Corre en un hilo aparte para no congelar la interfaz mientras yt-dlp resuelve el link"""
        try:
            if "youtube.com" in url or "youtu.be" in url:
                ydl_opts = {
                    'format': 'best[ext=mp4]/best',
                    'quiet': True,
                    'no_warnings': True,
                    'extractor_args': {'youtube': {'player_client': ['android', 'ios']}}
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    url = info.get('url', url)
        except Exception as e:
            self.root.after(0, lambda: self._error_carga(str(e)))
            return

        self.root.after(0, lambda: self._reproducir_resuelto(url))

    def _reproducir_resuelto(self, url: str):
        self.btn_cargar.config(state="normal", text="REPRODUCIR")
        self.playlist_actual = []
        self.indice_actual = -1
        self._cargar_media(url)

    def _error_carga(self, mensaje: str):
        self.btn_cargar.config(state="normal", text="REPRODUCIR")
        messagebox.showerror("Error al cargar", f"No se pudo reproducir la URL:\n{mensaje}")

    def _cargar_media(self, ruta_o_url: str):
        try:
            media = self.instance.media_new(ruta_o_url)
            self.player.set_media(media)
            self.player.play()
            self.reproduciendo = True
            self.actualizar_icono_play()
        except Exception as e:
            messagebox.showerror("Error de reproducción", str(e))

    def elegir_carpeta_audio(self):
        carpeta = filedialog.askdirectory(title="Selecciona carpeta de música")
        if not carpeta:
            return
        archivos = self._escanear_carpeta(Path(carpeta), EXTENSIONES_AUDIO)
        if not archivos:
            messagebox.showinfo("Sin resultados", "No se encontraron archivos de audio en esa carpeta.")
            return
        self.playlist_audio = archivos
        self._actualizar_menu(self.om_audio, self.var_audio, archivos, self._reproducir_de_audio)

    def elegir_carpeta_video(self):
        carpeta = filedialog.askdirectory(title="Selecciona carpeta de video")
        if not carpeta:
            return
        archivos = self._escanear_carpeta(Path(carpeta), EXTENSIONES_VIDEO)
        if not archivos:
            messagebox.showinfo("Sin resultados", "No se encontraron archivos de video en esa carpeta.")
            return
        self.playlist_video = archivos
        self._actualizar_menu(self.om_video, self.var_video, archivos, self._reproducir_de_video)

    @staticmethod
    def _escanear_carpeta(carpeta: Path, extensiones: set) -> list:
        try:
            return sorted(
                [p for p in carpeta.iterdir() if p.is_file() and p.suffix.lower() in extensiones],
                key=lambda p: p.name.lower()
            )
        except Exception as e:
            print(f"Error escaneando carpeta: {e}")
            return []

    def _actualizar_menu(self, option_menu: ttk.OptionMenu, var: tk.StringVar, archivos: list, callback):
        menu = option_menu["menu"]
        menu.delete(0, "end")
        for archivo in archivos:
            menu.add_command(label=archivo.name, command=lambda a=archivo: callback(a))
        var.set(f"{len(archivos)} archivo(s) — elige uno")

    def _reproducir_de_audio(self, archivo: Path):
        self.var_audio.set(archivo.name)
        self.playlist_actual = self.playlist_audio
        self.indice_actual = self.playlist_audio.index(archivo)
        self._cargar_media(str(archivo))

    def _reproducir_de_video(self, archivo: Path):
        self.var_video.set(archivo.name)
        self.playlist_actual = self.playlist_video
        self.indice_actual = self.playlist_video.index(archivo)
        self._cargar_media(str(archivo))

    def alternar_reproduccion(self):
        if self.reproduciendo:
            self.player.pause()
            self.reproduciendo = False
        else:
            self.player.play()
            self.reproduciendo = True
        self.actualizar_icono_play()

    def actualizar_icono_play(self):
        simbolo = SIMBOLOS["pausar"] if self.reproduciendo else SIMBOLOS["reproducir"]
        self.btn_play.config(text=simbolo)

    def detener(self):
        self.player.stop()
        self.reproduciendo = False
        self.progress_var.set(0)
        self.lbl_tiempo_actual.config(text="00:00")
        self.actualizar_icono_play()

    def anterior(self):
        if not self.playlist_actual or self.indice_actual <= 0:
            return
        self.indice_actual -= 1
        archivo = self.playlist_actual[self.indice_actual]
        self._reproducir_indice_actual(archivo)

    def siguiente(self):
        if not self.playlist_actual or self.indice_actual >= len(self.playlist_actual) - 1:
            return
        self.indice_actual += 1
        archivo = self.playlist_actual[self.indice_actual]
        self._reproducir_indice_actual(archivo)

    def _reproducir_indice_actual(self, archivo: Path):
        if archivo in self.playlist_audio:
            self.var_audio.set(archivo.name)
        elif archivo in self.playlist_video:
            self.var_video.set(archivo.name)
        self._cargar_media(str(archivo))

    def set_volumen(self, val):
        self.player.audio_set_volume(int(float(val)))

    def set_posicion(self, val):
        if self.player.get_length() > 0:
            self.player.set_position(float(val) / 100)

    def actualizar_progreso(self):
        if self.reproduciendo and not self.arrastrando_barra:
            duracion = self.player.get_length()
            actual = self.player.get_time()

            if duracion > 0:
                self.progress_var.set((actual / duracion) * 100)

                mins, secs = divmod(actual // 1000, 60)
                tmins, tsecs = divmod(duracion // 1000, 60)

                self.lbl_tiempo_actual.config(text=f"{mins:02d}:{secs:02d}")
                self.lbl_tiempo_total.config(text=f"{tmins:02d}:{tsecs:02d}")

        self.root.after(1000, self.actualizar_progreso)

    def alternar_pantalla_completa(self, event=None):
        self.pantalla_completa = not self.pantalla_completa
        self.root.attributes("-fullscreen", self.pantalla_completa)
        if not self.pantalla_completa:
            self.root.geometry("1024x768")

    def salir_pantalla_completa(self, event=None):
        self.pantalla_completa = False
        self.root.attributes("-fullscreen", False)


if __name__ == "__main__":
    root = tk.Tk()
    try:
        app = ReproductorMultimedia(root)
    except Exception as e:
        print(f"No se pudo iniciar la aplicación: {e}")
        sys.exit(1)
    root.mainloop()
