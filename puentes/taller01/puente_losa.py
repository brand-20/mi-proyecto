"""Taller 01 — Puente losa de concreto armado (L = 20 ft) y Teorema de Barré.

Norma:    AASHTO LRFD Bridge Design Specifications (base del Manual de Puentes
          MTC-2018). Clasificación de la vía: DG-2018 (MTC).
Unidades: tonf y m para cargas y momentos; kgf y cm para el diseño en concreto.
          Las fórmulas que AASHTO escribe en mm o MPa (t_min, E, fisuración)
          se evalúan en esas unidades y se convierten en la frontera.
Configuración del taller: A–L (f'c = 420 kgf/cm², asfalto 3",
          ejes HL-93 d1-2 = 3.00 m y d2-3 = 3.50 m).

Uso:
    python puente_losa.py    -> imprime la memoria y genera taller01_puentes.tex
"""
from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from civil.acero import barra  # noqa: E402
from civil.unidades import KGF_CM2_A_MPA, MPA_A_KGF_CM2, TONF_M_A_KGF_CM, redondear  # noqa: E402
from civil.verificacion import Verificacion  # noqa: E402

# --- Constantes normativas -------------------------------------------------
PIE = 0.3048  # m
PULGADA = 0.0254  # m
KSI_A_MPA = 6.894757

GAMMA_CONCRETO = 2.40  # tonf/m³, concreto armado (AASHTO Tabla 3.5.1-1)
GAMMA_ASFALTO = 2.25  # tonf/m³, superficie bituminosa (AASHTO Tabla 3.5.1-1)
ES = 200_000 * MPA_A_KGF_CM2  # kgf/cm² (AASHTO 5.4.3.2)

# Carga viva HL-93 (AASHTO 3.6.1.2), en tonf: 8 kip, 32 kip, 25 kip, 0.64 klf
P_DELANTERO = 3.63
P_TRASERO = 14.52
P_TANDEM = 11.34
S_TANDEM = 1.20  # m
W_CARRIL = 0.952  # tonf/m, repartida en 3.00 m de ancho (AASHTO 3.6.1.2.4)
ANCHO_CARGA_CARRIL = 3.00  # m
S_FATIGA = 9.00  # m, separación constante de ejes traseros (AASHTO 3.6.1.4.1)
ANCHO_CARRIL_DISENO = 3.60  # m (AASHTO 3.6.1.1.1)

IM = 0.33  # AASHTO Tabla 3.6.2.1-1, demás estados límite
IM_FATIGA = 0.15  # AASHTO Tabla 3.6.2.1-1
M_UN_CARRIL = 1.20  # factor de presencia múltiple, 1 carril (AASHTO Tabla 3.6.1.1.2-1)
M_MULTIPLES = 1.00  # 2 carriles cargados, criterio de clase (M_LL = m·M/E)

# Factores de carga (AASHTO Tablas 3.4.1-1 y 3.4.1-2)
GAMMA_DC = 1.25
GAMMA_DW = 1.50
GAMMA_LL = 1.75
# VERIFICAR edición: 1.50 en AASHTO 2014 (base del MTC-2018); 1.75 en AASHTO 9.ª ed. (2020)
GAMMA_FATIGA = 1.50
GAMMA_FATIGA_9ED = 1.75

PHI_FLEXION = 0.90  # sección controlada por tracción (AASHTO 5.5.4.2)
C_D_MAX = 0.42  # c/d máximo, criterio de clase (AASHTO 2014+ pide 0.375 para φ = 0.90)
RHO_MIN_COEF = 0.03  # ρmin >= 0.03 f'c/fy, criterio de clase
GAMMA_1_FISURACION = 1.6  # variabilidad de fr (AASHTO 5.6.3.3)
GAMMA_3_ACERO = 0.67  # A615 Gr 60 (AASHTO 5.6.3.3)
FSS_MAX = 0.60  # fss <= 0.6 fy (AASHTO 5.6.7)

ESPACIAMIENTO_MAX_PRINCIPAL = 45.0  # cm, y <= 1.5 h (AASHTO 5.10.3.2)
ESPACIAMIENTO_MAX_TEMPERATURA = 45.0  # cm, y <= 3 h (AASHTO 5.10.6)
PASO_ESPACIAMIENTO = 2.5  # cm, se redondea hacia abajo a este múltiplo

TOL = 1e-9


# --- Cargas móviles: líneas de influencia y Teorema de Barré ---------------
@dataclass(frozen=True)
class Eje:
    P: float  # tonf
    x: float  # m, medido desde el primer eje del vehículo


def vehiculo(cargas: tuple[float, ...], separaciones: tuple[float, ...]) -> tuple[Eje, ...]:
    """Ejes de un vehículo a partir de sus cargas [tonf] y separaciones [m]."""
    if len(separaciones) != len(cargas) - 1:
        raise ValueError("Debe haber una separación menos que cargas.")
    posiciones = [0.0]
    for s in separaciones:
        posiciones.append(posiciones[-1] + s)
    return tuple(Eje(P, x) for P, x in zip(cargas, posiciones))


def invertir(ejes: tuple[Eje, ...]) -> tuple[Eje, ...]:
    """El mismo vehículo circulando en sentido contrario."""
    largo = ejes[-1].x
    return tuple(Eje(e.P, largo - e.x) for e in reversed(ejes))


def _en_luz(x: float, L: float) -> bool:
    return -TOL <= x <= L + TOL


def ejes_en_luz(ejes: tuple[Eje, ...], a: float, L: float) -> tuple[int, ...]:
    """Índices de los ejes sobre la luz con el primer eje en x = a [m] del apoyo A."""
    return tuple(i for i, e in enumerate(ejes) if _en_luz(a + e.x, L))


def reaccion_A(ejes: tuple[Eje, ...], a: float, L: float) -> float:
    """Reacción en el apoyo A [tonf], viga simplemente apoyada de luz L [m]."""
    return sum(ejes[i].P * (L - (a + ejes[i].x)) / L for i in ejes_en_luz(ejes, a, L))


def momento_bajo_eje(ejes: tuple[Eje, ...], a: float, L: float, k: int) -> float:
    """Momento [tonf·m] en la sección donde está el eje k."""
    xk = a + ejes[k].x
    if not _en_luz(xk, L):
        return 0.0
    en_luz = ejes_en_luz(ejes, a, L)
    izquierda = sum(ejes[i].P * (xk - (a + ejes[i].x)) for i in en_luz if a + ejes[i].x < xk)
    return reaccion_A(ejes, a, L) * xk - izquierda


@dataclass(frozen=True)
class CasoBarre:
    """Posición de Barré de un grupo de ejes contiguos para un eje crítico."""

    grupo: tuple[int, ...]  # índices de los ejes del grupo
    critico: int  # índice del eje crítico
    R: float  # tonf, resultante del grupo
    e: float  # m, distancia del eje crítico a la resultante (con signo)
    x_critico: float  # m, desde el apoyo A: L/2 + e/2
    a: float  # m, posición del primer eje del vehículo
    valido: bool  # en esa posición están en la luz exactamente los ejes del grupo
    M: float  # tonf·m, momento bajo el eje crítico (con los ejes realmente en la luz)


