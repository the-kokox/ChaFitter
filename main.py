"""
OUTFIT AI · App futurista para armar outfits según la paleta de color de tus prendas.
Funciona en Android (cámara real) y en escritorio (Windows/Mac/Linux).

Ejecutar en PC:       python main.py
Compilar a Android:   buildozer -v android debug   (ver README.md)
"""

import sys
import os
from uuid import uuid4

if sys.platform == "win32":
    import tkinter as tk
    from tkinter import filedialog
else:
    tk = None
    filedialog = None

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView

from bg_removal import quitar_fondo
from camera_screen import PantallaCamara
from outfit_engine import Prenda, generar_outfits
from theme import (
    ACENTOS_CATEGORIA,
    FONDO,
    FONDO_ABAJO,
    FONDO_ARRIBA,
    PANEL,
    NEON_CIAN,
    NEON_MAGENTA,
    NEON_MORADO,
    TEXTO,
    TEXTO_TENUE,
    BarraAcento,
    BotonNeon,
    FondoDegradado,
    TituloSeccion,
)
from widgets import MiniaturaPrenda, TarjetaOutfit

try:
    from plyer import filechooser
except Exception:  # plyer puede faltar en algunos entornos de escritorio
    filechooser = None

CATEGORIAS = {
    "arriba": "Parte de arriba",
    "abajo": "Parte de abajo",
    "calzado": "Calzado",
    "accesorio": "Accesorio",
}

Window.clearcolor = FONDO


class FilaCategoria(BoxLayout):
    """Una fila del guardarropa: nombre de categoría + botones de agregar + miniaturas."""

    def __init__(self, clave, etiqueta, on_camara, on_galeria, color_acento=NEON_CIAN, **kwargs):
        super().__init__(
            orientation="vertical",
            size_hint=(1, None),
            height=dp(180),
            spacing=dp(4),
            padding=dp(10),
            **kwargs,
        )
        self.clave = clave
        self.color_acento = color_acento

        with self.canvas.before:
            Color(*PANEL)
            self._fondo = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
            Color(*color_acento[:3], 0.35)
            self._borde = Line(rounded_rectangle=(*self.pos, *self.size, dp(10)), width=dp(1))
        self.bind(pos=self._actualizar_fondo, size=self._actualizar_fondo)

        encabezado = BoxLayout(size_hint=(1, None), height=dp(28), spacing=dp(8))
        encabezado.add_widget(BarraAcento(color=color_acento))
        encabezado.add_widget(TituloSeccion(text=etiqueta))
        self.add_widget(encabezado)

        cuerpo = BoxLayout(spacing=dp(10))

        columna_botones = BoxLayout(
            orientation="vertical", size_hint=(None, 1), width=dp(112), spacing=dp(6)
        )
        boton_camara = BotonNeon(text="Cámara", font_size="13sp", color=color_acento)
        boton_camara.bind(on_release=lambda *_: on_camara(clave))
        boton_galeria = BotonNeon(text="Elegir archivo", font_size="13sp", color=NEON_MORADO)
        boton_galeria.bind(on_release=lambda *_: on_galeria(clave))
        columna_botones.add_widget(boton_camara)
        columna_botones.add_widget(boton_galeria)
        cuerpo.add_widget(columna_botones)

        self.scroll_miniaturas = ScrollView(size_hint=(1, 1), do_scroll_y=False)
        self.fila_miniaturas = BoxLayout(size_hint=(None, 1), spacing=dp(6))
        self.fila_miniaturas.bind(minimum_width=self.fila_miniaturas.setter("width"))
        self.scroll_miniaturas.add_widget(self.fila_miniaturas)
        cuerpo.add_widget(self.scroll_miniaturas)

        self.add_widget(cuerpo)

    def agregar_miniatura(self, widget):
        self.fila_miniaturas.add_widget(widget)

    def quitar_miniatura(self, widget):
        self.fila_miniaturas.remove_widget(widget)

    def _actualizar_fondo(self, *_):
        self._fondo.pos = self.pos
        self._fondo.size = self.size
        self._borde.rounded_rectangle = (*self.pos, *self.size, dp(10))


