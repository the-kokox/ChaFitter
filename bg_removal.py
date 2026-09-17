"""Elimina el fondo de una foto de ropa con un algoritmo ligero (sin modelos
pesados de IA), pensado para poder correr también dentro de un celular Android."""

import numpy as np
from PIL import Image

# Más grande = recorte más preciso pero más lento en un celular de gama media
TAMANO_MAXIMO_PROCESO = 380


def _dilatar(mascara):
    """Expande en un píxel una máscara booleana en las 4 direcciones."""
    arriba = np.zeros_like(mascara)
    abajo = np.zeros_like(mascara)
    izquierda = np.zeros_like(mascara)
    derecha = np.zeros_like(mascara)
    arriba[1:, :] = mascara[:-1, :]
    abajo[:-1, :] = mascara[1:, :]
    izquierda[:, 1:] = mascara[:, :-1]
    derecha[:, :-1] = mascara[:, 1:]
    return mascara | arriba | abajo | izquierda | derecha


def _erosionar(mascara):
    """Reduce en un píxel una máscara booleana (opuesto de _dilatar)."""
    return ~_dilatar(~mascara)


def _quitar_manchas_pequenas(mascara, iteraciones=1):
    """Elimina puntos aislados (ruido tipo "sal y pimienta") de la máscara con
    una apertura morfológica simple: erosiona y luego vuelve a dilatar.
    Evita que reflejos o sombras puntuales dentro de la prenda queden
    marcados como fondo, o viceversa."""
    resultado = mascara
    for _ in range(iteraciones):
        resultado = _erosionar(resultado)
    for _ in range(iteraciones):
        resultado = _dilatar(resultado)
    return resultado


def _suavizar_bordes(alfa, pasadas=2):
    """Aplica un filtro de caja 3x3 sobre el canal alfa para anti-aliasing.

    Convierte el corte "duro" (0 o 255) en un borde con degradado suave de
    un par de píxeles, que se ve mucho más natural que un recorte pixelado.
    Usa np.roll (desplazamiento circular) en vez de relleno con padding: es
    más barato en CPU y, como el fondo casi siempre toca los bordes del
    cuadro, el pequeño artefacto de "envolver" en los extremos es
    imperceptible en la práctica.
    """
    matriz = alfa.astype(np.float32)
    for _ in range(pasadas):
        acumulado = np.zeros_like(matriz)
        for desplazamiento_y in (-1, 0, 1):
            for desplazamiento_x in (-1, 0, 1):
                acumulado += np.roll(
                    np.roll(matriz, desplazamiento_y, axis=0), desplazamiento_x, axis=1
                )
        matriz = acumulado / 9.0
    return matriz


def quitar_fondo(
    ruta_entrada: str,
    ruta_salida: str,
    tolerancia: int = 42,
    iteraciones_max: int = 140,
    suavizar_bordes: bool = True,
):
    """Convierte a transparente el fondo de la foto y guarda un PNG con canal alfa.

    Estrategia (sin redes neuronales, apta para dispositivos móviles):
    1. Estima el color de fondo con la MEDIANA de las esquinas/bordes de la
       foto (más robusta que el promedio: una sombra o un reflejo puntual en
       una esquina ya no arrastra el color estimado hacia un tono raro).
    2. Ajusta la tolerancia automáticamente según qué tan uniforme es ese
       fondo: un fondo muy parejo (pared lisa) usa una tolerancia más
       ajustada, y uno con algo de textura (mesa de madera, tela con
       arrugas) se vuelve un poco más permisivo para no dejar restos.
    3. Marca como "posible fondo" cada píxel de color cercano a ese color
       (operación vectorizada, muy rápida) y propaga esa marca desde los
       bordes hacia adentro (flood-fill por dilatación), para no borrar por
       error partes de la ropa que compartan un color parecido al fondo pero
       no estén conectadas a él.
    4. Limpia manchas pequeñas mal clasificadas (apertura morfológica) y
       suaviza el borde final del recorte para evitar el efecto "pixelado".

    Funciona mejor con fondos lisos o poco texturizados (pared, mesa, sábana).
    """
    img = Image.open(ruta_entrada).convert("RGB")
    ancho_original, alto_original = img.size

    escala = min(1.0, TAMANO_MAXIMO_PROCESO / max(ancho_original, alto_original))
    img_chica = (
        img.resize((max(1, int(ancho_original * escala)), max(1, int(alto_original * escala))))
        if escala < 1.0
        else img
    )

    datos = np.array(img_chica).astype(np.int16)
    alto, ancho, _ = datos.shape

    margen = max(4, min(alto, ancho) // 20)
    muestras = np.concatenate(
        [
            datos[:margen, :, :].reshape(-1, 3),
            datos[-margen:, :, :].reshape(-1, 3),
            datos[:, :margen, :].reshape(-1, 3),
            datos[:, -margen:, :].reshape(-1, 3),
        ]
    )
    # Mediana en vez de promedio: ignora mejor a los "outliers" (una sombra
    # dura o un brillo puntual en una esquina) al estimar el color de fondo.
    color_fondo = np.median(muestras, axis=0)

    # Tolerancia adaptativa: un fondo con variación natural (textura, luz
    # despareja) necesita algo más de margen que uno perfectamente uniforme.
    variacion_fondo = np.mean(np.std(muestras, axis=0))
    tolerancia_efectiva = tolerancia + min(18, variacion_fondo * 0.6)

    distancia = np.abs(datos - color_fondo).sum(axis=2)
    es_similar_al_fondo = distancia < (tolerancia_efectiva * 3)

    borde = np.zeros((alto, ancho), dtype=bool)
    borde[0, :] = borde[-1, :] = True
    borde[:, 0] = borde[:, -1] = True

    region_fondo = es_similar_al_fondo & borde
    for _ in range(iteraciones_max):
        crecida = _dilatar(region_fondo) & es_similar_al_fondo
        if np.array_equal(crecida, region_fondo):
            break
        region_fondo = crecida

    region_fondo = _quitar_manchas_pequenas(region_fondo)

    alfa = np.where(region_fondo, 0, 255).astype(np.uint8)
    if suavizar_bordes:
        alfa = np.clip(_suavizar_bordes(alfa), 0, 255).astype(np.uint8)

    rgba_chico = np.dstack([np.array(img_chica), alfa])
    resultado = Image.fromarray(rgba_chico, mode="RGBA")

    if escala < 1.0:
        resultado = resultado.resize((ancho_original, alto_original), Image.BILINEAR)

    resultado.save(ruta_salida)
    return ruta_salida