def casos_barre(ejes: tuple[Eje, ...], L: float) -> list[CasoBarre]:
    """Teorema de Barré para cada grupo contiguo que cabe en la luz.

    El momento máximo bajo una carga se da cuando el centro de la luz divide en
    partes iguales la distancia entre esa carga y la resultante del grupo:
    x_crit = L/2 + e/2. Solo vale si en esa posición no entra ni sale otro eje.
    """
    casos = []
    n = len(ejes)
    for i in range(n):
        for j in range(i, n):
            if ejes[j].x - ejes[i].x > L + TOL:
                break
            grupo = tuple(range(i, j + 1))
            R = sum(ejes[g].P for g in grupo)
            x_R = sum(ejes[g].P * ejes[g].x for g in grupo) / R
            for k in grupo:
                e = ejes[k].x - x_R
                x_critico = L / 2 + e / 2
                a = x_critico - ejes[k].x
                valido = ejes_en_luz(ejes, a, L) == grupo
                casos.append(CasoBarre(grupo, k, R, e, x_critico, a, valido, momento_bajo_eje(ejes, a, L, k)))
    return casos


@dataclass(frozen=True)
class MomentoMaximo:
    M: float  # tonf·m
    a: float  # m, posición del primer eje
    critico: int  # eje bajo el cual ocurre
    x_critico: float  # m, desde el apoyo A
    en_luz: tuple[int, ...]


def momento_maximo(ejes: tuple[Eje, ...], L: float) -> MomentoMaximo:
    """Momento máximo absoluto [tonf·m] por el paso del vehículo.

    Bajo cada eje, M(a) es una parábola por tramos: su máximo está en la
    posición de Barré del grupo que está en la luz o en un punto donde un eje
    entra o sale (eje sobre un apoyo). Se evalúan todos esos candidatos.
    """
    candidatos = {c.a for c in casos_barre(ejes, L)}
    for e in ejes:
        candidatos |= {-e.x, L - e.x}
    mejor = None
    for a in candidatos:
        for k in range(len(ejes)):
            M = momento_bajo_eje(ejes, a, L, k)
            if mejor is None or M > mejor.M + TOL:
                mejor = MomentoMaximo(M, a, k, a + ejes[k].x, ejes_en_luz(ejes, a, L))
    return mejor


def momento_maximo_barrido(ejes: tuple[Eje, ...], L: float, paso: float = 0.001) -> float:
    """Control por fuerza bruta de momento_maximo() [tonf·m]."""
    a, M = -ejes[-1].x, 0.0
    while a <= L:
        M = max(M, *(momento_bajo_eje(ejes, a, L, k) for k in range(len(ejes))))
        a += paso
    return M


@dataclass(frozen=True)
class PosicionReaccion:
    """Un eje sobre el apoyo A; la numeración de ejes es la del vehículo original."""

    R: float  # tonf
    sentido: str  # "directo" o "inverso"
    eje_en_apoyo: int  # índice original
    en_luz: tuple[int, ...]  # índices originales
    cargas: tuple[tuple[int, float, float], ...]  # (índice original, P [tonf], x desde A [m])


def posiciones_reaccion(ejes: tuple[Eje, ...], L: float) -> list[PosicionReaccion]:
    """R_A es lineal por tramos: su máximo ocurre con un eje sobre el apoyo.

    Se prueba cada eje sobre el apoyo A, con el vehículo en ambos sentidos.
    """
    n = len(ejes)
    posiciones = []
    for sentido, v in (("directo", ejes), ("inverso", invertir(ejes))):
        original = (lambda i: i) if sentido == "directo" else (lambda i: n - 1 - i)
        for k, e in enumerate(v):
            a = -e.x
            en_luz = ejes_en_luz(v, a, L)
            cargas = tuple((original(i), v[i].P, a + v[i].x) for i in en_luz)
            posiciones.append(
                PosicionReaccion(reaccion_A(v, a, L), sentido, original(k), tuple(original(i) for i in en_luz), cargas)
            )
    return posiciones


def reaccion_maxima(ejes: tuple[Eje, ...], L: float) -> PosicionReaccion:
    """Reacción máxima [tonf] por el paso del vehículo."""
    return max(posiciones_reaccion(ejes, L), key=lambda pr: pr.R)


# --- Clasificación de la vía y predimensionamiento -------------------------
def clasificar_via(imda: float) -> str:
    """Clasificación por demanda (DG-2018, Art. 101.01), IMDA en veh/día."""
    if imda > 6000:
        return "Autopista de Primera Clase"
    if imda > 4000:
        return "Autopista de Segunda Clase"
    if imda > 2000:
        return "Carretera de Primera Clase"
    if imda >= 400:
        return "Carretera de Segunda Clase"
    return "Carretera de Tercera Clase"


def t_min_losa(L: float) -> float:
    """Espesor mínimo [m] de losa simplemente apoyada con refuerzo principal
    paralelo al tráfico: 1.2 (S + 3000)/30, S en mm (AASHTO Tabla 2.5.2.6.3-1)."""
    S = L * 1000
    return 1.2 * (S + 3000) / 30 / 1000


def numero_carriles(ancho_libre: float) -> int:
    """Carriles de diseño: parte entera de w/3.6 (AASHTO 3.6.1.1.1), w en m."""
    return int(ancho_libre / ANCHO_CARRIL_DISENO + TOL)


def E_un_carril(L: float, W: float) -> float:
    """Ancho de franja [m], un carril: 0.25 + 0.42 √(L1·W1), L1 = min(L, 18.26), W1 = min(W, 9.14)
    (AASHTO 4.6.2.3-1 en m, como en clase)."""
    return 0.25 + 0.42 * math.sqrt(min(L, 18.26) * min(W, 9.14))


def E_multiples_carriles(L: float, W: float, NL: int) -> float:
    """Ancho de franja [m], 2+ carriles: 2.10 + 0.12 √(L1·W1) <= W/NL, L1 = min(L, 18.26),
    W1 = min(W, 18) (AASHTO 4.6.2.3-2 en m, como en clase)."""
    return min(2.10 + 0.12 * math.sqrt(min(L, 18.26) * min(W, 18.0)), W / NL)


def E_borde(dist_cara_barrera: float, E: float) -> float:
    """Franja de borde [m]: d + 0.30 + E/4 <= E/2 y <= 1.80 m (AASHTO 4.6.2.1.4b)."""
    return min(dist_cara_barrera + 0.30 + E / 4, E / 2, 1.80)


# --- Concreto armado (AASHTO, en kgf y cm) ---------------------------------
def beta_1(f_c: float) -> float:
    """β1 (AASHTO 5.6.2.2): 0.85 - 0.05 (f'c - 28)/7 con f'c en MPa, 0.65 <= β1 <= 0.85."""
    f_MPa = f_c * KGF_CM2_A_MPA
    return min(0.85, max(0.65, 0.85 - 0.05 * (f_MPa - 28) / 7))


def Ec(f_c: float) -> float:
    """Módulo de elasticidad [kgf/cm²]: 0.043 wc^1.5 √f'c MPa con wc = 2320 kg/m³
    (AASHTO 5.4.2.4), que en kgf/cm² es 15 344 √f'c."""
    return 0.043 * 2320**1.5 * math.sqrt(f_c * KGF_CM2_A_MPA) * MPA_A_KGF_CM2


