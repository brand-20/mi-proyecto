"""Diseño de vigas de concreto armado según la Norma E.060 (2009) del RNE.

Unidades: kgf y cm. f'c y fy en kgf/cm², momentos en kgf·cm, cortantes en kgf.
Estas funciones usan los φ de la E.060; no combinarlas con las combinaciones
de carga del ACI 318 (1.2D + 1.6L), que van con otros φ.
"""
from __future__ import annotations

import math

from .unidades import TONF_M_A_KGF_CM
from .verificacion import Verificacion

NORMA = "E.060-2009"

ES = 2.0e6  # kgf/cm², módulo de elasticidad del acero
EPS_CU = 0.003  # deformación unitaria última del concreto

# Factores de reducción de resistencia (Art. 9.3.2)
PHI = {
    "flexion": 0.90,
    "traccion": 0.90,
    "compresion_estribos": 0.70,
    "compresion_espiral": 0.75,
    "corte": 0.85,
    "torsion": 0.85,
    "aplastamiento": 0.70,
}


def beta1(f_c: float) -> float:
    """Factor β1 del bloque equivalente de compresiones (Art. 10.2.7.3)."""
    if f_c <= 280:
        return 0.85
    return max(0.85 - 0.05 * (f_c - 280) / 70, 0.65)


def cuantia_balanceada(f_c: float, fy: float) -> float:
    """ρb para sección rectangular con acero en tracción."""
    return 0.85 * beta1(f_c) * f_c / fy * (EPS_CU * ES) / (EPS_CU * ES + fy)


def cuantia_maxima(f_c: float, fy: float) -> float:
    """ρmax = 0.75 ρb (Art. 10.3.4)."""
    return 0.75 * cuantia_balanceada(f_c, fy)


def As_min_flexion(f_c: float, fy: float, b_w: float, d: float) -> float:
    """Acero mínimo en secciones rectangulares [cm²] (Art. 10.5.2)."""
    return 0.7 * math.sqrt(f_c) / fy * b_w * d


def As_flexion(M_u: float, f_c: float, fy: float, b: float, d: float) -> float:
    """Acero en tracción requerido [cm²] para M_u [kgf·cm], sección simplemente armada.

    Resuelve M_u = φ·As·fy·(d − a/2) con a = As·fy / (0.85·f'c·b).
    El signo de M_u solo indica la cara en tracción: se usa su valor absoluto.
    """
    M_u = abs(M_u)
    phi = PHI["flexion"]
    R_u = M_u / (phi * b * d**2)
    discriminante = 1 - 2 * R_u / (0.85 * f_c)
    if discriminante < 0:
        raise ValueError(
            f"Sección insuficiente: M_u = {M_u / TONF_M_A_KGF_CM:.2f} tonf·m excede "
            f"la capacidad de {b:.0f}x{d:.0f} cm simplemente armada. "
            "Aumentar peralte o diseñar con acero en compresión."
        )
    rho = 0.85 * f_c / fy * (1 - math.sqrt(discriminante))
    return rho * b * d


def phi_Mn(As: float, f_c: float, fy: float, b: float, d: float) -> float:
    """Momento resistente de diseño φMn [kgf·cm], asumiendo que el acero fluye."""
    a = As * fy / (0.85 * f_c * b)
    return PHI["flexion"] * As * fy * (d - a / 2)


def Vc(f_c: float, b_w: float, d: float) -> float:
    """Resistencia nominal al corte del concreto [kgf] (Art. 11.3.1.1)."""
    return 0.53 * math.sqrt(f_c) * b_w * d


def Vs_max(f_c: float, b_w: float, d: float) -> float:
    """Límite de Vs para la sección [kgf] (Art. 11.5.7.9)."""
    return 2.1 * math.sqrt(f_c) * b_w * d


def espaciamiento_estribos(V_u: float, f_c: float, fy: float, b_w: float, d: float, Av: float) -> float:
    """Espaciamiento por resistencia [cm] de estribos de área Av [cm²] (todas las ramas).

    No incluye los máximos por confinamiento ni los de diseño sísmico (Cap. 21);
    esos se verifican aparte.
    """
    phi = PHI["corte"]
    Vs = V_u / phi - Vc(f_c, b_w, d)
    if Vs <= 0:
        return math.inf
    if Vs > Vs_max(f_c, b_w, d):
        raise ValueError("Vs supera 2.1·√f'c·bw·d: aumentar la sección (Art. 11.5.7.9).")
    return Av * fy * d / Vs


def verificar_flexion(
    M_u: float, As: float, f_c: float, fy: float, b: float, d: float
) -> list[Verificacion]:
    """Verificaciones de una viga a flexión con el acero colocado As [cm²]."""
    M_u = abs(M_u)
    rho = As / (b * d)
    return [
        Verificacion(
            "Resistencia a flexión Mu <= φMn",
            M_u / TONF_M_A_KGF_CM,
            phi_Mn(As, f_c, fy, b, d) / TONF_M_A_KGF_CM,
            "tonf·m",
            "E.060 Art. 9.3.2 / 10.2",
        ),
        Verificacion(
            "Acero mínimo As_min <= As",
            As_min_flexion(f_c, fy, b, d),
            As,
            "cm²",
            "E.060 Art. 10.5.2",
        ),
        Verificacion(
            "Cuantía máxima ρ <= 0.75ρb",
            rho,
            cuantia_maxima(f_c, fy),
            "",
            "E.060 Art. 10.3.4",
            decimales=4,
        ),
    ]


if __name__ == "__main__":
    from .acero import area_acero

    # Viga V-101 (25x50), f'c = 210, fy = 4200
    f_c, fy = 210.0, 4200.0  # kgf/cm²
    b, h = 25.0, 50.0  # cm
    d = h - 6.0  # cm, recubrimiento 4 + estribo 3/8" + db/2
    M_u = 12.0 * TONF_M_A_KGF_CM  # kgf·cm

    print(f"As requerido = {As_flexion(M_u, f_c, fy, b, d):.2f} cm²")
    for v in verificar_flexion(M_u, area_acero({'5/8"': 4}), f_c, fy, b, d):
        print(v)
