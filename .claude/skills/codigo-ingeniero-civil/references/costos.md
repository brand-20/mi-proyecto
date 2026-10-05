# Costos y presupuestos

Estructura de S10, que es lo que el usuario y las entidades leen. Implementado
en `civil/apu.py`. Montos en soles (S/) sin IGV salvo en el resumen final.

## Análisis de precios unitarios (APU)

```
Partida:      05.03.01  Concreto f'c = 210 kg/cm² en columnas
Rendimiento:  m3/DIA  MO. 10.0000  EQ. 10.0000
Costo unitario directo por m3:  S/ xxx.xx

Descripción             Und   Cuadrilla   Cantidad   Precio S/   Parcial S/
Mano de obra
  Operario              hh      2.0000     1.6000      ...         ...
  Peón                  hh      8.0000     6.4000      ...         ...
Materiales
  Cemento Portland I    bls                9.7300      ...         ...
Equipos
  Herramientas manuales %MO                3.0000      ...         ...
  Mezcladora 9-11 p3    hm      1.0000     0.8000      ...         ...
```

Fórmulas:

```
cantidad (hh o hm) = cuadrilla × jornada (8 h) / rendimiento (und/día)
cantidad material  = cantidad neta × (1 + desperdicio)
parcial            = cantidad × precio
herramientas       = % × total de mano de obra (3 % usual; declararlo en cada APU)
costo unitario     = MO + materiales + equipos (con herramientas) + subcontratos
```

Cantidades a 4 decimales y parciales a 2, como los muestra S10, para que los
totales cuadren con lo que ve el revisor.

```python
from civil.apu import APU

apu_muro = (
    APU("Muro de ladrillo KK de soga, mortero 1:4", "m2", rendimiento=10)
    .mano_obra("Operario", cuadrilla=1, precio_hh=precios["operario"])
    .mano_obra("Peón", cuadrilla=0.5, precio_hh=precios["peon"])
    .material("Ladrillo KK 18 huecos", "und", cantidad=38, precio=precios["ladrillo_kk"], desperdicio=0.05)
)
apu_muro.costo_unitario
```

## De dónde salen los números

| Dato | Fuente | En el código |
|---|---|---|
| Precio hora-hombre (operario, oficial, peón) | Tabla de salarios del régimen de construcción civil (convenio CAPECO – FTCCP) más leyes sociales; cambia cada año | CSV con fecha de vigencia |
| Precios de materiales y equipos | Cotizaciones o revista de costos; sin IGV | CSV con fuente y fecha |
| Rendimientos y cuadrillas | Rendimientos de la empresa o referencia (p. ej. CAPECO) | Datos del APU, con fuente |
| Desperdicios | Criterio del proyecto | Parámetro explícito por material |

Nunca escribas un precio en una función. Cárgalos así:

```python
import csv

def cargar_precios(ruta: str) -> dict[str, float]:
    """CSV con columnas: codigo, descripcion, unidad, precio, fuente, fecha."""
    with open(ruta, encoding="utf-8") as f:
        return {fila["codigo"]: float(fila["precio"]) for fila in csv.DictReader(f)}
```

## Presupuesto

```
Costo directo (CD)      = Σ metrado × costo unitario         (por ítem, redondeado a 2 decimales)
Gastos generales (GG)   = % CD o detallado (fijos + variables)
Utilidad                = % CD
Subtotal                = CD + GG + Utilidad
IGV                     = 18 % × Subtotal                     (verificar tasa vigente)
Total                   = Subtotal + IGV
```

`Presupuesto` exige GG y utilidad explícitos: dependen de cada obra y un
valor por defecto pasaría desapercibido.

```python
from civil.apu import ItemPresupuesto, Presupuesto

presupuesto = Presupuesto(
    items=[ItemPresupuesto("05.03.01", "Concreto en columnas", "m3", 12.35, apu_concreto.costo_unitario)],
    gastos_generales=0.10,
    utilidad=0.05,
)
presupuesto.resumen()   # {'costo_directo': ..., 'gastos_generales': ..., ..., 'total': ...}
```

## Fórmula polinómica (reajuste)

```
K = a·(Jr/Jo) + b·(Mr/Mo) + c·(Er/Eo) + ...     con a + b + c + ... = 1
```

Según el D.S. 011-79-VC: los índices son los Índices Unificados de Precios de
la Construcción (INEI); como máximo 8 monomios; cada coeficiente no menor de
0.05 (verificar). Los coeficientes salen de la incidencia de cada recurso en el
presupuesto: calcúlalos agrupando los insumos de todos los APU por índice
unificado, no a ojo.

## Redondeo

Usa `redondear()` de `civil/unidades.py` (mitad hacia arriba, como Excel y
S10). Redondea en cada parcial que se muestra en el reporte, no solo al
final; si no, la suma impresa no coincide con el total impreso.
