---
name: codigo-ingeniero-civil
description: "Estilo de código Python del usuario, ingeniero civil en Perú: diseño estructural (E.060, E.030, E.020 del RNE y ACI 318 / ASCE 7), metrados, costos y presupuestos (APU tipo S10) y programación de obras (CPM, Gantt, curva S). Usa esta skill SIEMPRE que el usuario pida escribir, revisar, corregir o refactorizar código, scripts, notebooks o funciones de ingeniería civil: diseño de vigas, columnas, zapatas o losas, cortante basal, espectros, derivas, combinaciones de carga, metrados de concreto, encofrado o acero, planillas de acero, análisis de precios unitarios, presupuestos, cronogramas, ruta crítica, valorizaciones o memorias de cálculo. Úsala aunque no diga 'estilo' ni 'skill', aunque pida solo 'un script rápido' o lo pida en inglés (beam design, quantity takeoff, cost estimate, construction schedule)."
compatibility: Python 3.10+. pandas, openpyxl y matplotlib solo para exportar a Excel y graficar.
---

# Código de ingeniería civil — estilo del usuario

El usuario es ingeniero civil en Perú. Programa en Python para cuatro frentes:
**estructuras** (E.060, E.030, E.020; a veces ACI 318 / ASCE 7), **metrados**,
**costos y presupuestos**, y **programación de obras**. Su código lo revisa otro
ingeniero (supervisor, revisor del expediente, la entidad), así que debe leerse
como una memoria de cálculo: cada número tiene origen, unidad y referencia.
Responde y comenta en español.

## Antes de escribir código

1. **Norma y edición.** ¿E.060-2009 o ACI 318-19? ¿E.030-2018? Si el usuario no
   lo dice y el proyecto es en Perú, usa el RNE y decláralo en la cabecera.
2. **Unidades.** Elige el sistema de la tabla de abajo y no lo cambies a mitad.
3. **Reutiliza.** `scripts/civil/` ya trae funciones probadas (flexión, corte,
   E.030, metrados, APU, CPM). Úsalas o cópialas al proyecto antes de reescribir.
4. **Lee la referencia** de la especialidad (sección "Referencias", al final).
5. **Código existente.** Si el usuario ya tiene un archivo con otro estilo,
   respétalo en cambios puntuales; aplica este estilo a lo nuevo y a las
   refactorizaciones que pida. Mezclar estilos en un archivo lo vuelve ilegible.

## Principios y por qué

1. **Trazabilidad normativa.** Cada fórmula, factor o límite lleva su referencia
   (`# E.060 Art. 10.5.2`). Un revisor debe poder cotejar cada número con la
   norma sin preguntarle nada al autor.
2. **Unidades explícitas.** El error más caro en ingeniería es de unidades:
   un f'c = 210 kgf/cm² tomado como 210 MPa sobrestima diez veces la
   resistencia del concreto y el cálculo "cumple" sin cumplir. La
   unidad va en la cabecera del módulo, en el docstring de cada función y en el
   comentario de cada dato de entrada. Se convierte solo en la frontera
   (al leer datos o al reportar), con las constantes de `civil/unidades.py`.
3. **Sin números mágicos.** `0.53`, `0.85`, `0.11` aparecen una vez, como
   constante o en una fórmula con su artículo. Lo que cambia con el tiempo
   (precios, jornales, feriados) va en archivos de datos con fecha de
   vigencia, no en el código; las tasas (IGV, GG, utilidad) entran como
   parámetros, nunca escritas dentro de una fórmula.
4. **Demanda/capacidad explícita.** Toda verificación devuelve un
   `Verificacion` (demanda, capacidad, unidad, referencia, D/C, CUMPLE). Un
   `True` suelto no le dice al revisor cuánto margen hay.
5. **Fallar fuerte y en español.** Si la sección no alcanza o falta una
   dimensión, `raise ValueError("Sección insuficiente: ... Aumentar peralte")`.
   Un resultado silenciosamente incorrecto termina construido.
6. **Una norma a la vez.** Los φ de la E.060 (0.90 / 0.85 / 0.70) van con sus
   combinaciones (1.4CM + 1.7CV). Los del ACI 318-19 (0.90 / 0.75 / 0.65) van
   con ASCE 7 (1.2D + 1.6L). Mezclarlos da diseños inseguros o sobredimensionados.
