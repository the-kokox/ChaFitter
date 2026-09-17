"""Pantalla de cámara: captura una foto, le quita el fondo y pide la
categoría antes de agregarla al guardarropa."""

import os
import time

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.camera import Camera
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen

from bg_removal import quitar_fondo
from theme import FONDO_ABAJO, FONDO_ARRIBA, NEON_CIAN, NEON_MAGENTA, TEXTO, BotonNeon, FondoDegradado

CARPETA_CAPTURAS = os.path.join(os.path.expanduser("~"), ".outfit_ai_capturas")
os.makedirs(CARPETA_CAPTURAS, exist_ok=True)


class PantallaCamara(Screen):
    """Pantalla con vista previa de cámara y botón de captura.

    En Android usa la cámara nativa del dispositivo (provider automático de
    Kivy). En escritorio requiere tener instalado opencv-python para que
    Kivy pueda usar la webcam como "provider" de la Camera; si no lo tienes,
    usa el botón "Galería" en la pantalla principal en su lugar.
    """

    def __init__(self, categorias, al_agregar_prenda, **kwargs):
        super().__init__(**kwargs)
        self.categorias = categorias
        self._al_agregar_prenda = al_agregar_prenda
        self.categoria_objetivo = None

        raiz = BoxLayout(orientation="vertical")
        FondoDegradado(raiz, FONDO_ARRIBA, FONDO_ABAJO)

        self.etiqueta_categoria = Label(
            text="",
            color=TEXTO,
            bold=True,
            size_hint=(1, None),
            height=dp(34),
        )
        raiz.add_widget(self.etiqueta_categoria)

        try:
            self.camara = Camera(play=False, resolution=(720, 960), size_hint=(1, 0.82))
        except Exception:
            self.camara = None

        if self.camara is not None:
            raiz.add_widget(self.camara)
        else:
            raiz.add_widget(
                Label(
                    text="No se detectó una cámara disponible en este dispositivo.\n"
                    "Usa el botón 'Galería' en la pantalla principal.",
                    color=TEXTO,
                    size_hint=(1, 0.82),
                )
            )

        fila_botones = BoxLayout(size_hint=(1, 0.18), spacing=dp(10), padding=dp(10))
        boton_capturar = BotonNeon(text="Capturar foto", color=NEON_CIAN)
        boton_capturar.bind(on_release=lambda *_: self._capturar())
        boton_cancelar = BotonNeon(text="Volver", color=NEON_MAGENTA)
        boton_cancelar.bind(on_release=lambda *_: self._cerrar())
        fila_botones.add_widget(boton_capturar)
        fila_botones.add_widget(boton_cancelar)
        raiz.add_widget(fila_botones)

        self.add_widget(raiz)

    def on_enter(self):
        if self.categoria_objetivo:
            self.etiqueta_categoria.text = f"Fotografiando: {self.categorias.get(self.categoria_objetivo, '')}"
        if self.camara is not None:
            self.camara.play = True

    def on_leave(self):
        if self.camara is not None:
            self.camara.play = False

    def _capturar(self):
        if self.camara is None:
            return
        marca = int(time.time() * 1000)
        ruta_original = os.path.join(CARPETA_CAPTURAS, f"foto_{marca}.png")
        self.camara.export_to_png(ruta_original)
        self._procesar_y_agregar(ruta_original)

    def _procesar_y_agregar(self, ruta_original):
        ruta_sin_fondo = ruta_original.replace(".png", "_sf.png")
        try:
            quitar_fondo(ruta_original, ruta_sin_fondo)
        except Exception:
            ruta_sin_fondo = ruta_original  # si algo falla, usamos la foto original

        categoria = self.categoria_objetivo or next(iter(self.categorias))
        self._al_agregar_prenda(categoria, ruta_sin_fondo)
        self._cerrar()

    def _cerrar(self):
        self.manager.current = "principal"