def fr(f_c: float) -> float:
    """Módulo de rotura [kgf/cm²]: 0.63 √f'c MPa (AASHTO 5.4.2.6)."""
    return 0.63 * math.sqrt(f_c * KGF_CM2_A_MPA) * MPA_A_KGF_CM2


def As_flexion(M_u: float, f_c: float, fy: float, b: float, d: float) -> float:
    """Acero de tracción [cm²] de una sección rectangular, M_u en kgf·cm.

    M_u = φ As fy (d - a/2), a = As fy / (0.85 f'c b)   (AASHTO 5.6.3.2)
    """
    k = 2 * M_u / (PHI_FLEXION * 0.85 * f_c * b * d**2)
    if k >= 1:
        raise ValueError(f"Sección insuficiente para M_u = {M_u / TONF_M_A_KGF_CM:.2f} tonf·m. Aumentar el peralte.")
    return 0.85 * f_c * b * d / fy * (1 - math.sqrt(1 - k))


def bloque_a(As: float, f_c: float, fy: float, b: float) -> float:
    """Profundidad del bloque de compresiones a [cm]."""
    return As * fy / (0.85 * f_c * b)


def phi_Mn(As: float, f_c: float, fy: float, b: float, d: float) -> float:
    """Resistencia de diseño a flexión [kgf·cm] (AASHTO 5.6.3.2)."""
    return PHI_FLEXION * As * fy * (d - bloque_a(As, f_c, fy, b) / 2)


def Mcr(f_c: float, b: float, h: float) -> float:
    """Momento de fisuración [kgf·cm]: γ3 γ1 fr Sc (AASHTO 5.6.3.3)."""
    return GAMMA_3_ACERO * GAMMA_1_FISURACION * fr(f_c) * b * h**2 / 6


@dataclass(frozen=True)
class SeccionFisurada:
    y: float  # cm, eje neutro desde la fibra comprimida
    jd: float  # cm, brazo de palanca d - y/3


def seccion_fisurada(As: float, b: float, d: float, n: float) -> SeccionFisurada:
    """Sección transformada fisurada: b y²/2 = n As (d - y)."""
    nAs = n * As
    y = (-nAs + math.sqrt(nAs**2 + 2 * b * nAs * d)) / b
    return SeccionFisurada(y, d - y / 3)


def s_max_fisuracion(fss: float, gamma_e: float, dc: float, h: float) -> float:
    """Espaciamiento máximo [cm] por control de fisuración (AASHTO 5.6.7).

    s <= 123 000 γe / (βs fss) - 2 dc, con fss en MPa y s, dc en mm;
    βs = 1 + dc / (0.7 (h - dc)). Entradas: fss en kgf/cm², dc y h en cm.
    """
    beta_s = 1 + dc / (0.7 * (h - dc))
    s_mm = 123_000 * gamma_e / (beta_s * fss * KGF_CM2_A_MPA) - 2 * dc * 10
    return s_mm / 10


def beta_s(dc: float, h: float) -> float:
    return 1 + dc / (0.7 * (h - dc))


def umbral_fatiga(f_min: float) -> float:
    """Umbral de fatiga [kgf/cm²]: 24 - 0.33 fmin ksi (AASHTO 2014, 5.5.3.2)."""
    f_min_ksi = f_min * KGF_CM2_A_MPA / KSI_A_MPA
    return (24 - 0.33 * f_min_ksi) * KSI_A_MPA * MPA_A_KGF_CM2


def umbral_fatiga_9ed(f_min: float, fy: float) -> float:
    """Umbral de fatiga [kgf/cm²]: 26 - 22 fmin/fy ksi (AASHTO 9.ª ed., 5.5.3.2)."""
    return (26 - 22 * f_min / fy) * KSI_A_MPA * MPA_A_KGF_CM2


def porcentaje_distribucion(L: float) -> float:
    """Acero de distribución [%] del principal: 1750/√S <= 50, S en mm (AASHTO 9.7.3.2)."""
    return min(1750 / math.sqrt(L * 1000), 50.0)


def As_temperatura(h: float, fy: float) -> float:
    """Acero por temperatura [cm²/m]: Ast = 0.75 b h / fy, b = 1000 mm, h en mm, fy en MPa
    (fórmula de clase). Entradas: h en m, fy en kgf/cm²."""
    return 0.75 * 1000 * (h * 1000) / (fy * KGF_CM2_A_MPA) / 100  # mm²/m -> cm²/m


def espaciamiento(As_req: float, designacion: str, s_max: float) -> float:
    """Espaciamiento [cm] de barras para cubrir As_req [cm²/m], redondeado hacia abajo."""
    s = barra(designacion).area / As_req * 100
    s = math.floor(s / PASO_ESPACIAMIENTO + TOL) * PASO_ESPACIAMIENTO
    if s < 10:
        raise ValueError(f"Con ø {designacion} el espaciamiento sale {s:.1f} cm. Usar una barra mayor.")
    return min(s, s_max)


# --- Datos de entrada ------------------------------------------------------
@dataclass(frozen=True)
class DatosPuente:
    configuracion: str
    luz: float  # m, entre ejes de apoyos
    imda: float  # veh/día
    f_c: float  # kgf/cm²
    fy: float  # kgf/cm²
    e_asfalto: float  # m
    d12: float  # m, ejes 1-2 del camión HL-93 (dato del taller)
    d23: float  # m, ejes 2-3 del camión HL-93 (dato del taller)
    galibo: float  # m, gálibo hidráulico mínimo
    # Sección transversal de un puente (una calzada), en m
    ancho_barrera: float
    berma_interior: float
    carriles_via: int
    ancho_carril_via: float
    berma_exterior: float
    area_barrera: float  # m²
    # Diseño
    t: float  # m, espesor adoptado
    recubrimiento: float  # cm, del fondo al eje de las barras (re)
    barra_principal: str
    barra_distribucion: str
    barra_temperatura: str
    eta_D: float
    eta_R: float
    eta_I: float
    gamma_e: float  # exposición para fisuración

    @property
    def ancho_libre(self) -> float:
        """Ancho de calzada entre caras de barreras [m]."""
        return self.berma_interior + self.carriles_via * self.ancho_carril_via + self.berma_exterior

    @property
    def W(self) -> float:
        """Ancho total del puente, borde a borde [m]."""
        return self.ancho_libre + 2 * self.ancho_barrera

    @property
    def d(self) -> float:
        """Peralte efectivo [cm]: d = t - re."""
        return self.t * 100 - self.recubrimiento

    @property
    def eta(self) -> float:
        """Modificador de cargas η = ηD ηR ηI >= 0.95 (AASHTO 1.3.2.1)."""
        return max(self.eta_D * self.eta_R * self.eta_I, 0.95)


