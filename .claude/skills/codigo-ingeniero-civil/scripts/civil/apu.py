"""Análisis de precios unitarios (APU) y presupuesto, con la estructura de S10.

Costos en soles (S/) sin IGV. Los precios de insumos y de hora-hombre cambian
cada año: se cargan desde datos con fecha de vigencia, no se escriben en el código.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .unidades import redondear

JORNADA_H = 8.0  # horas por día de trabajo
DECIMALES_CANTIDAD = 4
DECIMALES_PARCIAL = 2

TIPOS = ("mano_obra", "material", "equipo", "subcontrato")


@dataclass
class Insumo:
    tipo: str  # uno de TIPOS
    descripcion: str
    unidad: str  # hh, hm, m3, kg, bls, %MO, ...
    cantidad: float
    precio: float  # S/ por unidad
    cuadrilla: float | None = None

    def __post_init__(self) -> None:
        if self.tipo not in TIPOS:
            raise ValueError(f"Tipo de insumo '{self.tipo}' no válido: {TIPOS}")

    @property
    def parcial(self) -> float:
        return redondear(self.cantidad * self.precio, DECIMALES_PARCIAL)


@dataclass
class APU:
    partida: str
    unidad: str
    rendimiento: float  # unidad de la partida por día
    insumos: list[Insumo] = field(default_factory=list)
    herramientas: float = 0.03  # fracción de la mano de obra

    def __post_init__(self) -> None:
        if self.rendimiento <= 0:
            raise ValueError(f"{self.partida}: el rendimiento debe ser > 0 {self.unidad}/día")

    def _horas(self, cuadrilla: float) -> float:
        return redondear(cuadrilla * JORNADA_H / self.rendimiento, DECIMALES_CANTIDAD)

    def mano_obra(self, descripcion: str, cuadrilla: float, precio_hh: float) -> APU:
        self.insumos.append(Insumo("mano_obra", descripcion, "hh", self._horas(cuadrilla), precio_hh, cuadrilla))
        return self

    def equipo(self, descripcion: str, cuadrilla: float, precio_hm: float) -> APU:
        self.insumos.append(Insumo("equipo", descripcion, "hm", self._horas(cuadrilla), precio_hm, cuadrilla))
        return self

    def material(self, descripcion: str, unidad: str, cantidad: float, precio: float, desperdicio: float = 0.0) -> APU:
        """cantidad neta por unidad de partida; desperdicio como fracción (0.05 = 5 %)."""
        bruta = redondear(cantidad * (1 + desperdicio), DECIMALES_CANTIDAD)
        self.insumos.append(Insumo("material", descripcion, unidad, bruta, precio))
        return self

    def subcontrato(self, descripcion: str, unidad: str, cantidad: float, precio: float) -> APU:
        self.insumos.append(Insumo("subcontrato", descripcion, unidad, cantidad, precio))
        return self

    def subtotal(self, tipo: str) -> float:
        return redondear(sum(i.parcial for i in self.insumos if i.tipo == tipo), DECIMALES_PARCIAL)

    @property
    def herramientas_manuales(self) -> float:
        """Va en el grupo de equipos como %MO, igual que en S10."""
        return redondear(self.herramientas * self.subtotal("mano_obra"), DECIMALES_PARCIAL)

    @property
    def costo_unitario(self) -> float:
        return redondear(sum(self.subtotal(t) for t in TIPOS) + self.herramientas_manuales, DECIMALES_PARCIAL)


@dataclass
class ItemPresupuesto:
    item: str
    descripcion: str
    unidad: str
    metrado: float
    precio_unitario: float

    @property
    def parcial(self) -> float:
        return redondear(self.metrado * self.precio_unitario, 2)


@dataclass
class Presupuesto:
    """Gastos generales y utilidad son decisiones de cada obra: no tienen valor por defecto."""

    items: list[ItemPresupuesto]
    gastos_generales: float  # fracción del costo directo
    utilidad: float  # fracción del costo directo
    igv: float = 0.18  # verificar la tasa vigente

    def resumen(self) -> dict[str, float]:
        costo_directo = redondear(sum(i.parcial for i in self.items), 2)
        gg = redondear(costo_directo * self.gastos_generales, 2)
        utilidad = redondear(costo_directo * self.utilidad, 2)
        subtotal = costo_directo + gg + utilidad
        igv = redondear(subtotal * self.igv, 2)
        return {
            "costo_directo": costo_directo,
            "gastos_generales": gg,
            "utilidad": utilidad,
            "subtotal": redondear(subtotal, 2),
            "igv": igv,
            "total": redondear(subtotal + igv, 2),
        }
