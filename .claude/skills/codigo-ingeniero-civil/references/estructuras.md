# Estructuras: E.060, E.030, E.020 y ACI 318 / ASCE 7

Valores de las ediciones indicadas. Si el proyecto usa otra edición, cambia la
constante `NORMA` y los valores juntos. Lo marcado **(verificar)** no se ha
contrastado con el texto oficial: confírmalo antes de usarlo en un expediente.

## Contenido
1. Materiales
2. Combinaciones de carga
3. Factores φ
4. Flexión
5. Corte
6. Columnas
7. Recubrimientos
8. E.030 — sismo
9. E.020 — cargas
10. ACI 318-19 en SI: qué cambia

## 1. Materiales (E.060, kgf/cm²)

| Propiedad | Valor | Referencia |
|---|---|---|
| f'c usual | 175, 210, 280, 350 | — |
| fy (ASTM A615 Gr 60) | 4200 | — |
| Ec | 15 000 √f'c | E.060 Art. 8.5.1 |
| Es | 2 000 000 | E.060 Art. 8.5.5 |
| εcu | 0.003 | E.060 Art. 10.2.3 |
| Peso concreto armado | 2.4 tonf/m³ | E.020 Anexo 1 |

## 2. Combinaciones de carga

**E.060 Art. 9.2** (va con los φ de la E.060):

```
U = 1.4 CM + 1.7 CV
U = 1.25 (CM + CV) ± CS
U = 0.9 CM ± CS
U = 1.25 (CM + CV ± CVi)      # viento
U = 0.9 CM ± 1.25 CVi
```

**ASCE 7-22 / ACI 318-19 Tabla 5.3.1** (va con los φ del ACI):

```
1.4 D
1.2 D + 1.6 L + 0.5 (Lr o S o R)
1.2 D + 1.6 (Lr o S o R) + (L o 0.5 W)
1.2 D + 1.0 W + L + 0.5 (Lr o S o R)
1.2 D + 1.0 E + L + 0.2 S
0.9 D + 1.0 W
0.9 D + 1.0 E
```

Escríbelas como datos, no repartidas en `if`:

```python
COMBINACIONES_E060 = {
    "U1": {"CM": 1.4, "CV": 1.7},
    "U2": {"CM": 1.25, "CV": 1.25, "CS": 1.0},
    "U3": {"CM": 1.25, "CV": 1.25, "CS": -1.0},
    "U4": {"CM": 0.9, "CS": 1.0},
    "U5": {"CM": 0.9, "CS": -1.0},
}

def envolvente(cargas: dict[str, float], combinaciones=COMBINACIONES_E060) -> tuple[float, float]:
    """(mínimo, máximo) de las combinaciones; cargas en servicio, misma unidad."""
    valores = [sum(f * cargas.get(c, 0.0) for c, f in comb.items()) for comb in combinaciones.values()]
    return min(valores), max(valores)
```

## 3. Factores φ

| Solicitación | E.060 Art. 9.3.2 | ACI 318-19 Tabla 21.2.1 |
|---|---|---|
| Flexión (controlada por tracción) | 0.90 | 0.90 |
| Compresión con estribos | 0.70 | 0.65 |
| Compresión con espiral | 0.75 | 0.75 |
| Corte y torsión | 0.85 | 0.75 |
| Aplastamiento | 0.70 | 0.65 |

En el ACI, φ varía linealmente entre compresión y tracción según εt
(Tabla 21.2.2). La E.060 maneja la transición por carga axial; ver Art. 9.3.2.

## 4. Flexión (sección rectangular simplemente armada)

```
a      = As·fy / (0.85·f'c·b)
φMn    = φ·As·fy·(d − a/2)
Ru     = Mu / (φ·b·d²)
ρ      = 0.85·f'c/fy · (1 − √(1 − 2·Ru / (0.85·f'c)))
β1     = 0.85 si f'c ≤ 280; baja 0.05 cada 70 kgf/cm²; mínimo 0.65   (Art. 10.2.7.3)
ρb     = 0.85·β1·f'c/fy · 6000/(6000 + fy)
ρmax   = 0.75·ρb                                                    (Art. 10.3.4)
As_min = 0.7·√f'c/fy · b_w·d                                         (Art. 10.5.2)
```

Implementado en `civil/concreto_e060.py` (`As_flexion`, `phi_Mn`, `verificar_flexion`).
Peralte efectivo usual en vigas: `d = h − recubrimiento − ø_estribo − ø_barra/2`
(≈ h − 6 cm con recubrimiento de 4 cm, estribo 3/8" y barra 5/8").

## 5. Corte

```
Vc       = 0.53·√f'c·b_w·d                     (Art. 11.3.1.1)
Vs       = Vu/φ − Vc
s        = Av·fy·d / Vs                        (Av = área de todas las ramas)
Vs ≤ 2.1·√f'c·b_w·d                            (Art. 11.5.7.9)
s_max    = d/2 ≤ 60 cm; si Vs > 1.1·√f'c·b_w·d, s_max = d/4 ≤ 30 cm   (Art. 11.5.5) (verificar)
```

En elementos sismorresistentes manda el Cap. 21 (confinamiento, corte por
capacidad); verifícalo aparte, no lo mezcles con el espaciamiento por resistencia.

## 6. Columnas (verificar)