TALLER_AL = DatosPuente(
    configuracion="A–L",
    luz=20 * PIE,
    imda=4500,
    f_c=420.0,
    fy=4200.0,
    e_asfalto=3 * PULGADA,
    d12=3.00,
    d23=3.50,
    galibo=2.50,
    ancho_barrera=0.40,
    berma_interior=1.00,  # VERIFICAR con DG-2018 Tabla 304.02 y el criterio del curso
    carriles_via=2,
    ancho_carril_via=3.60,  # DG-2018 Art. 101.01, autopistas
    berma_exterior=2.60,  # VERIFICAR con DG-2018 Tabla 304.02 y el criterio del curso
    area_barrera=0.2028,  # barrera New Jersey TL-4, VERIFICAR con el plano de detalle
    t=0.40,
    recubrimiento=4.5,  # re al eje de la barra, criterio de clase
    barra_principal='1"',
    barra_distribucion='5/8"',
    barra_temperatura='1/2"',
    eta_D=1.00,  # diseño convencional (AASHTO 1.3.3)
    eta_R=1.00,  # redundancia convencional (AASHTO 1.3.4)
    eta_I=1.05,  # puente importante (AASHTO 1.3.5)
    gamma_e=0.75,  # clase 2: expuesto a la humedad del río (AASHTO 5.6.7)
)

VEHICULO_P2 = vehiculo((7.0, 9.0, 9.0, 9.0, 9.0), (3.50, 1.30, 4.50, 1.30))


# --- Cálculo ---------------------------------------------------------------
@dataclass(frozen=True)
class Franja:
    nombre: str
    ancho: float  # m
    w_DC: float  # tonf/m por m de ancho
    w_DW: float  # tonf/m por m de ancho
    M_DC: float  # tonf·m/m
    M_DW: float
    M_LL: float  # LL+IM, tonf·m/m
    M_u: float
    M_s: float  # Servicio I
    As_req: float  # cm²/m
    s: float  # cm
    As: float  # cm²/m


def calcular(p: DatosPuente) -> dict:
    """Resuelve la Pregunta 01. Devuelve todos los resultados intermedios."""
    r: dict = {"p": p}
    L = p.luz
    r["clase"] = clasificar_via(p.imda)
    r["t_min"] = t_min_losa(L)
    if p.t < r["t_min"] - TOL:
        raise ValueError(f"t = {p.t:.2f} m < t_min = {r['t_min']:.3f} m. Aumentar el espesor.")
    r["NL"] = numero_carriles(p.ancho_libre)

    # Materiales
    r["Ec"] = Ec(p.f_c)
    r["n"] = ES / r["Ec"]
    r["beta1"] = beta_1(p.f_c)
    r["fr"] = fr(p.f_c)

    # Cargas permanentes, franja interior de 1 m
    w_DC = p.t * GAMMA_CONCRETO
    w_DW = p.e_asfalto * GAMMA_ASFALTO
    r["w_barrera"] = p.area_barrera * GAMMA_CONCRETO
    L2_8 = L**2 / 8

    # Carga viva por carril
    camion = vehiculo((P_DELANTERO, P_TRASERO, P_TRASERO), (p.d12, p.d23))
    tandem = vehiculo((P_TANDEM, P_TANDEM), (S_TANDEM,))
    r["camion"], r["tandem"] = camion, tandem
    r["M_camion"] = momento_maximo(camion, L)
    r["M_tandem"] = momento_maximo(tandem, L)
    r["barre_camion"] = casos_barre(camion, L)
    r["barre_tandem"] = casos_barre(tandem, L)
    r["M_carril"] = W_CARRIL * L2_8
    r["M_vehicular"] = max(r["M_camion"].M, r["M_tandem"].M)
    r["gobierna"] = "tándem" if r["M_tandem"].M >= r["M_camion"].M else "camión"
    r["M_LL_carril"] = (1 + IM) * r["M_vehicular"] + r["M_carril"]

    # Anchos de franja
    r["E1"] = E_un_carril(L, p.W)
    r["Em"] = E_multiples_carriles(L, p.W, r["NL"])
    r["Em_sin_limite"] = (2100 + 0.12 * math.sqrt(min(L * 1000, 18_000) * min(p.W * 1000, 18_000))) / 1000
    r["E"] = min(r["E1"], r["Em"])
    r["Eb"] = E_borde(p.ancho_barrera, r["E"])
    # Momento por metro: M = m·M_LL+IM/E con un carril y con varios; se toma el mayor
    r["M_1carril"] = M_UN_CARRIL * r["M_LL_carril"] / r["E1"]
    r["M_multi"] = M_MULTIPLES * r["M_LL_carril"] / r["Em"]
    r["gobierna_carriles"] = "un carril" if r["M_1carril"] >= r["M_multi"] else "múltiples carriles"

    eta = p.eta
    franjas = []
    # Franja interior
    M_DC, M_DW = w_DC * L2_8, w_DW * L2_8
    M_LL = max(r["M_1carril"], r["M_multi"])
    franjas.append(("Interior", 1.0, w_DC, w_DW, M_DC, M_DW, M_LL))
    # Franja de borde: barrera, asfalto fuera de la barrera, una línea de ruedas y su parte del carril
    Eb = r["Eb"]
    r["ancho_carril_borde"] = Eb - p.ancho_barrera
    w_DC_b = w_DC + r["w_barrera"] / Eb
    w_DW_b = w_DW * r["ancho_carril_borde"] / Eb
    r["M_LL_borde_linea"] = 0.5 * (1 + IM) * r["M_vehicular"] + r["M_carril"] * r["ancho_carril_borde"] / ANCHO_CARGA_CARRIL
    M_LL_b = M_UN_CARRIL * r["M_LL_borde_linea"] / Eb
    franjas.append(("Borde", Eb, w_DC_b, w_DW_b, w_DC_b * L2_8, w_DW_b * L2_8, M_LL_b))

    b, d, h = 100.0, p.d, p.t * 100
    r["franjas"] = []
    for nombre, ancho, wdc, wdw, mdc, mdw, mll in franjas:
        M_u = eta * (GAMMA_DC * mdc + GAMMA_DW * mdw + GAMMA_LL * mll)
        M_s = mdc + mdw + mll
        As_req = As_flexion(M_u * TONF_M_A_KGF_CM, p.f_c, p.fy, b, d)
        s = espaciamiento(As_req, p.barra_principal, min(ESPACIAMIENTO_MAX_PRINCIPAL, 1.5 * h))
        As = barra(p.barra_principal).area * 100 / s
        r["franjas"].append(Franja(nombre, ancho, wdc, wdw, mdc, mdw, mll, M_u, M_s, As_req, s, As))

    # Verificaciones por franja
    dc = p.recubrimiento
    r["dc"], r["beta_s"] = dc, beta_s(dc, h)
    r["Mcr"] = Mcr(p.f_c, b, h) / TONF_M_A_KGF_CM

    # Fatiga: un camión con ejes traseros a 9.00 m, IM = 15 %, franja de un carril,
    # sin factor de presencia múltiple (AASHTO 3.6.1.1.2: se divide entre 1.20)
    camion_fatiga = vehiculo((P_DELANTERO, P_TRASERO, P_TRASERO), (p.d12, S_FATIGA))
    r["camion_fatiga"] = camion_fatiga
    r["M_fatiga_carril"] = momento_maximo(camion_fatiga, L)
    r["M_fatiga_m"] = (1 + IM_FATIGA) * r["M_fatiga_carril"].M / r["E1"] / M_UN_CARRIL

    r["detalle"] = {}
    verificaciones: list[Verificacion] = []
    for f in r["franjas"]:
        dd: dict = {}
        dd["a"] = bloque_a(f.As, p.f_c, p.fy, b)
        dd["c"] = dd["a"] / r["beta1"]
        dd["phi_Mn"] = phi_Mn(f.As, p.f_c, p.fy, b, d) / TONF_M_A_KGF_CM
        sec = seccion_fisurada(f.As, b, d, r["n"])
        dd["y"], dd["jd"] = sec.y, sec.jd
        dd["fss"] = f.M_s * TONF_M_A_KGF_CM / (f.As * sec.jd)
        dd["s_max"] = s_max_fisuracion(dd["fss"], p.gamma_e, dc, h)
        dd["f_min"] = (f.M_DC + f.M_DW) * TONF_M_A_KGF_CM / (f.As * sec.jd)
        dd["df"] = GAMMA_FATIGA * r["M_fatiga_m"] * TONF_M_A_KGF_CM / (f.As * sec.jd)
        dd["df_9ed"] = GAMMA_FATIGA_9ED * r["M_fatiga_m"] * TONF_M_A_KGF_CM / (f.As * sec.jd)
        dd["umbral"] = umbral_fatiga(dd["f_min"])
        dd["umbral_9ed"] = umbral_fatiga_9ed(dd["f_min"], p.fy)
        r["detalle"][f.nombre] = dd
        tag = f"franja {f.nombre.lower()}"
        verificaciones += [
            Verificacion(f"Resistencia I, M_u <= φMn ({tag})", f.M_u, dd["phi_Mn"], "tonf·m/m", "AASHTO 5.6.3.2"),
            Verificacion(f"Ductilidad c/d <= 0.42 ({tag})", dd["c"] / d, C_D_MAX, "", "Criterio de clase", 3),
            Verificacion(
                f"Acero mínimo min(Mcr, 1.33M_u) <= φMn ({tag})",
                min(r["Mcr"], 1.33 * f.M_u),
                dd["phi_Mn"],
                "tonf·m/m",
                "AASHTO 5.6.3.3",
            ),
            Verificacion(
                f"Cuantía mínima ρ >= 0.03 f'c/fy ({tag})",
                RHO_MIN_COEF * p.f_c / p.fy * b * d,
                f.As,
                "cm²/m",
                "Criterio de clase",
            ),
            Verificacion(f"Servicio I, fss <= 0.6 fy ({tag})", dd["fss"], FSS_MAX * p.fy, "kgf/cm²", "AASHTO 5.6.7"),
            Verificacion(f"Fisuración, s <= s_max ({tag})", f.s, dd["s_max"], "cm", "AASHTO 5.6.7"),
            Verificacion(f"Fatiga I, Δf <= ΔF_TH ({tag})", dd["df"], dd["umbral"], "kgf/cm²", "AASHTO 5.5.3"),
        ]

    # Acero de distribución (con el mayor As principal colocado) y de temperatura
    r["pct_dist"] = porcentaje_distribucion(L)
    As_principal_max = max(f.As for f in r["franjas"])
    r["As_dist_req"] = r["pct_dist"] / 100 * As_principal_max
    r["s_dist"] = espaciamiento(r["As_dist_req"], p.barra_distribucion, ESPACIAMIENTO_MAX_PRINCIPAL)
    r["As_dist"] = barra(p.barra_distribucion).area * 100 / r["s_dist"]
    r["As_temp_req"] = As_temperatura(p.t, p.fy)
    r["s_temp"] = espaciamiento(r["As_temp_req"], p.barra_temperatura, min(ESPACIAMIENTO_MAX_TEMPERATURA, 3 * h))
    r["As_temp"] = barra(p.barra_temperatura).area * 100 / r["s_temp"]
    verificaciones += [
        Verificacion("Acero de distribución", r["As_dist_req"], r["As_dist"], "cm²/m", "AASHTO 9.7.3.2"),
        Verificacion("Acero de temperatura (cara superior)", r["As_temp_req"], r["As_temp"], "cm²/m", "Criterio de clase"),
    ]
    r["verificaciones"] = verificaciones

    # Gálibo: fondo de losa >= NAME + gálibo
    r["rasante_sobre_NAME"] = p.galibo + p.t + p.e_asfalto
    return r


