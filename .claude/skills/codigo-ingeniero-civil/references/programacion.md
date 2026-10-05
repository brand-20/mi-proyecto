# Programación de obra

Implementado en `civil/cpm.py`. Tiempos en días hábiles desde el inicio de
obra; las fechas calendario se calculan al final con `fecha_habil()`.

## Duraciones

```
duración (días) = ⌈ metrado / (rendimiento × n° de cuadrillas) ⌉
```

Usa el mismo rendimiento del APU. Si la duración del cronograma y el
rendimiento del APU no coinciden, el costo de mano de obra del presupuesto no
es el que se va a gastar.

```python
from civil.cpm import duracion_por_rendimiento
duracion_por_rendimiento(metrado=125, rendimiento=10, n_cuadrillas=2)   # 7 días
```

## Relaciones (como MS Project en español)

| Tipo | Significado | Restricción |
|---|---|---|
| FC | Fin-Comienzo | inicio(B) ≥ fin(A) + desfase |
| CC | Comienzo-Comienzo | inicio(B) ≥ inicio(A) + desfase |
| FF | Fin-Fin | fin(B) ≥ fin(A) + desfase |
| CF | Comienzo-Fin | fin(B) ≥ inicio(A) + desfase |

Desfase positivo = espera (p. ej. curado); negativo = adelanto (solape).

## Ruta crítica (CPM)

```python
from civil.cpm import Actividad, Predecesora, programar, graficar_gantt

actividades = [
    Actividad("01", "Excavación de zapatas", 3),
    Actividad("02", "Concreto de zapatas", 4, [Predecesora("01")]),
    Actividad("03", "Habilitación de acero de columnas", 2, [Predecesora("01")]),
    Actividad("04", "Columnas 1er piso", 5, [Predecesora("02"), Predecesora("03")]),
    Actividad("05", "Muros 1er piso", 4, [Predecesora("04", "CC", 2)]),
]
programa = programar(actividades)
programa.duracion        # 13 días
programa.ruta_critica    # ['01', '02', '04', '05']
graficar_gantt(programa, "gantt.png")
```

`programar()` rechaza códigos repetidos, predecesoras inexistentes y ciclos,
con el ciclo indicado en el mensaje.

## Calendario

- Días laborables por defecto: lunes a sábado (régimen de construcción civil,
  48 h semanales). Si la obra trabaja otro régimen, pásalo como parámetro.
- Feriados: cárgalos de un archivo por año. Cambian por ley y por región,
  así que no se escriben en el código.

```python
from datetime import date
from civil.cpm import fecha_habil

inicio_obra = date(2026, 10, 5)
a = programa.actividades["04"]
fecha_habil(inicio_obra, a.inicio_temprano)    # primer día de trabajo
fecha_habil(inicio_obra, a.fin_temprano - 1)   # último día de trabajo
```

## Curva S y valorizaciones

```python
from civil.cpm import curva_s

montos = {"01": 4_500.0, "02": 18_200.0, "03": 6_100.0, "04": 25_400.0, "05": 15_800.0}
acumulado = curva_s(programa, montos)   # acumulado[t] = S/ ejecutados tras t días hábiles
```

- Los montos por actividad salen del presupuesto (metrado × costo unitario),
  con el mismo ítem: así cronograma y presupuesto cuadran.
- Valorización mensual: programado del mes, ejecutado del mes, acumulados y
  % de avance (= acumulado / costo directo total). Grafica programado contra
  ejecutado acumulado en el mismo eje.
- Los criterios de atraso y penalidad dependen del contrato y del reglamento
  de contrataciones vigente: tómalos como parámetros, no los asumas.