```
φPn,max = 0.80·φ·[0.85·f'c·(Ag − Ast) + fy·Ast]     # con estribos, φ = 0.70
Cuantía longitudinal: 1 % ≤ ρ ≤ 6 % (E.060 Art. 10.9.1); ACI 318: 1 % a 8 %
```

Para flexocompresión, genera el diagrama de interacción por compatibilidad de
deformaciones (εcu = 0.003, bloque de Whitney) con una función por punto y
verifica cada combinación contra la curva. Devuelve `Verificacion` por combinación.

## 7. Recubrimientos mínimos (E.060 Art. 7.7.1) (verificar)

| Caso | cm |
|---|---|
| Vaciado contra el suelo y expuesto a él | 7 |
| Expuesto a suelo o intemperie, barras ≥ 3/4" | 5 |
| Expuesto a suelo o intemperie, barras ≤ 5/8" | 4 |
| No expuesto: losas, muros, viguetas | 2 |
| No expuesto: vigas y columnas | 4 |

## 8. E.030-2018 — diseño sismorresistente

Implementado en `civil/sismo_e030.py`.

```
V    = Z·U·C·S / R · P         con C/R ≥ 0.11
T    = hn / CT                  CT = 35 pórticos; 45 pórticos con muros en ascensores/escaleras;
                                60 albañilería, duales, muros estructurales y de ductilidad limitada
C    = 2.5                      si T < Tp
     = 2.5·Tp/T                 si Tp ≤ T < TL
     = 2.5·Tp·TL/T²             si T ≥ TL
Fi   = αi·V,  αi = Pi·hi^k / Σ Pj·hj^k,   k = 1 si T ≤ 0.5 s; k = 0.75 + 0.5·T ≤ 2 si T > 0.5 s
R    = R0·Ia·Ip
```

| Zona | Z | S0 | S1 | S2 | S3 |
|---|---|---|---|---|---|
| 4 | 0.45 | 0.80 | 1.00 | 1.05 | 1.10 |
| 3 | 0.35 | 0.80 | 1.00 | 1.15 | 1.20 |
| 2 | 0.25 | 0.80 | 1.00 | 1.20 | 1.40 |
| 1 | 0.10 | 0.80 | 1.00 | 1.60 | 2.00 |

| Perfil | Tp (s) | TL (s) |
|---|---|---|
| S0 | 0.3 | 3.0 |
| S1 | 0.4 | 2.5 |
| S2 | 0.6 | 2.0 |
| S3 | 1.0 | 1.6 |

- U: A2 = 1.5, B = 1.3, C = 1.0. A1 depende del aislamiento sísmico: no lo
  asumas, pregúntalo.
- R0 (concreto armado): pórticos 8, dual 7, muros estructurales 6, muros de
  ductilidad limitada 4. Albañilería armada o confinada: 3.
- Peso sísmico P: CM + 50 % CV (categorías A y B); CM + 25 % CV (categoría C);
  80 % de la carga en depósitos; 25 % de la CV en azoteas y techos (Art. 26) (verificar).
- Derivas: desplazamiento inelástico = 0.75·R × elástico (regular) o 0.85·R
  (irregular). Límites Δ/h: concreto armado 0.007, acero 0.010,
  albañilería 0.005, madera 0.010, muros de ductilidad limitada 0.005.
- Análisis dinámico: el cortante en la base no menor que el 80 % del estático
  (regular) o el 90 % (irregular); si no, escalar (verificar).
- Excentricidad accidental: 0.05 de la dimensión perpendicular al sismo (verificar).

## 9. E.020 — cargas (verificar contra Anexo 1 y Tabla 1)

| Carga | Valor |
|---|---|
| Losa aligerada h = 17 / 20 / 25 / 30 cm | 280 / 300 / 350 / 420 kgf/m² |
| Albañilería sólida / hueca | 1800 / 1350 kgf/m³ |
| Piso terminado (usual) | 100 kgf/m² |
| CV vivienda | 200 kgf/m² |
| CV oficinas | 250 kgf/m² |
| CV aulas | 250 kgf/m² |
| CV azotea (techo con pendiente ≤ 3°) | 100 kgf/m² |

Las cargas van como datos de entrada con su fuente, nunca dentro de la función
de diseño.

## 10. ACI 318-19 en SI: qué cambia

Si el usuario pide ACI, trabaja en N, mm, MPa y crea un módulo aparte
(`concreto_aci318.py`); no reutilices las constantes en kgf/cm².

```
Vc     = 0.17·λ·√f'c·b_w·d       (si Av ≥ Av,min; si no, ver Tabla 22.5.5.1, efecto de tamaño)
As_min = max(0.25·√f'c/fy, 1.4/fy)·b_w·d                   (9.6.1.2)
β1     = 0.85 si f'c ≤ 28 MPa; baja 0.05 cada 7 MPa; mínimo 0.65   (Tabla 22.2.2.4.3)
Vigas: εt ≥ 0.004 (9.3.3.1); φ = 0.90 solo si εt ≥ εty + 0.003
```

Conversión: 1 MPa = 10.197 kgf/cm², así f'c = 21 MPa ≈ 214 kgf/cm² y
√f'c en kgf/cm² ≈ 3.19·√f'c en MPa (de ahí 0.53 ≈ 0.17 × 3.19).
