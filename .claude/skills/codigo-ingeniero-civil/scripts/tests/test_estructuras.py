"""Casos verificados a mano: viga 25x50, f'c = 210, fy = 4200, Mu = 12 tonf·m."""
import pytest

from civil.acero import area_acero, numero_barras, peso_acero
from civil.concreto_e060 import (
    As_flexion,
    As_min_flexion,
    Vc,
    beta1,
    cuantia_balanceada,
    espaciamiento_estribos,
    phi_Mn,
    verificar_flexion,
)
from civil.sismo_e030 import (
    coeficiente_sismico,
    cortante_basal,
    distribucion_fuerzas,
    exponente_k,
    factor_C,
    verificar_deriva,
)
from civil.unidades import MPA_A_KGF_CM2, TONF_M_A_KGF_CM, redondear

F_C, FY = 210.0, 4200.0
B, D = 25.0, 44.0
M_U = 12.0 * TONF_M_A_KGF_CM


def test_redondeo_comercial_como_excel():
    assert redondear(0.125, 2) == 0.13
    assert redondear(2.675, 2) == 2.68
    assert redondear(-1.005, 2) == -1.01


def test_conversion_mpa():
    assert 21 * MPA_A_KGF_CM2 == pytest.approx(214.1, abs=0.1)


def test_acero_comercial():
    assert area_acero({'5/8"': 3, '1/2"': 2}) == pytest.approx(8.58)
    assert numero_barras(7.88, '5/8"') == 4
    assert numero_barras(6.00, '5/8"') == 3
    assert peso_acero('3/8"', 9.0) == pytest.approx(5.04)
    with pytest.raises(ValueError, match="Válidas"):
        area_acero({'7/8"': 1})


def test_beta1():
    assert beta1(210) == 0.85
    assert beta1(350) == pytest.approx(0.80)
    assert beta1(700) == 0.65


def test_flexion_viga():
    As = As_flexion(M_U, F_C, FY, B, D)
    assert As == pytest.approx(7.88, abs=0.01)
    assert phi_Mn(As, F_C, FY, B, D) == pytest.approx(M_U)
    assert As_min_flexion(F_C, FY, B, D) == pytest.approx(2.66, abs=0.01)
    assert cuantia_balanceada(F_C, FY) == pytest.approx(0.02125, abs=1e-5)


def test_momento_negativo_usa_valor_absoluto():
    assert As_flexion(-M_U, F_C, FY, B, D) == pytest.approx(As_flexion(M_U, F_C, FY, B, D))


def test_reporte_de_verificacion_legible():
    texto = str(verificar_flexion(M_U, area_acero({'5/8"': 4}), F_C, FY, B, D)[2])
    assert "0.0073 <= 0.0159 ->" in texto
    assert "CUMPLE" in texto


def test_seccion_insuficiente_avisa():
    with pytest.raises(ValueError, match="Sección insuficiente"):
        As_flexion(60 * TONF_M_A_KGF_CM, F_C, FY, B, D)


def test_verificaciones_flexion():
    resultados = verificar_flexion(M_U, area_acero({'5/8"': 4}), F_C, FY, B, D)
    assert all(v.cumple for v in resultados)
    assert "E.060" in resultados[0].referencia
    insuficiente = verificar_flexion(M_U, area_acero({'1/2"': 3}), F_C, FY, B, D)
    assert not insuficiente[0].cumple


def test_corte():
    assert Vc(F_C, B, D) == pytest.approx(8448, abs=1)
    s = espaciamiento_estribos(15000, F_C, FY, B, D, Av=2 * 0.71)
    # Vs = 15000/0.85 - 8448 = 9199 kgf ; s = 1.42·4200·44/9199
    assert s == pytest.approx(28.5, abs=0.1)
    assert espaciamiento_estribos(5000, F_C, FY, B, D, Av=1.42) == float("inf")


def test_factor_C_tramos():
    assert factor_C(0.3, "S2") == 2.5
    assert factor_C(1.2, "S2") == pytest.approx(1.25)
    assert factor_C(2.5, "S2") == pytest.approx(2.5 * 0.6 * 2.0 / 2.5**2)


def test_cortante_basal_lima():
    # Zona 4, suelo S2, categoría C, pórticos regulares R = 8, T = 15/45
    T = 15 / 45
    assert coeficiente_sismico(4, "S2", "C", 8, T) == pytest.approx(0.1477, abs=1e-4)
    assert cortante_basal(500, 4, "S2", "C", 8, T) == pytest.approx(73.83, abs=0.01)


def test_parametros_invalidos_avisan():
    with pytest.raises(ValueError, match="Zona sísmica"):
        coeficiente_sismico(5, "S2", "C", 8, 0.3)
    with pytest.raises(ValueError, match="A1"):
        coeficiente_sismico(4, "S2", "A1", 8, 0.3)
    with pytest.raises(ValueError, match="Perfil de suelo"):
        factor_C(0.3, "S4")


def test_C_sobre_R_minimo():
    # T largo: C/R real < 0.11, se usa el mínimo
    assert coeficiente_sismico(4, "S1", "C", 8, 3.0) == pytest.approx(0.45 * 1.0 * 0.11 * 1.0)


def test_distribucion_fuerzas():
    assert exponente_k(0.4) == 1.0
    assert exponente_k(1.0) == pytest.approx(1.25)
    F = distribucion_fuerzas(100, [200, 200, 150], [3, 6, 9], 0.3)
    assert sum(F) == pytest.approx(100)
    assert F[0] == pytest.approx(100 * 600 / (600 + 1200 + 1350))


def test_deriva():
    # Regular: 0.75·8·0.0032/3 = 0.0064 ; irregular: 0.85·8·0.0032/3 = 0.00725 > 0.007
    v = verificar_deriva(0.0032, 3.0, 8, "concreto_armado", regular=True)
    assert v.demanda == pytest.approx(0.0064)
    assert v.cumple
    assert not verificar_deriva(0.0032, 3.0, 8, "concreto_armado", regular=False).cumple
