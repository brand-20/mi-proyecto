"""Programación de obra: método de la ruta crítica (CPM), Gantt y curva S.

Tiempos en días hábiles desde el inicio de obra. Una actividad con
inicio = 0 y duración = 3 ocupa los días hábiles 1, 2 y 3 ([inicio, fin)).
Relaciones como en MS Project en español: FC, CC, FF, CF, con desfase en días.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from graphlib import CycleError, TopologicalSorter

RELACIONES = ("FC", "CC", "FF", "CF")
DIAS_LABORABLES = frozenset({0, 1, 2, 3, 4, 5})  # lunes a sábado


@dataclass
class Predecesora:
    codigo: str
    tipo: str = "FC"
    desfase: int = 0

    def __post_init__(self) -> None:
        if self.tipo not in RELACIONES:
            raise ValueError(f"Relación '{self.tipo}' no válida: {RELACIONES}")


@dataclass
class Actividad:
    codigo: str
    descripcion: str
    duracion: int  # días hábiles
    predecesoras: list[Predecesora] = field(default_factory=list)
    inicio_temprano: int = 0
    fin_temprano: int = 0
    inicio_tardio: int = 0
    fin_tardio: int = 0

    @property
    def holgura_total(self) -> int:
        return self.inicio_tardio - self.inicio_temprano

    @property
    def critica(self) -> bool:
        return self.holgura_total == 0


@dataclass
class Programa:
    actividades: dict[str, Actividad]
    duracion: int

    @property
    def ruta_critica(self) -> list[str]:
        orden = sorted(self.actividades.values(), key=lambda a: (a.inicio_temprano, a.codigo))
        return [a.codigo for a in orden if a.critica]


def duracion_por_rendimiento(metrado: float, rendimiento: float, n_cuadrillas: int = 1) -> int:
    """Días hábiles = metrado / (rendimiento × cuadrillas), redondeado hacia arriba."""
    return math.ceil(metrado / (rendimiento * n_cuadrillas) - 1e-9)


def programar(actividades: list[Actividad]) -> Programa:
    """Calcula fechas tempranas, tardías y holguras (pasada hacia adelante y atrás)."""
    if not actividades:
        raise ValueError("No hay actividades que programar")
    por_codigo: dict[str, Actividad] = {}
    for a in actividades:
        if a.codigo in por_codigo:
            raise ValueError(f"Código de actividad repetido: '{a.codigo}'")
        if a.duracion < 0:
            raise ValueError(f"{a.codigo}: la duración no puede ser negativa")
        por_codigo[a.codigo] = a

    sucesoras: dict[str, list[tuple[Actividad, Predecesora]]] = {c: [] for c in por_codigo}
    grafo = {}
    for a in actividades:
        for p in a.predecesoras:
            if p.codigo not in por_codigo:
                raise ValueError(f"{a.codigo}: predecesora '{p.codigo}' no existe")
            sucesoras[p.codigo].append((a, p))
        grafo[a.codigo] = {p.codigo for p in a.predecesoras}
    try:
        orden = list(TopologicalSorter(grafo).static_order())
    except CycleError as e:
        raise ValueError(f"Las predecesoras forman un ciclo: {' -> '.join(e.args[1])}") from None

    for codigo in orden:
        a = por_codigo[codigo]
        inicio = 0
        for p in a.predecesoras:
            pred = por_codigo[p.codigo]
            inicio = max(inicio, {
                "FC": pred.fin_temprano + p.desfase,
                "CC": pred.inicio_temprano + p.desfase,
                "FF": pred.fin_temprano + p.desfase - a.duracion,
                "CF": pred.inicio_temprano + p.desfase - a.duracion,
            }[p.tipo])
        a.inicio_temprano = inicio
        a.fin_temprano = inicio + a.duracion

    duracion = max(a.fin_temprano for a in actividades)

    for codigo in reversed(orden):
        a = por_codigo[codigo]
        fin = duracion
        for suc, p in sucesoras[codigo]:
            fin = min(fin, {
                "FC": suc.inicio_tardio - p.desfase,
                "CC": suc.inicio_tardio - p.desfase + a.duracion,
                "FF": suc.fin_tardio - p.desfase,
                "CF": suc.fin_tardio - p.desfase + a.duracion,
            }[p.tipo])
        a.fin_tardio = fin
        a.inicio_tardio = fin - a.duracion

    return Programa(por_codigo, duracion)


def fecha_habil(inicio_obra: date, dias: int, laborables=DIAS_LABORABLES, feriados=frozenset()) -> date:
    """Fecha del día hábil al que se llega tras `dias` días hábiles transcurridos.

    Para una actividad: comienza en fecha_habil(obra, a.inicio_temprano) y su
    último día de trabajo es fecha_habil(obra, a.fin_temprano - 1).
    """
    fecha = inicio_obra
    while fecha.weekday() not in laborables or fecha in feriados:
        fecha += timedelta(days=1)
    for _ in range(dias):
        fecha += timedelta(days=1)
        while fecha.weekday() not in laborables or fecha in feriados:
            fecha += timedelta(days=1)
    return fecha


def curva_s(programa: Programa, montos: dict[str, float]) -> list[float]:
    """Monto acumulado programado al final de cada día (fechas tempranas).

    acumulado[t] = lo ejecutado tras t días hábiles; acumulado[0] = 0 es el
    inicio de obra. Cada actividad avanza uniforme durante su duración; un hito
    (duración 0) suma su monto completo en su fecha.
    """
    faltantes = set(montos) - set(programa.actividades)
    if faltantes:
        raise ValueError(f"Montos para actividades que no existen: {sorted(faltantes)}")

    def avance(a: Actividad, t: int) -> float:
        if a.duracion == 0:
            return 1.0 if t >= a.inicio_temprano else 0.0
        return min(max((t - a.inicio_temprano) / a.duracion, 0.0), 1.0)

    return [
        sum(monto * avance(programa.actividades[c], t) for c, monto in montos.items())
        for t in range(programa.duracion + 1)
    ]


def graficar_gantt(programa: Programa, ruta: str | None = None):
    """Diagrama de Gantt con la ruta crítica en rojo (requiere matplotlib)."""
    import matplotlib.pyplot as plt

    actividades = sorted(programa.actividades.values(), key=lambda a: (a.inicio_temprano, a.codigo))
    fig, ax = plt.subplots(figsize=(10, 0.4 * len(actividades) + 1.5))
    for i, a in enumerate(actividades):
        color = "#c0392b" if a.critica else "#2e86c1"
        ax.barh(i, a.duracion, left=a.inicio_temprano, color=color)
        if a.holgura_total > 0:
            ax.barh(i, a.holgura_total, left=a.fin_temprano, color="#d5d8dc", height=0.3)
    ax.set_yticks(range(len(actividades)), [f"{a.codigo} {a.descripcion}" for a in actividades])
    ax.invert_yaxis()
    ax.set_xlabel("Días hábiles")
    ax.set_title(f"Programación de obra — duración {programa.duracion} días (rojo: ruta crítica)")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    if ruta:
        fig.savefig(ruta, dpi=150)
    return fig