def calcular_p2(L: float) -> dict:
    """Resuelve la Pregunta 02 (reacción y momento máximo, Teorema de Barré)."""
    v = VEHICULO_P2
    return {
        "ejes": v,
        "L": L,
        "R_total": sum(e.P for e in v),
        "x_R": sum(e.P * e.x for e in v) / sum(e.P for e in v),
        "reaccion": reaccion_maxima(v, L),
        "posiciones_reaccion": posiciones_reaccion(v, L),
        "barre": casos_barre(v, L),
        "M": momento_maximo(v, L),
    }


# --- Reporte ---------------------------------------------------------------
def memoria(r: dict, r2: dict) -> str:
    p = r["p"]
    lineas = [
        f"PUENTE LOSA L = {p.luz:.3f} m — configuración {p.configuracion}",
        f"  Vía: {r['clase']}   W = {p.W:.2f} m   NL = {r['NL']}",
        f"  t_min = {r['t_min']:.3f} m -> t = {p.t:.2f} m   d = {p.d:.2f} cm   η = {p.eta:.2f}",
        f"  M camión = {r['M_camion'].M:.3f}  M tándem = {r['M_tandem'].M:.3f}  M carril = {r['M_carril']:.3f} tonf·m",
        f"  M LL+IM por carril = {r['M_LL_carril']:.3f} tonf·m   E1 = {r['E1']:.3f}  Em = {r['Em']:.3f}"
        f"  Eborde = {r['Eb']:.3f} m",
    ]
    for f in r["franjas"]:
        lineas.append(
            f"  {f.nombre:9s} M_DC={f.M_DC:.3f} M_DW={f.M_DW:.3f} M_LL={f.M_LL:.3f} M_u={f.M_u:.3f} "
            f"M_s={f.M_s:.3f}  As_req={f.As_req:.2f} -> ø{p.barra_principal}@{f.s:.1f} (As={f.As:.2f})"
        )
    lineas.append(f"  Distribución ø{p.barra_distribucion}@{r['s_dist']:.1f}   Temperatura ø{p.barra_temperatura}@{r['s_temp']:.1f}")
    lineas += ["", "Verificaciones", *(f"  {v}" for v in r["verificaciones"])]
    re_ = r2["reaccion"]
    lineas += [
        "",
        f"PREGUNTA 02  L = {r2['L']:.3f} m",
        f"  R_max = {re_.R:.3f} tonf (eje {re_.eje_en_apoyo + 1} en el apoyo, ejes en luz "
        f"{[i + 1 for i in re_.en_luz]})",
        f"  M_max = {r2['M'].M:.3f} tonf·m bajo el eje {r2['M'].critico + 1} a {r2['M'].x_critico:.3f} m del apoyo",
    ]
    return "\n".join(lineas)


# --- Documento LaTeX -------------------------------------------------------
def num(x: float, dec: int = 2) -> str:
    """Número con punto decimal y separador de miles fino para LaTeX (redondeo como Excel)."""
    s = f"{redondear(x, dec):,.{dec}f}"
    return s.replace(",", "\\,")


