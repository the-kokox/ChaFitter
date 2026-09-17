"""Utilidades para extraer y analizar paletas de color de imágenes de ropa."""

import colorsys
import math
from PIL import Image

# Ángulos de matiz (en grados) que tradicionalmente combinan bien en teoría
# del color, con un puntaje base de qué tan agradable resulta cada relación.
_ANGULOS_ARMONICOS = (
    (0, "monocromático", 0.92),
    (30, "análogo", 0.86),
    (60, "análogo amplio", 0.74),
    (120, "triádico", 0.82),
    (150, "pre-complementario", 0.68),
    (180, "complementario", 0.95),
)
_ANCHO_CAMPANA = 22.0  # qué tan "tolerante" es cada ángulo armónico, en grados
_PUNTAJE_PISO = 0.32  # ninguna combinación de color se puntúa peor que esto


def extraer_paleta(ruta_imagen: str, num_colores: int = 5):
    """Extrae los colores dominantes de una prenda.

    Si la imagen ya pasó por quitar_fondo() y tiene canal alfa, ignora los
    píxeles transparentes para que el fondo no contamine la paleta.
    """
    img = Image.open(ruta_imagen).convert("RGBA")
    img.thumbnail((150, 150))

    # Filtramos píxeles transparentes sin NumPy
    pixeles_prenda = []
    for r, g, b, a in img.getdata():
        if a > 10:
            pixeles_prenda.append((r, g, b))

    if not pixeles_prenda:
        # Si todo es transparente, tomamos todos los píxeles en RGB
        img_rgb = img.convert("RGB")
        pixeles_prenda = list(img_rgb.getdata())

    # Para cuantizar, creamos una imagen temporal con los píxeles filtrados
    # Usamos una imagen de 1xN para pasarla por quantize
    img_compacta = Image.new("RGB", (1, len(pixeles_prenda)))
    img_compacta.putdata(pixeles_prenda)

    img_cuantizada = img_compacta.quantize(colors=min(num_colores, 256), method=Image.MEDIANCUT)
    paleta = img_cuantizada.getpalette()
    conteo = img_cuantizada.getcolors()
    if conteo:
        conteo.sort(key=lambda x: x[0], reverse=True)
    else:
        return []

    colores = []
    for _, indice in conteo:
        r = paleta[indice * 3]
        g = paleta[indice * 3 + 1]
        b = paleta[indice * 3 + 2]
        colores.append((r, g, b))

    return colores


def color_dominante(ruta_imagen: str):
    """Devuelve el color RGB más dominante de la prenda."""
    paleta = extraer_paleta(ruta_imagen, num_colores=5)
    return paleta[0] if paleta else (255, 255, 255)


def rgb_a_hsv(color_rgb):
    r, g, b = (v / 255.0 for v in color_rgb)
    return colorsys.rgb_to_hsv(r, g, b)


def rgb_a_hex(color_rgb):
    return "#{:02x}{:02x}{:02x}".format(*color_rgb)


def distancia_de_matiz(color1, color2):
    """Distancia angular entre dos matices, en grados (0-180)."""
    h1, _, _ = rgb_a_hsv(color1)
    h2, _, _ = rgb_a_hsv(color2)
    diferencia = abs(h1 - h2) * 360
    return min(diferencia, 360 - diferencia)


def _puntaje_por_distancia(distancia):
    """Puntaje continuo (0-1): qué tan cerca está `distancia` de alguno de
    los ángulos armónicos conocidos."""
    mejor_etiqueta = "disonante"
    mejor_puntaje = 0.0
    for angulo, etiqueta, base in _ANGULOS_ARMONICOS:
        diferencia = abs(distancia - angulo)
        peso = math.exp(-(diferencia**2) / (2 * _ANCHO_CAMPANA**2))
        puntaje = base * peso
        if puntaje > mejor_puntaje:
            mejor_puntaje = puntaje
            mejor_etiqueta = etiqueta
    if mejor_puntaje < 0.2:
        mejor_etiqueta = "disonante"
    return mejor_etiqueta, _PUNTAJE_PISO + mejor_puntaje * (1 - _PUNTAJE_PISO)


def clasificar_armonia(color1, color2):
    """Clasifica la relación cromática entre dos colores."""
    h1, s1, v1 = rgb_a_hsv(color1)
    h2, s2, v2 = rgb_a_hsv(color2)

    es_neutro1 = s1 < 0.12 or v1 < 0.12
    es_neutro2 = s2 < 0.12 or v2 < 0.12
    if es_neutro1 and es_neutro2:
        return "neutro", 0.9
    if es_neutro1 or es_neutro2:
        return "neutro", 0.88

    distancia = distancia_de_matiz(color1, color2)
    etiqueta, puntaje_base = _puntaje_por_distancia(distancia)

    ajuste_saturacion = 1 - 0.12 * abs(s1 - s2)
    ajuste_brillo = 1 - 0.12 * abs(v1 - v2)
    puntaje_final = puntaje_base * ajuste_saturacion * ajuste_brillo

    return etiqueta, max(_PUNTAJE_PISO * 0.7, min(0.97, puntaje_final))


def puntaje_par(color1, color2):
    _, puntaje = clasificar_armonia(color1, color2)
    return puntaje
