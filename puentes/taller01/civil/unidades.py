"""Conversión de unidades y redondeo comercial.

Sistemas de trabajo de la librería:
    - Diseño en concreto (E.060): kgf y cm   -> f'c en kgf/cm², M en kgf·cm
    - Análisis y cargas:          tonf y m   -> M en tonf·m
    - Metrados:                   m, m², m³, kg, und
    - Costos:                     soles (S/), sin IGV salvo que se indique

Regla: convertir en la frontera (al leer datos o al reportar), nunca a mitad
de una fórmula.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

G = 9.80665  # m/s², gravedad estándar

# Fuerza
TONF_A_KGF = 1000.0
KGF_A_N = G
KN_A_KGF = 1000.0 / G

# Longitud
M_A_CM = 100.0

# Momento: 1 tonf·m = 1e5 kgf·cm
TONF_M_A_KGF_CM = TONF_A_KGF * M_A_CM

# Esfuerzo: 1 MPa = 10.197 kgf/cm²
MPA_A_KGF_CM2 = 1.0e6 / (G * 1.0e4)
KGF_CM2_A_MPA = 1.0 / MPA_A_KGF_CM2


def redondear(valor: float, decimales: int = 2) -> float:
    """Redondea "mitad hacia arriba", igual que Excel y S10.

    round() de Python usa redondeo bancario y opera sobre la representación
    binaria: round(0.125, 2) -> 0.12 y round(2.675, 2) -> 2.67. En un
    presupuesto eso descuadra céntimos frente a Excel/S10.
    """
    paso = Decimal(1).scaleb(-decimales)
    return float(Decimal(str(valor)).quantize(paso, rounding=ROUND_HALF_UP))
