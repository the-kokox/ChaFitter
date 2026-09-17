"""Paleta oscura vibrante y componentes visuales de la aplicación."""

from kivy.animation import Animation
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

# ---------- Paleta ----------
# Fondo casi negro con un tinte azulado, en vez de un gris plano: da más
# sensación de profundidad en pantallas oscuras.
FONDO_ARRIBA = (0.055, 0.06, 0.09, 1)
FONDO_ABAJO = (0.02, 0.022, 0.035, 1)
FONDO = FONDO_ABAJO  # se mantiene por compatibilidad con código existente

PANEL = (0.10, 0.11, 0.15, 1)
PANEL_CLARO = (0.15, 0.16, 0.22, 1)
BORDE_SUTIL = (0.24, 0.26, 0.34, 1)

# Acentos neón reales (antes eran grises apagados sin color).
NEON_CIAN = (0.0, 0.85, 1.0, 1)
NEON_MAGENTA = (1.0, 0.16, 0.62, 1)
NEON_VERDE = (0.25, 1.0, 0.55, 1)
NEON_MORADO = (0.58, 0.4, 1.0, 1)
NEON_AMARILLO = (1.0, 0.82, 0.25, 1)

TEXTO = (0.95, 0.96, 0.99, 1)
TEXTO_TENUE = (0.56, 0.59, 0.7, 1)

# Colores de acento por categoría, para darle identidad visual a cada fila
# del guardarropa sin recargar la interfaz.
ACENTOS_CATEGORIA = [NEON_CIAN, NEON_MAGENTA, NEON_VERDE, NEON_MORADO, NEON_AMARILLO]


def _mezclar(color_a, color_b, t):
    return tuple(color_a[i] + (color_b[i] - color_a[i]) * t for i in range(4))


class FondoDegradado:
    """Pinta un degradado vertical liso en el canvas.before de un widget.

    Kivy no trae un widget de degradado nativo, así que se simula apilando
    varias franjas horizontales cuyo color va interpolando entre dos tonos.
    Se actualiza solo al cambiar tamaño/posición del widget dueño.
    """

    def __init__(self, widget, color_arriba=FONDO_ARRIBA, color_abajo=FONDO_ABAJO, pasos=40):
        self.widget = widget
        self.pasos = pasos
        self._colores = []
        self._rects = []
        with widget.canvas.before:
            for i in range(pasos):
                t = i / max(1, pasos - 1)
                color = Color(*_mezclar(color_arriba, color_abajo, t))
                rect = Rectangle()
                self._colores.append(color)
                self._rects.append(rect)
        widget.bind(pos=self._actualizar, size=self._actualizar)
        self._actualizar(widget, None)

    def _actualizar(self, widget, _valor):
        alto_franja = widget.height / self.pasos if self.pasos else widget.height
        for indice, rect in enumerate(self._rects):
            y = widget.y + widget.height - (indice + 1) * alto_franja
            rect.pos = (widget.x, y)
            # +1px de solape para que no queden líneas visibles entre franjas
            rect.size = (widget.width, alto_franja + 1)


class TarjetaNeon(BoxLayout):
    """Contenedor oscuro con borde de acento y un halo suave (glow)."""

    def __init__(self, color_borde=NEON_CIAN, radio=None, **kwargs):
        radio = radio if radio is not None else dp(12)
        super().__init__(**kwargs)
        self.radio = radio
        self.color_borde = color_borde
        with self.canvas.before:
            # Halo: una línea ancha y muy transparente del color de acento,
            # simula un resplandor sutil detrás de la tarjeta.
            Color(*color_borde[:3], 0.14)
            self._halo = Line(rounded_rectangle=(*self.pos, *self.size, radio + dp(3)), width=dp(4))
            Color(*PANEL)
            self._fondo = RoundedRectangle(pos=self.pos, size=self.size, radius=[radio])
            Color(*color_borde[:3], 0.55)
            self._borde = Line(rounded_rectangle=(*self.pos, *self.size, radio), width=dp(1.2))
        self.bind(pos=self._actualizar, size=self._actualizar)

    def _actualizar(self, *_):
        self._halo.rounded_rectangle = (*self.pos, *self.size, self.radio + dp(3))
        self._fondo.pos = self.pos
        self._fondo.size = self.size
        self._borde.rounded_rectangle = (*self.pos, *self.size, self.radio)


class BotonNeon(Button):
    """Botón oscuro con relleno de acento y animación al presionar."""

    def __init__(self, color=NEON_CIAN, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.color = TEXTO
        self.bold = True
        self.halign = "center"
        self.valign = "middle"
        self._color_acento = color
        with self.canvas.before:
            self._color_relleno = Color(*color[:3], 0.16)
            self._fondo = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
            self._color_borde = Color(*color[:3], 0.75)
            self._borde = Line(rounded_rectangle=(*self.pos, *self.size, dp(10)), width=dp(1.1))
        self.bind(pos=self._actualizar, size=self._actualizar, size_hint=self._actualizar)
        self.bind(size=self._sync_texto, state=self._al_cambiar_estado)

    def _sync_texto(self, *_):
        self.text_size = self.size

    def _actualizar(self, *_):
        self._fondo.pos = self.pos
        self._fondo.size = self.size
        self._borde.rounded_rectangle = (*self.pos, *self.size, dp(10))

    def _al_cambiar_estado(self, _widget, estado):
        # Feedback visual al tocar: el relleno se vuelve más sólido y el
        # texto toma el color de acento (antes no había ninguna señal táctil).
        if estado == "down":
            self._color_relleno.a = 0.42
            self.color = (1, 1, 1, 1)
        else:
            self._color_relleno.a = 0.16
            self.color = TEXTO


class TituloSeccion(Label):
    def __init__(self, color_acento=None, **kwargs):
        super().__init__(**kwargs)
        self.color = TEXTO
        self.bold = True
        self.font_size = "15sp"
        self.size_hint_y = None
        self.height = dp(32)
        self.halign = "left"
        self.valign = "middle"
        self.color_acento = color_acento
        self.bind(size=self._sync_texto)

    def _sync_texto(self, *_):
        self.text_size = self.size


class BarraAcento(BoxLayout):
    """Franja delgada de color de acento, usada como detalle decorativo
    junto a títulos de sección para reforzar la identidad de cada categoría."""

    def __init__(self, color=NEON_CIAN, **kwargs):
        kwargs.setdefault("size_hint", (None, None))
        kwargs.setdefault("size", (dp(4), dp(20)))
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(2)])
        self.bind(pos=self._actualizar, size=self._actualizar)

    def _actualizar(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size
