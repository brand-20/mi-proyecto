"""Metrados, costos y programación con números verificables a mano."""
from datetime import date

import pytest

from civil.apu import APU, ItemPresupuesto, Presupuesto
from civil.cpm import (
    Actividad,
    Predecesora,
    curva_s,
    duracion_por_rendimiento,
    fecha_habil,
    graficar_gantt,
    programar,
)
from civil.metrados import Partida, PlanillaAcero, a_filas, exportar_excel


def test_partida_concreto_con_descuento():
    p = (
        Partida("05.03.01", "Concreto f'c=210 kg/cm² en columnas", "m3")
        .agregar("C-1 (eje A)", veces=4, largo=0.30, ancho=0.50, alto=2.80)
        .agregar("Descuento ducto", veces=-1, largo=0.10, ancho=0.10, alto=2.80)
    )
    # 4 × 0.42 − 0.028 = 1.652 m³ -> se reporta a 2 decimales
    assert p.total == 1.65


def test_medicion_con_dimensiones_incorrectas_falla():
    p = Partida("05.03.02", "Encofrado de columnas", "m2").agregar("C-1", veces=4, largo=1.6)
    with pytest.raises(ValueError, match="necesita 2 dimensiones"):
        _ = p.total


def test_planilla_acero():
    planilla = (
        PlanillaAcero()
        .agregar("Columna C-1", '5/8"', n_piezas=6, n_elementos=4, longitud=3.60)
        .agregar("Columna C-1 estribos", '3/8"', n_piezas=20, n_elementos=4, longitud=1.45)
    )
    resumen = planilla.resumen_por_diametro()
    assert resumen['5/8"']["longitud"] == pytest.approx(86.4)
    assert resumen['5/8"']["peso"] == pytest.approx(86.4 * 1.552)
    assert planilla.total_kg == pytest.approx(round(86.4 * 1.552 + 116 * 0.560, 2))


def test_exportar_excel(tmp_path):
    p = Partida("05.03.01", "Concreto columnas", "m3").agregar("C-1", 4, 0.3, 0.5, 2.8)
    assert len(a_filas([p])) == 2
    ruta = tmp_path / "metrado.xlsx"
    exportar_excel([p], str(ruta))
    assert ruta.exists()


def test_apu():
    apu = (
        APU("Muro de ladrillo KK de soga", "m2", rendimiento=10)
        .mano_obra("Operario", cuadrilla=1, precio_hh=25.00)
        .mano_obra("Peón", cuadrilla=0.5, precio_hh=18.00)
        .material("Ladrillo KK 18 huecos", "und", cantidad=38, precio=0.90, desperdicio=0.05)
    )
    # Operario 0.8 hh × 25 = 20.00 ; Peón 0.4 hh × 18 = 7.20
    assert apu.subtotal("mano_obra") == pytest.approx(27.20)
    assert apu.herramientas_manuales == pytest.approx(0.82)
    # 38 × 1.05 = 39.9 und × 0.90 = 35.91
    assert apu.subtotal("material") == pytest.approx(35.91)
    assert apu.costo_unitario == pytest.approx(27.20 + 0.82 + 35.91)


def test_presupuesto():
    pres = Presupuesto(
        [ItemPresupuesto("01", "Muro", "m2", 120.0, 63.93), ItemPresupuesto("02", "Tarrajeo", "m2", 240.0, 25.50)],
        gastos_generales=0.10,
        utilidad=0.05,
    )
    r = pres.resumen()
    assert r["costo_directo"] == pytest.approx(7671.60 + 6120.00)
    assert r["subtotal"] == pytest.approx(13791.60 + 1379.16 + 689.58)
    assert r["total"] == pytest.approx(r["subtotal"] + r["igv"])
    assert r["igv"] == pytest.approx(round(r["subtotal"] * 0.18, 2))


def test_duracion_por_rendimiento():
    assert duracion_por_rendimiento(120, 10) == 12
    assert duracion_por_rendimiento(125, 10, n_cuadrillas=2) == 7


def test_cpm_ruta_critica():
    acts = [
        Actividad("A", "Excavación", 3),
        Actividad("B", "Cimientos", 4, [Predecesora("A")]),
        Actividad("C", "Acero de columnas", 2, [Predecesora("A")]),
        Actividad("D", "Columnas", 5, [Predecesora("B"), Predecesora("C")]),
        Actividad("E", "Muros", 4, [Predecesora("D", "CC", 2)]),
    ]
    prog = programar(acts)
    # A 0-3, B 3-7, C 3-5, D 7-12, E empieza 2 días después de D: 9-13
    assert prog.duracion == 13
    assert prog.ruta_critica == ["A", "B", "D", "E"]
    c = prog.actividades["C"]
    assert (c.inicio_temprano, c.inicio_tardio, c.holgura_total) == (3, 5, 2)


def test_cpm_relacion_ff_y_ciclo():
    prog = programar([Actividad("A", "Losa", 5), Actividad("B", "Curado", 7, [Predecesora("A", "FF", 3)])])
    assert prog.actividades["B"].inicio_temprano == 1
    assert prog.duracion == 8
    with pytest.raises(ValueError, match="ciclo"):
        programar([Actividad("A", "x", 1, [Predecesora("B")]), Actividad("B", "y", 1, [Predecesora("A")])])


def test_cpm_valida_entradas():
    with pytest.raises(ValueError, match="repetido"):
        programar([Actividad("A", "x", 1), Actividad("A", "y", 2)])
    with pytest.raises(ValueError, match="no existe"):
        programar([Actividad("A", "x", 1, [Predecesora("Z")])])
    with pytest.raises(ValueError, match="no válida"):
        Predecesora("A", "XX")
    with pytest.raises(ValueError, match="No hay actividades"):
        programar([])


def test_fecha_habil_salta_domingos_y_feriados():
    lunes = date(2026, 10, 5)
    assert fecha_habil(lunes, 0) == lunes
    assert fecha_habil(lunes, 6) == date(2026, 10, 12)  # salta el domingo 11
    assert fecha_habil(lunes, 1, feriados={date(2026, 10, 6)}) == date(2026, 10, 7)


def test_curva_s():
    prog = programar([Actividad("A", "x", 2), Actividad("B", "y", 2, [Predecesora("A")])])
    assert curva_s(prog, {"A": 100.0, "B": 300.0}) == pytest.approx([0, 50, 100, 250, 400])


def test_curva_s_con_hito():
    prog = programar([Actividad("A", "x", 2), Actividad("H", "Entrega", 0, [Predecesora("A")])])
    assert curva_s(prog, {"A": 100.0, "H": 50.0}) == pytest.approx([0, 50, 150])
    with pytest.raises(ValueError, match="no existen"):
        curva_s(prog, {"Z": 1.0})


def test_gantt(tmp_path):
    import matplotlib

    matplotlib.use("Agg")
    prog = programar([Actividad("A", "x", 2), Actividad("B", "y", 3, [Predecesora("A")]), Actividad("C", "z", 1)])
    ruta = tmp_path / "gantt.png"
    graficar_gantt(prog, str(ruta))
    assert ruta.stat().st_size > 0


def test_apu_valida_rendimiento():
    with pytest.raises(ValueError, match="rendimiento"):
        APU("Tarrajeo", "m2", rendimiento=0)
