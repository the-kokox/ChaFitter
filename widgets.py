"""Widgets reutilizables: miniatura de prenda seleccionable y tarjeta de outfit."""

from kivy.graphics import Color, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label

from theme import NEON_CIAN, NEON_MAGENTA, NEON_VERDE, PANEL, PANEL_CLARO, TEXTO, TEXTO_TENUE

BORDE_APAGADO = (0.3, 0.32, 0.4, 0.7)


class MiniaturaPrenda(ButtonBehavior, BoxLayout):
    """Miniatura de una prenda subida. Se toca para seleccionar/deseleccionar
    (borde encendido con halo = se usará al generar outfits) y tiene botón
    para quitarla."""

    def __init__(self, prenda, on_toggle=None, on_eliminar=None, color_acento=NEON_CIAN, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (dp(114), dp(154)))
        super().__init__(orientation="vertical", padding=dp(6), spacing=dp(4), **kwargs)
        self.prenda = prenda
        self._on_toggle = on_toggle
        self.color_acento = color_acento

        with self.canvas.before:
            # Halo detrás del borde: solo se ve con fuerza cuando la prenda
            # está seleccionada (da la sensación de "encendida").
            self._color_halo = Color(*color_acento[:3], 0)
            self._halo = Line(rounded_rectangle=(*self.pos, *self.size, dp(9)), width=dp(3.5))
            Color(*PANEL)
            self._fondo = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
            self._color_borde_gfx = Color(*BORDE_APAGADO)
            self._borde = Line(rounded_rectangle=(*self.pos, *self.size, dp(8)), width=dp(1.1))
        self.bind(pos=self._actualizar, size=self._actualizar)

        self.imagen = KivyImage(
            source=prenda.ruta,
            size_hint=(1, 1),
            allow_stretch=True,
            keep_ratio=True,
            fit_mode="contain",
        )
        self.add_widget(self.imagen)

        fila_colores = BoxLayout(size_hint=(1, None), height=dp(11), spacing=dp(3))
        for color in prenda.paleta[:3]:
            fila_colores.add_widget(self._muestra_color(color))
        self.add_widget(fila_colores)

        boton_eliminar = Button(
            text="Quitar",
            font_size="11sp",
            size_hint=(1, None),
            height=dp(22),
            background_normal="",
            background_color=(0, 0, 0, 0),
            color=NEON_MAGENTA,
            bold=True,
        )
        if on_eliminar:
            boton_eliminar.bind(on_release=lambda *_: on_eliminar(self.prenda))
        self.add_widget(boton_eliminar)

        self._refrescar_borde()

    @staticmethod
    def _muestra_color(color):
        muestra = BoxLayout()
        with muestra.canvas:
            Color(color[0] / 255, color[1] / 255, color[2] / 255, 1)
            rect = RoundedRectangle(pos=muestra.pos, size=muestra.size, radius=[dp(2)])

        def _sync(_widget, valor, atributo=rect):
            setattr(atributo, "pos", muestra.pos)
            setattr(atributo, "size", muestra.size)

        muestra.bind(pos=_sync, size=_sync)
        return muestra

    def _actualizar(self, *_):
        self._halo.rounded_rectangle = (*self.pos, *self.size, dp(9))
        self._fondo.pos = self.pos
        self._fondo.size = self.size
        self._borde.rounded_rectangle = (*self.pos, *self.size, dp(8))

    def _refrescar_borde(self):
        if self.prenda.seleccionada:
            self._color_borde_gfx.rgba = (*self.color_acento[:3], 1)
            self._color_halo.a = 0.35
        else:
            self._color_borde_gfx.rgba = BORDE_APAGADO
            self._color_halo.a = 0

    def on_release(self):
        self.prenda.alternar_seleccion()
        self._refrescar_borde()
        if self._on_toggle:
            self._on_toggle(self.prenda)


class TarjetaOutfit(BoxLayout):
    """Tarjeta que muestra una combinación de prendas sugerida y su % de armonía."""

    def __init__(self, resultado, categorias_legibles, **kwargs):
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", dp(202))
        super().__init__(orientation="vertical", padding=dp(12), spacing=dp(8), **kwargs)

        puntaje = round(resultado["puntaje"] * 100)
        if puntaje >= 80:
            color_borde = NEON_VERDE
        elif puntaje >= 60:
            color_borde = NEON_CIAN
        else:
            color_borde = NEON_MAGENTA

        with self.canvas.before:
            Color(*color_borde[:3], 0.16)
            self._halo = Line(rounded_rectangle=(*self.pos, *self.size, dp(11)), width=dp(3.5))
            Color(*PANEL)
            self._fondo = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
            Color(*color_borde[:3], 0.8)
            self._borde = Line(rounded_rectangle=(*self.pos, *self.size, dp(10)), width=dp(1.3))
        self.bind(pos=self._actualizar, size=self._actualizar)

        fila_encabezado = BoxLayout(size_hint=(1, None), height=dp(26), spacing=dp(8))
        with fila_encabezado.canvas.before:
            Color(*color_borde[:3], 0.18)
            self._pastilla = RoundedRectangle(radius=[dp(12)])
        fila_encabezado.bind(
            pos=lambda w, v: self._actualizar_pastilla(),
            size=lambda w, v: self._actualizar_pastilla(),
        )
        self._fila_encabezado = fila_encabezado
        etiqueta_puntaje = Label(
            text=f"  Armonía {puntaje}%  ",
            bold=True,
            color=color_borde,
            size_hint=(None, 1),
            width=dp(140),
            font_size="14sp",
            halign="left",
            valign="middle",
        )
        etiqueta_puntaje.bind(size=lambda w, v: setattr(w, "text_size", v))
        fila_encabezado.add_widget(etiqueta_puntaje)
        self.add_widget(fila_encabezado)

        fila = BoxLayout(spacing=dp(10), size_hint=(1, 1))
        for prenda in resultado["prendas"]:
            columna = BoxLayout(orientation="vertical", spacing=dp(3))
            columna.add_widget(
                KivyImage(
                    source=prenda.ruta,
                    size_hint=(1, 1),
                    allow_stretch=True,
                    keep_ratio=True,
                    fit_mode="contain",
                )
            )
            columna.add_widget(
                Label(
                    text=categorias_legibles.get(prenda.categoria, ""),
                    font_size="10sp",
                    color=TEXTO_TENUE,
                    size_hint=(1, None),
                    height=dp(16),
                )
            )
            fila.add_widget(columna)
        self.add_widget(fila)

    def _actualizar_pastilla(self):
        self._pastilla.pos = self._fila_encabezado.pos
        self._pastilla.size = (dp(140), self._fila_encabezado.height)

    def _actualizar(self, *_):
        self._halo.rounded_rectangle = (*self.pos, *self.size, dp(11))
        self._fondo.pos = self.pos
        self._fondo.size = self.size
        self._borde.rounded_rectangle = (*self.pos, *self.size, dp(10))