7. **Probado contra un cálculo a mano.** Cada función de cálculo tiene un test
   con un caso resuelto a mano o de libro.
8. **No inventar valores normativos.** Si no estás seguro de un coeficiente o de
   un artículo, déjalo como parámetro, márcalo `# VERIFICAR: ...` y díselo al
   usuario. Un valor plausible pero falso es peor que un hueco visible.

## Nombres: español + notación de la norma

Se respeta la notación de la norma aunque rompa PEP 8 (mayúsculas en `M_u`,
`As`, `Vc`): así el código se lee igual que la fórmula del reglamento. En
`ruff`/`flake8`, desactivar N802, N803, N806, N815 y N816 (`assets/ruff.toml` ya lo trae). La regla:

- Solicitaciones últimas con `_u`: `M_u`, `V_u`, `P_u`, `w_u`. Así la
  demanda nunca se confunde con la resistencia.
- Resistencias, áreas y módulos tal como los escribe la norma: `Mn`, `Vc`,
  `Vs`, `As`, `Av`, `Ag`, `fy`, `Ec`. El apóstrofo y los subíndices de
  geometría van con guion bajo: `f_c` (f'c), `b_w`, `h_n`, `C_T`.
- Calificativos con guion bajo: `As_req`, `As_min`, `rho_max`, `phi_Mn`.

| Concepto | Nombre | Unidad típica |
|---|---|---|
| f'c, fy, Es | `f_c`, `fy`, `ES` | kgf/cm² |
| Ancho, peralte total, peralte efectivo | `b`, `b_w`, `h`, `d` | cm |
| Momento, cortante, axial últimos | `M_u`, `V_u`, `P_u` | kgf·cm, kgf |
| Resistencias de diseño | `phi_Mn`, `phi_Vn`, `phi_Pn` | kgf·cm, kgf |
| Aporte del concreto / acero al corte | `Vc`, `Vs` | kgf |
| Acero requerido / mínimo / colocado | `As_req`, `As_min`, `As` | cm² |
| Cuantía | `rho`, `rho_b`, `rho_max` | — |
| Parámetros sísmicos | `Z`, `U`, `C`, `S`, `R`, `T`, `Tp`, `TL` | —, s |
| Carga muerta / viva / sismo | `CM`, `CV`, `CS` | tonf, tonf/m |

- Todo lo demás en español y `snake_case`: `peralte_efectivo`, `partida`,
  `rendimiento`, `cuadrilla`, `holgura_total`.
- Sin tildes ni ñ en identificadores (`albanileria`, `diseno`, `anio`); sí en
  textos, comentarios y reportes.
- Funciones que devuelven una magnitud se nombran por la magnitud
  (`cortante_basal()`, `As_min_flexion()`); las que actúan, con verbo
  (`verificar_flexion()`, `exportar_excel()`, `programar()`).

## Unidades por especialidad

| Frente | Sistema | Ejemplo |
|---|---|---|
| Diseño en concreto (E.060) | kgf, cm | f'c = 210 kgf/cm², M_u en kgf·cm |
| Análisis y cargas | tonf, m | M_u = 12.5 tonf·m, w = 2.4 tonf/m |
| ACI 318 en SI | N, mm, MPa | f'c = 28 MPa |
| Metrados | m, m², m³, kg, und | Concreto 12.35 m³ |
| Costos | S/ sin IGV | CU = 63.93 S/ / m² |
| Programación | días hábiles | duración = 12 d |

## Estructura de un script de cálculo

Sigue `assets/plantilla_calculo.py` (ejecutable). El orden es el de una memoria:

```python
"""Diseño de la viga V-101 — Edificio Multifamiliar.

Norma:    E.060-2009, E.020 (RNE)
Unidades: kgf y cm para diseño; tonf y m para cargas
Autor / fecha / revisión
"""
# 1. Imports
# 2. Constantes normativas, cada una con su artículo
# 3. Datos de entrada juntos (dataclass), cada uno con su unidad
# 4. Funciones de cálculo puras: sin print, sin input, sin variables globales
# 5. Verificaciones -> list[Verificacion]
# 6. Reporte (memoria de cálculo)
# 7. if __name__ == "__main__": caso del proyecto
```

Una función de cálculo se ve así:

```python
def As_min_flexion(f_c: float, fy: float, b_w: float, d: float) -> float:
    """Acero mínimo en secciones rectangulares [cm²] (E.060 Art. 10.5.2).

    As_min = 0.7·√f'c / fy · b_w · d, con f'c y fy en kgf/cm², b_w y d en cm.
    """
    return 0.7 * math.sqrt(f_c) / fy * b_w * d
```

Argumentos explícitos con unidades en el docstring, type hints, la fórmula
escrita como en la norma y una sola responsabilidad.

## Salidas

- **Memoria de cálculo:** datos → fórmula con valores → resultado → verificación.
  Cada línea de verificación muestra demanda, capacidad, unidad, D/C y CUMPLE /
  NO CUMPLE (es lo que imprime `str(Verificacion)`).
- **Tablas para entregar** (metrados, APU, presupuesto, cronograma): en Excel
  con las columnas que se usan en Perú (ver referencias). Se generan con
  pandas + openpyxl, con anchos de columna y formato `#,##0.00`.
- **Redondeo:** se calcula sin redondear; se redondea al reportar (2 decimales;
  cuantías y derivas, 4). Para montos y metrados usa `redondear()` de
  `civil/unidades.py`, que redondea como Excel y S10. `round()` de Python
  redondea distinto (`round(0.125, 2) == 0.12`) y descuadra céntimos.
- **Gráficos:** matplotlib, título y ejes en español con unidades.

## Pruebas

pytest, un archivo por especialidad. Cada fórmula con un caso a mano y la
tolerancia acorde a los decimales que se reportan
(`pytest.approx(7.88, abs=0.01)`). También se prueban los caminos de error
(sección insuficiente, dimensiones faltantes, ciclos en el cronograma). Antes
de entregar, ejecuta el código y los tests.

## Librería incluida: `scripts/civil/`

Probada (`python -m pytest scripts/`). Para usarla en un proyecto, copia la
carpeta `civil/` junto al script o agrégala al `PYTHONPATH`.

| Módulo | Qué resuelve |
|---|---|
| `unidades` | Conversiones kgf/N/tonf, MPa/kgf/cm², `redondear()` como Excel |
| `verificacion` | `Verificacion` demanda/capacidad con referencia |
| `acero` | Barras comerciales (6 mm a 1 3/8"): área, peso, n° de barras |
| `concreto_e060` | φ, β1, ρb, ρmax, As_min, As por flexión, φMn, Vc, estribos |
| `sismo_e030` | Z, U, S, Tp, TL, C, ZUCS/R, cortante basal, fuerzas por piso, deriva |
| `metrados` | `Partida` con mediciones (veces × L × A × H, descuentos), planilla de acero, Excel |
| `apu` | APU con cuadrilla y rendimiento (formato S10), presupuesto con GG, utilidad, IGV |
| `cpm` | Ruta crítica con FC/CC/FF/CF y desfases, fechas hábiles, curva S, Gantt |

Si el usuario necesita algo que la librería no cubre (columnas, zapatas, losas,
ACI en SI), escríbelo con el mismo patrón y con su test.

## Referencias (lee solo la que aplica)

- `references/estructuras.md`: E.060, E.030, E.020 y ACI 318 / ASCE 7.
  Combinaciones, φ, fórmulas, tablas sísmicas, recubrimientos y diferencias
  entre normas.
- `references/metrados.md`: Norma Técnica de Metrados, formato de hoja,
  criterios de medición, losas aligeradas, planilla de acero.
- `references/costos.md`: APU estilo S10, mano de obra, presupuesto, fórmula
  polinómica y cómo cargar precios.
- `references/programacion.md`: duraciones por rendimiento, CPM, calendario,
  Gantt, curva S y valorizaciones.

## Revisión antes de entregar

- [ ] Norma, edición y unidades declaradas en la cabecera
- [ ] Cada constante normativa con su artículo; dudosas marcadas `# VERIFICAR`
- [ ] Conversiones de unidades solo en la frontera
- [ ] Verificaciones con D/C, no booleanos sueltos
- [ ] Errores en español que dicen qué hacer
- [ ] Código ejecutado y tests en verde
- [ ] Orden de magnitud contrastado: As entre As_min y ρmax·b·d; en concreto
      armado, zona 4, categoría C, ZUCS/R ronda 0.14–0.20 (R = 8 a 6)
- [ ] Al usuario: supuestos tomados y valores por confirmar
