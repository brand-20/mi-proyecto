"""Pruebas de puente_losa.py contra cálculos a mano (Taller 01, configuración A–L)."""
import pytest

import puente_losa as pl

L = pl.TALLER_AL.luz  # 6.096 m


def test_t_min_losa_simplemente_apoyada():
    # 1.2 (6096 + 3000) / 30 = 363.84 mm; pizarra: L = 20 m -> 920 mm
    assert pl.t_min_losa(L) == pytest.approx(0.36384, abs=1e-5)
    assert pl.t_min_losa(20.0) == pytest.approx(0.920, abs=1e-6)


def test_tandem_formula_de_barre_para_dos_cargas_iguales():
    # M = 2P/L (L/2 - s/4)^2 = 22.68/6.096 (2.748)^2 = 28.095 tonf·m
    tandem = pl.vehiculo((11.34, 11.34), (1.20,))
    assert pl.momento_maximo(tandem, L).M == pytest.approx(28.095, abs=1e-3)


def test_camion_modificado_no_caben_los_tres_ejes():
    camion = pl.vehiculo((3.63, 14.52, 14.52), (3.00, 3.50))
    M = pl.momento_maximo(camion, L)
    # Ejes 2 y 3 a 3.50 m: 29.04/6.096 (3.048 - 0.875)^2 = 22.494 tonf·m
    assert M.M == pytest.approx(22.494, abs=1e-3)
    assert M.en_luz == (1, 2)


@pytest.mark.parametrize(
    "cargas, separaciones",
    [
        ((3.63, 14.52, 14.52), (3.00, 3.50)),
        ((3.63, 14.52, 14.52), (3.50, 3.70)),  # configuración M–Z
        ((3.63, 14.52, 14.52), (4.30, 4.30)),  # HL-93 estándar
        ((7.0, 9.0, 9.0, 9.0, 9.0), (3.50, 1.30, 4.50, 1.30)),
    ],
)
def test_momento_maximo_coincide_con_barrido(cargas, separaciones):
    v = pl.vehiculo(cargas, separaciones)
    assert pl.momento_maximo(v, L).M == pytest.approx(pl.momento_maximo_barrido(v, L), abs=2e-3)


def test_pregunta_02_reaccion_maxima():
    # Eje 3 sobre el apoyo, eje 2 a 1.30 m y eje 1 (7 t) a 4.80 m:
    # 9 + 9 (4.796/6.096) + 7 (1.296/6.096) = 17.569 tonf
    r = pl.reaccion_maxima(pl.VEHICULO_P2, L)
    assert r.R == pytest.approx(17.569, abs=1e-3)
    assert r.eje_en_apoyo == 2
    assert sorted(r.en_luz) == [0, 1, 2]


def test_pregunta_02_momento_maximo():
    # Eje doble 9 + 9 t a 1.30 m: 18/6.096 (3.048 - 0.325)^2 = 21.894 tonf·m
    M = pl.momento_maximo(pl.VEHICULO_P2, L)
    assert M.M == pytest.approx(21.894, abs=1e-3)
    assert M.x_critico == pytest.approx(2.723, abs=1e-3)


def test_anchos_de_franja():
    # E1 = 0.25 + 0.42 √(6.096·9.14) = 3.385 m; Em = 2.10 + 0.12 √(6.096·11.60) = 3.109 m
    assert pl.E_un_carril(L, 11.60) == pytest.approx(3.3851, abs=1e-4)
    assert pl.E_multiples_carriles(L, 11.60, 3) == pytest.approx(3.1091, abs=1e-4)
    assert pl.E_borde(0.40, 3.1091) == pytest.approx(1.4773, abs=1e-4)
    assert pl.numero_carriles(10.80) == 3


def test_beta1_y_acero_por_flexion():
    assert pl.beta_1(420) == pytest.approx(0.7558, abs=1e-4)
    # M_u = 31.805 tonf·m, b = 100, d = 36.23 -> As = 24.17 cm²
    assert pl.As_flexion(31.805e5, 420, 4200, 100, 36.23) == pytest.approx(24.17, abs=0.01)


def test_seccion_insuficiente_falla():
    with pytest.raises(ValueError, match="Sección insuficiente"):
        pl.As_flexion(500e5, 420, 4200, 100, 36.23)


def test_espesor_menor_al_minimo_falla():
    from dataclasses import replace

    with pytest.raises(ValueError, match="Aumentar el espesor"):
        pl.calcular(replace(pl.TALLER_AL, t=0.30))


def test_diseno_completo_cumple():
    r = pl.calcular(pl.TALLER_AL)
    assert all(v.cumple for v in r["verificaciones"])
    interior, borde_separador, borde_vereda = r["franjas"]
    # W = 0.15 + 1.50 + 0.61 + 13.20 + 0.61 = 16.07 m
    assert pl.TALLER_AL.W == pytest.approx(16.07)
    # Un carril gobierna: 1.20 × 41.789 / 3.385 = 14.814 t·m/m
    assert r["M_1carril"] == pytest.approx(14.814, abs=1e-3)
    assert interior.M_u == pytest.approx(34.363, abs=1e-3)
    # La franja de la vereda no recibe vehículos; su espaciamiento lo controla la fisuración
    assert not borde_vereda.vehicular
    assert (interior.s, borde_separador.s, borde_vereda.s) == (17.5, 17.5, 30.0)


def test_vereda_segun_velocidad_y_pesos_de_clase():
    assert pl.ancho_vereda(60) == 1.20
    assert pl.ancho_vereda(70) == 1.50
    # 2240 + 0.23(420) + 80 = 2416.6 kg/m³; f'c <= 350: 2320 + 80 = 2400 kg/m³
    assert pl.gamma_concreto(420) == pytest.approx(2.4166)
    assert pl.gamma_concreto(280) == pytest.approx(2.400)
