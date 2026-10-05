"""Barras de refuerzo corrugadas comerciales en Perú (ASTM A615 Gr 60).

Valores nominales de catálogo: diámetro en cm, área en cm², peso en kg/m.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

FY_GRADO_60 = 4200.0  # kgf/cm²


@dataclass(frozen=True)
class Barra:
    designacion: str  # '3/8"', '1/2"', '8mm', ...
    diametro: float  # cm
    area: float  # cm²
    peso: float  # kg/m


BARRAS: dict[str, Barra] = {
    b.designacion: b
    for b in (
        Barra('6mm', 0.600, 0.28, 0.222),
        Barra('8mm', 0.800, 0.50, 0.395),
        Barra('3/8"', 0.953, 0.71, 0.560),
        Barra('12mm', 1.200, 1.13, 0.888),
        Barra('1/2"', 1.270, 1.29, 0.994),
        Barra('5/8"', 1.588, 2.00, 1.552),
        Barra('3/4"', 1.905, 2.84, 2.235),
        Barra('1"', 2.540, 5.10, 3.973),
        Barra('1 3/8"', 3.581, 10.06, 7.907),
    )
}


def barra(designacion: str) -> Barra:
    """Devuelve la barra o falla con un mensaje que lista las válidas."""
    try:
        return BARRAS[designacion]
    except KeyError:
        validas = ", ".join(BARRAS)
        raise ValueError(f"Barra '{designacion}' no existe. Válidas: {validas}") from None


def area_acero(armado: dict[str, int]) -> float:
    """Área total [cm²] de un armado, p. ej. {'5/8"': 3, '1/2"': 2}."""
    return sum(barra(d).area * n for d, n in armado.items())


def numero_barras(As_req: float, designacion: str) -> int:
    """Barras de un diámetro necesarias para cubrir As_req [cm²].

    No aplica mínimos constructivos (p. ej. 2 barras corridas en vigas):
    esos los decide el diseño y se verifican aparte.
    """
    return max(math.ceil(As_req / barra(designacion).area - 1e-9), 0)


def peso_acero(designacion: str, longitud: float) -> float:
    """Peso [kg] de una longitud [m] de barra."""
    return barra(designacion).peso * longitud
