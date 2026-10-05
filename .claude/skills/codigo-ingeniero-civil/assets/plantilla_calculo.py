"""Diseño por flexión y corte de la viga V-101 — Edificio Multifamiliar.

Norma:    E.060-2009 (RNE). Combinación U = 1.4 CM + 1.7 CV (Art. 9.2)
Unidades: datos de cargas en tonf y m; diseño en kgf y cm
Autor:    ...
Fecha:    ...
Revisión: 0

Requiere el paquete `civil`: junto a este archivo, en el PYTHONPATH, o en
scripts/civil de la skill (se encuentra solo al ejecutar desde la skill).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

# Ejecutada desde la skill, la librería está en ../scripts: así no hace falta PYTHONPATH.
_LIBRERIA_SKILL = Path(__file__).resolve().parent.parent / "scripts"
if (_LIBRERIA_SKILL / "civil").is_dir():
    sys.path.insert(0, str(_LIBRERIA_SKILL))

from civil.acero import area_acero, barra, numero_barras  # noqa: E402
from civil.concreto_e060 import NORMA, PHI, As_flexion, Vc, espaciamiento_estribos, verificar_flexion  # noqa: E402
from civil.unidades import TONF_A_KGF, TONF_M_A_KGF_CM  # noqa: E402
from civil.verificacion import Verificacion  # noqa: E402

# --- Constantes normativas -------------------------------------------------
FACTOR_CM = 1.4  # E.060 Art. 9.2.1
FACTOR_CV = 1.7  # E.060 Art. 9.2.1
ESPACIAMIENTO_LIBRE_MIN = 2.5  # cm, y no menor que db (E.060 Art. 7.6.1)
S_MAX_ESTRIBOS = 60.0  # cm, y no mayor que d/2 (E.060 Art. 11.5.5)

CANDIDATOS_LONG = ('5/8"', '3/4"', '1"')  # se prueba en este orden


# --- Datos de entrada ------------------------------------------------------
@dataclass(frozen=True)
class DatosViga:
    nombre: str
    f_c: float  # kgf/cm²
    fy: float  # kgf/cm²
    b: float  # cm
    h: float  # cm
    recubrimiento: float  # cm, al estribo
    luz: float  # m, luz libre
    w_CM: float  # tonf/m, carga muerta en servicio
    w_CV: float  # tonf/m, carga viva en servicio
    barra_estribo: str

    def d(self, barra_long: str) -> float:
        """Peralte efectivo [cm] con una capa de barras barra_long."""
        return self.h - self.recubrimiento - barra(self.barra_estribo).diametro - barra(barra_long).diametro / 2

    def espaciamiento_libre(self, barra_long: str, n: int) -> float:
        """Distancia libre entre n barras de una capa [cm]."""
        ancho_util = self.b - 2 * (self.recubrimiento + barra(self.barra_estribo).diametro)
        return (ancho_util - n * barra(barra_long).diametro) / (n - 1)


V101 = DatosViga(
    nombre="V-101 (eje B, tramo 1-2)",
    f_c=210.0,
    fy=4200.0,
    b=25.0,
    h=50.0,
    recubrimiento=4.0,
    luz=5.20,
    w_CM=1.80,
    w_CV=0.70,
    barra_estribo='3/8"',
)


# --- Cálculo ---------------------------------------------------------------
def carga_ultima(v: DatosViga) -> float:
    """w_u [tonf/m]."""
    return FACTOR_CM * v.w_CM + FACTOR_CV * v.w_CV


def momento_ultimo(v: DatosViga) -> float:
    """M_u al centro de la luz [kgf·cm], viga simplemente apoyada."""
    return carga_ultima(v) * v.luz**2 / 8 * TONF_M_A_KGF_CM


def cortante_ultimo(v: DatosViga, d: float) -> float:
    """V_u a una distancia d de la cara del apoyo [kgf]."""
    return carga_ultima(v) * (v.luz / 2 - d / 100) * TONF_A_KGF


def elegir_armado(v: DatosViga, M_u: float) -> tuple[str, int, float]:
    """Primer diámetro de CANDIDATOS_LONG que cubre As_req en una sola capa.

    Devuelve (designación, n° de barras, As_req con el d de esa barra).
    """
    for designacion in CANDIDATOS_LONG:
        As_req = As_flexion(M_u, v.f_c, v.fy, v.b, v.d(designacion))
        n = max(numero_barras(As_req, designacion), 2)  # mínimo constructivo: 2 barras corridas
        libre_min = max(barra(designacion).diametro, ESPACIAMIENTO_LIBRE_MIN)
        if v.espaciamiento_libre(designacion, n) >= libre_min:
            return designacion, n, As_req
    raise ValueError(
        f"{v.nombre}: el acero no entra en una capa con {CANDIDATOS_LONG}. "
        "Diseñar en dos capas o aumentar el ancho b."
    )


def diseno(v: DatosViga) -> tuple[dict, list[Verificacion]]:
    M_u = momento_ultimo(v)
    designacion, n, As_req = elegir_armado(v, M_u)
    d = v.d(designacion)
    As = area_acero({designacion: n})

    V_u = cortante_ultimo(v, d)
    Av = 2 * barra(v.barra_estribo).area  # estribo de 2 ramas
    s_req = espaciamiento_estribos(V_u, v.f_c, v.fy, v.b, d, Av)
    s = min(s_req, d / 2, S_MAX_ESTRIBOS)
    resultados = {
        "w_u": carga_ultima(v), "M_u": M_u, "V_u": V_u, "d": d,
        "barra": designacion, "n_barras": n, "As_req": As_req, "As": As, "s_req": s_req, "s": s,
    }

    verificaciones = verificar_flexion(M_u, As, v.f_c, v.fy, v.b, d)
    verificaciones += [
        Verificacion(
            "Espaciamiento libre entre barras",
            max(barra(designacion).diametro, ESPACIAMIENTO_LIBRE_MIN),
            v.espaciamiento_libre(designacion, n),
            "cm",
            "E.060 Art. 7.6.1",
        ),
        Verificacion(
            f"Corte V_u <= φ(Vc + Vs), estribos @ {s:.1f} cm",
            V_u,
            PHI["corte"] * (Vc(v.f_c, v.b, d) + Av * v.fy * d / s),
            "kgf",
            "E.060 Art. 11.1 / 11.5",
        ),
    ]
    return resultados, verificaciones


# --- Reporte ---------------------------------------------------------------
def memoria(v: DatosViga) -> str:
    r, verificaciones = diseno(v)
    lineas = [
        f"MEMORIA DE CÁLCULO — {v.nombre}   ({NORMA})",
        "",
        "Datos",
        f"  f'c = {v.f_c:.0f} kgf/cm²   fy = {v.fy:.0f} kgf/cm²",
        f"  b x h = {v.b:.0f} x {v.h:.0f} cm   d = {r['d']:.2f} cm   L = {v.luz:.2f} m",
        f"  w_CM = {v.w_CM:.2f} tonf/m   w_CV = {v.w_CV:.2f} tonf/m",
        "",
        "Solicitaciones",
        f"  w_u = 1.4·{v.w_CM:.2f} + 1.7·{v.w_CV:.2f} = {r['w_u']:.2f} tonf/m",
        f"  M_u = w_u·L²/8 = {r['M_u'] / TONF_M_A_KGF_CM:.2f} tonf·m",
        f"  V_u (a d de la cara) = {r['V_u'] / TONF_A_KGF:.2f} tonf",
        "",
        "Diseño",
        f"  As requerido = {r['As_req']:.2f} cm²  ->  {r['n_barras']} ø {r['barra']} (As = {r['As']:.2f} cm²)",
        f"  Estribos ø {v.barra_estribo}: s por resistencia = {r['s_req']:.1f} cm; "
        f"s = mín(s_req, d/2, {S_MAX_ESTRIBOS:.0f}) = {r['s']:.1f} cm",
        "  (No incluye requisitos sísmicos del Cap. 21: confinamiento y corte por capacidad.)",
        "",
        "Verificaciones",
        *(f"  {ver}" for ver in verificaciones),
    ]
    return "\n".join(lineas)


if __name__ == "__main__":
    print(memoria(V101))
