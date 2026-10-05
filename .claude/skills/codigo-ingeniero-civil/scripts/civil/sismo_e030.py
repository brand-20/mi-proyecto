"""Análisis sísmico estático según la Norma E.030 (2018) del RNE.

Unidades: tonf, m, s. Las tablas copian la norma; si se usa otra edición,
actualizar NORMA y las tablas juntos.
"""
from __future__ import annotations

from .verificacion import Verificacion

NORMA = "E.030-2018"

# Tabla N° 1: factor de zona
Z = {1: 0.10, 2: 0.25, 3: 0.35, 4: 0.45}

# Tabla N° 3: factor de suelo S[zona][perfil]
S = {
    4: {"S0": 0.80, "S1": 1.00, "S2": 1.05, "S3": 1.10},
    3: {"S0": 0.80, "S1": 1.00, "S2": 1.15, "S3": 1.20},
    2: {"S0": 0.80, "S1": 1.00, "S2": 1.20, "S3": 1.40},
    1: {"S0": 0.80, "S1": 1.00, "S2": 1.60, "S3": 2.00},
}

# Tabla N° 4: períodos (Tp, TL) en s
PERIODOS = {"S0": (0.3, 3.0), "S1": (0.4, 2.5), "S2": (0.6, 2.0), "S3": (1.0, 1.6)}

# Tabla N° 5: factor de uso. A1 no se incluye: depende del aislamiento sísmico.
U = {"A2": 1.5, "B": 1.3, "C": 1.0}

# Tabla N° 7: coeficiente básico de reducción R0 (concreto armado y albañilería)
R0 = {
    "porticos": 8,
    "dual": 7,
    "muros_estructurales": 6,
    "muros_ductilidad_limitada": 4,
    "albanileria": 3,
}

# Art. 28.4.1: coeficiente CT para el período fundamental
CT = {
    "porticos": 35,
    "porticos_con_muros_en_cajas": 45,
    "dual_muros_albanileria": 60,
}

# Tabla N° 11: deriva máxima de entrepiso Δi/hei
DERIVA_MAX = {
    "concreto_armado": 0.007,
    "acero": 0.010,
    "albanileria": 0.005,
    "madera": 0.010,
    "muros_ductilidad_limitada": 0.005,
}

C_SOBRE_R_MIN = 0.11


def _valor(tabla: dict, clave, nombre: str):
    """Lee una tabla de la norma con un error legible si la clave no existe."""
    try:
        return tabla[clave]
    except KeyError:
        raise ValueError(f"{nombre} '{clave}' no válido. Opciones: {list(tabla)}") from None


def factor_C(T: float, suelo: str) -> float:
    """Factor de amplificación sísmica C para el período T [s]."""
    Tp, TL = _valor(PERIODOS, suelo, "Perfil de suelo")
    if T < Tp:
        return 2.5
    if T < TL:
        return 2.5 * Tp / T
    return 2.5 * Tp * TL / T**2


def periodo_fundamental(h_n: float, C_T: float) -> float:
    """T = hn / CT, con hn = altura total del edificio [m]."""
    return h_n / C_T


def exponente_k(T: float) -> float:
    """Exponente k de distribución en altura."""
    return 1.0 if T <= 0.5 else min(0.75 + 0.5 * T, 2.0)


def coeficiente_sismico(zona: int, suelo: str, categoria: str, R: float, T: float) -> float:
    """ZUCS/R para el análisis estático, con C/R >= 0.11."""
    C = max(factor_C(T, suelo), C_SOBRE_R_MIN * R)
    z = _valor(Z, zona, "Zona sísmica")
    u = _valor(U, categoria, "Categoría (A1 requiere tratamiento aparte)")
    return z * u * C * S[zona][suelo] / R


def cortante_basal(P: float, zona: int, suelo: str, categoria: str, R: float, T: float) -> float:
    """V = ZUCS/R · P [tonf], con P = peso sísmico [tonf]."""
    return coeficiente_sismico(zona, suelo, categoria, R, T) * P


def distribucion_fuerzas(V: float, pesos: list[float], alturas: list[float], T: float) -> list[float]:
    """Fuerzas por nivel Fi = αi·V, de abajo hacia arriba [tonf].

    αi = Pi·hi^k / Σ Pj·hj^k, con hi medida desde el nivel del terreno [m].
    """
    if len(pesos) != len(alturas):
        raise ValueError("pesos y alturas deben tener un valor por nivel")
    k = exponente_k(T)
    productos = [P_i * h_i**k for P_i, h_i in zip(pesos, alturas, strict=True)]
    total = sum(productos)
    return [V * p / total for p in productos]


def verificar_deriva(
    desplazamiento_elastico: float,
    h_entrepiso: float,
    R: float,
    material: str,
    regular: bool,
) -> Verificacion:
    """Deriva inelástica = 0.75R (regular) u 0.85R (irregular) × deriva elástica.

    desplazamiento_elastico es el desplazamiento relativo de entrepiso [m]
    del análisis lineal con fuerzas reducidas.
    """
    factor = 0.75 if regular else 0.85
    deriva = factor * R * desplazamiento_elastico / h_entrepiso
    limite = _valor(DERIVA_MAX, material, "Material")
    return Verificacion("Deriva de entrepiso Δ/h", deriva, limite, "", "E.030 Art. 31-32", decimales=4)
