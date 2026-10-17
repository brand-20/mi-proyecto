"""Hojas de metrado y planilla de acero.

Formato y unidades de la Norma Técnica de Metrados para Obras de Edificación
y Habilitaciones Urbanas (RD N° 073-2010-VIVIENDA). El metrado es neto: los
desperdicios van en el análisis de precios unitarios, no aquí.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field

from .acero import barra
from .unidades import redondear

# Dimensiones que debe tener cada medición según la unidad de la partida.
# None = sin control (kg viene de la planilla de acero; glb es global).
DIMENSIONES_POR_UNIDAD = {"m3": 3, "m2": 2, "m": 1, "und": 0, "kg": None, "glb": None}

COLUMNAS_HOJA = ["Item", "Descripción", "Und", "Veces", "Largo", "Ancho", "Alto", "Parcial", "Total"]


@dataclass
class Medicion:
    """Una fila de la hoja de metrado. veces < 0 representa un descuento."""

    descripcion: str
    veces: float = 1
    largo: float | None = None
    ancho: float | None = None
    alto: float | None = None

    def parcial(self, unidad: str) -> float:
        dimensiones = [x for x in (self.largo, self.ancho, self.alto) if x is not None]
        esperadas = DIMENSIONES_POR_UNIDAD[unidad]
        if esperadas is not None and len(dimensiones) != esperadas:
            raise ValueError(
                f"'{self.descripcion}': una partida en {unidad} necesita {esperadas} "
                f"dimensiones y se dieron {len(dimensiones)}"
            )
        return self.veces * math.prod(dimensiones)


@dataclass
class Partida:
    item: str  # "05.02.01"
    descripcion: str
    unidad: str
    mediciones: list[Medicion] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.unidad not in DIMENSIONES_POR_UNIDAD:
            raise ValueError(f"Unidad '{self.unidad}' no reconocida: {list(DIMENSIONES_POR_UNIDAD)}")

    def agregar(
        self,
        descripcion: str,
        veces: float = 1,
        largo: float | None = None,
        ancho: float | None = None,
        alto: float | None = None,
    ) -> Partida:
        """Agrega una medición; devuelve la partida para encadenar llamadas."""
        self.mediciones.append(Medicion(descripcion, veces, largo, ancho, alto))
        return self

    @property
    def total(self) -> float:
        return redondear(sum(m.parcial(self.unidad) for m in self.mediciones), 2)


@dataclass
class FilaAcero:
    elemento: str  # "Columna C-1"
    designacion: str  # '5/8"'
    n_piezas: int  # piezas por elemento
    n_elementos: int  # elementos iguales
    longitud: float  # m por pieza, incluye ganchos y empalmes

    @property
    def longitud_total(self) -> float:
        return self.n_piezas * self.n_elementos * self.longitud

    @property
    def peso(self) -> float:
        return self.longitud_total * barra(self.designacion).peso


@dataclass
class PlanillaAcero:
    filas: list[FilaAcero] = field(default_factory=list)

    def agregar(
        self, elemento: str, designacion: str, n_piezas: int, n_elementos: int, longitud: float
    ) -> PlanillaAcero:
        self.filas.append(FilaAcero(elemento, designacion, n_piezas, n_elementos, longitud))
        return self

    def resumen_por_diametro(self) -> dict[str, dict[str, float]]:
        """{designación: {"longitud": m, "peso": kg}}"""
        resumen: dict[str, dict[str, float]] = defaultdict(lambda: {"longitud": 0.0, "peso": 0.0})
        for fila in self.filas:
            resumen[fila.designacion]["longitud"] += fila.longitud_total
            resumen[fila.designacion]["peso"] += fila.peso
        return dict(resumen)

    @property
    def total_kg(self) -> float:
        return redondear(sum(f.peso for f in self.filas), 2)


def a_filas(partidas: list[Partida]) -> list[list]:
    """Hoja de metrado como filas (encabezado de partida + mediciones)."""
    filas = []
    for p in partidas:
        filas.append([p.item, p.descripcion, p.unidad, None, None, None, None, None, p.total])
        for m in p.mediciones:
            filas.append(
                [None, m.descripcion, None, m.veces, m.largo, m.ancho, m.alto, redondear(m.parcial(p.unidad), 2), None]
            )
    return filas


def exportar_excel(partidas: list[Partida], ruta: str, hoja: str = "Metrados") -> None:
    """Escribe la hoja de metrado en Excel (requiere pandas y openpyxl)."""
    import pandas as pd

    df = pd.DataFrame(a_filas(partidas), columns=COLUMNAS_HOJA)
    with pd.ExcelWriter(ruta, engine="openpyxl") as escritor:
        df.to_excel(escritor, sheet_name=hoja, index=False)
        ws = escritor.sheets[hoja]
        for columna, ancho in zip("ABCDEFGHI", (10, 45, 6, 8, 8, 8, 8, 10, 10), strict=True):
            ws.column_dimensions[columna].width = ancho
        for fila in ws.iter_rows(min_row=2, min_col=4, max_col=9):
            for celda in fila:
                celda.number_format = "#,##0.00"