def _fila_barre(c: CasoBarre, ejes: tuple[Eje, ...]) -> str:
    grupo = "--".join(str(g + 1) for g in c.grupo) if len(c.grupo) > 1 else str(c.grupo[0] + 1)
    estado = r"\textcolor{ok}{sí}" if c.valido else r"\textcolor{mal}{no}"
    M = num(c.M, 3) if c.valido else "--"
    return (
        f"{grupo} & {c.critico + 1} & {num(c.R, 2)} & {num(c.e, 3)} & {num(c.x_critico, 3)} & {estado} & {M} \\\\"
    )


def _tabla_barre(casos: list[CasoBarre], ejes: tuple[Eje, ...]) -> str:
    return "\n".join(_fila_barre(c, ejes) for c in casos if len(c.grupo) > 1)


def _ejes_tikz(cargas: list[tuple[int, float, float]], L: float) -> str:
    """Flechas TikZ para (n° de eje, P [tonf], x desde el apoyo A [m]); fuera de la luz van en gris."""
    out = []
    for numero, P, x in cargas:
        color = "carga" if _en_luz(x, L) else "gray!55"
        out.append(
            rf"\draw[-{{Stealth[length=2.2mm]}}, very thick, {color}] ({x:.3f},1.25) -- ({x:.3f},0.10) "
            rf"node[pos=0, above, font=\scriptsize, text={color}, align=center] "
            rf"{{\textbf{{{numero}}}\\{num(P, 2)}}};"
        )
    return "\n".join(out)


def _cargas(ejes: tuple[Eje, ...], a: float) -> list[tuple[int, float, float]]:
    return [(i + 1, e.P, a + e.x) for i, e in enumerate(ejes)]


def _seccion_tikz(p: DatosPuente, Eb: float) -> str:
    """Sección transversal de un puente, en m (la escala la fija el tikzpicture)."""
    tramos = [
        (p.ancho_barrera, "Barrera"),
        (p.berma_interior, "Berma int."),
        *[(p.ancho_carril_via, f"Carril {k + 1}") for k in range(p.carriles_via)],
        (p.berma_exterior, "Berma ext."),
        (p.ancho_barrera, "Barrera"),
    ]
    W, t, e = p.W, p.t, p.e_asfalto
    b = p.ancho_barrera
    out = [
        rf"\fill[gray!25] ({b:.3f},0) rectangle ({W - b:.3f},{e:.4f});",
        rf"\draw[fill=gray!8] (0,{-t:.3f}) rectangle ({W:.3f},0);",
        rf"\node[font=\scriptsize] at ({W / 2:.3f},{-t / 2:.3f}) {{Losa maciza $t = {num(t, 2)}$ m}};",
    ]
    perfil = [(0, 0), (b, 0), (b, 0.075), (0.225 * b / 0.40, 0.33), (0.15 * b / 0.40, 0.81), (0, 0.81)]
    for espejo in (False, True):
        pts = [((W - x) if espejo else x, y) for x, y in perfil]
        out.append(r"\draw[fill=gray!35] " + " -- ".join(f"({x:.3f},{y:.3f})" for x, y in pts) + " -- cycle;")
    x = 0.0
    for ancho, texto in tramos:
        out.append(rf"\draw[<->, >=Stealth] ({x:.3f},1.15) -- ({x + ancho:.3f},1.15) "
                   rf"node[midway, above, font=\scriptsize] {{{num(ancho, 2)}}};")
        out.append(rf"\draw[gray] ({x:.3f},1.05) -- ({x:.3f},1.25);")
        if texto != "Barrera":
            out.append(rf"\node[font=\scriptsize] at ({x + ancho / 2:.3f},0.35) {{{texto}}};")
        x += ancho
    out.append(rf"\draw[gray] ({W:.3f},1.05) -- ({W:.3f},1.25);")
    for k in range(1, p.carriles_via):
        xc = p.ancho_barrera + p.berma_interior + k * p.ancho_carril_via
        out.append(rf"\draw[dashed] ({xc:.3f},{e:.4f}) -- ({xc:.3f},0.20);")
    out.append(rf"\draw[<->, >=Stealth] (0,{-t - 0.35:.3f}) -- ({W:.3f},{-t - 0.35:.3f}) "
               rf"node[midway, below, font=\scriptsize] {{$W = {num(W, 2)}$ m}};")
    out.append(rf"\draw[decorate, decoration={{brace, mirror, amplitude=4pt}}] (0,{-t - 0.08:.3f}) -- "
               rf"({Eb:.3f},{-t - 0.08:.3f}) node[midway, below=3pt, font=\scriptsize] {{$E_b$}};")
    out.append(rf"\draw[decorate, decoration={{brace, amplitude=4pt}}] ({W:.3f},{-t - 0.08:.3f}) -- "
               rf"({W - Eb:.3f},{-t - 0.08:.3f}) node[midway, below=3pt, font=\scriptsize] {{$E_b$}};")
    return "\n".join(out)


DESCRIPCIONES_LATEX = (
    ("min(Mcr, 1.33M_u) <= φMn", r"$\min(M_{cr};\,1.33M_u) \le \phi M_n$"),
    ("M_u <= φMn", r"$M_u \le \phi M_n$"),
    ("c/d <= 0.42", r"$c/d \le 0.42$"),
    ("ρ >= 0.03 f'c/fy", r"$\rho \ge 0.03\,f'_c/f_y$"),
    ("fss <= 0.6 fy", r"$f_{ss} \le 0.6 f_y$"),
    ("s <= s_max", r"$s \le s_{\max}$"),
    ("Δf <= ΔF_TH", r"$\Delta f \le \Delta F_{TH}$"),
)


