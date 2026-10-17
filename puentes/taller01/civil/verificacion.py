"""Resultado estándar de una verificación demanda/capacidad."""
from __future__ import annotations

from dataclasses import dataclass

# Margen numérico para que un diseño "justo" (D/C = 1.0000000001) no falle
# por errores de punto flotante.
TOLERANCIA = 1e-9


@dataclass(frozen=True)
class Verificacion:
    """Demanda vs. capacidad con su referencia normativa.

    Toda verificación devuelve este objeto: la memoria de cálculo se arma
    iterando resultados y cada chequeo conserva el artículo de donde salió.
    Para mínimos (p. ej. As >= As_min) lo requerido es la demanda y lo
    colocado es la capacidad.
    """

    descripcion: str
    demanda: float
    capacidad: float
    unidad: str
    referencia: str  # p. ej. "E.060 Art. 10.5.2"
    decimales: int = 2  # para reportar; cuantías y derivas necesitan 4

    @property
    def ratio(self) -> float:
        """Relación demanda/capacidad (D/C); cumple si es <= 1.0."""
        if self.capacidad <= 0:
            return float("inf")
        return self.demanda / self.capacidad

    @property
    def cumple(self) -> bool:
        return self.ratio <= 1.0 + TOLERANCIA

    def __str__(self) -> str:
        estado = "CUMPLE" if self.cumple else "NO CUMPLE"
        unidad = f" {self.unidad}" if self.unidad else ""
        n = self.decimales
        return (
            f"{self.descripcion} [{self.referencia}]: "
            f"{self.demanda:,.{n}f} <= {self.capacidad:,.{n}f}{unidad} "
            f"-> D/C = {self.ratio:.2f}  {estado}"
        )
