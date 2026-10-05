"""Flujos completos: los módulos deben cuadrar entre sí como en un expediente."""
from itertools import pairwise

import pytest

from civil.apu import APU, ItemPresupuesto, Presupuesto
from civil.cpm import Actividad, Predecesora, curva_s, duracion_por_rendimiento, programar
from civil.metrados import Partida, PlanillaAcero
from civil.sismo_e030 import CT, R0, cortante_basal, distribucion_fuerzas, periodo_fundamental

PRECIO_HH = {"operario": 26.10, "oficial": 20.65, "peon": 18.60}


def test_metrado_presupuesto_cronograma_cuadran():
    concreto = Partida("05.03.01", "Concreto f'c=210 en columnas", "m3").agregar("C-1", 12, 0.30, 0.50, 2.80)
    acero = PlanillaAcero().agregar("C-1", '5/8"', 6, 12, 3.60).agregar("C-1 estribos", '3/8"', 20, 12, 1.45)
    acero_partida = Partida("05.03.03", "Acero fy=4200 en columnas", "kg").agregar("Según planilla", acero.total_kg)

    apu_concreto = (
        APU("Concreto columnas", "m3", rendimiento=10)
        .mano_obra("Operario", 2, PRECIO_HH["operario"])
        .mano_obra("Peón", 8, PRECIO_HH["peon"])
        .material("Cemento", "bls", 9.73, 28.50, desperdicio=0.05)
    )
    apu_acero = (
        APU("Acero columnas", "kg", rendimiento=250)
        .mano_obra("Operario", 1, PRECIO_HH["operario"])
        .mano_obra("Oficial", 1, PRECIO_HH["oficial"])
        .material("Acero corrugado", "kg", 1.0, 4.20, desperdicio=0.07)
    )
    items = [
        ItemPresupuesto(concreto.item, concreto.descripcion, "m3", concreto.total, apu_concreto.costo_unitario),
        ItemPresupuesto(
            acero_partida.item, acero_partida.descripcion, "kg", acero_partida.total, apu_acero.costo_unitario
        ),
    ]
    resumen = Presupuesto(items, gastos_generales=0.12, utilidad=0.08).resumen()

    # Cronograma con las mismas partidas y rendimientos del APU
    d_acero = duracion_por_rendimiento(acero_partida.total, apu_acero.rendimiento)
    d_concreto = duracion_por_rendimiento(concreto.total, apu_concreto.rendimiento)
    programa = programar(
        [
            Actividad(acero_partida.item, "Acero columnas", d_acero),
            Actividad(concreto.item, "Concreto columnas", d_concreto, [Predecesora(acero_partida.item, "FC", 1)]),
        ]
    )
    montos = {i.item: i.parcial for i in items}
    acumulado = curva_s(programa, montos)

    # Concreto: 12 × 0.30 × 0.50 × 2.80 = 5.04 m³ ; 5.04 / 10 -> 1 día
    # Acero: 259.2 m × 1.552 + 348 m × 0.560 = 597.16 kg ; 597.16 / 250 = 2.39 -> 3 días
    assert concreto.total == pytest.approx(5.04)
    assert acero.total_kg == pytest.approx(597.16)
    assert (d_acero, d_concreto) == (3, 1)
    assert programa.duracion == 3 + 1 + 1  # acero, 1 día de espera, concreto
    # La curva S termina exactamente en el costo directo del presupuesto
    assert acumulado[-1] == pytest.approx(resumen["costo_directo"])
    assert all(b >= a for a, b in pairwise(acumulado))
    assert resumen["total"] == pytest.approx(resumen["subtotal"] * 1.18, abs=0.01)


def test_analisis_sismico_edificio_5_pisos():
    # Edificio dual en Lima: zona 4, suelo S1, categoría C (vivienda), regular
    alturas = [3.0, 5.8, 8.6, 11.4, 14.2]  # m desde el terreno
    pesos = [180.0, 175.0, 175.0, 175.0, 130.0]  # tonf
    T = periodo_fundamental(alturas[-1], CT["dual_muros_albanileria"])
    R = R0["dual"]  # regular: Ia = Ip = 1
    V = cortante_basal(sum(pesos), 4, "S1", "C", R, T)
    F = distribucion_fuerzas(V, pesos, alturas, T)

    assert T == pytest.approx(0.237, abs=1e-3)
    assert V / sum(pesos) == pytest.approx(0.45 * 2.5 / 7)  # T < Tp -> C = 2.5
    assert sum(F) == pytest.approx(V)
    # Pisos 2 a 4 tienen igual peso: la fuerza crece con la altura (k = 1)
    assert F[1] < F[2] < F[3]
    assert F[2] / F[1] == pytest.approx(8.6 / 5.8)