def valores_latex(r: dict, r2: dict) -> dict[str, str]:
    p = r["p"]
    L = p.luz
    fi, fb = r["franjas"]
    di, db = r["detalle"]["Interior"], r["detalle"]["Borde"]
    mc, mt = r["M_camion"], r["M_tandem"]
    camion = r["camion"]
    v: dict[str, str] = {}

    v["L"] = num(L, 3)
    v["L_mm"] = num(L * 1000, 0)
    v["L2_8"] = num(L**2 / 8, 4)
    v["clase"] = r["clase"]
    v["imda"] = num(p.imda, 0)
    v["W"] = num(p.W, 2)
    v["w_libre"] = num(p.ancho_libre, 2)
    v["NL"] = str(r["NL"])
    v["w_sobre_36"] = num(p.ancho_libre / ANCHO_CARRIL_DISENO, 2)
    v["b_int"] = num(p.berma_interior, 2)
    v["b_ext"] = num(p.berma_exterior, 2)
    v["barrera"] = num(p.ancho_barrera, 2)
    v["calzada"] = num(p.carriles_via * p.ancho_carril_via, 2)
    v["t_min"] = num(r["t_min"], 3)
    v["t_min_mm"] = num(r["t_min"] * 1000, 1)
    v["t"] = num(p.t, 2)
    v["t_cm"] = num(p.t * 100, 0)
    v["t_mm"] = num(p.t * 1000, 0)
    v["fc"] = num(p.f_c, 0)
    v["fc_MPa"] = num(p.f_c * KGF_CM2_A_MPA, 2)
    v["fy"] = num(p.fy, 0)
    v["fy_MPa"] = num(p.fy * KGF_CM2_A_MPA, 1)
    v["Ec"] = num(r["Ec"], 0)
    v["Es"] = num(ES, 0)
    v["n"] = num(r["n"], 2)
    v["beta1"] = num(r["beta1"], 3)
    v["fr"] = num(r["fr"], 2)
    v["rec"] = num(p.recubrimiento, 1)
    v["db"] = num(barra(p.barra_principal).diametro, 2)
    v["d"] = num(p.d, 2)
    v["eta"] = num(p.eta, 2)
    v["e_asf_cm"] = num(p.e_asfalto * 100, 2)

    # Cargas permanentes
    v["w_DC"] = num(fi.w_DC, 3)
    v["w_DW"] = num(fi.w_DW, 4)
    v["M_DC"] = num(fi.M_DC, 3)
    v["M_DW"] = num(fi.M_DW, 3)
    v["w_barrera"] = num(r["w_barrera"], 3)
    v["A_barrera"] = num(p.area_barrera, 4)

    # Camión: candidatos de Barré
    v["d12"] = num(p.d12, 2)
    v["d23"] = num(p.d23, 2)
    v["largo_camion"] = num(camion[-1].x, 2)
    v["tabla_barre_camion"] = _tabla_barre(r["barre_camion"], camion)
    v["tabla_barre_tandem"] = _tabla_barre(r["barre_tandem"], r["tandem"])
    v["M_eje_solo"] = num(P_TRASERO * L / 4, 3)
    v["M_camion"] = num(mc.M, 3)
    v["camion_critico"] = str(mc.critico + 1)
    v["camion_xc"] = num(mc.x_critico, 3)
    v["camion_ejes_luz"] = ", ".join(str(i + 1) for i in mc.en_luz)
    v["M_tandem"] = num(mt.M, 3)
    v["tandem_xc"] = num(mt.x_critico, 3)
    v["tandem_L2_s4"] = num(L / 2 - S_TANDEM / 4, 3)
    v["M_carril"] = num(r["M_carril"], 3)
    v["gobierna"] = r["gobierna"]
    v["M_veh"] = num(r["M_vehicular"], 3)
    v["M_LL_carril"] = num(r["M_LL_carril"], 3)
    v["IM_M"] = num((1 + IM) * r["M_vehicular"], 3)

    # Franjas
    v["E1"] = num(r["E1"], 3)
    v["E1_mm"] = num(r["E1"] * 1000, 1)
    v["Em"] = num(r["Em"], 3)
    v["Em_mm"] = num(r["Em_sin_limite"] * 1000, 1)
    v["W_NL_mm"] = num(p.W * 1000 / r["NL"], 1)
    v["W_mm"] = num(p.W * 1000, 0)
    v["W1_1"] = num(min(p.W * 1000, 9000), 0)
    v["W1_m"] = num(min(p.W * 1000, 18000), 0)
    v["raiz_1"] = num(math.sqrt(min(L * 1000, 18000) * min(p.W * 1000, 9000)), 1)
    v["raiz_m"] = num(math.sqrt(min(L * 1000, 18000) * min(p.W * 1000, 18000)), 1)
    v["E"] = num(r["E"], 3)
    v["M_1carril"] = num(r["M_1carril"], 3)
    v["M_multi"] = num(r["M_multi"], 3)
    v["gobierna_carriles"] = r["gobierna_carriles"]
    v["raiz_1"] = num(math.sqrt(min(L, 18.26) * min(p.W, 9.14)), 4)
    v["raiz_m"] = num(math.sqrt(min(L, 18.26) * min(p.W, 18.0)), 4)
    v["W1_1"] = num(min(p.W, 9.14), 2)
    v["W1_m"] = num(min(p.W, 18.0), 2)
    v["W_NL"] = num(p.W / r["NL"], 3)
    v["E1_m"] = num(r["E1"], 3)
    v["Em_sin"] = num(2.10 + 0.12 * math.sqrt(min(L, 18.26) * min(p.W, 18.0)), 3)
    v["rho_min"] = num(RHO_MIN_COEF * p.f_c / p.fy, 4)
    v["As_min_rho"] = num(RHO_MIN_COEF * p.f_c / p.fy * 100 * p.d, 2)
    v["Eb"] = num(r["Eb"], 3)
    v["Eb_formula"] = num(p.ancho_barrera + 0.30 + r["E"] / 4, 3)
    v["E_2"] = num(r["E"] / 2, 3)
    v["ancho_carril_borde"] = num(r["ancho_carril_borde"], 3)
    v["M_LL_borde_linea"] = num(r["M_LL_borde_linea"], 3)

    for clave, f, dd in (("i", fi, di), ("b", fb, db)):
        v[f"wDC_{clave}"] = num(f.w_DC, 3)
        v[f"wDW_{clave}"] = num(f.w_DW, 4)
        v[f"MDC_{clave}"] = num(f.M_DC, 3)
        v[f"MDW_{clave}"] = num(f.M_DW, 3)
        v[f"MLL_{clave}"] = num(f.M_LL, 3)
        v[f"Mu_{clave}"] = num(f.M_u, 3)
        v[f"Mu_sin_eta_{clave}"] = num(f.M_u / p.eta, 3)
        v[f"Ms_{clave}"] = num(f.M_s, 3)
        v[f"Mu_kgcm_{clave}"] = num(f.M_u * TONF_M_A_KGF_CM, 0)
        v[f"Asreq_{clave}"] = num(f.As_req, 2)
        v[f"s_{clave}"] = num(f.s, 1)
        v[f"s_teo_{clave}"] = num(barra(p.barra_principal).area / f.As_req * 100, 1)
        v[f"As_{clave}"] = num(f.As, 2)
        v[f"a_{clave}"] = num(dd["a"], 2)
        v[f"c_{clave}"] = num(dd["c"], 2)
        v[f"cd_{clave}"] = num(dd["c"] / p.d, 3)
        v[f"phiMn_{clave}"] = num(dd["phi_Mn"], 3)
        v[f"DC_Mu_{clave}"] = num(f.M_u / dd["phi_Mn"], 2)
        v[f"Mmin_{clave}"] = num(min(r["Mcr"], 1.33 * f.M_u), 3)
        v[f"Mu133_{clave}"] = num(1.33 * f.M_u, 3)
        v[f"nAs_{clave}"] = num(r["n"] * f.As, 2)
        v[f"y_{clave}"] = num(dd["y"], 2)
        v[f"jd_{clave}"] = num(dd["jd"], 2)
        v[f"fss_{clave}"] = num(dd["fss"], 1)
        v[f"fss_MPa_{clave}"] = num(dd["fss"] * KGF_CM2_A_MPA, 1)
        v[f"smax_{clave}"] = num(dd["s_max"], 1)
        v[f"fmin_{clave}"] = num(dd["f_min"], 1)
        v[f"df_{clave}"] = num(dd["df"], 1)
        v[f"umbral_{clave}"] = num(dd["umbral"], 1)
        v[f"df9_{clave}"] = num(dd["df_9ed"], 1)
        v[f"umbral9_{clave}"] = num(dd["umbral_9ed"], 1)
        v[f"k_{clave}"] = num(2 * f.M_u * TONF_M_A_KGF_CM / (PHI_FLEXION * 0.85 * p.f_c * 100 * p.d**2), 4)

    v["Mcr"] = num(r["Mcr"], 3)
    v["Sc"] = num(100 * (p.t * 100) ** 2 / 6, 0)
    v["dc"] = num(r["dc"], 2)
    v["dc_mm"] = num(r["dc"] * 10, 1)
    v["beta_s"] = num(r["beta_s"], 4)
    v["gamma_e"] = num(p.gamma_e, 2)
    v["fss_max"] = num(FSS_MAX * p.fy, 0)

    mf = r["M_fatiga_carril"]
    v["M_fat_carril"] = num(mf.M, 3)
    v["M_fat_m"] = num(r["M_fatiga_m"], 3)
    v["fat_critico"] = str(mf.critico + 1)

    v["pct_dist"] = num(r["pct_dist"], 2)
    v["As_principal_max"] = num(max(f.As for f in r["franjas"]), 2)
    v["As_dist_req"] = num(r["As_dist_req"], 2)
    v["s_dist"] = num(r["s_dist"], 1)
    v["As_dist"] = num(r["As_dist"], 2)
    v["As_temp_req"] = num(r["As_temp_req"], 2)
    v["As_temp_mm2"] = num(r["As_temp_req"] * 100, 1)
    v["s_temp"] = num(r["s_temp"], 1)
    v["As_temp"] = num(r["As_temp"], 2)
    v["bp"] = p.barra_principal.replace('"', "''")
    v["bd"] = p.barra_distribucion.replace('"', "''")
    v["bt"] = p.barra_temperatura.replace('"', "''")
    v["area_bp"] = num(barra(p.barra_principal).area, 2)
    v["area_bd"] = num(barra(p.barra_distribucion).area, 2)
    v["area_bt"] = num(barra(p.barra_temperatura).area, 2)
    v["rasante"] = num(r["rasante_sobre_NAME"], 3)
    v["galibo"] = num(p.galibo, 2)

    filas = []
    for ver in r["verificaciones"]:
        estado = r"\textcolor{ok}{\textbf{CUMPLE}}" if ver.cumple else r"\textcolor{mal}{\textbf{NO CUMPLE}}"
        desc = ver.descripcion
        for texto, latex in DESCRIPCIONES_LATEX:
            desc = desc.replace(texto, latex)
        unidad = ver.unidad.replace("tonf", "t").replace("kgf", "kg").replace("²", r"$^2$").replace("·", r"$\cdot$")
        dec = ver.decimales
        filas.append(
            f"{desc} & {num(ver.demanda, dec)} & {num(ver.capacidad, dec)} & {unidad} & "
            f"{num(ver.ratio, 2)} & {estado} \\\\"
        )
    v["tabla_verificaciones"] = "\n".join(filas)

    # Figuras: coordenadas en m; la escala horizontal la fija el tikzpicture
    v["esc"] = f"{10.5 / L:.4f}"
    v["Lr"] = f"{L:.4f}"
    v["tikz_seccion"] = _seccion_tikz(p, r["Eb"])
    v["tikz_tandem"] = _ejes_tikz(_cargas(r["tandem"], mt.a), L)
    v["tikz_camion"] = _ejes_tikz(_cargas(camion, mc.a), L)
    v["xc_tandem"] = f"{mt.x_critico:.4f}"
    v["xc_camion"] = f"{mc.x_critico:.4f}"

    # Pregunta 02
    ejes2 = r2["ejes"]
    re2, m2 = r2["reaccion"], r2["M"]
    v["p2_largo"] = num(ejes2[-1].x, 2)
    v["p2_R"] = num(re2.R, 3)
    v["p2_R_eje"] = str(re2.eje_en_apoyo + 1)
    v["p2_R_ejes_luz"] = " y ".join(str(i + 1) for i in sorted(re2.en_luz) if i != re2.eje_en_apoyo)
    v["p2_R_suma"] = " + ".join(
        rf"{num(P, 0)}\cdot\dfrac{{{num(L, 3)}-{num(x, 2)}}}{{{num(L, 3)}}}" for _, P, x in re2.cargas
    )
    filas = []
    for pr in r2["posiciones_reaccion"]:
        marca = r"\rowcolor{acento!10}" if pr is re2 else ""
        filas.append(
            f"{marca}{pr.sentido} & {pr.eje_en_apoyo + 1} & {', '.join(str(i + 1) for i in sorted(pr.en_luz))} & "
            f"{num(pr.R, 3)} \\\\"
        )
    v["p2_tabla_reacciones"] = "\n".join(filas)
    v["p2_tabla_barre"] = _tabla_barre(r2["barre"], ejes2)
    v["p2_M"] = num(m2.M, 3)
    v["p2_M_eje"] = str(m2.critico + 1)
    v["p2_M_x"] = num(m2.x_critico, 3)
    v["p2_M_x_centro"] = num(L / 2 - m2.x_critico, 3)
    v["p2_M_ejes_luz"] = ", ".join(str(i + 1) for i in m2.en_luz)
    v["p2_M_barrido"] = num(momento_maximo_barrido(ejes2, L), 3)
    v["tikz_p2_M"] = _ejes_tikz(_cargas(ejes2, m2.a), L)
    v["xc_p2"] = f"{m2.x_critico:.4f}"
    # Posición de la reacción máxima: todos los ejes (también los que quedan fuera), numeración original
    x_apoyo = ejes2[re2.eje_en_apoyo].x
    signo = 1 if re2.sentido == "directo" else -1
    v["tikz_p2_R"] = _ejes_tikz([(i + 1, e.P, signo * (e.x - x_apoyo)) for i, e in enumerate(ejes2)], L)
    v["p2_PL4"] = num(9.0 * L / 4, 3)
    v["p2_M_un_eje"] = num(momento_bajo_eje(ejes2, L / 2 - ejes2[1].x, L, 1), 3)
    return v


def generar_tex(r: dict, r2: dict, plantilla: Path, salida: Path) -> None:
    """Reemplaza los marcadores <<clave>> de la plantilla; falla si falta alguno."""
    v = valores_latex(r, r2)
    texto = plantilla.read_text(encoding="utf-8")
    faltan = sorted(set(re.findall(r"<<(\w+)>>", texto)) - v.keys())
    if faltan:
        raise ValueError(f"Faltan valores para los marcadores: {', '.join(faltan)}")
    salida.write_text(re.sub(r"<<(\w+)>>", lambda m: v[m.group(1)], texto), encoding="utf-8")


if __name__ == "__main__":
    aqui = Path(__file__).resolve().parent
    res = calcular(TALLER_AL)
    res2 = calcular_p2(TALLER_AL.luz)
    print(memoria(res, res2))
    plantilla_tex = aqui / "plantilla_taller01.tex"
    if plantilla_tex.exists():
        generar_tex(res, res2, plantilla_tex, aqui / "taller01_puentes.tex")
        print("\nGenerado: taller01_puentes.tex")