class PantallaPrincipal(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.guardarropa = {c: [] for c in CATEGORIAS}
        self.filas_categoria = {}
        self.widgets_miniatura = {}  # Prenda -> MiniaturaPrenda
        self.colores_categoria = {
            clave: ACENTOS_CATEGORIA[indice % len(ACENTOS_CATEGORIA)]
            for indice, clave in enumerate(CATEGORIAS)
        }

        raiz = BoxLayout(orientation="vertical", spacing=dp(8), padding=(dp(10), dp(8)))
        FondoDegradado(raiz, FONDO_ARRIBA, FONDO_ABAJO)

        raiz.add_widget(
            Label(
                text="[b]Cha[color=#00D9FF]Fitter[/color][/b]",
                markup=True,
                font_size="26sp",
                color=TEXTO,
                size_hint=(1, None),
                height=dp(36),
                halign="left",
            )
        )
        raiz.add_widget(
            Label(
                text="Arma combinaciones con las prendas de tu guardarropa",
                font_size="12sp",
                color=TEXTO_TENUE,
                size_hint=(1, None),
                height=dp(18),
                halign="left",
            )
        )

        scroll_categorias = ScrollView(size_hint=(1, 1))
        contenedor_categorias = BoxLayout(orientation="vertical", size_hint=(1, None), spacing=dp(8))
        contenedor_categorias.bind(minimum_height=contenedor_categorias.setter("height"))

        for indice, (clave, etiqueta) in enumerate(CATEGORIAS.items()):
            color_acento = ACENTOS_CATEGORIA[indice % len(ACENTOS_CATEGORIA)]
            fila = FilaCategoria(
                clave, etiqueta, self._abrir_camara, self._abrir_galeria, color_acento=color_acento
            )
            self.filas_categoria[clave] = fila
            contenedor_categorias.add_widget(fila)

        scroll_categorias.add_widget(contenedor_categorias)
        raiz.add_widget(scroll_categorias)

        pie = Label(
            text="Toca una prenda para incluirla o excluirla",
            font_size="11sp",
            color=TEXTO_TENUE,
            size_hint=(1, None),
            height=dp(16),
        )
        raiz.add_widget(pie)

        self.boton_generar = BotonNeon(
            text="GENERAR OUTFITS",
            color=NEON_CIAN,
            size_hint=(1, None),
            height=dp(44),
            font_size="15sp",
        )
        self.boton_generar.bind(on_release=lambda *_: self._generar_outfits())
        raiz.add_widget(self.boton_generar)

        raiz.add_widget(
            Label(
                text="Hecho por: Luis Ealo y Alejandro Rivera",
                font_size="10sp",
                color=TEXTO_TENUE,
                size_hint=(1, None),
                height=dp(20),
                halign="right",
                valign="middle",
                text_size=(None, dp(20)),
            )
        )

        self.add_widget(raiz)

    # ---------- Cámara / Galería ----------
    def _abrir_camara(self, categoria):
        pantalla_camara = self.manager.get_screen("camara")
        pantalla_camara.categoria_objetivo = categoria
        self.manager.current = "camara"

    def _abrir_galeria(self, categoria):
        if sys.platform == "win32":
            ventana = tk.Tk()
            ventana.withdraw()
            ventana.attributes("-topmost", True)
            ruta = filedialog.askopenfilename(
                parent=ventana,
                title="Seleccionar prenda",
                filetypes=[
                    ("Imágenes", "*.png *.jpg *.jpeg *.webp"),
                    ("Todos los archivos", "*.*"),
                ],
            )
            ventana.destroy()
            if ruta:
                self.agregar_prenda(categoria, ruta)
            return

        if filechooser is None:
            self._mostrar_aviso("La galería no está disponible en este entorno.")
            return
        filechooser.open_file(
            on_selection=lambda seleccion: Clock.schedule_once(
                lambda *_: self._al_elegir_de_galeria(categoria, seleccion)
            ),
            filters=["*.png", "*.jpg", "*.jpeg", "*.webp"],
        )

    def _al_elegir_de_galeria(self, categoria, seleccion):
        if not seleccion:
            return
        self.agregar_prenda(categoria, seleccion[0])

    # ---------- Guardarropa ----------
    def agregar_prenda(self, categoria, ruta_imagen):
        try:
            ruta_prenda = ruta_imagen
            if not ruta_imagen.lower().endswith("_sf.png"):
                carpeta_procesadas = os.path.join(
                    os.path.expanduser("~"), ".outfit_ai_procesadas"
                )
                os.makedirs(carpeta_procesadas, exist_ok=True)
                ruta_procesada = os.path.join(
                    carpeta_procesadas, f"prenda_{uuid4().hex}.png"
                )
                try:
                    quitar_fondo(ruta_imagen, ruta_procesada)
                    ruta_prenda = ruta_procesada
                except Exception:
                    pass

            prenda = Prenda(ruta=ruta_prenda, categoria=categoria)
        except Exception as e:
            self._mostrar_aviso(f"No se pudo leer la imagen:\n{e}")
            return

        self.guardarropa[categoria].append(prenda)

        miniatura = MiniaturaPrenda(
            prenda,
            on_eliminar=lambda p: self._eliminar_prenda(categoria, p),
            color_acento=self.colores_categoria.get(categoria, NEON_CIAN),
        )
        self.widgets_miniatura[id(prenda)] = miniatura
        self.filas_categoria[categoria].agregar_miniatura(miniatura)

    def _eliminar_prenda(self, categoria, prenda):
        if prenda in self.guardarropa[categoria]:
            self.guardarropa[categoria].remove(prenda)
        widget = self.widgets_miniatura.pop(id(prenda), None)
        if widget:
            self.filas_categoria[categoria].quitar_miniatura(widget)

    def _mostrar_aviso(self, texto):
        Popup(
            title="Aviso",
            title_color=TEXTO,
            background="",
            background_color=PANEL,
            separator_color=(*NEON_CIAN[:3], 0.6),
            content=Label(text=texto, color=TEXTO),
            size_hint=(0.8, 0.3),
        ).open()

    # ---------- Generación de outfits ----------
    def _generar_outfits(self):
        resultados = generar_outfits(self.guardarropa, max_resultados=6)

        if not resultados:
            self._mostrar_aviso(
                "Selecciona (borde encendido) al menos una prenda\n"
                "en dos categorías distintas para generar outfits."
            )
            return

        contenido = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(10))
        contenido.add_widget(
            Label(
                text=f"{len(resultados)} outfits sugeridos",
                bold=True,
                color=NEON_CIAN,
                size_hint=(1, None),
                height=dp(24),
            )
        )

        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        columna = BoxLayout(orientation="vertical", size_hint=(1, None), spacing=dp(10))
        columna.bind(minimum_height=columna.setter("height"))

        for resultado in resultados:
            columna.add_widget(TarjetaOutfit(resultado, CATEGORIAS))

        scroll.add_widget(columna)
        contenido.add_widget(scroll)

        Popup(
            title="Tus outfits",
            title_color=TEXTO,
            background="",
            background_color=PANEL,
            content=contenido,
            size_hint=(0.88, 0.78),
            separator_color=(*NEON_CIAN[:3], 0.6),
        ).open()


class OutfitAIApp(App):
    def build(self):
        self.title = "ChaFitter"
        gestor = ScreenManager()

        principal = PantallaPrincipal(name="principal")
        gestor.add_widget(principal)

        camara = PantallaCamara(
            categorias=CATEGORIAS,
            al_agregar_prenda=lambda categoria, ruta: principal.agregar_prenda(categoria, ruta),
            name="camara",
        )
        gestor.add_widget(camara)

        return gestor


if __name__ == "__main__":
    OutfitAIApp().run()
