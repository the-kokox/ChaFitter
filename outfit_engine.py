"""Motor de combinación de prendas para armar outfits según su paleta de color."""

import itertools
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Tuple

from color_utils import clasificar_armonia, extraer_paleta

# Peso de cada color de la paleta de una prenda al comparar contra otra:
# el color dominante pesa mucho más que los secundarios, pero estos ya no
# se ignoran del todo como antes (antes solo se comparaba color_principal
# contra color_principal, perdiendo matices como una camisa mayormente
# blanca con un detalle de color que sí combina con el pantalón).
_PESOS_PALETA = (0.6, 0.28, 0.12)


@dataclass
class Prenda:
    ruta: str
    categoria: str
    paleta: List[Tuple[int, int, int]] = field(default_factory=list)
    seleccionada: bool = True  # se incluye en la generación de outfits por defecto

    def __post_init__(self):
        if not self.paleta:
            self.paleta = extraer_paleta(self.ruta, num_colores=3)

    @property
    def color_principal(self):
        return self.paleta[0]

    def alternar_seleccion(self):
        self.seleccionada = not self.seleccionada
        return self.seleccionada


def _puntaje_entre_prendas(prenda1: Prenda, prenda2: Prenda):
    """Compara las paletas completas de dos prendas (no solo su color
    dominante), ponderando cada color según su peso en _PESOS_PALETA.

    Devuelve (etiqueta_para_mostrar, puntaje_ponderado). La etiqueta se
    calcula solo entre los colores dominantes, ya que es la relación más
    representativa para explicarle al usuario por qué combinan.
    """
    paleta1 = list(prenda1.paleta[: len(_PESOS_PALETA)])
    paleta2 = list(prenda2.paleta[: len(_PESOS_PALETA)])
    # Si a una prenda le faltan colores en la paleta, repite el último para
    # no perder peso en la ponderación.
    while len(paleta1) < len(_PESOS_PALETA):
        paleta1.append(paleta1[-1] if paleta1 else prenda1.color_principal)
    while len(paleta2) < len(_PESOS_PALETA):
        paleta2.append(paleta2[-1] if paleta2 else prenda2.color_principal)

    etiqueta_principal, _ = clasificar_armonia(paleta1[0], paleta2[0])

    total = 0.0
    suma_pesos = 0.0
    for indice1, color1 in enumerate(paleta1):
        for indice2, color2 in enumerate(paleta2):
            peso = _PESOS_PALETA[indice1] * _PESOS_PALETA[indice2]
            _, puntaje = clasificar_armonia(color1, color2)
            total += puntaje * peso
            suma_pesos += peso

    puntaje_ponderado = total / suma_pesos if suma_pesos else 0.5
    return etiqueta_principal, puntaje_ponderado


def puntuar_outfit(prendas: List[Prenda]):
    """Calcula el puntaje de armonía cromática promedio entre todas las prendas."""
    if len(prendas) < 2:
        return 1.0, []

    detalles = []
    puntajes = []
    for p1, p2 in itertools.combinations(prendas, 2):
        etiqueta, puntaje = _puntaje_entre_prendas(p1, p2)
        puntajes.append(puntaje)
        detalles.append((p1, p2, etiqueta, puntaje))

    return sum(puntajes) / len(puntajes), detalles


def generar_outfits(guardarropa: dict, max_resultados: int = 6, solo_seleccionadas: bool = True):
    """Genera las mejores combinaciones a partir de las prendas del guardarropa.

    guardarropa: dict categoria -> lista de Prenda.
    Si solo_seleccionadas=True (por defecto), únicamente se usan las prendas
    marcadas como seleccionadas por el usuario en la interfaz; así se pueden
    excluir prendas del cálculo sin borrarlas del guardarropa.
    """
    pool = {}
    for categoria, prendas in guardarropa.items():
        items = [p for p in prendas if (p.seleccionada or not solo_seleccionadas)]
        if items:
            pool[categoria] = items

    categorias_disponibles = list(pool.keys())
    if len(categorias_disponibles) < 2:
        return []

    combinaciones = list(itertools.product(*[pool[c] for c in categorias_disponibles]))

    resultados = []
    for combo in combinaciones:
        puntaje, detalles = puntuar_outfit(list(combo))
        resultados.append({"prendas": combo, "puntaje": puntaje, "detalles": detalles})

    resultados.sort(key=lambda r: r["puntaje"], reverse=True)

    # Mantiene la armonía, pero evita que las primeras sugerencias reciclen
    # continuamente la misma prenda cuando existen alternativas válidas.
    seleccionados = []
    usos = Counter()
    pendientes = resultados[:]
    while pendientes and len(seleccionados) < max_resultados:
        candidato = max(
            pendientes,
            key=lambda resultado: resultado["puntaje"]
            + 0.12
            * sum(
                1 / (1 + usos[id(prenda)])
                for prenda in resultado["prendas"]
            )
            / len(resultado["prendas"]),
        )
        pendientes.remove(candidato)
        seleccionados.append(candidato)
        for prenda in candidato["prendas"]:
            usos[id(prenda)] += 1

    return seleccionados
